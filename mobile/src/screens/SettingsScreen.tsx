import { Text } from 'react-native';
import { ActionButton, Card, GamePage, palette } from '../components/GameUI';
import { MatchNotifications } from '../components/MatchNotifications';
import { useAuthStore } from '../stores/authStore';
export function SettingsScreen() {
  const logout = useAuthStore(state => state.logout);
  const loggingOut = useAuthStore(state => state.loading);
  return <GamePage><Card>
    <Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Notificações de partidas</Text>
    <MatchNotifications />
  </Card>
    <ActionButton title={loggingOut ? 'Saindo…' : 'Sair da conta'} disabled={loggingOut} onPress={() => { void logout(); }} />
  </GamePage>;
}
