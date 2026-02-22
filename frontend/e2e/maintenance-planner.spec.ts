import { test, expect } from '@playwright/test';

/**
 * Maintenance Planner Persona Path
 * Equipment -> TPM Plan -> MWO -> Spare Parts -> Downtime Analysis -> MTBF
 */
test.describe('Maintenance Planner Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    await page.request.post(`${apiUrl}/api/v1/dev/repair-core-rbac`).catch(() => undefined);

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'ceo@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Phil',
        last_name: 'Planner',
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

  test('Maintenance Planner Flow: Maintenance, Analytics, Obeya', async ({ page }) => {
    // 1. Maintenance & TPM (Master Schedule)
    await page.goto('/maintenance');
    await expect(page.getByTestId('maintenance-page')).toBeVisible();

    // 2. Analytics (MTBF/MTTR Trends)
    await page.goto('/analytics');
    await expect(page).toHaveURL(/\/analytics/);
    await expect(page.locator('body')).toBeVisible();

    // 3. Obeya (OEE & Reliability)
    await page.goto('/obeya');
    await expect(page.getByTestId('obeya-page')).toBeVisible();
  });
});
