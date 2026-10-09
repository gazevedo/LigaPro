import { ClubHistory } from './HistoryScreen';
import { ScreenTabs } from '../components/ScreenTabs';
import { useAuthStore } from '../stores/authStore';
import { ClubBadge } from '../components/ClubBadge';
import { useEffect, useState } from 'react';
import { Modal, StyleSheet, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useClubDetailsStore } from '../stores/screenStores';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { useClubStore } from '../stores/clubStore';
import { ActionButton, Card, GamePage, NotificationBubble, palette, useAction } from '../components/GameUI';
import { clubService } from '../services/clubService';
import { resetDomainStores } from '../stores/domainStore';
import { useNotificationStore } from '../stores/notificationStore';
export function ClubScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'Club'>) {
  const { data: club, ensure, loading, error } = useClubDetailsStore();
  const [tab, setTab] = useState('Informações');
  const [confirmResignation, setConfirmResignation] = useState(false);
  const action = useAction();
  const auth = useAuthStore();
  const own = useClubStore(state => state.data?.club?.id);
  useScreenRefresh(() => ensure(route.params.id), undefined, true, route.params.id);
  useEffect(() => { navigation.setOptions({ title: own === route.params.id ? 'Meu clube' : 'Clube' }); }, [navigation, own, route.params.id]);
  async function resign() {
    const session = useAuthStore.getState();
    const id = route.params.id;
    await clubService.resign(id);
    if (useAuthStore.getState().user?.id !== session.user?.id || useClubStore.getState().data?.club?.id !== id) return;
    resetDomainStores();
    useClubStore.setState({ data: { club: null }, loading: false, error: null });
    useNotificationStore.getState().show('Gestão encerrada. Crie seu novo clube para continuar.');
  }
  return <GamePage loading={loading} error={error || (!confirmResignation ? action.error : null)}>{club?.id === route.params.id && <>
    <Card><View style={styles.hero}>
      <ClubBadge badge={club.badge} name={club.name} />
      <View style={{ flex: 1, gap: 8 }}>
        <View style={styles.nameRow}>
          <Text style={styles.name}>{club.name}</Text>
          <Text accessibilityLabel={`País: ${club.country?.name ?? club.country_id}`} style={styles.flag}>{countryFlag(club.country?.id ?? club.country_id)}</Text>
        </View>
        {own === club.id && auth.user?.name && <Text style={styles.caption}>Diretor: {auth.user.name}</Text>}
        <Text style={styles.caption}>Fundado em {new Date(club.created_at).toLocaleDateString('pt-BR')}</Text>
      </View>
    </View></Card>
    <ScreenTabs values={['Informações', 'Sala de troféus']} value={tab} onChange={setTab} />
    {tab === 'Informações' && <>
    <View style={styles.metrics}>
      {[
        { label: 'Ranking', value: `${club.ranking_position ?? 0}º`, detail: `${club.ranking_points ?? club.ranking} pontos`, color: '#e3edfc' },
        { label: 'Reputação', value: `${club.reputation ?? 10}/100`, detail: 'Prestígio do clube', color: '#daf4e7' },
        { label: 'Torcida', value: (club.supporters ?? 1000).toLocaleString('pt-BR'), detail: 'Torcedores', color: '#fff2c1' },
        { label: 'Confiança da torcida', value: `${club.fan_confidence ?? club.fan_satisfaction ?? 50}%`, detail: 'Influencia público e patrocínios', color: '#e8e0fc' },
      ].map(metric => <View key={metric.label} style={[styles.metric, { backgroundColor: metric.color }]}>
        <Text style={styles.label}>{metric.label}</Text><Text style={styles.value}>{metric.value}</Text><Text style={styles.caption}>{metric.detail}</Text>
      </View>)}
    </View>
    <Card>
      <View accessible accessibilityRole="progressbar" accessibilityLabel="Confiança da torcida" accessibilityValue={{ min: 0, max: 100, now: club.fan_confidence ?? club.fan_satisfaction ?? 50 }} style={styles.confidenceTrack}>
        <View style={{ width: `${Math.max(0, Math.min(100, club.fan_confidence ?? club.fan_satisfaction ?? 50))}%`, height: '100%', backgroundColor: (club.fan_confidence ?? club.fan_satisfaction ?? 50) < 30 ? '#c23c42' : '#087f70' }} />
      </View>
      <Text style={styles.caption}>Quanto maior a confiança, maior o público no estádio e melhores as novas propostas de patrocínio.</Text>
    </Card>
    {own === club.id && <ClubHistory openPlayer={id => navigation.navigate('PlayerDetails', { id })} />}
    {own === club.id && <>
      <ActionButton title="Abandonar gestão" secondary disabled={auth.loading || action.busy} onPress={() => setConfirmResignation(true)} />
      <ActionButton title="Logout" disabled={auth.loading || action.busy} onPress={() => { void auth.logout(); }} />
    </>}
    </>}
    {tab === 'Sala de troféus' && <Card>
      <Text style={styles.caption}>{club.trophies.length ? `${club.trophies.length} conquista${club.trophies.length > 1 ? 's' : ''}` : 'As próximas conquistas começam aqui.'}</Text>
      {club.trophies.map((trophy, index) => {
        const name = typeof trophy === 'string' ? trophy : trophy && typeof trophy === 'object' ? ('name' in trophy ? trophy.name : 'title' in trophy ? trophy.title : null) : null;
        return <Text key={index} style={styles.label}>🏆 {typeof name === 'string' ? name : `Título ${index + 1}`}</Text>;
      })}
    </Card>}
    <Modal visible={confirmResignation} transparent animationType="fade" onRequestClose={() => { if (!action.busy) setConfirmResignation(false); }}>
      <View style={{ flex: 1, justifyContent: 'center', padding: 24, backgroundColor: '#14243a88' }}>
        <View style={{ width: '100%', maxWidth: 450, alignSelf: 'center', padding: 24, gap: 18, borderRadius: 22, backgroundColor: '#fff' }}>
          <Text style={{ color: palette.ink, fontSize: 22, fontWeight: '800' }}>Abandonar gestão?</Text>
          <Text style={styles.caption}>Você deixará de administrar o clube {club.name} e perderá o acesso à sua gestão e aos seus recursos. O clube, seus jogadores e seu histórico serão preservados. Um bot assumirá o controle. Deseja continuar?</Text>
          <NotificationBubble message={action.error} />
          <ActionButton title="Não" secondary disabled={action.busy} onPress={() => setConfirmResignation(false)} />
          <ActionButton title={action.busy ? 'Confirmando…' : 'Sim'} disabled={action.busy} onPress={() => { void action.run(resign); }} />
        </View>
      </View>
    </Modal>
  </>}</GamePage>;
}

const styles = StyleSheet.create({
  hero: { flexDirection: 'row', alignItems: 'center', gap: 20 },
  nameRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  name: { color: palette.ink, fontSize: 28, fontWeight: '800', flexShrink: 1 },
  flag: { fontSize: 28 },
  confidenceTrack: { height: 10, borderRadius: 6, backgroundColor: '#e4eaf0', overflow: 'hidden' },
  caption: { color: palette.muted, lineHeight: 20 },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  metric: { flexGrow: 1, flexBasis: '45%', padding: 18, gap: 8, borderRadius: 20, borderWidth: 2, borderColor: palette.border },
  label: { color: palette.ink, fontWeight: '700' },
  value: { color: palette.ink, fontSize: 24, fontWeight: '800' },
});

function countryFlag(code: string) {
  const country = code.toUpperCase();
  return /^[A-Z]{2}$/.test(country) ? String.fromCodePoint(...[...country].map(letter => 127397 + letter.charCodeAt(0))) : '🌐';
}
