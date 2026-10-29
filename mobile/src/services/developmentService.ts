import { apiRequest } from './apiClient';
import { Player, PlayerSkill } from '../types/game';
export const developmentService = {
  training: () => apiRequest<Player[]>('/training'),
  youth: () => apiRequest<Player[]>('/youth'),
  train: (id: string, skill?: PlayerSkill) => apiRequest<Player>(`/players/${id}/train`, { method: 'POST', body: JSON.stringify({ skill }) }),
  selectYouth: (id: string) => apiRequest<Player>(`/youth/${id}/select`, { method: 'POST' }),
  release: (id: string) => apiRequest(`/youth/${id}/release`, { method: 'POST' }),
  promote: (id: string) => apiRequest<Player>(`/youth/${id}/promote`, { method: 'POST' }),
};

export type TrainingIntensity = 'light' | 'normal' | 'intense' | 'rest';
export interface TrainingPlan {
  enabled: boolean; days: number; skill: PlayerSkill; intensity: TrainingIntensity;
  individual: Record<string, PlayerSkill | 'rest'>;
  started_at?: string; ends_at?: string; next_session_at?: string; sessions_completed?: number;
}
export const trainingPlanService = {
  get: () => apiRequest<TrainingPlan>('/training/plan'),
  save: ({ enabled, days, skill, intensity, individual }: TrainingPlan) => apiRequest<TrainingPlan>('/training/plan', { method: 'PUT', body: JSON.stringify({ enabled, days, skill, intensity, individual }) }),
};
