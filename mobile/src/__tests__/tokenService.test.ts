import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';
import { tokenService } from '../services/tokenService';
jest.mock('expo-secure-store', () => ({
  WHEN_UNLOCKED_THIS_DEVICE_ONLY: 'device-only', getItemAsync: jest.fn(),
  setItemAsync: jest.fn(async () => undefined), deleteItemAsync: jest.fn(async () => undefined),
}));
const originalPlatform = Platform.OS;
beforeEach(async () => { Platform.OS = 'ios'; await tokenService.clear(); jest.clearAllMocks(); });
afterAll(() => { Platform.OS = originalPlatform; });
test('tokens persist only in SecureStore and restore', async () => {
  const tokens = { access_token: 'test-access', refresh_token: 'test-refresh' };
  await tokenService.save(tokens);
  expect(SecureStore.setItemAsync).toHaveBeenCalledWith('ligapro.auth.tokens', JSON.stringify(tokens),
    { keychainAccessible: 'device-only' });
  jest.mocked(SecureStore.getItemAsync).mockResolvedValueOnce(JSON.stringify(tokens));
  expect(await tokenService.read()).toEqual(tokens); await tokenService.clear();
  expect(SecureStore.deleteItemAsync).toHaveBeenCalledWith('ligapro.auth.tokens');
  expect(tokenService.current()).toBeNull();
});
test('web persists, restores rotated tokens, and removes them on logout', async () => {
  const storage = new Map<string, string>();
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  } });
  Platform.OS = 'web';
  const saved = { access_token: 'test-access', refresh_token: 'test-refresh' };
  await tokenService.save(saved);
  expect(storage.get('ligapro.auth.tokens')).toBe(JSON.stringify(saved));
  const rotated = { access_token: 'new-access', refresh_token: 'new-refresh' };
  storage.set('ligapro.auth.tokens', JSON.stringify(rotated));
  expect(await tokenService.read()).toEqual(rotated);
  expect(tokenService.current()).toEqual(rotated);
  expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
  await tokenService.clear();
  expect(storage.size).toBe(0);
  expect(await tokenService.read()).toBeNull();
});
test('corrupt browser session is removed', async () => {
  Platform.OS = 'web';
  globalThis.localStorage.setItem('ligapro.auth.tokens', '{invalid');
  expect(await tokenService.read()).toBeNull();
  expect(globalThis.localStorage.getItem('ligapro.auth.tokens')).toBeNull();
});
