import { useScreenRefresh } from '../components/useScreenRefresh';
import { useState } from 'react';
import { Text, View } from 'react-native';
import { useFinanceStore } from '../stores/financeStore';
import { ScreenTabs } from '../components/ScreenTabs';
import { Card, GamePage, money, palette } from '../components/GameUI';
import { BankScreen } from './BankScreen';
import { TicketingScreen } from './TicketingScreen';
import { SponsorsScreen } from './SponsorsScreen';
const categories: Record<string, string> = { sponsorship: 'Patrocínio', tv_rights: 'Direitos de TV', ticket_income: 'Bilheteria', ticketing: 'Bilheteria', prize: 'Premiações', salary: 'Salários', player_salary: 'Salários dos jogadores', transfer: 'Transferências', transfer_purchase: 'Compra de jogadores', transfer_sale: 'Venda de jogadores', loan: 'Empréstimos', bank_loan: 'Crédito bancário', bank_settlement: 'Pagamento bancário', stadium_upgrade: 'Obras do estádio', loan_fee: 'Empréstimo de jogadores', sponsor_bonus: 'Bônus de patrocínio', other_income: 'Outras receitas', other_expense: 'Outras despesas', bank_interest: 'Juros bancários', training: 'Treinamento', stadium: 'Estádio' };
export function FinanceScreen() {
  const store = useFinanceStore(), [tab, setTab] = useState('Resumo');
  useScreenRefresh(store.ensure, store.refresh, tab === 'Resumo' || tab === 'Folha e contratos');
  const data = store.data;
  const breakdown = (label: string, rows: { category: string; amount: number }[] | undefined, total: number) => <View style={{ gap: 8 }}>
    <Text style={{ fontWeight: '800', color: palette.ink }}>{label}: {money(total)}</Text>
    {rows?.map(row => <View key={row.category} style={{ flexDirection: 'row', gap: 8, justifyContent: 'space-between' }}><Text style={{ flex: 1, color: palette.muted }}>{categories[row.category] ?? row.category.replace(/_/g, ' ')}</Text><Text>{money(row.amount)}</Text></View>)}
    {rows?.length === 0 && <Text style={{ color: palette.muted }}>Nenhuma {label === 'Entradas' ? 'entrada' : 'saída'} neste mês.</Text>}
  </View>;
  return <View style={{ flex: 1 }}><ScreenTabs scrollable values={['Resumo', 'Folha e contratos', 'Banco', 'Bilheteria', 'Patrocinadores']} value={tab} onChange={setTab} />
    {tab === 'Resumo' ? <GamePage loading={store.loading} error={store.error}><Card>
      <Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Balanço do mês</Text>
      <Text style={{ fontSize: 24, fontWeight: '800', color: palette.primary }}>Saldo: {money(data?.balance ?? 0)}</Text>
      {breakdown('Entradas', data?.income_details, data?.monthly_income ?? 0)}
      {breakdown('Saídas', data?.expense_details, data?.monthly_expenses ?? 0)}
      <Text style={{ fontWeight: '800' }}>Resultado mensal: {money(data?.monthly_result ?? 0)}</Text>
      <Text>Receita fixa mensal: {money(data?.monthly_fixed_revenue ?? 0)}</Text>
      <Text>Premiação acumulada: {money(data?.accumulated_prizes ?? 0)}</Text>
    </Card></GamePage> : tab === 'Folha e contratos' ? <GamePage loading={store.loading} error={store.error}><Card>
      <Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Folha de pagamento e contratos</Text>
      <Text>Saúde da folha: {data?.payroll_health ?? 'Em avaliação'}</Text>
      {data?.monthly_period_end && <Text>Período financeiro até {new Date(data.monthly_period_end).toLocaleDateString('pt-BR')}</Text>}
      <Text>Folha mensal: {money(data?.monthly_payroll ?? 0)}</Text><Text>Custo restante dos contratos: {money(data?.total_contract_cost ?? 0)}</Text>
      <Text>Uma temporada tem 12 meses do jogo. Salários são debitados automaticamente e podem deixar o saldo negativo.</Text>
      {data?.salary_costs?.map(cost => <Text key={cost.player_id}>{cost.name} · salário mensal {money(cost.salary)} · até {new Date(cost.expires_at).toLocaleDateString('pt-BR')}{cost.status === 'expiring' ? ' · Próximo do fim' : ''}</Text>)}
    </Card></GamePage> : tab === 'Banco' ? <BankScreen /> : tab === 'Bilheteria' ? <TicketingScreen /> : <SponsorsScreen />}
  </View>;
}
