import { test, expect } from '@playwright/test';

/**
 * Sales/Estimator Persona Path
 * Opportunity -> RFQ -> AI Drafting -> Quote Approval -> Sales Order -> Revision Tracking
 */
test.describe('Sales/Estimator Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    // Skip if backend is not available
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');

    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    // Bootstrap sales user
    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'sales.estimator@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Sarah',
        last_name: 'Estimator',
        is_superuser: true,
      },
    });
    expect(bootstrap.ok()).toBeTruthy();
    const tokens = await bootstrap.json();

    // Set tokens in localStorage before navigation
    await page.addInitScript((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);
  });

  test('Sales Estimator Flow: Pipeline and Quotes', async ({ page }) => {
    // 1. Go to Today (Cockpit)
    await page.goto('/today');
    await expect(page.locator('body')).toBeVisible();

    // 2. Go to Pipeline (Opportunities/RFQs)
    await page.goto('/pipeline');
    await expect(page.getByTestId('pipeline-page')).toBeVisible();
    await expect(page.getByText('Pipeline', { exact: true })).toBeVisible();
    
    // Create new RFQ
    await page.getByRole('button', { name: /new rfq/i }).click();
    await page.getByLabel(/customer/i).click();
    await page.getByRole('option').first().click();
    await page.getByLabel(/description/i).fill('E2E Test RFQ');
    await page.getByRole('button', { name: /save/i }).click();
    await expect(page.getByText(/created successfully/i)).toBeVisible();

    // 3. Go to Quotes
    await page.goto('/quotes');
    await expect(page.getByTestId('quotes-page')).toBeVisible();
    await expect(page.getByText('Quotes', { exact: true })).toBeVisible();
    
    // Verify Quote stats cards
    await expect(page.getByText('Pending Approval')).toBeVisible();
    await expect(page.getByText('Sent to Customers')).toBeVisible();

    // 4. Go to Customers (CRM)
    await page.goto('/customers');
    await expect(page.getByTestId('customers-page')).toBeVisible();
    await expect(page.getByText('Customers', { exact: true })).toBeVisible();

    // 5. Go to Products (Engineering Catalog)
    await page.goto('/products');
    await expect(page.getByTestId('products-page')).toBeVisible();
    await expect(page.getByText('Products', { exact: true })).toBeVisible();
  });
});
