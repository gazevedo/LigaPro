import version from '../../version.json';
import { checkForAppUpdate, isNewerVersion } from '../services/versionMonitor.web';

const reload = jest.fn();
const fetchVersion = jest.fn();
const saved = new Map<string, string>();
const properties = ['document', 'navigator', 'location', 'sessionStorage', 'fetch'] as const;
const original = properties.map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)] as const);
beforeEach(() => {
  jest.clearAllMocks(); saved.clear();
  Object.defineProperties(globalThis, {
    document: { configurable: true, value: { visibilityState: 'visible' } },
    navigator: { configurable: true, value: { onLine: true } },
    location: { configurable: true, value: { href: 'https://ligapro.example/?screen=tactics', replace: reload } },
    sessionStorage: { configurable: true, value: { getItem: (key: string) => saved.get(key), setItem: (key: string, value: string) => saved.set(key, value) } },
    fetch: { configurable: true, value: fetchVersion },
  });
});
afterAll(() => {
  for (const [key, descriptor] of original) {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else Reflect.deleteProperty(globalThis, key);
  }
});
const newer = { ...version, patch: version.patch + 1 };
function response(value: unknown) { fetchVersion.mockResolvedValue({ ok: true, json: async () => value }); }

test('reloads a new deployed release once with cache bypass and preserves the URL', async () => {
  response(newer);
  await checkForAppUpdate(() => true);
  expect(fetchVersion).toHaveBeenCalledWith(expect.stringMatching(/^\/app-version.json\?t=/), expect.objectContaining({ cache: 'no-store' }));
  expect(reload).toHaveBeenCalledWith(`https://ligapro.example/?screen=tactics&appVersion=${newer.major}.${newer.minor}.${newer.patch}`);
  await checkForAppUpdate(() => true);
  expect(reload).toHaveBeenCalledTimes(1);
});

test('same, older, missing and malformed releases never reload', async () => {
  for (const candidate of [version, { ...version, major: 0 }, null, {}, { ...version, patch: '999' }, { ...version, patch: -1 }]) {
    response(candidate); await checkForAppUpdate(() => true);
  }
  expect(reload).not.toHaveBeenCalled();
  expect(isNewerVersion({ major: version.major + 1, minor: 0, patch: 0 })).toBe(true);
});

test('hidden, offline and unmounted apps do not restart', async () => {
  response(newer);
  Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
  await checkForAppUpdate(() => true);
  Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true });
  Object.defineProperty(navigator, 'onLine', { value: false, configurable: true });
  await checkForAppUpdate(() => true);
  expect(fetchVersion).not.toHaveBeenCalled();
  Object.defineProperty(navigator, 'onLine', { value: true });
  await checkForAppUpdate(() => false);
  expect(reload).not.toHaveBeenCalled();
});

test('failed deployment responses and stale reload targets do not loop', async () => {
  fetchVersion.mockResolvedValue({ ok: false });
  await checkForAppUpdate(() => true);
  response(newer);
  window.location.href = `https://ligapro.example/?appVersion=${newer.major}.${newer.minor}.${newer.patch}`;
  await checkForAppUpdate(() => true);
  expect(reload).not.toHaveBeenCalled();
});
