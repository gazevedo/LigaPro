import { useEffect, useState } from 'react';
import { Button, Text, View } from 'react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { Squad } from '../types/game';
import { useSquadStore } from '../stores/squadStore';
import { squadService } from '../services/squadService';
import { Choices, GamePage, useAction } from '../components/GameUI';
type Props = NativeStackScreenProps<RootStackParamList, 'Squad'>;
export function SquadScreen({ navigation }: Props) {
  const { data, loading, error, load } = useSquadStore();
  useEffect(() => { void load(); }, [load]);
  return <GamePage loading={loading} error={error}>
    <Button title="Atualizar plantel" onPress={() => void load()} />
    {data && <SquadEditor key={JSON.stringify(data.lineup)} squad={data} navigation={navigation} />}
  </GamePage>;
}
function SquadEditor({ squad, navigation }: { squad: Squad; navigation: Props['navigation'] }) {
  const action = useAction();
  const [formation, setFormation] = useState(squad.lineup.formation);
  const [starters, setStarters] = useState(squad.lineup.starters.filter(id => squad.players.some(p => p.id === id && !['injured', 'suspended', 'retired'].includes(p.status ?? ''))));
  return <View style={{ gap: 14 }}>
    {action.error && <Text accessibilityRole="alert">{action.error}</Text>}
    <Choices values={Object.keys(squad.formations)} value={formation} onChange={setFormation} />
    <Text>Entrosamento da equipe: {squad.team_chemistry ?? 40}/100</Text>
    <Text>Titulares: {starters.length}/11 · selecione um GK (GOL) e as posições da formação</Text>
    {squad.players.map(player => <View key={player.id}>
      <Text>Condição: {player.physical_condition ?? 100}/100 · {player.status ?? 'available'}{player.injury_return_at ? ` · retorno ${new Date(player.injury_return_at).toLocaleDateString('pt-BR')}` : ''}</Text>
      <Button disabled={['injured', 'suspended', 'retired'].includes(player.status ?? '')} title={`${starters.includes(player.id) ? 'Titular' : 'Reserva'} · ${player.position} ${player.name}`} onPress={() => setStarters(ids => ids.includes(player.id) ? ids.filter(id => id !== player.id) : [...ids, player.id])} />
      <Button title={`Detalhes de ${player.name}`} onPress={() => navigation.navigate('PlayerDetails', { id: player.id })} />
    </View>)}
    <Button title="Salvar escalação" disabled={action.busy || starters.length !== 11} onPress={() => void action.run(async () => {
      await squadService.save({ formation, starters, reserves: squad.players.filter(p => !starters.includes(p.id) && !['injured', 'suspended', 'retired'].includes(p.status ?? '')).map(p => p.id) });
      await useSquadStore.getState().load();
    })} />
  </View>;
}
