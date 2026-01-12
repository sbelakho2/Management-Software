import { test, expect } from '@playwright/test';

/**
 * Finance/Accountant Persona Path
 * Invoice -> Payment -> 3-Way Match -> Ledger -> Period Close
 */
test.describe('Finance/Accountant Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'finance.acc@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Finn',
        last_name: 'Finance',
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

  test('Finance/Accountant Flow: Executive and Analytics', async ({ page }) => {
    // 1. Executive Dashboard (Financial Overview)
    await page.goto('/executive');
    await expect(page.getByTestId('executive-page')).toBeVisible();
    await expect(page.getByText('North Star Dashboard', { exact: true })).toBeVisible();

    // 2. Analytics (Deep Dive)
    await page.goto('/analytics');
    await expect(page.getByTestId('analytics-page')).toBeVisible();
    await expect(page.getByText('Advanced Analytics', { exact: true })).toBeVisible();
    
    // 3. Quotes (Revenue Pipeline)
    await page.goto('/quotes');
    await expect(page.getByTestId('quotes-page')).toBeVisible();
  });
});
