import { HealthResponse } from '../types/api';
import { apiRequest } from './apiClient';
export async function checkHealth(): Promise<void> {
  const health = await apiRequest<HealthResponse>('/health', {}, false, 3000);
  if (health.status !== 'ok' || health.api !== 'ok' || health.mongodb !== 'ok') {
    throw new Error('API ou MongoDB indisponível.');
  }
}
