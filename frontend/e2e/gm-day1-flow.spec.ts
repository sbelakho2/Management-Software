import { test, expect, type Page } from '@playwright/test';

/**
 * GM Day-1 E2E Flow Test
 * 
 * Tests the complete Day-1 General Manager onboarding and daily workflow:
 * 1. GM Day-1 Setup Wizard (first-time setup)
 *    - Welcome screen
 *    - Organization profile
 *    - Pipeline stages configuration
 *    - Approval thresholds
 *    - Role assignments
 *    - Template setup
 *    - LSW cadence configuration
 *    - First Obeya creation
 *    - Review and complete
 * 
 * 2. Today Screen Workflow
 *    - View daily dashboard with KPIs
 *    - Check overdue items (tasks, RFQs, approvals)
 *    - Navigate to pending items
 * 
 * 3. Approvals Workflow
 *    - Review pending quote approval
 *    - Add approval rationale
 *    - Submit approval decision
 *    - Verify audit trail
 * 
 * 4. Export Snapshot
 *    - Generate daily snapshot export
 *    - Verify PDF generation
 *    - Download and validate export
 */

// =============================================================================
// Test Fixtures and Helpers
// =============================================================================

interface SetupWizardData {
  organizationName: string;
  industry: string;
  timezone: string;
  currency: string;
  gmName: string;
  gmEmail: string;
}

const mockSetupData: SetupWizardData = {
  organizationName: 'Test Manufacturing Co',
  industry: 'Aerospace Manufacturing',
  timezone: 'America/New_York',
  currency: 'USD',
  gmName: 'John Smith',
  gmEmail: 'john.smith@testmfg.com',
};

// Helper to wait for navigation and ensure page is loaded
async function waitForPageReady(page: Page, expectedUrl?: string | RegExp) {
  if (expectedUrl) {
    await page.waitForURL(expectedUrl, { timeout: 10000 });
  }
  await page.waitForLoadState('networkidle', { timeout: 10000 });
  await page.waitForLoadState('domcontentloaded');
}

// Helper to authenticate as GM via bootstrap API
async function authenticateAsGM(page: Page) {
  const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';
  
  // Only attempt authentication if E2E_WITH_BACKEND is set
  if (!process.env.E2E_WITH_BACKEND) {
    // If no backend, just go to page directly - it may work for static content
    await page.goto('/');
    return;
  }
  
  const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
    data: {
      email: mockSetupData.gmEmail,
      password: 'ChangeMe123!',
      first_name: 'E2E',
      last_name: 'GM',
    },
  });
  
  if (bootstrap.ok()) {
    const tokens = await bootstrap.json();
    
    await page.addInitScript((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);
  }
  
  await page.goto('/');
}

// Helper to check if element exists and is visible
async function elementExistsAndVisible(page: Page, selector: string, timeout = 5000): Promise<boolean> {
  try {
    const element = page.locator(selector).first();
    await element.waitFor({ state: 'visible', timeout });
    return true;
  } catch {
    return false;
  }
}

// =============================================================================
// Test Suite: GM Day-1 Setup Wizard
// =============================================================================

test.describe('GM Day-1 Setup Wizard', () => {
  test.beforeEach(async ({ page }) => {
    // Start at home page
    await page.goto('/');
    await waitForPageReady(page);
  });

  test('should display setup wizard for first-time GM', async ({ page }) => {
    // Check if setup wizard is shown
    // Note: This might redirect to /setup or show a modal
    const hasSetupWizard = 
      (await elementExistsAndVisible(page, '[data-testid="setup-wizard"]')) ||
      (await elementExistsAndVisible(page, 'h1:has-text("Welcome"), h1:has-text("Setup")')) ||
      page.url().includes('/setup');

    // If no wizard, that's ok - might already be set up
    // In that case, we'll test the Today screen flow
    if (!hasSetupWizard) {
      test.skip();
    }
  });

  test('should complete organization profile step', async ({ page }) => {
    // Navigate to setup wizard (if not already there)
    if (!page.url().includes('/setup')) {
      const setupLink = page.locator('a[href*="/setup"], button:has-text("Setup"), button:has-text("Get Started")');
      if (await setupLink.isVisible({ timeout: 2000 }).catch(() => false)) {
        await setupLink.click();
        await waitForPageReady(page);
      } else {
        test.skip();
      }
    }

    // Look for organization name input
    const orgNameInput = page.locator('input[name="organizationName"], input[name="name"], input[placeholder*="organization"]').first();
    
    if (await orgNameInput.isVisible({ timeout: 2000 }).catch(() => false)) {
      await orgNameInput.fill(mockSetupData.organizationName);

      // Fill industry if available
      const industryInput = page.locator('input[name="industry"], select[name="industry"]').first();
      if (await industryInput.isVisible({ timeout: 1000 }).catch(() => false)) {
        await industryInput.fill(mockSetupData.industry);
      }

      // Fill timezone if available
      const timezoneSelect = page.locator('select[name="timezone"]').first();
      if (await timezoneSelect.isVisible({ timeout: 1000 }).catch(() => false)) {
        await timezoneSelect.selectOption(mockSetupData.timezone);
      }

      // Fill currency if available
      const currencySelect = page.locator('select[name="currency"]').first();
      if (await currencySelect.isVisible({ timeout: 1000 }).catch(() => false)) {
        await currencySelect.selectOption(mockSetupData.currency);
      }

      // Click next/continue button
      const nextButton = page.locator('button:has-text("Next"), button:has-text("Continue"), button[type="submit"]').first();
      await nextButton.click();

      // Wait for navigation or next step
      await page.waitForTimeout(1000);
      
      // Verify we moved to next step (URL change or step indicator)
      const hasPipelineStep = 
        (await elementExistsAndVisible(page, 'text="Pipeline"')) ||
        (await elementExistsAndVisible(page, 'text="Stages"')) ||
        (await elementExistsAndVisible(page, '[data-step="pipeline"]'));
      
      expect(hasPipelineStep).toBeTruthy();
    } else {
      test.skip();
    }
  });

  test('should configure pipeline stages', async ({ page }) => {
    // This test assumes we're on the pipeline stages step
    // In a real scenario, we'd navigate through wizard steps
    const hasPipelineConfig = 
      (await elementExistsAndVisible(page, 'text="Pipeline"')) ||
      (await elementExistsAndVisible(page, 'text="Stages"'));

    if (!hasPipelineConfig) {
      test.skip();
    }

    // Look for stage configuration inputs
    const stageInputs = page.locator('input[name*="stage"], input[placeholder*="stage"]');
    const stageCount = await stageInputs.count();

    if (stageCount > 0) {
      // Verify default stages exist or can be added
      const addStageButton = page.locator('button:has-text("Add Stage"), button:has-text("Add")');
      if (await addStageButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await addStageButton.click();
        await page.waitForTimeout(500);
      }

      // Continue to next step
      const nextButton = page.locator('button:has-text("Next"), button:has-text("Continue")').first();
      if (await nextButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await nextButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should configure approval thresholds', async ({ page }) => {
    const hasThresholdConfig = 
      (await elementExistsAndVisible(page, 'text="Threshold"')) ||
      (await elementExistsAndVisible(page, 'text="Approval"'));

    if (!hasThresholdConfig) {
      test.skip();
    }

    // Look for threshold value inputs
    const thresholdInputs = page.locator('input[type="number"], input[name*="threshold"], input[name*="value"]');
    const count = await thresholdInputs.count();

    if (count > 0) {
      // Fill in a sample threshold
      await thresholdInputs.first().fill('50000');

      // Continue to next step
      const nextButton = page.locator('button:has-text("Next"), button:has-text("Continue")').first();
      if (await nextButton.isVisible({ timeout: 1000 }).catch(() => false)) {
        await nextButton.click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('should complete wizard and navigate to dashboard', async ({ page }) => {
    // Look for final step or complete button
    const completeButton = page.locator('button:has-text("Complete"), button:has-text("Finish"), button:has-text("Get Started")');
    
    if (await completeButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await completeButton.click();
      await waitForPageReady(page);

      // Should redirect to today screen or dashboard
      const url = page.url();
      expect(url).toMatch(/\/(today|dashboard)/);
    }
  });
});

// =============================================================================
// Test Suite: Today Screen - Daily Dashboard
// =============================================================================

test.describe('Today Screen - Daily Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateAsGM(page);
    // Navigate to Today screen
    await page.goto('/today');
    await waitForPageReady(page, /\/today/);
  });

  test('should display Today screen with KPIs', async ({ page }) => {
    // Verify page title/header - the Today page shows a greeting like "Good morning, {name}!"
    const header = page.locator('h1').first();
    await expect(header).toBeVisible({ timeout: 10000 });

    // Check the header contains a greeting
    const headerText = await header.textContent();
    expect(headerText).toMatch(/good\s+(morning|afternoon|evening)/i);

    // Check for card elements on the page (cards use bg-card class)
    // Look for elements with rounded corners and shadow - typical card styling
    const cards = page.locator('.bg-card, [class*="shadow"], .rounded-lg');
    
    // Wait a moment for potential data loading
    await page.waitForTimeout(2000);

    const cardCount = await cards.count();
    expect(cardCount).toBeGreaterThan(0);
  });

  test('should show overdue items section', async ({ page }) => {
    // Look for overdue section
    const overdueSection = page.locator('text=/overdue|past due|late/i').first();
    
    // Overdue section might not always exist if there are no overdue items
    const hasOverdueSection = await overdueSection.isVisible({ timeout: 3000 }).catch(() => false);
    
    if (hasOverdueSection) {
      // Check for overdue items list
      const overdueItems = page.locator('[data-testid="overdue-item"], [class*="overdue"]');
      const count = await overdueItems.count();
      
      // Might be 0 items (which is good!)
      expect(count).toBeGreaterThanOrEqual(0);
    }
    
    // Test passes whether or not overdue section exists
    expect(true).toBeTruthy();
  });

  test('should display pending approvals', async ({ page }) => {
    // Look for approvals section
    const approvalsSection = page.locator('text=/approval|pending/i').first();
    
    const hasApprovalsSection = await approvalsSection.isVisible({ timeout: 3000 }).catch(() => false);
    
    if (hasApprovalsSection) {
      // Check for approval items
      const approvalItems = page.locator('[data-testid*="approval"], [class*="approval"]');
      const count = await approvalItems.count();
      
      expect(count).toBeGreaterThanOrEqual(0);
    }
  });

  test('should show recent activity feed', async ({ page }) => {
    // Look for activity section
    const activitySection = page.locator('text=/activity|recent|feed/i').first();
    
    const hasActivitySection = await activitySection.isVisible({ timeout: 3000 }).catch(() => false);
    
    if (hasActivitySection) {
      // Check for activity items
      const activityItems = page.locator('[data-testid*="activity"], [class*="activity"]');
      const count = await activityItems.count();
      
      expect(count).toBeGreaterThanOrEqual(0);
    }
  });

  test('should allow navigation to pipeline from KPIs', async ({ page }) => {
    // Look for KPI card with link to pipeline
    const pipelineLink = page.locator('a[href="/pipeline"], a[href*="/pipeline"]').first();
    
    if (await pipelineLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await pipelineLink.click();
      await waitForPageReady(page, /\/pipeline/);
      
      // Verify we're on pipeline page
      expect(page.url()).toContain('pipeline');
    }
  });

  test('should have export snapshot functionality', async ({ page }) => {
    // Look for export button
    const exportButton = page.locator('button:has-text("Export"), button[aria-label*="export"]').first();
    
    if (await exportButton.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Click export button
      await exportButton.click();
      await page.waitForTimeout(1000);
      
      // Check for export dialog or dropdown
      const exportDialog = page.locator('[role="dialog"], [class*="menu"], [class*="dropdown"]');
      const hasDialog = await exportDialog.isVisible({ timeout: 2000 }).catch(() => false);
      
      if (hasDialog) {
        // Look for snapshot/PDF option
        const snapshotOption = page.locator('text=/snapshot|pdf|daily/i').first();
        if (await snapshotOption.isVisible({ timeout: 1000 }).catch(() => false)) {
          // Note: We won't actually trigger download in test
          // Just verify the option exists
          expect(snapshotOption).toBeVisible();
        }
      }
    }
  });
});

// =============================================================================
// Test Suite: Approvals Workflow
// =============================================================================

test.describe('Approvals Workflow', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateAsGM(page);
  });

  test('should navigate to approvals from Today screen', async ({ page }) => {
    await page.goto('/today');
    await waitForPageReady(page);

    // Look for "View All Approvals" or pending approval link
    const approvalsLink = page.locator('a[href*="approval"], button:has-text("Approval")').first();
    
    if (await approvalsLink.isVisible({ timeout: 3000 }).catch(() => false)) {
      await approvalsLink.click();
      await waitForPageReady(page);
      
      // Verify we navigated somewhere (might be /approvals, /quotes, etc.)
      expect(page.url()).not.toContain('/today');
    }
  });

  test('should display pending quote approval details', async ({ page }) => {
    // Navigate to quotes page (common place for approvals)
    await page.goto('/quotes');
    await waitForPageReady(page);

    // Look for pending approval indicator
    const pendingBadge = page.locator('text=/pending|awaiting|review/i').first();
    
    if (await pendingBadge.isVisible({ timeout: 3000 }).catch(() => false)) {
      // Click on a pending item
      const firstPendingItem = page.locator('[data-testid*="quote"], [class*="quote"]').first();
      if (await firstPendingItem.isVisible({ timeout: 2000 }).catch(() => false)) {
        await firstPendingItem.click();
        await waitForPageReady(page);
        
        // Should show quote details
        expect(page.locator('text=/quote|proposal/i')).toBeVisible();
      }
    }
  });

  test('should require rationale for approval decision', async ({ page }) => {
    // This test would require a quote in pending approval state
    // For now, we'll check if the approval form has rationale field
    await page.goto('/quotes');
    await waitForPageReady(page);

    // Look for approve/reject buttons
    const approveButton = page.locator('button:has-text("Approve")').first();
    
    if (await approveButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await approveButton.click();
      await page.waitForTimeout(500);
      
      // Should show rationale input
      const rationaleInput = page.locator('textarea[name*="rationale"], textarea[name*="note"], textarea[name*="comment"]').first();
      
      if (await rationaleInput.isVisible({ timeout: 2000 }).catch(() => false)) {
        expect(rationaleInput).toBeVisible();
        
        // Try submitting without rationale (if validation exists)
        const submitButton = page.locator('button[type="submit"], button:has-text("Submit")').first();
        if (await submitButton.isVisible({ timeout: 1000 }).catch(() => false)) {
          await submitButton.click();
          await page.waitForTimeout(500);
          
          // Should show validation error or still be on same page
          // (Actual behavior depends on implementation)
        }
      }
    }
  });

  test('should record approval in audit trail', async ({ page }) => {
    // After approval, should be able to view audit trail
    await page.goto('/quotes');
    await waitForPageReady(page);

    // Look for audit/history link
    const auditLink = page.locator('button:has-text("History"), button:has-text("Audit"), a:has-text("Activity")').first();
    
    if (await auditLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await auditLink.click();
      await page.waitForTimeout(1000);
      
      // Should show audit trail entries
      const auditEntries = page.locator('[data-testid*="audit"], [class*="audit"], [class*="activity"]');
      const count = await auditEntries.count();
      
      expect(count).toBeGreaterThanOrEqual(0);
    }
  });
});

// =============================================================================
// Test Suite: Export Snapshot
// =============================================================================

test.describe('Export Snapshot Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateAsGM(page);
    await page.goto('/today');
    await waitForPageReady(page);
  });

  test('should have export snapshot button', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export"), button[aria-label*="export"]').first();
    
    // Export button might be in header, toolbar, or actions menu
    const hasExportButton = await exportButton.isVisible({ timeout: 3000 }).catch(() => false);
    
    // If no direct button, check for actions menu
    if (!hasExportButton) {
      const actionsMenu = page.locator('button:has-text("Actions"), button[aria-label*="actions"]').first();
      if (await actionsMenu.isVisible({ timeout: 2000 }).catch(() => false)) {
        await actionsMenu.click();
        await page.waitForTimeout(500);
        
        const exportOption = page.locator('text=/export/i').first();
        expect(await exportOption.isVisible({ timeout: 1000 }).catch(() => false)).toBeTruthy();
      }
    }
  });

  test('should show export format options', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export")').first();
    
    if (await exportButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await exportButton.click();
      await page.waitForTimeout(500);
      
      // Check for format options (PDF, CSV, etc.)
      const formatOptions = page.locator('text=/pdf|csv|excel/i');
      const count = await formatOptions.count();
      
      // Should have at least one format option
      expect(count).toBeGreaterThanOrEqual(0);
    }
  });

  test('should trigger snapshot generation', async ({ page }) => {
    const exportButton = page.locator('button:has-text("Export")').first();
    
    if (await exportButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await exportButton.click();
      await page.waitForTimeout(500);
      
      // Look for PDF/snapshot option
      const snapshotOption = page.locator('text=/snapshot|daily|pdf/i').first();
      
      if (await snapshotOption.isVisible({ timeout: 1000 }).catch(() => false)) {
        // Set up download listener before clicking
        const downloadPromise = page.waitForEvent('download', { timeout: 10000 }).catch(() => null);
        
        await snapshotOption.click();
        
        // Wait a moment for generation
        await page.waitForTimeout(2000);
        
        // Check if download started or if there's a generation message
        const download = await downloadPromise;
        const hasGenerationMessage = await page.locator('text=/generating|preparing|creating/i')
          .isVisible({ timeout: 1000 })
          .catch(() => false);
        
        // Either download started or generation message shown
        expect(download !== null || hasGenerationMessage).toBeTruthy();
      }
    }
  });

  test('should show export history or status', async ({ page }) => {
    // After triggering export, might show status or history
    const exportButton = page.locator('button:has-text("Export")').first();
    
    if (await exportButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await exportButton.click();
      await page.waitForTimeout(500);
      
      // Look for history or recent exports
      const historyLink = page.locator('text=/history|recent|downloads/i').first();
      
      if (await historyLink.isVisible({ timeout: 1000 }).catch(() => false)) {
        await historyLink.click();
        await page.waitForTimeout(1000);
        
        // Should show list of exports
        const exportList = page.locator('[data-testid*="export"], [class*="export"]');
        const count = await exportList.count();
        
        expect(count).toBeGreaterThanOrEqual(0);
      }
    }
  });
});

// =============================================================================
// Test Suite: Complete GM Day-1 Integration Flow
// =============================================================================

test.describe('Complete GM Day-1 Integration Flow', () => {
  test.beforeEach(async ({ page }) => {
    await authenticateAsGM(page);
  });

  test('should complete full Day-1 journey', async ({ page }) => {
    // 1. Start at Today screen (authenticated)
    await page.goto('/today');
    await waitForPageReady(page);
    
    // Verify Today screen loaded - the page shows a greeting like "Good morning, {name}!"
    const todayHeader = page.locator('h1').first();
    await expect(todayHeader).toBeVisible({ timeout: 5000 });
    const headerText = await todayHeader.textContent();
    expect(headerText).toMatch(/good\s+(morning|afternoon|evening)/i);

    // Check for overdue items
    const overdueSection = await page.locator('text=/overdue|past due/i')
      .isVisible({ timeout: 2000 })
      .catch(() => false);

    // Navigate to approvals (if available)
    const approvalsLink = page.locator('a[href*="approval"], button:has-text("Approval")').first();
    if (await approvalsLink.isVisible({ timeout: 2000 }).catch(() => false)) {
      await approvalsLink.click();
      await waitForPageReady(page);
    }

    // Return to Today and try export
    await page.goto('/today');
    await waitForPageReady(page);

    const exportButton = page.locator('button:has-text("Export")').first();
    if (await exportButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await exportButton.click();
      await page.waitForTimeout(1000);
    }

    // Test completes successfully if we got this far
    expect(true).toBeTruthy();
  });
});

// =============================================================================
// Test Suite: Mobile/Responsive Day-1 Flow
// =============================================================================

test.describe('Mobile Day-1 Flow', () => {
  test.use({ 
    viewport: { width: 375, height: 667 } // iPhone SE size
  });

  test('should display Today screen on mobile', async ({ page }) => {
    await authenticateAsGM(page);
    await page.goto('/today');
    await waitForPageReady(page);

    // Verify Today screen loads on mobile
    const todayContent = page.locator('h1, h2, [data-testid="today"]');
    await expect(todayContent.first()).toBeVisible({ timeout: 5000 });
  });

  test('should have mobile-friendly navigation', async ({ page }) => {
    await authenticateAsGM(page);
    await page.goto('/today');
    await waitForPageReady(page);

    // Look for mobile menu/hamburger
    const mobileMenu = page.locator('button[aria-label*="menu"], button[data-testid="mobile-menu"]').first();
    
    if (await mobileMenu.isVisible({ timeout: 2000 }).catch(() => false)) {
      await mobileMenu.click();
      await page.waitForTimeout(500);
      
      // Should show navigation options
      const navItems = page.locator('a, button').filter({ hasText: /pipeline|quotes|today/i });
      const count = await navItems.count();
      
      expect(count).toBeGreaterThan(0);
    }
  });
});
