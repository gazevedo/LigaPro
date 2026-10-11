import { useSquadStore } from '../stores/squadStore';
import { useTacticsStore } from '../stores/tacticsStore';
import { useStadiumStore } from '../stores/stadiumStore';
import { useFinanceStore } from '../stores/financeStore';
import { useCalendarStore } from '../stores/calendarStore';
import { useMarketStore } from '../stores/marketStore';
import * as screens from '../stores/screenStores';
import { useInboxStore } from '../stores/inboxStore';
let preparedClub: string | undefined;

export function calendarMonthFilters(month: Date) {
  return { start: new Date(month.getFullYear(), month.getMonth(), 1).toISOString(),
    end: new Date(month.getFullYear(), month.getMonth() + 1, 1).toISOString() };
}
export async function prefetchGameData(clubId: string, isCurrent: () => boolean) {
  if (!isCurrent()) return;
  if (preparedClub && preparedClub !== clubId) {
    for (const store of [useSquadStore, useTacticsStore, useStadiumStore, useFinanceStore, useCalendarStore, useMarketStore, useInboxStore, ...Object.values(screens)]) store.getState().reset();
  }
  preparedClub = clubId;
  const jobs = [
    () => screens.useUpcomingMatchesStore.getState().ensure(),
    () => useInboxStore.getState().ensure(),
    () => screens.useClubDetailsStore.getState().ensure(clubId),
    () => screens.useCompetitionStore.getState().ensure(),
    () => useSquadStore.getState().ensure(),
    () => useFinanceStore.getState().ensure(),
    () => screens.useCompetitionMatchesStore.getState().ensure(),
    () => screens.useCupStore.getState().ensure(),
    () => screens.useLeagueStatisticsStore.getState().ensure(),
    () => screens.useCupStatisticsStore.getState().ensure(),
    () => useCalendarStore.getState().ensure(calendarMonthFilters(new Date())),
    () => useTacticsStore.getState().ensure(),
    () => useStadiumStore.getState().ensure(),
    () => screens.useTrainingStore.getState().ensure(),
    () => screens.useYouthStore.getState().ensure(),
    () => screens.useCatalogStore.getState().ensure(),
    () => screens.useMarketPlayersStore.getState().ensure({ sort: 'value_asc' }),
    () => screens.useMarketPlayersStore.getState().ensure({ sort: 'value_asc', type: 'sale' }),
    () => screens.useMarketPlayersStore.getState().ensure({ sort: 'value_asc', type: 'loan' }),
    () => screens.useMarketPlayersStore.getState().ensure({ sort: 'value_asc', status: 'free_agent' }),
    () => useMarketStore.getState().ensure(),
    () => screens.useHistoryStore.getState().ensure(),
    () => screens.useBankStore.getState().ensure(),
    () => screens.useTicketingStore.getState().ensure(),
    () => screens.useSponsorsStore.getState().ensure(),
    () => screens.useSettingsStore.getState().ensure(),
  ];
  // Upcoming matches use two parallel reads; three jobs keep at most four reads active.
  await Promise.allSettled(Array.from({ length: 3 }, async () => {
    while (jobs.length && isCurrent()) { const job = jobs.shift()!; await job(); }
  }));
}
