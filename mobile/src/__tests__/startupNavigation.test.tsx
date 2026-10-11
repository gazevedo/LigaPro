import { act, render, screen } from '@testing-library/react-native';
import { AppNavigator } from '../navigation/AppNavigator';
import { useAppStore } from '../stores/appStore';
import { useAuthStore } from '../stores/authStore';
import { useClubStore } from '../stores/clubStore';

jest.mock('react-native-safe-area-context', () => jest.requireActual('react-native-safe-area-context/jest/mock').default);
jest.mock('@react-navigation/native', () => {
  const ref = { isReady: () => false, canGoBack: () => false, goBack: jest.fn() };
  return {
    DefaultTheme: { colors: {} },
    useNavigationContainerRef: () => ref,
    NavigationContainer: ({ children }: any) => children,
  };
});
jest.mock('@react-navigation/native-stack', () => ({
  createNativeStackNavigator: () => ({
    Navigator: ({ children }: any) => children[0],
    Screen: ({ component: Component }: any) => <Component />,
  }),
}));
jest.mock('../navigation/AuthNavigator', () => ({ AuthNavigator: () => {
  const { Text } = jest.requireActual('react-native');
  return <Text>Login</Text>;
} }));
jest.mock('../screens/DashboardScreen', () => ({ DashboardScreen: () => {
  const { Text } = jest.requireActual('react-native');
  return <Text>Tela inicial</Text>;
} }));
jest.mock('../screens/CreateClubScreen', () => ({ CreateClubScreen: () => {
  const { Text } = jest.requireActual('react-native');
  return <Text>Criar clube</Text>;
} }));
jest.mock('../components/SwipeBack', () => ({ SwipeBack: ({ children }: any) => children }));
jest.mock('../components/NotificationHost', () => ({ NotificationHost: () => null }));
jest.mock('../services/prefetchService', () => ({ prefetchGameData: jest.fn() }));

const load = jest.fn(async () => undefined);
beforeEach(() => {
  jest.clearAllMocks();
  useAppStore.setState({ initialized: true, loading: false, apiAvailable: true, error: null,
    initialize: jest.fn(async () => undefined) });
  useAuthStore.setState({ initialized: true, authenticated: false, user: null, loading: false,
    error: null, restoreSession: jest.fn(async () => undefined) });
  useClubStore.setState({ data: null, loading: false, error: null, load, ensure: load });
});

test('startup opens login directly when there is no session', async () => {
  await render(<AppNavigator />);
  expect(screen.getByText('Login')).toBeTruthy();
  expect(screen.queryByText('Tentar novamente')).toBeNull();
  expect(load).not.toHaveBeenCalled();
});

test('restored session opens home while club data loads in the background', async () => {
  useAuthStore.setState({ authenticated: true, user: { id: 'user1' } as any });
  await render(<AppNavigator />);
  expect(screen.queryByLabelText('Carregando aplicativo')).toBeNull();
  expect(screen.getByText('Tela inicial')).toBeTruthy();
  expect(screen.queryByLabelText('Logotipo LigaPro')).toBeNull();
  expect(screen.queryByText('Tentar novamente')).toBeNull();
  expect(screen.queryByText('Sair')).toBeNull();
  expect(screen.queryByText('Criar clube')).toBeNull();
  expect(load).toHaveBeenCalledTimes(1);
  await act(async () => { useClubStore.setState({ data: { club: { id: 'club1' } as any } }); });
  expect(screen.getByText('Tela inicial')).toBeTruthy();
  expect(screen.queryByLabelText('Carregando aplicativo')).toBeNull();
});

test('club loading failure retries without a splash logo or the intermediate screen', async () => {
  jest.useFakeTimers();
  try {
    useAuthStore.setState({ authenticated: true });
    useClubStore.setState({ error: 'Sem conexão' });
    await render(<AppNavigator />);
    expect(screen.getByText('Sem conexão')).toBeTruthy();
    expect(screen.queryByText('Tentar novamente')).toBeNull();
    expect(screen.queryByText('Sair')).toBeNull();
    await act(async () => { jest.advanceTimersByTime(5000); });
    expect(load).toHaveBeenCalledTimes(1);
  } finally { jest.useRealTimers(); }
});

test('club creation opens only after confirming the account has no club', async () => {
  useAuthStore.setState({ authenticated: true });
  useClubStore.setState({ data: { club: null } });
  await render(<AppNavigator />);
  expect(screen.getByText('Criar clube')).toBeTruthy();
});

test('session expiry during club loading opens login', async () => {
  useAuthStore.setState({ authenticated: true });
  await render(<AppNavigator />);
  expect(screen.queryByLabelText('Carregando aplicativo')).toBeNull();
  expect(screen.getByText('Tela inicial')).toBeTruthy();
  expect(screen.queryByLabelText('Logotipo LigaPro')).toBeNull();
  await act(async () => { useAuthStore.setState({ authenticated: false }); });
  expect(screen.getByText('Login')).toBeTruthy();
  expect(screen.queryByText('Sair')).toBeNull();
});

test('login is visible while startup checks and session restoration are pending', async () => {
  useAppStore.setState({ initialized: false, loading: true, apiAvailable: false });
  useAuthStore.setState({ initialized: false, loading: true });
  await render(<AppNavigator />);
  expect(screen.getByText('Login')).toBeTruthy();
  expect(screen.queryByLabelText('Carregando aplicativo')).toBeNull();
});
