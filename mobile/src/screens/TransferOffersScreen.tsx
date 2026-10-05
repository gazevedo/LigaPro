import { useEffect } from 'react';
import { Button, Text, View } from 'react-native';
import { useMarketStore } from '../stores/marketStore';
import { marketService } from '../services/marketService';
import { GamePage, money, useAction } from '../components/GameUI';
export function TransferOffersScreen() {
  const store = useMarketStore(), action = useAction();
  const load = store.load;
  useEffect(() => { void load(); }, [load]);
  return <GamePage loading={store.loading || action.busy} error={action.error || store.error}><Button title="Atualizar propostas" onPress={() => void store.load()} /><Text>Propostas recebidas</Text>{store.data?.incoming.map(o => <View key={o.id}><Text>{o.id} · {money(o.amount)} · {o.status}</Text>{o.status === 'pending' && <><Button title="Aceitar proposta" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.accept(o.id); await store.load(); })} /><Button title="Recusar proposta" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.cancelOffer(o.id); await store.load(); })} /></>}</View>)}<Text>Propostas enviadas</Text>{store.data?.outgoing.map(o => <View key={o.id}><Text>{o.id} · {money(o.amount)} · {o.status}</Text>{o.status === 'pending' && <Button title="Cancelar proposta" disabled={action.busy} onPress={() => void action.run(async () => { await marketService.cancelOffer(o.id); await store.load(); })} />}</View>)}</GamePage>;
}
