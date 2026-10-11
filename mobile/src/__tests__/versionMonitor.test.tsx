import { act, render } from '@testing-library/react-native';
import { AppState } from 'react-native';
import { useVersionMonitor } from '../components/useVersionMonitor';
import { checkForAppUpdate } from '../services/versionMonitor';

jest.mock('../services/versionMonitor', () => ({ checkForAppUpdate: jest.fn(async () => undefined) }));
const check = jest.mocked(checkForAppUpdate);
const originalState = Object.getOwnPropertyDescriptor(AppState, 'currentState')!;
afterAll(() => { Object.defineProperty(AppState, 'currentState', originalState); });
function Monitor() { useVersionMonitor(); return null; }
beforeEach(() => { jest.useFakeTimers(); Object.defineProperty(AppState, 'currentState', { value: 'active', configurable: true }); check.mockReset(); check.mockResolvedValue(undefined); });
afterEach(() => { jest.useRealTimers(); jest.restoreAllMocks(); });

test('checks at startup, each minute and when the app becomes active; stops after unmount', async () => {
  const remove = jest.fn();
  const events = jest.spyOn(AppState, 'addEventListener').mockReturnValue({ remove });
  const view = await render(<Monitor />);
  expect(check).toHaveBeenCalledTimes(1);
  await act(async () => { jest.advanceTimersByTime(60000); });
  expect(check).toHaveBeenCalledTimes(2);
  await act(async () => { events.mock.calls[0][1]('active'); });
  expect(check).toHaveBeenCalledTimes(3);
  await view.unmount();
  expect(remove).toHaveBeenCalled();
  await act(async () => { jest.advanceTimersByTime(60000); });
  expect(check).toHaveBeenCalledTimes(3);
});

test('does not overlap requests and prevents a reload after unmount', async () => {
  let finish!: () => void;
  check.mockImplementation(() => new Promise(resolve => { finish = resolve; }));
  const view = await render(<Monitor />);
  await act(async () => { jest.advanceTimersByTime(120000); });
  expect(check).toHaveBeenCalledTimes(1);
  const mounted = check.mock.calls[0][0];
  await view.unmount();
  expect(mounted()).toBe(false);
  await act(async () => { finish(); });
});

test('retries a failed check on the next interval', async () => {
  check.mockRejectedValueOnce(new Error('Offline'));
  await render(<Monitor />);
  await act(async () => { jest.advanceTimersByTime(60000); });
  expect(check).toHaveBeenCalledTimes(2);
});
