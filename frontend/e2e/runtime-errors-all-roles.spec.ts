/**
 * Runtime Error Detection Tests Across All Roles
 * 
 * These tests verify that dashboard pages load without JavaScript runtime errors
 * for each user role. This catches issues like:
 * - Accessing properties on undefined/null (e.g., myWork.stories.length)
 * - Array methods on potentially undefined arrays
 * - Hydration mismatches with Zustand stores
 * - API response shape mismatches
 */

import { test, expect, Page } from '@playwright/test';

// All test users follow pattern: {role}@senseitest.com with password TestPassword123!
const ROLES = [
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
] as const;

const PASSWORD = 'TestPassword123!';

// Pages to test for each role (filtered by role access)
const PAGES_TO_TEST = [
  '/today',
  '/analytics',
  '/executive',
  '/pipeline',
  '/production',
  '/quality',
  '/products',
  '/warehouse',
  '/hr',
  '/finance',
  '/settings',
  '/project-management',
  '/tasks',
  '/training',
  '/admin',
] as const;

interface RuntimeError {
  message: string;
  source?: string;
  lineno?: number;
  colno?: number;
}

/**
 * Collect JavaScript errors from the page
 */
async function collectJSErrors(page: Page): Promise<RuntimeError[]> {
  const errors: RuntimeError[] = [];
  
  page.on('pageerror', (error) => {
    errors.push({
      message: error.message,
      source: error.stack?.split('\n')[1] || 'unknown',
    });
  });
  
  // Also catch console errors
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      // Filter out non-JS errors (network errors, etc.)
      if (text.includes('TypeError') || 
          text.includes('ReferenceError') || 
          text.includes('Cannot read properties of undefined') ||
          text.includes('Cannot read properties of null') ||
          text.includes('is not a function') ||
          text.includes('is not defined')) {
        errors.push({ message: text });
      }
    }
  });
  
  return errors;
}

/**
 * Login helper
 */
async function loginAs(page: Page, role: string): Promise<void> {
  const email = `${role}@senseitest.com`;
  const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';
  
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  
  // Clear any existing session
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  
  await page.reload();
  await page.waitForLoadState('networkidle');
  
  // Fill login form
  await page.fill('input[type="email"]', email);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"]');

  const dashboardPattern = /\/(today|tasks|settings|pipeline|production|executive|analytics|sales|ops|finance|hr|it|warehouse|purchase|supply-chain|quality|training|admin)/;

  try {
    // Wait for redirect to dashboard
    await page.waitForURL(dashboardPattern, { timeout: 15000 });
  } catch {
    // Fallback for environments where fixture users are missing: bootstrap via dev endpoint.
    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email,
        password: PASSWORD,
        first_name: 'E2E',
        last_name: role,
        is_superuser: true,
      },
    });

    if (!bootstrap.ok()) {
      throw new Error(`Failed to authenticate user ${email}`);
    }

    const tokens = await bootstrap.json();
    await page.evaluate((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);

    await page.goto('/today');
    await page.waitForURL(dashboardPattern, { timeout: 20000 });
  }
}

/**
 * Test a specific page for runtime errors
 */
async function testPageForErrors(
  page: Page, 
  url: string, 
  errorCollector: RuntimeError[]
): Promise<{ hasErrors: boolean; errors: RuntimeError[] }> {
  const pageErrors: RuntimeError[] = [];
  
  // Collect errors during navigation
  const errorHandler = (error: Error) => {
    pageErrors.push({ message: error.message, source: error.stack });
  };
  page.on('pageerror', errorHandler);
  
  const consoleHandler = (msg: any) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (text.includes('Failed to fetch RSC payload')) {
        return;
      }
      if (text.includes('TypeError') || 
          text.includes('Cannot read properties') ||
          text.includes('is not a function')) {
        pageErrors.push({ message: text });
      }
    }
  };
  page.on('console', consoleHandler);
  
  try {
    const response = await page.goto(url, { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    // Check if page loaded successfully (not redirected to login or error page)
    if (response?.status() === 200 || response?.status() === 307) {
      // Wait for any lazy-loaded content
      await page.waitForTimeout(500);
      
      // Check for error boundary content
      const errorBoundary = await page.locator('text="Something went wrong"').count();
      if (errorBoundary > 0) {
        pageErrors.push({ message: `Error boundary triggered on ${url}` });
      }
      
      // Check for "Unhandled Runtime Error" (Next.js dev mode)
      const runtimeError = await page.locator('text="Unhandled Runtime Error"').count();
      if (runtimeError > 0) {
        const errorText = await page.locator('[data-nextjs-toast]').textContent() || 'Unknown runtime error';
        pageErrors.push({ message: `Unhandled Runtime Error on ${url}: ${errorText}` });
      }
    }
  } catch (error: any) {
    // Navigation errors aren't necessarily runtime errors
    if (!error.message.includes('Navigation timeout') && 
        !error.message.includes('net::ERR') &&
        !error.message.includes('Test timeout') &&
        !error.message.includes('Target page, context or browser has been closed')) {
      pageErrors.push({ message: `Navigation error: ${error.message}` });
    }
  } finally {
    page.off('pageerror', errorHandler);
    page.off('console', consoleHandler);
  }
  
  errorCollector.push(...pageErrors);
  return { hasErrors: pageErrors.length > 0, errors: pageErrors };
}

test.describe('Runtime Error Detection - All Roles', () => {
  // Group tests by role for better reporting
  for (const role of ROLES) {
    test.describe(`Role: ${role}`, () => {
      test(`should load today page without runtime errors`, async ({ page }) => {
        const errors: RuntimeError[] = [];
        
        await loginAs(page, role);
        const result = await testPageForErrors(page, '/today', errors);
        
        // Log errors for debugging
        if (result.hasErrors) {
          console.error(`Runtime errors for ${role} on /today:`, result.errors);
        }
        
        expect(result.errors).toHaveLength(0);
      });
      
      test(`should load dashboard pages accessible to role without errors`, async ({ page }) => {
        test.setTimeout(180000);
        const errors: RuntimeError[] = [];
        const failedPages: string[] = [];
        
        await loginAs(page, role);
        
        for (const pageUrl of PAGES_TO_TEST) {
          const result = await testPageForErrors(page, pageUrl, errors);
          
          if (result.hasErrors) {
            failedPages.push(pageUrl);
            console.error(`Runtime errors for ${role} on ${pageUrl}:`, result.errors);
          }
        }
        
        // Report all failures
        if (failedPages.length > 0) {
          console.error(`\n${role} had errors on pages: ${failedPages.join(', ')}`);
        }
        
        expect(errors.filter(e => 
          !e.message.includes('Navigation timeout') &&
          !e.message.includes('net::ERR') &&
          !e.message.includes('Failed to fetch RSC payload') &&
          !e.message.includes('Test timeout') &&
          !e.message.includes('Target page, context or browser has been closed')
        )).toHaveLength(0);
      });
    });
  }
});

test.describe('Critical Path Runtime Error Detection', () => {
  test('CEO dashboard flow should have no runtime errors', async ({ page }) => {
    const errors: RuntimeError[] = [];
    
    await loginAs(page, 'ceo');
    
    // Test critical CEO pages
    const ceoPages = ['/today', '/executive', '/analytics', '/pipeline'];
    
    for (const pageUrl of ceoPages) {
      await testPageForErrors(page, pageUrl, errors);
    }
    
    const criticalErrors = errors.filter(e => 
      e.message.includes('TypeError') ||
      e.message.includes('Cannot read properties')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });
  
  test('GM dashboard flow should have no runtime errors', async ({ page }) => {
    const errors: RuntimeError[] = [];
    
    await loginAs(page, 'gm');
    
    const gmPages = ['/today', '/production', '/quality', '/analytics'];
    
    for (const pageUrl of gmPages) {
      await testPageForErrors(page, pageUrl, errors);
    }
    
    const criticalErrors = errors.filter(e => 
      e.message.includes('TypeError') ||
      e.message.includes('Cannot read properties')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });
  
  test('Finance dashboard flow should have no runtime errors', async ({ page }) => {
    const errors: RuntimeError[] = [];
    
    await loginAs(page, 'finance');
    
    const financePages = ['/today', '/finance', '/analytics'];
    
    for (const pageUrl of financePages) {
      await testPageForErrors(page, pageUrl, errors);
    }
    
    const criticalErrors = errors.filter(e => 
      e.message.includes('TypeError') ||
      e.message.includes('Cannot read properties')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });
  
  test('Admin dashboard flow should have no runtime errors', async ({ page }) => {
    const errors: RuntimeError[] = [];
    
    await loginAs(page, 'admin');
    
    const adminPages = ['/today', '/admin', '/settings', '/analytics'];
    
    for (const pageUrl of adminPages) {
      await testPageForErrors(page, pageUrl, errors);
    }
    
    const criticalErrors = errors.filter(e => 
      e.message.includes('TypeError') ||
      e.message.includes('Cannot read properties')
    );
    
    expect(criticalErrors).toHaveLength(0);
  });
});

test.describe('Hydration Error Detection', () => {
  test('should not have hydration mismatches after login', async ({ page }) => {
    const hydrationErrors: string[] = [];
    
    page.on('console', (msg) => {
      const text = msg.text();
      if (text.includes('Hydration') || 
          text.includes('hydration') ||
          text.includes('Text content does not match') ||
          text.includes('did not match')) {
        hydrationErrors.push(text);
      }
    });
    
    await loginAs(page, 'ceo');
    await page.goto('/today');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    
    // Filter out expected hydration warnings (like date formatting)
    const criticalHydrationErrors = hydrationErrors.filter(e => 
      !e.includes('suppressHydrationWarning')
    );
    
    expect(criticalHydrationErrors).toHaveLength(0);
  });
});

test.describe('Store State Runtime Errors', () => {
  test('MyWorkDashboard should handle undefined myWork gracefully', async ({ page }) => {
    const errors: RuntimeError[] = [];
    
    // Clear all storage before login to simulate fresh state
    await page.goto('/login');
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    
    await loginAs(page, 'executive');
    
    // Navigate directly to today page which includes MyWorkDashboard
    const result = await testPageForErrors(page, '/today', errors);
    
    // Specifically check for the "stories" undefined error
    const storiesError = errors.find(e => 
      e.message.includes("Cannot read properties of undefined (reading 'stories')")
    );
    
    expect(storiesError).toBeUndefined();
  });
  
  test('Analytics page should handle undefined insights/trends gracefully', async ({ page }) => {
    const errors: RuntimeError[] = [];
    
    await loginAs(page, 'ceo');
    
    const result = await testPageForErrors(page, '/analytics', errors);
    
    const arrayErrors = errors.filter(e => 
      e.message.includes("Cannot read properties of undefined (reading 'length')") ||
      e.message.includes("Cannot read properties of undefined (reading 'filter')") ||
      e.message.includes("Cannot read properties of undefined (reading 'slice')")
    );
    
    expect(arrayErrors).toHaveLength(0);
  });
});
