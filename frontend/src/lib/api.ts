import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export interface TestCase {
  id: string; title: string; description: string; category: string;
  subcategory?: string; priority: string; spec_source?: string;
  spec_ref?: string; ocp_req_id?: string; tool?: string;
  pass_fail_criteria?: string; tags?: string; status: string;
  owner?: string; notes?: string; created_at?: string; updated_at?: string;
  execution_count: number; comment_count: number;
}

export interface Execution {
  id: number; test_case_id: string; status: string; executed_by?: string;
  executed_at?: string; environment?: string; firmware_version?: string; notes?: string;
}

export interface Comment {
  id: number; test_case_id: string; author: string; content: string; created_at?: string;
}

export interface DashboardSummary {
  total: number; by_status: Record<string, number>; by_priority: Record<string, number>;
  by_category: Record<string, number>; pass_rate: number; p0_coverage: number;
}

export interface CoverageItem {
  category: string; total: number; passed: number; failed: number;
  blocked: number; skipped: number; not_started: number; coverage_pct: number;
}

export interface HeatmapCell {
  category: string; priority: string; total: number; passed: number; coverage_pct: number;
}

export interface FilterOptions {
  categories: string[]; priorities: string[]; statuses: string[]; spec_sources: string[];
}

export const fetchTestCases = (params?: Record<string, string>) =>
  api.get<TestCase[]>('/test-cases', { params }).then(r => r.data);

export const fetchTestCase = (id: string) =>
  api.get<TestCase>(`/test-cases/${id}`).then(r => r.data);

export const updateTestCase = (id: string, data: Partial<TestCase>) =>
  api.put<TestCase>(`/test-cases/${id}`, data).then(r => r.data);

export const updateStatus = (id: string, status: string) =>
  api.patch<TestCase>(`/test-cases/${id}/status`, { status }).then(r => r.data);

export const bulkUpdateStatus = (ids: string[], status: string) =>
  api.patch('/test-cases/bulk-status', { ids, status }).then(r => r.data);

export const fetchFilters = () =>
  api.get<FilterOptions>('/test-cases/filters').then(r => r.data);

export const fetchExecutions = (testId: string) =>
  api.get<Execution[]>(`/test-cases/${testId}/executions`).then(r => r.data);

export const createExecution = (testId: string, data: Partial<Execution>) =>
  api.post<Execution>(`/test-cases/${testId}/executions`, data).then(r => r.data);

export const fetchComments = (testId: string) =>
  api.get<Comment[]>(`/test-cases/${testId}/comments`).then(r => r.data);

export const createComment = (testId: string, data: { author: string; content: string }) =>
  api.post<Comment>(`/test-cases/${testId}/comments`, data).then(r => r.data);

export const fetchSummary = () =>
  api.get<DashboardSummary>('/dashboard/summary').then(r => r.data);

export const fetchCoverage = () =>
  api.get<CoverageItem[]>('/dashboard/coverage').then(r => r.data);

export const fetchHeatmap = () =>
  api.get<HeatmapCell[]>('/dashboard/heatmap').then(r => r.data);

export const importMarkdown = (file: File, specSource?: string) => {
  const fd = new FormData();
  fd.append('file', file);
  if (specSource) fd.append('spec_source', specSource);
  return api.post('/import/markdown', fd).then(r => r.data);
};

export const exportCsv = () => window.open('/api/export/csv', '_blank');
export default api;
