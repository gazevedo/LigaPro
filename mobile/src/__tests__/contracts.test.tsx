import { render, fireEvent, screen, waitFor } from '@testing-library/react-native';
import { NativeStackScreenProps } from '@react-navigation/native-stack';
import { RootStackParamList } from '../navigation/types';
import { PlayerDetailsScreen } from '../screens/PlayerDetailsScreen';
import { FinanceScreen } from '../screens/FinanceScreen';
import { MarketScreen } from '../screens/MarketScreen';
import { contractService } from '../services/contractService';
import { marketService } from '../services/marketService';
import { financeService } from '../services/financeService';
import { useFinanceStore } from '../stores/financeStore';
import { useMarketStore } from '../stores/marketStore';
jest.mock('../services/contractService', () => ({ contractService: { get: jest.fn(), renew: jest.fn(), sign: jest.fn() } }));
jest.mock('../services/marketService', () => ({ marketService: { player: jest.fn(), search: jest.fn(), mine: jest.fn() } }));
jest.mock('../services/financeService', () => ({ financeService: { get: jest.fn() } }));
jest.mock('../stores/clubStore', () => ({ useClubStore: (select: (state: { data: { club: { id: string } } }) => unknown) => select({ data: { club: { id: 'club1' } } }) }));
const player = { id: 'p1', name: 'Pedro', position: 'ATT', age: 22, overall: 50, value: 10000, country_id: 'BR', owner_club_id: 'club1', current_club_id: 'club1', status: 'active' };
const contract = { id: 'c1', player_id: 'p1', club_id: 'club1', salary: 5000, started_at: '2026-01-01T12:00:00Z', expires_at: '2027-01-01T12:00:00Z', status: 'active' } as const;
function props() { return { route: { params: { id: 'p1' } }, navigation: { navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'PlayerDetails'>; }
beforeEach(() => {
  jest.clearAllMocks(); useFinanceStore.getState().reset(); useMarketStore.getState().reset();
  jest.mocked(marketService.player).mockResolvedValue(player);
  jest.mocked(contractService.get).mockResolvedValue({ contract, history: [] });
  jest.mocked(contractService.renew).mockResolvedValue(contract);
  jest.mocked(contractService.sign).mockResolvedValue(contract);
  jest.mocked(marketService.search).mockResolvedValue([]);
  jest.mocked(marketService.mine).mockResolvedValue({ listings: [], incoming: [], outgoing: [], loans: [] });
});
test('renews with salary in cents and duration in seasons', async () => {
  await render(<PlayerDetailsScreen {...props()} />);
  await screen.findByText('Renovar contrato');
  await fireEvent.changeText(screen.getByLabelText('Salário mensal (R$)'), '75,50');
  await fireEvent.changeText(screen.getByLabelText('Duração (temporadas, 1–5)'), '3');
  await fireEvent.press(screen.getByText('Renovar contrato'));
  await waitFor(() => expect(contractService.renew).toHaveBeenCalledWith('p1', { salary: 7550, seasons: 3 }));
});
test('signs a free player without navigating to missing clubs', async () => {
  jest.mocked(marketService.player).mockResolvedValueOnce({ ...player, status: 'free_agent', owner_club_id: null, current_club_id: null });
  await render(<PlayerDetailsScreen {...props()} />);
  await screen.findByText('Contratar jogador livre');
  expect(screen.queryByText('Clube proprietário')).toBeNull();
  expect(screen.queryByText('Clube atual')).toBeNull();
  await fireEvent.changeText(screen.getByLabelText('Salário mensal (R$)'), '50');
  await fireEvent.press(screen.getByText('Contratar jogador livre'));
  await waitFor(() => expect(contractService.sign).toHaveBeenCalledWith('p1', { salary: 5000, seasons: 2 }));
  await screen.findByText('Renovar contrato');
});
test('rejects invalid duration and displays financial rejection', async () => {
  await render(<PlayerDetailsScreen {...props()} />);
  await screen.findByText('Renovar contrato');
  await fireEvent.changeText(screen.getByLabelText('Duração (temporadas, 1–5)'), '6');
  await fireEvent.press(screen.getByText('Renovar contrato'));
  await screen.findByText('Informe uma duração de 1 a 5 temporadas.');
  expect(contractService.renew).not.toHaveBeenCalled();
  jest.mocked(contractService.renew).mockRejectedValue(new Error('Saldo insuficiente para a nova folha mensal.'));
  await fireEvent.changeText(screen.getByLabelText('Duração (temporadas, 1–5)'), '2');
  await fireEvent.press(screen.getByText('Renovar contrato'));
  await screen.findByText('Saldo insuficiente para a nova folha mensal.');
});
test('finance displays payroll, individual cost and salary history', async () => {
  jest.mocked(financeService.get).mockResolvedValue({ balance: 10000, transactions: [], monthly_payroll: 5000, total_contract_cost: 120000, salary_costs: [{ player_id: 'p1', name: 'Pedro', salary: 5000, expires_at: contract.expires_at, status: 'expiring' }], salary_history: [{ id: 'payment1', amount: -5000, category: 'player_salary', created_at: '2026-01-01T12:00:00Z' }] });
  await render(<FinanceScreen />);
  await screen.findByText(/Pedro · salário mensal/);
  expect(screen.getByText(/Folha mensal:/)).toBeTruthy();
  expect(screen.getByText(/Custo restante dos contratos:/)).toBeTruthy();
  expect(screen.getByText('Histórico salarial')).toBeTruthy();
});
test('market filters free players', async () => {
  const input = { navigation: { navigate: jest.fn() } } as unknown as NativeStackScreenProps<RootStackParamList, 'Market'>;
  await render(<MarketScreen {...input} />);
  await waitFor(() => expect(marketService.search).toHaveBeenCalled());
  await fireEvent.press(screen.getByText('Jogadores livres'));
  await waitFor(() => expect(marketService.search).toHaveBeenLastCalledWith({ status: 'free_agent' }));
});

test('player profile displays morale band and only the potential hint', async () => {
  jest.mocked(marketService.player).mockResolvedValue({ ...player, morale: 15 });
  await render(<PlayerDetailsScreen {...props()} />);
  await screen.findByText('Moral: 15/100 · Muito baixa');
  expect(screen.queryByText(/Potencial:/)).toBeNull();
  expect(screen.getByText(/Condição: 100\/100/)).toBeTruthy();
});
