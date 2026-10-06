import { apiRequest } from './apiClient';
import { tokenService } from './tokenService';
export interface LivePlayer { id: string; name: string; position: string; assigned_position: string; energy: number; physical_condition: number; yellow_cards: number; injured: boolean; dismissed: boolean }
export interface LiveEvent { sequence: number; minute: number; type: string; narration: string }
export interface LiveState {
  match_id: string; status: string; current_minute: number; current_second: number; updated_at: string;
  home_name: string; away_name: string; home_score: number; away_score: number;
  simulation_speed: number; paused: boolean; connected_users: number; human_vs_human: boolean;
  home_possession: number; away_possession: number; home_attacks: number; away_attacks: number;
  home_chances: number; away_chances: number; home_shots: number; away_shots: number;
  home_shots_on_target: number; away_shots_on_target: number; home_fouls: number; away_fouls: number;
  home_yellow_cards: number; away_yellow_cards: number; home_red_cards: number; away_red_cards: number;
  events: LiveEvent[]; match_momentum: Record<string, number>;
  own_team: { id: string; formation: string; style: string; marking: string; attack_focus: string; substitutions_used: number; lineup: LivePlayer[]; reserves: LivePlayer[] } | null;
}
export interface LiveMessage { type: string; data: LiveState | LiveEvent | { reason?: string; status?: string } }
export const liveMatchService = {
  commandId: (sequence: number) => `${Date.now()}-${sequence}`,
  state: (id: string) => apiRequest<LiveState>(`/matches/${id}/live-state`),
  upcoming: () => apiRequest<{ id: string; date: string; round?: number; status: string }[]>('/matches/upcoming'),
  connect(id: string) {
    const base = process.env.EXPO_PUBLIC_API_URL?.replace(/\/api\/?$/, '').replace(/\/$/, '').replace(/^http/, 'ws');
    const token = tokenService.current()?.access_token;
    if (!base || !token) throw new Error('Sessão indisponível. Entre novamente para acompanhar.');
    return new WebSocket(`${base}/ws/matches/${id}`, [`bearer.${token}`]);
  },
};
