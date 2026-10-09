import { checkHealth } from '../services/healthService';
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

test('timeout produces a friendly error without retrying a mutation', async () => {
  jest.useFakeTimers();
  try {
    fetchMock.mockImplementation((_url, options) => new Promise((_resolve, reject) => {
      options?.signal?.addEventListener('abort', () => reject(new Error('signal is aborted without reason')));
    }));
    const request = apiRequest('/clubs', { method: 'POST' }, true, 30000, false);
    const rejected = expect(request).rejects.toThrow('O servidor demorou para responder.');
    await jest.advanceTimersByTimeAsync(8000);
    expect(fetchMock.mock.calls[0][1]?.signal?.aborted).toBe(false);
    await jest.advanceTimersByTimeAsync(22000);
    await rejected;
    expect(fetchMock).toHaveBeenCalledTimes(1);
  } finally { jest.useRealTimers(); }
});

test('the timeout also covers reading a response body', async () => {
  jest.useFakeTimers();
  try {
    fetchMock.mockImplementation(async (_url, options) => ({ status: 200, ok: true,
      json: () => new Promise((_resolve, reject) => options?.signal?.addEventListener('abort', () => reject(new Error('aborted')))),
    }) as Response);
    const request = apiRequest('/game/status', {}, true, 1000);
    const rejected = expect(request).rejects.toThrow('O servidor demorou para responder.');
    await jest.advanceTimersByTimeAsync(1000); await rejected;
  } finally { jest.useRealTimers(); }
});

test('expired session on club creation clears authentication without refreshing or retrying POST', async () => {
  const refresh = jest.fn(async () => undefined);
  const clear = jest.fn(async () => tokenService.clear());
  registerAuthHandlers({ refresh, clear });
  fetchMock.mockResolvedValue(response(401, { detail: 'Sessão expirada.' }));
  await expect(apiRequest('/clubs', { method: 'POST' }, true, 30000, false)).rejects.toThrow('Sessão expirada.');
  expect(refresh).not.toHaveBeenCalled();
  expect(clear).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(tokenService.current()).toBeNull();
});

test('startup allows cold starts and cancels an unresponsive server after thirty seconds', async () => {
  jest.useFakeTimers();
  let signal: AbortSignal | undefined;
  fetchMock.mockImplementation((_url, options) => new Promise((_resolve, reject) => {
    signal = options?.signal ?? undefined;
    signal?.addEventListener('abort', () => reject(new Error('Aborted')));
  }));
  try {
    const result = checkHealth().catch(error => error);
    await jest.advanceTimersByTimeAsync(29999);
    expect(signal?.aborted).toBe(false);
    await jest.advanceTimersByTimeAsync(1);
    expect(signal?.aborted).toBe(true);
    expect(await result).toMatchObject({ message: 'O servidor demorou para responder. Verifique sua conexão e tente novamente.' });
  } finally { jest.useRealTimers(); }
});

test('a slow but healthy server initializes without a false maintenance error', async () => {
  jest.useFakeTimers();
  let signal: AbortSignal | undefined;
  fetchMock.mockImplementation((_url, options) => new Promise(resolve => {
    signal = options?.signal ?? undefined;
    setTimeout(() => resolve(response(200, { status: 'ok', api: 'ok', mongodb: 'ok' })), 5000);
  }));
  try {
    const checking = checkHealth();
    await jest.advanceTimersByTimeAsync(5000);
    await expect(checking).resolves.toBeUndefined();
    expect(signal?.aborted).toBe(false);
    expect(fetchMock).toHaveBeenCalledWith('http://api.example/api/health', expect.objectContaining({ cache: 'no-store' }));
    expect((fetchMock.mock.calls[0][1]?.headers as Headers).has('Authorization')).toBe(false);
    expect((fetchMock.mock.calls[0][1]?.headers as Headers).has('Content-Type')).toBe(false);
    expect(jest.getTimerCount()).toBe(0);
  } finally { jest.useRealTimers(); }
});

test('JSON mutations keep their content type and explicit content types are preserved', async () => {
  fetchMock.mockResolvedValue(response(200, {}));
  await apiRequest('/auth/login', { method: 'POST', body: JSON.stringify({ email: 'coach@example.com' }) }, false);
  expect((fetchMock.mock.calls[0][1]?.headers as Headers).get('Content-Type')).toBe('application/json');
  await apiRequest('/upload', { method: 'POST', body: 'data', headers: { 'Content-Type': 'text/plain' } }, false);
  expect((fetchMock.mock.calls[1][1]?.headers as Headers).get('Content-Type')).toBe('text/plain');
});
