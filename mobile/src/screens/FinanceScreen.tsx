import { NavigationContext, NavigationProp } from '@react-navigation/native';
import { RootStackParamList } from '../navigation/types';
import { useScreenRefresh } from '../components/useScreenRefresh';
import { useContext, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useFinanceStore } from '../stores/financeStore';
import { ScreenTabs } from '../components/ScreenTabs';
import { Card, GamePage, money, palette } from '../components/GameUI';
import { BankScreen } from './BankScreen';
import { TicketingScreen } from './TicketingScreen';
import { SponsorsScreen } from './SponsorsScreen';
const categories: Record<string, string> = { sponsorship: 'Patrocínio', tv_rights: 'Direitos de TV', ticket_income: 'Bilheteria', ticketing: 'Bilheteria', prize: 'Premiações', salary: 'Salários', player_salary: 'Salários dos jogadores', transfer: 'Transferências', transfer_purchase: 'Compra de jogadores', transfer_sale: 'Venda de jogadores', loan: 'Empréstimos', bank_loan: 'Crédito bancário', bank_settlement: 'Pagamento bancário', loan_installment: 'Parcelas bancárias', loan_settlement: 'Antecipação bancária', stadium_upgrade: 'Obras do estádio', loan_fee: 'Empréstimo de jogadores', sponsor_bonus: 'Bônus de patrocínio', other_income: 'Outras receitas', other_expense: 'Outras despesas', bank_interest: 'Juros bancários', training: 'Treinamento', stadium: 'Estádio' };
export function FinanceScreen() {
  const navigation = useContext(NavigationContext) as NavigationProp<RootStackParamList> | undefined;
  const store = useFinanceStore(), [tab, setTab] = useState('Resumo');
  useScreenRefresh(store.ensure, store.refresh, tab === 'Resumo' || tab === 'Folha de pagamento');
  const data = store.data;
  const breakdown = (label: string, rows: { category: string; amount: number }[] | undefined, total: number) => <View style={{ gap: 8 }}>
    <Text style={{ fontWeight: '800', color: palette.ink }}>{label}: {money(total)}</Text>
    {rows?.slice().sort((a, b) => (categories[a.category] ?? a.category).localeCompare(categories[b.category] ?? b.category, 'pt-BR')).map(row => <View key={row.category} style={{ flexDirection: 'row', gap: 8, justifyContent: 'space-between' }}><Text style={{ flex: 1, color: palette.muted }}>{categories[row.category] ?? row.category.replace(/_/g, ' ')}</Text><Text>{money(row.amount)}</Text></View>)}
    {rows?.length === 0 && <Text style={{ color: palette.muted }}>Nenhuma {label === 'Entradas' ? 'entrada' : 'saída'} neste mês.</Text>}
  </View>;
  return <View style={{ flex: 1 }}><ScreenTabs scrollable values={['Resumo', 'Folha de pagamento', 'Banco', 'Bilheteria', 'Patrocinadores']} value={tab} onChange={setTab} />
    {tab === 'Resumo' ? <GamePage loading={store.loading} error={store.error}><Card>
      <Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Balanço do mês</Text>
      <Text style={{ fontSize: 24, fontWeight: '800', color: (data?.balance ?? 0) < 0 ? '#dc2626' : '#1d4ed8' }}>Saldo: {money(data?.balance ?? 0)}</Text>
      <View testID="finance-income" style={{ backgroundColor: 'rgba(37, 99, 235, 0.5)', padding: 16, borderRadius: 14 }}>{breakdown('Entradas', data?.income_details, data?.monthly_income ?? 0)}</View>
      <View testID="finance-expenses" style={{ backgroundColor: 'rgba(249, 115, 22, 0.5)', padding: 16, borderRadius: 14 }}>{breakdown('Saídas', data?.expense_details, data?.monthly_expenses ?? 0)}</View>
      <View testID="finance-totals" style={{ backgroundColor: 'rgba(34, 197, 94, 0.5)', padding: 16, borderRadius: 14, gap: 8 }}>
      <Text style={{ fontWeight: '800', color: palette.ink }}>Totais</Text>
      <Text>Premiação acumulada: {money(data?.accumulated_prizes ?? 0)}</Text>
      <Text>Receita fixa mensal: {money(data?.monthly_fixed_revenue ?? 0)}</Text>
      <Text style={{ fontWeight: '800' }}>Resultado mensal: {money(data?.monthly_result ?? 0)}</Text>
      </View>
    </Card></GamePage> : tab === 'Folha de pagamento' ? <GamePage loading={store.loading} error={store.error}><Card>
      <Text style={{ fontSize: 22, fontWeight: '800', color: palette.ink }}>Folha de pagamento</Text>
      <Text>Saúde da folha: {data?.payroll_health ?? 'Em avaliação'}</Text>
      {data?.monthly_period_end && <Text>Período financeiro até {new Date(data.monthly_period_end).toLocaleDateString('pt-BR')}</Text>}
      <Text>Folha mensal: {money(data?.monthly_payroll ?? 0)}</Text><Text>Custo restante dos contratos: {money(data?.total_contract_cost ?? 0)}</Text>
      <Text>Uma temporada tem 12 meses do jogo. Salários são debitados automaticamente e podem deixar o saldo negativo.</Text>
    </Card><Card><Text style={{ fontSize: 20, fontWeight: '700', color: palette.ink }}>Detalhamento da folha</Text>
      {data?.salary_costs?.map(cost => <View key={cost.player_id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, borderBottomWidth: 1, borderColor: palette.border, paddingVertical: 10 }}>
        <Text accessibilityLabel={`Camisa de ${cost.name}`} style={{ width: 32, fontWeight: '700' }}>{cost.shirt_number ?? '—'}</Text>
        <Text accessibilityLabel={`Posição de ${cost.name}`} style={{ width: 28, fontSize: 12 }}>{({ GK: 'GOL', CB: 'ZAG', FB: 'LAT', MID: 'MED', ATT: 'ATA' } as Record<string, string>)[cost.position ?? ''] ?? cost.position ?? '—'}</Text>
        <Text style={{ flex: 1, color: palette.ink }}>{cost.name}</Text><Text>{money(cost.salary)}/mês</Text>
        <Pressable accessibilityRole="button" accessibilityLabel={`Abrir contrato de ${cost.name}`} onPress={() => navigation?.navigate('PlayerNegotiation', { id: cost.player_id })} hitSlop={8}><Text style={{ fontSize: 24 }}>📄</Text></Pressable>
      </View>)}
    </Card></GamePage> : tab === 'Banco' ? <BankScreen /> : tab === 'Bilheteria' ? <TicketingScreen /> : <SponsorsScreen />}
  </View>;
}
