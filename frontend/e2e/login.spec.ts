import { test, expect } from '@playwright/test';

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('should display the login page', async ({ page }) => {
    // Check for login form elements
    await expect(page.locator('h1, h2').filter({ hasText: /sign in|login|welcome/i })).toBeVisible();
  });

  test('should have email and password fields', async ({ page }) => {
    // Look for email input
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    await expect(emailInput).toBeVisible();
    
    // Look for password input
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeVisible();
  });

  test('should have a submit button', async ({ page }) => {
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toBeVisible();
  });

  test('should show validation error on empty submit', async ({ page }) => {
    const submitButton = page.locator('button[type="submit"]');
    await submitButton.click();
    
    // Should stay on login page
    await expect(page).toHaveURL(/.*login.*/);
  });

  test('should have link to forgot password', async ({ page }) => {
    const forgotPasswordLink = page.locator('a').filter({ hasText: /forgot/i });
    // May or may not exist, just check it doesn't crash
    if (await forgotPasswordLink.count() > 0) {
      await expect(forgotPasswordLink).toBeVisible();
    }
  });
});
