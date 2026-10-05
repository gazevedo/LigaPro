import { apiRequest } from './apiClient';
import { Stadium } from '../types/game';
export const stadiumService = {
  get: () => apiRequest<Stadium>('/stadium'),
  upgrade: (facility: string) => apiRequest<Stadium>(`/stadium/${encodeURIComponent(facility)}/upgrade`, { method: 'POST' }),
};
