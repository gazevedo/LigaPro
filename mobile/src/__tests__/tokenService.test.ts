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
test('web never persists tokens to browser storage', async () => {
  Platform.OS = 'web'; await tokenService.save({ access_token: 'test-access', refresh_token: 'test-refresh' });
  expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
});
