import { create } from 'zustand';
import { useAuthStore } from './authStore';
export function domainStore<T, A extends unknown[]>(loader: (...args: A) => Promise<T>) {
  let generation = 0;
  const store = create<{ data: T | null; loading: boolean; error: string | null; load: (...args: A) => Promise<void>; reset: () => void }>((set) => ({
    data: null, loading: false, error: null,
    load: async (...args) => {
      const ticket = ++generation;
      set({ loading: true, error: null });
      try { const data = await loader(...args); if (ticket === generation) set({ data }); }
      catch (error) { if (ticket === generation) set({ error: error instanceof Error ? error.message : 'Falha ao carregar.' }); }
      finally { if (ticket === generation) set({ loading: false }); }
    },
    reset: () => { generation++; set({ data: null, loading: false, error: null }); },
  }));
  useAuthStore.subscribe((state, previous) => { if (state.user?.id !== previous.user?.id) store.getState().reset(); });
  return store;
}
