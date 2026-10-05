import { useEffect } from 'react';
import { Button, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { GamePage } from '../components/GameUI';
import { domainStore } from '../stores/domainStore';
import { statisticsService } from '../services/statisticsService';
const useReportStore = domainStore(statisticsService.report);
export function MatchReportScreen({ route }: NativeStackScreenProps<RootStackParamList, 'MatchReport'>) {
  const { data, loading, error, load } = useReportStore();
  useEffect(() => { void load(route.params.id); }, [load, route.params.id]);
  const report = data?.match.id === route.params.id ? data : null;
  return <GamePage loading={loading} error={error}>
    <Button title="Atualizar relatório" onPress={() => void load(route.params.id)} />
    {report && <>
      <Text style={{ fontSize: 22 }}>{report.home_name} {report.match.home_goals} × {report.match.away_goals} {report.away_name}</Text>
      <Text>Rodada {report.match.round} · {new Date(report.match.date).toLocaleString('pt-BR')}</Text>
      <Text>Notas dos jogadores que atuaram · escala de 5,0 a 10,0</Text>
      {([['home', report.home_name, report.match.home_club_id], ['away', report.away_name, report.match.away_club_id]] as const).map(([side, name, club]) => <View key={side} style={{ gap: 8 }}><Text style={{ fontWeight: 'bold' }}>{name}</Text>{report.ratings.filter(r => r.club_id === club).map(r => <View key={r.id}>
        <Text>{r.name} · {r.position} · nota {r.rating.toFixed(1).replace('.', ',')} · {r.minutes} min</Text>
        <Text>Gols: {r.events_summary.goals ?? 0} · Amarelos: {r.events_summary.yellow_cards ?? 0} · Vermelhos: {r.events_summary.red_cards ?? 0} · Defesas: {r.events_summary.saves ?? 0}</Text>
      </View>)}</View>)}
      {!report.ratings.length && <Text>Sem notas individuais para esta partida.</Text>}
    </>}
  </GamePage>;
}
