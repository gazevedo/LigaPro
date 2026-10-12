import { Pressable, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useClubDetailsStore, useOtherClubSquadStore } from '../stores/screenStores';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { ClubBadge } from '../components/ClubBadge';
import { Card, GamePage, money, palette } from '../components/GameUI';
const positions: Record<string, string> = { GK: 'GOL', GOL: 'GOL', FB: 'LAT', CB: 'ZAG', DEF: 'DEF', MID: 'MED', MED: 'MED', ATT: 'ATA', ATA: 'ATA' };
const skills: Record<string, string> = { goalkeeping: 'Defesa do goleiro', speed: 'Velocidade', technique: 'Técnica', passing: 'Passe', tackling: 'Desarme', playmaking: 'Criação', finishing: 'Finalização' };
const order: Record<string, number> = { GOL: 0, ZAG: 1, DEF: 1, LAT: 2, MED: 3, ATA: 4 };
export function OtherClubScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'OtherClub'>) {
  const details = useClubDetailsStore(), squad = useOtherClubSquadStore();
  useScreenRefresh(() => Promise.all([details.ensure(route.params.id), squad.ensure(route.params.id)]), undefined, true, route.params.id);
  const club = details.data?.id === route.params.id ? details.data : null;
  const players = [...(squad.data ?? [])].sort((a, b) => (order[positions[a.position]] ?? 5) - (order[positions[b.position]] ?? 5));
  return <GamePage loading={details.loading || squad.loading} error={details.error || squad.error}>
    {club && <Card><View style={{ flexDirection: 'row', gap: 16, alignItems: 'center' }}>
      <ClubBadge badge={club.badge} name={club.name} />
      <View style={{ flex: 1, gap: 8 }}><Text style={{ fontSize: 24, fontWeight: '800', color: palette.ink }}>{club.name}</Text><Text>{club.country?.name ?? club.country_id}</Text><Text>Ranking: {club.ranking_position ?? 0}º · Reputação: {club.reputation ?? 10}/100</Text></View>
    </View></Card>}
    {club && <Card><Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>Plantel</Text>
      {players.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Detalhes de ${player.name}`} onPress={() => navigation.navigate('PlayerDetails', { id: player.id })} style={{ borderTopWidth: 1, borderColor: palette.border, paddingVertical: 14, flexDirection: 'row', gap: 10 }}>
        <Text style={{ width: 34, color: palette.primary, fontWeight: '700' }}>{positions[player.position] ?? player.position}</Text>
        <View style={{ flex: 1, gap: 6 }}><Text style={{ fontWeight: '700', color: palette.ink }}>{player.name}</Text>{player.individual_skills && <Text style={{ color: palette.muted }}>{Object.entries(player.individual_skills).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([skill]) => skills[skill] ?? skill).join(' / ')}</Text>}<Text style={{ color: palette.muted }}>{player.age} anos · Força: {player.strength ?? player.overall}</Text><Text style={{ color: palette.muted }}>Energia: {player.energy ?? 100}% · Condição: {player.physical_condition ?? 100}%</Text><Text style={{ color: palette.muted }}>Valor: {money(player.market_value ?? player.value)} · Salário: {money(player.salary ?? 0)}</Text></View>
      </Pressable>)}
      {!squad.loading && !players.length && <Text>Nenhum jogador no plantel.</Text>}
    </Card>}
  </GamePage>;
}
