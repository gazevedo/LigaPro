import { apiRequest } from './apiClient';
import { Competition } from '../types/game';
export const competitionService = { get: () => apiRequest<Competition>('/competition') };
