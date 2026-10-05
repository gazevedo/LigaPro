import { AppSetting } from '../types/api';
import { apiRequest } from './apiClient';
export const settingsService = {
  list: () => apiRequest<AppSetting[]>('/settings'),
  get: (key: string) => apiRequest<AppSetting>(`/settings/${encodeURIComponent(key)}`),
  put: (key: string, value: unknown) => apiRequest<AppSetting>(
    `/settings/${encodeURIComponent(key)}`, { method: 'PUT', body: JSON.stringify({ value }) }),
};
