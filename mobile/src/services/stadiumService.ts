import { apiRequest } from './apiClient';
import { Stadium } from '../types/game';
import { useAuthStore } from '../stores/authStore';
import { useClubStore } from '../stores/clubStore';
let queue = Promise.resolve();
let revision = 0, latest: Stadium | null = null, latestOwner = '';
const owner = () => `${useAuthStore.getState().user?.id}:${useClubStore.getState().data?.club?.id}`;
function mutate(action: () => Promise<Stadium>) {
  const requestedOwner = owner();
  const request = queue.then(async () => {
    if (requestedOwner !== owner()) throw new Error('A sessão mudou. Abra novamente o estádio.');
    const data = await action();
    if (requestedOwner === owner()) { revision++; latest = data; latestOwner = requestedOwner; }
    return data;
  });
  queue = request.then(() => undefined, () => undefined);
  return request;
}
export const stadiumService = {
  get: async () => {
    const ticket = revision, requestedOwner = owner();
    const data = await apiRequest<Stadium>('/stadium');
    return ticket !== revision && latest && latestOwner === requestedOwner ? latest : data;
  },
  evolve: () => mutate(() => apiRequest<Stadium>('/stadium/evolve', { method: 'POST' })),
  price: (sector: string, price: number) => mutate(() => apiRequest<Stadium>(`/stadium/sectors/${encodeURIComponent(sector)}/price`, { method: 'PUT', body: JSON.stringify({ price }) })),
  upgrade: (facility: string) => mutate(() => apiRequest<Stadium>(`/stadium/${encodeURIComponent(facility)}/upgrade`, { method: 'POST' })),
};
