import { apiRequest } from '../services/apiClient';
import { stadiumService } from '../services/stadiumService';
import { Stadium } from '../types/game';
jest.mock('../services/apiClient', () => ({ apiRequest: jest.fn() }));
jest.mock('../stores/authStore', () => ({ useAuthStore: { getState: () => ({ user: { id: 'user' } }) } }));
jest.mock('../stores/clubStore', () => ({ useClubStore: { getState: () => ({ data: { club: { id: 'club' } } }) } }));
const initial: Stadium = { capacity: 10000, ticket_price: 2000, facilities: {}, names: {}, upgrade_costs: {} };
beforeEach(() => jest.clearAllMocks());
test('all stadium writes execute in the order selected, including sector edits', async () => {
  let finish!: (value: Stadium) => void;
  jest.mocked(apiRequest).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce(initial);
  const first = stadiumService.price('lower_north', 3000);
  const second = stadiumService.price('lower_north', 4000);
  await Promise.resolve();
  expect(apiRequest).toHaveBeenCalledTimes(1);
  finish(initial); await first; await second;
  expect(apiRequest).toHaveBeenNthCalledWith(2, '/stadium/sectors/lower_north/price', { method: 'PUT', body: JSON.stringify({ price: 4000 }) });
});
test('read that began before a confirmed write cannot overwrite the new stadium', async () => {
  let finish!: (value: Stadium) => void;
  const changed = { ...initial, capacity: 20000 };
  jest.mocked(apiRequest).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce(changed);
  const stale = stadiumService.get();
  await stadiumService.evolve();
  finish(initial);
  expect(await stale).toEqual(changed);
});
test('a failed write does not prevent the following edit from being saved', async () => {
  jest.mocked(apiRequest).mockRejectedValueOnce(new Error('Saldo insuficiente.')).mockResolvedValueOnce(initial);
  const failed = stadiumService.upgrade('medical');
  const next = stadiumService.price('lower_north', 2000);
  await expect(failed).rejects.toThrow('Saldo insuficiente.');
  await expect(next).resolves.toEqual(initial);
});
