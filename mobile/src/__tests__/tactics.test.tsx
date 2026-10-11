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
  jest.mocked(squadService.get).mockResolvedValue({ players, lineup: { formation: '4-4-2', starters, reserves: ['p11', 'p12'] }, formations: { '4-4-2': { DEF: 4, MED: 4, ATA: 2 }, '4-3-3': { DEF: 4, MED: 3, ATA: 3 }, '3-4-3': { DEF: 3, MED: 4, ATA: 3 }, '4-2-3-1': { DEF: 4, MED: 5, ATA: 1 } } });
});
test('selecting a strategy saves immediately without a save button', async () => {
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByRole('combobox', { name: 'Estilo de jogo' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Ataque total' }));
  await waitFor(() => expect(tacticsService.save).toHaveBeenCalledWith({ ...tactics, play_style: 'all_out_attack' }));
  expect(screen.queryByText('Salvar tática do clube')).toBeNull();
});
test('integrated lineup saves a replacement automatically and excludes injured reserves', async () => {
  await render(<TacticsScreen />);
  await screen.findByRole('combobox', { name: 'Formação' });
  expect(screen.queryByRole('combobox', { name: 'DEF 1' })).toBeNull();
  await fireEvent.press(screen.getByRole('button', { name: 'Substituir Jogador 1' }));
  expect(screen.getByRole('button', { name: 'Jogador 12, reserva, força 50' })).toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: 'Reserva Jogador 11' }));
  await waitFor(() => expect(squadService.save).toHaveBeenCalledWith({ formation: '4-4-2', starters: starters.map(id => id === 'p1' ? 'p11' : id), reserves: ['p1'], manual_positions: true }));
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

test('the strategy shows the pitch, roster and controls together and swaps a reserve from the pitch', async () => {
  await render(<TacticsScreen />);
  await screen.findByLabelText('Campo: formação 4-4-2');
  expect(screen.getByRole('combobox', { name: 'Formação' })).toBeTruthy();
  expect(screen.getByText('Energia')).toBeTruthy();
  expect(screen.queryByRole('tab', { name: 'Escalação' })).toBeNull();
  expect(screen.getByRole('button', { name: 'Reserva Jogador 11' })).not.toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: 'Substituir Jogador 1' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Reserva Jogador 11' }));
  await waitFor(() => expect(squadService.save).toHaveBeenCalledWith({ formation: '4-4-2', starters: starters.map(id => id === 'p1' ? 'p11' : id), reserves: ['p1'], manual_positions: true }));
});
test('failed replacement keeps the original starter on the pitch', async () => {
  jest.mocked(squadService.save).mockRejectedValueOnce(new Error('Não foi possível salvar a escalação.'));
  await render(<TacticsScreen />);
  await screen.findByLabelText('Campo: formação 4-4-2');
  await fireEvent.press(screen.getByRole('button', { name: 'Substituir Jogador 1' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Reserva Jogador 11' }));
  await screen.findByText('Não foi possível salvar a escalação.');
  expect(screen.getByRole('button', { name: 'Substituir Jogador 1' })).toBeTruthy();
});

test('selecting a reserve allows swapping with a starter from the player list', async () => {
  await render(<TacticsScreen />);
  await screen.findByLabelText('Campo: formação 4-4-2');
  expect(screen.getAllByText('T')).toHaveLength(11);
  expect(screen.getAllByText('R')).toHaveLength(1);
  await fireEvent.press(screen.getByRole('button', { name: 'Reserva Jogador 11' }));
  expect(screen.getByRole('button', { name: 'Jogador 9, titular, força 50' })).not.toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: 'Jogador 1, titular, força 50' }));
  await waitFor(() => expect(squadService.save).toHaveBeenCalledWith({ formation: '4-4-2', starters: starters.map(id => id === 'p1' ? 'p11' : id), reserves: ['p1'], manual_positions: true }));
});
test('two reserves can swap their places through touches without changing the starters', async () => {
  const extra = { ...players[9], id: 'p13', name: 'Jogador 13' };
  jest.mocked(squadService.get).mockResolvedValueOnce({ players: [...players, extra], lineup: { formation: '4-4-2', starters, reserves: ['p11', 'p13'] }, formations: { '4-4-2': { DEF: 4, MED: 4, ATA: 2 } } });
  await render(<TacticsScreen />);
  await screen.findByLabelText('Campo: formação 4-4-2');
  await fireEvent.press(screen.getByRole('button', { name: 'Reserva Jogador 11' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Jogador 13, reserva, força 50' }));
  await waitFor(() => expect(squadService.save).toHaveBeenCalledWith({ formation: '4-4-2', starters, reserves: ['p13', 'p11'], manual_positions: true }));
});
test('the player list displays accumulated yellows and a red card for a suspended player', async () => {
  jest.mocked(squadService.get).mockResolvedValueOnce({ players: players.map(player => player.id === 'p0' ? { ...player, yellow_cards_accumulated: 2 } : player.id === 'p12' ? { ...player, status: 'suspended', discipline_red_card: true, suspension_matches_remaining: 1 } : player), lineup: { formation: '4-4-2', starters, reserves: ['p11'] }, formations: { '4-4-2': { DEF: 4, MED: 4, ATA: 2 } } });
  await render(<TacticsScreen />);
  expect(await screen.findByLabelText('2 cartões amarelos')).toBeTruthy();
  expect(screen.getByLabelText('Cartão vermelho')).toBeTruthy();
});

test('changing formation rearranges the pitch immediately and shows improvisation without save messages', async () => {
  let finish!: () => void;
  jest.mocked(tacticsService.save).mockImplementationOnce(() => new Promise(resolve => { finish = () => resolve({ ...tactics, formation: '3-4-3' }); }));
  await render(<TacticsScreen />);
  await screen.findByLabelText('Campo: formação 4-4-2');
  await fireEvent.press(screen.getByRole('combobox', { name: 'Formação' }));
  await fireEvent.press(screen.getByRole('button', { name: '3-4-3' }));
  expect(screen.getByLabelText('Campo: formação 3-4-3')).toBeTruthy();
  expect(screen.getByLabelText('Linha ATA: 3 jogadores')).toBeTruthy();
  expect(screen.getAllByLabelText('Linha MED: 2 jogadores')).toHaveLength(2);
  expect(screen.getByLabelText('Linha DEF: 3 jogadores')).toBeTruthy();
  expect(screen.getByLabelText(/fora de posição/)).toBeTruthy();
  expect(screen.queryByText(/Salvamento automático/)).toBeNull();
  expect(screen.queryByRole('progressbar')).toBeNull();
  jest.mocked(tacticsService.get).mockResolvedValue({ ...tactics, formation: '3-4-3' });
  finish();
  await waitFor(() => expect(screen.getByRole('combobox', { name: 'Formação' })).not.toBeDisabled());
  expect(screen.queryByText('Tática salva.')).toBeNull();
});
test('an outfield reserve can replace a different position and goalkeeper swaps stay restricted', async () => {
  await render(<TacticsScreen />);
  await screen.findByLabelText('Campo: formação 4-4-2');
  await fireEvent.press(screen.getByRole('button', { name: 'Reserva Jogador 11' }));
  expect(screen.getByRole('button', { name: 'Jogador 0, titular, força 50' })).toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: 'Jogador 9, titular, força 50' }));
  await waitFor(() => expect(squadService.save).toHaveBeenCalledWith({ formation: '4-4-2', starters: starters.map(id => id === 'p9' ? 'p11' : id), reserves: ['p9'], manual_positions: true }));
});

test('4-2-3-1 displays both midfield lines instead of grouping all midfielders together', async () => {
  jest.mocked(tacticsService.get).mockResolvedValue({ ...tactics, formation: '4-2-3-1' });
  await render(<TacticsScreen />);
  await screen.findByLabelText('Campo: formação 4-2-3-1');
  expect(screen.getByLabelText('Linha ATA: 1 jogadores')).toBeTruthy();
  expect(screen.getByLabelText('Linha MED: 3 jogadores')).toBeTruthy();
  expect(screen.getByLabelText('Linha MED: 2 jogadores')).toBeTruthy();
  expect(screen.getByLabelText('Linha DEF: 4 jogadores')).toBeTruthy();
});

test('two starters exchange actual field positions and keep them after reloading the saved lineup', async () => {
  const swapped = starters.map(id => id === 'p1' ? 'p9' : id === 'p9' ? 'p1' : id);
  const data = { players, lineup: { formation: '4-4-2', starters, reserves: ['p11'] }, formations: { '4-4-2': { DEF: 4, MED: 4, ATA: 2 } } };
  jest.mocked(squadService.get).mockResolvedValueOnce(data).mockResolvedValue({ ...data, lineup: { ...data.lineup, starters: swapped, manual_positions: true } });
  await render(<TacticsScreen />);
  await screen.findByLabelText('Campo: formação 4-4-2');
  await fireEvent.press(screen.getByRole('button', { name: 'Substituir Jogador 1' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Substituir Jogador 9' }));
  await waitFor(() => expect(squadService.save).toHaveBeenCalledWith({ formation: '4-4-2', starters: swapped, reserves: ['p11'], manual_positions: true }));
  expect(await screen.findByLabelText('Jogador 1: fora de posição, natural DEF, escalado em ATA')).toBeTruthy();
  expect(screen.getByLabelText('Jogador 9: fora de posição, natural ATA, escalado em DEF')).toBeTruthy();
});
test('tactical selectors expand below the control without a popup or cancel button', async () => {
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByRole('combobox', { name: 'Marcação' }));
  expect(screen.getByRole('button', { name: 'Pesada' })).toBeTruthy();
  expect(screen.queryByText('Cancelar')).toBeNull();
});

test('editing stays enabled during saving and rapid changes persist the latest combined choices', async () => {
  let finish!: () => void;
  jest.mocked(tacticsService.save).mockImplementationOnce(() => new Promise(resolve => { finish = () => resolve({ ...tactics, play_style: 'all_out_attack' }); }));
  const latest = { ...tactics, play_style: 'all_out_attack', marking: 'heavy', attack_focus: 'wings' } as const;
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByRole('combobox', { name: 'Estilo de jogo' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Ataque total' }));
  expect(screen.getByRole('combobox', { name: 'Marcação' })).not.toBeDisabled();
  expect(screen.getByRole('combobox', { name: 'Formação' })).not.toBeDisabled();
  expect(screen.getByRole('button', { name: 'Substituir Jogador 1' })).not.toBeDisabled();
  await fireEvent.press(screen.getByRole('combobox', { name: 'Marcação' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Pesada' }));
  await fireEvent.press(screen.getByRole('combobox', { name: 'Foco dos ataques' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Laterais' }));
  expect(tacticsService.save).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Pesada')).toBeTruthy();
  expect(screen.getByText('Laterais')).toBeTruthy();
  jest.mocked(tacticsService.get).mockResolvedValue(latest);
  finish();
  await waitFor(() => expect(tacticsService.save).toHaveBeenCalledTimes(2));
  expect(tacticsService.save).toHaveBeenLastCalledWith(latest);
  await waitFor(() => expect(tacticsService.get).toHaveBeenCalledTimes(2));
  expect(screen.getByText('Pesada')).toBeTruthy();
  expect(screen.getByText('Laterais')).toBeTruthy();
});
