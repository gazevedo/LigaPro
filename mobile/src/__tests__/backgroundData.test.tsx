import { act, render, screen } from '@testing-library/react-native';
import { Text, ActivityIndicator } from 'react-native';
import { NavigationContext } from '@react-navigation/native';
import { domainStore } from '../stores/domainStore';
import { useScreenRefresh } from '../components/useScreenRefresh';

beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());

function setup() {
  const loader = jest.fn(async () => 'initial');
  const store = domainStore(loader);
  let focused = true;
  const listeners: Record<string, () => void> = {};
  const navigation = { isFocused: () => focused, addListener: jest.fn((event: string, listener: () => void) => {
    listeners[event] = listener; return () => { delete listeners[event]; };
  }) };
  function Screen() {
    const data = store();
    useScreenRefresh(data.ensure, data.load);
    return <><Text>{data.data}</Text>{data.loading && <ActivityIndicator testID="loader" />}</>;
  }
  return { loader, store, Screen,
    focus(value: boolean) { focused = value; listeners[value ? 'focus' : 'blur']?.(); },
    navigation: navigation as unknown as NonNullable<React.ContextType<typeof NavigationContext>>,
  };
}

test('prefetched data renders immediately; the three-second refresh keeps content without a loader', async () => {
  const app = setup();
  await app.store.getState().ensure();
  await render(<app.Screen />);
  expect(screen.getByText('initial')).toBeTruthy();
  expect(app.loader).toHaveBeenCalledTimes(1);
  let finish!: (value: string) => void;
  app.loader.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  await act(async () => { jest.advanceTimersByTime(3000); });
  expect(app.loader).toHaveBeenCalledTimes(2);
  expect(screen.getByText('initial')).toBeTruthy();
  expect(screen.queryByTestId('loader')).toBeNull();
  await act(async () => { finish('updated'); });
  expect(screen.getByText('updated')).toBeTruthy();
});

test('polling stops on blur, resumes on focus and cleans up when unmounted', async () => {
  const app = setup();
  const view = await render(<NavigationContext.Provider value={app.navigation}><app.Screen /></NavigationContext.Provider>);
  await act(async () => { app.focus(false); jest.advanceTimersByTime(9000); });
  expect(app.loader).toHaveBeenCalledTimes(1);
  await act(async () => { app.focus(true); await jest.advanceTimersByTimeAsync(3000); });
  expect(app.loader).toHaveBeenCalledTimes(2);
  await view.unmount();
  await act(async () => { jest.advanceTimersByTime(9000); });
  expect(app.loader).toHaveBeenCalledTimes(2);
});

test('slow background requests never overlap', async () => {
  const app = setup();
  await app.store.getState().ensure();
  let finish!: (value: string) => void;
  app.loader.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  await render(<app.Screen />);
  await act(async () => { jest.advanceTimersByTime(12000); });
  expect(app.loader).toHaveBeenCalledTimes(2);
  await act(async () => { finish('updated'); });
});

test('initial load and prefetch share the same pending request', async () => {
  let finish!: (value: string) => void;
  const loader = jest.fn(() => new Promise<string>(resolve => { finish = resolve; }));
  const store = domainStore(loader);
  const prefetch = store.getState().ensure(), screenLoad = store.getState().ensure();
  expect(loader).toHaveBeenCalledTimes(1);
  finish('ready'); await Promise.all([prefetch, screenLoad]);
  expect(store.getState().data).toBe('ready');
});

test('queries have separate cache entries and an older response cannot overwrite the visible query', async () => {
  let first!: (value: string) => void;
  const loader = jest.fn((month: string) => month === 'October' ? new Promise<string>(resolve => { first = resolve; }) : Promise.resolve(month));
  const store = domainStore(loader);
  const october = store.getState().ensure('October');
  await store.getState().ensure('November');
  first('October'); await october;
  expect(store.getState().data).toBe('November');
  await store.getState().ensure('October');
  expect(store.getState().data).toBe('October');
  expect(loader).toHaveBeenCalledTimes(2);
});

test('a session reset discards cached and in-flight private data', async () => {
  let finish!: (value: string) => void;
  const loader = jest.fn(() => new Promise<string>(resolve => { finish = resolve; }));
  const store = domainStore(loader);
  const request = store.getState().ensure();
  store.getState().reset(); finish('private'); await request;
  expect(store.getState().data).toBeNull();
  const next = store.getState().ensure();
  expect(loader).toHaveBeenCalledTimes(2);
  finish('new account'); await next;
});

test('a late poll cannot restore stale cache after a successful mutation reload', async () => {
  let finish!: (value: string) => void;
  const loader = jest.fn((query: string) => Promise.resolve(query));
  const store = domainStore(loader);
  await store.getState().ensure('roster');
  loader.mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  const oldPoll = store.getState().refresh('roster');
  loader.mockResolvedValueOnce('after transfer');
  await store.getState().load('roster');
  finish('before transfer'); await oldPoll;
  await store.getState().ensure('other query');
  await store.getState().ensure('roster');
  expect(store.getState().data).toBe('after transfer');
});
