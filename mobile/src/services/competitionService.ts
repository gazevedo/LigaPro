import { apiRequest } from './apiClient';
import { Competition } from '../types/game';
export const competitionService = { get: (divisionId?: string) => apiRequest<Competition>(`/competition${divisionId ? `?division_id=${encodeURIComponent(divisionId)}` : ''}`), matches: (divisionId?: string) => apiRequest<CompetitionMatch[]>(`/competition/matches${divisionId ? `?division_id=${encodeURIComponent(divisionId)}` : ''}`) };
export interface CompetitionMatch { id: string; round?: number; phase?: string; date: string; status: string; home_club_id?: string; away_club_id?: string; home_name?: string; away_name?: string; home_goals?: number; away_goals?: number }
