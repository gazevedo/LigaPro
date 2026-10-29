import { render, screen, fireEvent } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { CompetitionsScreen } from '../screens/CompetitionsScreen';
import { RootStackParamList } from '../navigation/types';
let mockStatus = 'scheduled';
jest.mock('../components/useScreenRefresh', () => ({ useScreenRefresh: jest.fn() }));
jest.mock('../stores/screenStores', () => ({
  useCompetitionStore: () => ({ data: null }),
  useCompetitionMatchesStore: () => ({ data: [{ id: 'match', date: new Date().toISOString(), round: 1, status: mockStatus, home_name: 'Casa', away_name: 'Visitante' }] }),
  useCupStore: () => ({ data: null }),
}));
test.each(['scheduled', 'pending', 'cancelled', 'completed', 'live', 'in_progress'])('match action is available only while playing (%s)', async status => {
  mockStatus = status;
  const navigate = jest.fn();
  await render(<CompetitionsScreen {...{ navigation: { navigate } } as unknown as NativeStackScreenProps<RootStackParamList, 'Competitions'>} />);
  await fireEvent.press(screen.getByRole('tab', { name: 'Partidas' }));
  expect(screen.queryByRole('button', { name: 'Acompanhar' })).toBeNull();
  if (['live', 'in_progress'].includes(status)) {
    await fireEvent.press(screen.getByRole('button', { name: 'Assistir' }));
    expect(navigate).toHaveBeenCalledWith('MatchLive', { id: 'match' });
  } else {
    expect(screen.queryByRole('button', { name: 'Assistir' })).toBeNull();
    expect(navigate).not.toHaveBeenCalled();
  }
  if (status === 'completed') expect(screen.getByRole('button', { name: 'Ver relatório' })).toBeTruthy();
});
