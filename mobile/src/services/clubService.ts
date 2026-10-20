import { apiRequest } from './apiClient';
import { Club, Catalog, Player } from '../types/game';
export interface RankedClub { id: string; name: string; ranking_position: number; ranking_points: number; reputation?: number }
export interface RankingPage { items: RankedClub[]; page: number; page_size: number; total: number; pages: number }
export const clubService = {
  squad: (id: string) => apiRequest<Player[]>(`/clubs/${encodeURIComponent(id)}/squad`),
  ranking: (page = 1, pageSize = 20) => apiRequest<RankingPage>(`/clubs/ranking/current?page=${page}&page_size=${pageSize}`),
  status: () => apiRequest<{ club: Club | null }>('/game/status'),
  resign: (id: string) => apiRequest<{ club: null }>(`/clubs/${encodeURIComponent(id)}/resign`, { method: 'POST', body: JSON.stringify({ confirmed: true }) }),
  catalog: () => apiRequest<Catalog>('/game/catalog'),
  get: (id: string) => apiRequest<Club>(`/clubs/${encodeURIComponent(id)}`),
  // Creation is an explicit, single POST. An expired session must return to login.
  create: (data: { name: string; country_id: string; badge_id: string; stadium_name?: string }) =>
    apiRequest<Club>('/clubs', { method: 'POST', body: JSON.stringify(data) }, true, 120000, false),
};
