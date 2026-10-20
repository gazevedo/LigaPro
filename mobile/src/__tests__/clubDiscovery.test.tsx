import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { ClubRankingScreen } from '../screens/ClubRankingScreen';
import { OtherClubScreen } from '../screens/OtherClubScreen';
import { RootStackParamList } from '../navigation/types';
import { clubService } from '../services/clubService';
import { useClubRankingStore } from '../stores/screenStores';
jest.mock('../services/clubService', () => ({ clubService: { ...jest.requireActual('../services/clubService').clubService, ranking: jest.fn() } }));
jest.mock('../stores/clubStore', () => ({ useClubStore: (select: (value: { data: { club: { id: string } } }) => unknown) => select({ data: { club: { id: 'own' } } }) }));
jest.mock('../stores/screenStores', () => ({
  useClubRankingStore: jest.requireActual('../stores/screenStores').useClubRankingStore,
  useClubDetailsStore: () => ({ ensure: jest.fn(), data: { id: 'rival', name: 'Rival', country_id: 'BR', ranking_position: 1, ranking_points: 2000, reputation: 20 } }),
  useOtherClubSquadStore: () => ({ ensure: jest.fn(), data: [{ id: 'player', name: 'João', position: 'GK', age: 25, strength: 70, overall: 70, value: 10000, energy: 85, physical_condition: 90 }] }),
}));
beforeEach(() => {
  jest.clearAllMocks();
  useClubRankingStore.getState().reset();
  jest.mocked(clubService.ranking).mockResolvedValue({ items: [{ id: 'rival', name: 'Rival', ranking_position: 1, ranking_points: 2000 }], page: 1, page_size: 20, total: 1, pages: 1 });
});
test('general ranking opens the opponent club', async () => {
  const navigate = jest.fn();
  await render(<ClubRankingScreen {...{ navigation: { navigate } } as unknown as NativeStackScreenProps<RootStackParamList, 'ClubRanking'>} />);
  expect(await screen.findByText('2000')).toBeTruthy();
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

test('ranking arrows load pages and stop at the first and last page', async () => {
  jest.mocked(clubService.ranking).mockImplementation(async (page = 1) => ({
    items: [{ id: `club-${page}`, name: `Clube ${page}`, ranking_position: page, ranking_points: 2000 - page }],
    page, page_size: 20, total: 21, pages: 2,
  }));
  const props = { navigation: { navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'ClubRanking'>;
  await render(<ClubRankingScreen {...props} />);
  await screen.findByText('Página 1 de 2');
  expect(screen.getByRole('button', { name: 'Página anterior do ranking' })).toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: 'Próxima página do ranking' }));
  await screen.findByText('Clube 2');
  expect(clubService.ranking).toHaveBeenCalledWith(2);
  expect(screen.queryByText('Clube 1')).toBeNull();
  expect(screen.getByRole('button', { name: 'Próxima página do ranking' })).toBeDisabled();
  await fireEvent.press(screen.getByRole('button', { name: 'Página anterior do ranking' }));
  await waitFor(() => expect(screen.getByText('Clube 1')).toBeTruthy());
  expect(screen.getByText('Página 1 de 2')).toBeTruthy();
});
