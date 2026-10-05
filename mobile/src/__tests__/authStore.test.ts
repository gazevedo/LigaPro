import { useAuthStore } from '../stores/authStore';
import { authService } from '../services/authService';
import { tokenService } from '../services/tokenService';
import { getGoogleIdToken } from '../services/googleService';
import { ApiError } from '../services/apiClient';
import { AuthResponse, Tokens } from '../types/auth';
jest.mock('../services/authService', () => ({ authService: {
  login: jest.fn(), register: jest.fn(), google: jest.fn(), refresh: jest.fn(), logout: jest.fn(), me: jest.fn(),
} }));
jest.mock('../services/googleService', () => ({ getGoogleIdToken: jest.fn() }));
jest.mock('../services/tokenService', () => {
  let saved: Tokens | null = null;
  return { tokenService: { current: jest.fn(() => saved), read: jest.fn(async () => saved),
    save: jest.fn(async (value: Tokens) => { saved = value; }), clear: jest.fn(async () => { saved = null; }) } };
});
const response: AuthResponse = {
  access_token: 'test-access', refresh_token: 'test-refresh', token_type: 'bearer', expires_in: 900,
  refresh_expires_at: '2026-11-01T00:00:00Z', user: {
    id: 'user-id', name: 'User', email: 'user@example.com', auth_provider: 'local', avatar_url: null,
    email_verified: false, active: true, created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z', last_login_at: null },
};
beforeEach(async () => {
  await useAuthStore.getState().clearSession();
  useAuthStore.setState({ initialized: false, loading: false, error: null }); jest.clearAllMocks();
});
test('register and login persist tokens and authenticate', async () => {
  jest.mocked(authService.register).mockResolvedValueOnce(response);
  await useAuthStore.getState().register('User', 'user@example.com', 'password-123');
  expect(useAuthStore.getState()).toMatchObject({ authenticated: true, user: response.user });
  expect(tokenService.save).toHaveBeenCalledWith(response);
  jest.mocked(authService.login).mockResolvedValueOnce(response);
  await useAuthStore.getState().login('user@example.com', 'password-123');
  expect(authService.login).toHaveBeenCalledWith('user@example.com', 'password-123');
});
test('invalid login exposes only the generic error', async () => {
  jest.mocked(authService.login).mockRejectedValueOnce(new ApiError(401, 'E-mail ou senha inválidos.'));
  await useAuthStore.getState().login('user@example.com', 'wrong');
  expect(useAuthStore.getState()).toMatchObject({ authenticated: false, loading: false,
    error: 'E-mail ou senha inválidos.' });
  useAuthStore.getState().clearError(); expect(useAuthStore.getState().error).toBeNull();
});
test('Google submits the native ID token', async () => {
  jest.mocked(getGoogleIdToken).mockResolvedValueOnce('google-id-token');
  jest.mocked(authService.google).mockResolvedValueOnce(response);
  await useAuthStore.getState().loginWithGoogle();
  expect(authService.google).toHaveBeenCalledWith('google-id-token');
  expect(useAuthStore.getState().authenticated).toBe(true);
});
test('session is restored from secure storage and /me', async () => {
  await tokenService.save(response); jest.mocked(authService.me).mockResolvedValueOnce(response.user);
  await useAuthStore.getState().restoreSession();
  expect(authService.me).toHaveBeenCalledTimes(1);
  expect(useAuthStore.getState()).toMatchObject({ initialized: true, authenticated: true });
});
test('missing stored session remains unauthenticated', async () => {
  await useAuthStore.getState().restoreSession();
  expect(authService.me).not.toHaveBeenCalled();
  expect(useAuthStore.getState()).toMatchObject({ initialized: true, authenticated: false });
});
test('concurrent refresh callers share one rotated request', async () => {
  await tokenService.save(response);
  jest.mocked(authService.refresh).mockResolvedValueOnce({ ...response, refresh_token: 'rotated' });
  await Promise.all([useAuthStore.getState().refreshSession(), useAuthStore.getState().refreshSession()]);
  expect(authService.refresh).toHaveBeenCalledTimes(1);
  expect(tokenService.current()?.refresh_token).toBe('rotated');
});
test('invalid refresh clears the session', async () => {
  await tokenService.save(response); useAuthStore.setState({ authenticated: true, user: response.user });
  jest.mocked(authService.refresh).mockRejectedValueOnce(new ApiError(401, 'Sessão expirada.'));
  await expect(useAuthStore.getState().refreshSession()).rejects.toThrow('Sessão expirada.');
  expect(useAuthStore.getState().authenticated).toBe(false); expect(tokenService.current()).toBeNull();
});
test('logout clears local session despite network failure', async () => {
  await tokenService.save(response); jest.mocked(authService.logout).mockRejectedValueOnce(new Error('Offline'));
  await useAuthStore.getState().logout();
  expect(tokenService.current()).toBeNull(); expect(useAuthStore.getState().authenticated).toBe(false);
});
test('late refresh cannot restore a logged-out session', async () => {
  await tokenService.save(response);
  let resolve!: (value: AuthResponse) => void;
  jest.mocked(authService.refresh).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
  jest.mocked(authService.logout).mockResolvedValueOnce(undefined);
  const refresh = useAuthStore.getState().refreshSession(); await useAuthStore.getState().logout();
  resolve(response); await refresh;
  expect(tokenService.current()).toBeNull(); expect(useAuthStore.getState().authenticated).toBe(false);
});

test('a late /me response cannot restore a cleared session', async () => {
  await tokenService.save(response);
  let resolve!: (value: typeof response.user) => void;
  jest.mocked(authService.me).mockReturnValueOnce(new Promise((done) => { resolve = done; }));
  const restoring = useAuthStore.getState().restoreSession();
  await Promise.resolve();
  await useAuthStore.getState().clearSession();
  resolve(response.user); await restoring;
  expect(useAuthStore.getState()).toMatchObject({ authenticated: false, loading: false });
});
