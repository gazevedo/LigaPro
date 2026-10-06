import { act, fireEvent, render, screen } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { MatchLiveScreen } from '../screens/MatchLiveScreen';
import { LiveState, liveMatchService } from '../services/liveMatchService';
jest.mock('../services/liveMatchService', () => ({ liveMatchService: { connect: jest.fn(), commandId: jest.fn().mockReturnValue('command-1') } }));
function socket() { return { readyState: 1, send: jest.fn(), close: jest.fn(), onopen: null as (() => void) | null, onmessage: null as ((e: { data: string }) => void) | null, onclose: null as ((e: { code: number }) => void) | null, onerror: null as (() => void) | null }; }
function state(): LiveState { return { match_id: 'match', status: 'second_half', current_minute: 60, current_second: 0, updated_at: new Date().toISOString(), home_name: 'Casa', away_name: 'Visitante', home_score: 1, away_score: 0, simulation_speed: 1, paused: false, connected_users: 2, human_vs_human: true, home_possession: 55, away_possession: 45, home_attacks: 4, away_attacks: 3, home_chances: 2, away_chances: 1, home_shots: 2, away_shots: 1, home_shots_on_target: 1, away_shots_on_target: 0, home_fouls: 1, away_fouls: 2, home_yellow_cards: 1, away_yellow_cards: 0, home_red_cards: 0, away_red_cards: 0, match_momentum: { home: 3, away: 2 }, events: [{ sequence: 1, type: 'goal', minute: 31, narration: '31′ GOL! João finaliza.' }], own_team: { id: 'club', formation: '4-4-2', style: 'balanced', marking: 'light', attack_focus: 'normal', substitutions_used: 0, lineup: [{ id: 'out', name: 'João', position: 'ATT', assigned_position: 'ATT', energy: 70, physical_condition: 80, yellow_cards: 1, dismissed: false, injured: false }], reserves: [{ id: 'in', name: 'Pedro', position: 'ATT', assigned_position: 'ATT', energy: 100, physical_condition: 100, yellow_cards: 0, dismissed: false, injured: false }] } }; }
beforeEach(() => { jest.clearAllMocks(); Object.defineProperty(global, 'WebSocket', { value: { OPEN: 1 }, configurable: true }); });
test('shares server state, sends own tactics and substitution, prevents unilateral skips', async () => {
  const ws = socket(); jest.mocked(liveMatchService.connect).mockReturnValue(ws as unknown as WebSocket);
  const navigation = { navigate: jest.fn(), replace: jest.fn() };
  const props = { route: { params: { id: 'match' } }, navigation } as unknown as NativeStackScreenProps<RootStackParamList, 'MatchLive'>;
  await render(<MatchLiveScreen {...props} />);
  await act(() => { ws.onopen?.(); ws.onmessage?.({ data: JSON.stringify({ type: 'sync', data: state() }) }); });
  expect(screen.getByText('Casa 1 × 0 Visitante')).toBeTruthy();
  await fireEvent.press(screen.getByText('Ir para o final'));
  expect(ws.send).toHaveBeenCalledTimes(1); // join only; shared human game cannot skip.
  await fireEvent.press(screen.getByText('Aplicar mudanças táticas'));
  expect(JSON.parse(ws.send.mock.calls.at(-1)![0])).toMatchObject({ type: 'combined_change', command_id: 'command-1', payload: { formation: '4-4-2', play_style: 'balanced' } });
  await fireEvent.press(screen.getByText(/João · ATT · Energia/));
  await fireEvent.press(screen.getByText(/Pedro · ATT · Energia/));
  await fireEvent.press(screen.getByText('Confirmar substituição'));
  expect(JSON.parse(ws.send.mock.calls.at(-1)![0])).toMatchObject({ type: 'substitution', payload: { out_player_id: 'out', in_player_id: 'in' } });
  await act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'match_event', data: state().events[0] }) }));
  expect(screen.getAllByText('31′ GOL! João finaliza.')).toHaveLength(2); // timeline and transient overlay; no duplicate timeline row.
  await act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'match_finished', data: { ...state(), status: 'finished', current_minute: 90 } }) }));
  expect(navigation.replace).toHaveBeenCalledWith('MatchReport', { id: 'match' });
});
test('shows rejected commands and server halftime, closes socket on leaving', async () => {
  const ws = socket(); jest.mocked(liveMatchService.connect).mockReturnValue(ws as unknown as WebSocket);
  const props = { route: { params: { id: 'match' } }, navigation: { navigate: jest.fn(), replace: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'MatchLive'>;
  const result = await render(<MatchLiveScreen {...props} />);
  await act(() => { ws.onopen?.(); ws.onmessage?.({ data: JSON.stringify({ type: 'halftime', data: { ...state(), status: 'halftime', current_minute: 45, paused: true } }) }); });
  await fireEvent.press(screen.getByText('Continuar'));
  expect(JSON.parse(ws.send.mock.calls.at(-1)![0]).type).toBe('resume');
  await act(() => ws.onmessage?.({ data: JSON.stringify({ type: 'command_rejected', data: { reason: 'Substituição inelegível.' } }) }));
  expect(screen.getByText('Substituição inelegível.')).toBeTruthy();
  await result.unmount(); expect(ws.close).toHaveBeenCalled();
});
