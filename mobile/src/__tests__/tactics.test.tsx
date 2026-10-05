import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { TacticsScreen } from '../screens/TacticsScreen';
import { tacticsService } from '../services/tacticsService';
import { squadService } from '../services/squadService';
import { useTacticsStore } from '../stores/tacticsStore';
import { useSquadStore } from '../stores/squadStore';
jest.mock('../services/tacticsService', () => ({ tacticsService: { get: jest.fn(), save: jest.fn(), matches: jest.fn(), command: jest.fn() } }));
jest.mock('../services/squadService', () => ({ squadService: { get: jest.fn(), save: jest.fn() } }));
jest.mock('../stores/clubStore', () => ({ useClubStore: (select: (state: { data: { club: { id: string } } }) => unknown) => select({ data: { club: { id: 'club1' } } }) }));
const tactics = { formation: '4-4-2', play_style: 'balanced', marking: 'light', attack_focus: 'normal' } as const;
const player = { id: 'starter', name: 'Pedro', position: 'ATT', age: 22, overall: 50, value: 10000, country_id: 'BR', owner_club_id: 'club1', current_club_id: 'club1' };
beforeEach(() => {
  jest.clearAllMocks(); useTacticsStore.getState().reset(); useSquadStore.getState().reset();
  jest.mocked(tacticsService.get).mockResolvedValue(tactics);
  jest.mocked(tacticsService.save).mockResolvedValue(tactics);
  jest.mocked(tacticsService.matches).mockResolvedValue([{ id: 'match1', round: 1, date: '2027-01-01T12:00:00Z', status: 'scheduled' }]);
  jest.mocked(tacticsService.command).mockResolvedValue([]);
  jest.mocked(squadService.get).mockResolvedValue({ players: [player, { ...player, id: 'reserve', name: 'Lucas' }], lineup: { formation: '4-4-2', starters: ['starter'], reserves: ['reserve'] }, formations: { '4-4-2': {}, '4-3-3': {} } });
});
test('saves four tactics using Portuguese choices', async () => {
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByText('Ataque total'));
  await fireEvent.press(screen.getByText('Pesada'));
  await fireEvent.press(screen.getByText('Laterais'));
  await fireEvent.press(screen.getByText('4-3-3'));
  await fireEvent.press(screen.getByText('Salvar tática do clube'));
  await waitFor(() => expect(tacticsService.save).toHaveBeenCalledWith({ formation: '4-3-3', play_style: 'all_out_attack', marking: 'heavy', attack_focus: 'wings' }));
  await screen.findByText('Tática salva.');
});
test('plans substitution with actual starter and reserve', async () => {
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByText(/Rodada 1/));
  await fireEvent.press(screen.getByText('Pedro · ATT'));
  await fireEvent.press(screen.getByText('Lucas · ATT'));
  await fireEvent.press(screen.getByText('Programar substituição'));
  await waitFor(() => expect(tacticsService.command).toHaveBeenCalledWith('match1', { minute: 60, type: 'substitution', payload: { out_player_id: 'starter', in_player_id: 'reserve' } }));
});
test('plans tactical changes and rejects minutes without future blocks', async () => {
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByText(/Rodada 1/));
  await fireEvent.changeText(screen.getByLabelText('Minuto do comando (0–85)'), '90');
  await fireEvent.press(screen.getByText('Programar mudança com a tática acima'));
  await screen.findByText('Informe um minuto de 0 a 85.');
  expect(tacticsService.command).not.toHaveBeenCalled();
  await fireEvent.changeText(screen.getByLabelText('Minuto do comando (0–85)'), '45');
  await fireEvent.press(screen.getByText('Programar mudança com a tática acima'));
  await waitFor(() => expect(tacticsService.command).toHaveBeenCalledWith('match1', { minute: 45, type: 'tactics_change', payload: tactics }));
});
test('shows server rejection without adding local command', async () => {
  jest.mocked(tacticsService.command).mockRejectedValue(new Error('Máximo de cinco substituições.'));
  await render(<TacticsScreen />);
  await fireEvent.press(await screen.findByText(/Rodada 1/));
  await fireEvent.press(screen.getByText('Pedro · ATT'));
  await fireEvent.press(screen.getByText('Lucas · ATT'));
  await fireEvent.press(screen.getByText('Programar substituição'));
  await screen.findByText('Máximo de cinco substituições.');
  expect(screen.queryByText('Comando programado.')).toBeNull();
});
