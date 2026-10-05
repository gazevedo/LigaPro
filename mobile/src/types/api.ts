export interface HealthResponse { status: string; api: string; mongodb: string; }
export interface AppSetting {
  id: string; key: string; value: unknown; created_at: string; updated_at: string;
}
