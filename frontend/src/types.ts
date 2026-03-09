export interface PredefinedPolicyConfig {
  dangerous_content: boolean;
  harassment: boolean;
  hate_speech: boolean;
  sexually_explicit: boolean;
}

export interface SafetyPolicy {
  id: string;
  name: string;
  description?: string;
  policy_content: string;
  is_default: boolean;
  predefined_policy_config: PredefinedPolicyConfig;
  created_at: string;
  updated_at?: string;
}

export interface SafetyPolicyListResponse {
  policies: SafetyPolicy[];
  total: number;
}

export interface SafetyCategory {
  category: string;
  score: number;
}

export interface SafetyAnalysisRequest {
  text_input: string;
  model_id?: string;
  policy_id?: string;
}

export interface SafetyAnalysisResponse {
  model_used: string;
  is_safe: boolean;
  safety_categories: SafetyCategory[];
  raw_output: string;
  inference_time_seconds: number;
  policy_name?: string;
}

export interface AnalysisLog {
  id: string;
  text_input: string;
  policy_id?: string;
  policy_name?: string;
  is_safe: boolean;
  safety_categories: { category: string; score: number }[];
  model_used: string;
  max_score: number;
  inference_time_seconds: number;
  created_at: string;
}

export interface AnalysisLogListResponse {
  logs: AnalysisLog[];
  total: number;
}
