import { useEffect } from 'react';
import { Button, Text, View } from 'react-native';
import { GamePage, useAction } from '../components/GameUI';
import { developmentService } from '../services/developmentService';
import { domainStore } from '../stores/domainStore';
const useYouthStore = domainStore(developmentService.youth);
export function YouthAcademyScreen() {
  const { data, loading, error, load } = useYouthStore();
  const action = useAction();
  useEffect(() => { void load(); }, [load]);
  return <GamePage loading={loading || action.busy} error={action.error || error}>
    <Button title="Atualizar base" onPress={() => void load()} />
    <Text>O clube recebe dois jovens por temporada. A promoção pode ocorrer a partir dos 18 anos.</Text>
    {data?.map(player => <View key={player.id} style={{ gap: 6 }}>
      <Text>{player.name} · {player.position} · {player.age} anos</Text>
      <Text>Força: {player.strength ?? player.overall} · Treino: {player.training_progress ?? 0}/100</Text>
      {player.can_train === false && <Text>Limite de desenvolvimento atingido.</Text>}
      <Button title={`Treinar ${player.name}`} disabled={action.busy || loading || player.can_train === false}
        onPress={() => void action.run(async () => { await developmentService.train(player.id); await load(); })} />
      <Button title={`Promover ${player.name}`} disabled={action.busy || loading || player.age < 18}
        onPress={() => void action.run(async () => { await developmentService.promote(player.id); await load(); })} />
    </View>)}
    {data?.length === 0 && <Text>Nenhum jovem disponível.</Text>}
  </GamePage>;
}
