import { calendarMonthFilters, prefetchGameData, startGameDataRefresh, refreshGameData } from '../services/prefetchService';
import { apiRequest } from '../services/apiClient';
import { resetDomainStores } from '../stores/domainStore';
import { useSquadStore } from '../stores/squadStore';
import * as screens from '../stores/screenStores';
import { useTacticsStore } from '../stores/tacticsStore';
import { useStadiumStore } from '../stores/stadiumStore';
import { useFinanceStore } from '../stores/financeStore';
import { useCalendarStore } from '../stores/calendarStore';
import { useMarketStore } from '../stores/marketStore';
import { useInboxStore } from '../stores/inboxStore';
import { AppState, AppStateStatus } from 'react-native';
jest.mock('../services/apiClient', () => ({ ...jest.requireActual('../services/apiClient'), apiRequest: jest.fn(async () => ({})) }));
beforeEach(() => { jest.clearAllMocks(); jest.mocked(AppState.addEventListener).mockReturnValue({ remove: jest.fn() }); jest.mocked(apiRequest).mockImplementation(async path => path.startsWith('/calendar?') || path === '/matches/upcoming' ? [] : {}); resetDomainStores(); });

test('all dashboard destinations preload before they are opened and reuse their data', async () => {
  await prefetchGameData('club', () => true);
  const paths = jest.mocked(apiRequest).mock.calls.map(([path]) => path);
  expect(paths.slice(0, 2)).toEqual(['/competition/matches', '/competition']);
  expect(paths).toEqual(expect.arrayContaining(['/clubs/club', '/competition', '/competition/matches', '/competition/cup', '/squad', '/tactics', '/stadium', '/finance', '/finance/bank', '/finance/tickets', '/finance/sponsors', '/training', '/youth', '/history', '/game/catalog', '/market/players?sort=value_asc', '/market/mine', '/settings', '/market/players?sort=value_asc&type=sale', '/market/players?sort=value_asc&type=loan', '/market/players?sort=value_asc&status=free_agent']));
  expect(paths.filter(path => path.startsWith('/competition/statistics?'))).toHaveLength(2);
  expect(paths.filter(path => path.startsWith('/calendar?'))).toHaveLength(2);
  const requests = paths.length;
  await screens.useClubDetailsStore.getState().ensure('club');
  await useCalendarStore.getState().ensure(calendarMonthFilters(new Date()));
  const marketQueries: Record<string, string>[] = [{ sort: 'value_asc' }, { sort: 'value_asc', type: 'sale' },
    { sort: 'value_asc', type: 'loan' }, { sort: 'value_asc', status: 'free_agent' }];
  for (const query of marketQueries) {
    await screens.useMarketPlayersStore.getState().ensure(query);
  }
  for (const store of [useSquadStore, useTacticsStore, useStadiumStore, useFinanceStore,
    useMarketStore, useInboxStore, screens.useCompetitionStore, screens.useCompetitionMatchesStore,
    screens.useCupStore, screens.useLeagueStatisticsStore, screens.useCupStatisticsStore,
    screens.useTrainingStore, screens.useYouthStore, screens.useCatalogStore, screens.useHistoryStore,
    screens.useBankStore, screens.useTicketingStore, screens.useSponsorsStore,
    screens.useUpcomingMatchesStore, screens.useSettingsStore]) {
    await store.getState().ensure();
    expect(store.getState().loading).toBe(false);
    expect(store.getState().data).not.toBeNull();
  }
  expect(apiRequest).toHaveBeenCalledTimes(requests);
});

test('queued prefetch jobs stop after leaving the session and concurrency is limited to four', async () => {
  let active = true;
  const finishes: (() => void)[] = [];
  jest.mocked(apiRequest).mockImplementation(() => new Promise(resolve => { finishes.push(() => resolve({})); }));
  const task = prefetchGameData('club', () => active);
  expect(apiRequest).toHaveBeenCalledTimes(4);
  active = false;
  for (const finish of finishes) finish();
  await task;
  expect(apiRequest).toHaveBeenCalledTimes(4);
});


test('login fetches fresh data once, refreshes every minute and stops after logout', async () => {
  await prefetchGameData('club', () => true);
  jest.mocked(apiRequest).mockClear();
  jest.useFakeTimers();
  let active = true;
  const stop = startGameDataRefresh('club', () => active);
  try {
    await jest.advanceTimersByTimeAsync(0);
    const initial = jest.mocked(apiRequest).mock.calls.length;
    expect(initial).toBeGreaterThan(20);
    await jest.advanceTimersByTimeAsync(59999);
    expect(apiRequest).toHaveBeenCalledTimes(initial);
    await jest.advanceTimersByTimeAsync(1);
    expect(jest.mocked(apiRequest).mock.calls.length).toBeGreaterThan(initial);
    const refreshed = jest.mocked(apiRequest).mock.calls.length;
    active = false; stop();
    await jest.advanceTimersByTimeAsync(120000);
    expect(apiRequest).toHaveBeenCalledTimes(refreshed);
  } finally { stop(); jest.useRealTimers(); }
});

test('background refresh preserves selected calendar month and market filters', async () => {
  await prefetchGameData('club', () => true);
  const month = calendarMonthFilters(new Date(2027, 0, 1));
  const filters = { name: 'João', position: 'MID', sort: 'strength_desc' };
  await useCalendarStore.getState().ensure(month);
  await screens.useMarketPlayersStore.getState().ensure(filters);
  jest.mocked(apiRequest).mockClear();
  await refreshGameData(() => true);
  expect(apiRequest).toHaveBeenCalledWith(`/calendar?${new URLSearchParams(month)}`);
  expect(apiRequest).toHaveBeenCalledWith(`/market/players?${new URLSearchParams(filters)}`);
  expect(jest.mocked(apiRequest).mock.calls.filter(([path]) => path.startsWith('/market/players?'))).toHaveLength(1);
});


test('minute ticks do not overlap a slow initial load', async () => {
  jest.useFakeTimers();
  const finishes: (() => void)[] = [];
  jest.mocked(apiRequest).mockImplementation(() => new Promise(resolve => { finishes.push(() => resolve({})); }));
  const stop = startGameDataRefresh('club', () => true);
  try {
    await jest.advanceTimersByTimeAsync(120000);
    expect(apiRequest).toHaveBeenCalledTimes(4);
    stop();
    for (const finish of finishes) finish();
    await jest.advanceTimersByTimeAsync(0);
  } finally { stop(); jest.useRealTimers(); }
});

test('failed league data retries in background without reloading other screens', async () => {
  jest.useFakeTimers();
  let tableReads = 0;
  jest.mocked(apiRequest).mockImplementation(async path => {
    if (path === '/competition') {
      tableReads++;
      if (tableReads === 1) throw new Error('Falha temporária');
      return { standings: [{ club_id: 'club' }] };
    }
    if (path === '/competition/matches') return [{ id: 'game', status: 'scheduled', date: new Date().toISOString() }];
    return path.startsWith('/calendar?') || path === '/matches/upcoming' ? [] : {};
  });
  const stop = startGameDataRefresh('club', () => true);
  try {
    await jest.advanceTimersByTimeAsync(0);
    expect(tableReads).toBe(1);
    const initial = jest.mocked(apiRequest).mock.calls.length;
    await jest.advanceTimersByTimeAsync(3000);
    expect(tableReads).toBe(2);
    expect(jest.mocked(apiRequest).mock.calls.length).toBe(initial + 1);
    expect(screens.useCompetitionStore.getState().data?.standings).toHaveLength(1);
    await jest.advanceTimersByTimeAsync(9000);
    expect(jest.mocked(apiRequest).mock.calls.length).toBe(initial + 1);
  } finally { stop(); jest.useRealTimers(); }
});

test('returning to the app refreshes data immediately and removes the listener on logout', async () => {
  jest.useFakeTimers();
  let listener: ((state: AppStateStatus) => void) | undefined;
  const remove = jest.fn();
  const subscription = jest.spyOn(AppState, 'addEventListener').mockImplementation((_event, callback) => {
    listener = callback;
    return { remove };
  });
  const stop = startGameDataRefresh('club', () => true);
  try {
    await jest.advanceTimersByTimeAsync(0);
    jest.mocked(apiRequest).mockClear();
    listener?.('active');
    await jest.advanceTimersByTimeAsync(0);
    expect(apiRequest).toHaveBeenCalledWith('/competition/matches');
    expect(apiRequest).toHaveBeenCalledWith('/competition');
    stop();
    expect(remove).toHaveBeenCalled();
    jest.mocked(apiRequest).mockClear();
    listener?.('active');
    await jest.advanceTimersByTimeAsync(60000);
    expect(apiRequest).not.toHaveBeenCalled();
  } finally { stop(); subscription.mockRestore(); jest.useRealTimers(); }
});

test('future scheduled games do not trigger catch-up polling', async () => {
  jest.useFakeTimers();
  jest.mocked(apiRequest).mockImplementation(async path => {
    if (path === '/competition/matches') return [{ id: 'future', date: new Date(Date.now() + 86400000).toISOString(), status: 'scheduled' }];
    return path.startsWith('/calendar?') || path === '/matches/upcoming' ? [] : {};
  });
  const stop = startGameDataRefresh('club', () => true);
  try {
    await jest.advanceTimersByTimeAsync(0);
    jest.mocked(apiRequest).mockClear();
    await jest.advanceTimersByTimeAsync(15000);
    expect(apiRequest).not.toHaveBeenCalled();
  } finally { stop(); jest.useRealTimers(); }
});


test('league recovers while secondary screens are still loading in background', async () => {
  jest.useFakeTimers();
  let tableReads = 0;
  const finishMarket: (() => void)[] = [];
  jest.mocked(apiRequest).mockImplementation(async path => {
    if (path === '/competition') {
      tableReads++;
      if (tableReads === 1) throw new Error('Falha temporária');
      return { standings: [] };
    }
    if (path.startsWith('/market/players')) return new Promise(resolve => { finishMarket.push(() => resolve([])); });
    return path.startsWith('/calendar?') || path === '/matches/upcoming' ? [] : {};
  });
  const stop = startGameDataRefresh('club', () => true);
  try {
    await jest.advanceTimersByTimeAsync(0);
    expect(tableReads).toBe(1);
    expect(finishMarket.length).toBeGreaterThan(0);
    await jest.advanceTimersByTimeAsync(3000);
    expect(tableReads).toBe(2);
    expect(screens.useCompetitionStore.getState().data).not.toBeNull();
  } finally {
    stop();
    for (const finish of finishMarket) finish();
    await jest.advanceTimersByTimeAsync(0);
    jest.useRealTimers();
  }
});
