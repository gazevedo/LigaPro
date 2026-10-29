import { useState } from 'react';
import { Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Card, GamePage, palette, ActionButton } from '../components/GameUI';
import { ComboBox } from '../components/ComboBox';
import { domainStore } from '../stores/domainStore';
import { PerformanceRow, performanceService } from '../services/statisticsService';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { trainingSkills } from '../components/TrainingPlanEditor';
const usePerformance = domainStore(performanceService.get);
function Chart({ values, labels, max, title }: { values: number[]; labels: string[]; max: number; title: string }) {
  return <View style={{ gap: 8 }}><Text style={{ fontWeight: '700' }}>{title}</Text>
    {!values.length ? <Text>Sem registros suficientes. O histórico será preenchido com a evolução do jogador.</Text> : <View style={{ flexDirection: 'row', gap: 4, alignItems: 'flex-end', height: 140 }}>{values.map((value, i) => <View key={i} style={{ flex: 1, alignItems: 'center', gap: 4 }}>
      <Text style={{ fontSize: 10 }}>{value.toFixed(1)}</Text><View accessibilityLabel={`${labels[i]}: ${value.toFixed(1)}`} style={{ width: '100%', maxWidth: 36, height: Math.max(2, value / max * 100), backgroundColor: palette.primary, borderRadius: 3 }} /><Text style={{ fontSize: 9 }}>{labels[i]}</Text>
    </View>)}</View>}
  </View>;
}
function Summary({ row }: { row: PerformanceRow }) {
  const total = (field: 'goals' | 'assists' | 'minutes') => row.recent.reduce((sum, match) => sum + match[field], 0);
  const dates = row.recent.map(match => new Date(match.date).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }));
  return <Card><Text style={{ fontSize: 20, fontWeight: '700' }}>{row.player.name}</Text>
    <Text>Média nas últimas {Math.min(5, row.recent.length)} atuações: {row.average_rating?.toFixed(2) ?? 'Sem atuações'} · Variação contra as cinco anteriores: {row.rating_change === null ? 'Sem base anterior' : `${row.rating_change > 0 ? '+' : ''}${row.rating_change.toFixed(2)}`}</Text>
    <Text>Últimas {row.recent.length} atuações: {total('minutes')} min · {total('goals')} gols · {total('assists')} assistências</Text>
    <Chart title="Notas por partida · ordem cronológica" values={row.recent.map(match => match.rating)} labels={dates} max={10} />
    <Chart title="Evolução da força · treino e temporadas" values={row.development.length ? [row.development[0].previous_strength, ...row.development.map(item => item.strength)] : []} labels={row.development.length ? ['Inicial', ...row.development.map(item => new Date(item.created_at).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }))] : []} max={100} />
  </Card>;
}
export function PerformanceScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Performance'>) {
  const store = usePerformance(); const [first, setFirst] = useState(''), [second, setSecond] = useState('');
  useScreenRefresh(store.ensure, store.refresh);
  const players = store.data?.players ?? [];
  const a = players.find(row => row.player.id === first) ?? players[0];
  const b = players.find(row => row.player.id === second) ?? players.find(row => row.player.id !== a?.player.id);
  const options = players.map(row => ({ value: row.player.id, label: `${row.player.name} · ${row.player.position}` }));
  return <GamePage loading={store.loading} error={store.error}>
    <Text style={{ fontSize: 22, fontWeight: '800' }}>Desempenho e comparação</Text>
    <Text>Notas reais das últimas dez atuações no clube. Sem jogos ou evolução registrados, nenhum dado é estimado.</Text>
    {!!players.length && <>
      <ComboBox label="Primeiro jogador" value={a?.player.id ?? ''} options={options} onChange={setFirst} />
      <ComboBox label="Comparar com" value={b?.player.id ?? ''} options={options} onChange={setSecond} />
      {a && b && <Card><Text style={{ fontWeight: '700' }}>{a.player.name} × {b.player.name}</Text>
        <Text>Força: {a.player.strength ?? a.player.overall} × {b.player.strength ?? b.player.overall}</Text>
        {Object.entries(trainingSkills).map(([key, label]) => <Text key={key}>{label}: {a.player.individual_skills?.[key as keyof typeof trainingSkills] ?? '—'} × {b.player.individual_skills?.[key as keyof typeof trainingSkills] ?? '—'}</Text>)}
        <Text>Condição física: {a.player.physical_condition ?? 100} × {b.player.physical_condition ?? 100} · Moral: {a.player.morale ?? 50} × {b.player.morale ?? 50}</Text>
      </Card>}
      {a && <Summary row={a} />}{b && b.player.id !== a?.player.id && <Summary row={b} />}
      {a?.recent.slice().reverse().map(match => <ActionButton secondary key={match.match_id} title={`Pós-jogo · ${new Date(match.date).toLocaleDateString('pt-BR')} · nota ${match.rating}`} onPress={() => navigation.navigate('MatchReport', { id: match.match_id })} />)}
    </>}
    {!store.loading && !players.length && <Text>Nenhum jogador no plantel.</Text>}
  </GamePage>;
}
