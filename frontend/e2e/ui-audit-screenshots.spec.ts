import { test, expect, type Page } from '@playwright/test';

type BootstrapTokens = {
  access_token: string;
  refresh_token: string;
};

async function authenticate(page: Page, email: string): Promise<BootstrapTokens> {
  const apiUrl = process.env.E2E_API_URL || 'http://localhost:8001';

  const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
    data: {
      email: email,
      password: 'SenseiOS2026!',
      first_name: 'Audit',
      last_name: email.split('@')[0],
      is_superuser: email === 'ceo@sensei.os',
    },
  });

  if (bootstrap.ok()) {
    const tokens = await bootstrap.json();
    await page.addInitScript((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);
    return tokens as BootstrapTokens;
  }

  throw new Error(`Failed to bootstrap user: ${email}`);
}

const roles = [
  { name: 'CEO', email: 'ceo@sensei.os', path: '/executive' },
  { name: 'GM', email: 'gm@sensei.os', path: '/obeya' },
  { name: 'OPERATOR', email: 'operator@sensei.os', path: '/today' },
  { name: 'SALES', email: 'sales@sensei.os', path: '/pipeline' },
  { name: 'QUALITY', email: 'quality@sensei.os', path: '/ctq' },
];

test.describe('UI/UX Audit Screenshots', () => {
  for (const role of roles) {
    test(`Capture screenshots for ${role.name}`, async ({ page }) => {
      await authenticate(page, role.email);
      
      // Navigate to the main path for the role
      await page.goto(role.path);
      await page.waitForTimeout(2000); // Wait for animations/loading
      
      // Take a full page screenshot
      await page.screenshot({ 
        path: `e2e/screenshots/${role.name.toLowerCase()}-main.png`, 
        fullPage: true 
      });

      // Try some other common paths if they exist
      const commonPaths = ['/obeya', '/analytics', '/settings'];
      for (const p of commonPaths) {
          if (p !== role.path) {
              await page.goto(p);
              await page.waitForTimeout(1000);
              await page.screenshot({ 
                path: `e2e/screenshots/${role.name.toLowerCase()}-${p.replace('/', '')}.png`, 
                fullPage: true 
              });
          }
      }
    });
  }
});
