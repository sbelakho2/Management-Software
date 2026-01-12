import { test, expect, type Page } from '@playwright/test';

type BootstrapTokens = {
  access_token: string;
  refresh_token: string;
};

async function authenticateAsExecutive(page: Page): Promise<BootstrapTokens> {
  const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

  test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');

  const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
    data: {
      email: 'ceo@sensei.os',
      password: 'ChangeMe123!',
      first_name: 'E2E',
      last_name: 'CEO',
      is_superuser: true,
    },
  });

  if (bootstrap.ok()) {
    const tokens = await bootstrap.json();
    await page.addInitScript((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);

    await page.goto('/executive');
    return tokens as BootstrapTokens;
  }

  throw new Error('Failed to bootstrap Executive user');
}

test.describe('CEO/Exec Path', () => {
  test('North Star -> NL2SQL -> Employee Risk -> Export', async ({ page }) => {
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';
    const tokens = await authenticateAsExecutive(page);
    const authHeaders = { Authorization: `Bearer ${tokens.access_token}` };

    // Backend + DB integrity seed (shared invariant across persona paths)
    const seed = await page.request.post(`${apiUrl}/api/v1/dev/e2e/seed-lineage`, { headers: authHeaders });
    expect(seed.ok()).toBeTruthy();
    const seedJson = await seed.json();
    expect(seedJson.success).toBeTruthy();
    const seeded = seedJson.data as { rfq_id: string; quote_id: string; lineage_relationship_type: string };

    const rfqGet = await page.request.get(`${apiUrl}/api/v1/rfqs/${seeded.rfq_id}`, { headers: authHeaders });
    expect(rfqGet.ok()).toBeTruthy();
    const quoteGet = await page.request.get(`${apiUrl}/api/v1/quotes/${seeded.quote_id}`, { headers: authHeaders });
    expect(quoteGet.ok()).toBeTruthy();

    const lineage = await page.request.get(
      `${apiUrl}/api/v1/data-lineage/graph?entity_type=rfq&entity_id=${encodeURIComponent(seeded.rfq_id)}&max_depth=2`,
      { headers: authHeaders }
    );
    expect(lineage.ok()).toBeTruthy();
    const lineageJson = await lineage.json();
    expect(lineageJson.success).toBeTruthy();
    expect(
      (lineageJson.data?.edges ?? []).some(
        (e: any) =>
          e.source_entity_type === 'rfq' &&
          e.source_entity_id === seeded.rfq_id &&
          e.target_entity_type === 'quote' &&
          e.target_entity_id === seeded.quote_id &&
          e.relationship_type === seeded.lineage_relationship_type
      )
    ).toBeTruthy();

    const ctx = await page.request.get(
      `${apiUrl}/api/v1/context/pack?entity_type=rfq&entity_id=${encodeURIComponent(seeded.rfq_id)}&max_depth=2`,
      { headers: authHeaders }
    );
    expect(ctx.ok()).toBeTruthy();
    const ctxJson = await ctx.json();
    expect(ctxJson.success).toBeTruthy();
    expect((ctxJson.data?.nodes ?? []).some((n: any) => n.entity_type === 'rfq' && n.entity_id === seeded.rfq_id)).toBeTruthy();

    // Page is visible
    await expect(page.locator('[data-testid="executive-page"]')).toBeVisible();

    // 1) North Star dashboard
    await page.getByRole('tab', { name: 'North Star Dashboard' }).click();
    await expect(page.locator('[data-testid="north-star"]')).toBeVisible();

    // 2) NL2SQL query
    await page.getByRole('tab', { name: 'NL2SQL Query' }).click();
    await expect(page.locator('[data-testid="nl2sql-question"]')).toBeVisible();

    await page.locator('[data-testid="nl2sql-question"]').fill('How many open CAPAs are there?');
    await page.locator('[data-testid="nl2sql-run"]').click();
    await expect(page.locator('[data-testid="nl2sql-result"]')).toBeVisible();
    await expect(page.locator('[data-testid="nl2sql-result"]').getByText(/open_capas/i)).toBeVisible();

    // 3) Employee risk analysis
    await page.getByRole('tab', { name: 'Employee Risk Analysis' }).click();
    await expect(page.locator('[data-testid="risk-employee-name"]')).toBeVisible();

    await page.locator('[data-testid="risk-employee-name"]').fill('Alice Example');
    await page.locator('[data-testid="risk-department"]').fill('Operations');
    await page.locator('[data-testid="risk-run"]').click();
    await expect(page.locator('[data-testid="risk-result"]')).toBeVisible();

    // 4) Strategic export (download)
    await page.getByRole('tab', { name: 'Strategic Report Export' }).click();
    await expect(page.locator('[data-testid="export-download"]')).toBeVisible();

    const downloadPromise = page.waitForEvent('download');
    await page.locator('[data-testid="export-download"] a').click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/strategic-report-.*\.json/);
  });
});
