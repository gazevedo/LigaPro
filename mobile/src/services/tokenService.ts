import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { Tokens } from '../types/auth';
const key = 'ligapro.auth.tokens';
let tokens: Tokens | null = null;
let writes = Promise.resolve();
function serialize(operation: () => Promise<void>) {
  const result = writes.then(operation, operation);
  writes = result.catch(() => undefined);
  return result;
}
const options = { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY };
export const tokenService = {
  current: (): Tokens | null => tokens,
  read: async (): Promise<Tokens | null> => {
    await writes;
    const value = Platform.OS === 'web'
      ? globalThis.localStorage.getItem(key)
      : await SecureStore.getItemAsync(key);
    if (!value) return (tokens = null);
    let parsed: unknown;
    try { parsed = JSON.parse(value); }
    catch { await tokenService.clear(); return null; }
    if (typeof parsed !== 'object' || parsed === null ||
        !('access_token' in parsed) || !('refresh_token' in parsed) ||
        typeof parsed.access_token !== 'string' || typeof parsed.refresh_token !== 'string') {
      await tokenService.clear(); return null;
    }
    return (tokens = { access_token: parsed.access_token, refresh_token: parsed.refresh_token });
  },
  save: (value: Tokens): Promise<void> => serialize(async () => {
    const stored = JSON.stringify({ access_token: value.access_token, refresh_token: value.refresh_token });
    if (Platform.OS === 'web') globalThis.localStorage.setItem(key, stored);
    else await SecureStore.setItemAsync(key, stored, options);
    tokens = { access_token: value.access_token, refresh_token: value.refresh_token };
  }),
  clear: (): Promise<void> => serialize(async () => {
    tokens = null;
    if (Platform.OS === 'web') globalThis.localStorage.removeItem(key);
    else await SecureStore.deleteItemAsync(key);
  }),
};
