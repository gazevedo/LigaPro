import { tokenService } from './tokenService';
let handlers: { refresh: () => Promise<void>; clear: () => Promise<void> } | null = null;
let refreshing: Promise<void> | null = null;
export function registerAuthHandlers(value: NonNullable<typeof handlers>) { handlers = value; }
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
async function refreshOnce(): Promise<void> {
  if (!handlers) throw new ApiError(401, 'Sessão inválida ou expirada.');
  if (!refreshing) {
    refreshing = handlers.refresh().finally(() => { refreshing = null; });
  }
  await refreshing;
}
export async function apiRequest<T>(
  path: string, options: RequestInit = {}, authenticated = true,
): Promise<T> {
  const baseUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');
  if (!baseUrl) throw new Error('Configure EXPO_PUBLIC_API_URL no arquivo .env.');
  async function send(accessToken?: string) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
    try { return await fetch(`${baseUrl}${path}`, { ...options, headers, signal: controller.signal }); }
    finally { clearTimeout(timeout); }
  }
  const token = authenticated ? tokenService.current()?.access_token : undefined;
  let response = await send(token);
  if (response.status === 401 && authenticated) {
    if (tokenService.current()?.refresh_token) {
      if (token === tokenService.current()?.access_token) await refreshOnce();
      response = await send(tokenService.current()?.access_token);
    }
    if (response.status === 401) await handlers?.clear();
  }
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    const detail = typeof data === 'object' && data !== null && 'detail' in data &&
      typeof data.detail === 'string' ? data.detail : `Falha na API (${response.status}).`;
    throw new ApiError(response.status, detail);
  }
  return response.status === 204 ? undefined as T : (await response.json()) as T;
}
