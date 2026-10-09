import { useEffect, useState } from 'react';
import { Text } from 'react-native';
import { Ticketing } from '../types/game';
import { financeService } from '../services/financeService';
import { ActionButton as Button, Field, GamePage, cents, money, useAction } from '../components/GameUI';
export function TicketingScreen() {
  const [data, setData] = useState<Ticketing | null>(null), [price, setPrice] = useState('');
  const action = useAction();
  async function load() { const result = await financeService.tickets(); setData(result); setPrice(String(result.price / 100)); }
  useEffect(() => { void action.run(load); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const entered = Number(price.replace(',', '.')) * 100;
  const estimate = data ? Math.max(0, Math.min(data.capacity, Math.round((data.supporters ?? 1000) * (data.attendance_share ?? .1) * (.4 + .8 * (data.fan_satisfaction ?? 50) / 100) * (1 + (data.reputation ?? 10) / 200) * Math.min(1.5, 2000 / Math.max(500, entered))))) : 0;
  return <GamePage loading={action.busy} error={action.error}><Text>Capacidade: {data?.capacity} · Renda: {money(data?.income ?? 0)}</Text><Field label="Preço do ingresso (R$)" value={price} onChange={setPrice} numeric /><Text>Público estimado com este preço: {Number.isFinite(estimate) ? estimate : 0} pessoas</Text><Text>Preços mais altos reduzem a procura. A capacidade limita o público.</Text><Button title="Salvar preço" disabled={action.busy} onPress={() => void action.run(async () => { await financeService.price(cents(price)); await load(); })} /><Text>Histórico de público</Text>{!data?.history.length && <Text>Nenhuma partida disputada.</Text>}{data?.history.map(h => <Text key={h.id}>{h.attendance} pessoas · {money(h.income)}</Text>)}</GamePage>;
}
