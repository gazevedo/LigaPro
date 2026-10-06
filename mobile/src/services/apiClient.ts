import { tokenService } from './tokenService';
let handlers: { refresh: () => Promise<void>; clear: () => Promise<void> } | null = null;
let refreshing: Promise<void> | null = null;
export function registerAuthHandlers(value: NonNullable<typeof handlers>) { handlers = value; }
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export class ApiTimeoutError extends Error {
  constructor() { super('O servidor demorou para responder. Verifique sua conexão e tente novamente.'); }
}
async function refreshOnce(): Promise<void> {
  if (!handlers) throw new ApiError(401, 'Sessão inválida ou expirada.');
  if (!refreshing) {
    refreshing = handlers.refresh().finally(() => { refreshing = null; });
  }
  await refreshing;
}
export async function apiRequest<T>(
  path: string, options: RequestInit = {}, authenticated = true, timeoutMs = 30000, refreshExpiredSession = true,
): Promise<T> {
  const baseUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');
  if (!baseUrl) throw new Error('Configure EXPO_PUBLIC_API_URL no arquivo .env.');
  async function send(accessToken?: string) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
    try {
      const response = await fetch(`${baseUrl}${path}`, { ...options, headers, signal: controller.signal });
      // Read the body within the timeout too; headers alone do not complete a request.
      const data: unknown = response.status === 204 ? undefined : await response.json().catch(error => {
        if (controller.signal.aborted) throw error;
        if (response.ok) throw new Error('O servidor retornou uma resposta inválida.');
        return null;
      });
      return { status: response.status, ok: response.ok, data };
    } catch (error) {
      if (controller.signal.aborted) throw new ApiTimeoutError();
      if (error instanceof TypeError) throw new Error('Não foi possível conectar ao servidor. Verifique sua conexão.');
      throw error;
    } finally { clearTimeout(timeout); }
  }
  const token = authenticated ? tokenService.current()?.access_token : undefined;
  let response = await send(token);
  if (response.status === 401 && authenticated) {
    if (refreshExpiredSession && tokenService.current()?.refresh_token) {
      if (token === tokenService.current()?.access_token) await refreshOnce();
      response = await send(tokenService.current()?.access_token);
    }
    if (response.status === 401) await handlers?.clear();
  }
  if (!response.ok) {
    const data = response.data;
    const detail = typeof data === 'object' && data !== null && 'detail' in data &&
      typeof data.detail === 'string' ? data.detail : `Falha na API (${response.status}).`;
    throw new ApiError(response.status, detail);
  }
  return response.data as T;
}
