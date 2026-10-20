import { AppState } from 'react-native';
import { useSquadStore } from '../stores/squadStore';
import { useTacticsStore } from '../stores/tacticsStore';
import { useStadiumStore } from '../stores/stadiumStore';
import { useFinanceStore } from '../stores/financeStore';
import { useCalendarStore } from '../stores/calendarStore';
import { useMarketStore } from '../stores/marketStore';
import * as screens from '../stores/screenStores';
import { useInboxStore } from '../stores/inboxStore';
import { useClubStore } from '../stores/clubStore';
let preparedClub: string | undefined;

export function calendarMonthFilters(month: Date) {
  return { start: new Date(month.getFullYear(), month.getMonth(), 1).toISOString(),
    end: new Date(month.getFullYear(), month.getMonth() + 1, 1).toISOString() };
}
export async function prefetchGameData(clubId: string, isCurrent: () => boolean, fresh = false) {
  if (!isCurrent()) return;
  if (preparedClub && preparedClub !== clubId) {
    for (const store of [useSquadStore, useTacticsStore, useStadiumStore, useFinanceStore, useCalendarStore, useMarketStore, useInboxStore, ...Object.values(screens)]) store.getState().reset();
  }
  preparedClub = clubId;
  const jobs = [
    () => screens.useCompetitionMatchesStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useCompetitionStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useUpcomingMatchesStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => useInboxStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useClubRankingStore.getState()[fresh ? 'refresh' : 'ensure'](1),
    () => screens.useClubDetailsStore.getState()[fresh ? 'refresh' : 'ensure'](clubId),
    () => useSquadStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => useFinanceStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useCupStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useLeagueStatisticsStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useCupStatisticsStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => useCalendarStore.getState()[fresh ? 'refresh' : 'ensure'](calendarMonthFilters(new Date())),
    () => useTacticsStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => useStadiumStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useTrainingStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useYouthStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useCatalogStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useMarketPlayersStore.getState()[fresh ? 'refresh' : 'ensure']({ sort: 'value_asc' }),
    () => screens.useMarketPlayersStore.getState()[fresh ? 'refresh' : 'ensure']({ sort: 'value_asc', type: 'sale' }),
    () => screens.useMarketPlayersStore.getState()[fresh ? 'refresh' : 'ensure']({ sort: 'value_asc', type: 'loan' }),
    () => screens.useMarketPlayersStore.getState()[fresh ? 'refresh' : 'ensure']({ sort: 'value_asc', status: 'free_agent' }),
    () => useMarketStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useHistoryStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useBankStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useTicketingStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useSponsorsStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useSettingsStore.getState()[fresh ? 'refresh' : 'ensure'](),
  ];
  // Upcoming matches use two parallel reads; three jobs keep at most four reads active.
  await Promise.allSettled(Array.from({ length: 3 }, async () => {
    while (jobs.length && isCurrent()) { const job = jobs.shift()!; await job(); }
  }));
}

export async function refreshGameData(isCurrent: () => boolean) {
  const jobs = [useClubStore, useSquadStore, useTacticsStore, useStadiumStore, useFinanceStore,
    useCalendarStore, useMarketStore, useInboxStore, ...Object.values(screens)]
    .map(store => () => store.getState().refreshCurrent());
  await Promise.allSettled(Array.from({ length: 3 }, async () => {
    while (jobs.length && isCurrent()) await jobs.shift()!();
  }));
}
export function startGameDataRefresh(clubId: string, isCurrent: () => boolean) {
  let active = true, pending = false, prepared = false, retrying = false;
  const current = () => active && isCurrent();
  const visible = () => AppState.currentState !== 'background' && AppState.currentState !== 'inactive' &&
    (typeof document === 'undefined' || document.visibilityState !== 'hidden') &&
    (typeof navigator === 'undefined' || navigator.onLine !== false);
  async function retryCompetitionData() {
    const table = screens.useCompetitionStore.getState(), matches = screens.useCompetitionMatchesStore.getState();
    if (retrying || !current() || !visible() || (table.data !== null && matches.data !== null && !table.error && !matches.error)) return;
    retrying = true;
    try {
      // Retry only missing/failed reads, even while other screens are still loading.
      await Promise.allSettled([
        table.data === null || table.error ? table.refresh() : Promise.resolve(),
        matches.data === null || matches.error ? matches.refresh() : Promise.resolve(),
      ]);
    } finally { retrying = false; }
  }
  async function run(initial: boolean) {
    if (pending || !current() || !visible()) return;
    pending = true;
    try {
      if (initial || !prepared) {
        await prefetchGameData(clubId, current, true);
        prepared = true;
      } else await refreshGameData(current);
    } finally { pending = false; }
  }
  const resume = () => { void run(false); };
  const appState = AppState.addEventListener('change', resume);
  const browserEvents = typeof window !== 'undefined' && typeof window.addEventListener === 'function';
  if (typeof document !== 'undefined') document.addEventListener('visibilitychange', resume);
  if (browserEvents) { window.addEventListener('focus', resume); window.addEventListener('online', resume); }
  void run(true);
  const timer = setInterval(() => { void run(false); }, 60000);
  const retryTimer = setInterval(() => { void retryCompetitionData(); }, 3000);
  return () => {
    active = false; clearInterval(timer); clearInterval(retryTimer); appState.remove();
    if (typeof document !== 'undefined') document.removeEventListener('visibilitychange', resume);
    if (browserEvents) { window.removeEventListener('focus', resume); window.removeEventListener('online', resume); }
  };
}
