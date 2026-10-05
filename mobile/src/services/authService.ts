import { tokenService } from './tokenService';
import { Platform } from 'react-native';
import { AuthResponse, User } from '../types/auth';
import { apiRequest } from './apiClient';
const device = { device_name: Platform.OS };
const post = <T>(path: string, body: unknown) => apiRequest<T>(path, {
  method: 'POST', body: JSON.stringify(body),
}, false);
export const authService = {
  login: (email: string, password: string) => post<AuthResponse>('/auth/login', { email, password, ...device }),
  register: (name: string, email: string, password: string) =>
    post<AuthResponse>('/auth/register', { name, email, password, ...device }),
  google: (id_token: string) => post<AuthResponse>('/auth/google', { id_token, ...device }),
  refresh: (refresh_token: string) => post<AuthResponse>('/auth/refresh', { refresh_token }),
  logout: (refresh_token: string) => apiRequest<void>('/auth/logout', {
    method: 'POST', body: JSON.stringify({ refresh_token }),
    headers: tokenService.current()?.access_token
      ? { Authorization: `Bearer ${tokenService.current()?.access_token}` } : {},
  }, false),
  me: () => apiRequest<User>('/auth/me'),
};
