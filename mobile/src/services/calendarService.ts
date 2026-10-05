import { apiRequest } from './apiClient';
import { CalendarEvent } from '../types/game';
export const calendarService = {
  get: (filters: Record<string, string> = {}) => apiRequest<CalendarEvent[]>(`/calendar?${new URLSearchParams(filters)}`),
};
