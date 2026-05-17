export type Platform = 'trendyol' | 'amazon' | 'hepsiburada';

export type SeoTone = 'casual' | 'professional' | 'premium';

export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Variant {
  name: string;
  color: string;
  price_diff: number;
}

export interface AnalyzePayload {
  title: string;
  description: string;
  brand: string;
  price: number;
  category: string;
  stock: number;
  weight?: number;
  dimensions?: string;
  seo_keywords?: string[];
  image_urls?: string[];
  platform: Platform;
  variants?: Variant[];
}

export interface AnalysisTask {
  id: string;
  user_id: string;
  status: AnalysisStatus;
  payload: AnalyzePayload;
  seo_tone?: SeoTone | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  generated_image_url?: string | null;
}

export type StepName =
  | 'competitor_discovery'
  | 'competitor_research'
  | 'market_gap'
  | 'pricing_analysis'
  | 'seo_context'
  | 'seo_optimization'
  | 'image_generation';

export type StepStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ProgressStep {
  name: StepName;
  status: StepStatus;
  label: string;
}

export interface SSEProgressEvent {
  step: string;
  status: string;
  pct: number | string;
  message?: string;
}

export interface Competitor {
  name: string;
  price: number;
  rating: number;
  review_count: number;
  brand: string;
  source_url: string;
}

export interface MarketGapCluster {
  cluster_id: number;
  keywords: string[];
  avg_price: number;
  saturation: number;
}

export interface MarketGapResult {
  clusters: MarketGapCluster[];
  gap_opportunities: string[];
  positioning_rationale: string;
}

export interface PricingResult {
  current_position: string;
  suggested_min: number;
  suggested_max: number;
  optimal_price: number;
  confidence_score: number;
  competitor_prices: { name: string; price: number }[];
}

export interface SeoResult {
  title_suggestion: string;
  meta_description: string;
  keyword_gaps: string[];
  content_recommendations: string[];
  platform_tips: string[];
  product_development_ideas?: string[];
}

export interface VisionResult {
  generation_prompt: string;
  dominant_colors: string[];
  improvement_suggestions: string[];
}

export interface AnalysisResult {
  task_id: string;
  product_title: string;
  platform: Platform;
  analyzed_at: string;
  status: AnalysisStatus;
  seo_tone?: SeoTone;
  competitors: Competitor[];
  market_gap: MarketGapResult;
  pricing: PricingResult;
  seo: SeoResult;
  vision: VisionResult;
  generated_image_url: string | null;
}

export interface User {
  id: string;
  email: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface QuotaInfo {
  used: number;
  limit: number;
  remaining: number;
}
