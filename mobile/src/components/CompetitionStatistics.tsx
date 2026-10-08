import { useEffect, useState } from 'react';
import { Text } from 'react-native';
import { ActionButton, Card, Choices, NotificationBubble, palette } from './GameUI';
import { statisticsService, Ranking, Statistics } from '../services/statisticsService';
const labels: Record<Ranking, string> = { goals: 'Artilharia', matches: 'Mais jogos', cards: 'Mais cartões' };
export function CompetitionStatistics({ kind, openPlayer }: { kind: 'league' | 'cup'; openPlayer: (id: string) => void }) {
  const [ranking, setRanking] = useState<Ranking>('goals'), [data, setData] = useState<Statistics | null>(null), [error, setError] = useState<string | null>(null);
  useEffect(() => { let active = true; void statisticsService.competition(kind, ranking).then(result => { if (active) { setData(result); setError(null); } }).catch(reason => { if (active) setError(reason instanceof Error ? reason.message : 'Não foi possível carregar as estatísticas.'); }); return () => { active = false; }; }, [kind, ranking]);
  return <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Estatísticas do campeonato</Text><NotificationBubble message={error} />
    <Choices values={Object.values(labels)} value={labels[ranking]} onChange={label => setRanking((Object.keys(labels) as Ranking[]).find(key => labels[key] === label)!)} />
    {data?.ranking === ranking && data.rows.map((row, i) => <ActionButton secondary key={row.player_id} title={`${i + 1}. ${row.name} · ${row.total} ${ranking === 'goals' ? 'gols' : ranking === 'matches' ? 'jogos' : 'cartões'} · ${row.minutes} min`} onPress={() => openPlayer(row.player_id)} />)}
    {data?.ranking === ranking && !data.rows.length && <Text style={{ color: palette.muted }}>Nenhuma estatística neste campeonato.</Text>}
  </Card>;
}
