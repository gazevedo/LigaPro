import { useEffect } from 'react';
import { Pressable, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { useSquadStore } from '../stores/squadStore';
import { ActionButton, Card, GamePage, money, palette } from '../components/GameUI';
export function SquadScreen({ navigation }: NativeStackScreenProps<RootStackParamList, 'Squad'>) {
  const { data, loading, error, load } = useSquadStore();
  useEffect(() => { void load(); }, [load]);
  return <GamePage loading={loading} error={error}><Text style={{ fontSize: 26, fontWeight: '800', color: palette.ink }}>Seu plantel</Text>
    <Text style={{ color: palette.muted }}>Jogadores, contratos e desempenho. A escalação fica em Táticas.</Text>
    <ActionButton secondary title="Atualizar plantel" onPress={() => void load()} />
    {data?.players.map(player => <Pressable key={player.id} accessibilityRole="button" accessibilityLabel={`Detalhes de ${player.name}`} onPress={() => navigation.navigate('PlayerDetails', { id: player.id })}><Card>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}><Text style={{ backgroundColor: '#e3edfc', padding: 12, borderRadius: 14, fontWeight: '800', color: palette.ink }}>{player.position}</Text><View style={{ flex: 1, gap: 4 }}><Text style={{ fontSize: 19, fontWeight: '800', color: palette.ink }}>{player.name}</Text><Text style={{ color: palette.muted }}>{player.age} anos · Força {player.strength ?? player.overall} · {player.stars ?? 0} estrelas</Text></View></View>
      <Text>Salário mensal: {money(player.contract?.salary ?? player.salary ?? 0)}</Text>
      <Text>Contrato: {player.contract ? `até ${new Date(player.contract.expires_at).toLocaleDateString('pt-BR')}${player.contract.status === 'expiring' ? ' · Próximo do fim' : ''}` : 'Sem contrato ativo'}</Text>
      <Text>Condição: {player.physical_condition ?? 100}/100 · Energia: {player.energy ?? 100}/100</Text>
      <Text>{player.status === 'injured' ? `Lesionado${player.injury_type ? ` · ${player.injury_type}` : ''}` : player.status === 'suspended' ? 'Suspenso' : 'Disponível'}{player.injury_return_at ? ` · retorno ${new Date(player.injury_return_at).toLocaleDateString('pt-BR')}` : ''}</Text>
      <View style={{ backgroundColor: '#f4f7fc', borderRadius: 12, padding: 12, gap: 4 }}><Text style={{ fontWeight: '700', color: palette.ink }}>Estatísticas da carreira</Text><Text>{player.statistics?.matches ?? 0} jogos · {player.statistics?.goals ?? 0} gols · {player.statistics?.minutes ?? 0} min</Text><Text>{player.statistics?.yellow_cards ?? 0} amarelos · {player.statistics?.red_cards ?? 0} vermelhos</Text></View>
    </Card></Pressable>)}
  </GamePage>;
}
