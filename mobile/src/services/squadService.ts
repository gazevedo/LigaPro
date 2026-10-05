import { apiRequest } from './apiClient';
import { Squad, Lineup } from '../types/game';
export const squadService = {
  get: () => apiRequest<Squad>('/squad'),
  save: (lineup: Lineup) => apiRequest<Lineup>('/squad/lineup', { method: 'PUT', body: JSON.stringify(lineup) }),
};
