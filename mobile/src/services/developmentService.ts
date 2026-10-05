import { apiRequest } from './apiClient';
import { Player } from '../types/game';
export const developmentService = {
  training: () => apiRequest<Player[]>('/training'),
  youth: () => apiRequest<Player[]>('/youth'),
  train: (id: string) => apiRequest<Player>(`/players/${id}/train`, { method: 'POST' }),
  promote: (id: string) => apiRequest<Player>(`/youth/${id}/promote`, { method: 'POST' }),
};
