import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { SettingsScreen } from '../screens/SettingsScreen';
import { useAuthStore } from '../stores/authStore';
import { settingsService } from '../services/settingsService';
jest.mock('../services/settingsService', () => ({ settingsService: { resetCapability: jest.fn(), resetDatabase: jest.fn() } }));
beforeEach(() => { jest.clearAllMocks(); jest.mocked(settingsService.resetCapability).mockResolvedValue({ allowed: false }); });

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

test('database reset requires typed confirmation and clears the session after success', async () => {
  jest.mocked(settingsService.resetCapability).mockResolvedValue({ allowed: true });
  jest.mocked(settingsService.resetDatabase).mockResolvedValue({ status: 'ready' });
  const previous = useAuthStore.getState().clearSession;
  const clearSession = jest.fn(async () => undefined);
  useAuthStore.setState({ clearSession });
  try {
    await render(<SettingsScreen />);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Zerar banco de dados' }).props.accessibilityState.disabled).toBe(false));
    await fireEvent.press(screen.getByRole('button', { name: 'Zerar banco de dados' }));
    await fireEvent.press(screen.getByRole('button', { name: 'Confirmar reinicialização' }));
    expect(settingsService.resetDatabase).not.toHaveBeenCalled();
    await fireEvent.changeText(screen.getByLabelText('Digite APAGAR TODOS OS DADOS'), 'APAGAR TODOS OS DADOS');
    await fireEvent.press(screen.getByRole('button', { name: 'Confirmar reinicialização' }));
    await waitFor(() => expect(clearSession).toHaveBeenCalledTimes(1));
    expect(settingsService.resetDatabase).toHaveBeenCalledWith('APAGAR TODOS OS DADOS');
  } finally { useAuthStore.setState({ clearSession: previous }); }
});

test('database reset is unavailable to a regular player', async () => {
  await render(<SettingsScreen />);
  await screen.findByText('Esta ação está disponível somente para o administrador autorizado.');
  await fireEvent.press(screen.getByRole('button', { name: 'Zerar banco de dados' }));
  expect(screen.queryByLabelText('Digite APAGAR TODOS OS DADOS')).toBeNull();
  expect(settingsService.resetDatabase).not.toHaveBeenCalled();
});
