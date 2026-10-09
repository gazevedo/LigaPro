import { useScreenRefresh } from '../components/useScreenRefresh';
import { useTicketingStore } from '../stores/screenStores';
import { useState } from 'react';
import { Text } from 'react-native';
import { financeService } from '../services/financeService';
import { ActionButton as Button, Field, GamePage, cents, money, useAction } from '../components/GameUI';
export function TicketingScreen() {
  const store = useTicketingStore(), { data, loading, error, ensure } = store;
  const [price, setPrice] = useState<string | null>(() => data ? String(data.price / 100) : null);
  const action = useAction();
  async function load() { await store.load(); const result = useTicketingStore.getState().data; if (result) setPrice(String(result.price / 100)); }
  useScreenRefresh(ensure, store.refresh);
  const displayedPrice = price ?? (data ? String(data.price / 100) : '');
  const entered = Number(displayedPrice.replace(',', '.')) * 100;
  const estimate = data ? Math.max(0, Math.min(data.capacity, Math.round((data.supporters ?? 1000) * (data.attendance_share ?? .1) * (.4 + .8 * (data.fan_confidence ?? data.fan_satisfaction ?? 50) / 100) * (1 + (data.reputation ?? 10) / 200) * Math.min(1.5, 2000 / Math.max(500, entered))))) : 0;
  return <GamePage loading={loading || action.busy} error={action.error || error}><Text>Capacidade: {data?.capacity} · Renda: {money(data?.income ?? 0)}</Text><Field label="Preço do ingresso (R$)" value={displayedPrice} onChange={setPrice} numeric /><Text>Público estimado com este preço: {Number.isFinite(estimate) ? estimate : 0} pessoas</Text><Text>Preços mais altos reduzem a procura. A capacidade limita o público.</Text><Button title="Salvar preço" disabled={action.busy} onPress={() => void action.run(async () => { await financeService.price(cents(displayedPrice)); await load(); })} /><Text>Histórico de público</Text>{!data?.history.length && <Text>Nenhuma partida disputada.</Text>}{data?.history.map(h => <Text key={h.id}>{h.attendance} pessoas · {money(h.income)}</Text>)}</GamePage>;
}
