import { apiRequest, ApiError, ApiTimeoutError } from '../services/apiClient';
import { checkHealth } from '../services/healthService';
import { settingsService } from '../services/settingsService';
jest.mock('../services/apiClient', () => ({ ...jest.requireActual('../services/apiClient'), apiRequest: jest.fn() }));
const request = jest.mocked(apiRequest);
beforeEach(() => request.mockReset());
test('health requires API and MongoDB to be available', async () => {
  request.mockResolvedValueOnce({ status: 'ok', api: 'ok', mongodb: 'ok' });
  await expect(checkHealth()).resolves.toBeUndefined();
  expect(request).toHaveBeenCalledWith('/health', { cache: 'no-store' }, false, 15000);
  request.mockResolvedValueOnce({ status: 'ok', api: 'ok', mongodb: 'error' });
  await expect(checkHealth()).rejects.toThrow('API ou MongoDB indisponível.');
});
test('settings list and get use encoded REST paths', async () => {
  request.mockResolvedValue([]);
  await settingsService.list();
  await settingsService.get('display name');
  expect(request).toHaveBeenNthCalledWith(1, '/settings');
  expect(request).toHaveBeenNthCalledWith(2, '/settings/display%20name');
});
test('settings update sends JSON value with PUT', async () => {
  request.mockResolvedValue({});
  await settingsService.put('language', 'pt-BR');
  expect(request).toHaveBeenCalledWith('/settings/language', {
    method: 'PUT', body: JSON.stringify({ value: 'pt-BR' }),
  });
});

test('health polls while the persistent league is being prepared', async () => {
  jest.useFakeTimers();
  try {
    request.mockResolvedValueOnce({ status: 'initializing', api: 'ok', mongodb: 'ok' });
    request.mockResolvedValueOnce({ status: 'ok', api: 'ok', mongodb: 'ok' });
    const pending = checkHealth();
    await jest.advanceTimersByTimeAsync(1000);
    await expect(pending).resolves.toBeUndefined();
    expect(request).toHaveBeenCalledTimes(2);
  } finally { jest.useRealTimers(); }
});
test('health stops polling with an actionable message if preparation is still incomplete', async () => {
  jest.useFakeTimers();
  try {
    request.mockResolvedValue({ status: 'initializing', api: 'ok', mongodb: 'ok' });
    const pending = expect(checkHealth()).rejects.toThrow('A liga ainda está sendo preparada. Tente novamente em instantes.');
    await jest.runAllTimersAsync();
    await pending;
    expect(request).toHaveBeenCalledTimes(60);
  } finally { jest.useRealTimers(); }
});

test.each([new ApiTimeoutError(), new ApiError(503, 'Inicializando'), new ApiError(504, 'Gateway timeout')])('health retries a cold-start failure without losing preparation progress (%s)', async error => {
  jest.useFakeTimers();
  try {
    request.mockRejectedValueOnce(error);
    request.mockResolvedValueOnce({ status: 'ok', api: 'ok', mongodb: 'ok' });
    const pending = checkHealth();
    await jest.advanceTimersByTimeAsync(1000);
    await expect(pending).resolves.toBeUndefined();
    expect(request).toHaveBeenCalledTimes(2);
  } finally { jest.useRealTimers(); }
});
