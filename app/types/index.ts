export interface SimulationData {
  id?: number;
  request_time?: string;
  prediction: Price[][];
  variable?: {
    start_time: string;
    mean?: number;
    coeff?: number;
    sigma?: number;
    model?: string;
    std?: number;
    volatility_type?: string;
    analytics_id?: number;
  };
}

export interface Price {
  time: string;
  price: number;
}

export interface ScoreData {
  total_score: number;
  detailed_scores: {
    Interval: string;
    Increment: number | "Total";
    CRPS: number;
  }[];
}

export interface Score {
  miner_uid: number;
  prompt_score: number;
  crps: number;
  scored_time: string;
}

export interface AnalyticsData {
  id: number;
  data: any;
}
