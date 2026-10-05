import { useEffect, useState } from 'react';
import { Button, Text } from 'react-native';
import { Ticketing } from '../types/game';
import { financeService } from '../services/financeService';
import { Field, GamePage, cents, money, useAction } from '../components/GameUI';
export function TicketingScreen() {
  const [data, setData] = useState<Ticketing | null>(null), [price, setPrice] = useState('');
  const action = useAction();
  async function load() { const result = await financeService.tickets(); setData(result); setPrice(String(result.price / 100)); }
  useEffect(() => { void action.run(load); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}><Button title="Atualizar bilheteria" onPress={() => void action.run(load)} /><Text>Capacidade: {data?.capacity} · Renda: {money(data?.income ?? 0)}</Text><Field label="Preço do ingresso (R$)" value={price} onChange={setPrice} numeric /><Button title="Salvar preço" disabled={action.busy} onPress={() => void action.run(async () => { await financeService.price(cents(price)); await load(); })} /><Text>Histórico de público</Text>{!data?.history.length && <Text>Nenhuma partida disputada.</Text>}{data?.history.map(h => <Text key={h.id}>{h.attendance} pessoas · {money(h.income)}</Text>)}</GamePage>;
}
