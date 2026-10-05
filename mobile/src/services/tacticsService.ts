import { apiRequest } from './apiClient';
export interface Tactics {
  formation: string;
  play_style: 'balanced' | 'all_out_attack' | 'counter_attack';
  marking: 'light' | 'heavy' | 'very_heavy';
  attack_focus: 'normal' | 'center' | 'wings';
}
export interface MatchCommand { minute: number; type: 'tactics_change' | 'substitution'; payload: Record<string, string> }
export interface PlannedMatch { id: string; date: string; round: number; status: string; commands?: (MatchCommand & { team_id: string })[] }
export const tacticsService = {
  get: () => apiRequest<Tactics>('/tactics'),
  save: (tactics: Tactics) => apiRequest<Tactics>('/tactics', { method: 'PUT', body: JSON.stringify(tactics) }),
  matches: () => apiRequest<PlannedMatch[]>('/competition/matches'),
  command: (id: string, command: MatchCommand) => apiRequest<MatchCommand[]>(`/competition/matches/${id}/commands`, { method: 'POST', body: JSON.stringify(command) }),
};
