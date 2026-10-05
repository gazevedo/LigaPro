import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { StatisticsScreen } from '../screens/StatisticsScreen';
import { MatchReportScreen } from '../screens/MatchReportScreen';
import { statisticsService } from '../services/statisticsService';
jest.mock('../services/statisticsService', () => ({ statisticsService: { get: jest.fn(), report: jest.fn() } }));
const stats = { season: { id: 'season2', number: 2 }, seasons: [{ id: 'season2', number: 2 }, { id: 'season1', number: 1 }], ranking: 'goals' as const, rows: [{ player_id: 'p1', name: 'Pedro', position: 'ATT', total: 3, matches: 2, minutes: 150, goals: 3, yellow_cards: 1, red_cards: 0 }], recent_matches: [{ id: 'm1', round: 1, date: '2026-01-01T12:00:00Z', home_goals: 3, away_goals: 1 }] };
beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(statisticsService.get).mockResolvedValue(stats);
  jest.mocked(statisticsService.report).mockResolvedValue({ match: { id: 'm1', round: 1, date: '2026-01-01T12:00:00Z', home_club_id: 'home', away_club_id: 'away', home_goals: 3, away_goals: 1 }, home_name: 'Clube da casa', away_name: 'Visitante', ratings: [{ id: 'r1', player_id: 'p1', club_id: 'home', name: 'Pedro', position: 'ATT', rating: 8.4, minutes: 60, events_summary: { goals: 2, yellow_cards: 1, red_cards: 0, saves: 0 } }, { id: 'r2', player_id: 'p2', club_id: 'away', name: 'Lucas', position: 'GK', rating: 8.1, minutes: 90, events_summary: { goals: 0, saves: 12 } }] });
});
test('switches rankings and seasons, then opens a match report', async () => {
  const navigate = jest.fn();
  const props = { navigation: { navigate } } as unknown as NativeStackScreenProps<RootStackParamList, 'Statistics'>;
  await render(<StatisticsScreen {...props} />);
  await screen.findByText('1. Pedro · ATT · 3 gols · 150 min');
  await fireEvent.press(screen.getByText('Mais cartões'));
  await waitFor(() => expect(statisticsService.get).toHaveBeenLastCalledWith('cards', undefined));
  await fireEvent.press(screen.getByText('Temporada 1'));
  await waitFor(() => expect(statisticsService.get).toHaveBeenLastCalledWith('cards', 'season1'));
  await fireEvent.press(screen.getByText('Rodada 1 · 3 × 1'));
  expect(navigate).toHaveBeenCalledWith('MatchReport', { id: 'm1' });
});
test('match report displays notes and minutes for both teams', async () => {
  const props = { route: { params: { id: 'm1' } } } as unknown as NativeStackScreenProps<RootStackParamList, 'MatchReport'>;
  await render(<MatchReportScreen {...props} />);
  await screen.findByText('Pedro · ATT · nota 8,4 · 60 min');
  expect(screen.getByText('Lucas · GK · nota 8,1 · 90 min')).toBeTruthy();
  expect(screen.getByText('Gols: 2 · Amarelos: 1 · Vermelhos: 0 · Defesas: 0')).toBeTruthy();
});
test('report shows permission rejection and permits retry', async () => {
  jest.mocked(statisticsService.report).mockRejectedValueOnce(new Error('Partida de outro clube.'));
  const props = { route: { params: { id: 'm1' } } } as unknown as NativeStackScreenProps<RootStackParamList, 'MatchReport'>;
  await render(<MatchReportScreen {...props} />);
  await screen.findByText('Partida de outro clube.');
  await fireEvent.press(screen.getByText('Atualizar relatório'));
  await screen.findByText('Pedro · ATT · nota 8,4 · 60 min');
});
