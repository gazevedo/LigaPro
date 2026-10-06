import { clubService } from '../services/clubService';
import { apiRequest, ApiError, ApiTimeoutError } from '../services/apiClient';
jest.mock('../services/apiClient', () => ({ ...jest.requireActual('../services/apiClient'), apiRequest: jest.fn() }));
const request = jest.mocked(apiRequest);
beforeEach(() => request.mockReset());
test('creation sends a single explicit request with no session refresh or recovery', async () => {
  request.mockResolvedValueOnce({ id: 'created' });
  await expect(clubService.create({ name: 'Clube', country_id: 'BR', badge_id: 'blue' })).resolves.toEqual({ id: 'created' });
  expect(request).toHaveBeenCalledWith('/clubs', { method: 'POST', body: JSON.stringify({ name: 'Clube', country_id: 'BR', badge_id: 'blue' }) }, true, 30000, false);
  expect(request).toHaveBeenCalledTimes(1);
});
test.each([new ApiTimeoutError(), new ApiError(401, 'Sessão expirada'), new ApiError(409, 'Clube já existe')])('does not recover or retry a failed creation (%s)', async error => {
  request.mockRejectedValueOnce(error);
  await expect(clubService.create({ name: 'Clube', country_id: 'BR', badge_id: 'blue' })).rejects.toBe(error);
  expect(request).toHaveBeenCalledTimes(1);
});
