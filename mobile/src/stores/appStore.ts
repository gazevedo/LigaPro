import { create } from 'zustand';
import { checkHealth } from '../services/healthService';
interface AppState {
  initialized: boolean; loading: boolean; apiAvailable: boolean; error: string | null;
  initialize: () => Promise<void>;
}
export const useAppStore = create<AppState>((set) => ({
  initialized: false, loading: false, apiAvailable: false, error: null,
  initialize: async () => {
    const minimumDuration = new Promise<void>(resolve => setTimeout(resolve, 5000));
    set({ loading: true, error: null });
    try {
      await checkHealth();
      await minimumDuration;
      set({ initialized: true, apiAvailable: true, loading: false });
    } catch (error) {
      await minimumDuration;
      set({ initialized: true, apiAvailable: false, loading: false,
        error: error instanceof Error ? error.message : 'Falha ao conectar à API.' });
    }
  },
}));
