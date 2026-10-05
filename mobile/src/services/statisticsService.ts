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
  match: { id: string; round: number; date: string; home_club_id: string; away_club_id: string; home_goals: number; away_goals: number };
  home_name: string; away_name: string;
  ratings: { id: string; player_id: string; club_id: string; name: string; position: string; rating: number; minutes: number; events_summary: Record<string, number | string> }[];
}
export const statisticsService = {
  get: (ranking: Ranking = 'goals', season?: string) => apiRequest<Statistics>(`/statistics?${new URLSearchParams({ ranking, ...(season ? { season_id: season } : {}) })}`),
  report: (id: string) => apiRequest<MatchReport>(`/competition/matches/${id}`),
};
