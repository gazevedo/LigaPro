import { useScreenRefresh } from '../components/useScreenRefresh';
import { useState } from 'react';
import { Text, View } from 'react-native';
import { useFinanceStore } from '../stores/financeStore';
import { ScreenTabs } from '../components/ScreenTabs';
import { Card, GamePage, money, palette } from '../components/GameUI';
import { BankScreen } from './BankScreen';
import { TicketingScreen } from './TicketingScreen';
import { SponsorsScreen } from './SponsorsScreen';
export function FinanceScreen() {
  const store = useFinanceStore(), [tab, setTab] = useState('Resumo');
  useScreenRefresh(store.ensure, store.refresh, tab === 'Resumo');
  return <View style={{ flex: 1 }}><ScreenTabs values={['Resumo', 'Banco', 'Bilheteria', 'Patrocinadores']} value={tab} onChange={setTab} />
    {tab === 'Resumo' ? <GamePage loading={store.loading} error={store.error}>
      <View style={{ backgroundColor: '#183f63', borderRadius: 24, padding: 24, gap: 12, borderWidth: 2, borderColor: '#142f4c', boxShadow: '0 5px 0 #abc3d3' }}><Text style={{ color: '#bfe0f1', fontWeight: '800', letterSpacing: 2 }}>CAIXA DO CLUBE</Text><Text style={{ color: '#fff', fontSize: 28, fontWeight: '800' }}>Saldo: {money(store.data?.balance ?? 0)}</Text><Text style={{ color: '#bfe0f1' }}>Acompanhamento do mês atual</Text></View>
      {[
        { label: 'Entradas', value: store.data?.monthly_income ?? 0, color: '#daf4e7' },
        { label: 'Saídas', value: store.data?.monthly_expenses ?? 0, color: '#ffe5df' },
        { label: 'Resultado mensal', value: store.data?.monthly_result ?? 0, color: '#fff2c1' },
        { label: 'Premiação acumulada', value: store.data?.accumulated_prizes ?? 0, color: '#e8e0fc' },
      ].map(metric => <View key={metric.label} style={{ borderRadius: 18, borderWidth: 2, borderColor: palette.border, padding: 20, backgroundColor: metric.color }}><Text style={{ fontWeight: '800', color: palette.ink }}>{metric.label}: {money(metric.value)}</Text></View>)}
      <Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Balanço do mês</Text>
      {[{ label: 'Entradas', value: store.data?.monthly_income ?? 0, color: '#269573' }, { label: 'Saídas', value: store.data?.monthly_expenses ?? 0, color: '#e07162' }].map(metric => <View key={metric.label} style={{ gap: 8 }}><Text>{metric.label}: {money(metric.value)}</Text><View style={{ backgroundColor: '#edf2f8', height: 14, borderRadius: 8 }}><View style={{ height: 14, borderRadius: 8, backgroundColor: metric.color, width: `${Math.max(0, metric.value) / Math.max(store.data?.monthly_income ?? 0, store.data?.monthly_expenses ?? 0, 1) * 100}%` }} /></View></View>)}
      <Text>Receita fixa mensal: {money(store.data?.monthly_fixed_revenue ?? 0)}</Text><Text>Faturamento mensal: {money(store.data?.monthly_income ?? 0)}</Text><Text>Patrocínio: {money(store.data?.sponsorship ?? 0)} · TV: {money(store.data?.tv_rights ?? 0)}</Text><Text>Bilheteria mensal: {money(store.data?.ticketing ?? 0)}</Text><Text>Outras despesas: {money(store.data?.other_expenses ?? 0)}</Text></Card><Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Folha e contratos</Text><Text>Saúde da folha: {store.data?.payroll_health ?? 'Em avaliação'}</Text>{store.data?.monthly_period_end && <Text>Período financeiro até {new Date(store.data.monthly_period_end).toLocaleDateString('pt-BR')}</Text>}<Text>Folha mensal: {money(store.data?.monthly_payroll ?? 0)}</Text><Text>Custo restante dos contratos: {money(store.data?.total_contract_cost ?? 0)}</Text><Text>Uma temporada tem 12 meses do jogo. Salários são debitados automaticamente e podem deixar o saldo negativo.</Text>{store.data?.salary_costs?.map(cost => <Text key={cost.player_id}>{cost.name} · salário mensal {money(cost.salary)} · até {new Date(cost.expires_at).toLocaleDateString('pt-BR')}{cost.status === 'expiring' ? ' · Próximo do fim' : ''}</Text>)}</Card><Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Histórico salarial</Text>{store.data?.salary_history?.map(t => <Text key={t.id}>{new Date(t.created_at).toLocaleDateString('pt-BR')} · {money(t.amount)}</Text>)}</Card><Card><Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Movimentações</Text>{store.data?.transactions.map(t => <Text key={t.id}>{new Date(t.created_at).toLocaleDateString('pt-BR')} · {t.category}: {money(t.amount)}</Text>)}</Card></GamePage> : tab === 'Banco' ? <BankScreen /> : tab === 'Bilheteria' ? <TicketingScreen /> : <SponsorsScreen />}
  </View>;
}
