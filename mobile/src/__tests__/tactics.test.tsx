import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { TacticsScreen } from '../screens/TacticsScreen';
import { tacticsService } from '../services/tacticsService';
import { squadService } from '../services/squadService';
import { useTacticsStore } from '../stores/tacticsStore';
import { useSquadStore } from '../stores/squadStore';
jest.mock('../services/tacticsService', () => ({ tacticsService: { get: jest.fn(), save: jest.fn(), matches: jest.fn() } }));
jest.mock('../services/squadService', () => ({ squadService: { get: jest.fn(), save: jest.fn() } }));
const tactics = { formation: '4-4-2', play_style: 'balanced', marking: 'light', attack_focus: 'normal' } as const;
const players = Array.from({ length: 13 }, (_, i) => ({ id: `p${i}`, name: `Jogador ${i}`, position: i === 0 ? 'GK' : i < 5 || i > 10 ? 'DEF' : i < 9 ? 'MID' : 'ATT', age: 22, overall: 50, value: 10000, country_id: 'BR', owner_club_id: 'club', current_club_id: 'club', status: i === 12 ? 'injured' : 'available' }));
const starters = players.slice(0, 11).map(player => player.id);
beforeEach(() => {
  jest.clearAllMocks(); useTacticsStore.getState().reset(); useSquadStore.getState().reset();
  jest.mocked(tacticsService.get).mockResolvedValue(tactics);
  jest.mocked(tacticsService.save).mockResolvedValue(tactics);
  jest.mocked(squadService.get).mockResolvedValue({ players, lineup: { formation: '4-4-2', starters, reserves: ['p11', 'p12'] }, formations: { '4-4-2': { DEF: 4, MED: 4, ATA: 2 }, '4-3-3': { DEF: 4, MED: 3, ATA: 3 } } });
});
test('selecting a strategy saves immediately without a save button', async () => {
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByRole('combobox', { name: 'Estilo de jogo' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Ataque total' }));
  await waitFor(() => expect(tacticsService.save).toHaveBeenCalledWith({ ...tactics, play_style: 'all_out_attack' }));
  expect(screen.queryByText('Salvar tática do clube')).toBeNull();
});
test('lineup tab saves a replacement automatically and excludes injured reserves', async () => {
  await render(<TacticsScreen />);
  await screen.findByRole('combobox', { name: 'Formação' });
  await fireEvent.press(screen.getByRole('tab', { name: 'Escalação' }));
  await fireEvent.press(screen.getByRole('combobox', { name: 'DEF 1' }));
  expect(screen.queryByRole('button', { name: 'Jogador 12 · 50' })).toBeNull();
  await fireEvent.press(screen.getByRole('button', { name: 'Jogador 11 · 50' }));
  await waitFor(() => expect(squadService.save).toHaveBeenCalledWith({ formation: '4-4-2', starters: starters.map(id => id === 'p1' ? 'p11' : id), reserves: ['p1'] }));
  expect(screen.queryByText('Salvar escalação')).toBeNull();
});
test('failed strategy save keeps the previous strategy and shows the error', async () => {
  jest.mocked(tacticsService.save).mockRejectedValueOnce(new Error('Partida em andamento.'));
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByRole('combobox', { name: 'Marcação' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Pesada' }));
  await screen.findByText('Partida em andamento.');
  expect(screen.getByText('Leve')).toBeTruthy();
});
