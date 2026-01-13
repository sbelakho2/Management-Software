/**
 * Comprehensive Role-based UI Audit with Screenshots
 * 
 * This test logs in as each of the 24 user roles, navigates through
 * all accessible pages, clicks buttons, and takes screenshots to
 * verify role-based access control is working correctly.
 */

import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// All roles to audit (one user per role is created by backend/scripts/ensure_e2e_role_users.py)
const ALL_ROLES = [
  'admin',
  'ceo',
  'executive',
  'gm',
  'sales_rep',
  'sales_engineer',
  'estimator',
  'quality',
  'quality_inspector',
  'supervisor',
  'operator',
  'finance',
  'accountant',
  'hr',
  'it',
  'security',
  'warehouse',
  'shipping_receiver',
  'auditor',
  'supply_chain',
  'purchasing',
  'maintenance',
  'maintenance_tech',
  'team_lead',
];

// Test credentials (seeded via scripts)
const TEST_PASSWORD = 'TestPassword123!';
const EMAIL_DOMAIN = 'senseitest.com';

const ONLY_PAGE_PATHS = (process.env.E2E_PAGE_PATHS || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);
const DISABLE_BUTTON_CLICKS = process.env.E2E_DISABLE_BUTTON_CLICKS === '1';

// Pages to test based on sidebar navigation
const PAGES_TO_TEST = [
  { path: '/today', name: 'Today' },
  { path: '/tasks', name: 'Tasks' },
  { path: '/executive', name: 'Executive' },
  { path: '/analytics', name: 'Analytics' },
  { path: '/pipeline', name: 'Pipeline' },
  { path: '/rfqs', name: 'RFQs' },
  { path: '/quotes', name: 'Quotes' },
  { path: '/customers', name: 'Customers' },
  { path: '/production', name: 'Production' },
  { path: '/projects', name: 'Projects' },
  { path: '/products', name: 'Products' },
  { path: '/obeya', name: 'Obeya' },
  { path: '/a3', name: 'A3' },
  { path: '/ctq', name: 'CTQ' },
  { path: '/exceptions', name: 'Exceptions' },
  { path: '/quality', name: 'Quality' },
  { path: '/andon', name: 'Andon' },
  { path: '/maintenance', name: 'Maintenance' },
  { path: '/supply-chain', name: 'Supply Chain' },
  { path: '/warehouse', name: 'Warehouse' },
  { path: '/training', name: 'Training' },
  { path: '/finance', name: 'Finance' },
  { path: '/hr', name: 'HR' },
  { path: '/it', name: 'IT' },
  { path: '/settings', name: 'Settings' },
  { path: '/admin', name: 'Admin' },
];

// Create screenshots directory
const SCREENSHOT_DIR = path.join(__dirname, '..', 'role-screenshots');

type CapturedError = { source: string; message: string };
type CapturedRequestFailure = { url: string; method: string; failure: string };
type CapturedResponseError = { url: string; status: number; method?: string };

function attachErrorCapture(page: Page) {
  const consoleErrors: CapturedError[] = [];
  const pageErrors: CapturedError[] = [];
  const requestFailures: CapturedRequestFailure[] = [];
  const responseErrors: CapturedResponseError[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push({ source: 'console', message: msg.text() });
    }
  });

  page.on('pageerror', (err) => {
    pageErrors.push({ source: 'pageerror', message: err.message });
  });

  page.on('requestfailed', (req) => {
    requestFailures.push({
      url: req.url(),
      method: req.method(),
      failure: req.failure()?.errorText || 'requestfailed',
    });
  });

  page.on('response', (resp) => {
    const status = resp.status();
    if (status >= 500) {
      responseErrors.push({ url: resp.url(), status });
    }
  });

  return {
    consoleErrors,
    pageErrors,
    requestFailures,
    responseErrors,
    snapshotCounts: () => ({
      consoleErrors: consoleErrors.length,
      pageErrors: pageErrors.length,
      requestFailures: requestFailures.length,
      responseErrors: responseErrors.length,
    }),
  };
}

async function ensureScreenshotDir(role: string): Promise<string> {
  const roleDir = path.join(SCREENSHOT_DIR, role);
  if (!fs.existsSync(roleDir)) {
    fs.mkdirSync(roleDir, { recursive: true });
  }
  return roleDir;
}

async function loginAsRole(page: Page, role: string): Promise<boolean> {
  const email = `${role}@${EMAIL_DOMAIN}`;
  
  // Navigate to login page
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  
  // Take screenshot of login page
  const roleDir = await ensureScreenshotDir(role);
  await page.screenshot({ path: path.join(roleDir, '00-login-page.png'), fullPage: true });
  
  // Fill login form
  await page.fill('input[name="email"], input[type="email"]', email);
  await page.fill('input[name="password"], input[type="password"]', TEST_PASSWORD);
  
  // Take screenshot before submit
  await page.screenshot({ path: path.join(roleDir, '01-login-filled.png'), fullPage: true });
  
  // Submit login form
  await page.click('button[type="submit"]');
  
  // Wait for navigation or error
  try {
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10000 });
    
    // Take screenshot after login
    await page.screenshot({ path: path.join(roleDir, '02-after-login.png'), fullPage: true });
    
    return true;
  } catch {
    // Login failed - take error screenshot
    await page.screenshot({ path: path.join(roleDir, '02-login-failed.png'), fullPage: true });
    return false;
  }
}

async function captureSidebar(page: Page, role: string): Promise<void> {
  const roleDir = await ensureScreenshotDir(role);
  
  // Wait for sidebar to be visible
  const sidebar = page.locator('aside, nav[role="navigation"], [data-testid="sidebar"]').first();
  
  try {
    await sidebar.waitFor({ state: 'visible', timeout: 5000 });
    await sidebar.screenshot({ path: path.join(roleDir, '03-sidebar.png') });
  } catch {
    // Sidebar not visible - might be mobile view or collapsed
    await page.screenshot({ path: path.join(roleDir, '03-full-page-no-sidebar.png'), fullPage: true });
  }
}

async function getSidebarHrefs(page: Page): Promise<string[]> {
  const hrefs = await page
    .locator('aside a[href], nav[role="navigation"] a[href], [data-testid="sidebar"] a[href]')
    .evaluateAll((els) =>
      els
        .map((e) => (e as HTMLAnchorElement).getAttribute('href') || '')
        .filter(Boolean)
        .map((href) => href.split('#')[0])
    );
  // de-dupe and keep only internal paths
  return Array.from(new Set(hrefs)).filter((h) => h.startsWith('/'));
}

async function navigateAndScreenshot(
  page: Page,
  role: string,
  pagePath: string,
  pageName: string,
  index: number,
  capture?: ReturnType<typeof attachErrorCapture>
): Promise<{ accessible: boolean; hasError: boolean; errorMessage?: string }> {
  const roleDir = await ensureScreenshotDir(role);
  const screenshotName = `${String(index + 10).padStart(2, '0')}-${pageName.toLowerCase().replace(/\s+/g, '-')}.png`;
  
  try {
    const beforeCounts = capture?.snapshotCounts();
    await page.goto(pagePath, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1000); // Wait for any animations
    
    // Check for error indicators
    const errorIndicators = [
      // explicit status codes
      page.locator('text=/\\b401\\b/'),
      page.locator('text=/\\b403\\b/'),
      page.locator('text=/\\b404\\b/'),
      page.locator('text=/\\b500\\b/'),

      // common auth/route denial messages
      page.locator('text=Access Denied'),
      page.locator('text=Unauthorized'),
      page.locator('text=Not Found'),

      // common app exception pages
      page.locator('text=Something went wrong'),
      page.locator('text=Application error'),
      page.locator('text=Client-side exception'),

      // structured error elements (if present)
      page.locator('[data-testid="error"], [data-testid="error-page"], [data-testid="not-found"], [data-testid="forbidden"]'),
      page.locator('[role="alert"]:has-text("error"), [role="alert"]:has-text("Error")'),
    ];
    
    let hasError = false;
    let errorMessage: string | undefined;
    
    for (const indicator of errorIndicators) {
      try {
        if (await indicator.first().isVisible({ timeout: 500 })) {
          hasError = true;
          errorMessage = await indicator.first().textContent() || undefined;
          break;
        }
      } catch {
        // Indicator not found - that's fine
      }
    }

    if (!hasError && capture && beforeCounts) {
      const afterCounts = capture.snapshotCounts();
      const newConsoleErrors = afterCounts.consoleErrors - beforeCounts.consoleErrors;
      const newPageErrors = afterCounts.pageErrors - beforeCounts.pageErrors;
      const newRequestFailures = afterCounts.requestFailures - beforeCounts.requestFailures;
      const newResponseErrors = afterCounts.responseErrors - beforeCounts.responseErrors;

      if (newConsoleErrors > 0 || newPageErrors > 0 || newRequestFailures > 0 || newResponseErrors > 0) {
        hasError = true;
        const newest =
          capture.pageErrors.at(-1)?.message ||
          capture.consoleErrors.at(-1)?.message ||
          capture.requestFailures.at(-1)?.failure ||
          (capture.responseErrors.at(-1)
            ? `HTTP ${capture.responseErrors.at(-1)!.status}`
            : undefined);
        errorMessage = newest;
      }
    }
    
    // Check if we were redirected to login (access denied)
    const currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      await page.screenshot({ path: path.join(roleDir, screenshotName), fullPage: true });
      return { accessible: false, hasError: false };
    }
    
    // Take full page screenshot
    await page.screenshot({ path: path.join(roleDir, screenshotName), fullPage: true });
    
    return { accessible: true, hasError, errorMessage };
  } catch (error) {
    // Navigation failed
    await page
      .screenshot({ path: path.join(roleDir, `${screenshotName}-error.png`), fullPage: true })
      .catch(() => undefined);
    return { 
      accessible: false, 
      hasError: true, 
      errorMessage: error instanceof Error ? error.message : 'Unknown error' 
    };
  }
}

async function clickButtonsAndScreenshot(
  page: Page,
  role: string,
  pagePath: string,
  pageName: string
): Promise<void> {
  const roleDir = await ensureScreenshotDir(role);

  // Find all clickable buttons (excluding navigation/sidebar)
  const excluded = page.locator(
    'nav button, nav [role="button"], nav a, aside button, aside [role="button"], aside a, [data-testid="sidebar"] button, [data-testid="sidebar"] [role="button"], [data-testid="sidebar"] a'
  );
  const buttons = page
    .locator('button:visible:not([disabled]), [role="button"]:visible')
    .filter({ hasNot: excluded });

  const buttonCount = await buttons.count();

  for (let i = 0; i < buttonCount; i++) {
    try {
      const button = buttons.nth(i);
      const buttonText = await button.textContent() || `button-${i}`;
      const sanitizedText = buttonText.trim().slice(0, 20).replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();

      const beforeUrl = page.url();

      // Click the button
      await button.click({ timeout: 5000 });
      await page.waitForLoadState('networkidle').catch(() => undefined);
      await page.waitForTimeout(300);

      // Take screenshot after click
      const screenshotName = `${pageName.toLowerCase().replace(/\s+/g, '-')}-click-${String(i + 1).padStart(3, '0')}-${sanitizedText}.png`;
      await page.screenshot({ path: path.join(roleDir, screenshotName), fullPage: true });

      // Close common modal patterns
      const closeButtons = page.locator(
        '[aria-label="Close"], [data-testid="close"], button:has-text("Cancel"), button:has-text("Close"), button:has-text("Dismiss")'
      );
      if (await closeButtons.first().isVisible({ timeout: 500 }).catch(() => false)) {
        await closeButtons.first().click({ timeout: 2000 }).catch(() => undefined);
        await page.waitForTimeout(250);
      }

      // If navigation occurred, return to the original page to continue clicking remaining buttons
      const afterUrl = page.url();
      if (afterUrl !== beforeUrl || afterUrl.endsWith('/login')) {
        await page.goto(pagePath, { waitUntil: 'networkidle', timeout: 15000 }).catch(() => undefined);
        await page.waitForTimeout(500);
      }
    } catch {
      // Button click failed - continue to next
    }
  }
}

// Run tests only on Chromium for speed
test.describe.configure({ mode: 'serial' });

test.describe('Role-based UI Audit with Screenshots', () => {
  // Create one test per role
  for (const role of ALL_ROLES) {
    test(`Audit ${role} role`, async ({ page }) => {
      test.setTimeout(30 * 60 * 1000); // up to 30 minutes per role
      
      const results: {
        role: string;
        loginSuccess: boolean;
        sidebarHrefs?: string[];
        pages: Array<{
          path: string;
          name: string;
          accessible: boolean;
          hasError: boolean;
          errorMessage?: string;
          clickedButtons?: number;
        }>;
      } = {
        role,
        loginSuccess: false,
        sidebarHrefs: [],
        pages: [],
      };
      
      // Login as this role
      const loginSuccess = await loginAsRole(page, role);
      results.loginSuccess = loginSuccess;
      
      if (!loginSuccess) {
        console.log(`❌ Login failed for role: ${role}`);

        // Save results for debugging even when login fails
        const roleDir = await ensureScreenshotDir(role);
        fs.writeFileSync(path.join(roleDir, 'results.json'), JSON.stringify(results, null, 2));

        expect(loginSuccess, `Login must succeed for role: ${role}`).toBe(true);
      }
      
      console.log(`✅ Logged in as: ${role}`);

      const capture = attachErrorCapture(page);
      
      // Capture sidebar
      await captureSidebar(page, role);
      results.sidebarHrefs = await getSidebarHrefs(page);
      
      // Navigate to each page and take screenshots
      const sidebarPages = results.sidebarHrefs || [];
      const hardcodedPages = PAGES_TO_TEST.map((p) => p.path);
      const unionPaths = Array.from(new Set([...sidebarPages, ...hardcodedPages])).filter((p) => p.startsWith('/'));
      const pagesToTest = ONLY_PAGE_PATHS.length ? unionPaths.filter((p) => ONLY_PAGE_PATHS.includes(p)) : unionPaths;

      for (let i = 0; i < pagesToTest.length; i++) {
        const pagePath = pagesToTest[i];
        const pageName = PAGES_TO_TEST.find((p) => p.path === pagePath)?.name || pagePath.replace(/^\//, '') || 'root';
        
        const result = await navigateAndScreenshot(page, role, pagePath, pageName, i, capture);
        const pageEntry: {
          path: string;
          name: string;
          accessible: boolean;
          hasError: boolean;
          errorMessage?: string;
          clickedButtons?: number;
        } = {
          path: pagePath,
          name: pageName,
          ...result,
        };
        results.pages.push(pageEntry);
        
        if (result.accessible && !result.hasError && !DISABLE_BUTTON_CLICKS) {
          await clickButtonsAndScreenshot(page, role, pagePath, pageName);
          // Best-effort count: infer by matching screenshots created for this page
          const roleDir = await ensureScreenshotDir(role);
          const prefix = `${pageName.toLowerCase().replace(/\s+/g, '-')}-click-`;
          try {
            const files = fs.readdirSync(roleDir).filter((f) => f.startsWith(prefix));
            pageEntry.clickedButtons = files.length;
          } catch {
            pageEntry.clickedButtons = undefined;
          }
        }
      }

      // Sidebar correctness heuristic:
      // - Any sidebar link that leads to a restricted page should not be present.
      // - Any accessible audited page should be represented in the sidebar (best-effort).
      const sidebarHrefs = results.sidebarHrefs || [];
      const restrictedPages = results.pages.filter((p) => !p.accessible).map((p) => p.path);
      const accessiblePages = results.pages.filter((p) => p.accessible).map((p) => p.path);
      const sidebarHasRestricted = sidebarHrefs.filter((h) => restrictedPages.includes(h));
      const sidebarMissingAccessible = accessiblePages.filter((p) => !sidebarHrefs.includes(p));

      if (sidebarHasRestricted.length > 0) {
        console.log(`❌ Sidebar exposes restricted links for ${role}:`, sidebarHasRestricted);
      }
      if (sidebarMissingAccessible.length > 0) {
        console.log(`⚠ Sidebar missing accessible links for ${role}:`, sidebarMissingAccessible);
      }
      
      // Save results as JSON
      const roleDir = await ensureScreenshotDir(role);
      fs.writeFileSync(
        path.join(roleDir, 'results.json'),
        JSON.stringify(results, null, 2)
      );
      
      // Log summary
      const accessibleCount = results.pages.filter(p => p.accessible).length;
      const errorCount = results.pages.filter(p => p.hasError).length;
      console.log(`Role ${role}: ${accessibleCount}/${pagesToTest.length} pages accessible, ${errorCount} errors`);
      
      // Verify no unexpected errors (403/401 are expected for restricted pages)
      const unexpectedErrors = results.pages.filter(
        p => p.hasError && p.errorMessage && !p.errorMessage.includes('401') && !p.errorMessage.includes('403')
      );
      
      expect(unexpectedErrors.length).toBe(0);
      expect(sidebarHasRestricted.length).toBe(0);
    });
  }
});

test('Generate audit summary report', async () => {
  // Wait for all role tests to complete, then generate summary
  const summaryPath = path.join(SCREENSHOT_DIR, 'audit-summary.json');
  const summary: Record<string, unknown> = {
    generatedAt: new Date().toISOString(),
    roles: {},
  };
  
  for (const role of ALL_ROLES) {
    const roleDir = path.join(SCREENSHOT_DIR, role);
    const resultsPath = path.join(roleDir, 'results.json');
    
    if (fs.existsSync(resultsPath)) {
      const results = JSON.parse(fs.readFileSync(resultsPath, 'utf-8'));
      summary.roles[role] = results;
    }
  }
  
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
  console.log(`Audit summary saved to: ${summaryPath}`);
});
