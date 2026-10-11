import { useEffect } from 'react';
import { AppState } from 'react-native';
import { checkForAppUpdate } from '../services/versionMonitor';

export function useVersionMonitor() {
  useEffect(() => {
    let mounted = true;
    let checking = false;
    async function check() {
      if (!mounted || checking || (AppState.currentState && AppState.currentState !== 'active')) return;
      checking = true;
      try { await checkForAppUpdate(() => mounted); }
      catch { /* Offline or unavailable updates must not interrupt the game. */ }
      finally { checking = false; }
    }
    void check();
    const interval = setInterval(() => { void check(); }, 60000);
    const subscription = AppState.addEventListener('change', state => {
      if (state === 'active') void check();
    });
    return () => { mounted = false; clearInterval(interval); subscription.remove(); };
  }, []);
}
