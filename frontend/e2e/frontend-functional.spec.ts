import { test, expect } from '@playwright/test';

const json = (data: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ status: 'success', data }),
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'e2e-access-token');
    localStorage.setItem('refresh_token', 'e2e-refresh-token');
  });

  await page.route('**/api/v1/**', async (route) => {
    const url = route.request().url();
    if (url.includes('/auth/me')) {
      await route.fulfill(json({ id: 'e2e-user', tenant_id: 'e2e-tenant', email: 'e2e@example.test' }));
      return;
    }
    if (url.includes('/dynamic/onboarding/industries')) {
      await route.fulfill(json([{ id: '1', industry_code: 'construction', industry_name: 'Construction', industry_name_ar: 'مقاولات', description: 'E2E industry', default_modules: ['projects'] }]));
      return;
    }
    if (url.includes('/dynamic/onboarding/modules')) {
      await route.fulfill(json([{ id: '1', module_code: 'projects', module_name: 'Projects', module_name_ar: 'المشروعات', description: 'E2E module' }]));
      return;
    }
    if (url.includes('/dynamic/onboarding/status')) {
      await route.fulfill(json({ status: 'draft', current_step: 'industry_selection', progress_percent: 0, selected_modules: [] }));
      return;
    }
    if (url.includes('/reports/profit-and-loss')) {
      await route.fulfill(json({ revenue: 125000, gross_profit: 45000, gross_margin: 36, receivables: 18000, cost_of_goods: 80000 }));
      return;
    }
    if (url.includes('/reports/sales')) {
      await route.fulfill(json({ daily: [{ count: 3, amount: 1000 }, { count: 5, amount: 2000 }], top_customers: [{ id: 'c1' }] }));
      return;
    }
    if (url.includes('/reports/inventory')) {
      await route.fulfill(json({ total_items: 42, low_stock_items: 2 }));
      return;
    }
    await route.fulfill(json([]));
  });
});

test('loads the authenticated production build and exposes the core workspace', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'مرحباً بك في EOS' })).toBeVisible();
  await expect(page.getByText('إيرادات الشهر')).toBeVisible();
  await expect(page.locator('.eos-app')).toHaveAttribute('dir', 'rtl');
});

test('navigates across customers, inventory, reports and settings', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: 'العملاء' }).click();
  await expect(page.getByRole('heading', { name: 'العملاء' })).toBeVisible();

  await page.getByRole('button', { name: 'المخزون' }).click();
  await expect(page.getByRole('heading', { name: 'المخزون' })).toBeVisible();

  await page.getByRole('button', { name: 'التقارير' }).click();
  await expect(page.getByRole('heading', { name: 'التقارير' })).toBeVisible();
  await expect(page.getByText('125,000')).toBeVisible();

  await page.getByRole('button', { name: 'الإعدادات' }).click();
  await expect(page.getByRole('heading', { name: 'الإعدادات' })).toBeVisible();
});

test('switches between Arabic and English without losing the workspace', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /English/ }).click();
  await expect(page.getByRole('heading', { name: 'Welcome to EOS' })).toBeVisible();
  await expect(page.locator('.eos-app')).toHaveAttribute('dir', 'ltr');

  await page.getByRole('button', { name: 'العربية' }).click();
  await expect(page.getByRole('heading', { name: 'مرحباً بك في EOS' })).toBeVisible();
  await expect(page.locator('.eos-app')).toHaveAttribute('dir', 'rtl');
});

test('opens the metadata-driven ERP builder and loads its first step', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'ابدأ بناء نظامك' }).first().click();
  await expect(page.getByText('EOS BUSINESS BUILDER')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'النشاط' })).toBeVisible();
  await expect(page.getByRole('button', { name: /مقاولات/ })).toBeVisible();
});
