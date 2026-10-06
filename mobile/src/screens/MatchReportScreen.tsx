import { useClubStore } from '../stores/clubStore';
import { useEffect } from 'react';
import { Button, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { GamePage, money } from '../components/GameUI';
import { domainStore } from '../stores/domainStore';
import { statisticsService } from '../services/statisticsService';
const useReportStore = domainStore(statisticsService.report);
export function MatchReportScreen({ route, navigation }: NativeStackScreenProps<RootStackParamList, 'MatchReport'>) {
  const ownClubId = useClubStore(state => state.data?.club?.id);
  const { data, loading, error, load } = useReportStore();
  useEffect(() => { void load(route.params.id); }, [load, route.params.id]);
  const report = data?.match.id === route.params.id ? data : null;
  return <GamePage loading={loading} error={error}>
    <Button title="Atualizar relatório" onPress={() => void load(route.params.id)} />
    {report && <>
      <Text style={{ fontSize: 22 }}>{report.home_name} {report.match.home_goals} × {report.match.away_goals} {report.away_name}</Text>
      <Text>{report.match.phase ? `Copa Nacional · ${report.match.phase}` : report.match.round ? `Rodada ${report.match.round}` : 'Amistoso'} · {new Date(report.match.date).toLocaleString('pt-BR')}</Text>
      {report.match.extra_time && <Text>Partida com prorrogação · 120 minutos</Text>}{report.match.shootout_score && <Text>Pênaltis: {report.match.shootout_score[report.match.home_club_id]} × {report.match.shootout_score[report.match.away_club_id]}</Text>}{report.match.winner_club_id && <Text>Classificado: {report.match.winner_club_id === report.match.home_club_id ? report.home_name : report.away_name}</Text>}
      <Text>{report.competition}</Text>
      <Text>Estatísticas: mandante × visitante</Text>
      {['possession', 'attacks', 'chances', 'shots', 'shots_on_target', 'fouls', 'yellow_cards', 'red_cards'].map(key => <Text key={key}>{({possession: 'Posse', attacks: 'Ataques', chances: 'Chances', shots: 'Finalizações', shots_on_target: 'No alvo', fouls: 'Faltas', yellow_cards: 'Amarelos', red_cards: 'Vermelhos'} as Record<string, string>)[key]}: {[report.match.home_club_id, report.match.away_club_id].map(id => { const value = Number(report.statistics?.[id]?.[key] ?? 0); return key === 'possession' ? `${Math.round(value * 100)}%` : value; }).join(' × ')}</Text>)}
      <Text>Público: {report.financial?.attendance ?? 0} · Ingresso médio: {money(report.financial?.price ?? 0)} · Renda: {money(report.financial?.income ?? 0)}</Text>
      <Text>Linha do tempo</Text>
      {report.events?.filter(e => ['goal', 'yellow_card', 'red_card', 'penalty_awarded', 'substitution', 'injury'].includes(e.type)).map((e, i) => <Text key={e.id ?? i}>{e.minute}′ · {({goal: 'Gol', yellow_card: 'Amarelo', red_card: 'Vermelho', penalty_awarded: 'Pênalti', substitution: 'Substituição', injury: 'Lesão'} as Record<string, string>)[e.type]} · {report.ratings.find(r => r.player_id === e.player_id)?.name ?? 'Equipe'}</Text>)}
      <Text>Consequências</Text>
      {report.consequences?.map(p => <Text key={p.player_id}>{p.name} · Energia {Math.round(p.energy_before)} → {Math.round(p.energy)} · Moral {p.morale_before} → {p.morale}{p.injury_type ? ` · ${p.injury_type}` : ''}{p.suspended_until ? ' · Suspenso' : ''}</Text>)}
      <Text>Notas dos jogadores que atuaram · escala de 5,0 a 10,0</Text>
      {([['home', report.home_name, report.match.home_club_id], ['away', report.away_name, report.match.away_club_id]] as const).map(([side, name, club]) => <View key={side} style={{ gap: 8 }}><Text style={{ fontWeight: 'bold' }}>{name}</Text>{report.ratings.filter(r => r.club_id === club).map(r => <View key={r.id}>
        <Text>{r.name} · {r.position} · nota {r.rating.toFixed(1).replace('.', ',')} · {r.minutes} min</Text>
        <Button title={`Ver ${r.name}`} onPress={() => navigation.navigate('PlayerDetails', { id: r.player_id })} />
        <Text>Gols: {r.events_summary.goals ?? 0} · Amarelos: {r.events_summary.yellow_cards ?? 0} · Vermelhos: {r.events_summary.red_cards ?? 0} · Defesas: {r.events_summary.saves ?? 0}</Text>
      </View>)}</View>)}
      {!report.ratings.length && <Text>Sem notas individuais para esta partida.</Text>}
      <Button title="Voltar" onPress={() => navigation.goBack()} />
      <Button title="Ver classificação" onPress={() => navigation.navigate('Club', { id: ownClubId ?? report.match.home_club_id })} />
      <Button title="Próximo evento" onPress={() => navigation.navigate('Calendar')} />
    </>}
  </GamePage>;
}
