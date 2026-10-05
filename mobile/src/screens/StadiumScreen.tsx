import { useEffect } from 'react';
import { Button, Text, View } from 'react-native';
import { useStadiumStore } from '../stores/stadiumStore';
import { stadiumService } from '../services/stadiumService';
import { GamePage, money, useAction } from '../components/GameUI';
export function StadiumScreen() {
  const store = useStadiumStore(), action = useAction();
  const load = store.load;
  useEffect(() => { void load(); }, [load]);
  return <GamePage loading={store.loading || action.busy} error={action.error || store.error}><Button title="Atualizar estádio" onPress={() => void store.load()} /><Text>Capacidade: {store.data?.capacity}</Text>
    {Object.entries(store.data?.facilities ?? {}).map(([key, level]) => <View key={key}><Text>{store.data?.names[key]} · nível {level}</Text><Button title={`Melhorar ${store.data?.names[key]} — ${money(store.data?.upgrade_costs[key] ?? 0)}`} disabled={action.busy} onPress={() => void action.run(async () => { await stadiumService.upgrade(key); await store.load(); })} /></View>)}
  </GamePage>;
}
