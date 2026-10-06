import { apiRequest } from './apiClient';
export interface History {
  seasons: { id: string; season_number: number; champion_club_id: string; champion_name?: string; top_scorer?: { goals: number } }[];
  clubs: { id: string; season_number: number; position: number; division_tier: number; cash: number; title: boolean }[];
  records: { id: string; value: number }[];
  players: { id: string; player_id: string; player_name?: string; type: string; goals?: number; matches?: number; stars?: number; titles?: number[]; cup_titles?: string[] }[];
}
export interface NewsItem { id: string; type: string; title: string; body: string; created_at: string }
export const historyService = { get: () => apiRequest<History>('/history'), news: () => apiRequest<NewsItem[]>('/news') };
