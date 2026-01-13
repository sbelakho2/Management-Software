import { test, expect, type Page } from '@playwright/test';

type BootstrapTokens = {
  access_token: string;
  refresh_token: string;
};

async function authenticateAsRole(page: Page, role: string): Promise<BootstrapTokens> {
  const apiUrl = process.env.E2E_API_URL || 'http://localhost:8003';

  const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
    data: {
      email: `${role.toLowerCase()}@sensei.os`,
      password: 'ChangeMe123!',
      first_name: 'E2E',
      last_name: role.toUpperCase(),
      role: role.toLowerCase(),
      is_superuser: role.toLowerCase() === 'admin' || role.toLowerCase() === 'ceo',
    },
  });

  if (bootstrap.ok()) {
    const tokens = await bootstrap.json();
    await page.addInitScript((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);

    await page.goto('/today');
    await page.waitForLoadState('networkidle');
    return tokens as BootstrapTokens;
  }

  throw new Error(`Failed to bootstrap user with role ${role}`);
}

const rolesToTest = [
  'admin',
  'ceo',
  'gm',
  'operator',
  'sales_engineer',
  'quality',
  'supervisor',
  'finance',
  'hr'
];

const majorPages = [
  '/today',
  '/tasks',
  '/executive',
  '/analytics',
  '/pipeline',
  '/production',
  '/quality',
  '/andon',
  '/obeya',
  '/inventory',
  '/maintenance',
  '/settings'
];

test.describe('Role-based Access Screenshots', () => {
  for (const role of rolesToTest) {
    test(`Capture screenshots for ${role}`, async ({ page }) => {
      await authenticateAsRole(page, role);
      
      // Take screenshot of the sidebar specifically
      const sidebar = page.locator('aside');
      if (await sidebar.isVisible()) {
          await sidebar.screenshot({ path: `e2e/screenshots/${role}-sidebar.png` });
      }

      for (const path of majorPages) {
        await page.goto(path);
        // Wait for some content or a timeout to allow for error messages to appear
        await page.waitForTimeout(1000); 
        await page.screenshot({ path: `e2e/screenshots/${role}-${path.replace(/\//g, '') || 'index'}.png`, fullPage: true });
      }
    });
  }
});
