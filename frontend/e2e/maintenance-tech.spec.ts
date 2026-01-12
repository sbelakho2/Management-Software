import { test, expect } from '@playwright/test';

/**
 * Maintenance/Technician Persona Path
 * TPM Schedule -> Execution -> Health Check -> Calibration -> WO Link -> Spare Parts
 */
test.describe('Maintenance/Technician Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'maintenance.tech@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Monty',
        last_name: 'Maintenance',
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

  test('Maintenance Flow: Maintenance and Production', async ({ page }) => {
    // 1. Maintenance & TPM Dashboard
    await page.goto('/maintenance');
    await expect(page.getByTestId('maintenance-page')).toBeVisible();
    await expect(page.getByText('Maintenance & TPM', { exact: true })).toBeVisible();

    // 2. Production (Asset Monitoring)
    await page.goto('/production');
    await expect(page.getByTestId('production-page')).toBeVisible();
  });
});
