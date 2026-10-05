import { apiRequest } from './apiClient';
import { Player, PlayerSkill } from '../types/game';
export const developmentService = {
  training: () => apiRequest<Player[]>('/training'),
  youth: () => apiRequest<Player[]>('/youth'),
  train: (id: string, skill?: PlayerSkill) => apiRequest<Player>(`/players/${id}/train`, { method: 'POST', body: JSON.stringify({ skill }) }),
  promote: (id: string) => apiRequest<Player>(`/youth/${id}/promote`, { method: 'POST' }),
};
