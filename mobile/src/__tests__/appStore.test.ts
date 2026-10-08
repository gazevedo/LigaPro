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
  const initializing = useAppStore.getState().initialize();
  await initializing;
  expect(useAppStore.getState()).toMatchObject({
    initialized: true, loading: false, apiAvailable: true, error: null });
});
test('failed health check can be retried', async () => {
  health.mockRejectedValueOnce(new Error('Offline'));
  const failed = useAppStore.getState().initialize();
  await failed;
  expect(useAppStore.getState()).toMatchObject({ apiAvailable: false, error: 'Offline' });
  health.mockResolvedValueOnce(undefined);
  const retry = useAppStore.getState().initialize();
  await retry;
  expect(useAppStore.getState()).toMatchObject({ apiAvailable: true, error: null });
});

test('startup completes without an artificial splash delay', async () => {
  jest.useFakeTimers();
  try {
    health.mockResolvedValueOnce(undefined);
    await useAppStore.getState().initialize();
    expect(useAppStore.getState()).toMatchObject({ initialized: true, loading: false });
    expect(jest.getTimerCount()).toBe(0);
  } finally { jest.useRealTimers(); }
});
