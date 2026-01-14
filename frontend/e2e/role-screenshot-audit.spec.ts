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

  const shouldIgnoreConsoleError = (text: string) => {
    // Next.js dev sometimes logs transient RSC fetch issues during navigations;
    // these are noisy and not actionable for RBAC.
    if (text.includes('Failed to fetch RSC payload for')) return true;
    // Aborted resource loads are common when navigating quickly between pages.
    // We only treat them as relevant if they clearly involve the API.
    if (text.includes('net::ERR_ABORTED') && !text.includes('/api/')) return true;
    return false;
  };

  const shouldIgnoreRequestFailure = (url: string, failure: string) => {
    // Playwright/Next dev commonly emits aborted requests during route changes.
    // We treat these as non-fatal noise unless they surface as actual page errors
    // or API error responses.
    if (failure.includes('net::ERR_ABORTED')) return true;
    if (url.includes('/_next/')) return true;
    if (url.endsWith('/favicon.ico')) return true;
    return false;
  };

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      if (!shouldIgnoreConsoleError(text)) {
        consoleErrors.push({ source: 'console', message: text });
      }
    }
  });

  page.on('pageerror', (err) => {
    pageErrors.push({ source: 'pageerror', message: err.message });
  });

  page.on('requestfailed', (req) => {
    const url = req.url();
    const failure = req.failure()?.errorText || 'requestfailed';
    if (shouldIgnoreRequestFailure(url, failure)) return;
    requestFailures.push({
      url,
      method: req.method(),
      failure,
    });
  });

  page.on('response', (resp) => {
    const status = resp.status();
    const url = resp.url();
    const isApi = url.includes('/api/');

    if (status >= 500 || (isApi && status >= 400)) {
      responseErrors.push({ url, status });
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

function clearRoleArtifacts(roleDir: string): void {
  try {
    for (const entry of fs.readdirSync(roleDir)) {
      const fullPath = path.join(roleDir, entry);
      try {
        // Clean *everything* inside the role directory, including nested
        // folders like "training/" or "settings/".
        fs.rmSync(fullPath, { recursive: true, force: true });
      } catch {
        // ignore
      }
    }
  } catch {
    // ignore
  }
}

function clearAllArtifacts(): void {
  try {
    // Remove the aggregated summary from any previous run.
    const summaryPath = path.join(SCREENSHOT_DIR, 'audit-summary.json');
    if (fs.existsSync(summaryPath)) {
      fs.unlinkSync(summaryPath);
    }
  } catch {
    // ignore
  }

  for (const role of ALL_ROLES) {
    const roleDir = path.join(SCREENSHOT_DIR, role);
    if (fs.existsSync(roleDir)) {
      clearRoleArtifacts(roleDir);
    }
  }
}

async function loginAsRole(
  page: Page,
  role: string,
  capture?: ReturnType<typeof attachErrorCapture>
): Promise<boolean> {
  const email = `${role}@${EMAIL_DOMAIN}`;

  const roleDir = await ensureScreenshotDir(role);
  const loginLogPath = path.join(roleDir, 'login-progress.log');

  const log = (line: string) => {
    try {
      fs.appendFileSync(loginLogPath, `[${new Date().toISOString()}] ${line}\n`);
    } catch {
      // ignore
    }
  };

  for (let attempt = 1; attempt <= 8; attempt++) {
    const beforeCounts = capture?.snapshotCounts();

    // Navigate to login page
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded').catch(() => undefined);
    await page.waitForTimeout(300).catch(() => undefined);

    log(`attempt=${attempt} url=${page.url()}`);

    // Take screenshot of login page
    await page.screenshot({ path: path.join(roleDir, '00-login-page.png'), fullPage: true, timeout: 15000 }).catch(() => undefined);

    // Fill login form
    await page.fill('input[name="email"], input[type="email"]', email);
    await page.fill('input[name="password"], input[type="password"]', TEST_PASSWORD);

    // Take screenshot before submit
    await page.screenshot({ path: path.join(roleDir, '01-login-filled.png'), fullPage: true, timeout: 15000 }).catch(() => undefined);

    // Submit login form and observe backend response
    const loginResponse = await Promise.all([
      page
        .waitForResponse(
          (r) =>
            r.url().includes('/auth/login') &&
            r.request().method() === 'POST',
          { timeout: 15000 }
        )
        .catch(() => null),
      page.click('button[type="submit"]'),
    ]).then(([resp]) => resp);

    if (loginResponse) {
      const status = loginResponse.status();
      log(`attempt=${attempt} loginResponse status=${status} url=${loginResponse.url()}`);
      if (status === 429) {
        await page.screenshot({ path: path.join(roleDir, `02-login-rate-limited-attempt-${attempt}.png`), fullPage: true });
        const headers = loginResponse.headers();
        const retryAfterSeconds = Number.parseFloat(headers['retry-after'] || '');
        const waitMs = Number.isFinite(retryAfterSeconds)
          ? Math.min(120_000, Math.max(1_000, retryAfterSeconds * 1000))
          : Math.min(120_000, 2000 * Math.pow(2, attempt - 1));
        log(`attempt=${attempt} rate_limited waitMs=${waitMs}`);
        await page.waitForTimeout(waitMs).catch(() => undefined);
        continue;
      }
      if (status >= 400 && status !== 202) {
        await page.screenshot({ path: path.join(roleDir, `02-login-http-${status}.png`), fullPage: true });
        return false;
      }
    } else {
      log(`attempt=${attempt} loginResponse=null`);
    }

    if (capture && beforeCounts) {
      const afterCounts = capture.snapshotCounts();
      const newRequestFailures = afterCounts.requestFailures - beforeCounts.requestFailures;
      const newResponseErrors = afterCounts.responseErrors - beforeCounts.responseErrors;
      const newPageErrors = afterCounts.pageErrors - beforeCounts.pageErrors;
      const newConsoleErrors = afterCounts.consoleErrors - beforeCounts.consoleErrors;

      if (newRequestFailures > 0 || newResponseErrors > 0 || newPageErrors > 0 || newConsoleErrors > 0) {
        log(
          `attempt=${attempt} newErrors requestfailed=${newRequestFailures} responseErrors=${newResponseErrors} pageErrors=${newPageErrors} consoleErrors=${newConsoleErrors}`
        );

        const recentRequestFailures = capture.requestFailures.slice(-Math.max(0, newRequestFailures));
        const recentResponseErrors = capture.responseErrors.slice(-Math.max(0, newResponseErrors));
        const recentPageErrors = capture.pageErrors.slice(-Math.max(0, newPageErrors));
        const recentConsoleErrors = capture.consoleErrors.slice(-Math.max(0, newConsoleErrors));

        for (const rf of recentRequestFailures) log(`requestfailed ${rf.method} ${rf.url} :: ${rf.failure}`);
        for (const re of recentResponseErrors) log(`responseError ${re.status} ${re.url}`);
        for (const pe of recentPageErrors) log(`pageerror ${pe.message}`);
        for (const ce of recentConsoleErrors) log(`consoleerror ${ce.message}`);
      }
    }

    // Wait for navigation away from /login
    try {
      await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 20000 });
      await page.waitForLoadState('domcontentloaded').catch(() => undefined);
      await page.waitForTimeout(300);

      // Take screenshot after login
      await page.screenshot({ path: path.join(roleDir, '02-after-login.png'), fullPage: true, timeout: 15000 }).catch(() => undefined);
      return true;
    } catch {
      await page
        .screenshot({ path: path.join(roleDir, `02-login-failed-attempt-${attempt}.png`), fullPage: true, timeout: 15000 })
        .catch(() => undefined);
      await page.waitForTimeout(1000 * attempt).catch(() => undefined);
    }
  }

  return false;
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
    // In Next.js dev, the first hit to a route can be slow due to on-demand compilation.
    // Waiting for 'domcontentloaded' often times out even though the server has responded.
    // Use 'commit' to ensure we at least have a response, then do a best-effort DOM settle.
    const resp = await page.goto(pagePath, { waitUntil: 'commit', timeout: 15000 });
    await page.waitForLoadState('domcontentloaded', { timeout: 5000 }).catch(() => undefined);
    await page.waitForTimeout(400);
    
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

    // If we got an HTTP response, record obvious error status codes.
    const status = resp?.status();
    if (typeof status === 'number' && status >= 400) {
      hasError = true;
      errorMessage = `HTTP ${status} for ${pagePath}`;
    }
    
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

    if (capture && beforeCounts) {
      const afterCounts = capture.snapshotCounts();
      const newConsoleErrors = afterCounts.consoleErrors - beforeCounts.consoleErrors;
      const newPageErrors = afterCounts.pageErrors - beforeCounts.pageErrors;
      const newRequestFailures = afterCounts.requestFailures - beforeCounts.requestFailures;
      const newResponseErrors = afterCounts.responseErrors - beforeCounts.responseErrors;

      const hasHardCaptureErrors = newPageErrors > 0 || newRequestFailures > 0 || newResponseErrors > 0;
      const shouldAttachConsole = newConsoleErrors > 0 && (hasError || hasHardCaptureErrors);

      if (hasHardCaptureErrors || shouldAttachConsole) {
        const newest =
          capture.pageErrors.at(-1)?.message ||
          (capture.responseErrors.at(-1)
            ? `HTTP ${capture.responseErrors.at(-1)!.status} ${capture.responseErrors.at(-1)!.url}`
            : undefined) ||
          capture.requestFailures.at(-1)?.failure;

        const newestConsole = capture.consoleErrors.at(-1)?.message;

        if (!hasError && hasHardCaptureErrors) {
          hasError = true;
          errorMessage = newest;
        } else if (newest) {
          errorMessage = errorMessage ? `${errorMessage} | ${newest}` : newest;
        }

        if (shouldAttachConsole && newestConsole) {
          errorMessage = errorMessage ? `${errorMessage} | ${newestConsole}` : newestConsole;
        }
      }
    }
    
    // Check if we were redirected to login (access denied)
    const currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      await page.screenshot({ path: path.join(roleDir, screenshotName), fullPage: true });
      return { accessible: false, hasError: false };
    }
    
    // Take full page screenshot
    await page.screenshot({ path: path.join(roleDir, screenshotName), fullPage: true, timeout: 15000 });
    
    return { accessible: true, hasError, errorMessage };
  } catch (error) {
    // Navigation failed
    await page
      .screenshot({ path: path.join(roleDir, `${screenshotName}-error.png`), fullPage: false, timeout: 10000 })
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
  pageName: string,
  capture?: ReturnType<typeof attachErrorCapture>
): Promise<{ total: number; unique: number; clicked: number; failures: number; durationMs: number }> {
  const roleDir = await ensureScreenshotDir(role);
  const progressPath = path.join(roleDir, 'click-progress.log');

  // Find all clickable buttons (excluding navigation/sidebar)
  const excluded = page.locator(
    'nav button, nav [role="button"], nav a, aside button, aside [role="button"], aside a, [data-testid="sidebar"] button, [data-testid="sidebar"] [role="button"], [data-testid="sidebar"] a'
  );
  const buttons = page
    .locator('button:visible:not([disabled]), [role="button"]:visible')
    .filter({ hasNot: excluded });

  let buttonCount = 0;
  try {
    buttonCount = await buttons.count();
  } catch {
    return { total: 0, unique: 0, clicked: 0, failures: 0, durationMs: 0 };
  }
  const startedAt = Date.now();
  const seen = new Set<string>();
  let clicked = 0;
  let failures = 0;
  let unique = 0;

  let clickIndex = 0;
  // Re-scan until we stop finding new unique buttons.
  for (let scan = 1; scan <= 20; scan++) {
    const handles = await buttons.elementHandles().catch(() => []);
    let progressMade = false;

    // If the page/context is gone, stop trying to click.
    if (handles.length === 0) {
      break;
    }

    for (let i = 0; i < handles.length; i++) {
      const handle = handles[i];
      try {
        const buttonKey = await handle
          .evaluate((el) => {
            const text = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80);
            const aria = el.getAttribute('aria-label') || '';
            const testId = el.getAttribute('data-testid') || '';
            const type = (el as HTMLButtonElement).getAttribute?.('type') || '';
            const tag = el.tagName;
            const role = el.getAttribute('role') || '';
            const name = [testId, aria, text].filter(Boolean).join('|');
            return `${tag}|${role}|${type}|${name}`;
          })
          .catch(() => `scan-${scan}-idx-${i}`);

        if (seen.has(buttonKey)) {
          continue;
        }

        seen.add(buttonKey);
        unique += 1;
        progressMade = true;

        // Best-effort label for filenames/logs.
        const buttonText = await handle
          .evaluate((el) => (el.textContent || '').trim())
          .catch(() => '') as string;
        const sanitizedText = (buttonText || `button-${clickIndex + 1}`)
          .trim()
          .slice(0, 20)
          .replace(/[^a-zA-Z0-9]/g, '-')
          .toLowerCase();

        const beforeUrl = page.url();
        clickIndex += 1;
        const clickLabel = `${pageName}#${clickIndex} ${sanitizedText}`;

        try {
          fs.appendFileSync(
            progressPath,
            `[${new Date().toISOString()}] scan=${scan} click=${clickIndex} start url=${beforeUrl} key=${buttonKey}\n`
          );
        } catch {
          // ignore
        }

        await handle.scrollIntoViewIfNeeded({ timeout: 2000 }).catch(() => undefined);

        // Click the button with a hard timeout.
        await handle.click({ timeout: 5000 });
        await page.waitForTimeout(150);

        // Take screenshot after click (viewport only for speed)
        const screenshotName = `${pageName.toLowerCase().replace(/\s+/g, '-')}-click-${String(clickIndex).padStart(4, '0')}-${sanitizedText}.png`;
        const shotOk = await page
          .screenshot({ path: path.join(roleDir, screenshotName), fullPage: false, timeout: 15000 })
          .then(() => true)
          .catch(() => false);
        if (shotOk) {
          clicked += 1;
        } else {
          failures += 1;
        }

        // If a click logged us out, re-login and return to the page so we can keep clicking.
        if (page.url().includes('/login')) {
          const reloginOk = await loginAsRole(page, role, capture);
          if (!reloginOk) {
            failures += 1;
            break;
          }
          await page.goto(pagePath, { waitUntil: 'commit', timeout: 15000 }).catch(() => undefined);
          await page.waitForLoadState('domcontentloaded', { timeout: 5000 }).catch(() => undefined);
          await page.waitForTimeout(250).catch(() => undefined);
        }

        // Close common modal patterns
        const closeButtons = page.locator(
          '[aria-label="Close"], [data-testid="close"], button:has-text("Cancel"), button:has-text("Close"), button:has-text("Dismiss")'
        );
        if (await closeButtons.first().isVisible({ timeout: 500 }).catch(() => false)) {
          await closeButtons.first().click({ timeout: 2000 }).catch(() => undefined);
          await page.waitForTimeout(200);
        }

        // If navigation occurred, return to the original page
        const afterUrl = page.url();
        if (afterUrl !== beforeUrl || afterUrl.endsWith('/login')) {
          await page.goto(pagePath, { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => undefined);
          await page.waitForTimeout(300);
        }

        try {
          fs.appendFileSync(
            progressPath,
            `[${new Date().toISOString()}] scan=${scan} click=${clickIndex} done url=${page.url()}\n`
          );
        } catch {
          // ignore
        }
      } catch {
        failures += 1;
        try {
          fs.appendFileSync(
            progressPath,
            `[${new Date().toISOString()}] scan=${scan} click=${clickIndex} FAILED\n`
          );
        } catch {
          // ignore
        }
      } finally {
        await handle.dispose().catch(() => undefined);
      }
    }

    // If we didn't discover any new unique buttons in this scan, we are done.
    if (!progressMade) {
      break;
    }
  }

  return {
    total: buttonCount,
    unique,
    clicked,
    failures,
    durationMs: Date.now() - startedAt,
  };
}

test.describe.serial('Role-based UI Audit with Screenshots', () => {
  test.beforeAll(() => {
    // Keep runs deterministic: start from a clean artifact slate.
    clearAllArtifacts();
  });

  // Create one test per role
  for (const role of ALL_ROLES) {
    test(`Audit ${role} role`, async ({ page }) => {
      test.setTimeout(30 * 60 * 1000); // 30 minutes per role
      
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
          durationMs?: number;
          clickStats?: {
            total: number;
            unique: number;
            clicked: number;
            failures: number;
            durationMs: number;
          };
        }>;
      } = {
        role,
        loginSuccess: false,
        sidebarHrefs: [],
        pages: [],
      };

      // Ensure artifacts are from this run (avoid stale screenshots/logs)
      const roleDir = await ensureScreenshotDir(role);
      clearRoleArtifacts(roleDir);

      // Capture errors for the whole role flow (including login)
      const capture = attachErrorCapture(page);
      
      // Login as this role
      const loginSuccess = await loginAsRole(page, role, capture);
      results.loginSuccess = loginSuccess;
      
      if (!loginSuccess) {
        console.log(`❌ Login failed for role: ${role}`);

        // Save results for debugging even when login fails
        fs.writeFileSync(path.join(roleDir, 'results.json'), JSON.stringify(results, null, 2));

        // Defer assertions to the final analysis pass.
        return;
      }
      
      console.log(`✅ Logged in as: ${role}`);
      
      // Capture sidebar
      await captureSidebar(page, role);
      results.sidebarHrefs = await getSidebarHrefs(page);
      
      // Navigate to each page and take screenshots
      const sidebarPages = results.sidebarHrefs || [];
      const hardcodedPages = PAGES_TO_TEST.map((p) => p.path);
      const pagesToTest = Array.from(new Set([...sidebarPages, ...hardcodedPages])).filter((p) => p.startsWith('/'));

      for (let i = 0; i < pagesToTest.length; i++) {
        const pagePath = pagesToTest[i];
        const pageName = PAGES_TO_TEST.find((p) => p.path === pagePath)?.name || pagePath.replace(/^\//, '') || 'root';

        const pageStartedAt = Date.now();
        const result = await navigateAndScreenshot(page, role, pagePath, pageName, i, capture);
        const pageEntry: {
          path: string;
          name: string;
          accessible: boolean;
          hasError: boolean;
          errorMessage?: string;
          clickedButtons?: number;
          durationMs?: number;
          clickStats?: {
            total: number;
            unique: number;
            clicked: number;
            failures: number;
            durationMs: number;
          };
        } = {
          path: pagePath,
          name: pageName,
          ...result,
        };
        pageEntry.durationMs = Date.now() - pageStartedAt;
        results.pages.push(pageEntry);

        // Write incremental progress so timeouts still leave useful artifacts
        try {
          fs.writeFileSync(path.join(roleDir, 'results.json'), JSON.stringify(results, null, 2));
        } catch {
          // ignore
        }
        
        if (result.accessible && !result.hasError) {
          const clickStats = await clickButtonsAndScreenshot(page, role, pagePath, pageName, capture);
          pageEntry.clickStats = clickStats;
          pageEntry.clickedButtons = clickStats.clicked;

          // Persist after click pass too
          try {
            fs.writeFileSync(path.join(roleDir, 'results.json'), JSON.stringify(results, null, 2));
          } catch {
            // ignore
          }
        }
      }

      // Sidebar correctness heuristic:
      // - Any sidebar link that leads to a restricted page should not be present.
      // - Any accessible audited page should be represented in the sidebar (best-effort).
      const sidebarHrefs = results.sidebarHrefs || [];
      // Only treat "restricted" as "redirected away / access denied" (accessible=false, hasError=false).
      // If a page errored or timed out, that's not a permissions signal.
      const restrictedPages = results.pages.filter((p) => !p.accessible && !p.hasError).map((p) => p.path);
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
      fs.writeFileSync(
        path.join(roleDir, 'results.json'),
        JSON.stringify(results, null, 2)
      );
      
      // Log summary
      const accessibleCount = results.pages.filter(p => p.accessible).length;
      const errorCount = results.pages.filter(p => p.hasError).length;
      console.log(`Role ${role}: ${accessibleCount}/${pagesToTest.length} pages accessible, ${errorCount} errors`);
      // Defer assertions to the final analysis pass.
    });
  }

  test('Analyze screenshots after all roles', async () => {
  // Must run after role screenshot capture. With --workers=1 and no role-level assertions,
  // this will execute after the capture loop and can do aggregated checks.
  const summaryPath = path.join(SCREENSHOT_DIR, 'audit-summary.json');
  const summary: Record<string, unknown> = {
    generatedAt: new Date().toISOString(),
    roles: {},
  };

  const failures: Array<{ role: string; reason: string }> = [];
  
  for (const role of ALL_ROLES) {
    const roleDir = path.join(SCREENSHOT_DIR, role);
    const resultsPath = path.join(roleDir, 'results.json');
    
    if (fs.existsSync(resultsPath)) {
      const results = JSON.parse(fs.readFileSync(resultsPath, 'utf-8'));
      summary.roles[role] = results;

      if (!results?.loginSuccess) {
        failures.push({ role, reason: 'login failed' });
        continue;
      }

      const pages: Array<{ hasError?: boolean; errorMessage?: string; accessible?: boolean }> = results?.pages || [];

      // Unexpected errors: allow explicit 401/403 (restricted) only.
      const unexpectedErrors = pages.filter(
        (p) => p.hasError && p.errorMessage && !String(p.errorMessage).includes('401') && !String(p.errorMessage).includes('403')
      );
      if (unexpectedErrors.length > 0) {
        failures.push({ role, reason: `${unexpectedErrors.length} unexpected page errors` });
      }

      // Sidebar should not contain links that truly behaved as "restricted" (redirect-to-login)
      const sidebarHrefs: string[] = results?.sidebarHrefs || [];
      const restrictedPages: string[] = (results?.pages || [])
        .filter((p: any) => p && p.accessible === false && p.hasError === false && typeof p.path === 'string')
        .map((p: any) => p.path);
      const sidebarHasRestricted = sidebarHrefs.filter((h) => restrictedPages.includes(h));
      if (sidebarHasRestricted.length > 0) {
        failures.push({ role, reason: `sidebar exposes restricted links: ${sidebarHasRestricted.join(', ')}` });
      }
    }
    else {
      failures.push({ role, reason: 'missing results.json' });
    }
  }
  
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));

  if (failures.length > 0) {
    console.log(`Audit summary saved to: ${summaryPath}`);
    for (const f of failures) {
      console.log(`❌ ${f.role}: ${f.reason}`);
    }
  }

  expect(failures, `One or more roles failed audit; see ${summaryPath}`).toEqual([]);
  });
});
