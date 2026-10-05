import { apiRequest } from './apiClient';
export interface PlayerContract { id: string; player_id: string; club_id: string; salary: number; started_at: string; expires_at: string; status: 'active' | 'expiring' | 'expired' | 'terminated' }
export interface ContractView { contract: PlayerContract | null; history: { id: string; action: string; salary: number; created_at: string }[] }
export interface ContractInput { salary: number; seasons: number }
export const contractService = {
  get: (id: string) => apiRequest<ContractView>(`/players/${id}/contract`),
  renew: (id: string, data: ContractInput) => apiRequest<PlayerContract>(`/players/${id}/contract/renew`, { method: 'POST', body: JSON.stringify(data) }),
  sign: (id: string, data: ContractInput) => apiRequest<PlayerContract>(`/market/players/${id}/sign`, { method: 'POST', body: JSON.stringify(data) }),
};
