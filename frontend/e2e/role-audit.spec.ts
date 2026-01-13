import { test, expect, type Page } from '@playwright/test';

type BootstrapTokens = {
  access_token: string;
  refresh_token: string;
};

async function authenticateAsRole(page: Page, role: string): Promise<BootstrapTokens> {
  const apiUrl = process.env.E2E_API_URL || 'http://localhost:8004';

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
  'hr',
  'it',
  'warehouse',
  'auditor',
  'supply_chain',
  'team_lead'
];

const majorPages = [
  '/today',
  '/tasks',
  '/executive',
  '/analytics',
  '/hr',
  '/it',
  '/warehouse',
  '/auditor',
  '/sales',
  '/pipeline',
  '/quotes',
  '/customers',
  '/ops',
  '/production',
  '/projects',
  '/products',
  '/obeya',
  '/a3',
  '/ctq',
  '/exceptions',
  '/quality',
  '/andon',
  '/maintenance',
  '/supply-chain',
  '/training',
  '/training/matrix',
  '/finance',
  '/settings',
  '/admin'
];

test.describe('Full Role-based UI/UX Audit', () => {
  for (const role of rolesToTest) {
    test(`Audit for ${role}`, async ({ page }) => {
      await authenticateAsRole(page, role);
      
      // Wait for sidebar to be populated
      const sidebar = page.locator('aside');
      await expect(sidebar).toBeVisible();
      
      // Take a screenshot of the sidebar to verify correctly filtered links
      await sidebar.screenshot({ path: `e2e/screenshots/${role}/sidebar.png` });

      for (const path of majorPages) {
        await page.goto(path);
        // Wait a bit for page load and any redirects/hiding to happen
        await page.waitForTimeout(500);
        
        // We check if the body is visible. If PageGuard returned null, the main content area might be empty.
        // We capture what's there.
        await page.screenshot({ 
            path: `e2e/screenshots/${role}/${path.replace(/\//g, '-') || 'index'}.png`, 
            fullPage: true 
        });
      }
    });
  }
});
