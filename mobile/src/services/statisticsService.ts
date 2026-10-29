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
  analysis?: { club_id: string; shots: number; shots_on_target: number; accuracy: number | null; sectors: { label: string; attempts: number; successes: number; rate: number | null }[] }[];
  home_name: string; away_name: string;
  competition?: string;
  events?: { id?: string; minute: number; type: string; team_id?: string; player_id?: string }[];
  statistics?: Record<string, Record<string, number | object>>;
  financial?: { attendance?: number; price?: number; income?: number };
  consequences?: { player_id: string; name: string; energy_before: number; energy: number; morale_before: number; morale: number; injury_type?: string; suspended_until?: string }[];
  ratings: { id: string; player_id: string; club_id: string; name: string; position: string; rating: number; minutes: number; events_summary: Record<string, number | string> }[];
}
export const statisticsService = {
  competition: (kind: 'league' | 'cup', ranking: Ranking = 'goals', divisionId?: string) => apiRequest<Statistics>(`/competition/statistics?${new URLSearchParams({ kind, ranking, ...(divisionId ? { division_id: divisionId } : {}) })}`),
  get: (ranking: Ranking = 'goals', season?: string) => apiRequest<Statistics>(`/statistics?${new URLSearchParams({ ranking, ...(season ? { season_id: season } : {}) })}`),
  report: (id: string) => apiRequest<MatchReport>(`/competition/matches/${id}`),
};

export interface PerformanceRow {
  player: import('../types/game').Player; average_rating: number | null; rating_change: number | null;
  recent: { date: string; rating: number; minutes: number; match_id: string; goals: number; assists: number; shots: number; saves: number; defensive_actions: number }[];
  development: { created_at: string; strength: number; previous_strength: number; individual_skills: Record<string, number>; skill: string; previous_skill: number }[];
}
export const performanceService = { get: () => apiRequest<{ players: PerformanceRow[] }>('/squad/performance') };
