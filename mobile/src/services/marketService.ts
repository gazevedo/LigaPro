import { apiRequest } from './apiClient';
import { Listing, Offer, Player, Market } from '../types/game';
export const marketService = {
  search: (filters: Record<string, string> = {}) => apiRequest<Player[]>(`/market/players?${new URLSearchParams(filters)}`),
  mine: () => apiRequest<Market>('/market/mine'),
  player: (id: string) => apiRequest<Player>(`/players/${id}`),
  list: (data: { player_id: string; type: 'sale' | 'loan'; price: number; duration_days: number }) => apiRequest<Listing>('/market/listings', { method: 'POST', body: JSON.stringify(data) }),
  offer: (listing_id: string, amount: number) => apiRequest<Offer>('/market/offers', { method: 'POST', body: JSON.stringify({ listing_id, amount }) }),
  accept: (id: string) => apiRequest<Offer>(`/market/offers/${id}/accept`, { method: 'POST' }),
  cancelOffer: (id: string) => apiRequest(`/market/offers/${id}/cancel`, { method: 'POST' }),
  cancelListing: (id: string) => apiRequest(`/market/listings/${id}/cancel`, { method: 'POST' }),
};
