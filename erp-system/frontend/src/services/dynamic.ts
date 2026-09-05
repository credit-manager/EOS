import apiClient from './api';

export type DynamicColumn = {
  field: string;
  label?: string;
  label_ar?: string;
  type?: string;
  sortable?: boolean;
  maskable?: boolean;
  relation?: { entity_code: string; display_field: string };
};

export type DynamicListSchema = {
  entity_code: string;
  entity_name?: string;
  entity_name_ar?: string;
  columns: DynamicColumn[];
  filters: Array<{ field: string; label?: string; type: string; operators: string[] }>;
  actions?: Record<string, boolean>;
  pagination?: { default_limit: number; max_limit: number };
};

export type DynamicRecordsResponse = {
  status: string;
  data: Record<string, unknown>[];
  count: number;
  pagination: { total: number; limit: number; offset: number; has_next: boolean };
};

export const dynamicAPI = {
  listSchema: (entityCode: string) =>
    apiClient.get<{ data: DynamicListSchema }>(`/dynamic/entities/${encodeURIComponent(entityCode)}/ui/list`),
  records: (entityCode: string, params: { filters?: string; sort?: string; limit: number; offset: number }) =>
    apiClient.get<DynamicRecordsResponse>(`/dynamic/entities/${encodeURIComponent(entityCode)}/records`, { params }),
  formSchema: (entityCode: string, mode: 'create' | 'edit' = 'create') =>
    apiClient.get(`/dynamic/entities/${encodeURIComponent(entityCode)}/ui/form`, { params: { mode } }),
  lookup: (entityCode: string, fieldCode: string, q: string, limit = 20) =>
    apiClient.get(`/dynamic/entities/${encodeURIComponent(entityCode)}/ui/lookup/${encodeURIComponent(fieldCode)}`, { params: { q, limit } }),
};
