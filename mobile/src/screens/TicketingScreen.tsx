import { Text, View } from 'react-native';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { useTicketingStore } from '../stores/screenStores';
import { Card, GamePage, money, palette } from '../components/GameUI';
import { TicketMatch } from '../types/game';
const statusNames: Record<string, string> = { completed: 'Encerrado', finished: 'Encerrado', live: 'Em andamento', scheduled: 'Agendado' };
function MatchInfo({ match }: { match?: TicketMatch | null }) {
  if (!match) return null;
  return <View style={{ gap: 6 }}><Text style={{ fontWeight: '700' }}>{match.home_name} × {match.away_name}</Text>
    <Text>{new Date(match.date).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })} · {statusNames[match.status] ?? match.status}</Text>
    {match.home_goals != null && match.away_goals != null && <Text>Placar: {match.home_goals} × {match.away_goals}</Text>}
  </View>;
}
export function TicketingScreen() {
  const { data, loading, error, ensure, refresh } = useTicketingStore();
  useScreenRefresh(ensure, refresh);
  const last = data?.last_match ?? data?.history[0];
  return <GamePage loading={loading} error={error}>
    <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Último jogo em casa</Text>
      {last ? <><MatchInfo match={last.match} /><Text>Público: {last.attendance} pessoas</Text><Text>Faturamento: {money(last.income)}</Text></> : <Text>Nenhuma partida com bilheteria registrada.</Text>}
    </Card>
    <Card><Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>Projeção para o próximo jogo em casa</Text>
      {data?.next_match ? <><MatchInfo match={data.next_match} /><Text>Público estimado: {data.estimated_attendance ?? 0} pessoas</Text><Text>Faturamento estimado: {money(data.estimated_income ?? 0)}</Text></> : <Text>Nenhum jogo em casa agendado.</Text>}
      <Text>Capacidade: {data?.capacity ?? 0} pessoas</Text><Text style={{ color: palette.muted }}>A projeção usa os preços configurados no estádio.</Text>
    </Card>
    <Card><Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>Histórico de público e faturamento</Text>
      <Text>Faturamento acumulado: {money(data?.income ?? 0)}</Text>
      {!data?.history.length && <Text>Nenhuma partida disputada.</Text>}
      {data?.history.map(row => <View key={row.id} style={{ gap: 8, borderTopWidth: 1, borderColor: palette.border, paddingTop: 12 }}><MatchInfo match={row.match} />{!row.match && row.created_at && <Text>{new Date(row.created_at).toLocaleDateString('pt-BR')}</Text>}<Text>{row.attendance} pessoas · {money(row.income)}</Text></View>)}
    </Card>
  </GamePage>;
}
