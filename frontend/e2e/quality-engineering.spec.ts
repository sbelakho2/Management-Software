import { test, expect } from '@playwright/test';

/**
 * Quality/Engineering Persona Path
 * NC -> 8D -> CAPA -> SPC -> Drawing Sync -> ECO -> Revision Control
 */
test.describe('Quality/Engineering Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    await page.request.post(`${apiUrl}/api/v1/dev/repair-core-rbac`).catch(() => undefined);

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'ceo@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Quincy',
        last_name: 'Quality',
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

  test('Quality/Engineering Flow: Quality, Products, Production', async ({ page }) => {
    // 1. Quality (NCR/CAPA/Inspections)
    await page.goto('/quality');
    await expect(page.getByTestId('quality-page')).toBeVisible();

    // 2. Products (Engineering Catalog / Revisions)
    await page.goto('/products');
    await expect(page.getByTestId('products-page')).toBeVisible();

    // 3. Production (Verify Quality on Shop Floor)
    await page.goto('/production');
    await expect(page.getByTestId('production-page')).toBeVisible();
  });
});
