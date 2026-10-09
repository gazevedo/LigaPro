import { useContext, useEffect, useRef } from 'react';
import { AppState } from 'react-native';
import { NavigationContext } from '@react-navigation/native';

// Pause hidden screens/apps and never overlap polls while a request is in flight.
export function useScreenRefresh(ensure: () => Promise<unknown>, refresh?: () => Promise<unknown>, enabled = true, identity?: string) {
  const navigation = useContext(NavigationContext);
  const callbacks = useRef({ ensure, refresh });
  useEffect(() => { callbacks.current = { ensure, refresh }; }, [ensure, refresh]);
  useEffect(() => {
    if (!enabled) return;
    let pending = false, disposed = false, timer: ReturnType<typeof setInterval> | undefined;
    const visible = () => !disposed && (!navigation || navigation.isFocused()) &&
      AppState.currentState !== 'background' && AppState.currentState !== 'inactive' &&
      (typeof document === 'undefined' || document.visibilityState !== 'hidden');
    async function run(refreshing: boolean) {
      if (pending || !visible()) return;
      pending = true;
      try { await (refreshing ? callbacks.current.refresh?.() : callbacks.current.ensure()); }
      catch { /* Stores expose request errors while preserving the last successful data. */ }
      finally { pending = false; }
    }
    function stop() { if (timer !== undefined) clearInterval(timer); timer = undefined; }
    function start() {
      stop();
      if (!visible()) return;
      void run(false);
      if (callbacks.current.refresh) timer = setInterval(() => { void run(true); }, 3000);
    }
    const focus = navigation?.addListener('focus', start);
    const blur = navigation?.addListener('blur', stop);
    const appState = AppState.addEventListener('change', start);
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', start);
    start();
    return () => {
      disposed = true; stop(); focus?.(); blur?.(); appState.remove();
      if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', start);
    };
  }, [navigation, enabled, identity]);
}
