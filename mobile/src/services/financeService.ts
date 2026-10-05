import { apiRequest } from './apiClient';
import { Finance, Bank, Ticketing, Sponsors, Contract } from '../types/game';
export const financeService = {
  get: () => apiRequest<Finance>('/finance'),
  bank: () => apiRequest<Bank>('/finance/bank'),
  contract: (type: 'investment' | 'bank_loan', amount: number) => apiRequest<Contract>(`/finance/bank/${type}`, { method: 'POST', body: JSON.stringify({ amount }) }),
  settle: (id: string) => apiRequest<Contract>(`/finance/contracts/${id}/settle`, { method: 'POST' }),
  tickets: () => apiRequest<Ticketing>('/finance/tickets'),
  price: (price: number) => apiRequest<Ticketing>('/finance/tickets', { method: 'PUT', body: JSON.stringify({ price }) }),
  sponsors: () => apiRequest<Sponsors>('/finance/sponsors'),
  sponsor: (id: string) => apiRequest(`/finance/sponsors/${id}/accept`, { method: 'POST' }),
};
