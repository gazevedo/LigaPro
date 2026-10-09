import { prefetchGameData } from '../services/prefetchService';
import { apiRequest } from '../services/apiClient';
import { resetDomainStores } from '../stores/domainStore';
import { useSquadStore } from '../stores/squadStore';
import { useTrainingStore } from '../stores/screenStores';
jest.mock('../services/apiClient', () => ({ ...jest.requireActual('../services/apiClient'), apiRequest: jest.fn(async () => ({})) }));
beforeEach(() => { jest.clearAllMocks(); jest.mocked(apiRequest).mockResolvedValue({}); resetDomainStores(); });

test('all dashboard destinations preload before they are opened and reuse their data', async () => {
  await prefetchGameData('club', () => true);
  const paths = jest.mocked(apiRequest).mock.calls.map(([path]) => path);
  expect(paths).toEqual(expect.arrayContaining(['/clubs/club', '/competition', '/competition/matches', '/competition/cup', '/squad', '/tactics', '/stadium', '/finance', '/finance/bank', '/finance/tickets', '/finance/sponsors', '/training', '/youth', '/history', '/game/catalog', '/market/players?sort=value_asc', '/market/mine']));
  expect(paths.filter(path => path.startsWith('/competition/statistics?'))).toHaveLength(2);
  expect(paths.filter(path => path.startsWith('/calendar?'))).toHaveLength(1);
  const requests = paths.length;
  await useSquadStore.getState().ensure();
  await useTrainingStore.getState().ensure();
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
