import apiClient from './api';

export type Evaluation = {
  id: string;
  data: {
    subcontractor: string;
    project: string;
    evaluation_date: string;
    quality_score: number;
    safety_score: number;
    delivery_score: number;
    total_score: number;
    status: 'draft' | 'submitted' | 'approved' | 'rejected';
    notes?: string;
  };
  row_version: number;
};

export const subcontractorEvaluationAPI = {
  bootstrap: () => apiClient.post<{ id: string; name: string; version: number; created: boolean }>('/subcontractor-evaluation/bootstrap'),
  list: (limit = 50, offset = 0) => apiClient.get<{ data: Evaluation[]; total: number; limit: number; offset: number; has_next: boolean }>('/subcontractor-evaluation/records', { params: { limit, offset } }),
  create: (data: Omit<Evaluation['data'], 'total_score' | 'status'>) => apiClient.post('/subcontractor-evaluation/records', data),
  transition: (id: string, target_status: Evaluation['data']['status'], expected_row_version: number) => apiClient.post(`/subcontractor-evaluation/records/${id}/transition`, { target_status, expected_row_version }),
};
