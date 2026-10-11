import { Platform } from 'react-native';
import * as FileSystem from 'expo-file-system/legacy';

const prefix = 'ligapro.game.v1.';
const directory = `${FileSystem.documentDirectory}game-cache/`;
let operations = Promise.resolve();
const storageKey = (owner: string, name: string) => `${prefix}${encodeURIComponent(owner)}.${encodeURIComponent(name)}`;
function serialize(operation: () => Promise<void>) {
  const next = operations.then(operation, operation);
  operations = next.catch(() => undefined);
  return next;
}
async function readDocument(key: string): Promise<Record<string, unknown>> {
  try {
    const raw = Platform.OS === 'web' ? globalThis.localStorage.getItem(key)
      : await FileSystem.readAsStringAsync(`${directory}${key}.json`);
    const value: unknown = raw ? JSON.parse(raw) : null;
    return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
  } catch { return {}; }
}
export const localGameCache = {
  read: async <T>(owner: string, name: string, query: string): Promise<T | null> => {
    await operations;
    return (await readDocument(storageKey(owner, name)))[query] as T ?? null;
  },
  write: (owner: string, name: string, query: string, data: unknown, isCurrent: () => boolean) => serialize(async () => {
    if (!isCurrent()) return;
    const key = storageKey(owner, name);
    const document = await readDocument(key);
    if (!isCurrent()) return;
    document[query] = data;
    // Keep bounded query history for filters and calendar months.
    const keys = Object.keys(document);
    for (const old of keys.slice(0, Math.max(0, keys.length - 50))) if (old !== query) delete document[old];
    const raw = JSON.stringify(document);
    if (Platform.OS === 'web') globalThis.localStorage.setItem(key, raw);
    else {
      await FileSystem.makeDirectoryAsync(directory, { intermediates: true });
      await FileSystem.writeAsStringAsync(`${directory}${key}.json`, raw);
    }
  }).catch(() => { /* A full or unavailable local disk must not hide server data. */ }),
  clearUser: (userId: string) => serialize(async () => {
    const userPrefix = `${prefix}${encodeURIComponent(userId)}`;
    const belongsToUser = (key: string) => key.startsWith(`${userPrefix}.`) || key.startsWith(`${userPrefix}%3A`);
    if (Platform.OS === 'web') {
      const storage = globalThis.localStorage;
      const keys = Array.from({ length: storage.length }, (_, index) => storage.key(index));
      for (const key of keys) if (key && belongsToUser(key)) storage.removeItem(key);
    } else {
      const files = await FileSystem.readDirectoryAsync(directory);
      for (const file of files) if (belongsToUser(file)) await FileSystem.deleteAsync(`${directory}${file}`, { idempotent: true });
    }
  }).catch(() => undefined),
};
