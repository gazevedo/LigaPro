import { Pressable, Text, View } from 'react-native';
import { Card, NotificationBubble, palette } from './GameUI';
import { useLeagueStatisticsStore, useCupStatisticsStore } from '../stores/screenStores';
import { useScreenRefresh } from './useScreenRefresh';
export function CompetitionStatistics({ kind, openPlayer }: { kind: 'league' | 'cup'; openPlayer: (id: string) => void }) {
  const league = useLeagueStatisticsStore(), cup = useCupStatisticsStore();
  const { data, error, ensure, refresh } = kind === 'league' ? league : cup;
  useScreenRefresh(ensure, refresh);
  return <Card><NotificationBubble message={error} />
    <View style={{ flexDirection: 'row', gap: 8 }}><Text style={{ width: 25 }}>#</Text><Text style={{ flex: 1, fontWeight: '700' }}>Jogador</Text><Text style={{ width: 40 }}>Gols</Text><Text style={{ width: 40 }}>Jogos</Text></View>
    {data?.rows.map((row, i) => <Pressable key={row.player_id} accessibilityRole="button" accessibilityLabel={`Detalhes de ${row.name}`} onPress={() => openPlayer(row.player_id)} style={{ flexDirection: 'row', gap: 8, paddingVertical: 14, borderTopWidth: 1, borderColor: palette.border }}><Text style={{ width: 25 }}>{i + 1}</Text><Text style={{ flex: 1, color: palette.ink, fontWeight: '600' }}>{row.name}</Text><Text style={{ width: 40 }}>{row.goals ?? row.total}</Text><Text style={{ width: 40 }}>{row.matches ?? 0}</Text></Pressable>)}
    {data && !data.rows.length && <Text style={{ color: palette.muted }}>Nenhum gol registrado neste campeonato.</Text>}
  </Card>;
}
