import { useAppStore } from '../stores/appStore';
import { checkHealth } from '../services/healthService';
jest.mock('../services/healthService', () => ({ checkHealth: jest.fn() }));
const health = jest.mocked(checkHealth);
beforeEach(() => {
  jest.useFakeTimers();
  jest.clearAllMocks();
  useAppStore.setState({ initialized: false, loading: false, apiAvailable: false, error: null });
});
afterEach(() => jest.useRealTimers());
test('health check initializes the app', async () => {
  health.mockResolvedValueOnce(undefined);
  const initializing = useAppStore.getState().initialize();
  await jest.advanceTimersByTimeAsync(5000);
  await initializing;
  expect(useAppStore.getState()).toMatchObject({
    initialized: true, loading: false, apiAvailable: true, error: null });
});
test('failed health check can be retried', async () => {
  health.mockRejectedValueOnce(new Error('Offline'));
  const failed = useAppStore.getState().initialize();
  await jest.advanceTimersByTimeAsync(5000);
  await failed;
  expect(useAppStore.getState()).toMatchObject({ apiAvailable: false, error: 'Offline' });
  health.mockResolvedValueOnce(undefined);
  const retry = useAppStore.getState().initialize();
  await jest.advanceTimersByTimeAsync(5000);
  await retry;
  expect(useAppStore.getState()).toMatchObject({ apiAvailable: true, error: null });
});

test('successful startup keeps the splash for five seconds', async () => {
  health.mockResolvedValueOnce(undefined);
  const initializing = useAppStore.getState().initialize();
  await jest.advanceTimersByTimeAsync(4999);
  expect(useAppStore.getState()).toMatchObject({ initialized: false, loading: true });
  await jest.advanceTimersByTimeAsync(1);
  await initializing;
  expect(useAppStore.getState()).toMatchObject({ initialized: true, loading: false });
});
