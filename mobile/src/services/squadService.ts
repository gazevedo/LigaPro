import { apiRequest } from './apiClient';
import { Squad, Lineup, Player } from '../types/game';
export const squadService = {
  get: () => apiRequest<Squad>('/squad'),
  shirtNumber: (id: string, number: number) => apiRequest<Player>(`/squad/players/${id}/shirt-number`, { method: 'PUT', body: JSON.stringify({ number }) }),
  save: (lineup: Lineup) => apiRequest<Lineup>('/squad/lineup', { method: 'PUT', body: JSON.stringify(lineup) }),
};
