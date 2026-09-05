import { act } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { createRoot, type Root } from 'react-dom/client';
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
let container: HTMLDivElement;
let root: Root;

async function renderApp() {
  container = document.createElement('div');
  document.body.appendChild(container);
  root = createRoot(container);
  await act(async () => { root.render(<App />); });
}

afterEach(() => {
  vi.clearAllMocks();
  act(() => root?.unmount());
  container?.remove();
});

describe('EOS frontend functional smoke tests', () => {
  it('renders the Arabic dashboard and loads reporting data', async () => {
    await renderApp();

    expect(container.textContent).toContain('مرحباً بك في EOS');
    expect(container.textContent).toContain('إيرادات الشهر');
    expect(container.textContent).toContain('12,500');
    expect(mockedReports.profitAndLoss).toHaveBeenCalledTimes(1);
    expect(mockedReports.sales).toHaveBeenCalledTimes(1);
    expect(mockedReports.inventory).toHaveBeenCalledTimes(1);
  });

  it('switches language and preserves the dashboard workflow', async () => {
    await renderApp();
    const languageButton = Array.from(container.querySelectorAll('button')).find((button) => button.textContent?.includes('English'));
    expect(languageButton).toBeTruthy();

    await act(async () => { languageButton?.click(); });

    expect(container.textContent).toContain('Welcome to EOS');
    expect(container.textContent).toContain('Customers');
    expect(container.textContent).toContain('Inventory');
    expect(container.textContent).toContain('Reports');
  });

  it('navigates between customer and inventory workspaces', async () => {
    await renderApp();
    const customersButton = Array.from(container.querySelectorAll('button')).find((button) => button.textContent?.includes('العملاء'));
    const inventoryButton = Array.from(container.querySelectorAll('button')).find((button) => button.textContent?.includes('المخزون'));

    expect(customersButton).toBeTruthy();
    expect(inventoryButton).toBeTruthy();

    await act(async () => { customersButton?.click(); });
    expect(container.textContent).toContain('مساحة عمل مبنية من Metadata');

    await act(async () => { inventoryButton?.click(); });
    expect(container.textContent).toContain('المخزون الفعلي');
  });
});
