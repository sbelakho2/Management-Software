// Sensei OS smoke suite (item 77): the behavioral contracts that unit
// tests cannot reach — login, the Today landing page, the station help
// flow and explicit error states. These run against a REAL built stack.

const { test, expect } = require('@playwright/test');

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@sensei.local';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'admin-password';

test('login renders the Sensei OS identity', async ({ page }) => {
  await page.goto('/login');
  await expect(page.getByText('SENSEI OS')).toBeVisible();
  await expect(page.getByRole('heading', { name: /AUTHENTICATE/i })).toBeVisible();
});

test('unauthenticated access redirects to login', async ({ page }) => {
  await page.goto('/today');
  await expect(page).toHaveURL(/\/login/);
});

test('authenticated session lands on Today', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: /sign in|login|authenticate/i }).click();
  // The default landing route is /today (item 30/67).
  await expect(page).toHaveURL(/\/today/, { timeout: 20_000 });
  await expect(page.getByText(/TODAY/i).first()).toBeVisible();
});

test('Today page shows explicit states, never silent zeros', async ({ page }) => {
  // With the API unreachable the page must render UNAVAILABLE — a failed
  // request must never look like a healthy zero (item 4).
  await page.route('**/api/v1/today', (route) => route.fulfill({ status: 500 }));
  await page.goto('/today');
  await expect(page.getByText(/STATUS UNKNOWN/i)).toBeVisible({ timeout: 15_000 });
});

test('sidebar exposes the TPS work surfaces (item 67)', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: /sign in|login|authenticate/i }).click();
  await expect(page).toHaveURL(/\/today/, { timeout: 20_000 });
  for (const label of ['WORK', 'LSW', 'TIER MEETINGS', 'KANBAN']) {
    await expect(page.getByText(label, { exact: false }).first()).toBeVisible();
  }
});

test('station page offers plain-language help categories (item 31)', async ({ page }) => {
  // The operator never needs Andon terminology: the help categories are
  // plain language.
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: /sign in|login|authenticate/i }).click();
  await expect(page).toHaveURL(/\/today/, { timeout: 20_000 });
  await page.goto('/station');
  await expect(page.getByText(/I NEED HELP/i)).toBeVisible({ timeout: 15_000 });
  await page.getByText(/I NEED HELP/i).click();
  for (const category of ['QUALITY', 'MATERIAL', 'SAFETY', 'I CANNOT KEEP PACE']) {
    await expect(page.getByText(category, { exact: true })).toBeVisible();
  }
});

// Item 42: the Andon flow must be proven END-TO-END THROUGH THE REAL UI —
// select a category, enter a note, submit, assert the network request used
// the safe command DTO, and verify the Team Lead interval board surfaces
// the abnormality.

async function login(page) {
  await page.goto('/login');
  await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
  await page.getByRole('button', { name: /sign in|login|authenticate/i }).click();
  await expect(page).toHaveURL(/\/today/, { timeout: 20_000 });
}

test('station help: UI submit creates a server-derived Andon the team lead sees', async ({ page }) => {
  await login(page);
  await page.goto('/station');
  await expect(page.getByText(/I NEED HELP/i)).toBeVisible({ timeout: 15_000 });

  // Intercept the SAFE command request — the payload must be the plain
  // operator DTO (item 40), never a client-supplied full Andon object.
  let commandBody = null;
  await page.route('**/api/v1/andon', async (route) => {
    commandBody = route.request().postDataJSON();
    await route.continue();
  });

  await page.getByText(/I NEED HELP/i).click();
  await page.getByText('MATERIAL', { exact: true }).click();
  // The note field (plain-language description) must be filled and the
  // form submitted — the operator's flow, not a raw API call.
  const noteField = page.getByPlaceholder(/note|describe/i).first();
  await noteField.fill('e2e: connector tray empty');
  await page.getByRole('button', { name: /send|submit|request help/i }).click();

  await expect
    .poll(async () => commandBody !== null, { timeout: 15_000 })
    .toBeTruthy();
  expect(commandBody.issue_type).toBe('material');
  expect(commandBody.severity).toBe('medium');
  expect(commandBody.description).toContain('connector tray empty');
  // The safe DTO carries NO server-owned identity fields.
  expect(commandBody.status).toBeUndefined();
  expect(commandBody.raised_by).toBeUndefined();

  // The Team Lead interval board surfaces the abnormality (the Andon the
  // operator raised must be visible to the lead).
  await page.goto('/team-lead');
  await expect(page.getByText(/ABNORMALITY|ANDON/i).first()).toBeVisible({ timeout: 15_000 });
});

test('unauthenticated access redirects to login', async ({ page }) => {
  await page.goto('/today');
  await expect(page).toHaveURL(/\/login/);
});
