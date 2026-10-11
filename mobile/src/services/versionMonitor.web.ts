import version from '../../version.json';

const reloadKey = 'ligapro-version-reload';

export function isNewerVersion(candidate: unknown): candidate is typeof version {
  if (!candidate || typeof candidate !== 'object') return false;
  const next = candidate as typeof version;
  const fields = ['major', 'minor', 'patch'] as const;
  if (!fields.every(field => Number.isSafeInteger(next[field]) && next[field] >= 0)) return false;
  for (const field of fields) {
    if (next[field] !== version[field]) return next[field] > version[field];
  }
  return false;
}

export async function checkForAppUpdate(isMounted: () => boolean) {
  if (document.visibilityState === 'hidden' || !navigator.onLine) return;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(`/app-version.json?t=${Date.now()}`, { cache: 'no-store', signal: controller.signal });
    if (!response.ok) return;
    const latest: unknown = await response.json();
    if (!isMounted() || !isNewerVersion(latest)) return;
    const release = `${latest.major}.${latest.minor}.${latest.patch}`;
    const url = new URL(window.location.href);
    if (url.searchParams.get('appVersion') === release) return;
    // A stale HTML deployment must not cause an endless restart loop.
    try {
      if (sessionStorage.getItem(reloadKey) === release) return;
      sessionStorage.setItem(reloadKey, release);
    } catch { /* Restart still works when browser storage is unavailable. */ }
    url.searchParams.set('appVersion', release);
    window.location.replace(url.toString());
  } finally {
    clearTimeout(timeout);
  }
}
