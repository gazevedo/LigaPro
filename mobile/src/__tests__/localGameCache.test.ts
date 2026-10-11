import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';
import { localGameCache } from '../services/localGameCache';
jest.mock('expo-file-system/legacy', () => ({
  documentDirectory: 'file:///documents/', readAsStringAsync: jest.fn(),
  makeDirectoryAsync: jest.fn(async () => undefined), writeAsStringAsync: jest.fn(async () => undefined),
  readDirectoryAsync: jest.fn(), deleteAsync: jest.fn(async () => undefined),
}));
const originalPlatform = Platform.OS;
beforeEach(() => { jest.clearAllMocks(); Platform.OS = 'ios'; });
afterAll(() => { Platform.OS = originalPlatform; });
test('native data is written in the persistent document directory and restored', async () => {
  jest.mocked(FileSystem.readAsStringAsync).mockRejectedValueOnce(new Error('Missing'));
  await localGameCache.write('user-a', 'club-status', '[]', { club: 'my-club' }, () => true);
  expect(FileSystem.writeAsStringAsync).toHaveBeenCalledWith('file:///documents/game-cache/ligapro.game.v1.user-a.club-status.json', '{"[]":{"club":"my-club"}}');
  jest.mocked(FileSystem.readAsStringAsync).mockResolvedValueOnce('{"[]":{"club":"my-club"}}');
  expect(await localGameCache.read('user-a', 'club-status', '[]')).toEqual({ club: 'my-club' });
});
test('corrupt cache falls back to the server and obsolete writes are discarded', async () => {
  jest.mocked(FileSystem.readAsStringAsync).mockResolvedValueOnce('corrupt json');
  expect(await localGameCache.read('user-a', 'squad', '[]')).toBeNull();
  await localGameCache.write('user-a', 'squad', '[]', 'private', () => false);
  expect(FileSystem.writeAsStringAsync).not.toHaveBeenCalled();
});
test('web persistence survives reads and clearing one user preserves other accounts', async () => {
  Platform.OS = 'web';
  const values = new Map<string, string>();
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
    get length() { return values.size; }, key: (index: number) => [...values.keys()][index],
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value), removeItem: (key: string) => values.delete(key),
  } });
  await localGameCache.write('user-a:club', 'squad', '[]', 'squad-a', () => true);
  await localGameCache.write('user-b:club', 'squad', '[]', 'squad-b', () => true);
  expect(await localGameCache.read('user-a:club', 'squad', '[]')).toBe('squad-a');
  await localGameCache.clearUser('user-a');
  expect(await localGameCache.read('user-a:club', 'squad', '[]')).toBeNull();
  expect(await localGameCache.read('user-b:club', 'squad', '[]')).toBe('squad-b');
});
