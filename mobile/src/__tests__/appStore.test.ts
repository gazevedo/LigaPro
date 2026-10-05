import { useAppStore } from '../stores/appStore';
import { checkHealth } from '../services/healthService';
jest.mock('../services/healthService', () => ({ checkHealth: jest.fn() }));
const health = jest.mocked(checkHealth);
beforeEach(() => {
  jest.clearAllMocks();
  useAppStore.setState({ initialized: false, loading: false, apiAvailable: false, error: null });
});
test('health check initializes the app', async () => {
  health.mockResolvedValueOnce(undefined);
  await useAppStore.getState().initialize();
  expect(useAppStore.getState()).toMatchObject({
    initialized: true, loading: false, apiAvailable: true, error: null });
});
test('failed health check can be retried', async () => {
  health.mockRejectedValueOnce(new Error('Offline'));
  await useAppStore.getState().initialize();
  expect(useAppStore.getState()).toMatchObject({ apiAvailable: false, error: 'Offline' });
  health.mockResolvedValueOnce(undefined);
  await useAppStore.getState().initialize();
  expect(useAppStore.getState()).toMatchObject({ apiAvailable: true, error: null });
});
