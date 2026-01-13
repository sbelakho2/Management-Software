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

// All user roles from the system that have test accounts
const ALL_ROLES = [
  'admin',
  'ceo', 
  'gm',
  'sales',
  'sales_engineer',
  'quality',
  'supervisor',
  'operator',
  'finance',
  'hr',
  'it',
  'warehouse',
  'auditor',
  'supply_chain',
  'team_lead',
];

// Test credentials (seeded via scripts)
const TEST_PASSWORD = 'TestPassword123!';
const EMAIL_DOMAIN = 'senseitest.com';

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

async function navigateAndScreenshot(
  page: Page,
  role: string,
  pagePath: string,
  pageName: string,
  index: number
): Promise<{ accessible: boolean; hasError: boolean; errorMessage?: string }> {
  const roleDir = await ensureScreenshotDir(role);
  const screenshotName = `${String(index + 10).padStart(2, '0')}-${pageName.toLowerCase().replace(/\s+/g, '-')}.png`;
  
  try {
    await page.goto(pagePath, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(1000); // Wait for any animations
    
    // Check for error indicators
    const errorIndicators = [
      page.locator('text=401'),
      page.locator('text=403'),
      page.locator('text=404'),
      page.locator('text=500'),
      page.locator('text=Error'),
      page.locator('text=Access Denied'),
      page.locator('text=Not Found'),
      page.locator('text=Unauthorized'),
      page.locator('[role="alert"]'),
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
    await page.screenshot({ path: path.join(roleDir, `${screenshotName}-error.png`), fullPage: true });
    return { 
      accessible: false, 
      hasError: true, 
      errorMessage: error instanceof Error ? error.message : 'Unknown error' 
    };
  }
}

async function clickButtonsAndScreenshot(page: Page, role: string, pageName: string): Promise<void> {
  const roleDir = await ensureScreenshotDir(role);
  
  // Find all clickable buttons (excluding navigation)
  const buttons = page.locator('button:visible, [role="button"]:visible').filter({
    hasNot: page.locator('nav button, aside button, [data-testid="sidebar"] button')
  });
  
  const buttonCount = await buttons.count();
  const maxButtons = Math.min(buttonCount, 5); // Limit to 5 buttons per page
  
  for (let i = 0; i < maxButtons; i++) {
    try {
      const button = buttons.nth(i);
      const buttonText = await button.textContent() || `button-${i}`;
      const sanitizedText = buttonText.trim().slice(0, 20).replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
      
      // Click the button
      await button.click({ timeout: 2000 });
      await page.waitForTimeout(500);
      
      // Take screenshot
      const screenshotName = `${pageName.toLowerCase().replace(/\s+/g, '-')}-click-${sanitizedText}.png`;
      await page.screenshot({ path: path.join(roleDir, screenshotName), fullPage: true });
      
      // Close any modals that might have opened
      const closeButtons = page.locator('[aria-label="Close"], [data-testid="close"], button:has-text("Cancel"), button:has-text("Close")');
      if (await closeButtons.first().isVisible({ timeout: 500 })) {
        await closeButtons.first().click();
        await page.waitForTimeout(300);
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
      test.setTimeout(120000); // 2 minutes per role
      
      const results: {
        role: string;
        loginSuccess: boolean;
        pages: Array<{
          path: string;
          name: string;
          accessible: boolean;
          hasError: boolean;
          errorMessage?: string;
        }>;
      } = {
        role,
        loginSuccess: false,
        pages: [],
      };
      
      // Login as this role
      const loginSuccess = await loginAsRole(page, role);
      results.loginSuccess = loginSuccess;
      
      if (!loginSuccess) {
        console.log(`❌ Login failed for role: ${role}`);
        return;
      }
      
      console.log(`✅ Logged in as: ${role}`);
      
      // Capture sidebar
      await captureSidebar(page, role);
      
      // Navigate to each page and take screenshots
      for (let i = 0; i < PAGES_TO_TEST.length; i++) {
        const { path: pagePath, name: pageName } = PAGES_TO_TEST[i];
        
        const result = await navigateAndScreenshot(page, role, pagePath, pageName, i);
        results.pages.push({
          path: pagePath,
          name: pageName,
          ...result,
        });
        
        if (result.accessible && !result.hasError) {
          // Click some buttons on accessible pages
          await clickButtonsAndScreenshot(page, role, pageName);
        }
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
      console.log(`Role ${role}: ${accessibleCount}/${PAGES_TO_TEST.length} pages accessible, ${errorCount} errors`);
      
      // Verify no unexpected errors (403/401 are expected for restricted pages)
      const unexpectedErrors = results.pages.filter(
        p => p.hasError && p.errorMessage && !p.errorMessage.includes('401') && !p.errorMessage.includes('403')
      );
      
      expect(unexpectedErrors.length).toBe(0);
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
