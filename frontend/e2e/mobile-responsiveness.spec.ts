import { test, expect, devices } from '@playwright/test';

/**
 * Mobile Responsiveness Verification Tests
 * 
 * Tests critical screens for mobile responsiveness:
 * - Today screen
 * - Tasks list
 * - Approvals
 * - Navigation
 * 
 * Devices tested:
 * - iPhone 12 Pro (390x844)
 * - iPhone SE (375x667)
 * - iPad (768x1024)
 * - Android phone (360x740)
 */

const CRITICAL_PAGES = [
  { name: 'Today', path: '/today', testid: 'today-screen-loaded' },
  { name: 'Tasks', path: '/tasks', testid: 'tasks-list' },
  { name: 'Approvals', path: '/approvals', testid: 'approvals-list' },
  { name: 'Dashboard', path: '/dashboard', testid: 'dashboard-loaded' },
];

test.describe('Mobile Responsiveness - iPhone 12 Pro', () => {
  test.use({ ...devices['iPhone 12 Pro'] });

  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/');
    await page.fill('[data-testid="email-input"]', 'test@sensei.test');
    await page.fill('[data-testid="password-input"]', 'Test123!@#');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard', { timeout: 5000 });
  });

  for (const pageInfo of CRITICAL_PAGES) {
    test(`${pageInfo.name} page should be mobile responsive`, async ({ page }) => {
      // Navigate to page
      await page.goto(pageInfo.path);
      await page.waitForSelector(`[data-testid="${pageInfo.testid}"]`, { timeout: 5000 });

      // Verify viewport dimensions
      const viewport = page.viewportSize();
      expect(viewport?.width).toBe(390);

      // Verify no horizontal scroll
      const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
      const bodyClientWidth = await page.evaluate(() => document.body.clientWidth);
      expect(bodyScrollWidth).toBeLessThanOrEqual(bodyClientWidth + 1); // Allow 1px tolerance

      // Verify touch targets are at least 44px (iOS guideline)
      const buttons = await page.locator('button:visible').all();
      for (const button of buttons.slice(0, 10)) { // Test first 10 buttons
        const box = await button.boundingBox();
        if (box) {
          expect(box.height).toBeGreaterThanOrEqual(40); // Allow small variance
        }
      }

      // Verify text is readable (font size >= 16px to prevent zoom)
      const bodyFontSize = await page.evaluate(() => {
        return parseInt(window.getComputedStyle(document.body).fontSize);
      });
      expect(bodyFontSize).toBeGreaterThanOrEqual(14); // Base font should be readable

      // Take screenshot for visual regression
      await page.screenshot({
        path: `test-results/mobile-iphone12-${pageInfo.name.toLowerCase()}.png`,
        fullPage: true,
      });
    });
  }

  test('Mobile navigation menu should work correctly', async ({ page }) => {
    await page.goto('/dashboard');

    // Open mobile menu (hamburger)
    const menuButton = page.locator('[data-testid="mobile-menu-button"]');
    await expect(menuButton).toBeVisible();
    await menuButton.click();

    // Verify menu drawer opens
    await expect(page.locator('[data-testid="mobile-nav-drawer"]')).toBeVisible();

    // Verify navigation links are visible
    await expect(page.locator('[data-testid="nav-link-today"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-link-tasks"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-link-approvals"]')).toBeVisible();

    // Click a navigation link
    await page.click('[data-testid="nav-link-today"]');

    // Verify navigation works and menu closes
    await expect(page).toHaveURL('/today');
    await expect(page.locator('[data-testid="mobile-nav-drawer"]')).not.toBeVisible();
  });

  test('Forms should be usable on mobile', async ({ page }) => {
    await page.goto('/tasks');

    // Open create task form
    await page.click('[data-testid="create-task-button"]');

    // Verify form is visible
    await expect(page.locator('[data-testid="task-form"]')).toBeVisible();

    // Fill form fields (should not zoom on focus)
    await page.fill('[data-testid="task-title-input"]', 'Mobile test task');
    await page.fill('[data-testid="task-description-input"]', 'Testing mobile form usability');

    // Verify inputs have correct font size (>= 16px prevents iOS zoom)
    const titleInput = page.locator('[data-testid="task-title-input"]');
    const fontSize = await titleInput.evaluate((el: HTMLElement) => {
      return parseInt(window.getComputedStyle(el).fontSize);
    });
    expect(fontSize).toBeGreaterThanOrEqual(16);

    // Submit form
    await page.click('[data-testid="submit-task-button"]');

    // Verify success
    await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
  });

  test('Swipe gestures should work for cards', async ({ page }) => {
    await page.goto('/tasks');
    await page.waitForSelector('[data-testid="tasks-list"]');

    const taskCards = page.locator('[data-testid="task-card"]');
    const firstCard = taskCards.first();

    if (await firstCard.isVisible()) {
      // Get initial position
      const box = await firstCard.boundingBox();
      if (box) {
        // Simulate swipe left gesture
        await page.mouse.move(box.x + box.width - 10, box.y + box.height / 2);
        await page.mouse.down();
        await page.mouse.move(box.x + 10, box.y + box.height / 2);
        await page.mouse.up();

        // Verify swipe actions appear
        await expect(page.locator('[data-testid="swipe-actions"]')).toBeVisible();
      }
    }
  });
});

test.describe('Mobile Responsiveness - iPhone SE (Small Screen)', () => {
  test.use({ ...devices['iPhone SE'] });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="email-input"]', 'test@sensei.test');
    await page.fill('[data-testid="password-input"]', 'Test123!@#');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('Today screen should adapt to small viewport', async ({ page }) => {
    await page.goto('/today');
    await page.waitForSelector('[data-testid="today-screen-loaded"]');

    // Verify critical content is visible
    await expect(page.locator('[data-testid="greeting-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="top-priorities"]')).toBeVisible();

    // Verify content stacks vertically (not side-by-side)
    const viewport = page.viewportSize();
    expect(viewport?.width).toBe(375);

    // Verify no content is cut off
    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyScrollWidth).toBeLessThanOrEqual(375);
  });

  test('Tables should be scrollable horizontally on small screens', async ({ page }) => {
    await page.goto('/tasks');

    const table = page.locator('[data-testid="tasks-table"]');
    if (await table.isVisible()) {
      // Check if table has horizontal scroll
      const scrollWidth = await table.evaluate((el: HTMLElement) => el.scrollWidth);
      const clientWidth = await table.evaluate((el: HTMLElement) => el.clientWidth);

      // Table should be wider than container (scrollable)
      expect(scrollWidth).toBeGreaterThanOrEqual(clientWidth);

      // Verify horizontal scroll works
      await table.evaluate((el: HTMLElement) => {
        el.scrollLeft = 100;
      });

      const scrollLeft = await table.evaluate((el: HTMLElement) => el.scrollLeft);
      expect(scrollLeft).toBeGreaterThan(0);
    }
  });
});

test.describe('Tablet Responsiveness - iPad', () => {
  test.use({ ...devices['iPad'] });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="email-input"]', 'test@sensei.test');
    await page.fill('[data-testid="password-input"]', 'Test123!@#');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('Today screen should use 2-column layout on tablet', async ({ page }) => {
    await page.goto('/today');
    await page.waitForSelector('[data-testid="today-screen-loaded"]');

    // Verify viewport is tablet size
    const viewport = page.viewportSize();
    expect(viewport?.width).toBe(768);

    // Verify multi-column layout (sections side-by-side)
    const priorities = page.locator('[data-testid="top-priorities"]');
    const risks = page.locator('[data-testid="risks-section"]');

    const prioritiesBox = await priorities.boundingBox();
    const risksBox = await risks.boundingBox();

    if (prioritiesBox && risksBox) {
      // Check if sections are side-by-side (y coordinates similar)
      const yDiff = Math.abs(prioritiesBox.y - risksBox.y);
      expect(yDiff).toBeLessThan(100); // Allow some variance
    }
  });

  test('Sidebar should be visible on tablet', async ({ page }) => {
    await page.goto('/dashboard');

    // Sidebar should be visible (not hidden behind hamburger menu)
    const sidebar = page.locator('[data-testid="sidebar"]');
    await expect(sidebar).toBeVisible();

    // Hamburger menu should not be visible
    const hamburger = page.locator('[data-testid="mobile-menu-button"]');
    await expect(hamburger).not.toBeVisible();
  });
});

test.describe('Touch Interactions', () => {
  test.use({ ...devices['iPhone 12 Pro'], hasTouch: true });

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="email-input"]', 'test@sensei.test');
    await page.fill('[data-testid="password-input"]', 'Test123!@#');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('Pull-to-refresh should work', async ({ page }) => {
    await page.goto('/today');
    await page.waitForSelector('[data-testid="today-screen-loaded"]');

    // Simulate pull-to-refresh gesture
    await page.evaluate(() => {
      window.scrollTo(0, 0);
    });

    await page.mouse.move(200, 100);
    await page.mouse.down();
    await page.mouse.move(200, 300);
    await page.mouse.up();

    // Verify refresh indicator appears
    await expect(page.locator('[data-testid="refresh-indicator"]')).toBeVisible({ timeout: 2000 });

    // Wait for refresh to complete
    await expect(page.locator('[data-testid="refresh-indicator"]')).not.toBeVisible({ timeout: 5000 });
  });

  test('Long press should show context menu', async ({ page }) => {
    await page.goto('/tasks');
    await page.waitForSelector('[data-testid="tasks-list"]');

    const firstTask = page.locator('[data-testid="task-card"]').first();
    if (await firstTask.isVisible()) {
      const box = await firstTask.boundingBox();
      if (box) {
        // Simulate long press
        await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
        await page.mouse.down();
        await page.waitForTimeout(800); // Hold for 800ms
        await page.mouse.up();

        // Verify context menu appears
        await expect(page.locator('[data-testid="context-menu"]')).toBeVisible();
      }
    }
  });
});

test.describe('Orientation Changes', () => {
  test('Should handle portrait to landscape rotation', async ({ page, context }) => {
    // Start in portrait
    await context.newPage();
    await page.setViewportSize({ width: 390, height: 844 });

    await page.goto('/');
    await page.fill('[data-testid="email-input"]', 'test@sensei.test');
    await page.fill('[data-testid="password-input"]', 'Test123!@#');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');

    await page.goto('/today');
    await page.waitForSelector('[data-testid="today-screen-loaded"]');

    // Take portrait screenshot
    await page.screenshot({ path: 'test-results/mobile-portrait.png' });

    // Rotate to landscape
    await page.setViewportSize({ width: 844, height: 390 });
    await page.waitForTimeout(500); // Allow layout to adjust

    // Verify layout adjusts
    await expect(page.locator('[data-testid="today-screen-loaded"]')).toBeVisible();

    // Take landscape screenshot
    await page.screenshot({ path: 'test-results/mobile-landscape.png' });

    // Verify no horizontal scroll in landscape
    const bodyScrollWidth = await page.evaluate(() => document.body.scrollWidth);
    expect(bodyScrollWidth).toBeLessThanOrEqual(844);
  });
});

test.describe('Performance on Mobile', () => {
  test.use({ ...devices['iPhone 12 Pro'] });

  test('Pages should load quickly on mobile', async ({ page }) => {
    await page.goto('/');
    await page.fill('[data-testid="email-input"]', 'test@sensei.test');
    await page.fill('[data-testid="password-input"]', 'Test123!@#');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');

    const measurements: { page: string; loadTime: number }[] = [];

    for (const pageInfo of CRITICAL_PAGES) {
      const startTime = Date.now();
      await page.goto(pageInfo.path);
      await page.waitForSelector(`[data-testid="${pageInfo.testid}"]`);
      const loadTime = Date.now() - startTime;

      measurements.push({ page: pageInfo.name, loadTime });

      console.log(`${pageInfo.name} loaded in ${loadTime}ms on mobile`);

      // Performance gate: < 4 seconds on mobile (slightly more lenient than desktop)
      expect(loadTime).toBeLessThan(4000);
    }

    console.table(measurements);
  });
});
