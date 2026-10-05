import { useEffect } from 'react';
import { Button, Text, View } from 'react-native';
import { GamePage, useAction } from '../components/GameUI';
import { developmentService } from '../services/developmentService';
import { domainStore } from '../stores/domainStore';
const useTrainingStore = domainStore(developmentService.training);
export function TrainingScreen() {
  const { data, loading, error, load } = useTrainingStore();
  const action = useAction();
  useEffect(() => { void load(); }, [load]);
  return <GamePage loading={loading || action.busy} error={action.error || error}>
    <Button title="Atualizar treinamento" onPress={() => void load()} />
    <Text>A cada 100 treinos, o jogador ganha um ponto de força.</Text>
    {data?.map(player => <View key={player.id} style={{ gap: 6 }}>
      <Text>{player.name} · {player.position} · {player.age} anos</Text>
      <Text>Força: {player.strength ?? player.overall} · Treino: {player.training_level ?? 0}/100</Text>
      <Button title={`Treinar ${player.name}`} disabled={action.busy || loading}
        onPress={() => void action.run(async () => { await developmentService.train(player.id); await load(); })} />
    </View>)}
    {data?.length === 0 && <Text>Nenhum jogador disponível.</Text>}
  </GamePage>;
}
