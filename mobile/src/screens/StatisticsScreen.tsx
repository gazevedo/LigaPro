import { useEffect, useState } from 'react';
import { Text } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { ActionButton as Button, GamePage, Choices } from '../components/GameUI';
import { domainStore } from '../stores/domainStore';
import { statisticsService, Ranking } from '../services/statisticsService';
const useStatisticsStore = domainStore(statisticsService.get);
const labels: Record<Ranking, string> = { goals: 'Artilharia', matches: 'Mais jogos', cards: 'Mais cartões' };
export function StatisticsScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Statistics'>) {
  const store = useStatisticsStore(), [ranking, setRanking] = useState<Ranking>('goals'), [season, setSeason] = useState<string>();
  const load = store.load;
  useEffect(() => { void load(ranking, season); }, [load, ranking, season]);
  return <GamePage loading={store.loading} error={store.error}>
    <Choices values={Object.values(labels)} value={labels[ranking]} onChange={label => setRanking((Object.keys(labels) as Ranking[]).find(key => labels[key] === label)!)} />
    <Text>Temporada {store.data?.season?.number ?? '—'}</Text>
    {!!store.data?.seasons?.length && <Choices values={store.data.seasons.map(s => `Temporada ${s.number}`)} value={`Temporada ${store.data.season?.number}`} onChange={label => setSeason(store.data?.seasons?.find(s => `Temporada ${s.number}` === label)?.id)} />}
    <Button title="Atualizar estatísticas" onPress={() => void load(ranking, season)} />
    {store.data?.rows.map((row, i) => <Text key={row.player_id}>{i + 1}. {row.name} · {row.position} · {row.total} {ranking === 'goals' ? 'gols' : ranking === 'matches' ? 'jogos' : 'cartões'} · {row.minutes} min</Text>)}
    {store.data?.rows.length === 0 && <Text>Nenhuma estatística nesta temporada.</Text>}
    <Text>Relatórios das minhas partidas</Text>
    {store.data?.recent_matches?.map(match => <Button key={match.id} title={`Rodada ${match.round} · ${match.home_goals} × ${match.away_goals}`} onPress={() => navigation.navigate('MatchReport', { id: match.id })} />)}
    {store.data?.recent_matches?.length === 0 && <Text>Nenhuma partida concluída nesta temporada.</Text>}
  </GamePage>;
}
