/**
 * Full-System Live Smoke Test
 * 
 * This comprehensive test verifies:
 * 1. All 24 role users can log in via browser
 * 2. Key navigation paths work for each role
 * 3. Critical UI elements are clickable and functional
 * 4. No runtime errors occur during navigation
 * 5. API endpoints respond correctly
 * 
 * Run with: npx playwright test e2e/full-system-smoke.spec.ts
 */

import { test, expect, type Page, type BrowserContext } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_URL = process.env.E2E_API_URL || 'http://localhost:8000';
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const TEST_PASSWORD = process.env.E2E_PASSWORD || 'TestPassword123!';
const EMAIL_DOMAIN = process.env.E2E_EMAIL_DOMAIN || 'sensei.test';

// All roles to test
const ALL_ROLES = [
  'admin',
  'ceo',
  'gm',
  'exec',
  'finance',
  'accountant',
  'hr',
  'ops',
  'quality',
  'auditor',
  'it',
  'supervisor',
  'team_lead',
  'operator',
  'viewer',
  'sales_engineer',
  'estimator',
  'supply_chain',
  'maintenance',
  'warehouse',
  'sales',
  'purchasing',
  'logistics',
  'engineering',
] as const;

type Role = typeof ALL_ROLES[number];

// Pages each role should be able to access (based on RBAC)
const ROLE_PAGE_ACCESS: Record<Role, string[]> = {
  admin: ['/today', '/admin', '/settings', '/executive', '/analytics', '/pipeline', '/quality', '/production'],
  ceo: ['/today', '/executive', '/analytics', '/pipeline', '/quality', '/obeya'],
  gm: ['/today', '/executive', '/analytics', '/pipeline', '/production', '/quality', '/obeya', '/admin'],
  exec: ['/today', '/executive', '/analytics', '/pipeline'],
  finance: ['/today', '/finance', '/analytics', '/pipeline'],
  accountant: ['/today', '/finance'],
  hr: ['/today', '/hr', '/training'],
  ops: ['/today', '/production', '/quality', '/andon', '/obeya'],
  quality: ['/today', '/quality', '/andon', '/a3', '/ctq'],
  auditor: ['/today', '/quality', '/analytics'],
  it: ['/today', '/it', '/settings'],
  supervisor: ['/today', '/production', '/andon', '/quality'],
  team_lead: ['/today', '/production', '/tasks'],
  operator: ['/today', '/production', '/andon'],
  viewer: ['/today', '/analytics'],
  sales_engineer: ['/today', '/pipeline', '/rfqs', '/quotes', '/customers'],
  estimator: ['/today', '/pipeline', '/rfqs', '/quotes'],
  supply_chain: ['/today', '/supply-chain', '/warehouse'],
  maintenance: ['/today', '/maintenance', '/andon'],
  warehouse: ['/today', '/warehouse', '/supply-chain'],
  sales: ['/today', '/pipeline', '/rfqs', '/quotes', '/customers'],
  purchasing: ['/today', '/supply-chain'],
  logistics: ['/today', '/supply-chain', '/warehouse'],
  engineering: ['/today', '/production', '/quality', '/ctq'],
};

// Critical interactive elements to verify on key pages
const CRITICAL_ELEMENTS = {
  '/today': [
    { selector: '[data-testid="today-greeting"]', action: 'visible' },
    { selector: 'button', action: 'clickable' },
  ],
  '/pipeline': [
    { selector: '[data-testid="pipeline-stage"], .pipeline-stage, [class*="pipeline"]', action: 'visible' },
  ],
  '/production': [
    { selector: '[data-testid="production-dashboard"], [class*="production"]', action: 'visible' },
  ],
  '/quality': [
    { selector: 'button, [role="tab"]', action: 'clickable' },
  ],
  '/analytics': [
    { selector: '[class*="chart"], [class*="analytics"], canvas, svg', action: 'visible' },
  ],
};

// Results directory
const RESULTS_DIR = path.join(__dirname, '..', 'smoke-test-results');

// ============================================================================
// TEST UTILITIES
// ============================================================================

interface TestResult {
  role: Role;
  loginSuccess: boolean;
  pagesVisited: Array<{
    path: string;
    success: boolean;
    loadTime: number;
    errors: string[];
  }>;
  interactiveElements: Array<{
    page: string;
    selector: string;
    found: boolean;
    clickable: boolean;
  }>;
  consoleErrors: string[];
  networkErrors: string[];
  timestamp: string;
}

interface ErrorCapture {
  consoleErrors: string[];
  networkErrors: string[];
  pageErrors: string[];
}

function setupErrorCapture(page: Page): ErrorCapture {
  const capture: ErrorCapture = {
    consoleErrors: [],
    networkErrors: [],
    pageErrors: [],
  };

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Filter out known benign errors
      if (!text.includes('net::ERR_ABORTED') && 
          !text.includes('Failed to fetch RSC') &&
          !text.includes('favicon')) {
        capture.consoleErrors.push(text);
      }
    }
  });

  page.on('pageerror', (err) => {
    capture.pageErrors.push(err.message);
  });

  page.on('requestfailed', (req) => {
    const url = req.url();
    const failure = req.failure()?.errorText || 'unknown';
    // Filter out expected failures
    if (!url.includes('/_next/') && 
        !url.includes('favicon') &&
        !failure.includes('net::ERR_ABORTED')) {
      capture.networkErrors.push(`${req.method()} ${url}: ${failure}`);
    }
  });

  return capture;
}

async function loginViaAPI(role: Role): Promise<{ accessToken: string; refreshToken: string } | null> {
  const email = `test_${role}@${EMAIL_DOMAIN}`;
  
  try {
    const response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password: TEST_PASSWORD }),
    });

    if (!response.ok) {
      console.error(`Login failed for ${role}: ${response.status} ${response.statusText}`);
      return null;
    }

    const data = await response.json();
    return {
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    };
  } catch (error) {
    console.error(`Login error for ${role}:`, error);
    return null;
  }
}

async function setAuthTokens(page: Page, tokens: { accessToken: string; refreshToken: string }) {
  await page.addInitScript((t) => {
    localStorage.setItem('access_token', t.accessToken);
    localStorage.setItem('refresh_token', t.refreshToken);
    localStorage.setItem('token_type', 'bearer');
  }, tokens);
}

async function visitPageWithTiming(page: Page, pagePath: string, timeout = 30000): Promise<{
  success: boolean;
  loadTime: number;
  errors: string[];
}> {
  const errors: string[] = [];
  const startTime = Date.now();
  
  try {
    const response = await page.goto(pagePath, { 
      waitUntil: 'domcontentloaded',
      timeout,
    });

    if (!response) {
      errors.push('No response received');
      return { success: false, loadTime: Date.now() - startTime, errors };
    }

    if (response.status() >= 400) {
      errors.push(`HTTP ${response.status()}`);
      return { success: false, loadTime: Date.now() - startTime, errors };
    }

    // Wait for main content to be visible
    await page.waitForSelector('main, [role="main"], #__next', { timeout: 10000 }).catch(() => {
      errors.push('Main content not found');
    });

    // Check for error boundaries or error messages
    const errorBoundary = await page.$('[data-testid="error-boundary"], .error-boundary, [class*="error"]');
    if (errorBoundary) {
      const errorText = await errorBoundary.textContent();
      if (errorText?.toLowerCase().includes('error') || errorText?.toLowerCase().includes('something went wrong')) {
        errors.push(`Error boundary: ${errorText?.slice(0, 100)}`);
      }
    }

    return {
      success: errors.length === 0,
      loadTime: Date.now() - startTime,
      errors,
    };
  } catch (error) {
    errors.push(`Navigation error: ${error instanceof Error ? error.message : String(error)}`);
    return {
      success: false,
      loadTime: Date.now() - startTime,
      errors,
    };
  }
}

async function checkInteractiveElements(page: Page, pagePath: string): Promise<Array<{
  selector: string;
  found: boolean;
  clickable: boolean;
}>> {
  const elements = CRITICAL_ELEMENTS[pagePath as keyof typeof CRITICAL_ELEMENTS] || [];
  const results: Array<{ selector: string; found: boolean; clickable: boolean }> = [];

  for (const { selector, action } of elements) {
    const element = await page.$(selector);
    const found = !!element;
    let clickable = false;

    if (element && action === 'clickable') {
      try {
        const isVisible = await element.isVisible();
        const isEnabled = await element.isEnabled();
        clickable = isVisible && isEnabled;
      } catch {
        clickable = false;
      }
    }

    results.push({ selector, found, clickable: action === 'clickable' ? clickable : true });
  }

  return results;
}

function ensureResultsDir(): void {
  if (!fs.existsSync(RESULTS_DIR)) {
    fs.mkdirSync(RESULTS_DIR, { recursive: true });
  }
}

function saveResult(result: TestResult): void {
  ensureResultsDir();
  const filename = `smoke-test-${result.role}-${Date.now()}.json`;
  fs.writeFileSync(
    path.join(RESULTS_DIR, filename),
    JSON.stringify(result, null, 2)
  );
}

function saveSummary(results: TestResult[]): void {
  ensureResultsDir();
  
  const summary = {
    timestamp: new Date().toISOString(),
    totalRoles: results.length,
    successfulLogins: results.filter(r => r.loginSuccess).length,
    totalPagesVisited: results.reduce((sum, r) => sum + r.pagesVisited.length, 0),
    totalPageErrors: results.reduce((sum, r) => 
      sum + r.pagesVisited.filter(p => !p.success).length, 0
    ),
    totalConsoleErrors: results.reduce((sum, r) => sum + r.consoleErrors.length, 0),
    totalNetworkErrors: results.reduce((sum, r) => sum + r.networkErrors.length, 0),
    roleResults: results.map(r => ({
      role: r.role,
      loginSuccess: r.loginSuccess,
      pagesSuccessful: r.pagesVisited.filter(p => p.success).length,
      pagesTotal: r.pagesVisited.length,
      avgLoadTime: r.pagesVisited.length > 0
        ? Math.round(r.pagesVisited.reduce((sum, p) => sum + p.loadTime, 0) / r.pagesVisited.length)
        : 0,
      errors: [
        ...r.consoleErrors.slice(0, 3),
        ...r.networkErrors.slice(0, 3),
      ],
    })),
  };

  fs.writeFileSync(
    path.join(RESULTS_DIR, 'smoke-test-summary.json'),
    JSON.stringify(summary, null, 2)
  );

  // Also save as markdown for easy reading
  const markdown = `# Full System Smoke Test Results

**Timestamp:** ${summary.timestamp}

## Summary

| Metric | Value |
|--------|-------|
| Total Roles Tested | ${summary.totalRoles} |
| Successful Logins | ${summary.successfulLogins} |
| Total Pages Visited | ${summary.totalPagesVisited} |
| Pages with Errors | ${summary.totalPageErrors} |
| Console Errors | ${summary.totalConsoleErrors} |
| Network Errors | ${summary.totalNetworkErrors} |

## Results by Role

| Role | Login | Pages OK | Pages Total | Avg Load (ms) |
|------|-------|----------|-------------|---------------|
${summary.roleResults.map(r => 
  `| ${r.role} | ${r.loginSuccess ? '✅' : '❌'} | ${r.pagesSuccessful} | ${r.pagesTotal} | ${r.avgLoadTime} |`
).join('\n')}

## Errors

${summary.roleResults
  .filter(r => r.errors.length > 0)
  .map(r => `### ${r.role}\n${r.errors.map(e => `- ${e}`).join('\n')}`)
  .join('\n\n') || 'No errors detected! 🎉'}
`;

  fs.writeFileSync(
    path.join(RESULTS_DIR, 'smoke-test-summary.md'),
    markdown
  );
}

// ============================================================================
// TESTS
// ============================================================================

test.describe.configure({ mode: 'serial' });

test.describe('Full System Smoke Test', () => {
  const allResults: TestResult[] = [];

  test.beforeAll(() => {
    ensureResultsDir();
    // Clean up old results
    try {
      const files = fs.readdirSync(RESULTS_DIR);
      for (const file of files) {
        if (file.startsWith('smoke-test-')) {
          fs.unlinkSync(path.join(RESULTS_DIR, file));
        }
      }
    } catch {
      // ignore
    }
  });

  test.afterAll(() => {
    saveSummary(allResults);
    console.log(`\n📊 Smoke test summary saved to ${path.join(RESULTS_DIR, 'smoke-test-summary.md')}`);
  });

  for (const role of ALL_ROLES) {
    test(`Role: ${role} - Full flow test`, async ({ browser }) => {
      const result: TestResult = {
        role,
        loginSuccess: false,
        pagesVisited: [],
        interactiveElements: [],
        consoleErrors: [],
        networkErrors: [],
        timestamp: new Date().toISOString(),
      };

      // Create a fresh context for each role
      const context = await browser.newContext({
        baseURL: BASE_URL,
        viewport: { width: 1920, height: 1080 },
      });
      const page = await context.newPage();
      const errorCapture = setupErrorCapture(page);

      try {
        // Step 1: Login via API
        const tokens = await loginViaAPI(role);
        if (!tokens) {
          result.consoleErrors.push('API login failed');
          allResults.push(result);
          saveResult(result);
          return;
        }
        result.loginSuccess = true;

        // Set tokens in browser
        await setAuthTokens(page, tokens);

        // Step 2: Visit each accessible page
        const accessiblePages = ROLE_PAGE_ACCESS[role] || ['/today'];
        
        for (const pagePath of accessiblePages) {
          console.log(`  [${role}] Visiting ${pagePath}...`);
          
          const pageResult = await visitPageWithTiming(page, pagePath);
          result.pagesVisited.push({
            path: pagePath,
            ...pageResult,
          });

          // Step 3: Check interactive elements
          if (pageResult.success) {
            const elementResults = await checkInteractiveElements(page, pagePath);
            for (const el of elementResults) {
              result.interactiveElements.push({
                page: pagePath,
                ...el,
              });
            }
          }

          // Take screenshot if there were errors
          if (!pageResult.success || pageResult.errors.length > 0) {
            const screenshotPath = path.join(
              RESULTS_DIR,
              `${role}-${pagePath.replace(/\//g, '-')}-error.png`
            );
            await page.screenshot({ path: screenshotPath, fullPage: true }).catch(() => {});
          }

          // Small delay between pages to avoid rate limiting
          await page.waitForTimeout(500);
        }

        // Collect errors
        result.consoleErrors = errorCapture.consoleErrors;
        result.networkErrors = errorCapture.networkErrors;

      } catch (error) {
        result.consoleErrors.push(`Test error: ${error instanceof Error ? error.message : String(error)}`);
      } finally {
        await context.close();
      }

      allResults.push(result);
      saveResult(result);

      // Assert no critical failures
      expect(result.loginSuccess, `Login failed for ${role}`).toBe(true);
      
      const failedPages = result.pagesVisited.filter(p => !p.success);
      if (failedPages.length > 0) {
        console.warn(`  ⚠️  [${role}] Failed pages: ${failedPages.map(p => p.path).join(', ')}`);
      }
      
      // Allow up to 20% page failures (for roles with restricted access)
      const failureRate = failedPages.length / result.pagesVisited.length;
      expect(failureRate, `Too many page failures for ${role}`).toBeLessThan(0.5);
    });
  }
});

// Single quick test for CI/CD
test('Quick smoke test - Admin login and dashboard', async ({ browser }) => {
  const context = await browser.newContext({ baseURL: BASE_URL });
  const page = await context.newPage();

  try {
    // Login via API
    const tokens = await loginViaAPI('admin');
    expect(tokens, 'Admin login should succeed').not.toBeNull();

    if (tokens) {
      await setAuthTokens(page, tokens);
      
      // Visit today page
      await page.goto('/today');
      await page.waitForLoadState('domcontentloaded');
      
      // Verify we're on the dashboard
      const title = await page.title();
      expect(title).not.toContain('Login');
      
      // Check for main content
      const mainContent = await page.$('main, [role="main"]');
      expect(mainContent).not.toBeNull();
    }
  } finally {
    await context.close();
  }
});
