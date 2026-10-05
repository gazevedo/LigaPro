import { apiRequest } from './apiClient';
import { Club, Catalog } from '../types/game';
export const clubService = {
  status: () => apiRequest<{ club: Club | null }>('/game/status'),
  catalog: () => apiRequest<Catalog>('/game/catalog'),
  get: (id: string) => apiRequest<Club>(`/clubs/${encodeURIComponent(id)}`),
  create: (data: { name: string; country_id: string; badge_id: string }) => apiRequest<Club>('/clubs', { method: 'POST', body: JSON.stringify(data) }),
};
