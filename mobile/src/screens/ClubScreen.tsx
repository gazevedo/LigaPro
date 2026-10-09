import { ClubHistory } from './HistoryScreen';
import { ScreenTabs } from '../components/ScreenTabs';
import { useAuthStore } from '../stores/authStore';
import { ClubBadge } from '../components/ClubBadge';
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useClubDetailsStore } from '../stores/screenStores';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { useClubStore } from '../stores/clubStore';
import { ActionButton, Card, GamePage, palette } from '../components/GameUI';
export function ClubScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'Club'>) {
  const { data: club, ensure, loading, error } = useClubDetailsStore();
  const [tab, setTab] = useState('Informações');
  const auth = useAuthStore();
  const own = useClubStore(state => state.data?.club?.id);
  useScreenRefresh(() => ensure(route.params.id), undefined, true, route.params.id);
  useEffect(() => { navigation.setOptions({ title: own === route.params.id ? 'Meu clube' : 'Clube' }); }, [navigation, own, route.params.id]);
  return <GamePage loading={loading} error={error}>{club?.id === route.params.id && <>
    <Card><View style={styles.hero}>
      <View style={{ alignItems: 'center', gap: 8 }}><ClubBadge badge={club.badge} name={club.name} />
        <Text accessibilityLabel={`País: ${club.country?.name ?? club.country_id}`} style={{ fontSize: 28 }}>{countryFlag(club.country?.id ?? club.country_id)}</Text>
      </View>
      <View style={{ flex: 1, gap: 8 }}>
        <Text style={styles.name}>{club.name}</Text>
        {own === club.id && <Text style={styles.caption}>{auth.user?.name}</Text>}
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
        { label: 'Satisfação', value: `${club.fan_satisfaction ?? 50}/100`, detail: 'Apoio da torcida', color: '#e8e0fc' },
      ].map(metric => <View key={metric.label} style={[styles.metric, { backgroundColor: metric.color }]}>
        <Text style={styles.label}>{metric.label}</Text><Text style={styles.value}>{metric.value}</Text><Text style={styles.caption}>{metric.detail}</Text>
      </View>)}
    </View>
    {own === club.id && <ClubHistory openPlayer={id => navigation.navigate('PlayerDetails', { id })} />}
    </>}
    {tab === 'Sala de troféus' && <Card>
      <Text style={styles.caption}>{club.trophies.length ? `${club.trophies.length} conquista${club.trophies.length > 1 ? 's' : ''}` : 'As próximas conquistas começam aqui.'}</Text>
      {club.trophies.map((trophy, index) => {
        const name = typeof trophy === 'string' ? trophy : trophy && typeof trophy === 'object' ? ('name' in trophy ? trophy.name : 'title' in trophy ? trophy.title : null) : null;
        return <Text key={index} style={styles.label}>🏆 {typeof name === 'string' ? name : `Título ${index + 1}`}</Text>;
      })}
    </Card>}
    {own === club.id && <ActionButton title="Sair" disabled={auth.loading} onPress={() => { void auth.logout(); }} />}
  </>}</GamePage>;
}

const styles = StyleSheet.create({
  hero: { flexDirection: 'row', alignItems: 'center', gap: 20 },
  name: { color: palette.ink, fontSize: 28, fontWeight: '800' },
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
