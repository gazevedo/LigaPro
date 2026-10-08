import { act, render, screen } from '@testing-library/react-native';
import { ConnectionRetry } from '../components/ConnectionRetry';
beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());
test('counts down and retries exactly once after five seconds', async () => {
  const retry = jest.fn();
  await render(<ConnectionRetry onRetry={retry} />);
  expect(screen.getByText('Nova tentativa em 5s…')).toBeTruthy();
  await act(async () => { jest.advanceTimersByTime(4000); });
  expect(screen.getByText('Nova tentativa em 1s…')).toBeTruthy();
  expect(retry).not.toHaveBeenCalled();
  await act(async () => { jest.advanceTimersByTime(1000); });
  expect(retry).toHaveBeenCalledTimes(1);
  await act(async () => { jest.advanceTimersByTime(10000); });
  expect(retry).toHaveBeenCalledTimes(1);
});
test('leaving the waiting screen cancels its timer', async () => {
  const retry = jest.fn();
  const view = await render(<ConnectionRetry onRetry={retry} />);
  await view.unmount();
  await act(async () => { jest.advanceTimersByTime(5000); });
  expect(retry).not.toHaveBeenCalled();
});
