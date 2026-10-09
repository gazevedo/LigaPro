import { PartialState, NavigationState } from '@react-navigation/native';
import { navigationDepth, registerBrowserBack } from '../navigation/browserBack';

function state(depth: number): PartialState<NavigationState> {
  return { index: depth, routes: Array.from({ length: depth + 1 }, (_, index) => ({ name: `Screen${index}` })) };
}
function setup() {
  const entries: unknown[] = [null];
  let position = 0;
  let listener: (() => void) | undefined;
  const history = {
    get state() { return entries[position]; },
    pushState: jest.fn((value: unknown) => { entries.splice(++position); entries[position] = value; }),
    replaceState: jest.fn((value: unknown) => { entries[position] = value; }),
    go: jest.fn((delta: number) => { position += delta; }),
  };
  const browser = {
    history,
    addEventListener: jest.fn((event: string, callback: () => void) => { listener = callback; }),
    removeEventListener: jest.fn(),
  };
  let depth = 0;
  const back = jest.fn(() => { depth--; handler.sync(state(depth)); });
  const handler = registerBrowserBack(browser as unknown as Window, () => depth > 0, back);
  return { history, browser, handler, back,
    navigate(next: number) { depth = next; handler.sync(state(depth)); },
    pop() { listener?.(); },
    gesture() { history.go(-1); listener?.(); },
  };
}

test('Android browser back follows the in-app stack one screen at a time', () => {
  const app = setup();
  app.navigate(1); app.navigate(2);
  app.gesture();
  expect(app.back).toHaveBeenCalledTimes(1);
  expect(app.history.state).toEqual({ ligaproNavigationDepth: 1 });
  app.gesture();
  expect(app.back).toHaveBeenCalledTimes(2);
  expect(app.history.state).toEqual({ ligaproNavigationDepth: 0 });
  app.handler.dispose();
  expect(app.browser.removeEventListener).toHaveBeenCalledWith('popstate', expect.any(Function));
});

test('back on the initial screen keeps an in-app entry instead of exiting', () => {
  const app = setup();
  app.gesture(); app.gesture();
  expect(app.back).not.toHaveBeenCalled();
  expect(app.history.state).toEqual({ ligaproNavigationDepth: 0 });
});

test('toolbar back synchronizes history without popping the app twice', () => {
  const app = setup();
  app.navigate(1); app.navigate(2);
  app.navigate(1); // App arrow / touch swipe already navigated back.
  expect(app.history.go).toHaveBeenLastCalledWith(-1);
  app.pop();
  expect(app.back).not.toHaveBeenCalled();
  app.gesture();
  expect(app.back).toHaveBeenCalledTimes(1);
});

test('logout discards old screen depth and stale forward entries', () => {
  const app = setup();
  app.navigate(2); app.navigate(0); app.pop();
  expect(app.back).not.toHaveBeenCalled();
  app.history.go(1); app.pop();
  expect(app.history.state).toEqual({ ligaproNavigationDepth: 0 });
});

test('nested authentication navigation also contributes to back depth', () => {
  expect(navigationDepth(undefined)).toBe(0);
  expect(navigationDepth({ index: 0, routes: [{ name: 'Authentication', state: state(1) }] })).toBe(1);
});
