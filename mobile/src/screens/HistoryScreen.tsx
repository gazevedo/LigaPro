import { Text } from 'react-native';
import { ActionButton as Button, Card, NotificationBubble, money, palette } from '../components/GameUI';
import { useHistoryStore } from '../stores/screenStores';
import { useScreenRefresh } from '../components/useScreenRefresh';
export function ClubHistory({ openPlayer }: { openPlayer: (id: string) => void }) {
  const { data, error, ensure } = useHistoryStore();
  useScreenRefresh(ensure);
  return <Card><NotificationBubble message={error} />
    {data?.seasons.map(s => <Text key={s.id}>Temporada {s.season_number} · Campeão: {s.champion_name ?? 'Clube'} · Artilheiro: {s.top_scorer?.goals ?? 0} gols</Text>)}
    {data?.clubs.map(c => <Text key={c.id}>Temporada {c.season_number} · Divisão {c.division_tier + 1} · {c.position}º {c.title ? '🏆' : ''} · Caixa {money(c.cash)}</Text>)}
    <Text style={{ color: palette.primary, fontSize: 17, fontWeight: '700' }}>Records do clube</Text>{data?.records.map(r => <Text key={r.id}>{({biggest_win: 'Maior goleada', longest_win_streak: 'Sequência de vitórias', largest_attendance: 'Maior público', largest_transfer: 'Maior transferência', most_goals_player: 'Mais gols na carreira', highest_market_value: 'Maior valor de mercado'} as Record<string, string>)[r.id] ?? 'Recorde'}: {['largest_transfer', 'highest_market_value'].includes(r.id) ? money(r.value) : r.value}</Text>)}
    {data?.players.map(p => <Button key={p.id} title={`${p.player_name ?? 'Jogador'} · ${({transfer: 'Transferência', season: 'Temporada', retirement: 'Aposentadoria'} as Record<string, string>)[p.type] ?? 'Carreira'} · ${p.goals ?? 0} gols · ${p.matches ?? 0} jogos · ${p.stars ?? 0} estrelas · ${(p.titles?.length ?? 0) + (p.cup_titles?.length ?? 0)} títulos`} onPress={() => openPlayer(p.player_id)} />)}
  </Card>;
}
