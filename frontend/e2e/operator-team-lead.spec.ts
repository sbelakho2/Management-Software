import { test, expect } from '@playwright/test';

/**
 * Operator/Team Lead Persona Path
 * Login -> Badge Scan -> Standard Work -> WO Execution -> Andon -> Escalation -> Micro-learning
 */
test.describe('Operator/Team Lead Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    await page.request.post(`${apiUrl}/api/v1/dev/repair-core-rbac`);

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'ceo@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'E2E',
        last_name: 'Ops',
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

  test('Operator/Team Lead Flow: Production, Andon, Obeya, Training', async ({ page }) => {
    // 1. Production (Shop Floor Execution)
    await page.goto('/production');
    await page.waitForLoadState('domcontentloaded');
    await expect(page.getByTestId('production-page')).toBeVisible({ timeout: 20000 });
    
    // Simulate starting a Work Order
    const firstStartButton = page.getByRole('button', { name: /start/i }).first();
    if ((await firstStartButton.count()) > 0) {
      await firstStartButton.click();
    }

    // 2. Andon (Alerts & Escalation)
    await page.goto('/andon');
    await expect(page.getByTestId('andon-page')).toBeVisible();

    // 3. Obeya (Team Huddle / KPIs)
    await page.goto('/obeya');
    await expect(page.getByTestId('obeya-page')).toBeVisible();

    // 4. Training (Micro-learning)
    await page.goto('/training');
    await expect(page.getByTestId('training-page')).toBeVisible();
  });
});
