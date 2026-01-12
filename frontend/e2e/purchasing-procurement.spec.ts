import { test, expect } from '@playwright/test';

/**
 * Purchasing/Procurement Persona Path
 * Requisition -> PO -> Match -> Payment -> AP Aging -> Vendor Scorecard
 */
test.describe('Purchasing/Procurement Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'purchasing.proc@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Penny',
        last_name: 'Purchasing',
        is_superuser: true,
      },
    });
    expect(bootstrap.ok()).toBeTruthy();
    const tokens = await bootstrap.json();

    await page.addInitScript((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);
  });

  test('Purchasing Flow: Pipeline, Products, Customers (Suppliers)', async ({ page }) => {
    // 1. Pipeline (Procurement RFQs)
    await page.goto('/pipeline');
    await expect(page.getByTestId('pipeline-page')).toBeVisible();

    // 2. Products (Material Catalog)
    await page.goto('/products');
    await expect(page.getByTestId('products-page')).toBeVisible();

    // 3. Customers (Supplier CRM)
    await page.goto('/customers');
    await expect(page.getByTestId('customers-page')).toBeVisible();
  });
});
