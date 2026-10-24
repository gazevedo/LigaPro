import { useRef, useState } from 'react';
import { Text } from 'react-native';
import { ActionButton, Card, GamePage, NotificationBubble, palette } from '../components/GameUI';
import { MatchNotifications } from '../components/MatchNotifications';
import { useAuthStore } from '../stores/authStore';
import { settingsService } from '../services/settingsService';
import { resetDomainStores } from '../stores/domainStore';
export function SettingsScreen() {
  const [resetting, setResetting] = useState(false), [error, setError] = useState('');
  const pending = useRef(false);
  async function reset() {
    if (pending.current) return;
    pending.current = true; setResetting(true); setError('');
    try {
      await settingsService.resetDatabase();
      resetDomainStores();
      await useAuthStore.getState().clearSession();
    } catch (reason) { setError(`Não foi possível confirmar a reinicialização. ${reason instanceof Error ? reason.message : 'Verifique a sessão antes de tentar novamente.'}`); }
    finally { pending.current = false; setResetting(false); }
  }
  const logout = useAuthStore(state => state.logout);
  const loggingOut = useAuthStore(state => state.loading);
  return <GamePage><Card>
    <Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Notificações de partidas</Text>
    <MatchNotifications />
  </Card>
    <Card>
      <Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Reiniciar universo do jogo</Text>
      <NotificationBubble message={error} onClose={() => setError('')} />
      <ActionButton title={resetting ? 'Reinicializando…' : 'Zerar banco de dados'} onPress={() => { void reset(); }} />
    </Card>
    <ActionButton title={loggingOut ? 'Saindo…' : 'Sair da conta'} disabled={loggingOut} onPress={() => { void logout(); }} />
  </GamePage>;
}
