const baseUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '');
export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  if (!baseUrl) throw new Error('Configure EXPO_PUBLIC_API_URL no arquivo .env.');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 8000);
  try {
    const response = await fetch(`${baseUrl}${path}`, { ...options,
      headers: { 'Content-Type': 'application/json', ...options.headers },
      signal: controller.signal });
    if (!response.ok) throw new Error(`Falha na API (${response.status}).`);
    return (await response.json()) as T;
  } finally { clearTimeout(timeout); }
}
