import { render, screen, fireEvent, waitFor } from '@testing-library/react-native';
import { CupSummary } from '../components/CupSummary';
import { FinanceScreen } from '../screens/FinanceScreen';
import { TicketingScreen } from '../screens/TicketingScreen';
import { cupService } from '../services/cupService';
import { financeService } from '../services/financeService';
import { useFinanceStore } from '../stores/financeStore';
jest.mock('../services/cupService', () => ({ cupService: { get: jest.fn() } }));
jest.mock('../services/financeService', () => ({ financeService: { get: jest.fn(), tickets: jest.fn(), price: jest.fn() } }));
beforeEach(() => { jest.clearAllMocks(); useFinanceStore.getState().reset(); });

test('cup shows phase, result and report navigation', async () => {
  jest.mocked(cupService.get).mockResolvedValue({ competition: { id: 'cup', name: 'Copa Nacional', status: 'active' }, entry: { phase: 'Semifinal', status: 'active' }, matches: [{ id: 'match', phase: 'Quartas de final', date: '2026-01-01T00:00:00Z', status: 'completed', home_goals: 2, away_goals: 1 }] });
  const report = jest.fn(); await render(<CupSummary report={report} />);
  await screen.findByText('Copa Nacional · Semifinal · Em disputa');
  await fireEvent.press(screen.getByText('Relatório · Quartas de final'));
  expect(report).toHaveBeenCalledWith('match');
});

test('finance shows monthly revenue, result and payroll health', async () => {
  jest.mocked(financeService.get).mockResolvedValue({ balance: 10150000, transactions: [], monthly_fixed_revenue: 1500000, monthly_income: 1500000, monthly_payroll: 1350000, sponsorship: 500000, tv_rights: 1000000, monthly_result: 150000, payroll_health: 'atenção', accumulated_prizes: 8000000 });
  await render(<FinanceScreen />);
  await screen.findByText('Saúde da folha: atenção');
  expect(screen.getByText(/Receita fixa mensal:/)).toHaveTextContent(/15\.000/);
  expect(screen.getByText(/Resultado mensal:/)).toHaveTextContent(/1\.500/);
  expect(screen.getByText(/Premiação acumulada:/)).toHaveTextContent(/80\.000/);
});

test('ticket price previews reduced demand and respects capacity', async () => {
  jest.mocked(financeService.tickets).mockResolvedValue({ price: 2000, capacity: 1000, income: 0, history: [], supporters: 20000, fan_satisfaction: 50, reputation: 10 });
  await render(<TicketingScreen />);
  await screen.findByText('Público estimado com este preço: 1000 pessoas');
  await fireEvent.changeText(screen.getByLabelText('Preço do ingresso (R$)'), '500');
  await waitFor(() => expect(screen.getByText('Público estimado com este preço: 67 pessoas')).toBeTruthy());
});
