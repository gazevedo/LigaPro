import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';
import { Tokens, User } from '../types/auth';
const key = 'ligapro.auth.tokens';
let tokens: Tokens | null = null;
let cachedUser: User | null = null;
let writes = Promise.resolve();
function serialize(operation: () => Promise<void>) {
  const result = writes.then(operation, operation);
  writes = result.catch(() => undefined);
  return result;
}
const options = { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY };
export const tokenService = {
  current: (): Tokens | null => tokens,
  currentUser: (): User | null => cachedUser,
  read: async (): Promise<Tokens | null> => {
    await writes;
    const value = Platform.OS === 'web'
      ? globalThis.localStorage.getItem(key)
      : await SecureStore.getItemAsync(key);
    if (!value) { cachedUser = null; return (tokens = null); }
    let parsed: unknown;
    try { parsed = JSON.parse(value); }
    catch { await tokenService.clear(); return null; }
    if (typeof parsed !== 'object' || parsed === null ||
        !('access_token' in parsed) || !('refresh_token' in parsed) ||
        typeof parsed.access_token !== 'string' || typeof parsed.refresh_token !== 'string') {
      await tokenService.clear(); return null;
    }
    const user = 'user' in parsed ? parsed.user : null;
    cachedUser = user && typeof user === 'object' && 'id' in user && typeof user.id === 'string' && 'name' in user && typeof user.name === 'string' && 'email' in user && typeof user.email === 'string' && 'active' in user && user.active === true ? user as User : null;
    return (tokens = { access_token: parsed.access_token, refresh_token: parsed.refresh_token });
  },
  save: (value: Tokens & { user?: User }): Promise<void> => serialize(async () => {
    const user = value.user ?? cachedUser;
    const stored = JSON.stringify({ access_token: value.access_token, refresh_token: value.refresh_token, ...(user ? { user } : {}) });
    if (Platform.OS === 'web') globalThis.localStorage.setItem(key, stored);
    else await SecureStore.setItemAsync(key, stored, options);
    tokens = { access_token: value.access_token, refresh_token: value.refresh_token };
    cachedUser = user;
  }),
  saveUser: (user: User): Promise<void> => serialize(async () => {
    if (!tokens) return;
    const stored = JSON.stringify({ ...tokens, user });
    if (Platform.OS === 'web') globalThis.localStorage.setItem(key, stored);
    else await SecureStore.setItemAsync(key, stored, options);
    cachedUser = user;
  }),
  clear: (): Promise<void> => serialize(async () => {
    tokens = null; cachedUser = null;
    if (Platform.OS === 'web') globalThis.localStorage.removeItem(key);
    else await SecureStore.deleteItemAsync(key);
  }),
};
