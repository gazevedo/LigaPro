import { fireEvent, render, screen } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ClubRankingScreen } from '../screens/ClubRankingScreen';
import { OtherClubScreen } from '../screens/OtherClubScreen';
import { RootStackParamList } from '../navigation/types';
jest.mock('../components/useScreenRefresh', () => ({ useScreenRefresh: jest.fn() }));
jest.mock('../stores/clubStore', () => ({ useClubStore: (select: (value: { data: { club: { id: string } } }) => unknown) => select({ data: { club: { id: 'own' } } }) }));
jest.mock('../stores/screenStores', () => ({
  useClubRankingStore: () => ({ ensure: jest.fn(), data: [{ id: 'rival', name: 'Rival', ranking_position: 1, ranking_points: 2000 }] }),
  useClubDetailsStore: () => ({ ensure: jest.fn(), data: { id: 'rival', name: 'Rival', country_id: 'BR', ranking_position: 1, ranking_points: 2000, reputation: 20 } }),
  useOtherClubSquadStore: () => ({ ensure: jest.fn(), data: [{ id: 'player', name: 'João', position: 'GK', age: 25, strength: 70, overall: 70, value: 10000, energy: 85, physical_condition: 90 }] }),
}));
test('general ranking opens the opponent club', async () => {
  const navigate = jest.fn();
  await render(<ClubRankingScreen {...{ navigation: { navigate } } as unknown as NativeStackScreenProps<RootStackParamList, 'ClubRanking'>} />);
  expect(screen.getByText('2000')).toBeTruthy();
  await fireEvent.press(screen.getByRole('button', { name: 'Abrir clube Rival' }));
  expect(navigate).toHaveBeenCalledWith('OtherClub', { id: 'rival' });
});
test('opponent roster displays position, fitness and opens player details', async () => {
  const navigate = jest.fn();
  await render(<OtherClubScreen {...{ navigation: { navigate }, route: { params: { id: 'rival' } } } as unknown as NativeStackScreenProps<RootStackParamList, 'OtherClub'>} />);
  expect(screen.getByText('GOL')).toBeTruthy();
  expect(screen.getByText('Energia: 85% · Condição: 90%')).toBeTruthy();
  await fireEvent.press(screen.getByRole('button', { name: 'Detalhes de João' }));
  expect(navigate).toHaveBeenCalledWith('PlayerDetails', { id: 'player' });
});
