import { apiRequest } from './apiClient';
import { Finance, Bank, Ticketing, Sponsors, Contract } from '../types/game';
export const financeService = {
  get: () => apiRequest<Finance>('/finance'),
  bank: () => apiRequest<Bank>('/finance/bank'),
  contract: (type: 'investment' | 'bank_loan', amount: number) => apiRequest<Contract>(`/finance/bank/${type}`, { method: 'POST', body: JSON.stringify({ amount }) }),
  loan: (product: string, amount: number) => apiRequest(`/finance/loans/${product}`, { method: 'POST', body: JSON.stringify({ amount }) }),
  settleLoan: (id: string, amount?: number) => apiRequest(`/finance/loans/${id}/settle`, { method: 'POST', ...(amount !== undefined ? { body: JSON.stringify({ amount }) } : {}) }),
  settle: (id: string, amount?: number) => apiRequest<Contract>(`/finance/contracts/${id}/settle`, { method: 'POST', ...(amount !== undefined ? { body: JSON.stringify({ amount }) } : {}) }),
  tickets: () => apiRequest<Ticketing>('/finance/tickets'),
  price: (price: number) => apiRequest<Ticketing>('/finance/tickets', { method: 'PUT', body: JSON.stringify({ price }) }),
  sponsors: () => apiRequest<Sponsors>('/finance/sponsors'),
  terminateSponsor: (id: string) => apiRequest(`/finance/sponsors/${id}/terminate`, { method: 'POST' }),
  sponsor: (id: string) => apiRequest(`/finance/sponsors/${id}/accept`, { method: 'POST' }),
};
