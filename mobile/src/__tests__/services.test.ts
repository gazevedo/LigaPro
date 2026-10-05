import { apiRequest } from '../services/apiClient';
import { checkHealth } from '../services/healthService';
import { settingsService } from '../services/settingsService';
jest.mock('../services/apiClient', () => ({ apiRequest: jest.fn() }));
const request = jest.mocked(apiRequest);
beforeEach(() => jest.clearAllMocks());
test('health requires API and MongoDB to be available', async () => {
  request.mockResolvedValueOnce({ status: 'ok', api: 'ok', mongodb: 'ok' });
  await expect(checkHealth()).resolves.toBeUndefined();
  expect(request).toHaveBeenCalledWith('/health');
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
