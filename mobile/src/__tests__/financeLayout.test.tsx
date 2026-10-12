import { render, screen, fireEvent } from '@testing-library/react-native';
import { FinanceScreen } from '../screens/FinanceScreen';
import { BankScreen } from '../screens/BankScreen';
jest.mock('../components/useScreenRefresh', () => ({ useScreenRefresh: jest.fn() }));
jest.mock('../stores/financeStore', () => ({ useFinanceStore: () => ({ ensure: jest.fn(), data: { balance: 50000, monthly_income: 10000, monthly_expenses: 3000, income_details: [{ category: 'tv_rights', amount: 10000 }], expense_details: [{ category: 'player_salary', amount: 3000 }], monthly_payroll: 3000, salary_costs: [] } }) }));
jest.mock('../stores/screenStores', () => ({ useBankStore: () => ({ ensure: jest.fn(), data: { rules: { bank_loan_days: 30, bank_loan_interest_bps: 500, max_bank_loan: 500000 }, products: {}, contracts: [{ id: 'old', type: 'investment', amount: 10000, interest: 500, status: 'active', ends_at: '2026-12-01T00:00:00Z' }] } }) }));
test('balance contains detailed entries and expenses without separate history or payroll cards', async () => {
  await render(<FinanceScreen />);
  expect(screen.getByText('Direitos de TV')).toBeTruthy();
  expect(screen.getByText('Salários dos jogadores')).toBeTruthy();
  expect(screen.queryByText('Acompanhamento do mês atual')).toBeNull();
  expect(screen.queryByText('Movimentações')).toBeNull();
  expect(screen.queryByText(/Folha mensal:/)).toBeNull();
  await fireEvent.press(screen.getByRole('tab', { name: 'Folha e contratos' }));
  expect(screen.getByText(/Folha mensal:/)).toBeTruthy();
});
test('bank offers no investment action or investment contracts', async () => {
  await render(<BankScreen />);
  expect(screen.queryByText('Investir')).toBeNull();
  expect(screen.queryByText(/Investimento/)).toBeNull();
  expect(screen.getByText('Solicitar empréstimo bancário')).toBeTruthy();
});
