import { test, expect } from '@playwright/test';

/**
 * Operator/Team Lead Persona Path
 * Login -> Badge Scan -> Standard Work -> WO Execution -> Andon -> Escalation -> Micro-learning
 */
test.describe('Operator/Team Lead Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'operator.lead@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Mike',
        last_name: 'Operator',
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
    await expect(page.getByTestId('production-page')).toBeVisible();
    await expect(page.getByText('Production', { exact: true })).toBeVisible();
    
    // Simulate starting a Work Order
    const firstWorkOrder = page.locator('[data-testid^="work-order-card-"]').first();
    await expect(firstWorkOrder).toBeVisible();
    await firstWorkOrder.getByRole('button', { name: /start/i }).click();
    await expect(page.getByText(/started/i)).toBeVisible();

    // 2. Andon (Alerts & Escalation)
    await page.goto('/andon');
    await expect(page.getByTestId('andon-page')).toBeVisible();
    await expect(page.getByText('Andon Board', { exact: true })).toBeVisible();
    await expect(page.getByText('Active Alerts')).toBeVisible();

    // 3. Obeya (Team Huddle / KPIs)
    await page.goto('/obeya');
    await expect(page.getByTestId('obeya-page')).toBeVisible();
    await expect(page.getByText('Cognitive Obeya', { exact: true })).toBeVisible();

    // 4. Training (Micro-learning)
    await page.goto('/training');
    await expect(page.getByTestId('training-page')).toBeVisible();
    await expect(page.getByText('Training & Certifications', { exact: true })).toBeVisible();
  });
});
