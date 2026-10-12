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
    () => screens.useClubRankingStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useUpcomingMatchesStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => useInboxStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useClubDetailsStore.getState()[fresh ? 'refresh' : 'ensure'](clubId),
    () => screens.useCompetitionStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => useSquadStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => useFinanceStore.getState()[fresh ? 'refresh' : 'ensure'](),
    () => screens.useCompetitionMatchesStore.getState()[fresh ? 'refresh' : 'ensure'](),
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
  let active = true, pending = false;
  const current = () => active && isCurrent();
  async function run(initial: boolean) {
    if (pending || !current()) return;
    pending = true;
    try {
      if (initial) await prefetchGameData(clubId, current, true);
      else await refreshGameData(current);
    } finally { pending = false; }
  }
  void run(true);
  const timer = setInterval(() => { void run(false); }, 60000);
  return () => { active = false; clearInterval(timer); };
}
