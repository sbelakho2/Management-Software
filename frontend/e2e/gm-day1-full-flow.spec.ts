import { test, expect } from '@playwright/test';

/**
 * E2E Test: GM Day-1 Flow
 * 
 * This test validates the complete GM daily workflow:
 * 1. Login as GM
 * 2. View Today screen
 * 3. Review overdue items
 * 4. Process approvals
 * 5. Export daily snapshot
 * 
 * Success criteria:
 * - All screens load under 3 seconds
 * - All data is displayed correctly
 * - Approvals are processed successfully
 * - Export generates successfully
 */

test.describe('GM Day-1 Complete Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to application
    await page.goto('/');
  });

  test('should complete full GM daily workflow', async ({ page }) => {
    // STEP 1: Login as GM
    await test.step('Login as GM user', async () => {
      await page.fill('[data-testid="email-input"]', 'gm@sensei.test');
      await page.fill('[data-testid="password-input"]', 'Test123!@#');
      await page.click('[data-testid="login-button"]');
      
      // Wait for successful login
      await expect(page).toHaveURL('/dashboard', { timeout: 5000 });
      
      // Verify GM role is displayed
      await expect(page.locator('[data-testid="user-role"]')).toContainText('GM');
    });

    // STEP 2: Navigate to Today screen
    await test.step('View Today screen', async () => {
      // Click on Today navigation
      await page.click('[data-testid="nav-today"]');
      await expect(page).toHaveURL('/today');
      
      // Wait for page to load (performance gate: < 3 seconds)
      const startTime = Date.now();
      await page.waitForSelector('[data-testid="today-screen-loaded"]', { timeout: 5000 });
      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(3000);
      
      // Verify Today screen components are visible
      await expect(page.locator('[data-testid="greeting-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="top-priorities"]')).toBeVisible();
      await expect(page.locator('[data-testid="risks-section"]')).toBeVisible();
      await expect(page.locator('[data-testid="commitments-section"]')).toBeVisible();
    });

    // STEP 3: Review overdue items
    await test.step('Review overdue items', async () => {
      // Check for overdue commitments
      const overdueSection = page.locator('[data-testid="overdue-commitments"]');
      const overdueCount = await overdueSection.locator('[data-testid="commitment-card"]').count();
      
      console.log(`Found ${overdueCount} overdue commitments`);
      
      if (overdueCount > 0) {
        // Click on first overdue item to view details
        await overdueSection.locator('[data-testid="commitment-card"]').first().click();
        
        // Verify detail modal/drawer opens
        await expect(page.locator('[data-testid="commitment-detail"]')).toBeVisible();
        
        // Close detail view
        await page.click('[data-testid="close-detail"]');
      }
    });

    // STEP 4: Process approvals
    await test.step('Process pending approvals', async () => {
      // Navigate to approvals section
      await page.click('[data-testid="nav-approvals"]');
      await expect(page).toHaveURL(/.*approvals.*/);
      
      // Wait for approvals to load
      await page.waitForSelector('[data-testid="approvals-list"]', { timeout: 5000 });
      
      // Check for pending approvals
      const pendingApprovals = page.locator('[data-testid="approval-card"]');
      const approvalCount = await pendingApprovals.count();
      
      console.log(`Found ${approvalCount} pending approvals`);
      
      if (approvalCount > 0) {
        // Click on first approval
        await pendingApprovals.first().click();
        
        // Verify approval detail view
        await expect(page.locator('[data-testid="approval-detail"]')).toBeVisible();
        
        // Check if approval button is visible
        const approveButton = page.locator('[data-testid="approve-button"]');
        if (await approveButton.isVisible()) {
          // Add rationale (required for GM approvals)
          await page.fill('[data-testid="approval-rationale"]', 'Approved after review - all criteria met');
          
          // Click approve
          await approveButton.click();
          
          // Wait for success message
          await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
          
          // Verify approval is processed
          await expect(page.locator('[data-testid="approval-status"]')).toContainText('Approved');
        }
      }
    });

    // STEP 5: Export daily snapshot
    await test.step('Export daily snapshot', async () => {
      // Navigate back to Today screen
      await page.click('[data-testid="nav-today"]');
      await page.waitForSelector('[data-testid="today-screen-loaded"]');
      
      // Click export button
      await page.click('[data-testid="export-snapshot-button"]');
      
      // Verify export dialog opens
      await expect(page.locator('[data-testid="export-dialog"]')).toBeVisible();
      
      // Select format (PDF)
      await page.click('[data-testid="export-format-pdf"]');
      
      // Confirm export
      const [download] = await Promise.all([
        page.waitForEvent('download'),
        page.click('[data-testid="confirm-export-button"]'),
      ]);
      
      // Verify download started
      expect(download).toBeTruthy();
      const filename = download.suggestedFilename();
      expect(filename).toMatch(/today_snapshot_.*\.pdf/);
      
      // Verify success message
      await expect(page.locator('[data-testid="export-success-message"]')).toBeVisible();
    });

    // STEP 6: Verify LSW checklist interaction
    await test.step('Interact with LSW checklist', async () => {
      // Scroll to LSW section
      await page.locator('[data-testid="lsw-checklist"]').scrollIntoViewIfNeeded();
      
      // Verify LSW items are visible
      await expect(page.locator('[data-testid="lsw-item"]').first()).toBeVisible();
      
      // Check first item if unchecked
      const firstCheckbox = page.locator('[data-testid="lsw-checkbox"]').first();
      const isChecked = await firstCheckbox.isChecked();
      
      if (!isChecked) {
        await firstCheckbox.check();
        
        // Verify check is persisted
        await expect(firstCheckbox).toBeChecked();
      }
    });

    // STEP 7: Review quick metrics
    await test.step('Review quick metrics', async () => {
      // Verify metrics section is visible
      await expect(page.locator('[data-testid="quick-metrics"]')).toBeVisible();
      
      // Check for key metrics
      await expect(page.locator('[data-testid="metric-open-rfqs"]')).toBeVisible();
      await expect(page.locator('[data-testid="metric-pending-quotes"]')).toBeVisible();
      await expect(page.locator('[data-testid="metric-overdue-tasks"]')).toBeVisible();
      
      // Verify metrics have numerical values
      const rfqCount = await page.locator('[data-testid="metric-open-rfqs-value"]').textContent();
      expect(rfqCount).toMatch(/\d+/);
    });

    // STEP 8: Logout
    await test.step('Logout successfully', async () => {
      // Click user menu
      await page.click('[data-testid="user-menu-button"]');
      
      // Click logout
      await page.click('[data-testid="logout-button"]');
      
      // Verify redirected to login
      await expect(page).toHaveURL('/', { timeout: 5000 });
      
      // Verify login form is visible
      await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
    });
  });

  test('should handle offline mode gracefully', async ({ page, context }) => {
    // Login first
    await page.fill('[data-testid="email-input"]', 'gm@sensei.test');
    await page.fill('[data-testid="password-input"]', 'Test123!@#');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');

    // Navigate to Today screen
    await page.click('[data-testid="nav-today"]');
    await page.waitForSelector('[data-testid="today-screen-loaded"]');

    // Simulate offline mode
    await context.setOffline(true);

    // Verify offline indicator appears
    await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible({ timeout: 5000 });

    // Verify cached data is still visible
    await expect(page.locator('[data-testid="greeting-message"]')).toBeVisible();

    // Try to perform action (should queue)
    const checkbox = page.locator('[data-testid="lsw-checkbox"]').first();
    if (!(await checkbox.isChecked())) {
      await checkbox.check();
      
      // Verify sync pending indicator
      await expect(page.locator('[data-testid="sync-pending"]')).toBeVisible();
    }

    // Go back online
    await context.setOffline(false);

    // Wait for sync to complete
    await expect(page.locator('[data-testid="sync-success"]')).toBeVisible({ timeout: 10000 });
  });

  test('should measure performance of Today screen', async ({ page }) => {
    // Login
    await page.fill('[data-testid="email-input"]', 'gm@sensei.test');
    await page.fill('[data-testid="password-input"]', 'Test123!@#');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');

    // Measure Today screen load time
    const startTime = Date.now();
    await page.click('[data-testid="nav-today"]');
    await page.waitForSelector('[data-testid="today-screen-loaded"]');
    const loadTime = Date.now() - startTime;

    console.log(`Today screen loaded in ${loadTime}ms`);

    // Performance gate: < 3 seconds
    expect(loadTime).toBeLessThan(3000);

    // Measure search performance
    const searchStart = Date.now();
    await page.fill('[data-testid="search-input"]', 'quote');
    await page.waitForSelector('[data-testid="search-results"]', { timeout: 2000 });
    const searchTime = Date.now() - searchStart;

    console.log(`Search completed in ${searchTime}ms`);

    // Performance gate: < 500ms
    expect(searchTime).toBeLessThan(500);
  });
});
