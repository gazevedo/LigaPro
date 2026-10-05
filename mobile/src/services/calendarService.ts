import { apiRequest } from './apiClient';
import { CalendarEvent } from '../types/game';
export interface Friendly { id: string; home_club_id: string; away_club_id: string; date: string; status: string }
export const calendarService = {
  friendlies: () => apiRequest<Friendly[]>('/calendar/friendlies'),
  friendly: (opponent_club_id: string, date: string) => apiRequest<Friendly>('/calendar/friendlies', { method: 'POST', body: JSON.stringify({ opponent_club_id, date }) }),
  acceptFriendly: (id: string) => apiRequest<Friendly>(`/calendar/friendlies/${id}/accept`, { method: 'POST' }),
  get: (filters: Record<string, string> = {}) => apiRequest<CalendarEvent[]>(`/calendar?${new URLSearchParams(filters)}`),
};
