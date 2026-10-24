import { useRef, useState } from 'react';
import { Text } from 'react-native';
import { ActionButton, Card, Field, GamePage, NotificationBubble, palette } from '../components/GameUI';
import { MatchNotifications } from '../components/MatchNotifications';
import { useAuthStore } from '../stores/authStore';
import { settingsService } from '../services/settingsService';
import { resetDomainStores } from '../stores/domainStore';
export function SettingsScreen() {
  const [confirming, setConfirming] = useState(false), [confirmation, setConfirmation] = useState('');
  const [resetting, setResetting] = useState(false), [error, setError] = useState('');
  const pending = useRef(false);
  async function reset() {
    if (pending.current || confirmation !== 'APAGAR TODOS OS DADOS') return;
    pending.current = true; setResetting(true); setError('');
    try {
      await settingsService.resetDatabase(confirmation);
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
      {resetting && <NotificationBubble tone="info" message="Reinicialização em andamento. Ao concluir, a sessão será encerrada para você testar um novo cadastro." />}
      {!confirming ? <ActionButton title="Zerar banco de dados" onPress={() => setConfirming(true)} /> : <>
        <NotificationBubble message="Isso apaga todos os usuários, clubes, partidas e históricos e recria a liga inicial com bots. Ao concluir, será necessário cadastrar uma nova conta." onClose={() => { if (!pending.current) setConfirming(false); }} />
        <Field label="Digite APAGAR TODOS OS DADOS" value={confirmation} onChange={setConfirmation} autoCapitalize="characters" autoCorrect={false} />
        <ActionButton title={resetting ? 'Reinicializando…' : 'Confirmar reinicialização'} disabled={confirmation !== 'APAGAR TODOS OS DADOS'} onPress={() => { void reset(); }} />
        {!resetting && <ActionButton secondary title="Cancelar" onPress={() => { setConfirming(false); setConfirmation(''); }} />}
      </>}
    </Card>
    <ActionButton title={loggingOut ? 'Saindo…' : 'Sair da conta'} disabled={loggingOut} onPress={() => { void logout(); }} />
  </GamePage>;
}
