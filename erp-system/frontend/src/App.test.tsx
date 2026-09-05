import { afterEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import App from './App';
import { reportsAPI } from './services/api';

vi.mock('./services/api', () => ({
  reportsAPI: {
    profitAndLoss: vi.fn().mockResolvedValue({ data: { data: { revenue: 12500, gross_margin: 32, gross_profit: 4000, receivables: 2500 } } }),
    sales: vi.fn().mockResolvedValue({ data: { data: { daily: [{ count: 3, amount: 900 }], top_customers: [{ id: 'c1' }] } } }),
    inventory: vi.fn().mockResolvedValue({ data: { data: { total_items: 17, low_stock_items: 2 } } }),
  },
}));

const mockedReports = vi.mocked(reportsAPI);

afterEach(() => {
  vi.clearAllMocks();
});

describe('EOS frontend functional smoke tests', () => {
  it('renders the Arabic dashboard and loads reporting data', async () => {
    render(<App />);

    expect(screen.getByText('مرحباً بك في EOS')).toBeTruthy();
    expect(screen.getByText('إيرادات الشهر')).toBeTruthy();
    expect(screen.getByText('12,500')).toBeTruthy();

    expect(mockedReports.profitAndLoss).toHaveBeenCalledTimes(1);
    expect(mockedReports.sales).toHaveBeenCalledTimes(1);
    expect(mockedReports.inventory).toHaveBeenCalledTimes(1);
  });

  it('switches language and preserves the dashboard workflow', () => {
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: /English/i }));

    expect(screen.getByText('Welcome to EOS')).toBeTruthy();
    expect(screen.getByText('Home')).toBeTruthy();
    expect(screen.getByText('Customers')).toBeTruthy();
    expect(screen.getByText('Inventory')).toBeTruthy();
    expect(screen.getByText('Reports')).toBeTruthy();
  });

  it('navigates to customers and inventory workspaces', () => {
    render(<App />);

    fireEvent.click(screen.getByRole('button', { name: 'العملاء' }));
    expect(screen.getByRole('heading', { name: 'العملاء' })).toBeTruthy();

    fireEvent.click(screen.getByRole('button', { name: 'المخزون' }));
    expect(screen.getByRole('heading', { name: 'المخزون' })).toBeTruthy();
  });
});
