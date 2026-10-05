import { useEffect, useState } from 'react';
import { Button, Text, View } from 'react-native';
import { Bank } from '../types/game';
import { financeService } from '../services/financeService';
import { Field, GamePage, cents, money, useAction } from '../components/GameUI';
export function BankScreen() {
  const [data, setData] = useState<Bank | null>(null), [amount, setAmount] = useState('');
  const action = useAction();
  async function load() { setData(await financeService.bank()); }
  useEffect(() => { void action.run(load); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <GamePage loading={action.busy} error={action.error}><Button title="Atualizar banco" onPress={() => void action.run(load)} />
    {data && <Text>Investimento: {data.rules.investment_days} dias, {data.rules.investment_interest_bps / 100}% por contrato. Empréstimo: {data.rules.bank_loan_days} dias, {data.rules.bank_loan_interest_bps / 100}% por contrato. Limite: {money(data.rules.max_bank_loan)}</Text>}
    <Field label="Valor (R$)" value={amount} onChange={setAmount} numeric />
    <Button title="Investir" disabled={action.busy} onPress={() => void action.run(async () => { await financeService.contract('investment', cents(amount)); await load(); })} />
    <Button title="Solicitar empréstimo bancário" disabled={action.busy} onPress={() => void action.run(async () => { await financeService.contract('bank_loan', cents(amount)); await load(); })} />
    {data?.contracts.map(c => <View key={c.id}><Text>{c.type === 'investment' ? 'Investimento' : 'Empréstimo'} · {money(c.amount)} + juros {money(c.interest)} · {c.status} {c.overdue ? '(vencido)' : ''} · {new Date(c.ends_at).toLocaleDateString('pt-BR')}</Text>{c.status === 'active' && <Button title={c.type === 'investment' ? 'Resgatar investimento vencido' : 'Quitar empréstimo'} disabled={action.busy} onPress={() => void action.run(async () => { await financeService.settle(c.id); await load(); })} />}</View>)}
  </GamePage>;
}
