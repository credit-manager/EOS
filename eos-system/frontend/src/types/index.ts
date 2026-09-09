/**
 * EOS System — TypeScript Types
 * All type definitions for the application
 */

// =====================================================
// Auth Types
// =====================================================

export interface LoginRequest {
  email: string;
  password: string;
  tenant_id: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RegisterRequest {
  company_name: string;
  company_name_ar: string;
  email: string;
  password: string;
  industry: string;
  employee_count?: number;
}

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  first_name_ar?: string;
  last_name_ar?: string;
  phone?: string;
  role: string;
  tenant_id: string;
  is_active: boolean;
  last_login_at?: string;
  created_at: string;
}

// =====================================================
// Tenant Types
// =====================================================

export interface Tenant {
  id: string;
  name: string;
  name_ar: string;
  slug: string;
  industry: string;
  employee_count?: number;
  email: string;
  phone?: string;
  status: string;
  subscription_plan: string;
  subscription_expires_at?: string;
  created_at: string;
  updated_at: string;
}

// =====================================================
// Accounting Types
// =====================================================

export interface Account {
  id: string;
  code: string;
  name: string;
  name_ar: string;
  account_type: 'asset' | 'liability' | 'equity' | 'revenue' | 'expense';
  parent_id?: string;
  balance: number;
  currency: string;
  is_active: boolean;
  created_at: string;
  children?: Account[];
}

export interface AccountCreate {
  code: string;
  name: string;
  name_ar: string;
  account_type: string;
  parent_id?: string;
  currency?: string;
  is_active?: boolean;
}

export interface JournalEntry {
  id: string;
  entry_number: string;
  entry_date: string;
  description: string;
  description_ar?: string;
  total_debit: number;
  total_credit: number;
  status: 'draft' | 'posted' | 'reversed';
  reference?: string;
  source_module?: string;
  created_by?: string;
  created_at: string;
  lines?: JournalEntryLine[];
}

export interface JournalEntryLine {
  id: string;
  journal_entry_id: string;
  account_id: string;
  account_code?: string;
  account_name?: string;
  debit: number;
  credit: number;
  description?: string;
}

export interface JournalEntryCreate {
  entry_date: string;
  description: string;
  description_ar?: string;
  lines: JournalEntryLineCreate[];
  reference?: string;
  source_module?: string;
}

export interface JournalEntryLineCreate {
  account_id: string;
  debit: number;
  credit: number;
  description?: string;
}

export interface TrialBalance {
  accounts: Account[];
  total_debit: number;
  total_credit: number;
  as_of_date: string;
}

export interface IncomeStatement {
  period_start: string;
  period_end: string;
  revenue: FinancialStatementItem[];
  total_revenue: number;
  expenses: FinancialStatementItem[];
  total_expenses: number;
  net_income: number;
}

export interface BalanceSheet {
  as_of_date: string;
  assets: FinancialStatementItem[];
  total_assets: number;
  liabilities: FinancialStatementItem[];
  total_liabilities: number;
  equity: FinancialStatementItem[];
  total_equity: number;
  total_liabilities_and_equity: number;
}

export interface FinancialStatementItem {
  account_id: string;
  account_name: string;
  account_name_ar: string;
  amount: number;
}

// =====================================================
// Inventory Types
// =====================================================

export interface Product {
  id: string;
  sku: string;
  name: string;
  name_ar: string;
  description?: string;
  category_id?: string;
  unit_price: number;
  cost_price: number;
  currency: string;
  current_stock: number;
  min_stock: number;
  max_stock?: number;
  barcode?: string;
  is_active: boolean;
  created_at: string;
  category?: Category;
}

export interface ProductCreate {
  sku: string;
  name: string;
  name_ar: string;
  description?: string;
  category_id?: string;
  unit_price: number;
  cost_price: number;
  currency?: string;
  min_stock?: number;
  max_stock?: number;
  barcode?: string;
  is_active?: boolean;
}

export interface Category {
  id: string;
  name: string;
  name_ar: string;
  parent_id?: string;
  is_active: boolean;
  created_at: string;
  children?: Category[];
}

export interface Warehouse {
  id: string;
  code: string;
  name: string;
  name_ar: string;
  address?: string;
  address_ar?: string;
  is_active: boolean;
  created_at: string;
}

export interface WarehouseCreate {
  code: string;
  name: string;
  name_ar: string;
  address?: string;
  address_ar?: string;
  is_active?: boolean;
}

export interface StockMovement {
  id: string;
  product_id: string;
  warehouse_id: string;
  movement_type: 'in' | 'out' | 'transfer' | 'adjustment';
  quantity: number;
  unit_cost?: number;
  total_cost?: number;
  reference?: string;
  notes?: string;
  movement_date: string;
  created_at: string;
  product?: Product;
  warehouse?: Warehouse;
}

export interface StockMovementCreate {
  product_id: string;
  warehouse_id: string;
  movement_type: string;
  quantity: number;
  unit_cost?: number;
  reference?: string;
  notes?: string;
  movement_date: string;
}

export interface LowStockAlert {
  product_id: string;
  sku: string;
  name: string;
  name_ar: string;
  current_stock: number;
  min_stock: number;
  warehouse_name?: string;
}

// =====================================================
// HR Types
// =====================================================

export interface Employee {
  id: string;
  employee_id: string;
  first_name: string;
  last_name: string;
  first_name_ar?: string;
  last_name_ar?: string;
  email: string;
  phone?: string;
  department_id?: string;
  position_id?: string;
  hire_date: string;
  salary: number;
  currency: string;
  status: string;
  national_id?: string;
  social_insurance_number?: string;
  created_at: string;
  department?: Department;
  position?: Position;
}

export interface EmployeeCreate {
  employee_id: string;
  first_name: string;
  last_name: string;
  first_name_ar?: string;
  last_name_ar?: string;
  email: string;
  phone?: string;
  department_id?: string;
  position_id?: string;
  hire_date: string;
  salary: number;
  currency?: string;
  national_id?: string;
  social_insurance_number?: string;
}

export interface Department {
  id: string;
  code: string;
  name: string;
  name_ar: string;
  manager_id?: string;
  parent_id?: string;
  employee_count: number;
  created_at: string;
}

export interface DepartmentCreate {
  code: string;
  name: string;
  name_ar: string;
  manager_id?: string;
  parent_id?: string;
}

export interface Position {
  id: string;
  name: string;
  name_ar: string;
  department_id?: string;
  created_at: string;
}

export interface AttendanceRecord {
  id: string;
  employee_id: string;
  date: string;
  clock_in?: string;
  clock_out?: string;
  status: 'present' | 'absent' | 'late' | 'leave';
  overtime_hours: number;
  notes?: string;
  hours_worked: number;
  created_at: string;
  employee?: Employee;
}

export interface AttendanceRecordCreate {
  employee_id: string;
  date: string;
  clock_in?: string;
  clock_out?: string;
  status: string;
  overtime_hours?: number;
  notes?: string;
}

// =====================================================
// Sales & CRM Types
// =====================================================

export interface Customer {
  id: string;
  name: string;
  name_ar?: string;
  type: 'individual' | 'company';
  email?: string;
  phone?: string;
  address?: string;
  tax_id?: string;
  total_orders: number;
  total_spent: number;
  created_at: string;
}

export interface CustomerCreate {
  name: string;
  name_ar?: string;
  type?: string;
  email?: string;
  phone?: string;
  address?: string;
  tax_id?: string;
}

export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  company_name?: string;
  email?: string;
  phone?: string;
  source?: string;
  status: 'new' | 'contacted' | 'qualified' | 'unqualified';
  score: number;
  notes?: string;
  created_at: string;
}

export interface LeadCreate {
  first_name: string;
  last_name: string;
  company_name?: string;
  email?: string;
  phone?: string;
  source?: string;
  notes?: string;
}

export interface Opportunity {
  id: string;
  lead_id?: string;
  customer_id?: string;
  name: string;
  stage: 'qualification' | 'needs_analysis' | 'proposal' | 'negotiation' | 'closed_won' | 'closed_lost';
  amount: number;
  currency: string;
  expected_close_date?: string;
  probability?: number;
  notes?: string;
  created_at: string;
  lead?: Lead;
  customer?: Customer;
}

export interface OpportunityCreate {
  lead_id?: string;
  customer_id?: string;
  name: string;
  stage?: string;
  amount: number;
  currency?: string;
  expected_close_date?: string;
  probability?: number;
  notes?: string;
}

export interface Quote {
  id: string;
  quote_number: string;
  opportunity_id?: string;
  customer_id: string;
  status: 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired';
  total_amount: number;
  valid_until: string;
  notes?: string;
  created_at: string;
  items?: QuoteItem[];
}

export interface QuoteItem {
  id: string;
  quote_id: string;
  product_id: string;
  product_name?: string;
  quantity: number;
  unit_price: number;
  discount_percent?: number;
  total: number;
}

export interface QuoteCreate {
  opportunity_id?: string;
  customer_id: string;
  valid_until: string;
  notes?: string;
  items: QuoteItemCreate[];
}

export interface QuoteItemCreate {
  product_id: string;
  quantity: number;
  unit_price: number;
  discount_percent?: number;
}

// =====================================================
// Projects Types
// =====================================================

export interface Project {
  id: string;
  name: string;
  name_ar?: string;
  description?: string;
  client_id?: string;
  start_date: string;
  end_date?: string;
  budget?: number;
  currency: string;
  manager_id?: string;
  status: 'planning' | 'in_progress' | 'on_hold' | 'completed' | 'cancelled';
  progress: number;
  created_at: string;
  tasks?: Task[];
}

export interface ProjectCreate {
  name: string;
  name_ar?: string;
  description?: string;
  client_id?: string;
  start_date: string;
  end_date?: string;
  budget?: number;
  currency?: string;
  manager_id?: string;
}

export interface Task {
  id: string;
  project_id: string;
  name: string;
  name_ar?: string;
  description?: string;
  assignee_id?: string;
  assignee_name?: string;
  start_date?: string;
  due_date?: string;
  estimated_hours?: number;
  actual_hours?: number;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  status: 'todo' | 'in_progress' | 'review' | 'done';
  parent_task_id?: string;
  created_at: string;
  subtasks?: Task[];
}

export interface TaskCreate {
  project_id: string;
  name: string;
  name_ar?: string;
  description?: string;
  assignee_id?: string;
  start_date?: string;
  due_date?: string;
  estimated_hours?: number;
  priority?: string;
  parent_task_id?: string;
}

export interface TimeEntry {
  id: string;
  task_id: string;
  project_id: string;
  employee_id: string;
  date: string;
  hours: number;
  description?: string;
  created_at: string;
  task?: Task;
  employee?: Employee;
}

export interface TimeEntryCreate {
  task_id: string;
  project_id: string;
  date: string;
  hours: number;
  description?: string;
}

// =====================================================
// AI Types
// =====================================================

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface ChatRequest {
  message: string;
  context?: Record<string, any>;
  module?: string;
}

export interface ChatResponse {
  response: string;
  suggestions?: string[];
  actions?: AIAction[];
  confidence: number;
}

export interface AIAction {
  type: string;
  module: string;
  action: string;
  params?: Record<string, any>;
}

export interface ForecastRequest {
  module: string;
  metric: string;
  period_days?: number;
  filters?: Record<string, any>;
}

export interface ForecastResponse {
  metric: string;
  current_value: number;
  predicted_values: number[];
  confidence_interval: number[];
  trend: 'increasing' | 'decreasing' | 'stable';
  insights: string[];
}

export interface OCRRequest {
  image_url?: string;
  image_base64?: string;
  document_type: 'invoice' | 'receipt' | 'id_card' | 'contract';
}

export interface OCRResponse {
  extracted_data: Record<string, any>;
  confidence: number;
  document_type: string;
  raw_text: string;
}

// =====================================================
// Common Types
// =====================================================

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// =====================================================
// Analytics Types (P65)
// =====================================================

export interface ExecutiveSummary {
  period: string;
  start_date: string;
  end_date: string;
  revenue: number;
  expenses: number;
  profit: number;
  profit_margin: number;
  receivables: number;
  payables: number;
  cash_position: number;
  active_customers: number;
  active_projects: number;
}

export interface KPI {
  name: string;
  current: number;
  previous: number;
  change: number;
  trend: 'up' | 'down' | 'flat';
  format: 'currency' | 'percent' | 'number';
}

export interface RevenueTrendPoint {
  month: string;
  revenue: number;
  invoice_count: number;
}

export interface ExpensesTrendPoint {
  month: string;
  expenses: number;
  order_count: number;
}

export interface ProfitTrendPoint {
  month: string;
  revenue: number;
  expenses: number;
  profit: number;
}

export interface CashFlowPoint {
  month: string;
  inflow: number;
  outflow: number;
  net: number;
  cumulative: number;
}

export interface SalesSummary {
  period: string;
  total_invoices: number;
  total_revenue: number;
  average_invoice: number;
  paid_count: number;
  unpaid_count: number;
  collection_rate: number;
}

export interface SalesByPeriod {
  this_month: SalesSummary;
  last_month: SalesSummary;
  this_year: SalesSummary;
  changes: {
    revenue_change: number;
    invoice_change: number;
  };
}

export interface TopCustomer {
  customer_id: string;
  name: string;
  revenue: number;
  invoices: number;
}

export interface PurchaseSummary {
  period: string;
  total_orders: number;
  total_amount: number;
  pending_orders: number;
  approval_rate: number;
}

export interface TopSupplier {
  supplier_id: string;
  name: string;
  purchases: number;
  orders: number;
}

export interface InventorySummary {
  total_items: number;
  total_stock_value: number;
  low_stock_items: number;
  warehouses: number;
}

export interface StockMovement {
  date: string;
  in: number;
  out: number;
}

export interface ProjectSummary {
  total_projects: number;
  active: number;
  completed: number;
  overdue: number;
  total_budget: number;
  total_spent: number;
  budget_utilization: number;
}

export interface ProjectCostItem {
  project_id: string;
  name: string;
  budget: number;
  actual_cost: number;
  labor_cost: number;
  variance: number;
  status: string;
}

export interface HRSummary {
  total_employees: number;
  departments: number;
  total_payroll: number;
  pending_leave_requests: number;
}

export interface BusinessAlert {
  type: 'warning' | 'danger' | 'info';
  category: string;
  title: string;
  message: string;
  action: string;
}

export interface RoleDashboard {
  role: string;
  period: string;
  generated_at: string;
  summary?: ExecutiveSummary;
  kpis?: KPI[];
  revenue_trend?: RevenueTrendPoint[];
  expenses_trend?: ExpensesTrendPoint[];
  profit_trend?: ProfitTrendPoint[];
  cash_flow?: CashFlowPoint[];
  top_customers?: TopCustomer[];
  top_suppliers?: TopSupplier[];
  project_summary?: ProjectSummary;
  project_costs?: ProjectCostItem[];
  hr_summary?: HRSummary;
  purchase_summary?: PurchaseSummary;
  inventory?: InventorySummary;
  stock_movements?: StockMovement[];
  sales_by_period?: SalesByPeriod;
}

export interface DrillDownResult {
  [key: string]: any;
}

// =====================================================
// White-Label / Branding Types (P67)
// =====================================================

export interface TenantBranding {
  tenant_id: string;
  system_name_en: string;
  system_name_ar: string;
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string;
  secondary_color: string;
  theme_mode: 'light' | 'dark';
  direction: 'rtl' | 'ltr';
  login_title_en: string;
  login_title_ar: string;
  login_subtitle_en: string;
  login_subtitle_ar: string;
  email_footer_text: string | null;
  report_header_text: string | null;
  report_footer_text: string | null;
  custom_domain: string | null;
  domain_verified: boolean;
  dns_txt_record?: string | null;
  show_powered_by: boolean;
  enable_custom_domain: boolean;
  enable_custom_branding: boolean;
  enable_custom_login: boolean;
}

/** Safe public projection (login pages) — no flags or verification state */
export interface PublicBranding {
  tenant_id?: string;
  system_name_en: string | null;
  system_name_ar: string | null;
  logo_url: string | null;
  favicon_url: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  theme_mode: 'light' | 'dark' | null;
  direction: 'rtl' | 'ltr' | null;
  login_title_en: string | null;
  login_title_ar: string | null;
  login_subtitle_en: string | null;
  login_subtitle_ar: string | null;
  show_powered_by?: boolean;
}

export interface FeatureFlags {
  show_powered_by: boolean;
  enable_custom_domain: boolean;
  enable_custom_branding: boolean;
  enable_custom_login: boolean;
}

export type SortOrder = 'ascend' | 'descend';

export interface TableParams {
  pagination?: {
    current?: number;
    pageSize?: number;
  };
  sort?: {
    field: string;
    order: SortOrder;
  };
  filters?: Record<string, any>;
}
