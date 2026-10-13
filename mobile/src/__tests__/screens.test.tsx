import { render, fireEvent, screen } from '@testing-library/react-native';
import { SettingsScreen } from '../screens/SettingsScreen';
import { useAuthStore } from '../stores/authStore';

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
