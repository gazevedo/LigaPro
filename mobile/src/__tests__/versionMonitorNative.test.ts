import * as Updates from 'expo-updates';
import { checkForAppUpdate } from '../services/versionMonitor';

jest.mock('expo-updates', () => ({ isEnabled: true, checkForUpdateAsync: jest.fn(), fetchUpdateAsync: jest.fn(), reloadAsync: jest.fn() }));
const check = jest.mocked(Updates.checkForUpdateAsync);
const download = jest.mocked(Updates.fetchUpdateAsync);
const restart = jest.mocked(Updates.reloadAsync);
beforeEach(() => { jest.clearAllMocks(); });
afterEach(() => { jest.restoreAllMocks(); });

test('downloads an available update before restarting', async () => {
  check.mockResolvedValue({ isAvailable: true } as Awaited<ReturnType<typeof check>>);
  download.mockResolvedValue({ isNew: true } as Awaited<ReturnType<typeof download>>);
  await checkForAppUpdate(() => true);
  expect(download).toHaveBeenCalledTimes(1);
  expect(restart).toHaveBeenCalledTimes(1);
  expect(download.mock.invocationCallOrder[0]).toBeLessThan(restart.mock.invocationCallOrder[0]);
});

test('no update and disabled OTA never restart', async () => {
  check.mockResolvedValue({ isAvailable: false } as Awaited<ReturnType<typeof check>>);
  await checkForAppUpdate(() => true);
  expect(download).not.toHaveBeenCalled();
  jest.replaceProperty(Updates, 'isEnabled', false);
  await checkForAppUpdate(() => true);
  expect(check).toHaveBeenCalledTimes(1);
  expect(restart).not.toHaveBeenCalled();
});

test('does not restart after a download fails or the monitor stops', async () => {
  check.mockResolvedValue({ isAvailable: true } as Awaited<ReturnType<typeof check>>);
  download.mockRejectedValueOnce(new Error('Offline'));
  await expect(checkForAppUpdate(() => true)).rejects.toThrow('Offline');
  let mounted = true;
  download.mockImplementationOnce(async () => { mounted = false; return { isNew: true } as Awaited<ReturnType<typeof download>>; });
  await checkForAppUpdate(() => mounted);
  expect(restart).not.toHaveBeenCalled();
});
