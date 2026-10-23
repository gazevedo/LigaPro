import { act, fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { MatchLiveScreen } from '../screens/MatchLiveScreen';
import { LiveState, liveMatchService } from '../services/liveMatchService';
jest.mock('../services/liveMatchService', () => ({ liveMatchService: { state: jest.fn(), command: jest.fn(), commandId: jest.fn().mockReturnValue('command-1') } }));
function state(): LiveState { return { match_id: 'match', status: 'second_half', current_minute: 60, current_second: 0, updated_at: new Date().toISOString(), home_name: 'Casa', away_name: 'Visitante', home_score: 1, away_score: 0, simulation_speed: 1, paused: false, connected_users: 2, human_vs_human: true, home_possession: 55, away_possession: 45, home_attacks: 4, away_attacks: 3, home_chances: 2, away_chances: 1, home_shots: 2, away_shots: 1, home_shots_on_target: 1, away_shots_on_target: 0, home_fouls: 1, away_fouls: 2, home_yellow_cards: 1, away_yellow_cards: 0, home_red_cards: 0, away_red_cards: 0, match_momentum: { home: 3, away: 2 }, events: [{ sequence: 1, type: 'goal', minute: 31, narration: '31′ GOL! João finaliza.' }], own_team: { id: 'club', formation: '4-4-2', style: 'balanced', marking: 'light', attack_focus: 'normal', substitutions_used: 0, lineup: [{ id: 'out', name: 'João', position: 'ATT', assigned_position: 'ATT', energy: 70, physical_condition: 80, yellow_cards: 1, dismissed: false, injured: false }], reserves: [{ id: 'in', name: 'Pedro', position: 'ATT', assigned_position: 'ATT', energy: 100, physical_condition: 100, yellow_cards: 0, dismissed: false, injured: false }] } }; }

beforeEach(() => {
  jest.clearAllMocks(); jest.useFakeTimers();
  jest.mocked(liveMatchService.state).mockResolvedValue(state());
  jest.mocked(liveMatchService.command).mockResolvedValue({ status: 'pending' });
});
afterEach(() => { jest.useRealTimers(); });
test('follows the five minute match over HTTP and sends tactics and substitutions', async () => {
  const navigation = { navigate: jest.fn(), replace: jest.fn() };
  const props = { route: { params: { id: 'match' } }, navigation } as unknown as NativeStackScreenProps<RootStackParamList, 'MatchLive'>;
  await render(<MatchLiveScreen {...props} />);
  expect(await screen.findByText('Casa 1 × 0 Visitante')).toBeTruthy();
  expect(screen.getByText(/Duração: 5 minutos/)).toBeTruthy();
  expect(screen.queryByText('Ir para o final')).toBeNull();
  await fireEvent.press(screen.getByText('Aplicar mudanças táticas'));
  await waitFor(() => expect(liveMatchService.command).toHaveBeenCalledWith('match', 'combined_change', expect.objectContaining({ formation: '4-4-2' }), 'command-1'));
  await fireEvent.press(screen.getByText(/João · ATT · Energia/));
  await fireEvent.press(screen.getByText(/Pedro · ATT · Energia/));
  await fireEvent.press(screen.getByText('Confirmar substituição'));
  expect(liveMatchService.command).toHaveBeenLastCalledWith('match', 'substitution', { out_player_id: 'out', in_player_id: 'in' }, 'command-1');
  jest.mocked(liveMatchService.state).mockResolvedValue({ ...state(), status: 'finished', current_minute: 90 });
  await act(async () => { jest.advanceTimersByTime(2000); });
  expect(navigation.replace).toHaveBeenCalledWith('MatchReport', { id: 'match' });
});
test('shows command errors and stops polling after leaving', async () => {
  const props = { route: { params: { id: 'match' } }, navigation: { navigate: jest.fn(), replace: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'MatchLive'>;
  const result = await render(<MatchLiveScreen {...props} />);
  await screen.findByText('Casa 1 × 0 Visitante');
  jest.mocked(liveMatchService.command).mockRejectedValue(new Error('Substituição inelegível.'));
  await fireEvent.press(screen.getByText('Aplicar mudanças táticas'));
  expect(await screen.findByText('Substituição inelegível.')).toBeTruthy();
  await result.unmount();
  const calls = jest.mocked(liveMatchService.state).mock.calls.length;
  await act(async () => { jest.advanceTimersByTime(10000); });
  expect(liveMatchService.state).toHaveBeenCalledTimes(calls);
});
