import { create } from 'zustand';
import { useAuthStore } from './authStore';
const resets = new Set<() => void>();
export function resetDomainStores() { for (const reset of resets) reset(); }
export function domainStore<T, A extends unknown[]>(loader: (...args: A) => Promise<T>) {
  let generation = 0;
  let ownerGeneration = 0;
  let currentKey = '';
  const cached = new Map<string, T>();
  const pending = new Map<string, Promise<void>>();
  const latestRequest = new Map<string, number>();
  const keyFor = (args: A) => JSON.stringify(args);
  const store = create<{ data: T | null; loading: boolean; error: string | null; load: (...args: A) => Promise<void>; ensure: (...args: A) => Promise<void>; refresh: (...args: A) => Promise<void>; reset: () => void }>((set, get) => ({
    data: null, loading: false, error: null,
    load: (...args) => {
      const ticket = ++generation;
      const owner = ownerGeneration;
      const key = keyFor(args);
      const previous = currentKey === key ? get().data : cached.get(key) ?? null;
      currentKey = key;
      latestRequest.set(key, ticket);
      set({ data: previous, loading: previous === null, error: null });
      const request = (async () => {
        try { const data = await loader(...args); if (owner === ownerGeneration && latestRequest.get(key) === ticket) cached.set(key, data); if (ticket === generation) set({ data }); }
        catch (error) { if (ticket === generation) set({ error: error instanceof Error ? error.message : 'Falha ao carregar.' }); }
        finally { if (ticket === generation) set({ loading: false }); }
      })();
      pending.set(key, request);
      void request.then(() => { if (pending.get(key) === request) pending.delete(key); });
      return request;
    },
    ensure: (...args) => {
      const key = keyFor(args);
      if (currentKey === key && get().data !== null) return Promise.resolve();
      if (cached.has(key)) { generation++; currentKey = key; set({ data: cached.get(key)!, loading: false, error: null }); return Promise.resolve(); }
      const request = pending.get(key);
      if (!request || currentKey === key) return request ?? get().load(...args);
      const ticket = ++generation;
      currentKey = key; set({ data: null, loading: true, error: null });
      return request.then(() => {
        if (ticket === generation) set({ data: cached.get(key) ?? null, loading: false });
      });
    },
    refresh: (...args) => pending.get(keyFor(args)) ?? get().load(...args),
    reset: () => { generation++; ownerGeneration++; currentKey = ''; cached.clear(); pending.clear(); latestRequest.clear(); set({ data: null, loading: false, error: null }); },
  }));
  useAuthStore.subscribe((state, previous) => { if (state.user?.id !== previous.user?.id) store.getState().reset(); });
  resets.add(store.getState().reset);
  return store;
}
