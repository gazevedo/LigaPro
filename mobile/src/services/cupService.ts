import { CompetitionMatch } from './competitionService';
import { apiRequest } from './apiClient';
export interface Cup {
  competition: { id: string; name: string; status: string } | null;
  entry: { status: string; phase: string } | null;
  matches: CompetitionMatch[];
}
export const cupService = { get: () => apiRequest<Cup>('/competition/cup') };
