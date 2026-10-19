import { HealthResponse } from '../types/api';
import { apiRequest, ApiError, ApiTimeoutError } from './apiClient';
export async function checkHealth(): Promise<void> {
  for (let attempt = 0; attempt < 60; attempt++) {
    let health: HealthResponse;
    try { health = await apiRequest<HealthResponse>('/health', { cache: 'no-store' }, false, 15000); }
    catch (error) {
      const retryable = error instanceof ApiTimeoutError || (error instanceof ApiError && [503, 504].includes(error.status));
      if (!retryable || attempt === 59) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000));
      continue;
    }
    if (health.status === 'initializing' && health.api === 'ok' && health.mongodb === 'ok') {
      if (attempt < 59) await new Promise(resolve => setTimeout(resolve, 1000));
      continue;
    }
    if (health.status !== 'ok' || health.api !== 'ok' || health.mongodb !== 'ok') {
      throw new Error('API ou MongoDB indisponível.');
    }
    return;
  }
  throw new Error('A liga ainda está sendo preparada. Tente novamente em instantes.');
}
