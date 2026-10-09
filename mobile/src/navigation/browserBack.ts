import { NavigationState, PartialState } from '@react-navigation/native';

const HISTORY_KEY = 'ligaproNavigationDepth';
type Browser = Pick<Window, 'history' | 'addEventListener' | 'removeEventListener'>;

export function navigationDepth(state: NavigationState | PartialState<NavigationState> | undefined): number {
  if (!state) return 0;
  const index = state.index ?? 0;
  return index + navigationDepth(state.routes[index]?.state);
}

// Give Android's browser back gesture an in-app entry to consume.
export function registerBrowserBack(browser: Browser, canGoBack: () => boolean, goBack: () => void) {
  let appDepth = 0;
  let browserDepth = 0;
  const entry = (depth: number) => ({ ...browser.history.state, [HISTORY_KEY]: depth });
  if (browser.history.state?.[HISTORY_KEY] === undefined) browser.history.pushState(entry(0), '');
  else browser.history.replaceState(entry(0), '');

  function pop() {
    const destination = browser.history.state?.[HISTORY_KEY];
    const depth = typeof destination === 'number' ? destination : 0;
    const steps = Math.max(0, appDepth - depth);
    browserDepth = depth;
    for (let step = 0; step < steps && canGoBack(); step++) goBack();
    if (destination === undefined) {
      browser.history.pushState(entry(0), '');
      browserDepth = 0;
    } else if (depth > appDepth) {
      // A forward entry may belong to a route discarded by logout or a reset.
      browser.history.replaceState(entry(appDepth), '');
      browserDepth = appDepth;
    }
  }
  browser.addEventListener('popstate', pop);
  return {
    sync(state: NavigationState | PartialState<NavigationState> | undefined) {
      appDepth = navigationDepth(state);
      if (appDepth > browserDepth) {
        for (let depth = browserDepth + 1; depth <= appDepth; depth++) browser.history.pushState(entry(depth), '');
      } else if (appDepth < browserDepth) browser.history.go(appDepth - browserDepth);
      browserDepth = appDepth;
    },
    dispose() { browser.removeEventListener('popstate', pop); },
  };
}
