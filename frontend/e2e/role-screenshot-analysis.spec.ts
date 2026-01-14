import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Keep this list aligned with the capture spec.
const ALL_ROLES = [
  'admin',
  'ceo',
  'executive',
  'gm',
  'sales_rep',
  'sales_engineer',
  'estimator',
  'quality',
  'quality_inspector',
  'supervisor',
  'operator',
  'finance',
  'accountant',
  'hr',
  'it',
  'security',
  'warehouse',
  'shipping_receiver',
  'auditor',
  'supply_chain',
  'purchasing',
  'maintenance',
  'maintenance_tech',
  'team_lead',
];

const SCREENSHOT_DIR = path.join(__dirname, '..', 'role-screenshots');

type RoleResults = {
  role: string;
  loginSuccess?: boolean;
  sidebarHrefs?: string[];
  pages?: Array<{ path?: string; accessible?: boolean; hasError?: boolean; errorMessage?: string }>;
};

test.describe('Role screenshot analysis (post-capture)', () => {
  test('Analyze results.json for all roles', async () => {
    const summaryPath = path.join(SCREENSHOT_DIR, 'audit-summary.json');

    const failures: Array<{ role: string; reason: string }> = [];
    const roles: Record<string, unknown> = {};

    let totalUnexpectedPageErrors = 0;

    for (const role of ALL_ROLES) {
      const roleDir = path.join(SCREENSHOT_DIR, role);
      const resultsPath = path.join(roleDir, 'results.json');

      if (!fs.existsSync(resultsPath)) {
        failures.push({ role, reason: 'missing results.json (capture run incomplete)' });
        continue;
      }

      let results: RoleResults;
      try {
        results = JSON.parse(fs.readFileSync(resultsPath, 'utf-8')) as RoleResults;
      } catch (err) {
        failures.push({ role, reason: `results.json unreadable: ${err instanceof Error ? err.message : 'unknown error'}` });
        continue;
      }

      roles[role] = results;

      if (!results?.loginSuccess) {
        failures.push({ role, reason: 'login failed' });
        continue;
      }

      const pages = results?.pages || [];

      // Unexpected errors: allow explicit 401/403 (restricted) only.
      const unexpectedErrors = pages.filter((p) => {
        if (!p?.hasError) return false;
        const msg = String(p.errorMessage || '');
        return !msg.includes('401') && !msg.includes('403');
      });

      if (unexpectedErrors.length > 0) {
        totalUnexpectedPageErrors += unexpectedErrors.length;
        failures.push({ role, reason: `${unexpectedErrors.length} unexpected page errors` });
      }

      // Sidebar should not contain links that truly behaved as "restricted" (redirect-to-login)
      const sidebarHrefs: string[] = results?.sidebarHrefs || [];
      const restrictedPages: string[] = (results?.pages || [])
        .filter((p) => p && p.accessible === false && p.hasError === false && typeof p.path === 'string')
        .map((p) => p.path as string);

      const sidebarHasRestricted = sidebarHrefs.filter((h) => restrictedPages.includes(h));
      if (sidebarHasRestricted.length > 0) {
        failures.push({ role, reason: `sidebar exposes restricted links: ${sidebarHasRestricted.join(', ')}` });
      }
    }

    const summary = {
      generatedAt: new Date().toISOString(),
      totalUnexpectedPageErrors,
      failures,
      roles,
    };

    fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));

    if (failures.length > 0) {
      console.log(`Audit summary saved to: ${summaryPath}`);
      for (const f of failures) {
        console.log(`❌ ${f.role}: ${f.reason}`);
      }
    }

    expect(failures, `One or more roles failed audit; see ${summaryPath}`).toEqual([]);
  });
});
