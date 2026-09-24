import React, { useState, useEffect, useCallback } from 'react';
import { TranslationKeys } from '../i18n';

interface Account { id: string; code: string; name: string; account_type: string; is_active: boolean; currency: string; }
interface JournalEntry { id: string; entry_number: number; accounting_date: string; currency: string; description: string; reference: string | null; status: string; lines?: JournalLine[]; }
interface JournalLine { id?: string; account_id?: string; line_number?: number; description: string | null; debit: number; credit: number; }
interface Customer { id: string; code: string; name: string; email: string | null; phone: string | null; payment_terms: string; currency: string; credit_limit: number; is_active: boolean; }
interface Supplier { id: string; code: string; name: string; email: string | null; phone: string | null; payment_terms: string; currency: string; is_active: boolean; }
interface Invoice { id: string; invoice_number: string; customer_id: string; status: string; issue_date: string; due_date: string; currency: string; subtotal: number; tax_amount: number; total_amount: number; paid_amount: number; balance_due: number; description: string | null; lines?: InvoiceLine[]; }
interface InvoiceLine { description: string; quantity: number; unit_price: number; tax_rate: number; line_total: number; }
interface Bill { id: string; bill_number: string; supplier_id: string; status: string; issue_date: string; due_date: string; currency: string; subtotal: number; tax_amount: number; total_amount: number; paid_amount: number; balance_due: number; description: string | null; lines?: BillLine[]; }
interface BillLine { description: string; quantity: number; unit_price: number; tax_rate: number; line_total: number; }
interface Payment { id: string; payment_number: string; payment_type: string; customer_id: string | null; supplier_id: string | null; status: string; payment_date: string; currency: string; amount: number; payment_method: string; reference: string | null; }
interface BankAccount { id: string; account_number: string; account_name: string; bank_name: string | null; account_type: string; currency: string; current_balance: number; is_active: boolean; }
interface BankTransaction { id: string; bank_account_id: string; transaction_date: string; description: string; reference: string | null; debit: number; credit: number; balance: number; status: string; }
interface Reconciliation { id: string; bank_account_id: string; statement_date: string; statement_balance: number; book_balance: number; difference: number; status: string; }
interface PnLData { currency: string; revenue: { lines: { code: string; name: string; balance: number }[]; total: number }; expense: { lines: { code: string; name: string; balance: number }[]; total: number }; gross_profit: number; net_income: number; }
interface BalanceSheetData { currency: string; assets: { lines: { code: string; name: string; balance: number }[]; total: number }; liabilities: { lines: { code: string; name: string; balance: number }[]; total: number }; equity: { lines: { code: string; name: string; balance: number }[]; total: number }; total_liabilities_and_equity: number; is_balanced: boolean; }
interface AgingData { as_of: string; buckets: Record<string, number>; total_outstanding: number; }
interface LedgerAccount { id: string; account_code: string; account_name: string; account_type: string; normal_balance: string; is_active: boolean; currency: string; }
interface LedgerEntry { id: string; entry_number: number; entry_date: string; description: string; reference_type: string | null; reference_id: string | null; status: string; posted_by: string | null; period_id: string | null; lines: LedgerLine[]; }
interface LedgerLine { id: string; account_code: string; description: string | null; debit: number; credit: number; }
interface TrialBalanceData { period: string; accounts: Array<{ account_code: string; account_name: string; debit: number; credit: number }>; total_debit: number; total_credit: number; is_balanced: boolean; }
interface FiscalPeriod { id: string; period_name: string; start_date: string; end_date: string; status: string; }

type Tab = 'overview' | 'accounts' | 'journal' | 'ledger' | 'ar' | 'ap' | 'payments' | 'bank' | 'statements' | 'ai';

const h = (token: string) => ({ Authorization: `Bearer ${token}` });
const jh = (token: string) => ({ 'Content-Type': 'application/json', Authorization: `Bearer ${token}` });
const fmt = (n: number) => n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function FinancialPage({ t, token }: { t: TranslationKeys; token: string }) {
  const [tab, setTab] = useState<Tab>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [accounts, setAccounts] = useState<Account[]>([]);
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [bills, setBills] = useState<Bill[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [_bankTransactions] = useState<BankTransaction[]>([]);
  const [reconciliations] = useState<Reconciliation[]>([]);

  const [pnl, setPnl] = useState<PnLData | null>(null);
  const [bs, setBs] = useState<BalanceSheetData | null>(null);
  const [arAging, setArAging] = useState<AgingData | null>(null);
  const [apAging, setApAging] = useState<AgingData | null>(null);

  const [ledgerAccounts, setLedgerAccounts] = useState<LedgerAccount[]>([]);
  const [ledgerEntries, setLedgerEntries] = useState<LedgerEntry[]>([]);
  const [trialBalance, setTrialBalance] = useState<TrialBalanceData | null>(null);
  const [fiscalPeriods, setFiscalPeriods] = useState<FiscalPeriod[]>([]);
  const [ledgerSubTab, setLedgerSubTab] = useState<'accounts' | 'entries' | 'trial' | 'periods'>('accounts');
  const [showCreateLedgerAccount, setShowCreateLedgerAccount] = useState(false);
  const [showCreateLedgerEntry, setShowCreateLedgerEntry] = useState(false);
  const [showCreateFiscalPeriod, setShowCreateFiscalPeriod] = useState(false);
  const [expandedLedgerEntry, setExpandedLedgerEntry] = useState<string | null>(null);
  const [ledgerAccountForm, setLedgerAccountForm] = useState({ account_code: '', account_name: '', account_type: 'asset', normal_balance: 'debit', currency: 'USD' });
  const [ledgerEntryForm, setLedgerEntryForm] = useState({ description: '', entry_date: new Date().toISOString().slice(0, 10), reference_type: '', reference_id: '', lines: [{ account_code: '', description: '', debit: 0, credit: 0 }] });
  const [fiscalPeriodForm, setFiscalPeriodForm] = useState({ period_name: '', start_date: '', end_date: '' });

  const [selectedEntry, setSelectedEntry] = useState<JournalEntry | null>(null);
  const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
  const [selectedBill, setSelectedBill] = useState<Bill | null>(null);

  const [showCreateAccount, setShowCreateAccount] = useState(false);
  const [showCreateCustomer, setShowCreateCustomer] = useState(false);
  const [showCreateSupplier, setShowCreateSupplier] = useState(false);
  const [showCreateInvoice, setShowCreateInvoice] = useState(false);
  const [showCreateBill, setShowCreateBill] = useState(false);
  const [showCreatePayment, setShowCreatePayment] = useState(false);
  const [showCreateBankAccount, setShowCreateBankAccount] = useState(false);

  const [accountForm, setAccountForm] = useState({ code: '', name: '', account_type: 'asset' });
  const [customerForm, setCustomerForm] = useState({ code: '', name: '', email: '', phone: '', payment_terms: 'NET30', currency: 'USD', credit_limit: 0 });
  const [supplierForm, setSupplierForm] = useState({ code: '', name: '', email: '', phone: '', payment_terms: 'NET30', currency: 'USD' });
  const [invoiceForm, setInvoiceForm] = useState({ customer_id: '', issue_date: '', due_date: '', currency: 'USD', description: '', lines: [{ description: '', quantity: 1, unit_price: 0, tax_rate: 0 }] });
  const [billForm, setBillForm] = useState({ supplier_id: '', issue_date: '', due_date: '', currency: 'USD', description: '', lines: [{ description: '', quantity: 1, unit_price: 0, tax_rate: 0 }] });
  const [paymentForm, setPaymentForm] = useState({ payment_type: 'customer' as 'customer' | 'supplier', customer_id: '', supplier_id: '', payment_date: '', currency: 'USD', amount: 0, payment_method: 'bank_transfer', reference: '' });
  const [bankAccountForm, setBankAccountForm] = useState({ account_number: '', account_name: '', bank_name: '', account_type: 'checking', currency: 'USD', gl_account_id: '' });
  const [aiQuery, setAiQuery] = useState('');
  const [aiResponse, setAiResponse] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [accRes, entRes, custRes, supRes, invRes, billRes, payRes, baRes] = await Promise.all([
        fetch('/api/v1/financial/accounts', { headers: h(token) }),
        fetch('/api/v1/financial/journal-entries', { headers: h(token) }),
        fetch('/api/v1/financial/customers', { headers: h(token) }),
        fetch('/api/v1/financial/suppliers', { headers: h(token) }),
        fetch('/api/v1/financial/invoices', { headers: h(token) }),
        fetch('/api/v1/financial/bills', { headers: h(token) }),
        fetch('/api/v1/financial/payments', { headers: h(token) }),
        fetch('/api/v1/financial/bank-accounts', { headers: h(token) }),
      ]);
      if (accRes.ok) { const d = await accRes.json(); setAccounts((d.items || d).map((a: Record<string, unknown>) => ({ id: String(a.id ?? ''), code: String(a.code ?? ''), name: String(a.name ?? ''), account_type: String(a.account_type ?? ''), is_active: Boolean(a.is_active ?? true), currency: String(a.currency ?? 'USD') }))); }
      if (entRes.ok) { const d = await entRes.json(); setEntries((d.items || d).map((e: Record<string, unknown>) => ({ id: String(e.id ?? ''), entry_number: Number(e.entry_number ?? 0), accounting_date: String(e.accounting_date ?? ''), currency: String(e.currency ?? 'USD'), description: String(e.description ?? ''), reference: String(e.reference ?? ''), status: String(e.status ?? 'posted') }))); }
      if (custRes.ok) { const d = await custRes.json(); setCustomers((d.items || d).map((c: Record<string, unknown>) => ({ id: String(c.id ?? ''), code: String(c.code ?? ''), name: String(c.name ?? ''), email: String(c.email ?? ''), phone: String(c.phone ?? ''), payment_terms: String(c.payment_terms ?? 'NET30'), currency: String(c.currency ?? 'USD'), credit_limit: Number(c.credit_limit ?? 0), is_active: Boolean(c.is_active ?? true) }))); }
      if (supRes.ok) { const d = await supRes.json(); setSuppliers((d.items || d).map((s: Record<string, unknown>) => ({ id: String(s.id ?? ''), code: String(s.code ?? ''), name: String(s.name ?? ''), email: String(s.email ?? ''), phone: String(s.phone ?? ''), payment_terms: String(s.payment_terms ?? 'NET30'), currency: String(s.currency ?? 'USD'), is_active: Boolean(s.is_active ?? true) }))); }
      if (invRes.ok) { const d = await invRes.json(); setInvoices((d.items || d).map((i: Record<string, unknown>) => ({ id: String(i.id ?? ''), invoice_number: String(i.invoice_number ?? ''), customer_id: String(i.customer_id ?? ''), status: String(i.status ?? ''), issue_date: String(i.issue_date ?? ''), due_date: String(i.due_date ?? ''), currency: String(i.currency ?? 'USD'), subtotal: Number(i.subtotal ?? 0), tax_amount: Number(i.tax_amount ?? 0), total_amount: Number(i.total_amount ?? 0), paid_amount: Number(i.paid_amount ?? 0), balance_due: Number(i.balance_due ?? 0), description: String(i.description ?? '') }))); }
      if (billRes.ok) { const d = await billRes.json(); setBills((d.items || d).map((b: Record<string, unknown>) => ({ id: String(b.id ?? ''), bill_number: String(b.bill_number ?? ''), supplier_id: String(b.supplier_id ?? ''), status: String(b.status ?? ''), issue_date: String(b.issue_date ?? ''), due_date: String(b.due_date ?? ''), currency: String(b.currency ?? 'USD'), subtotal: Number(b.subtotal ?? 0), tax_amount: Number(b.tax_amount ?? 0), total_amount: Number(b.total_amount ?? 0), paid_amount: Number(b.paid_amount ?? 0), balance_due: Number(b.balance_due ?? 0), description: String(b.description ?? '') }))); }
      if (payRes.ok) { const d = await payRes.json(); setPayments((d.items || d).map((p: Record<string, unknown>) => ({ id: String(p.id ?? ''), payment_number: String(p.payment_number ?? ''), payment_type: String(p.payment_type ?? ''), customer_id: String(p.customer_id ?? ''), supplier_id: String(p.supplier_id ?? ''), status: String(p.status ?? ''), payment_date: String(p.payment_date ?? ''), currency: String(p.currency ?? 'USD'), amount: Number(p.amount ?? 0), payment_method: String(p.payment_method ?? ''), reference: String(p.reference ?? '') }))); }
      if (baRes.ok) { const d = await baRes.json(); setBankAccounts((d.items || d).map((b: Record<string, unknown>) => ({ id: String(b.id ?? ''), account_number: String(b.account_number ?? ''), account_name: String(b.account_name ?? ''), bank_name: String(b.bank_name ?? ''), account_type: String(b.account_type ?? ''), currency: String(b.currency ?? 'USD'), current_balance: Number(b.current_balance ?? 0), is_active: Boolean(b.is_active ?? true) }))); }
    } catch { setError(t.common.error); } finally { setLoading(false); }
  }, [token, t]);

  const fetchStatements = useCallback(async () => {
    try {
      const [pnlRes, bsRes, arRes, apRes] = await Promise.all([
        fetch('/api/v1/financial/statements/profit-and-loss', { headers: h(token) }),
        fetch('/api/v1/financial/statements/balance-sheet', { headers: h(token) }),
        fetch('/api/v1/financial/statements/ar-aging', { headers: h(token) }),
        fetch('/api/v1/financial/statements/ap-aging', { headers: h(token) }),
      ]);
      if (pnlRes.ok) setPnl(await pnlRes.json());
      if (bsRes.ok) setBs(await bsRes.json());
      if (arRes.ok) setArAging(await arRes.json());
      if (apRes.ok) setApAging(await apRes.json());
    } catch { /* silent */ }
  }, [token]);

  useEffect(() => { fetchAll(); }, [fetchAll]);
  useEffect(() => { if (tab === 'statements') fetchStatements(); }, [tab, fetchStatements]);

  useEffect(() => {
    if (tab !== 'ledger') return;
    const fetchLedger = async () => {
      try {
        const [acctsRes, entriesRes, tbRes, periodsRes] = await Promise.all([
          fetch('/api/v1/financial/ledger/accounts', { headers: h(token) }),
          fetch('/api/v1/financial/ledger/entries', { headers: h(token) }),
          fetch('/api/v1/financial/ledger/trial-balance', { headers: h(token) }),
          fetch('/api/v1/financial/ledger/fiscal-periods', { headers: h(token) }),
        ]);
        if (acctsRes.ok) { const d = await acctsRes.json(); setLedgerAccounts((d.items || d).map((a: Record<string, unknown>) => ({ id: String(a.id ?? ''), account_code: String(a.account_code ?? ''), account_name: String(a.account_name ?? ''), account_type: String(a.account_type ?? ''), normal_balance: String(a.normal_balance ?? 'debit'), is_active: Boolean(a.is_active ?? true), currency: String(a.currency ?? 'USD') }))); }
        if (entriesRes.ok) { const d = await entriesRes.json(); setLedgerEntries((d.items || d).map((e: Record<string, unknown>) => ({ id: String(e.id ?? ''), entry_number: Number(e.entry_number ?? 0), entry_date: String(e.entry_date ?? ''), description: String(e.description ?? ''), reference_type: e.reference_type ? String(e.reference_type) : null, reference_id: e.reference_id ? String(e.reference_id) : null, status: String(e.status ?? 'draft'), posted_by: e.posted_by ? String(e.posted_by) : null, period_id: e.period_id ? String(e.period_id) : null, lines: Array.isArray(e.lines) ? (e.lines as Record<string, unknown>[]).map((l: Record<string, unknown>) => ({ id: String(l.id ?? ''), account_code: String(l.account_code ?? ''), description: l.description ? String(l.description) : null, debit: Number(l.debit ?? 0), credit: Number(l.credit ?? 0) })) : [] }))); }
        if (tbRes.ok) { const d = await tbRes.json(); setTrialBalance(d); }
        if (periodsRes.ok) { const d = await periodsRes.json(); setFiscalPeriods((d.items || d).map((p: Record<string, unknown>) => ({ id: String(p.id ?? ''), period_name: String(p.period_name ?? ''), start_date: String(p.start_date ?? ''), end_date: String(p.end_date ?? ''), status: String(p.status ?? 'open') }))); }
      } catch { /* silent */ }
    };
    fetchLedger();
  }, [tab, token]);

  const createAccount = async () => {
    setError(null);
    const r = await fetch('/api/v1/financial/accounts', { method: 'POST', headers: jh(token), body: JSON.stringify(accountForm) });
    if (r.ok) { setShowCreateAccount(false); setAccountForm({ code: '', name: '', account_type: 'asset' }); fetchAll(); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createCustomer = async () => {
    setError(null);
    const r = await fetch('/api/v1/financial/customers', { method: 'POST', headers: jh(token), body: JSON.stringify(customerForm) });
    if (r.ok) { setShowCreateCustomer(false); setCustomerForm({ code: '', name: '', email: '', phone: '', payment_terms: 'NET30', currency: 'USD', credit_limit: 0 }); fetchAll(); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createSupplier = async () => {
    setError(null);
    const r = await fetch('/api/v1/financial/suppliers', { method: 'POST', headers: jh(token), body: JSON.stringify(supplierForm) });
    if (r.ok) { setShowCreateSupplier(false); setSupplierForm({ code: '', name: '', email: '', phone: '', payment_terms: 'NET30', currency: 'USD' }); fetchAll(); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createInvoice = async () => {
    setError(null);
    const validLines = invoiceForm.lines.filter(l => l.description);
    const r = await fetch('/api/v1/financial/invoices', { method: 'POST', headers: jh(token), body: JSON.stringify({ ...invoiceForm, lines: validLines }) });
    if (r.ok) { setShowCreateInvoice(false); setInvoiceForm({ customer_id: '', issue_date: '', due_date: '', currency: 'USD', description: '', lines: [{ description: '', quantity: 1, unit_price: 0, tax_rate: 0 }] }); fetchAll(); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const postInvoice = async (id: string) => {
    const r = await fetch(`/api/v1/financial/invoices/${id}/post`, { method: 'POST', headers: jh(token) });
    if (r.ok) fetchAll();
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createBill = async () => {
    setError(null);
    const validLines = billForm.lines.filter(l => l.description);
    const r = await fetch('/api/v1/financial/bills', { method: 'POST', headers: jh(token), body: JSON.stringify({ ...billForm, lines: validLines }) });
    if (r.ok) { setShowCreateBill(false); setBillForm({ supplier_id: '', issue_date: '', due_date: '', currency: 'USD', description: '', lines: [{ description: '', quantity: 1, unit_price: 0, tax_rate: 0 }] }); fetchAll(); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const postBill = async (id: string) => {
    const r = await fetch(`/api/v1/financial/bills/${id}/post`, { method: 'POST', headers: jh(token) });
    if (r.ok) fetchAll();
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createPaymentAction = async () => {
    setError(null);
    const r = await fetch('/api/v1/financial/payments', { method: 'POST', headers: jh(token), body: JSON.stringify(paymentForm) });
    if (r.ok) { setShowCreatePayment(false); setPaymentForm({ payment_type: 'customer', customer_id: '', supplier_id: '', payment_date: '', currency: 'USD', amount: 0, payment_method: 'bank_transfer', reference: '' }); fetchAll(); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createBankAccount = async () => {
    setError(null);
    const r = await fetch('/api/v1/financial/bank-accounts', { method: 'POST', headers: jh(token), body: JSON.stringify(bankAccountForm) });
    if (r.ok) { setShowCreateBankAccount(false); setBankAccountForm({ account_number: '', account_name: '', bank_name: '', account_type: 'checking', currency: 'USD', gl_account_id: '' }); fetchAll(); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createLedgerAccount = async () => {
    setError(null);
    const r = await fetch('/api/v1/financial/ledger/accounts', { method: 'POST', headers: jh(token), body: JSON.stringify(ledgerAccountForm) });
    if (r.ok) { setShowCreateLedgerAccount(false); setLedgerAccountForm({ account_code: '', account_name: '', account_type: 'asset', normal_balance: 'debit', currency: 'USD' }); const d = await r.json(); setLedgerAccounts(prev => [...prev, { id: String(d.id ?? ''), ...ledgerAccountForm, is_active: true }]); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createLedgerEntry = async () => {
    setError(null);
    const validLines = ledgerEntryForm.lines.filter(l => l.account_code);
    const payload = { description: ledgerEntryForm.description, entry_date: ledgerEntryForm.entry_date, reference_type: ledgerEntryForm.reference_type || null, reference_id: ledgerEntryForm.reference_id || null, lines: validLines };
    const r = await fetch('/api/v1/financial/ledger/entries', { method: 'POST', headers: jh(token), body: JSON.stringify(payload) });
    if (r.ok) { setShowCreateLedgerEntry(false); setLedgerEntryForm({ description: '', entry_date: new Date().toISOString().slice(0, 10), reference_type: '', reference_id: '', lines: [{ account_code: '', description: '', debit: 0, credit: 0 }] }); const tab = document.querySelector('[data-refresh-ledger]'); if (tab) tab.dispatchEvent(new Event('click')); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const postLedgerEntry = async (id: string) => {
    setError(null);
    const r = await fetch(`/api/v1/financial/ledger/entries/${id}/post`, { method: 'POST', headers: jh(token) });
    if (r.ok) {
      setLedgerEntries(prev => prev.map(e => e.id === id ? { ...e, status: 'posted' } : e));
    } else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const reverseLedgerEntry = async (id: string) => {
    setError(null);
    const r = await fetch(`/api/v1/financial/ledger/entries/${id}/reverse`, { method: 'POST', headers: jh(token) });
    if (r.ok) {
      setLedgerEntries(prev => prev.map(e => e.id === id ? { ...e, status: 'reversed' } : e));
    } else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const createFiscalPeriodAction = async () => {
    setError(null);
    const r = await fetch('/api/v1/financial/ledger/fiscal-periods', { method: 'POST', headers: jh(token), body: JSON.stringify(fiscalPeriodForm) });
    if (r.ok) { setShowCreateFiscalPeriod(false); setFiscalPeriodForm({ period_name: '', start_date: '', end_date: '' }); const d = await r.json(); setFiscalPeriods(prev => [...prev, { id: String(d.id ?? ''), ...fiscalPeriodForm, status: 'open' }]); }
    else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const closeFiscalPeriod = async (id: string) => {
    setError(null);
    const r = await fetch(`/api/v1/financial/ledger/fiscal-periods/${id}/close`, { method: 'POST', headers: jh(token) });
    if (r.ok) {
      setFiscalPeriods(prev => prev.map(p => p.id === id ? { ...p, status: 'closed' } : p));
    } else { const d = await r.json(); setError(d.detail || t.common.error); }
  };

  const handleAskAI = async () => {
    if (!aiQuery.trim()) return;
    setAiResponse(null);
    try {
      const r = await fetch('/api/v1/ai/ask', { method: 'POST', headers: jh(token), body: JSON.stringify({ query: aiQuery }) });
      if (r.ok) { const d = await r.json(); setAiResponse(d.response || 'Analysis complete.'); }
      else { setAiResponse('AI engine initializing...'); }
    } catch { setAiResponse('AI engine connecting...'); }
    setAiQuery('');
  };

  const tc: Record<string, string> = { asset: 'bg-blue-100 text-blue-800', liability: 'bg-red-100 text-red-800', equity: 'bg-purple-100 text-purple-800', revenue: 'bg-green-100 text-green-800', expense: 'bg-yellow-100 text-yellow-800' };
  const sc: Record<string, string> = { posted: 'bg-green-100 text-green-800', draft: 'bg-gray-100 text-gray-800', sent: 'bg-blue-100 text-blue-800', paid: 'bg-green-100 text-green-800', overdue: 'bg-red-100 text-red-800', cancelled: 'bg-gray-100 text-gray-800', received: 'bg-blue-100 text-blue-800', approved: 'bg-green-100 text-green-800', pending: 'bg-yellow-100 text-yellow-800', completed: 'bg-green-100 text-green-800', failed: 'bg-red-100 text-red-800', matched: 'bg-green-100 text-green-800', unmatched: 'bg-yellow-100 text-yellow-800', voided: 'bg-red-100 text-red-800', reversed: 'bg-orange-100 text-orange-800' };

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" /></div>;

  const tabs: [Tab, string][] = [['overview', t.financialPage.overview], ['accounts', t.financialPage.accounts], ['journal', t.financialPage.journal], ['ledger', t.financialPage.ledger], ['ar', t.financialPage.ar], ['ap', t.financialPage.ap], ['payments', t.financialPage.payments], ['bank', t.financialPage.bank], ['statements', t.financialPage.statements], ['ai', t.financialPage.ai]];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{t.financial.title}</h1>
          <p className="text-gray-500 mt-1">{accounts.length} {t.financialPage.subtitle} &middot; {entries.length} {t.financialPage.recentEntries} &middot; {customers.length} {t.financialPage.customer} &middot; {suppliers.length} {t.financialPage.supplier}</p>
        </div>
      </div>

      {error && <div className="px-4 py-2 bg-red-50 text-red-700 rounded-lg text-sm flex items-center justify-between"><span>{error}</span><button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">&times;</button></div>}

      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit overflow-x-auto">
        {tabs.map(([key, label]) => (
          <button key={key} onClick={() => setTab(key)} className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${tab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>{label}</button>
        ))}
      </div>

      {/* ============================================================ */}
      {/* OVERVIEW */}
      {/* ============================================================ */}
      {tab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
            {[
              [t.financialPage.accounts, accounts.length, tc.asset],
              ['Invoices', invoices.length, 'bg-blue-100 text-blue-800'],
              ['Bills', bills.length, 'bg-orange-100 text-orange-800'],
              [t.financialPage.payments, payments.length, 'bg-green-100 text-green-800'],
              ['Bank Accounts', bankAccounts.length, 'bg-indigo-100 text-indigo-800'],
              [t.financialPage.journal, entries.length, 'bg-purple-100 text-purple-800'],
            ].map(([label, val, color]) => (
              <div key={String(label)} className="bg-white rounded-xl border border-gray-200 p-4 text-center">
                <p className={`text-2xl font-bold ${color}`}>{val}</p>
                <p className="text-xs text-gray-500 mt-1">{String(label)}</p>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.financialPage.recentEntries}</h3>
              <div className="space-y-2">
                {entries.slice(0, 5).map(e => (
                  <div key={e.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div><p className="text-sm font-medium text-gray-900">{e.description}</p><p className="text-xs text-gray-500">{e.accounting_date} &middot; #{e.entry_number}</p></div>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${sc[e.status] || 'bg-gray-100 text-gray-800'}`}>{e.status}</span>
                  </div>
                ))}
                {entries.length === 0 && <p className="text-sm text-gray-400 text-center py-4">{t.financialPage.noJournalEntries}</p>}
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">{t.financialPage.recentInvoices}</h3>
              <div className="space-y-2">
                {invoices.slice(0, 5).map(inv => (
                  <div key={inv.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div><p className="text-sm font-medium text-gray-900">{inv.invoice_number}</p><p className="text-xs text-gray-500">{inv.issue_date} &middot; {fmt(inv.total_amount)} {inv.currency}</p></div>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${sc[inv.status] || 'bg-gray-100 text-gray-800'}`}>{inv.status}</span>
                  </div>
                ))}
                {invoices.length === 0 && <p className="text-sm text-gray-400 text-center py-4">{t.financialPage.noInvoices}</p>}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* ACCOUNTS */}
      {/* ============================================================ */}
      {tab === 'accounts' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">{t.financialPage.chartOfAccounts}</h2>
            <button onClick={() => setShowCreateAccount(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{t.financialPage.newAccount}</button>
          </div>
          {showCreateAccount && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newAccount}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.code} *</label><input type="text" value={accountForm.code} onChange={e => setAccountForm({ ...accountForm, code: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.name} *</label><input type="text" value={accountForm.name} onChange={e => setAccountForm({ ...accountForm, name: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.type} *</label><select value={accountForm.account_type} onChange={e => setAccountForm({ ...accountForm, account_type: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="asset">{t.financialPage.asset}</option><option value="liability">{t.financialPage.liability}</option><option value="equity">{t.financialPage.equity}</option><option value="revenue">{t.financialPage.revenue}</option><option value="expense">{t.financialPage.expense}</option></select></div>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createAccount} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateAccount(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}
          <div className="bg-white rounded-xl border border-gray-200">
            <table className="w-full">
                <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.code}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.name}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.type}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.active}</th></tr></thead>
              <tbody>
                {accounts.map(acc => (
                  <tr key={acc.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-mono text-gray-900">{acc.code}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{acc.name}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${tc[acc.account_type] || 'bg-gray-100 text-gray-800'}`}>{acc.account_type}</span></td>
                    <td className="px-4 py-3"><span className={acc.is_active ? 'text-green-600' : 'text-gray-400'}>{acc.is_active ? t.financialPage.yes : t.financialPage.no_}</span></td>
                  </tr>
                ))}
                {accounts.length === 0 && <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">{t.financialPage.noAccounts}</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* JOURNAL */}
      {/* ============================================================ */}
      {tab === 'journal' && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-900">{t.financialPage.journalEntries}</h2>
          {selectedEntry ? (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <div><button onClick={() => setSelectedEntry(null)} className="text-sm text-blue-600 hover:text-blue-800 mb-2">&larr; {t.financialPage.back}</button><h3 className="text-lg font-bold text-gray-900">Entry #{selectedEntry.entry_number}</h3><p className="text-sm text-gray-500">{selectedEntry.description}</p></div>
                <span className={`px-3 py-1 text-sm font-medium rounded-full ${sc[selectedEntry.status] || 'bg-gray-100 text-gray-800'}`}>{selectedEntry.status}</span>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 mb-4">
                <div className="grid grid-cols-3 gap-4"><div><p className="text-xs text-gray-500">{t.financialPage.date}</p><p className="text-sm font-medium">{selectedEntry.accounting_date}</p></div><div><p className="text-xs text-gray-500">{t.financialPage.reference}</p><p className="text-sm font-medium">{selectedEntry.reference || '—'}</p></div><div><p className="text-xs text-gray-500">{t.financialPage.currency}</p><p className="text-sm font-medium">{selectedEntry.currency}</p></div></div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200">
              <table className="w-full">
                <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.date}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.description}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.reference}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.status}</th></tr></thead>
                <tbody>
                  {entries.map(e => (
                    <tr key={e.id} onClick={() => setSelectedEntry(e)} className="border-b border-gray-100 last:border-0 hover:bg-gray-50 cursor-pointer">
                      <td className="px-4 py-3 text-sm font-mono text-gray-900">{e.entry_number}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{e.accounting_date}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{e.description}</td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-600">{e.reference || '—'}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${sc[e.status] || 'bg-gray-100 text-gray-800'}`}>{e.status}</span></td>
                    </tr>
                  ))}
                  {entries.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">{t.financialPage.noJournalEntries}</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* LEDGER (Double-Entry) */}
      {/* ============================================================ */}
      {tab === 'ledger' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">{t.financialPage.doubleEntryLedger}</h2>
            <div className="flex gap-2">
              {ledgerSubTab === 'accounts' && <button onClick={() => setShowCreateLedgerAccount(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{t.financialPage.newAccount}</button>}
              {ledgerSubTab === 'entries' && <button onClick={() => setShowCreateLedgerEntry(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{t.financialPage.newJournalEntry}</button>}
              {ledgerSubTab === 'periods' && <button onClick={() => setShowCreateFiscalPeriod(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">+ Period</button>}
            </div>
          </div>

          <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
            {([['accounts', t.financialPage.chartOfAccountsTab], ['entries', t.financialPage.journalEntriesTab], ['trial', t.financialPage.trialBalance], ['periods', t.financialPage.fiscalPeriods]] as const).map(([key, label]) => (
              <button key={key} onClick={() => setLedgerSubTab(key)} className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${ledgerSubTab === key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}>{label}</button>
            ))}
          </div>

          {/* Create Ledger Account Form */}
          {showCreateLedgerAccount && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newLedgerAccount}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountCode} *</label><input type="text" value={ledgerAccountForm.account_code} onChange={e => setLedgerAccountForm({ ...ledgerAccountForm, account_code: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountName} *</label><input type="text" value={ledgerAccountForm.account_name} onChange={e => setLedgerAccountForm({ ...ledgerAccountForm, account_name: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.type} *</label><select value={ledgerAccountForm.account_type} onChange={e => setLedgerAccountForm({ ...ledgerAccountForm, account_type: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="asset">{t.financialPage.asset}</option><option value="liability">{t.financialPage.liability}</option><option value="equity">{t.financialPage.equity}</option><option value="revenue">{t.financialPage.revenue}</option><option value="expense">{t.financialPage.expense}</option></select></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.normalBalance} *</label><select value={ledgerAccountForm.normal_balance} onChange={e => setLedgerAccountForm({ ...ledgerAccountForm, normal_balance: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="debit">{t.financialPage.debit}</option><option value="credit">{t.financialPage.credit}</option></select></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.currency}</label><input type="text" value={ledgerAccountForm.currency} onChange={e => setLedgerAccountForm({ ...ledgerAccountForm, currency: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createLedgerAccount} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateLedgerAccount(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          {/* Create Journal Entry Form */}
          {showCreateLedgerEntry && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newJournalEntry}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.entryDate} *</label><input type="date" value={ledgerEntryForm.entry_date} onChange={e => setLedgerEntryForm({ ...ledgerEntryForm, entry_date: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.description} *</label><input type="text" value={ledgerEntryForm.description} onChange={e => setLedgerEntryForm({ ...ledgerEntryForm, description: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.referenceType}</label><input type="text" value={ledgerEntryForm.reference_type} onChange={e => setLedgerEntryForm({ ...ledgerEntryForm, reference_type: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.lines}</label>
                {ledgerEntryForm.lines.map((line, idx) => (
                  <div key={idx} className="grid grid-cols-5 gap-2 mb-2">
                    <select value={line.account_code} onChange={e => { const newLines = [...ledgerEntryForm.lines]; newLines[idx].account_code = e.target.value; setLedgerEntryForm({ ...ledgerEntryForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"><option value="">Account</option>{ledgerAccounts.map(a => <option key={a.id} value={a.account_code}>{a.account_code} - {a.account_name}</option>)}</select>
                    <input placeholder="Description" value={line.description || ''} onChange={e => { const newLines = [...ledgerEntryForm.lines]; newLines[idx].description = e.target.value; setLedgerEntryForm({ ...ledgerEntryForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="Debit" value={line.debit || ''} onChange={e => { const newLines = [...ledgerEntryForm.lines]; newLines[idx].debit = Number(e.target.value); setLedgerEntryForm({ ...ledgerEntryForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="Credit" value={line.credit || ''} onChange={e => { const newLines = [...ledgerEntryForm.lines]; newLines[idx].credit = Number(e.target.value); setLedgerEntryForm({ ...ledgerEntryForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <button onClick={() => setLedgerEntryForm({ ...ledgerEntryForm, lines: ledgerEntryForm.lines.filter((_, i) => i !== idx) })} className="text-red-500 text-sm">&times;</button>
                  </div>
                ))}
                <button onClick={() => setLedgerEntryForm({ ...ledgerEntryForm, lines: [...ledgerEntryForm.lines, { account_code: '', description: '', debit: 0, credit: 0 }] })} className="text-sm text-blue-600 hover:text-blue-800">{t.financialPage.addLine}</button>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createLedgerEntry} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateLedgerEntry(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          {/* Create Fiscal Period Form */}
          {showCreateFiscalPeriod && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newFiscalPeriod}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.periodName} *</label><input type="text" value={fiscalPeriodForm.period_name} onChange={e => setFiscalPeriodForm({ ...fiscalPeriodForm, period_name: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.startDate} *</label><input type="date" value={fiscalPeriodForm.start_date} onChange={e => setFiscalPeriodForm({ ...fiscalPeriodForm, start_date: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.endDate} *</label><input type="date" value={fiscalPeriodForm.end_date} onChange={e => setFiscalPeriodForm({ ...fiscalPeriodForm, end_date: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createFiscalPeriodAction} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateFiscalPeriod(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          {/* Chart of Accounts */}
          {ledgerSubTab === 'accounts' && (
            <div className="bg-white rounded-xl border border-gray-200">
              <table className="w-full">
                <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.accountCode}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.accountName}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.type}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.normalBalance}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.currency}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.active}</th></tr></thead>
                <tbody>
                  {ledgerAccounts.map(a => (
                    <tr key={a.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono text-gray-900">{a.account_code}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{a.account_name}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${tc[a.account_type] || 'bg-gray-100 text-gray-800'}`}>{a.account_type}</span></td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${a.normal_balance === 'debit' ? 'bg-blue-100 text-blue-800' : 'bg-purple-100 text-purple-800'}`}>{a.normal_balance}</span></td>
                      <td className="px-4 py-3 text-sm font-mono text-gray-600">{a.currency}</td>
                      <td className="px-4 py-3"><span className={a.is_active ? 'text-green-600' : 'text-gray-400'}>{a.is_active ? t.financialPage.yes : t.financialPage.no_}</span></td>
                    </tr>
                  ))}
                  {ledgerAccounts.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">{t.financialPage.noLedgerAccounts}</td></tr>}
                </tbody>
              </table>
            </div>
          )}

          {/* Journal Entries */}
          {ledgerSubTab === 'entries' && (
            <div className="bg-white rounded-xl border border-gray-200">
              <table className="w-full">
                <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">#</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.entryDate}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.description}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.referenceType}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.status}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th></tr></thead>
                <tbody>
                  {ledgerEntries.map(e => (
                    <React.Fragment key={e.id}>
                      <tr className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-mono text-gray-900 cursor-pointer" onClick={() => setExpandedLedgerEntry(expandedLedgerEntry === e.id ? null : e.id)}>{e.entry_number}</td>
                        <td className="px-4 py-3 text-sm text-gray-600">{e.entry_date}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{e.description}</td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-600">{e.reference_type || '—'}{e.reference_id ? ` / ${e.reference_id}` : ''}</td>
                        <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${sc[e.status] || 'bg-gray-100 text-gray-800'}`}>{e.status}</span></td>
                        <td className="px-4 py-3">
                          <div className="flex gap-2">
                            {e.status === 'draft' && <button onClick={() => postLedgerEntry(e.id)} className="text-sm text-green-600 hover:text-green-800 font-medium">{t.financialPage.post}</button>}
                            {e.status === 'posted' && <button onClick={() => reverseLedgerEntry(e.id)} className="text-sm text-red-600 hover:text-red-800 font-medium">{t.financialPage.reverse}</button>}
                          </div>
                        </td>
                      </tr>
                      {expandedLedgerEntry === e.id && e.lines.length > 0 && (
                        <tr className="bg-gray-50">
                          <td colSpan={6} className="px-4 py-3">
                            <table className="w-full ml-8">
                              <thead><tr className="border-b border-gray-200"><th className="px-3 py-2 text-left text-xs font-medium text-gray-500">{t.financialPage.account}</th><th className="px-3 py-2 text-left text-xs font-medium text-gray-500">{t.financialPage.description}</th><th className="px-3 py-2 text-right text-xs font-medium text-gray-500">{t.financialPage.debit}</th><th className="px-3 py-2 text-right text-xs font-medium text-gray-500">{t.financialPage.credit}</th></tr></thead>
                              <tbody>
                                {e.lines.map(l => (
                                  <tr key={l.id} className="border-b border-gray-100 last:border-0">
                                    <td className="px-3 py-2 text-sm font-mono text-gray-900">{l.account_code}</td>
                                    <td className="px-3 py-2 text-sm text-gray-600">{l.description || '—'}</td>
                                    <td className="px-3 py-2 text-sm text-right font-medium text-gray-900">{l.debit ? fmt(l.debit) : '—'}</td>
                                    <td className="px-3 py-2 text-sm text-right font-medium text-gray-900">{l.credit ? fmt(l.credit) : '—'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                  {ledgerEntries.length === 0 && <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">{t.financialPage.journalEntriesTab}</td></tr>}
                </tbody>
              </table>
            </div>
          )}

          {/* Trial Balance */}
          {ledgerSubTab === 'trial' && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-4">{t.financialPage.trialBalance} {trialBalance?.period && <span className="text-sm font-normal text-gray-500">({trialBalance.period})</span>}</h3>
              {trialBalance ? (
                <div>
                  <table className="w-full">
                    <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.accountCode}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.accountName}</th><th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t.financialPage.debit}</th><th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t.financialPage.credit}</th></tr></thead>
                    <tbody>
                      {trialBalance.accounts.map(a => (
                        <tr key={a.account_code} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-mono text-gray-900">{a.account_code}</td>
                          <td className="px-4 py-3 text-sm text-gray-900">{a.account_name}</td>
                          <td className="px-4 py-3 text-sm text-right font-medium text-gray-900">{a.debit ? fmt(a.debit) : '—'}</td>
                          <td className="px-4 py-3 text-sm text-right font-medium text-gray-900">{a.credit ? fmt(a.credit) : '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="border-t-2 border-gray-300 font-bold">
                        <td className="px-4 py-3 text-sm" colSpan={2}>{t.financialPage.total}</td>
                        <td className="px-4 py-3 text-sm text-right">{fmt(trialBalance.total_debit)}</td>
                        <td className="px-4 py-3 text-sm text-right">{fmt(trialBalance.total_credit)}</td>
                      </tr>
                    </tfoot>
                  </table>
                  {!trialBalance.is_balanced && <p className="text-sm text-red-600 font-medium mt-3">{t.financialPage.trialBalanceNotBalanced}</p>}
                </div>
              ) : <p className="text-gray-400 text-center py-4">{t.financialPage.loadingTrialBalance}</p>}
            </div>
          )}

          {/* Fiscal Periods */}
          {ledgerSubTab === 'periods' && (
            <div className="bg-white rounded-xl border border-gray-200">
              <table className="w-full">
                <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.periodName}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.startDate}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.endDate}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.status}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th></tr></thead>
                <tbody>
                  {fiscalPeriods.map(p => (
                    <tr key={p.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{p.period_name}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{p.start_date}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{p.end_date}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${p.status === 'open' ? 'bg-green-100 text-green-800' : p.status === 'closed' ? 'bg-gray-100 text-gray-800' : 'bg-red-100 text-red-800'}`}>{p.status}</span></td>
                      <td className="px-4 py-3">{p.status === 'open' && <button onClick={() => closeFiscalPeriod(p.id)} className="text-sm text-orange-600 hover:text-orange-800 font-medium">{t.financialPage.close}</button>}</td>
                    </tr>
                  ))}
                  {fiscalPeriods.length === 0 && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">{t.financialPage.noFiscalPeriods}</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* AR (Invoices) */}
      {/* ============================================================ */}
      {tab === 'ar' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">{t.financialPage.accountsReceivable}</h2>
            <div className="flex gap-2">
              <button onClick={() => setShowCreateCustomer(true)} className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700">{t.financialPage.newCustomer}</button>
              <button onClick={() => setShowCreateInvoice(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">{t.financialPage.newInvoice}</button>
            </div>
          </div>

          {showCreateCustomer && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newCustomer}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountCode} *</label><input type="text" value={customerForm.code} onChange={e => setCustomerForm({ ...customerForm, code: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountName} *</label><input type="text" value={customerForm.name} onChange={e => setCustomerForm({ ...customerForm, name: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.email}</label><input type="email" value={customerForm.email} onChange={e => setCustomerForm({ ...customerForm, email: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createCustomer} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateCustomer(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          {showCreateInvoice && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newInvoice}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.customer} *</label><select value={invoiceForm.customer_id} onChange={e => setInvoiceForm({ ...invoiceForm, customer_id: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="">{t.financialPage.selectCustomer}</option>{customers.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.issueDate} *</label><input type="date" value={invoiceForm.issue_date} onChange={e => setInvoiceForm({ ...invoiceForm, issue_date: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.dueDate} *</label><input type="date" value={invoiceForm.due_date} onChange={e => setInvoiceForm({ ...invoiceForm, due_date: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div className="mt-3">
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.lines}</label>
                {invoiceForm.lines.map((line, idx) => (
                  <div key={idx} className="grid grid-cols-4 gap-2 mb-2">
                    <input placeholder="Description" value={line.description} onChange={e => { const newLines = [...invoiceForm.lines]; newLines[idx].description = e.target.value; setInvoiceForm({ ...invoiceForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="Qty" value={line.quantity} onChange={e => { const newLines = [...invoiceForm.lines]; newLines[idx].quantity = Number(e.target.value); setInvoiceForm({ ...invoiceForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="Price" value={line.unit_price} onChange={e => { const newLines = [...invoiceForm.lines]; newLines[idx].unit_price = Number(e.target.value); setInvoiceForm({ ...invoiceForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <button onClick={() => setInvoiceForm({ ...invoiceForm, lines: invoiceForm.lines.filter((_, i) => i !== idx) })} className="text-red-500 text-sm">&times;</button>
                  </div>
                ))}
                <button onClick={() => setInvoiceForm({ ...invoiceForm, lines: [...invoiceForm.lines, { description: '', quantity: 1, unit_price: 0, tax_rate: 0 }] })} className="text-sm text-blue-600 hover:text-blue-800">{t.financialPage.addLine}</button>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createInvoice} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateInvoice(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          {selectedInvoice ? (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <div><button onClick={() => setSelectedInvoice(null)} className="text-sm text-blue-600 hover:text-blue-800 mb-2">&larr; {t.financialPage.back}</button><h3 className="text-lg font-bold text-gray-900">{selectedInvoice.invoice_number}</h3></div>
                <div className="flex gap-2">
                  <span className={`px-3 py-1 text-sm font-medium rounded-full ${sc[selectedInvoice.status] || 'bg-gray-100 text-gray-800'}`}>{selectedInvoice.status}</span>
                  {selectedInvoice.status === 'draft' && <button onClick={() => postInvoice(selectedInvoice.id)} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.financialPage.post}</button>}
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-gray-50 rounded-lg p-4 mb-4">
                <div><p className="text-xs text-gray-500">{t.financialPage.customer}</p><p className="text-sm font-medium">{customers.find(c => c.id === selectedInvoice.customer_id)?.name || '—'}</p></div>
                <div><p className="text-xs text-gray-500">{t.financialPage.issueDate}</p><p className="text-sm font-medium">{selectedInvoice.issue_date}</p></div>
                <div><p className="text-xs text-gray-500">{t.financialPage.dueDate}</p><p className="text-sm font-medium">{selectedInvoice.due_date}</p></div>
                <div><p className="text-xs text-gray-500">{t.financialPage.total}</p><p className="text-sm font-bold">{fmt(selectedInvoice.total_amount)} {selectedInvoice.currency}</p></div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-green-50 rounded-lg p-3 text-center"><p className="text-xs text-green-600">{t.financialPage.paid}</p><p className="text-lg font-bold text-green-700">{fmt(selectedInvoice.paid_amount)}</p></div>
                <div className="bg-red-50 rounded-lg p-3 text-center"><p className="text-xs text-red-600">{t.financialPage.balanceDue}</p><p className="text-lg font-bold text-red-700">{fmt(selectedInvoice.balance_due)}</p></div>
                <div className="bg-blue-50 rounded-lg p-3 text-center"><p className="text-xs text-blue-600">{t.financialPage.tax}</p><p className="text-lg font-bold text-blue-700">{fmt(selectedInvoice.tax_amount)}</p></div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200">
              <table className="w-full">
                <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.number}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.customer}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.issueDate}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.total}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.balanceDue}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.status}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th></tr></thead>
                <tbody>
                  {invoices.map(inv => (
                    <tr key={inv.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono text-blue-600 cursor-pointer" onClick={() => setSelectedInvoice(inv)}>{inv.invoice_number}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{customers.find(c => c.id === inv.customer_id)?.name || '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{inv.issue_date}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{fmt(inv.total_amount)}</td>
                      <td className="px-4 py-3 text-sm font-medium text-red-600">{fmt(inv.balance_due)}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${sc[inv.status] || 'bg-gray-100 text-gray-800'}`}>{inv.status}</span></td>
                      <td className="px-4 py-3">{inv.status === 'draft' && <button onClick={() => postInvoice(inv.id)} className="text-sm text-green-600 hover:text-green-800 font-medium">Post</button>}</td>
                    </tr>
                  ))}
                  {invoices.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No invoices</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* AP (Bills) */}
      {/* ============================================================ */}
      {tab === 'ap' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">{t.financialPage.accountsPayable}</h2>
            <div className="flex gap-2">
              <button onClick={() => setShowCreateSupplier(true)} className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700">{t.financialPage.newSupplier}</button>
              <button onClick={() => setShowCreateBill(true)} className="px-4 py-2 bg-orange-600 text-white rounded-lg text-sm font-medium hover:bg-orange-700">{t.financialPage.newBill}</button>
            </div>
          </div>

          {showCreateSupplier && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newSupplier}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountCode} *</label><input type="text" value={supplierForm.code} onChange={e => setSupplierForm({ ...supplierForm, code: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountName} *</label><input type="text" value={supplierForm.name} onChange={e => setSupplierForm({ ...supplierForm, name: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.email}</label><input type="email" value={supplierForm.email} onChange={e => setSupplierForm({ ...supplierForm, email: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createSupplier} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateSupplier(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          {showCreateBill && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newBill}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.supplier} *</label><select value={billForm.supplier_id} onChange={e => setBillForm({ ...billForm, supplier_id: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="">{t.financialPage.selectSupplier}</option>{suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.issueDate} *</label><input type="date" value={billForm.issue_date} onChange={e => setBillForm({ ...billForm, issue_date: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.dueDate} *</label><input type="date" value={billForm.due_date} onChange={e => setBillForm({ ...billForm, due_date: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div className="mt-3">
                <label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.lines}</label>
                {billForm.lines.map((line, idx) => (
                  <div key={idx} className="grid grid-cols-4 gap-2 mb-2">
                    <input placeholder="Description" value={line.description} onChange={e => { const newLines = [...billForm.lines]; newLines[idx].description = e.target.value; setBillForm({ ...billForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="Qty" value={line.quantity} onChange={e => { const newLines = [...billForm.lines]; newLines[idx].quantity = Number(e.target.value); setBillForm({ ...billForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <input type="number" placeholder="Price" value={line.unit_price} onChange={e => { const newLines = [...billForm.lines]; newLines[idx].unit_price = Number(e.target.value); setBillForm({ ...billForm, lines: newLines }); }} className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm" />
                    <button onClick={() => setBillForm({ ...billForm, lines: billForm.lines.filter((_, i) => i !== idx) })} className="text-red-500 text-sm">&times;</button>
                  </div>
                ))}
                <button onClick={() => setBillForm({ ...billForm, lines: [...billForm.lines, { description: '', quantity: 1, unit_price: 0, tax_rate: 0 }] })} className="text-sm text-blue-600 hover:text-blue-800">{t.financialPage.addLine}</button>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createBill} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateBill(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          {selectedBill ? (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-4">
                <div><button onClick={() => setSelectedBill(null)} className="text-sm text-blue-600 hover:text-blue-800 mb-2">&larr; {t.financialPage.back}</button><h3 className="text-lg font-bold text-gray-900">{selectedBill.bill_number}</h3></div>
                <div className="flex gap-2">
                  <span className={`px-3 py-1 text-sm font-medium rounded-full ${sc[selectedBill.status] || 'bg-gray-100 text-gray-800'}`}>{selectedBill.status}</span>
                  {selectedBill.status === 'draft' && <button onClick={() => postBill(selectedBill.id)} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.financialPage.post}</button>}
                </div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-gray-50 rounded-lg p-4 mb-4">
                <div><p className="text-xs text-gray-500">{t.financialPage.supplier}</p><p className="text-sm font-medium">{suppliers.find(s => s.id === selectedBill.supplier_id)?.name || '—'}</p></div>
                <div><p className="text-xs text-gray-500">{t.financialPage.issueDate}</p><p className="text-sm font-medium">{selectedBill.issue_date}</p></div>
                <div><p className="text-xs text-gray-500">{t.financialPage.dueDate}</p><p className="text-sm font-medium">{selectedBill.due_date}</p></div>
                <div><p className="text-xs text-gray-500">{t.financialPage.total}</p><p className="text-sm font-bold">{fmt(selectedBill.total_amount)} {selectedBill.currency}</p></div>
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="bg-green-50 rounded-lg p-3 text-center"><p className="text-xs text-green-600">{t.financialPage.paid}</p><p className="text-lg font-bold text-green-700">{fmt(selectedBill.paid_amount)}</p></div>
                <div className="bg-red-50 rounded-lg p-3 text-center"><p className="text-xs text-red-600">{t.financialPage.balanceDue}</p><p className="text-lg font-bold text-red-700">{fmt(selectedBill.balance_due)}</p></div>
                <div className="bg-blue-50 rounded-lg p-3 text-center"><p className="text-xs text-blue-600">{t.financialPage.tax}</p><p className="text-lg font-bold text-blue-700">{fmt(selectedBill.tax_amount)}</p></div>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200">
              <table className="w-full">
                <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.number}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.supplier}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.issueDate}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.total}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.balanceDue}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.status}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th></tr></thead>
                <tbody>
                  {bills.map(bill => (
                    <tr key={bill.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono text-orange-600 cursor-pointer" onClick={() => setSelectedBill(bill)}>{bill.bill_number}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{suppliers.find(s => s.id === bill.supplier_id)?.name || '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">{bill.issue_date}</td>
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{fmt(bill.total_amount)}</td>
                      <td className="px-4 py-3 text-sm font-medium text-red-600">{fmt(bill.balance_due)}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${sc[bill.status] || 'bg-gray-100 text-gray-800'}`}>{bill.status}</span></td>
                      <td className="px-4 py-3">{bill.status === 'draft' && <button onClick={() => postBill(bill.id)} className="text-sm text-green-600 hover:text-green-800 font-medium">{t.financialPage.post}</button>}</td>
                    </tr>
                  ))}
                  {bills.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">{t.financialPage.noBills}</td></tr>}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* PAYMENTS */}
      {/* ============================================================ */}
      {tab === 'payments' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">{t.financialPage.payments}</h2>
            <button onClick={() => setShowCreatePayment(true)} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.financialPage.payments}</button>
          </div>

          {showCreatePayment && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.payments}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.type} *</label><select value={paymentForm.payment_type} onChange={e => setPaymentForm({ ...paymentForm, payment_type: e.target.value as 'customer' | 'supplier' })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="customer">{t.financialPage.customerAR}</option><option value="supplier">{t.financialPage.supplierAP}</option></select></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{paymentForm.payment_type === 'customer' ? t.financialPage.customer : t.financialPage.supplier} *</label><select value={paymentForm.payment_type === 'customer' ? paymentForm.customer_id : paymentForm.supplier_id} onChange={e => paymentForm.payment_type === 'customer' ? setPaymentForm({ ...paymentForm, customer_id: e.target.value }) : setPaymentForm({ ...paymentForm, supplier_id: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="">{t.financialPage.select}</option>{(paymentForm.payment_type === 'customer' ? customers : suppliers).map(e => <option key={e.id} value={e.id}>{e.name}</option>)}</select></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.total} *</label><input type="number" value={paymentForm.amount || ''} onChange={e => setPaymentForm({ ...paymentForm, amount: Number(e.target.value) })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.entryDate} *</label><input type="date" value={paymentForm.payment_date} onChange={e => setPaymentForm({ ...paymentForm, payment_date: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.bankTransfer}</label><select value={paymentForm.payment_method} onChange={e => setPaymentForm({ ...paymentForm, payment_method: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="bank_transfer">{t.financialPage.bankTransfer}</option><option value="cash">{t.financialPage.cash}</option><option value="check">{t.financialPage.check}</option></select></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.reference}</label><input type="text" value={paymentForm.reference} onChange={e => setPaymentForm({ ...paymentForm, reference: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createPaymentAction} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreatePayment(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          <div className="bg-white rounded-xl border border-gray-200">
            <table className="w-full">
              <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.number}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.type}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.account}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.entryDate}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.total}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.bankTransfer}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.status}</th></tr></thead>
              <tbody>
                {payments.map(p => (
                  <tr key={p.id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-mono text-green-600">{p.payment_number}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${p.payment_type === 'customer' ? 'bg-blue-100 text-blue-800' : 'bg-orange-100 text-orange-800'}`}>{p.payment_type}</span></td>
                    <td className="px-4 py-3 text-sm text-gray-900">{p.payment_type === 'customer' ? customers.find(c => c.id === p.customer_id)?.name : suppliers.find(s => s.id === p.supplier_id)?.name || '—'}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{p.payment_date}</td>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{fmt(p.amount)} {p.currency}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">{p.payment_method}</td>
                    <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${sc[p.status] || 'bg-gray-100 text-gray-800'}`}>{p.status}</span></td>
                  </tr>
                ))}
                {payments.length === 0 && <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No payments</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* BANK */}
      {/* ============================================================ */}
      {tab === 'bank' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">{t.financialPage.bankReconciliation}</h2>
            <button onClick={() => setShowCreateBankAccount(true)} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">{t.financialPage.newBankAccount}</button>
          </div>

          {showCreateBankAccount && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-3">{t.financialPage.newBankAccount}</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountNumber} *</label><input type="text" value={bankAccountForm.account_number} onChange={e => setBankAccountForm({ ...bankAccountForm, account_number: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountName} *</label><input type="text" value={bankAccountForm.account_name} onChange={e => setBankAccountForm({ ...bankAccountForm, account_name: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.bankName}</label><input type="text" value={bankAccountForm.bank_name} onChange={e => setBankAccountForm({ ...bankAccountForm, bank_name: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.accountType}</label><select value={bankAccountForm.account_type} onChange={e => setBankAccountForm({ ...bankAccountForm, account_type: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"><option value="checking">{t.financialPage.checking}</option><option value="savings">{t.financialPage.savings}</option><option value="credit">{t.financialPage.credit}</option><option value="cash">{t.financialPage.cash}</option></select></div>
                <div><label className="block text-xs font-medium text-gray-600 mb-1">{t.financialPage.glAccountId} *</label><input type="text" value={bankAccountForm.gl_account_id} onChange={e => setBankAccountForm({ ...bankAccountForm, gl_account_id: e.target.value })} className="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500" /></div>
              </div>
              <div className="flex gap-2 mt-3"><button onClick={createBankAccount} className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700">{t.common.save}</button><button onClick={() => setShowCreateBankAccount(false)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200">{t.common.cancel}</button></div>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {bankAccounts.map(ba => (
              <div key={ba.id} className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold text-gray-900">{ba.account_name}</h3>
                  <span className="text-lg font-bold text-indigo-600">{fmt(ba.current_balance)} {ba.currency}</span>
                </div>
                <p className="text-sm text-gray-500">{ba.bank_name || '—'} &middot; {ba.account_number}</p>
                <p className="text-xs text-gray-400 mt-1">{ba.account_type}</p>
              </div>
            ))}
            {bankAccounts.length === 0 && <div className="bg-white rounded-xl border border-gray-200 p-8 text-center text-gray-400 col-span-3">{t.financialPage.noBankAccounts}</div>}
          </div>

          {reconciliations.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200">
              <div className="px-4 py-3 border-b border-gray-200"><h3 className="font-semibold text-gray-900">{t.financialPage.reconciliations}</h3></div>
              <table className="w-full">
                <thead><tr className="border-b border-gray-200"><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.entryDate}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.statementBalance}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.bookBalance}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.difference}</th><th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t.financialPage.status}</th></tr></thead>
                <tbody>
                  {reconciliations.map(r => (
                    <tr key={r.id} className="border-b border-gray-100 last:border-0">
                      <td className="px-4 py-3 text-sm text-gray-600">{r.statement_date}</td>
                      <td className="px-4 py-3 text-sm font-medium">{fmt(r.statement_balance)}</td>
                      <td className="px-4 py-3 text-sm font-medium">{fmt(r.book_balance)}</td>
                      <td className={`px-4 py-3 text-sm font-medium ${Number(r.difference) !== 0 ? 'text-red-600' : 'text-green-600'}`}>{fmt(r.difference)}</td>
                      <td className="px-4 py-3"><span className={`px-2 py-1 text-xs font-medium rounded-full ${sc[r.status] || 'bg-gray-100 text-gray-800'}`}>{r.status}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ============================================================ */}
      {/* STATEMENTS */}
      {/* ============================================================ */}
      {tab === 'statements' && (
        <div className="space-y-6">
          <h2 className="text-lg font-semibold text-gray-900">{t.financialPage.financialStatements}</h2>

          {/* P&L */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-4">{t.financialPage.profitAndLoss}</h3>
            {pnl ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm font-medium text-green-700 mb-2">{t.financialPage.revenue}</h4>
                    {pnl.revenue.lines.map(l => (
                      <div key={l.code} className="flex justify-between py-1 text-sm"><span className="text-gray-600">{l.name}</span><span className="font-medium text-green-600">{fmt(l.balance)}</span></div>
                    ))}
                    <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.financialPage.totalRevenue}</span><span className="text-green-700">{fmt(pnl.revenue.total)}</span></div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-red-700 mb-2">{t.financialPage.expense}</h4>
                    {pnl.expense.lines.map(l => (
                      <div key={l.code} className="flex justify-between py-1 text-sm"><span className="text-gray-600">{l.name}</span><span className="font-medium text-red-600">{fmt(l.balance)}</span></div>
                    ))}
                    <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.financialPage.totalExpenses}</span><span className="text-red-700">{fmt(pnl.expense.total)}</span></div>
                  </div>
                </div>
                <div className="flex justify-between py-3 border-t-2 border-gray-300 text-lg font-bold">
                  <span>{t.financialPage.netIncome}</span>
                  <span className={pnl.net_income >= 0 ? 'text-green-700' : 'text-red-700'}>{fmt(pnl.net_income)} {pnl.currency}</span>
                </div>
              </div>
            ) : <p className="text-gray-400 text-center py-4">{t.financialPage.loading}</p>}
          </div>

          {/* Balance Sheet */}
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 mb-4">{t.financialPage.balanceSheet}</h3>
            {bs ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <h4 className="text-sm font-medium text-blue-700 mb-2">{t.financialPage.asset}</h4>
                    {bs.assets.lines.map(l => (
                      <div key={l.code} className="flex justify-between py-1 text-sm"><span className="text-gray-600">{l.name}</span><span className="font-medium">{fmt(l.balance)}</span></div>
                    ))}
                    <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.financialPage.totalAssets}</span><span>{fmt(bs.assets.total)}</span></div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-red-700 mb-2">{t.financialPage.liability}</h4>
                    {bs.liabilities.lines.map(l => (
                      <div key={l.code} className="flex justify-between py-1 text-sm"><span className="text-gray-600">{l.name}</span><span className="font-medium">{fmt(l.balance)}</span></div>
                    ))}
                    <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.financialPage.totalLiabilities}</span><span>{fmt(bs.liabilities.total)}</span></div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-purple-700 mb-2">{t.financialPage.equity}</h4>
                    {bs.equity.lines.map(l => (
                      <div key={l.code} className="flex justify-between py-1 text-sm"><span className="text-gray-600">{l.name}</span><span className="font-medium">{fmt(l.balance)}</span></div>
                    ))}
                    <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.financialPage.totalEquity}</span><span>{fmt(bs.equity.total)}</span></div>
                  </div>
                </div>
                <div className="flex justify-between py-3 border-t-2 border-gray-300 text-lg font-bold">
                  <span>{t.financialPage.le}</span>
                  <span>{fmt(bs.total_liabilities_and_equity)} {bs.currency}</span>
                </div>
                {!bs.is_balanced && <p className="text-sm text-red-600 font-medium">{t.financialPage.balanceNotBalanced}</p>}
              </div>
            ) : <p className="text-gray-400 text-center py-4">{t.financialPage.loading}</p>}
          </div>

          {/* Aging */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-4">{t.financialPage.arAging}</h3>
              {arAging ? (
                <div className="space-y-2">
                  {Object.entries(arAging.buckets).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-sm"><span className="text-gray-600 capitalize">{k.replace(/_/g, ' ')}</span><span className="font-medium">{fmt(v)}</span></div>
                  ))}
                  <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.financialPage.totalOutstanding}</span><span>{fmt(arAging.total_outstanding)}</span></div>
                </div>
              ) : <p className="text-gray-400 text-center py-4">{t.financialPage.loading}</p>}
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 mb-4">{t.financialPage.apAging}</h3>
              {apAging ? (
                <div className="space-y-2">
                  {Object.entries(apAging.buckets).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-sm"><span className="text-gray-600 capitalize">{k.replace(/_/g, ' ')}</span><span className="font-medium">{fmt(v)}</span></div>
                  ))}
                  <div className="flex justify-between py-2 border-t border-gray-200 mt-2 text-sm font-bold"><span>{t.financialPage.totalOutstanding}</span><span>{fmt(apAging.total_outstanding)}</span></div>
                </div>
              ) : <p className="text-gray-400 text-center py-4">{t.financialPage.loading}</p>}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* AI */}
      {/* ============================================================ */}
      {tab === 'ai' && (
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-emerald-600 to-teal-700 rounded-2xl p-6 text-white">
            <h3 className="font-bold text-lg mb-2">{t.financialPage.aiFinancialAnalyst}</h3>
            <p className="text-emerald-100 text-sm mb-4">{t.financialPage.aiFinancialDesc}</p>
            <div className="flex gap-3">
              <input type="text" value={aiQuery} onChange={e => setAiQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleAskAI()} placeholder={t.financialPage.aiPlaceholder} className="flex-1 px-4 py-3 rounded-xl bg-white/10 border border-white/20 text-white placeholder-emerald-200 focus:outline-none" />
              <button onClick={handleAskAI} className="px-6 py-3 bg-white text-emerald-700 font-semibold rounded-xl hover:bg-emerald-50">{t.financialPage.ask}</button>
            </div>
          </div>
          {aiResponse && <div className="bg-white rounded-xl border border-gray-200 p-5"><p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{aiResponse}</p></div>}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {['AR aging summary', 'Overdue invoices', 'Cash position', 'P&L overview', 'Top customers by balance', 'Unpaid bills', 'Bank reconciliation status'].map(q => (
              <button key={q} onClick={() => setAiQuery(q)} className="p-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50 text-left">{q}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
