import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { HomeScreen } from '../screens/HomeScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { useAuthStore } from '../stores/authStore';
import { settingsService } from '../services/settingsService';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
jest.mock('../services/settingsService', () => ({ settingsService: { list: jest.fn() } }));
const list = jest.mocked(settingsService.list);
beforeEach(() => jest.clearAllMocks());
test('home navigates only to settings; game buttons disabled', async () => {
  const navigate = jest.fn();
  const props = { navigation: { navigate }, route: { key: 'Home', name: 'Home' } } as unknown as NativeStackScreenProps<RootStackParamList, 'Home'>;
  await render(<HomeScreen {...props} />);
  expect(screen.getByRole('button', { name: 'Novo Jogo' })).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Carregar Jogo' })).toBeDisabled();
  await fireEvent.press(screen.getByText('Configurações'));
  expect(navigate).toHaveBeenCalledWith('Settings');
});
test('settings displays API values', async () => {
  list.mockResolvedValueOnce([{ id: '123', key: 'language', value: 'pt-BR',
    created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }]);
  await render(<SettingsScreen />);
  expect(await screen.findByText('language: "pt-BR"')).toBeTruthy();
});
test('settings shows empty state', async () => {
  list.mockResolvedValueOnce([]);
  await render(<SettingsScreen />);
  expect(await screen.findByText('Nenhuma configuração cadastrada.')).toBeTruthy();
});
test('settings retries after error', async () => {
  list.mockRejectedValueOnce(new Error('Offline')).mockResolvedValueOnce([]);
  await render(<SettingsScreen />);
  await screen.findByText('Offline');
  await fireEvent.press(screen.getByText('Tentar novamente'));
  await waitFor(() => expect(list).toHaveBeenCalledTimes(2));
  expect(await screen.findByText('Nenhuma configuração cadastrada.')).toBeTruthy();
});

test('settings logs out using the existing session handler', async () => {
  const previous = useAuthStore.getState().logout;
  const logout = jest.fn(async () => undefined);
  useAuthStore.setState({ logout, loading: false });
  list.mockResolvedValueOnce([]);
  try {
    await render(<SettingsScreen />);
    await screen.findByText('Nenhuma configuração cadastrada.');
    await fireEvent.press(screen.getByRole('button', { name: 'Sair da conta' }));
    expect(logout).toHaveBeenCalledTimes(1);
  } finally { useAuthStore.setState({ logout: previous }); }
});
