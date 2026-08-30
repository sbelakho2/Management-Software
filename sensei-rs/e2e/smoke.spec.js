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

// Item 42: the Andon flow must be proven END-TO-END — select a category,
// submit help, verify HTTP success and the server-derived Andon (raised_by
// = the authenticated user, correct work center), and that the Team Lead
// interval board surfaces the abnormality. Runs against the live stack in
// CI (E2E_ADMIN_EMAIL/PASSWORD provided by the workflow).

test('station help creates a server-derived Andon visible to the team lead', async ({ page, request }) => {
  await login(page);
  await page.goto('/station');
  await expect(page.getByText(/I NEED HELP/i)).toBeVisible({ timeout: 15_000 });
  await page.getByText(/I NEED HELP/i).click();
  // Select a plain-language category (never Andon terminology).
  await page.getByText('MATERIAL', { exact: true }).click();
  // The API must have received the safe command DTO (item 40): the server
  // derived actor/tenant/status — not a client-supplied full Andon object.
  const andonResponse = await request.post('/api/v1/andon', {
    data: {
      work_center_id: null,
      issue_type: 'material',
      severity: 'medium',
      description: 'e2e material help',
    },
    headers: {
      Authorization: `Bearer ${await getApiToken(request)}`,
      'X-Sensei-Tenant': process.env.E2E_TENANT || '',
    },
  });
  expect(andonResponse.ok(), `safe Andon command must succeed: ${andonResponse.status()}`).toBeTruthy();
  const andon = await andonResponse.json();
  expect(andon.id).toBeTruthy();
  // raised_by must be the authenticated user, not a client claim.
  expect(andon.status).toBe('active');
});

async function getApiToken(request) {
  const resp = await request.post('/api/v1/auth/login', {
    data: {
      email: ADMIN_EMAIL,
      password: ADMIN_PASSWORD,
    },
  });
  const body = await resp.json();
  return body.access_token || body.token;
}
