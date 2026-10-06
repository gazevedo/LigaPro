import { useEffect, useState } from 'react';
import { Button, Text } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { GamePage, money, useAction } from '../components/GameUI';
import { History, historyService } from '../services/historyService';
export function HistoryScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'History'>) {
  const [data, setData] = useState<History | null>(null); const action = useAction();
  useEffect(() => { void action.run(async () => setData(await historyService.get())); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}>
    <Text>Histórico das temporadas</Text>
    {data?.seasons.map(s => <Text key={s.id}>Temporada {s.season_number} · Campeão: {s.champion_name ?? 'Clube'} · Artilheiro: {s.top_scorer?.goals ?? 0} gols</Text>)}
    <Text>Trajetória do clube</Text>{data?.clubs.map(c => <Text key={c.id}>Temporada {c.season_number} · Divisão {c.division_tier + 1} · {c.position}º {c.title ? '🏆' : ''} · Caixa {money(c.cash)}</Text>)}
    <Text>Recordes do universo</Text>{data?.records.map(r => <Text key={r.id}>{({biggest_win: 'Maior goleada', longest_win_streak: 'Sequência de vitórias', largest_attendance: 'Maior público', largest_transfer: 'Maior transferência', most_goals_player: 'Mais gols na carreira', highest_market_value: 'Maior valor de mercado'} as Record<string, string>)[r.id] ?? 'Recorde'}: {['largest_transfer', 'highest_market_value'].includes(r.id) ? money(r.value) : r.value}</Text>)}
    <Text>Carreiras dos jogadores</Text>{data?.players.map(p => <Button key={p.id} title={`${p.player_name ?? 'Jogador'} · ${({transfer: 'Transferência', season: 'Temporada', retirement: 'Aposentadoria'} as Record<string, string>)[p.type] ?? 'Carreira'} · ${p.goals ?? 0} gols · ${p.matches ?? 0} jogos · ${p.stars ?? 0} estrelas · ${(p.titles?.length ?? 0) + (p.cup_titles?.length ?? 0)} títulos`} onPress={() => navigation.navigate('PlayerDetails', { id: p.player_id })} />)}
  </GamePage>;
}
