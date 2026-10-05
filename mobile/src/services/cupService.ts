import { apiRequest } from './apiClient';
export interface Cup {
  competition: { id: string; name: string; status: string } | null;
  entry: { status: string; phase: string } | null;
  matches: { id: string; phase: string; date: string; status: string; home_goals?: number; away_goals?: number }[];
}
export const cupService = { get: () => apiRequest<Cup>('/competition/cup') };
