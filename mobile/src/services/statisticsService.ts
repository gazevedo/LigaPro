import { apiRequest } from './apiClient';
export type Ranking = 'goals' | 'matches' | 'cards';
export interface Statistics {
  season: { id: string; number: number } | null;
  seasons?: { id: string; number: number }[];
  ranking: Ranking;
  rows: { player_id: string; name: string; position: string; total: number; matches: number; minutes: number; goals: number; yellow_cards: number; red_cards: number }[];
  recent_matches?: { id: string; round: number; date: string; home_goals: number; away_goals: number }[];
}
export interface MatchReport {
  match: { phase?: string; extra_time?: boolean; shootout_score?: Record<string, number> | null; winner_club_id?: string; id: string; round: number; date: string; home_club_id: string; away_club_id: string; home_goals: number; away_goals: number };
  home_name: string; away_name: string;
  competition?: string;
  events?: { id?: string; minute: number; type: string; team_id?: string; player_id?: string }[];
  statistics?: Record<string, Record<string, number | object>>;
  financial?: { attendance?: number; price?: number; income?: number };
  consequences?: { player_id: string; name: string; energy_before: number; energy: number; morale_before: number; morale: number; injury_type?: string; suspended_until?: string }[];
  ratings: { id: string; player_id: string; club_id: string; name: string; position: string; rating: number; minutes: number; events_summary: Record<string, number | string> }[];
}
export const statisticsService = {
  get: (ranking: Ranking = 'goals', season?: string) => apiRequest<Statistics>(`/statistics?${new URLSearchParams({ ranking, ...(season ? { season_id: season } : {}) })}`),
  report: (id: string) => apiRequest<MatchReport>(`/competition/matches/${id}`),
};
