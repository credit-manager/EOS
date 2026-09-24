import { API, api } from './api';

export interface Tenant {
  id: string;
  name: string;
  owner: string;
  industry: string;
  country: string;
  plan: string;
  status: string;
  users: number;
  storage: string;
  aiUsage: string;
  createdAt: string;
  lastActive: string;
}

export interface User {
  id: string;
  email: string;
  tenant: string;
  role: string;
  status: string;
  mfa: boolean;
  lastLogin: string;
  created: string;
  sessions: number;
  riskStatus: string;
}

export interface HealthStatus {
  api: { status: string; latency: number };
  database: { status: string };
  aiServices: { status: string };
  backgroundJobs: { status: string };
  queue: { status: string };
  storage: { status: string };
  emailService: { status: string };
  paymentGateway: { status: string };
  externalIntegrations: { status: string };
}

export interface Plan {
  id: string;
  code: string;
  name: string;
  description: string;
  priceMonthly: number;
  priceYearly: number;
  maxUsers: number;
  maxStorageGb: number;
  features: Record<string, boolean>;
  isActive: boolean;
}

export interface AuditEvent {
  id: string;
  user: string;
  tenant: string;
  action: string;
  resource: string;
  timestamp: string;
  ip: string;
  device: string;
  result: string;
}

export interface Metric {
  name: string;
  value: number;
  unit: string;
  timestamp: string;
}

export interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  recipient: string;
  status: string;
  createdAt: string;
}

export interface TenantListResponse {
  tenants: Tenant[];
  total: number;
}

export interface UserListResponse {
  users: User[];
  total: number;
}

export async function getTenants(token: string): Promise<TenantListResponse> {
  return api<TenantListResponse>(`${API}/tenants`, token);
}

export async function getUsers(token: string): Promise<UserListResponse> {
  return api<UserListResponse>(`${API}/users`, token);
}

export async function getHealth(token: string): Promise<HealthStatus> {
  return api<HealthStatus>(`${API}/health`, token);
}

export async function getPlans(token: string): Promise<Plan[]> {
  return api<Plan[]>(`${API}/billing/plans`, token);
}

export async function getSubscription(token: string) {
  return api(`${API}/billing/subscription`, token);
}

export async function getAuditEvents(token: string, params?: {
  limit?: number;
  action?: string;
  success?: boolean;
}): Promise<{ events: AuditEvent[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', String(params.limit));
  if (params?.action) searchParams.set('action', params.action);
  if (params?.success !== undefined) searchParams.set('success', String(params.success));
  const query = searchParams.toString();
  return api(`${API}/audit/events${query ? '?' + query : ''}`, token);
}

export async function getMetrics(token: string): Promise<Metric[]> {
  return api<Metric[]>(`${API}/metrics`, token);
}

export async function getNotifications(token: string): Promise<Notification[]> {
  return api<Notification[]>(`${API}/notifications`, token);
}

export async function createNotification(token: string, data: {
  type: string;
  title: string;
  message: string;
  recipients: string[];
}): Promise<Notification> {
  return api<Notification>(`${API}/notifications`, token, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export interface FeatureFlag {
  id: string;
  code: string;
  name: string;
  description: string;
  isGlobal: boolean;
  enabledPlans: string[];
  enabledTenants: string[];
  isActive: boolean;
  createdAt: string;
}

export async function getFeatureFlags(token: string): Promise<{ flags: FeatureFlag[] }> {
  return api<{ flags: FeatureFlag[] }>(`${API}/feature-flags`, token);
}

export async function createFeatureFlag(token: string, data: Partial<FeatureFlag>): Promise<{ id: string }> {
  return api(`${API}/feature-flags`, token, { method: 'POST', body: JSON.stringify(data) });
}

export async function updateFeatureFlag(token: string, id: string, data: Partial<FeatureFlag>): Promise<{ status: string }> {
  return api(`${API}/feature-flags/${id}`, token, { method: 'PATCH', body: JSON.stringify(data) });
}

export async function deleteFeatureFlag(token: string, id: string): Promise<{ status: string }> {
  return api(`${API}/feature-flags/${id}`, token, { method: 'DELETE' });
}

export interface BillingKPIs {
  mrr: number;
  arr: number;
  totalRevenue: number;
  outstanding: number;
  activeSubscriptions: number;
  totalPlans: number;
}

export interface Invoice {
  id: string;
  tenantId: string;
  subscriptionId: string;
  amount: number;
  currency: string;
  status: string;
  dueDate: string;
  paidAt: string;
  createdAt: string;
}

export async function getBillingKPIs(token: string): Promise<BillingKPIs> {
  return api<BillingKPIs>(`${API}/billing/kpis`, token);
}

export async function getInvoices(token: string): Promise<{ invoices: Invoice[] }> {
  return api<{ invoices: Invoice[] }>(`${API}/billing/invoices`, token);
}

export interface AIStats {
  apiRequests: number;
  avgLatencyMs: number;
  totalLlmConfigs: number;
  tokenUsage: string;
  cost: number;
}

export async function getAIStats(token: string): Promise<AIStats> {
  return api<AIStats>(`${API}/ai/stats`, token);
}
