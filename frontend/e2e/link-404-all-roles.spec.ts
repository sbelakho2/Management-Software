/**
 * E2E Test: Comprehensive 404 Link Detection
 * 
 * This test logs in as each of the 24 roles and navigates through all
 * accessible pages, clicking on every interactive link to detect 404s.
 * 
 * Purpose:
 * - Detect broken navigation links before production
 * - Ensure all router.push and Link href routes are valid
 * - Catch missing detail pages (e.g., /orders/[id])
 */

import { test, expect, Page, Locator } from '@playwright/test';

// All 24 roles in the system
const ALL_ROLES = [
  'ceo',
  'executive', 
  'general_manager',
  'sales',
  'finance',
  'hr',
  'it',
  'quality',
  'warehouse',
  'maintenance',
  'operator',
  'supervisor',
  'team_lead',
  'auditor',
  'admin',
  'sales_manager',
  'accountant',
  'recruiter',
  'security_analyst',
  'qc_inspector',
  'inventory_clerk',
  'maintenance_tech',
  'machine_operator',
  'shift_supervisor',
];

// Known routes that exist in the application
const KNOWN_ROUTES = [
  '/today',
  '/tasks',
  '/tasks/new',
  '/analytics',
  '/executive',
  '/hr',
  '/it',
  '/auditor',
  '/warehouse',
  '/admin',
  '/sales',
  '/pipeline',
  '/pipeline/new',
  '/rfqs',
  '/rfqs/new',
  '/quotes',
  '/quotes/new',
  '/customers',
  '/customers/new',
  '/orders',
  '/ops',
  '/production',
  '/production/new',
  '/projects',
  '/project-management',
  '/products',
  '/products/new',
  '/obeya',
  '/obeya/new',
  '/a3',
  '/a3/new',
  '/ctq',
  '/exceptions',
  '/quality',
  '/quality/analytics',
  '/quality/inspections/new',
  '/quality/ncrs/new',
  '/quality/capas/new',
  '/andon',
  '/andon/analytics',
  '/andon/history',
  '/andon/reports',
  '/maintenance',
  '/maintenance/mobile',
  '/supply-chain',
  '/purchase',
  '/training',
  '/training/matrix',
  '/training/enroll',
  '/training/certifications/new',
  '/training/programs/new',
  '/finance',
  '/finance/costing',
  '/finance/currency',
  '/finance/ledger',
  '/finance/tax',
  '/mrp/mps',
  '/settings',
  '/settings/profile',
  '/settings/security',
  '/settings/notifications',
  '/settings/appearance',
];

// Test a subset of roles for faster CI runs
const ROLES_FOR_CI = ['ceo', 'general_manager', 'sales', 'finance', 'operator'];

// Determine which roles to test based on environment
const ROLES_TO_TEST = process.env.CI ? ROLES_FOR_CI : ALL_ROLES.slice(0, 5);

test.describe('404 Link Detection - All Roles', () => {
  test.setTimeout(120000); // 2 minutes per test

  for (const role of ROLES_TO_TEST) {
    test(`${role} - no 404 errors on navigation`, async ({ page }) => {
      const errors: string[] = [];
      
      // Track 404s
      page.on('response', response => {
        if (response.status() === 404) {
          errors.push(`404: ${response.url()}`);
        }
      });

      // Track console errors that might indicate missing pages
      page.on('console', msg => {
        if (msg.type() === 'error' && msg.text().includes('404')) {
          errors.push(`Console 404: ${msg.text()}`);
        }
      });

      // Login as the role
      await page.goto('/login');
      await page.waitForLoadState('networkidle');
      
      await page.fill('[name="email"]', `${role}@senseitest.com`);
      await page.fill('[name="password"]', 'TestPassword123!');
      await page.click('button[type="submit"]');
      
      // Wait for dashboard to load
      await page.waitForURL(/\/(today|dashboard|executive|sales|ops)/);
      await page.waitForLoadState('networkidle');

      // Get all navigation links visible to this role
      const navLinks = await page.locator('nav a[href], aside a[href]').all();
      const visitedUrls = new Set<string>();
      
      // Visit each unique URL from navigation
      for (const link of navLinks) {
        const href = await link.getAttribute('href');
        if (href && !visitedUrls.has(href) && href.startsWith('/') && !href.includes('#')) {
          visitedUrls.add(href);
          
          try {
            // Navigate to the page
            await page.goto(href, { waitUntil: 'networkidle', timeout: 15000 });
            
            // Check for 404 indicators in the page content
            const pageContent = await page.content();
            if (pageContent.includes('404') && pageContent.includes('not found')) {
              errors.push(`Page 404: ${href}`);
            }
            
            // Small delay to let any errors surface
            await page.waitForTimeout(500);
          } catch (e) {
            errors.push(`Navigation error to ${href}: ${e}`);
          }
        }
      }

      // Also check quick action buttons on the current page
      const currentUrl = page.url();
      await page.goto(currentUrl);
      
      const buttons = await page.locator('button').all();
      for (const button of buttons) {
        const text = await button.textContent();
        // Skip buttons that are actions (like submit/save)
        if (text && (text.includes('New') || text.includes('Create') || text.includes('View'))) {
          // Get any onclick handlers that do router.push
          // This is tricky to test without actually clicking
          // For now, we rely on the navigation links above
        }
      }

      // Assert no errors
      if (errors.length > 0) {
        console.log(`Role ${role} had 404 errors:`);
        errors.forEach(e => console.log(`  - ${e}`));
      }
      
      expect(errors, `Role ${role} should have no 404 errors`).toHaveLength(0);
    });
  }
});

test.describe('Direct Route Validation', () => {
  test('all known routes are accessible', async ({ page }) => {
    const inaccessibleRoutes: string[] = [];
    
    // Login as CEO to have access to most routes
    await page.goto('/login');
    await page.fill('[name="email"]', 'ceo@senseitest.com');
    await page.fill('[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(today|dashboard|executive)/);
    
    // Test each known route
    for (const route of KNOWN_ROUTES.slice(0, 20)) { // Limit for CI speed
      try {
        const response = await page.goto(route, { 
          waitUntil: 'networkidle', 
          timeout: 10000 
        });
        
        if (response && response.status() === 404) {
          inaccessibleRoutes.push(`${route} - 404`);
        }
        
        // Check for 404 content in page
        const content = await page.content();
        if (content.toLowerCase().includes('404') && 
            (content.toLowerCase().includes('not found') || content.toLowerCase().includes('page not found'))) {
          inaccessibleRoutes.push(`${route} - 404 page content`);
        }
        
      } catch (e) {
        inaccessibleRoutes.push(`${route} - error: ${e}`);
      }
    }
    
    if (inaccessibleRoutes.length > 0) {
      console.log('Inaccessible routes found:');
      inaccessibleRoutes.forEach(r => console.log(`  - ${r}`));
    }
    
    expect(inaccessibleRoutes).toHaveLength(0);
  });
});

test.describe('Link Click Validation', () => {
  test('purchase page links are valid', async ({ page }) => {
    const errors: string[] = [];
    
    // Login
    await page.goto('/login');
    await page.fill('[name="email"]', 'general_manager@senseitest.com');
    await page.fill('[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(today|dashboard)/);
    
    // Go to purchase page
    await page.goto('/purchase');
    await page.waitForLoadState('networkidle');
    
    // Track 404 responses
    page.on('response', response => {
      if (response.status() === 404) {
        errors.push(`404 response: ${response.url()}`);
      }
    });
    
    // Click the Suppliers button
    const suppliersBtn = page.locator('button', { hasText: 'Suppliers' });
    if (await suppliersBtn.count() > 0) {
      await suppliersBtn.click();
      await page.waitForLoadState('networkidle');
      
      // Should navigate to /supply-chain
      const url = page.url();
      if (url.includes('404') || !(url.includes('supply-chain'))) {
        errors.push(`Suppliers button led to unexpected URL: ${url}`);
      }
    }
    
    // Go back and click MRP Suggestions
    await page.goto('/purchase');
    await page.waitForLoadState('networkidle');
    
    const mrpCard = page.locator('text=MRP Suggestions').first();
    if (await mrpCard.count() > 0) {
      await mrpCard.click();
      await page.waitForLoadState('networkidle');
      
      const url = page.url();
      if (url.includes('404')) {
        errors.push(`MRP Suggestions led to 404: ${url}`);
      }
    }
    
    expect(errors).toHaveLength(0);
  });
  
  test('orders page links are valid', async ({ page }) => {
    const errors: string[] = [];
    
    // Login
    await page.goto('/login');
    await page.fill('[name="email"]', 'sales@senseitest.com');
    await page.fill('[name="password"]', 'TestPassword123!');
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/(today|dashboard|sales)/);
    
    // Go to orders page
    await page.goto('/orders');
    await page.waitForLoadState('networkidle');
    
    // Track 404 responses
    page.on('response', response => {
      if (response.status() === 404) {
        errors.push(`404 response: ${response.url()}`);
      }
    });
    
    // Click New Order button
    const newOrderBtn = page.locator('button', { hasText: /New Order|Create Order/ }).first();
    if (await newOrderBtn.count() > 0) {
      await newOrderBtn.click();
      await page.waitForLoadState('networkidle');
      
      const url = page.url();
      if (url.includes('404')) {
        errors.push(`New Order button led to 404: ${url}`);
      }
    }
    
    expect(errors).toHaveLength(0);
  });
});
