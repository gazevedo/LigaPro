import { fireEvent, render, screen } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { CalendarScreen } from '../screens/CalendarScreen';
import { RootStackParamList } from '../navigation/types';
jest.mock('../components/useScreenRefresh', () => ({ useScreenRefresh: jest.fn() }));
jest.mock('../stores/calendarStore', () => ({ useCalendarStore: () => ({ data: [
  { id: 'event1', reference_id: 'match1', title: 'Rodada 1', date: new Date().toISOString(), type: 'match', status: 'completed', home_goals: 2, away_goals: 1 },
  { id: 'event2', reference_id: 'match2', title: 'Rodada 2', date: new Date().toISOString(), type: 'match', status: 'live' },
  { id: 'event3', reference_id: 'match3', title: 'Rodada 3', date: new Date().toISOString(), type: 'match', status: 'scheduled' },
], ensure: jest.fn(), refresh: jest.fn() }) }));
test('calendar distinguishes completed, live and scheduled matches and opens the right screen', async () => {
  const navigate = jest.fn();
  await render(<CalendarScreen {...{ navigation: { navigate } } as unknown as NativeStackScreenProps<RootStackParamList, 'Calendar'>} />);
  expect(screen.getByText('Concluída · 2 × 1')).toBeTruthy();
  expect(screen.getByText('Em andamento')).toBeTruthy();
  expect(screen.getByText('Agendada')).toBeTruthy();
  await fireEvent.press(screen.getByText('Ver relatório'));
  expect(navigate).toHaveBeenCalledWith('MatchReport', { id: 'match1' });
  await fireEvent.press(screen.getByText('Assistir'));
  expect(navigate).toHaveBeenCalledWith('MatchLive', { id: 'match2' });
});
