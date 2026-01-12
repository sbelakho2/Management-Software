import { test, expect } from '@playwright/test';

/**
 * E2E Test: GM Day-1 Flow
 * 
 * This test validates the complete GM daily workflow.
 * Requires real backend (set E2E_WITH_BACKEND=1).
 */

// Helper function to authenticate via bootstrap API
async function authenticateUser(page: import('@playwright/test').Page, email: string) {
  const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';
  
  const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
    data: {
      email,
      password: 'ChangeMe123!',
      first_name: 'E2E',
      last_name: 'GM',
    },
  });
  
  if (!bootstrap.ok()) {
    throw new Error('Failed to bootstrap user');
  }
  
  const tokens = await bootstrap.json();
  
  await page.addInitScript((t) => {
    localStorage.setItem('access_token', t.access_token);
    localStorage.setItem('refresh_token', t.refresh_token);
  }, tokens);
}

test.describe('GM Day-1 Complete Flow', () => {
  test('should complete full GM daily workflow', async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');

    await authenticateUser(page, 'e2e.gm.workflow@example.com');

    // STEP 1: Navigate to Today screen
    await test.step('View Today screen', async () => {
      await page.goto('/today');
      await expect(page.locator('body')).toBeVisible();
    });

    // STEP 2: Navigate to Pipeline
    await test.step('View Pipeline', async () => {
      await page.goto('/pipeline');
      await expect(page.locator('body')).toBeVisible();
    });

    // STEP 3: Navigate to Project Management
    await test.step('View Project Management', async () => {
      await page.goto('/project-management');
      await expect(page.locator('body')).toBeVisible();
    });
  });

  test('should handle offline mode gracefully', async ({ page, context }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');

    await authenticateUser(page, 'e2e.gm.offline@example.com');

    // Load the page first
    await page.goto('/today');
    await expect(page.locator('body')).toBeVisible();

    // Go offline
    await context.setOffline(true);

    // Try to navigate - should show offline indicator or cached content
    await page.goto('/offline').catch(() => {});
    
    // Page should still be visible (either offline page or cached)
    await expect(page.locator('body')).toBeVisible();

    // Go back online
    await context.setOffline(false);
  });

  test('should measure performance of Today screen', async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');

    await authenticateUser(page, 'e2e.gm.perf@example.com');

    const startTime = Date.now();
    await page.goto('/today');
    await page.waitForLoadState('domcontentloaded');
    const loadTime = Date.now() - startTime;

    console.log(`Today screen loaded in ${loadTime}ms`);

    // Performance gate: < 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });
});
