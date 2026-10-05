export interface Club { country?: { id: string; name: string }; badge?: { id: string; color: string; symbol: string }; id: string; name: string; country_id: string; badge_id: string; created_at: string; ranking: number; competition_positions: unknown[]; trophies: unknown[] }
export interface Catalog { countries: { id: string; name: string }[]; badges: { id: string; name: string; color: string; symbol: string }[] }
export interface Player { strength?: number; training_level?: number; disease?: string | null; status?: string; id: string; name: string; position: string; age: number; overall: number; value: number; country_id: string; owner_club_id: string; current_club_id: string; listing?: Listing | null }
export interface Lineup { formation: string; starters: string[]; reserves: string[] }
export interface Squad { players: Player[]; lineup: Lineup; formations: Record<string, Record<string, number>> }
export interface Stadium { capacity: number; ticket_price: number; facilities: Record<string, number>; names: Record<string, string>; upgrade_costs: Record<string, number> }
export interface Transaction { id: string; amount: number; category: string; created_at: string }
export interface Finance { balance: number; transactions: Transaction[] }
export interface Contract { id: string; type: string; amount: number; interest: number; status: string; ends_at: string; overdue?: boolean }
export interface Bank { contracts: Contract[]; rules: Record<string, number> }
export interface Ticketing { price: number; capacity: number; income: number; history: { id: string; attendance: number; income: number }[] }
export interface Sponsors { contracts: { id: string; name: string; status: string; value: number; ends_at: string }[]; offers: { id: string; name: string; value: number; duration_days: number; required_ranking: number }[] }
export interface CalendarEvent { id: string; type: string; title: string; date: string }
export interface Listing { id: string; player_id: string; seller_club_id: string; type: 'sale' | 'loan'; price: number; duration_days: number; status: string }
export interface Offer { id: string; listing_id: string; seller_club_id: string; buyer_club_id: string; amount: number; status: string }
export interface Market { listings: Listing[]; incoming: Offer[]; outgoing: Offer[]; loans: { id: string; player_id: string; owner_club_id: string; current_club_id: string; status: string; ends_at: string }[] }

export interface Competition {
  season: { number: number; starts_at: string; ends_at: string };
  division: { name: string };
  standings: { id: string; club_id: string; club_name: string; position: number; points: number; games: number; wins: number; draws: number; losses: number; goals_for: number; goals_against: number; goal_difference: number }[];
}
