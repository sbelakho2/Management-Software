# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke.spec.js >> login renders the Starz Forge identity
- Location: e2e/smoke.spec.js:10:1

# Error details

```
Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:18099/login
Call log:
  - navigating to "http://localhost:18099/login", waiting until "load"

```

# Test source

```ts
  1   | // Starz Forge smoke suite (item 77): the behavioral contracts that unit
  2   | // tests cannot reach — login, the Today landing page, the station help
  3   | // flow and explicit error states. These run against a REAL built stack.
  4   | 
  5   | const { test, expect } = require('@playwright/test');
  6   | 
  7   | const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL || 'admin@starzforge.local';
  8   | const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD || 'admin-password';
  9   | 
  10  | test('login renders the Starz Forge identity', async ({ page }) => {
> 11  |   await page.goto('/login');
      |              ^ Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:18099/login
  12  |   await expect(page.getByText('STARZ FORGE')).toBeVisible();
  13  |   await expect(page.getByRole('heading', { name: /AUTHENTICATE/i })).toBeVisible();
  14  | });
  15  | 
  16  | test('operator route access redirects unauthenticated visitors to login', async ({ page }) => {
  17  |   await page.goto('/today');
  18  |   await expect(page).toHaveURL(/\/login/);
  19  | });
  20  | 
  21  | test('authenticated session lands on Today', async ({ page }) => {
  22  |   await page.goto('/login');
  23  |   await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  24  |   await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
  25  |   await page.getByRole('button', { name: /sign in|login|authenticate/i }).click();
  26  |   // The default landing route is /today (item 30/67).
  27  |   await expect(page).toHaveURL(/\/today/, { timeout: 20_000 });
  28  |   await expect(page.getByText(/TODAY/i).first()).toBeVisible();
  29  | });
  30  | 
  31  | test('Today page shows explicit states, never silent zeros', async ({ page }) => {
  32  |   // With the API unreachable the page must render UNAVAILABLE — a failed
  33  |   // request must never look like a healthy zero (item 4).
  34  |   await page.route('**/api/v1/today', (route) => route.fulfill({ status: 500 }));
  35  |   await page.goto('/today');
  36  |   await expect(page.getByText(/STATUS UNKNOWN/i)).toBeVisible({ timeout: 15_000 });
  37  | });
  38  | 
  39  | test('sidebar exposes the TPS work surfaces (item 67)', async ({ page }) => {
  40  |   await page.goto('/login');
  41  |   await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  42  |   await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
  43  |   await page.getByRole('button', { name: /sign in|login|authenticate/i }).click();
  44  |   await expect(page).toHaveURL(/\/today/, { timeout: 20_000 });
  45  |   for (const label of ['WORK', 'LSW', 'TIER MEETINGS', 'KANBAN']) {
  46  |     await expect(page.getByText(label, { exact: false }).first()).toBeVisible();
  47  |   }
  48  | });
  49  | 
  50  | test('station page offers plain-language help categories (item 31)', async ({ page }) => {
  51  |   // The operator never needs Andon terminology: the help categories are
  52  |   // plain language.
  53  |   await page.goto('/login');
  54  |   await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  55  |   await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
  56  |   await page.getByRole('button', { name: /sign in|login|authenticate/i }).click();
  57  |   await expect(page).toHaveURL(/\/today/, { timeout: 20_000 });
  58  |   await page.goto('/station');
  59  |   await expect(page.getByText(/I NEED HELP/i)).toBeVisible({ timeout: 15_000 });
  60  |   await page.getByText(/I NEED HELP/i).click();
  61  |   for (const category of ['QUALITY', 'MATERIAL', 'SAFETY', 'I CANNOT KEEP PACE']) {
  62  |     await expect(page.getByText(category, { exact: true })).toBeVisible();
  63  |   }
  64  | });
  65  | 
  66  | // Item 42: the Andon flow must be proven END-TO-END THROUGH THE REAL UI —
  67  | // select a category, enter a note, submit, assert the network request used
  68  | // the safe command DTO, and verify the Team Lead interval board surfaces
  69  | // the abnormality.
  70  | 
  71  | async function login(page) {
  72  |   await page.goto('/login');
  73  |   await page.getByLabel(/email/i).fill(ADMIN_EMAIL);
  74  |   await page.getByLabel(/password/i).fill(ADMIN_PASSWORD);
  75  |   await page.getByRole('button', { name: /sign in|login|authenticate/i }).click();
  76  |   await expect(page).toHaveURL(/\/today/, { timeout: 20_000 });
  77  | }
  78  | 
  79  | test('station help: UI submit creates a server-derived Andon the team lead sees', async ({ page }) => {
  80  |   await login(page);
  81  |   await page.goto('/station');
  82  |   await expect(page.getByText(/I NEED HELP/i)).toBeVisible({ timeout: 15_000 });
  83  | 
  84  |   // Intercept the SAFE command request — the payload must be the plain
  85  |   // operator DTO (item 40), never a client-supplied full Andon object.
  86  |   let commandBody = null;
  87  |   await page.route('**/api/v1/andon', async (route) => {
  88  |     commandBody = route.request().postDataJSON();
  89  |     await route.continue();
  90  |   });
  91  | 
  92  |   await page.getByText(/I NEED HELP/i).click();
  93  |   await page.getByText('MATERIAL', { exact: true }).click();
  94  |   // The note field (plain-language description) must be filled and the
  95  |   // form submitted — the operator's flow, not a raw API call.
  96  |   const noteField = page.getByPlaceholder(/note|describe/i).first();
  97  |   await noteField.fill('e2e: connector tray empty');
  98  |   await page.getByRole('button', { name: /send|submit|request help/i }).click();
  99  | 
  100 |   await expect
  101 |     .poll(async () => commandBody !== null, { timeout: 15_000 })
  102 |     .toBeTruthy();
  103 |   expect(commandBody.issue_type).toBe('material');
  104 |   expect(commandBody.severity).toBe('medium');
  105 |   expect(commandBody.description).toContain('connector tray empty');
  106 |   // The safe DTO carries NO server-owned identity fields.
  107 |   expect(commandBody.status).toBeUndefined();
  108 |   expect(commandBody.raised_by).toBeUndefined();
  109 | 
  110 |   // The Team Lead interval board surfaces the abnormality (the Andon the
  111 |   // operator raised must be visible to the lead).
```