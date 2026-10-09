import { HealthResponse } from '../types/api';
import { apiRequest } from './apiClient';
export async function checkHealth(): Promise<void> {
  // A newly deployed serverless function may need time to initialize MongoDB.
  const health = await apiRequest<HealthResponse>('/health', { cache: 'no-store' }, false, 30000);
  if (health.status !== 'ok' || health.api !== 'ok' || health.mongodb !== 'ok') {
    throw new Error('API ou MongoDB indisponível.');
  }
}
