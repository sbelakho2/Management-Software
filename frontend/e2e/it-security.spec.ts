import { test, expect } from '@playwright/test';

/**
 * IT/Security Persona Path
 * SSO -> Access Policy -> Device Management -> OT Zoning -> Security Review -> Audit Logs -> Lineage
 */
test.describe('IT/Security Persona Path', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'it.security@sensei.os',
        password: 'ChangeMe123!',
        first_name: 'Isaac',
        last_name: 'IT',
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

  test('IT/Security Flow: Admin (Security & Lineage)', async ({ page }) => {
    // 1. Admin Dashboard (Security Settings)
    await page.goto('/admin');
    await expect(page.getByTestId('admin-page')).toBeVisible();
    await expect(page.getByText('System Administration', { exact: true })).toBeVisible();

    // Verify presence of security-related tabs
    await expect(page.getByRole('tab', { name: /Roles/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /Lineage/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /Features/i })).toBeVisible();

    // 2. Data Lineage (Traceability Audit)
    await page.getByRole('tab', { name: /Lineage/i }).click();
    await expect(page.getByText(/Lineage Viewer/i)).toBeVisible();
  });
});
