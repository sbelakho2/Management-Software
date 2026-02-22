import { test, expect } from '@playwright/test';

/**
 * HR/Auditor Persona Path
 * Candidate -> Onboarding -> Training Matrix -> Certification Audit -> Performance Review
 */
test.describe('HR/Auditor Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    await page.request.post(`${apiUrl}/api/v1/dev/repair-core-rbac`).catch(() => undefined);

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'ceo@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Holly',
        last_name: 'HR',
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

  test('HR/Auditor Flow: Training and Executive', async ({ page }) => {
    // 1. Training (Skills & Matrix)
    await page.goto('/training');
    await expect(page.getByTestId('training-page')).toBeVisible();

    // 2. Executive (Org Health / Employee Risk)
    await page.goto('/executive');
    await expect(page.getByTestId('executive-page')).toBeVisible();
  });
});
