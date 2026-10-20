import { act, render, screen, fireEvent, waitFor } from '@testing-library/react-native';
import { NavigationContext, NavigationProp, ParamListBase } from '@react-navigation/native';
import { BankScreen } from '../screens/BankScreen';
import { SponsorsScreen } from '../screens/SponsorsScreen';
import { useBankStore, useSponsorsStore, useTicketingStore } from '../stores/screenStores';
import { CupSummary } from '../components/CupSummary';
import { FinanceScreen } from '../screens/FinanceScreen';
import { TicketingScreen } from '../screens/TicketingScreen';
import { cupService } from '../services/cupService';
import { financeService } from '../services/financeService';
import { useFinanceStore } from '../stores/financeStore';
jest.mock('../services/cupService', () => ({ cupService: { get: jest.fn() } }));
jest.mock('../services/financeService', () => ({ financeService: { get: jest.fn(), tickets: jest.fn(), price: jest.fn(), bank: jest.fn(), loan: jest.fn(), settleLoan: jest.fn(), settle: jest.fn(), sponsors: jest.fn(), sponsor: jest.fn(), terminateSponsor: jest.fn() } }));
beforeEach(() => { jest.clearAllMocks(); useFinanceStore.getState().reset(); useTicketingStore.getState().reset(); useBankStore.getState().reset(); useSponsorsStore.getState().reset(); jest.mocked(financeService.get).mockResolvedValue({ balance: 0, transactions: [] }); });

test('cup shows phase, result and report navigation', async () => {
  jest.mocked(cupService.get).mockResolvedValue({ competition: { id: 'cup', name: 'Copa Nacional', status: 'active' }, entry: { phase: 'Semifinal', status: 'active' }, matches: [{ id: 'match', phase: 'Quartas de final', date: '2026-01-01T00:00:00Z', status: 'completed', home_goals: 2, away_goals: 1 }] });
  const report = jest.fn(); await render(<CupSummary report={report} />);
  await screen.findByText('Copa Nacional · Semifinal · Em disputa');
  expect(screen.queryByRole('button', { name: 'Atualizar copa' })).toBeNull();
  await fireEvent.press(screen.getByText('Relatório · Quartas de final'));
  expect(report).toHaveBeenCalledWith('match');
});

test('finance shows monthly revenue, result and payroll health', async () => {
  jest.mocked(financeService.get).mockResolvedValue({ balance: 10150000, transactions: [], monthly_fixed_revenue: 1500000, monthly_income: 1500000, monthly_payroll: 1350000, sponsorship: 500000, tv_rights: 1000000, monthly_result: 150000, payroll_health: 'atenção', accumulated_prizes: 8000000 });
  await render(<FinanceScreen />);
  await screen.findByText(/Receita fixa mensal:/);
  expect(screen.getByText(/Receita fixa mensal:/)).toHaveTextContent(/15\.000/);
  expect(screen.getByText(/Resultado mensal:/)).toHaveTextContent(/1\.500/);
  expect(screen.getByText(/Premiação acumulada:/)).toHaveTextContent(/80\.000/);
  await fireEvent.press(screen.getByRole('tab', { name: 'Folha de pagamento' }));
  expect(screen.getByText('Saúde da folha: atenção')).toBeTruthy();
});


test('ticketing displays last match, projection and revenue without price controls', async () => {
  const match = { id: 'last', date: '2026-10-20T15:00:00Z', status: 'completed', home_name: 'Aurora', away_name: 'Estrela', home_goals: 2, away_goals: 1 };
  jest.mocked(financeService.tickets).mockResolvedValue({ price: 2000, capacity: 1000, income: 100000, history: [{ id: 'gate', attendance: 50, income: 100000, match }], next_match: { ...match, id: 'next', status: 'scheduled', home_goals: null, away_goals: null }, estimated_attendance: 70, estimated_income: 140000 });
  await render(<TicketingScreen />);
  await screen.findByText('Público estimado: 70 pessoas');
  expect(screen.getByText('Faturamento estimado: R$ 1.400,00')).toBeTruthy();
  expect(screen.getAllByText('Placar: 2 × 1')).toHaveLength(2);
  expect(screen.queryByLabelText('Preço do ingresso (R$)')).toBeNull();
  expect(screen.queryByRole('button', { name: 'Salvar preço' })).toBeNull();
  expect(financeService.price).not.toHaveBeenCalled();
});

test('ticketing refresh updates revenue and keeps empty state informative', async () => {
  const tickets = { price: 2000, capacity: 1000, income: 0, history: [] };
  jest.mocked(financeService.tickets).mockResolvedValueOnce(tickets).mockResolvedValueOnce({ ...tickets, income: 100000 });
  await render(<TicketingScreen />);
  await screen.findByText('Nenhum jogo em casa agendado.');
  await act(async () => { await useTicketingStore.getState().refresh(); });
  expect(screen.getByText(/Faturamento acumulado:/)).toHaveTextContent(/1\.000/);
});

test('payroll lists monthly salaries and opens the player contract', async () => {
  const navigate = jest.fn();
  const navigation = { navigate, isFocused: () => true, addListener: () => () => {} } as unknown as NavigationProp<ParamListBase>;
  jest.mocked(financeService.get).mockResolvedValue({ balance: 0, transactions: [], monthly_payroll: 120000, salary_costs: [{ player_id: 'player', name: 'João', salary: 120000, expires_at: '2027-01-01', status: 'active' }] });
  await render(<NavigationContext.Provider value={navigation}><FinanceScreen /></NavigationContext.Provider>);
  await fireEvent.press(screen.getByRole('tab', { name: 'Folha de pagamento' }));
  await screen.findByText('João');
  expect(screen.getByText(/Folha mensal:/)).toHaveTextContent(/1\.200/);
  await fireEvent.press(screen.getByRole('button', { name: 'Abrir contrato de João' }));
  expect(navigate).toHaveBeenCalledWith('PlayerNegotiation', { id: 'player' });
});

test('bank selects repayment terms and submits a partial early payment', async () => {
  jest.mocked(financeService.bank).mockResolvedValue({ contracts: [], rules: {}, credit_limit: 300000, products: { short_term: { installments: 3, interest_rate: .09 }, medium_term: { installments: 6, interest_rate: .18 } }, loans: [{ id: 'loan', product: 'short_term', principal: 100000, installments: 3, interest_rate: .09, installment_value: 36334, remaining_balance: 109000, status: 'active' }] });
  await render(<BankScreen />);
  await screen.findByText('Crédito disponível');
  await fireEvent.changeText(screen.getByLabelText('Valor do empréstimo (R$)'), '1000');
  await fireEvent.press(screen.getByRole('combobox', { name: 'Condições de pagamento' }));
  await fireEvent.press(screen.getByText('Médio prazo · 6 parcelas · 18% de juros'));
  await fireEvent.press(screen.getByRole('button', { name: 'Solicitar empréstimo' }));
  await waitFor(() => expect(financeService.loan).toHaveBeenCalledWith('medium_term', 100000));
  await waitFor(() => expect(financeService.bank).toHaveBeenCalledTimes(2));
  await fireEvent.changeText(screen.getByLabelText('Valor para antecipar (R$) · Curto prazo'), '200');
  await fireEvent.press(screen.getByText('Antecipar pagamento'));
  await waitFor(() => expect(financeService.settleLoan).toHaveBeenCalledWith('loan', 20000));
});

test('inherited sponsorship can be terminated and then replaced', async () => {
  const contract = { id: 'sponsor', name: 'Parceiro bot', status: 'active', value: 500000, ends_at: '2027-01-01', can_terminate: true };
  const offer = { id: 'offer', name: 'Novo parceiro', value: 500000, duration_days: 30, required_ranking: 0 };
  jest.mocked(financeService.sponsors).mockResolvedValueOnce({ contracts: [contract], offers: [offer] }).mockResolvedValue({ contracts: [{ ...contract, status: 'terminated', can_terminate: false }], offers: [offer] });
  await render(<SponsorsScreen />);
  await fireEvent.press(await screen.findByText('Encerrar patrocínio herdado'));
  await waitFor(() => expect(financeService.terminateSponsor).toHaveBeenCalledWith('sponsor'));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Aceitar patrocínio' })).toBeEnabled());
});
