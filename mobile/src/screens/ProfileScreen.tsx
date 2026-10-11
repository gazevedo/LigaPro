import { ActionButton as Button, GamePage, palette } from '../components/GameUI';
import { Text } from 'react-native';
import { useAuthStore } from '../stores/authStore';
export function ProfileScreen() {
  const { user, loading, logout } = useAuthStore();
  return <GamePage>
    <Text style={{ color: palette.ink, fontSize: 18, fontWeight: '700' }}>{user?.name}</Text><Text style={{ color: palette.muted }}>{user?.email}</Text>
    <Button title="Sair" disabled={loading} onPress={() => { void logout(); }} />
  </GamePage>;
}
