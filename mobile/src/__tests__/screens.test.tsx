import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { SettingsScreen } from '../screens/SettingsScreen';
import { useAuthStore } from '../stores/authStore';
import { settingsService } from '../services/settingsService';
jest.mock('../services/settingsService', () => ({ settingsService: { resetDatabase: jest.fn() } }));
beforeEach(() => { jest.clearAllMocks(); });

jest.mock('../components/MatchNotifications', () => ({ MatchNotifications: () => {
  const { Text } = jest.requireActual('react-native');
  return <Text>Ativar avisos de partidas</Text>;
} }));

test('notification preferences are inside settings', async () => {
  await render(<SettingsScreen />);
  expect(screen.getByText('Notificações de partidas')).toBeTruthy();
  expect(screen.getByText('Ativar avisos de partidas')).toBeTruthy();
});

test('settings logs out using the existing session handler', async () => {
  const previous = useAuthStore.getState().logout;
  const logout = jest.fn(async () => undefined);
  useAuthStore.setState({ logout, loading: false });
  try {
    await render(<SettingsScreen />);
    await fireEvent.press(screen.getByRole('button', { name: 'Sair da conta' }));
    expect(logout).toHaveBeenCalledTimes(1);
  } finally { useAuthStore.setState({ logout: previous }); }
});

test('one press resets the database and clears the session after success', async () => {
  jest.mocked(settingsService.resetDatabase).mockResolvedValue({ status: 'ready' });
  const previous = useAuthStore.getState().clearSession;
  const clearSession = jest.fn(async () => undefined);
  useAuthStore.setState({ clearSession });
  try {
    await render(<SettingsScreen />);
    await fireEvent.press(screen.getByRole('button', { name: 'Zerar banco de dados' }));
    await waitFor(() => expect(clearSession).toHaveBeenCalledTimes(1));
    expect(settingsService.resetDatabase).toHaveBeenCalledTimes(1);
    expect(settingsService.resetDatabase).toHaveBeenCalledWith();
  } finally { useAuthStore.setState({ clearSession: previous }); }
});
