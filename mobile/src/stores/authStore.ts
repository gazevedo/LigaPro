import { create } from 'zustand';
import { User, AuthResponse } from '../types/auth';
import { ApiError, registerAuthHandlers } from '../services/apiClient';
import { authService } from '../services/authService';
import { tokenService } from '../services/tokenService';
import { getGoogleIdToken } from '../services/googleService';
interface AuthState {
  user: User | null; authenticated: boolean; loading: boolean; initialized: boolean; error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  loginWithGoogle: () => Promise<void>; logout: () => Promise<void>;
  refreshSession: () => Promise<void>; restoreSession: () => Promise<void>;
  clearError: () => void; clearSession: () => Promise<void>;
}
let generation = 0;
let refreshPromise: Promise<void> | null = null;
let restorePromise: Promise<void> | null = null;
export const useAuthStore = create<AuthState>((set, get) => {
  async function accept(response: AuthResponse, expectedGeneration: number) {
    if (generation !== expectedGeneration) return;
    await tokenService.save(response);
    if (generation === expectedGeneration) {
      set({ user: response.user, authenticated: true, initialized: true, error: null });
    }
  }
  async function authenticate(action: () => Promise<AuthResponse>) {
    const ticket = ++generation;
    set({ loading: true, error: null });
    try { await accept(await action(), ticket); }
    catch (error) { set({ error: error instanceof Error ? error.message : 'Falha ao autenticar.' }); }
    finally { set({ loading: false }); }
  }
  return {
    user: null, authenticated: false, loading: false, initialized: false, error: null,
    login: (email, password) => authenticate(() => authService.login(email, password)),
    register: (name, email, password) => authenticate(() => authService.register(name, email, password)),
    loginWithGoogle: () => authenticate(async () => authService.google(await getGoogleIdToken())),
    clearError: () => set({ error: null }),
    clearSession: async () => {
      generation++;
      try { await tokenService.clear(); }
      finally { set({ user: null, authenticated: false, initialized: true, loading: false }); }
    },
    logout: async () => {
      generation++;
      set({ loading: true, error: null });
      try {
        const token = tokenService.current()?.refresh_token;
        if (token) await authService.logout(token);
      } catch { set({ error: 'Sessão local encerrada. Não foi possível confirmar o logout no servidor.' }); }
      finally { await get().clearSession(); set({ loading: false }); }
    },
    refreshSession: () => {
      if (!refreshPromise) {
        refreshPromise = (async () => {
          const ticket = generation;
          const refresh = tokenService.current()?.refresh_token;
          if (!refresh) { await get().clearSession(); throw new ApiError(401, 'Sessão expirada.'); }
          try { await accept(await authService.refresh(refresh), ticket); }
          catch (error) {
            if (generation === ticket && error instanceof ApiError && error.status === 401) await get().clearSession();
            throw error;
          }
        })().finally(() => { refreshPromise = null; });
      }
      return refreshPromise;
    },
    restoreSession: () => {
      if (!restorePromise) {
        restorePromise = (async () => {
          const ticket = generation;
          set({ loading: true, error: null });
          try {
            const tokens = await tokenService.read();
            if (tokens) {
              const user = await authService.me();
              if (generation === ticket) set({ user, authenticated: true });
            } else if (generation === ticket) { set({ user: null, authenticated: false }); }
          } catch (error) {
            if (generation === ticket) {
              if (error instanceof ApiError && error.status === 401) await get().clearSession();
              set({ error: error instanceof Error ? error.message : 'Falha ao restaurar sessão.' });
            }
          } finally {
            if (generation === ticket) set({ initialized: true, loading: false });
          }
        })().finally(() => { restorePromise = null; });
      }
      return restorePromise;
    },
  };
});
registerAuthHandlers({ refresh: () => useAuthStore.getState().refreshSession(),
  clear: () => useAuthStore.getState().clearSession() });
