import { test, expect } from '@playwright/test';

/**
 * Logistics/Shipping Persona Path
 * Packing List -> Shipment -> Carrier -> Tracking -> Notification -> POD
 */
test.describe('Logistics/Shipping Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'logistics.ship@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Larry',
        last_name: 'Logistics',
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

  test('Logistics Flow: Production, Today, Supply Chain', async ({ page }) => {
    // 1. Production (Final Assembly / Ship)
    await page.goto('/production');
    await expect(page.getByTestId('production-page')).toBeVisible();

    // 2. Today (Logistics Cockpit)
    await page.goto('/today');
    await expect(page.locator('body')).toBeVisible();

    // 3. Supply Chain (Carrier Coordination)
    await page.goto('/supply-chain');
    await expect(page.getByTestId('supply-chain-page')).toBeVisible();
  });
});
