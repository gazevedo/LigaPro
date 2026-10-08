import { ClubHistory } from './HistoryScreen';
import { ProfileScreen } from './ProfileScreen';
import { ClubBadge } from '../components/ClubBadge';
import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Club } from '../types/game';
import { clubService } from '../services/clubService';
import { useClubStore } from '../stores/clubStore';
import { Card, GamePage, palette, useAction } from '../components/GameUI';
export function ClubScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'Club'>) {
  const [club, setClub] = useState<Club | null>(null);
  const own = useClubStore(state => state.data?.club?.id);
  const action = useAction();
  useEffect(() => { void action.run(async () => setClub(await clubService.get(route.params.id))); }, [route.params.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}>{club?.id === route.params.id && <>
    <Card><View style={styles.hero}>
      <ClubBadge badge={club.badge} name={club.name} />
      <View style={{ flex: 1, gap: 8 }}>
        <Text style={styles.eyebrow}>{own === club.id ? 'MEU CLUBE' : 'CLUBE'}</Text>
        <Text style={styles.name}>{club.name}</Text>
        <Text style={styles.caption}>{club.country?.name ?? club.country_id}</Text>
        <Text style={styles.caption}>Fundado em {new Date(club.created_at).toLocaleDateString('pt-BR')}</Text>
      </View>
    </View></Card>
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
    <Card><Text style={styles.heading}>Sala de troféus</Text>
      <Text style={styles.caption}>{club.trophies.length ? `${club.trophies.length} conquista${club.trophies.length > 1 ? 's' : ''}` : 'As próximas conquistas começam aqui.'}</Text>
      {club.trophies.map((trophy, index) => {
        const name = typeof trophy === 'string' ? trophy : trophy && typeof trophy === 'object' ? ('name' in trophy ? trophy.name : 'title' in trophy ? trophy.title : null) : null;
        return <Text key={index} style={styles.label}>🏆 {typeof name === 'string' ? name : `Título ${index + 1}`}</Text>;
      })}
    </Card>
    {own === club.id && <>
      <Card><Text style={styles.heading}>Perfil do técnico</Text><ProfileScreen /></Card>
      <ClubHistory openPlayer={id => navigation.navigate('PlayerDetails', { id })} />
    </>}
  </>}</GamePage>;
}

const styles = StyleSheet.create({
  hero: { flexDirection: 'row', alignItems: 'center', gap: 20 },
  eyebrow: { color: palette.primary, fontSize: 12, fontWeight: '800', letterSpacing: 2 },
  name: { color: palette.ink, fontSize: 28, fontWeight: '800' },
  heading: { color: palette.ink, fontSize: 21, fontWeight: '800' },
  caption: { color: palette.muted, lineHeight: 20 },
  metrics: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  metric: { flexGrow: 1, flexBasis: '45%', padding: 18, gap: 8, borderRadius: 20, borderWidth: 2, borderColor: palette.border },
  label: { color: palette.ink, fontWeight: '700' },
  value: { color: palette.ink, fontSize: 24, fontWeight: '800' },
});
