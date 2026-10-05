import { apiRequest, ApiError, registerAuthHandlers } from '../services/apiClient';
import { tokenService } from '../services/tokenService';
import { Tokens } from '../types/auth';
jest.mock('../services/tokenService', () => {
  let saved: Tokens | null = null;
  return { tokenService: { current: () => saved, save: async (value: Tokens) => { saved = value; },
    clear: async () => { saved = null; } } };
});
const originalFetch = global.fetch;
const fetchMock = jest.fn() as jest.MockedFunction<typeof fetch>;
const response = (status: number, value: unknown) => ({
  status, ok: status >= 200 && status < 300, json: async () => value,
}) as Response;
beforeEach(async () => {
  process.env.EXPO_PUBLIC_API_URL = 'http://api.example/api'; global.fetch = fetchMock;
  fetchMock.mockReset(); await tokenService.save({ access_token: 'old', refresh_token: 'refresh' });
});
afterAll(() => { global.fetch = originalFetch; });
test('concurrent 401s share one refresh and retry with new bearer', async () => {
  const refresh = jest.fn(async () => { await tokenService.save({ access_token: 'new', refresh_token: 'rotated' }); });
  const clear = jest.fn(async () => { await tokenService.clear(); });
  registerAuthHandlers({ refresh, clear });
  fetchMock.mockImplementation(async (_url, options) =>
    (options?.headers as Headers).get('Authorization') === 'Bearer new'
      ? response(200, { id: 'user' }) : response(401, { detail: 'expired' }));
  expect(await Promise.all([apiRequest('/auth/me'), apiRequest('/auth/me')])).toEqual([{ id: 'user' }, { id: 'user' }]);
  expect(refresh).toHaveBeenCalledTimes(1); expect(fetchMock).toHaveBeenCalledTimes(4);
  expect(clear).not.toHaveBeenCalled();
});
test('invalid refresh does not loop', async () => {
  const clear = jest.fn(async () => { await tokenService.clear(); });
  const refresh = jest.fn(async () => { await clear(); throw new ApiError(401, 'Sessão expirada.'); });
  registerAuthHandlers({ refresh, clear }); fetchMock.mockResolvedValue(response(401, { detail: 'expired' }));
  await expect(apiRequest('/auth/me')).rejects.toThrow('Sessão expirada.');
  expect(refresh).toHaveBeenCalledTimes(1); expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(tokenService.current()).toBeNull();
});
test('public login neither attaches bearer nor refreshes invalid credentials', async () => {
  const refresh = jest.fn(async () => undefined);
  registerAuthHandlers({ refresh, clear: async () => tokenService.clear() });
  fetchMock.mockResolvedValue(response(401, { detail: 'E-mail ou senha inválidos.' }));
  await expect(apiRequest('/auth/login', { method: 'POST' }, false)).rejects.toThrow('E-mail ou senha inválidos.');
  expect((fetchMock.mock.calls[0][1]?.headers as Headers).has('Authorization')).toBe(false);
  expect(refresh).not.toHaveBeenCalled();
});
test('logout accepts HTTP 204 without a JSON body', async () => {
  fetchMock.mockResolvedValue(response(204, undefined));
  await expect(apiRequest('/auth/logout', { method: 'POST' }, false)).resolves.toBeUndefined();
});
