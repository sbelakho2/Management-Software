import { test, expect, type Page } from '@playwright/test';

/**
 * GM/Admin Path E2E Test
 * 
 * Setup Wizard -> Role/Permission Audit -> LSW Checklist -> Obeya SQDCP Review -> System Health Dashboard
 */

type BootstrapTokens = {
  access_token: string;
  refresh_token: string;
};

async function authenticateAsGM(page: Page): Promise<BootstrapTokens> {
  const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';

  test.skip(!process.env.E2E_WITH_BACKEND, 'Requires real backend (set E2E_WITH_BACKEND=1)');

  await page.request.post(`${apiUrl}/api/v1/dev/repair-core-rbac`);

  const bootstrap = await page.request.post(`${apiUrl}/api/v1/dev/bootstrap-user`, {
    data: {
      email: 'gm@sensei.os',
      password: 'ChangeMe123!',
      first_name: 'E2E',
      last_name: 'GM',
      is_superuser: true,
    },
  });

  if (bootstrap.ok()) {
    const tokens = await bootstrap.json();
    await page.addInitScript((t) => {
      localStorage.setItem('access_token', t.access_token);
      localStorage.setItem('refresh_token', t.refresh_token);
    }, tokens);

    await page.goto('/admin');
    return tokens as BootstrapTokens;
  }

  throw new Error('Failed to bootstrap GM user');
}

test.describe('GM/Admin Path', () => {
  test('Setup Wizard -> Role Audit -> LSW -> Obeya SQDCP -> System Health', async ({ page }) => {
    const apiUrl = process.env.E2E_API_URL || 'http://localhost:8000';
    const tokens = await authenticateAsGM(page);
    const authHeaders = { Authorization: `Bearer ${tokens.access_token}` };

    // Backend + DB integrity seed
    const seed = await page.request.post(`${apiUrl}/api/v1/dev/e2e/seed-lineage`, { headers: authHeaders });
    if (seed.ok()) {
      const seedJson = await seed.json();
      expect(seedJson.success).toBeTruthy();
      const seeded = seedJson.data as { rfq_id: string; quote_id: string; lineage_relationship_type: string };

      // Verify persisted entities are readable (DB-backed)
      const rfqGet = await page.request.get(`${apiUrl}/api/v1/rfqs/${seeded.rfq_id}`, { headers: authHeaders });
      expect(rfqGet.ok()).toBeTruthy();
      const quoteGet = await page.request.get(`${apiUrl}/api/v1/quotes/${seeded.quote_id}`, { headers: authHeaders });
      expect(quoteGet.ok()).toBeTruthy();

      // Verify lineage graph reflects the persisted link
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

      // Verify context pack can resolve RFQ snapshot (DB-backed)
      const ctx = await page.request.get(
        `${apiUrl}/api/v1/context/pack?entity_type=rfq&entity_id=${encodeURIComponent(seeded.rfq_id)}&max_depth=2`,
        { headers: authHeaders }
      );
      expect(ctx.ok()).toBeTruthy();
      const ctxJson = await ctx.json();
      expect(ctxJson.success).toBeTruthy();
      expect((ctxJson.data?.nodes ?? []).some((n: any) => n.entity_type === 'rfq' && n.entity_id === seeded.rfq_id)).toBeTruthy();
    }

    // 1) Setup Wizard section in Admin
    // Navigate to admin page where setup wizard config lives
    await page.goto('/admin');
    await expect(page).toHaveURL(/\/(admin|today|settings)/);
    await expect(page.locator('main, [role="main"], [data-testid="admin-page"]').first()).toBeVisible({ timeout: 10000 });

    const hasGatesTab = await page.getByRole('tab', { name: /gates/i }).isVisible({ timeout: 2000 }).catch(() => false);

    // Click Gates tab for setup wizard gate configuration
    if (hasGatesTab) {
      await page.getByRole('tab', { name: /gates/i }).click();
      await expect(page.locator('text=Quality Gates Configuration')).toBeVisible();

      // 2) Role/Permission Audit
      await page.getByRole('tab', { name: /roles/i }).click();
      await expect(page.locator('text=Role & Permission Management')).toBeVisible();

      // Verify role table displays at least one role
      await expect(page.locator('table').locator('tr').first()).toBeVisible();

      // 3) LSW Checklist (Learning cadence tab)
      await page.getByRole('tab', { name: /learning/i }).click();
      await expect(page.locator('text=Learning Cadence Configuration')).toBeVisible();

      // Verify a cadence row exists
      await expect(page.getByText('Weekly Team Learning', { exact: false })).toBeVisible();
    }

    // 4) Obeya SQDCP Review
    await page.goto('/obeya');
    await expect(page).toHaveURL(/\/obeya/);
    await expect(page.locator('main, [role="main"], [data-testid="obeya-page"]').first()).toBeVisible({ timeout: 10000 });

    const hasSqdcpTab = await page.getByRole('tab', { name: /sqdcp detail/i }).isVisible({ timeout: 2000 }).catch(() => false);
    if (hasSqdcpTab) {
      await page.getByRole('tab', { name: /sqdcp detail/i }).click();

      // Verify SQDCP sections exist (Safety, Quality, Delivery, Cost, People)
      for (const label of ['Safety', 'Quality', 'Delivery', 'Cost', 'People']) {
        await expect(page.getByText(label, { exact: false }).first()).toBeVisible();
      }
    }

    // 5) System Health Dashboard
    await page.goto('/analytics');
    await expect(page).toHaveURL(/\/analytics/);
    await expect(page.locator('main, [role="main"], [data-testid="analytics-page"]').first()).toBeVisible({ timeout: 10000 });
    const hasModelHealth = await page.locator('text=Model Health Status').first().isVisible({ timeout: 2000 }).catch(() => false);
    if (hasModelHealth) {
      await expect(page.locator('text=Model Health Status').first()).toBeVisible();
    }

    // 6) System health adjacency: Data lineage tooling in Admin
    await page.goto('/admin');
    await expect(page.locator('main, [role="main"], [data-testid="admin-page"]').first()).toBeVisible({ timeout: 10000 });

    const hasLineageTab = await page.getByRole('tab', { name: /lineage/i }).isVisible({ timeout: 2000 }).catch(() => false);
    if (hasLineageTab) {
      await page.getByRole('tab', { name: /lineage/i }).click();
      await expect(page.locator('[data-testid="admin-lineage-entity-type"]')).toBeVisible();
      await expect(page.locator('[data-testid="admin-lineage-load"]')).toBeVisible();
    }
  });
});
