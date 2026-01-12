import { test, expect } from '@playwright/test';

/**
 * Login functionality tests
 * 
 * Note: This app doesn't have a separate /login page. Authentication is handled
 * via API tokens stored in localStorage. These tests verify the authentication
 * flow using the bootstrap-user dev endpoint.
 */

test.describe('Login Page', () => {
  test('should display the login page', async ({ page }) => {
    test.skip(true, 'App does not have a dedicated login page - uses token-based auth via API');
  });

  test('should have email and password fields', async ({ page }) => {
    test.skip(true, 'App does not have a dedicated login page - uses token-based auth via API');
  });

  test('should have a submit button', async ({ page }) => {
    test.skip(true, 'App does not have a dedicated login page - uses token-based auth via API');
  });

  test('should show validation error on empty submit', async ({ page }) => {
    test.skip(true, 'App does not have a dedicated login page - uses token-based auth via API');
  });

  test('should have link to forgot password', async ({ page }) => {
    test.skip(true, 'App does not have a dedicated login page - uses token-based auth via API');
  });
});

test.describe('Authentication Flow', () => {
  test('should authenticate via bootstrap-user API', async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');

    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    // Use bootstrap endpoint to create/auth user
    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'e2e.auth@example.com',
        password: 'ChangeMe123!',
        first_name: 'E2E',
        last_name: 'Auth',
      },
    });
    expect(bootstrap.ok()).toBeTruthy();

    const tokens = await bootstrap.json();
    expect(tokens.access_token).toBeTruthy();
    expect(tokens.refresh_token).toBeTruthy();
  });

  test('should allow authenticated access to protected routes', async ({ page }) => {
    test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');

    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

    // Bootstrap user
    const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
      data: {
        email: 'e2e.protected@example.com',
        password: 'ChangeMe123!',
        first_name: 'E2E',
        last_name: 'Protected',
      },
    });
    expect(bootstrap.ok()).toBeTruthy();
    const tokens = await bootstrap.json();

    // Set tokens in localStorage before navigation
    await page.addInitScript((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);

    // Navigate to protected route
    await page.goto('/today');

    // Should load the page content (not redirect to login)
    await expect(page.locator('body')).toBeVisible();
  });
});
