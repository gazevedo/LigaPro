import { waitFor } from '@testing-library/react-native';
import { domainStore, setDomainClubId } from '../stores/domainStore';
import { useAuthStore } from '../stores/authStore';
import { localGameCache } from '../services/localGameCache';

jest.mock('../services/localGameCache', () => ({ localGameCache: {
  read: jest.fn(), write: jest.fn(async () => undefined), clearUser: jest.fn(async () => undefined),
} }));
beforeEach(() => {
  jest.clearAllMocks();
  useAuthStore.setState({ user: { id: 'user-a' } as never, authenticated: true });
  setDomainClubId('club-a');
  jest.mocked(localGameCache.read).mockResolvedValue(null);
});

test('first load waits for the server and saves its result for the same user', async () => {
  let finish!: (data: { badge: string }) => void;
  const loader = jest.fn(() => new Promise<{ badge: string }>(resolve => { finish = resolve; }));
  const store = domainStore(loader, 'club-status');
  const request = store.getState().ensure();
  await waitFor(() => expect(loader).toHaveBeenCalledTimes(1));
  expect(store.getState()).toMatchObject({ data: null, loading: true });
  finish({ badge: 'my-badge' }); await request;
  expect(store.getState().data).toEqual({ badge: 'my-badge' });
  expect(localGameCache.write).toHaveBeenCalledWith('user-a', 'club-status', '[]', { badge: 'my-badge' }, expect.any(Function));
});

test('a new store restores disk data while its background refresh is still pending', async () => {
  jest.mocked(localGameCache.read).mockResolvedValueOnce({ badge: 'saved-badge' });
  let finish!: (data: { badge: string }) => void;
  const loader = jest.fn(() => new Promise<{ badge: string }>(resolve => { finish = resolve; }));
  const store = domainStore(loader, 'club-status');
  const request = store.getState().ensure();
  await waitFor(() => expect(loader).toHaveBeenCalledTimes(1));
  expect(store.getState()).toMatchObject({ data: { badge: 'saved-badge' }, loading: false });
  await store.getState().ensure();
  expect(loader).toHaveBeenCalledTimes(1);
  finish({ badge: 'updated-badge' }); await request;
  expect(store.getState().data).toEqual({ badge: 'updated-badge' });
});

test('offline refresh preserves the saved club data', async () => {
  jest.mocked(localGameCache.read).mockResolvedValueOnce({ badge: 'saved-badge' });
  const store = domainStore(async () => { throw new Error('Offline'); }, 'club-status');
  await store.getState().ensure();
  expect(store.getState()).toMatchObject({ data: { badge: 'saved-badge' }, loading: false, error: 'Offline' });
});

test('late disk responses cannot display or fetch data after changing accounts', async () => {
  let finish!: (value: unknown) => void;
  jest.mocked(localGameCache.read).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
  const loader = jest.fn(async () => 'server');
  const store = domainStore(loader, 'club-status');
  const request = store.getState().ensure();
  useAuthStore.setState({ user: { id: 'user-b' } as never });
  finish('private-user-a'); await request;
  expect(store.getState().data).toBeNull();
  expect(loader).not.toHaveBeenCalled();
});

test('screen cache keys separate users, clubs and filters', async () => {
  const loader = jest.fn(async (query: string) => query);
  const store = domainStore(loader, 'calendar');
  await store.getState().ensure('October');
  expect(localGameCache.read).toHaveBeenCalledWith('user-a:club-a', 'calendar', '["October"]');
  store.getState().reset(); setDomainClubId('club-b');
  await store.getState().ensure('November');
  expect(localGameCache.read).toHaveBeenCalledWith('user-a:club-b', 'calendar', '["November"]');
});
