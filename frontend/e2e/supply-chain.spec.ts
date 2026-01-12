import { test, expect } from '@playwright/test';

/**
 * Supply Chain Persona Path
 * Portal -> RFQ Response -> Scorecard -> Disruption Simulation -> Cycle Count -> GR
 */
test.describe('Supply Chain Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'supply.chain@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Stan',
        last_name: 'Supply',
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

  test('Supply Chain Flow: Intelligence, Customers (Suppliers), Pipeline', async ({ page }) => {
    // 1. Supply Chain Intelligence
    await page.goto('/supply-chain');
    await expect(page.getByTestId('supply-chain-page')).toBeVisible();
    await expect(page.getByText('Supply Chain Intelligence', { exact: true })).toBeVisible();

    // 2. Customers (Suppliers)
    await page.goto('/customers');
    await expect(page.getByTestId('customers-page')).toBeVisible();

    // 3. Pipeline (Procurement RFQs)
    await page.goto('/pipeline');
    await expect(page.getByTestId('pipeline-page')).toBeVisible();
  });
});
