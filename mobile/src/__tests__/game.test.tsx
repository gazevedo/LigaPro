import { ApiError, ApiTimeoutError } from '../services/apiClient';
import { act, render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Button } from 'react-native';
import { SquadScreen } from '../screens/SquadScreen';
import { useSquadStore } from '../stores/squadStore';
import { squadService } from '../services/squadService';
import { useAction } from '../components/GameUI';
import { CreateClubScreen } from '../screens/CreateClubScreen';
import { DashboardScreen } from '../screens/DashboardScreen';
import { ClubScreen } from '../screens/ClubScreen';
import { StadiumScreen } from '../screens/StadiumScreen';
import { TransferOffersScreen } from '../screens/TransferOffersScreen';
import { clubService } from '../services/clubService';
import { stadiumService } from '../services/stadiumService';
import { marketService } from '../services/marketService';
import { useClubStore } from '../stores/clubStore';
import { useStadiumStore } from '../stores/stadiumStore';
import { useMarketStore } from '../stores/marketStore';
import { useAuthStore } from '../stores/authStore';
import { domainStore, resetDomainStores } from '../stores/domainStore';
jest.mock('../services/historyService', () => ({ historyService: { get: jest.fn().mockResolvedValue({ seasons: [], clubs: [], records: [], players: [] }) } }));
jest.mock('../services/cupService', () => ({ cupService: { get: jest.fn().mockResolvedValue({ competition: null, entry: null, matches: [] }) } }));
jest.mock('../services/competitionService', () => ({ competitionService: { get: jest.fn().mockResolvedValue(null) } }));
jest.mock('../services/squadService', () => ({ squadService: { get: jest.fn(), save: jest.fn() } }));
jest.mock('../services/clubService', () => ({ clubService: { catalog: jest.fn(), status: jest.fn(), create: jest.fn(), get: jest.fn(), resign: jest.fn() } }));
jest.mock('../services/stadiumService', () => ({ stadiumService: { get: jest.fn(), upgrade: jest.fn() } }));
jest.mock('../services/marketService', () => ({ marketService: { mine: jest.fn(), accept: jest.fn(), cancelOffer: jest.fn() } }));
const club = { id: 'club1', name: 'Clube teste', country_id: 'BR', badge_id: 'blue', created_at: '2026-01-01T00:00:00Z', ranking: 0, competition_positions: [], trophies: [] };
beforeEach(() => {
  jest.clearAllMocks(); resetDomainStores(); useClubStore.getState().reset(); useStadiumStore.getState().reset(); useMarketStore.getState().reset();
  jest.mocked(clubService.status).mockResolvedValue({ club });
  jest.mocked(clubService.get).mockResolvedValue(club);
  jest.mocked(clubService.catalog).mockResolvedValue({ countries: [{ id: 'BR', name: 'Brasil' }], badges: [{ id: 'blue', name: 'blue', symbol: '🛡', color: '#2563eb' }] });
  jest.mocked(marketService.mine).mockResolvedValue({ listings: [], loans: [], incoming: [{ id: 'offer1', listing_id: 'listing1', buyer_club_id: 'club2', seller_club_id: club.id, amount: 10000, status: 'pending' }], outgoing: [] });
});
test('creates club from catalog and enters with the returned club', async () => {
  jest.mocked(clubService.create).mockResolvedValue(club);
  await render(<CreateClubScreen />); await screen.findByText('✓ Brasil');
  await fireEvent.changeText(screen.getByLabelText('Nome do clube'), 'Clube teste');
  await fireEvent.press(screen.getByText('Criar clube'));
  await waitFor(() => expect(clubService.create).toHaveBeenCalledWith({ name: 'Clube teste', country_id: 'BR', badge_id: 'blue' }));
  await waitFor(() => expect(useClubStore.getState().data?.club?.id).toBe('club1'));
});
test('dashboard opens every module', async () => {
  useClubStore.setState({ data: { club } });
  const navigate = jest.fn();
  const props = { navigation: { navigate } } as unknown as NativeStackScreenProps<RootStackParamList, 'Dashboard'>;
  await render(<DashboardScreen {...props} />);
  for (const title of ['Campeonatos', 'Clube', 'Plantel', 'Táticas', 'Estádio', 'Financeiro', 'Calendário', 'Mercado', 'Treinamento', 'Categorias de Base']) await fireEvent.press(screen.getByText(title));
  expect(navigate.mock.calls).toEqual([['Competitions'], ['Club', { id: club.id }], ['Squad'], ['Tactics'], ['Stadium'], ['Finance'], ['Calendar'], ['Market'], ['Training'], ['YouthAcademy']]);
});
test('public club hides administration for a different owner', async () => {
  useClubStore.setState({ data: { club: { ...club, id: 'other' } } });
  const props = { route: { params: { id: club.id } }, navigation: { setParams: jest.fn(), setOptions: jest.fn(), navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'Club'>;
  await render(<ClubScreen {...props} />); await screen.findByText('Clube teste');
  expect(screen.queryByText('Administrar plantel')).toBeNull();
  expect(screen.queryByText('Pedir demissão')).toBeNull();
  expect(screen.queryByText(/Saldo/)).toBeNull();
});
test('stadium reports insufficient balance without optimistic upgrade', async () => {
  jest.mocked(stadiumService.get).mockResolvedValue({ capacity: 10000, ticket_price: 2000, facilities: { stands: 1 }, names: { stands: 'Arquibancadas' }, upgrade_costs: { stands: 100000 } });
  jest.mocked(stadiumService.upgrade).mockRejectedValue(new Error('Saldo insuficiente.'));
  await render(<StadiumScreen />); const button = await screen.findByRole('button', { name: /Melhorar Arquibancadas/ });
  await fireEvent.press(button); await screen.findByText('Saldo insuficiente.');
  expect(screen.getByText('Arquibancadas · nível 1')).toBeTruthy();
});
test('accepts incoming offer and reloads negotiations', async () => {
  await render(<TransferOffersScreen />); await screen.findByText('Aceitar proposta');
  await fireEvent.press(screen.getByText('Aceitar proposta'));
  await waitFor(() => expect(marketService.accept).toHaveBeenCalledWith('offer1'));
  await waitFor(() => expect(marketService.mine).toHaveBeenCalledTimes(2));
});
test('late response cannot restore private club state after account change', async () => {
  let resolve!: (value: string) => void;
  const store = domainStore(() => new Promise<string>(done => { resolve = done; }));
  const request = store.getState().load();
  await act(async () => { useAuthStore.setState({ user: null }); store.getState().reset(); resolve('private data'); await request; });
  expect(store.getState().data).toBeNull();
  expect(store.getState().loading).toBe(false);
});

test('squad refresh discards starters removed by a transfer', async () => {
  const players = Array.from({ length: 12 }, (_, i) => ({ id: String(i), name: `Player ${i}`, position: 'DEF', age: 21, overall: 50, value: 1000, country_id: 'BR', owner_club_id: 'club1', current_club_id: 'club1' }));
  const starters = players.slice(0, 11).map(p => p.id);
  jest.mocked(squadService.get).mockResolvedValueOnce({ players, lineup: { formation: '4-4-2', starters, reserves: ['11'] }, formations: { '4-4-2': { DEF: 4, MED: 4, ATA: 2 } } });
  jest.mocked(squadService.get).mockResolvedValueOnce({ players: players.slice(1), lineup: { formation: '4-4-2', starters: [...starters.slice(1), '11'], reserves: [] }, formations: { '4-4-2': { DEF: 4, MED: 4, ATA: 2 } } });
  useSquadStore.getState().reset();
  const props = { navigation: { navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'Squad'>;
  await render(<SquadScreen {...props} />);
  await screen.findByText('Player 0');
  expect(screen.queryByText('Atualizar plantel')).toBeNull();
  await act(async () => { await useSquadStore.getState().load(); });
  await waitFor(() => expect(screen.queryByText('Player 0')).toBeNull());
  expect(screen.getByText('Player 11')).toBeTruthy();
  expect(screen.queryByText('Salvar escalação')).toBeNull();
});
test('synchronous double tap runs one financial action', async () => {
  let complete!: () => void;
  const operation = jest.fn(() => new Promise<void>(resolve => { complete = resolve; }));
  function Control() { const action = useAction(); return <Button title="Executar" onPress={() => { void action.run(operation); void action.run(operation); }} />; }
  await render(<Control />); await fireEvent.press(screen.getByText('Executar'));
  expect(operation).toHaveBeenCalledTimes(1);
  await act(async () => { complete(); });
});

test('club hides consultation and management shortcuts', async () => {
  useClubStore.setState({ data: { club } });
  const props = { route: { params: { id: club.id } }, navigation: { setParams: jest.fn(), setOptions: jest.fn(), navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'Club'>;
  await render(<ClubScreen {...props} />);
  await screen.findByText(club.name);
  expect(screen.queryByText('Gestão do clube')).toBeNull();
  expect(screen.queryByText('Administrar plantel')).toBeNull();
  expect(screen.queryByText('Consultar outro clube')).toBeNull();
  expect(screen.queryByText('MEU CLUBE')).toBeNull();
  expect(screen.queryByText('Perfil do técnico')).toBeNull();
  expect(screen.getByLabelText('País: BR')).toHaveTextContent('🇧🇷');
  expect(props.navigation.setOptions).toHaveBeenCalledWith({ title: 'Meu clube' });
  expect(screen.getByRole('tab', { name: 'Informações', selected: true })).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Logout' })).toBeTruthy();
  expect(screen.getByRole('button', { name: 'Pedir demissão' })).toBeTruthy();
  await fireEvent.press(screen.getByRole('tab', { name: 'Sala de troféus' }));
  expect(screen.queryByText('Records do clube')).toBeNull();
  expect(screen.getByText('As próximas conquistas começam aqui.')).toBeTruthy();
  expect(screen.queryByRole('button', { name: 'Sair' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Logout' })).toBeNull();
  expect(screen.queryByRole('button', { name: 'Pedir demissão' })).toBeNull();
});

test('country picker searches without accents and selects the result', async () => {
  jest.mocked(clubService.catalog).mockResolvedValue({ countries: [{ id: 'BR', name: 'Brasil' }, { id: 'JP', name: 'Japão' }], badges: [{ id: 'blue', name: 'Azul', symbol: '🛡', color: '#2563eb' }] });
  jest.mocked(clubService.create).mockResolvedValue(club);
  await render(<CreateClubScreen />); await screen.findByText('✓ Brasil');
  await fireEvent.press(screen.getByText('✓ Brasil'));
  await fireEvent.changeText(screen.getByLabelText('Buscar país'), 'japao');
  await fireEvent.press(screen.getByText('Japão'));
  await fireEvent.changeText(screen.getByLabelText('Nome do clube'), 'Clube japonês');
  await fireEvent.press(screen.getByText('Criar clube'));
  expect(clubService.create).toHaveBeenCalledWith({ name: 'Clube japonês', country_id: 'JP', badge_id: 'blue' });
  expect(screen.queryByText('Voltar')).toBeNull();
});

test.each([new ApiTimeoutError(), new ApiError(401, 'Sessão expirada')])('failed creation returns to login without checking or creating again (%s)', async error => {
  useAuthStore.setState({ authenticated: true });
  jest.mocked(clubService.create).mockRejectedValueOnce(error);
  await render(<CreateClubScreen />); await screen.findByText('✓ Brasil');
  await fireEvent.changeText(screen.getByLabelText('Nome do clube'), 'Clube teste');
  await fireEvent.press(screen.getByText('Criar clube'));
  await waitFor(() => expect(useAuthStore.getState().authenticated).toBe(false));
  expect(clubService.create).toHaveBeenCalledTimes(1);
  expect(clubService.status).not.toHaveBeenCalled();
  expect(useClubStore.getState().data?.club).toBeFalsy();
  expect(screen.queryByText('Verificar criação')).toBeNull();
});

test('opening the initial form never creates a club', async () => {
  await render(<CreateClubScreen />); await screen.findByText('✓ Brasil');
  expect(clubService.create).not.toHaveBeenCalled();
});

test('a successful response after session expiry does not enter the game', async () => {
  useAuthStore.setState({ authenticated: true });
  let finish!: (value: typeof club) => void;
  jest.mocked(clubService.create).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  await render(<CreateClubScreen />); await screen.findByText('✓ Brasil');
  await fireEvent.changeText(screen.getByLabelText('Nome do clube'), 'Clube teste');
  await fireEvent.press(screen.getByText('Criar clube'));
  await act(async () => { await useAuthStore.getState().clearSession(); finish(club); });
  expect(useClubStore.getState().data?.club).toBeFalsy();
  expect(useAuthStore.getState().authenticated).toBe(false);
});

test('stadium upgrade refreshes capacity and facilities automatically', async () => {
  const before = { capacity: 10000, ticket_price: 2000, facilities: { stands: 1 }, names: { stands: 'Arquibancadas' }, upgrade_costs: { stands: 100000 } };
  jest.mocked(stadiumService.get).mockResolvedValueOnce(before).mockResolvedValueOnce({ ...before, capacity: 15000, facilities: { stands: 2 } });
  jest.mocked(stadiumService.upgrade).mockResolvedValue({ ...before, capacity: 15000 });
  await render(<StadiumScreen />);
  await fireEvent.press(await screen.findByRole('button', { name: /Melhorar Arquibancadas/ }));
  await screen.findByText('Arquibancadas · nível 2');
  expect(screen.queryByText('Atualizar estádio')).toBeNull();
  expect(stadiumService.get).toHaveBeenCalledTimes(2);
});

test('resignation asks for confirmation and cancelling preserves the club', async () => {
  useClubStore.setState({ data: { club } });
  const props = { route: { params: { id: club.id } }, navigation: { setOptions: jest.fn(), navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'Club'>;
  await render(<ClubScreen {...props} />);
  await fireEvent.press(await screen.findByRole('button', { name: 'Pedir demissão' }));
  expect(screen.getByText(/seus jogadores e seu histórico serão preservados/)).toBeTruthy();
  expect(clubService.resign).not.toHaveBeenCalled();
  await fireEvent.press(screen.getByRole('button', { name: 'Não' }));
  expect(useClubStore.getState().data?.club?.id).toBe(club.id);
  expect(clubService.resign).not.toHaveBeenCalled();
});

test('confirmed resignation clears club data but keeps authentication and never auto-creates a club', async () => {
  useAuthStore.setState({ authenticated: true });
  useClubStore.setState({ data: { club } });
  jest.mocked(clubService.resign).mockResolvedValue({ club: null });
  const props = { route: { params: { id: club.id } }, navigation: { setOptions: jest.fn(), navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'Club'>;
  await render(<ClubScreen {...props} />);
  await fireEvent.press(await screen.findByRole('button', { name: 'Pedir demissão' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Sim' }));
  await waitFor(() => expect(useClubStore.getState().data).toEqual({ club: null }));
  expect(useAuthStore.getState().authenticated).toBe(true);
  expect(clubService.resign).toHaveBeenCalledWith(club.id);
  expect(clubService.create).not.toHaveBeenCalled();
});

test('rejected resignation keeps the current club and displays the reason', async () => {
  useClubStore.setState({ data: { club } });
  jest.mocked(clubService.resign).mockRejectedValueOnce(new Error('Aguarde o fim da partida para pedir demissão.'));
  const props = { route: { params: { id: club.id } }, navigation: { setOptions: jest.fn(), navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'Club'>;
  await render(<ClubScreen {...props} />);
  await fireEvent.press(await screen.findByRole('button', { name: 'Pedir demissão' }));
  await fireEvent.press(screen.getByRole('button', { name: 'Sim' }));
  await screen.findByText('Aguarde o fim da partida para pedir demissão.');
  expect(useClubStore.getState().data?.club?.id).toBe(club.id);
});
