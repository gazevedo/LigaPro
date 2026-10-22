import { settingsService } from '../services/settingsService';
import { calendarService } from '../services/calendarService';
import { liveMatchService } from '../services/liveMatchService';
import { domainStore } from './domainStore';
import { clubService } from '../services/clubService';
import { historyService } from '../services/historyService';
import { competitionService } from '../services/competitionService';
import { cupService } from '../services/cupService';
import { statisticsService } from '../services/statisticsService';
import { financeService } from '../services/financeService';
import { developmentService } from '../services/developmentService';
import { marketService } from '../services/marketService';

export const useOtherClubSquadStore = domainStore(clubService.squad, 'other-club-squad');
export const useClubRankingStore = domainStore(clubService.ranking, 'club-ranking');
export const useSettingsStore = domainStore(settingsService.list, 'useSettingsStore');
export const useClubDetailsStore = domainStore(clubService.get, 'useClubDetailsStore');
export const useHistoryStore = domainStore(historyService.get, 'useHistoryStore');
export const useCatalogStore = domainStore(clubService.catalog, 'useCatalogStore');
export const useCompetitionStore = domainStore(competitionService.get, 'useCompetitionStore');
export const useCompetitionMatchesStore = domainStore(competitionService.matches, 'useCompetitionMatchesStore');
export const useCupStore = domainStore(cupService.get, 'useCupStore');
export const useLeagueStatisticsStore = domainStore((divisionId?: string) => statisticsService.competition('league', 'goals', divisionId), 'useLeagueStatisticsStore');
export const useCupStatisticsStore = domainStore(() => statisticsService.competition('cup', 'goals'), 'useCupStatisticsStore');
export const useBankStore = domainStore(financeService.bank, 'useBankStore');
export const useTicketingStore = domainStore(financeService.tickets, 'useTicketingStore');
export const useSponsorsStore = domainStore(financeService.sponsors, 'useSponsorsStore');
export const useTrainingStore = domainStore(developmentService.training, 'useTrainingStore');
export const useYouthStore = domainStore(developmentService.youth, 'useYouthStore');
export const useMarketPlayersStore = domainStore(marketService.search, 'useMarketPlayersStore');

// Share the dashboard's upcoming matches between background loading and remounts.
export const useUpcomingMatchesStore = domainStore(async () => {
  const [events, upcoming] = await Promise.all([calendarService.get(), liveMatchService.upcoming()]);
  return events.flatMap(event => {
    if (!['match', 'league_match', 'cup_match', 'friendly'].includes(event.kind || event.type)) return [];
    const match = upcoming.find(item => item.id === event.reference_id);
    return match ? [{ ...match, date: event.date }] : [];
  });
}, 'upcoming-matches');
