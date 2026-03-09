import axios from 'axios';
import type {
  SafetyPolicy,
  SafetyPolicyListResponse,
  SafetyAnalysisRequest,
  SafetyAnalysisResponse,
  AnalysisLogListResponse,
  PredefinedPolicyConfig,
} from './types';

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  headers: { 'Content-Type': 'application/json' },
});

// --- Safety Analysis ---

export const analyzeSafety = async (data: SafetyAnalysisRequest): Promise<SafetyAnalysisResponse> => {
  const resp = await apiClient.post('/api/v1/safety/analyze', data);
  return resp.data;
};

export const listModels = async () => {
  const resp = await apiClient.get('/api/v1/safety/models');
  return resp.data;
};

// --- Analysis Logs ---

export const listAnalysisLogs = async (skip = 0, limit = 20): Promise<AnalysisLogListResponse> => {
  const resp = await apiClient.get('/api/v1/safety/logs', { params: { skip, limit } });
  return resp.data;
};

// --- Safety Policies ---

export const listPolicies = async (
  search = '',
  page = 1,
  limit = 10
): Promise<SafetyPolicyListResponse> => {
  const resp = await apiClient.get('/api/v1/safety/policies/', {
    params: { search, skip: (page - 1) * limit, limit },
  });
  return resp.data;
};

export const getPolicy = async (id: string): Promise<SafetyPolicy> => {
  const resp = await apiClient.get(`/api/v1/safety/policies/${id}`);
  return resp.data;
};

export const createPolicy = async (
  policy: Omit<SafetyPolicy, 'id' | 'created_at' | 'updated_at'>
): Promise<SafetyPolicy> => {
  const resp = await apiClient.post('/api/v1/safety/policies/', policy);
  return resp.data;
};

export const updatePolicy = async (
  id: string,
  policy: {
    name?: string;
    description?: string;
    policy_content?: string;
    is_default?: boolean;
    predefined_policy_config?: PredefinedPolicyConfig;
  }
): Promise<SafetyPolicy> => {
  const resp = await apiClient.patch(`/api/v1/safety/policies/${id}`, policy);
  return resp.data;
};

export const deletePolicy = async (id: string): Promise<void> => {
  await apiClient.delete(`/api/v1/safety/policies/${id}`);
};

export const checkPolicyNameExists = async (name: string): Promise<boolean> => {
  const resp = await apiClient.get(`/api/v1/safety/policies/check_name/${encodeURIComponent(name)}`);
  return resp.data.exists;
};
