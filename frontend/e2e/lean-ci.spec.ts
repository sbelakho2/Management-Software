import { test, expect } from '@playwright/test';

/**
 * Continuous Improvement/Lean Persona Path
 * A3 -> PDCA -> 5-Why -> Standard Work Update -> Micro-Lesson -> Gemba
 */
test.describe('Continuous Improvement/Lean Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'lean.ci@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Lana',
        last_name: 'Lean',
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

  test('Lean Flow: Obeya, Project Management, Training', async ({ page }) => {
    // 1. Obeya (Lean Problem Solving)
    await page.goto('/obeya');
    await expect(page.getByTestId('obeya-page')).toBeVisible();

    // 2. Project Management (A3 / Kaizen Projects)
    await page.goto('/project-management');
    await expect(page.getByTestId('project-management-page')).toBeVisible();

    // 3. Training (Socratic Learning)
    await page.goto('/training');
    await expect(page.getByTestId('training-page')).toBeVisible();
  });
});
