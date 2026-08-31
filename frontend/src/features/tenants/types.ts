export type CreditScore = 'reliable' | 'average' | 'problematic' | 'no_data';

export interface CreditScoreMetrics {
  total_payments: number;
  on_time_payments: number;
  on_time_percent: number;
  late_payments: number;
  avg_delay_days: number;
  severe_late_count: number;
}

export interface TenantScore {
  tenant_id: string;
  score: CreditScore;
  metrics: CreditScoreMetrics;
  updated_at: string;
}
