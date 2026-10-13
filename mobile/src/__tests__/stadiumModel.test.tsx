import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { StadiumScreen } from '../screens/StadiumScreen';
import { useStadiumStore } from '../stores/stadiumStore';
import { stadiumService } from '../services/stadiumService';
import { useNotificationStore } from '../stores/notificationStore';
import { Stadium } from '../types/game';
jest.mock('../components/useScreenRefresh', () => ({ useScreenRefresh: jest.fn() }));
jest.mock('../services/stadiumService', () => ({ stadiumService: { get: jest.fn(), upgrade: jest.fn(), price: jest.fn(), evolve: jest.fn() } }));
const initial: Stadium = { capacity: 10000, ticket_price: 2000, facilities: { medical: 1, gym: 0 }, names: { medical: 'Departamento médico', gym: 'Academia' }, upgrade_costs: { medical: 100000, gym: 400000 }, arena_level: 1, arena_name: 'Estádio local',
  levels: [{ level: 1, name: 'Estádio local', capacity: 10000, cost: 0, description: 'Local' }, { level: 2, name: 'Estádio municipal', capacity: 20000, cost: 20000000, description: 'Municipal' }],
  sectors: [{ id: 'lower_north', name: 'Inferior Norte', capacity: 1900, price: 2000, available: true }, { id: 'skybox', name: 'Skyboxes', capacity: 0, price: 2000, available: false }],
  facility_catalog: { medical: { name: 'Departamento médico', minimum_arena_level: 1, maximum_level: 5, icon: 4, benefit: 'Recuperação física', level_name: 'Essencial' }, gym: { name: 'Academia', minimum_arena_level: 2, maximum_level: 5, icon: 5, benefit: 'Energia', level_name: 'Não construído' } }, facility_level_names: ['Não construído','Essencial','Estruturado','Profissional','Avançado','Referência'] };
beforeEach(() => { jest.clearAllMocks(); useStadiumStore.getState().reset(); useStadiumStore.setState({ data: initial }); useNotificationStore.getState().clear(); });
test('sector map opens price editor and pending save does not disable further edits', async () => {
  let finish!: (data: Stadium) => void;
  jest.mocked(stadiumService.price).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  await render(<StadiumScreen />);
  expect(screen.getByRole('button', { name: 'Setor Skyboxes' })).toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: 'Setor Inferior Norte' }));
  await fireEvent.changeText(screen.getByLabelText('Ingresso do setor (R$)'), '35,50');
  await fireEvent.press(screen.getByRole('button', { name: 'Salvar preço do setor' }));
  expect(stadiumService.price).toHaveBeenCalledWith('lower_north', 3550);
  expect(screen.getByRole('button', { name: 'Setor Inferior Norte' })).toBeEnabled();
  expect(screen.getByText('R$ 35,50')).toBeTruthy();
  await act(() => finish({ ...initial, sectors: initial.sectors?.map(sector => sector.id==='lower_north' ? { ...sector, price: 3550 } : sector) }));
});
test('facility progression uses prerequisites rather than network saving to disable controls', async () => {
  let finish!: (data: Stadium) => void;
  jest.mocked(stadiumService.upgrade).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  await render(<StadiumScreen />);
  await fireEvent.press(screen.getByRole('tab', { name: 'Instalações' }));
  expect(screen.getByRole('button', { name: /Construir Academia/ })).toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: /Melhorar Departamento médico/ }));
  expect(screen.getByText('Nível 2 · Estruturado')).toBeTruthy();
  expect(screen.getByRole('button', { name: /Melhorar Departamento médico/ })).toBeEnabled();
  await act(() => finish({ ...initial, facilities: { ...initial.facilities, medical: 2 } }));
});
test('failed evolution restores capacity and shows a shared notification', async () => {
  jest.mocked(stadiumService.evolve).mockRejectedValue(new Error('Saldo insuficiente.'));
  await render(<StadiumScreen />);
  await fireEvent.press(screen.getByRole('tab', { name: 'Evolução' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Evoluir para Estádio municipal' }));
  await waitFor(() => expect(useNotificationStore.getState().message).toBe('Saldo insuficiente.'));
  expect(screen.getByText('Capacidade: 10.000 lugares')).toBeTruthy();
});
