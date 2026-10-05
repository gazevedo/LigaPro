import { useEffect, useState } from 'react';
import { Button, Text, View } from 'react-native';
import { useFinanceStore } from '../stores/financeStore';
import { Choices, GamePage, money } from '../components/GameUI';
import { BankScreen } from './BankScreen';
import { TicketingScreen } from './TicketingScreen';
import { SponsorsScreen } from './SponsorsScreen';
export function FinanceScreen() {
  const store = useFinanceStore(), [tab, setTab] = useState('Resumo');
  const load = store.load;
  useEffect(() => { void load(); }, [load]);
  return <View style={{ flex: 1 }}><Choices values={['Resumo', 'Banco', 'Bilheteria', 'Patrocinadores']} value={tab} onChange={value => { setTab(value); if (value === 'Resumo') void load(); }} />
    {tab === 'Resumo' ? <GamePage loading={store.loading} error={store.error}><Button title="Atualizar resumo" onPress={() => void load()} /><Text>Saldo: {money(store.data?.balance ?? 0)}</Text><Text>Folha mensal: {money(store.data?.monthly_payroll ?? 0)}</Text><Text>Custo restante dos contratos: {money(store.data?.total_contract_cost ?? 0)}</Text><Text>Uma temporada tem 12 meses do jogo. Salários são debitados automaticamente e podem deixar o saldo negativo.</Text>{store.data?.salary_costs?.map(cost => <Text key={cost.player_id}>{cost.name} · salário mensal {money(cost.salary)} · até {new Date(cost.expires_at).toLocaleDateString('pt-BR')}{cost.status === 'expiring' ? ' · Próximo do fim' : ''}</Text>)}<Text>Histórico salarial</Text>{store.data?.salary_history?.map(t => <Text key={t.id}>{new Date(t.created_at).toLocaleDateString('pt-BR')} · {money(t.amount)}</Text>)}<Text>Movimentações</Text>{store.data?.transactions.map(t => <Text key={t.id}>{new Date(t.created_at).toLocaleDateString('pt-BR')} · {t.category}: {money(t.amount)}</Text>)}</GamePage> : tab === 'Banco' ? <BankScreen /> : tab === 'Bilheteria' ? <TicketingScreen /> : <SponsorsScreen />}
  </View>;
}
