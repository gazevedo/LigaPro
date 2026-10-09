import { useEffect } from 'react';
import { Text } from 'react-native';
import { ActionButton as Button, Card, GamePage, useAction } from '../components/GameUI';
import { developmentService } from '../services/developmentService';
import { domainStore } from '../stores/domainStore';
const useYouthStore = domainStore(developmentService.youth);
export function YouthAcademyScreen() {
  const { data, loading, error, load } = useYouthStore();
  const action = useAction();
  useEffect(() => { void load(); }, [load]);
  return <GamePage loading={loading || action.busy} error={action.error || error}>
    <Text>A cada temporada, escolha um dos três candidatos para a base. A promoção ocorre a partir dos 18 anos.</Text>
    {data?.map(player => <Card key={player.id}>
      <Text>{player.name} · {player.position} · {player.age} anos</Text>
      <Text>Força: {player.strength ?? player.overall} · CPE: {player.estimated_potential_capacity ?? 'Em avaliação'} · Treino: {player.training_progress ?? 0}/100</Text>
      {player.can_train === false && player.status !== 'candidate' && <Text>Limite de desenvolvimento atingido.</Text>}
      {player.status === 'candidate' ? <Button title={`Escolher ${player.name}`} disabled={action.busy || loading} onPress={() => void action.run(async () => { await developmentService.selectYouth(player.id); await load(); })} /> : <>
      <Button title={`Treinar ${player.name}`} disabled={action.busy || loading || player.can_train === false}
        onPress={() => void action.run(async () => { await developmentService.train(player.id); await load(); })} />
      <Button title={`Promover ${player.name}`} disabled={action.busy || loading || player.age < 18}
        onPress={() => void action.run(async () => { await developmentService.promote(player.id); await load(); })} />
      <Button title={`Dispensar ${player.name}`} disabled={action.busy || loading} onPress={() => void action.run(async () => { await developmentService.release(player.id); await load(); })} />
      </>}
    </Card>)}
    {data?.length === 0 && <Text>Nenhum jovem disponível.</Text>}
  </GamePage>;
}
