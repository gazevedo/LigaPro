export interface Badge { id: string; name?: string; color: string; symbol: string; accent?: string; pattern?: 'stripe' | 'cross' | 'plain' }
export interface Club { supporters?: number; fan_satisfaction?: number; ranking_points?: number; ranking_position?: number; reputation?: number; country?: { id: string; name: string }; badge?: Badge; id: string; name: string; country_id: string; badge_id: string; created_at: string; ranking: number; competition_positions: unknown[]; trophies: unknown[] }
export interface Catalog { countries: { id: string; name: string }[]; badges: Badge[] }
export type PlayerSkill = 'goalkeeping' | 'speed' | 'technique' | 'passing' | 'tackling' | 'playmaking' | 'finishing';
export interface Player { estimated_potential_capacity?: number; morale?: number; can_train?: boolean; strength?: number; training_progress?: number; disease?: string | null; status?: string; physical_condition?: number; energy?: number; stars?: number; salary?: number; salary_reference?: number; market_value?: number; asking_price?: number; nationality?: string; preferred_side?: string; individual_skills?: Record<PlayerSkill, number>; innate_characteristics?: string[]; injury_type?: string | null; injury_return_at?: string | null; is_free_agent?: boolean; player_transfer_status?: string; id: string; name: string; position: string; age: number; overall: number; value: number; country_id: string; owner_club_id: string | null; current_club_id: string | null; listing?: Listing | null }

export interface Lineup { formation: string; starters: string[]; reserves: string[] }
export interface Squad { team_chemistry?: number; players: Player[]; lineup: Lineup; formations: Record<string, Record<string, number>> }
export interface Stadium { capacity: number; ticket_price: number; facilities: Record<string, number>; names: Record<string, string>; upgrade_costs: Record<string, number> }
export interface Transaction { id: string; amount: number; category: string; created_at: string }
export interface Finance { cash_balance?: number; monthly_fixed_revenue?: number; monthly_income?: number; monthly_expenses?: number; monthly_result?: number; sponsorship?: number; tv_rights?: number; ticketing?: number; other_expenses?: number; accumulated_prizes?: number; payroll_health?: string; monthly_period_end?: string; balance: number; transactions: Transaction[]; monthly_payroll?: number; total_contract_cost?: number; salary_costs?: { player_id: string; name: string; salary: number; expires_at: string; status: string }[]; salary_history?: Transaction[] }
export interface Contract { id: string; type: string; amount: number; interest: number; status: string; ends_at: string; overdue?: boolean }
export interface BankLoan { id: string; product: string; principal: number; interest_rate: number; installments: number; installment_value: number; remaining_balance: number; status: string }
export interface Bank { contracts: Contract[]; rules: Record<string, number>; loans?: BankLoan[]; products?: Record<string, { installments: number; interest_rate: number }>; credit_limit?: number; financial_risk?: string; credit_blocked?: boolean }
export interface Ticketing { attendance_share?: number; estimated_attendance?: number; supporters?: number; fan_satisfaction?: number; reputation?: number; price: number; capacity: number; income: number; history: { id: string; attendance: number; income: number }[] }
export interface Sponsors { contracts: { id: string; name: string; status: string; value: number; monthly_value?: number; ends_at: string }[]; offers: { id: string; name: string; value: number; monthly_value?: number; duration_months?: number; bonus?: number; duration_days: number; required_ranking: number }[] }
export interface CalendarEvent { kind?: string; id: string; type: string; title: string; date: string }
export interface Listing { id: string; player_id: string; seller_club_id: string; type: 'sale' | 'loan'; price: number; duration_days: number; status: string }
export interface Offer { negotiation_version?: number; salary_offer?: number; contract_months?: number; loan_months?: number; salary_share?: number; expires_at?: string; player_decision?: { accepted: boolean; reason: string }; id: string; listing_id: string; seller_club_id: string; buyer_club_id: string; amount: number; status: string }
export interface Market { listings: Listing[]; incoming: Offer[]; outgoing: Offer[]; loans: { id: string; player_id: string; owner_club_id: string; current_club_id: string; status: string; ends_at: string }[] }

export interface Competition {
  season: { number: number; starts_at: string; ends_at: string };
  division: { name: string };
  standings: { id: string; club_id: string; club_name: string; position: number; points: number; games: number; wins: number; draws: number; losses: number; goals_for: number; goals_against: number; goal_difference: number }[];
}
