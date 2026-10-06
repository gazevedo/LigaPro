import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';
import { ActionButton as Button, Choices, GamePage, useAction } from '../components/GameUI';
import { developmentService } from '../services/developmentService';
import { PlayerSkill } from '../types/game';
import { domainStore } from '../stores/domainStore';
const useTrainingStore = domainStore(developmentService.training);
export function TrainingScreen() {
  const { data, loading, error, load } = useTrainingStore();
  const action = useAction();
  const [skill, setSkill] = useState<PlayerSkill>('passing');
  useEffect(() => { void load(); }, [load]);
  return <GamePage loading={loading || action.busy} error={action.error || error}>
    <Button title="Atualizar treinamento" onPress={() => void load()} />
    <Text>A cada 100 treinos, a habilidade escolhida pode ganhar um ponto. A força geral acompanha as habilidades.</Text>
    <Choices values={['goalkeeping', 'speed', 'technique', 'passing', 'tackling', 'playmaking', 'finishing']} value={skill} onChange={value => setSkill(value as PlayerSkill)} />
    {data?.map(player => <View key={player.id} style={{ gap: 6 }}>
      <Text>{player.name} · {player.position} · {player.age} anos</Text>
      <Text>Força: {player.strength ?? player.overall} · Treino: {player.training_progress ?? 0}/100</Text>
      {player.can_train === false && <Text>Jogador indisponível ou no limite de desenvolvimento.</Text>}
      <Button title={`Treinar ${player.name}`} disabled={action.busy || loading || player.can_train === false}
        onPress={() => void action.run(async () => { await developmentService.train(player.id, skill); await load(); })} />
    </View>)}
    {data?.length === 0 && <Text>Nenhum jogador disponível.</Text>}
  </GamePage>;
}
