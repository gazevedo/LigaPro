export interface User {
  id: string; name: string; email: string; auth_provider: string;
  avatar_url: string | null; email_verified: boolean; active: boolean;
  created_at: string; updated_at: string; last_login_at: string | null;
}
export interface Tokens { access_token: string; refresh_token: string; }
export interface AuthResponse extends Tokens {
  token_type: string; expires_in: number; refresh_expires_at: string; user: User;
}
