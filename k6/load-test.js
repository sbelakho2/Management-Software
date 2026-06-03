/**
 * k6 load test — Sensei OS API (Tri-System Integration)
 *
 * Run:
 *   k6 run k6/load-test.js --env BASE_URL=http://localhost:8000
 *   k6 run k6/load-test.js --env BASE_URL=https://staging.sensei.example.com --env ERPSTARZ_URL=https://erp.starz.example.com --env CRM_V2_URL=https://crm-v2.example.com
 *
 * Scenarios:
 *   smoke         — 1 VU  × 30s   (quick sanity)
 *   average       — 20 VU × 2 min (normal day)
 *   stress        — 100 VU ramp   (peak hour)
 *   integration   — 10 VU × 2 min (cross-system sync scenarios)
 *
 * Endpoints covered:
 *   - Native Sensei: health, auth, work-orders, inspections, employees, dashboard
 *   - erpStarz sync: /api/v1/integration/erpstarz/sync*, /api/v1/integration/erpstarz/status
 *   - CRM-v2 sync:   /api/v1/integration/crm-v2/sync*, /api/v1/integration/crm-v2/status
 *   - Redis Streams: (simulated via integration health endpoints)
 *   - WebSocket:     connection lifecycle via API (actual WS testing requires k6 WS extension)
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ─── custom metrics ──────────────────────────────────────────────
const errorRate = new Rate('errors');
const healthLatency = new Trend('health_latency', true);
const authLatency = new Trend('auth_latency', true);
const apiLatency = new Trend('api_latency', true);
const integrationLatency = new Trend('integration_latency', true);
const erpStarzLatency = new Trend('erpstarz_latency', true);
const crmV2Latency = new Trend('crmv2_latency', true);

// ─── options ─────────────────────────────────────────────────────
export const options = {
  scenarios: {
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      tags: { scenario: 'smoke' },
    },
    average: {
      executor: 'constant-vus',
      vus: 20,
      duration: '2m',
      startTime: '35s',
      tags: { scenario: 'average' },
    },
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 50 },
        { duration: '1m', target: 100 },
        { duration: '30s', target: 0 },
      ],
      startTime: '3m',
      tags: { scenario: 'stress' },
    },
    integration: {
      executor: 'constant-vus',
      vus: 10,
      duration: '2m',
      startTime: '1m',
      tags: { scenario: 'integration' },
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1500'],
    errors: ['rate<0.05'],
    health_latency: ['p(95)<100'],
    auth_latency: ['p(95)<300'],
    integration_latency: ['p(95)<1000'],  // cross-system syncs may be slower
    erpstarz_latency: ['p(95)<2000'],     // external ERP calls have higher latency
    crmV2_latency: ['p(95)<2000'],        // external CRM calls have higher latency
  },
};

// ─── helpers ─────────────────────────────────────────────────────
const BASE = __ENV.BASE_URL || 'http://localhost:8000';

function headers(token) {
  const h = { 'Content-Type': 'application/json' };
  if (token) h['Authorization'] = `Bearer ${token}`;
  return h;
}

// ─── setup (auth once) ──────────────────────────────────────────
export function setup() {
  const loginPayload = JSON.stringify({
    username: __ENV.TEST_USER || 'admin@sensei.local',
    password: __ENV.TEST_PASS || 'admin',
  });
  const res = http.post(`${BASE}/api/v1/auth/login`, loginPayload, {
    headers: { 'Content-Type': 'application/json' },
  });
  if (res.status === 200) {
    return { token: res.json('access_token') };
  }
  console.warn(`Login failed (${res.status}), running unauthenticated tests only`);
  return { token: null };
}

// ─── integration test group: erpStarz sync scenarios ────────────
function testErpStarzIntegration(token) {
  group('erpStarz Integration', () => {
    // Check erpStarz sync status
    const status = http.get(`${BASE}/api/v1/integration/erpstarz/status`, {
      headers: headers(token),
    });
    erpStarzLatency.add(status.timings.duration);
    check(status, { 'erpstarz status 200': (r) => r.status === 200 });
    errorRate.add(status.status !== 200);

    // Trigger erpStarz data sync (material master)
    const syncMat = http.post(`${BASE}/api/v1/integration/erpstarz/sync/materials?limit=50`, {}, {
      headers: headers(token),
    });
    integrationLatency.add(syncMat.timings.duration);
    check(syncMat, { 'erpstarz sync materials 202': (r) => r.status === 202 });
    errorRate.add(syncMat.status !== 202);

    // Trigger erpStarz order sync
    const syncOrd = http.post(`${BASE}/api/v1/integration/erpstarz/sync/orders?limit=20`, {}, {
      headers: headers(token),
    });
    integrationLatency.add(syncOrd.timings.duration);
    check(syncOrd, { 'erpstarz sync orders 202': (r) => r.status === 202 });
    errorRate.add(syncOrd.status !== 202);
  });
}

// ─── integration test group: CRM-v2 sync scenarios ──────────────
function testCrmV2Integration(token) {
  group('CRM-v2 Integration', () => {
    // Check CRM-v2 sync status
    const status = http.get(`${BASE}/api/v1/integration/crm-v2/status`, {
      headers: headers(token),
    });
    crmV2Latency.add(status.timings.duration);
    check(status, { 'crmv2 status 200': (r) => r.status === 200 });
    errorRate.add(status.status !== 200);

    // Trigger CRM-v2 customer sync
    const syncCust = http.post(`${BASE}/api/v1/integration/crm-v2/sync/customers?limit=50`, {}, {
      headers: headers(token),
    });
    integrationLatency.add(syncCust.timings.duration);
    check(syncCust, { 'crmv2 sync customers 202': (r) => r.status === 202 });
    errorRate.add(syncCust.status !== 202);

    // Trigger CRM-v2 lead sync
    const syncLead = http.post(`${BASE}/api/v1/integration/crm-v2/sync/leads?limit=20`, {}, {
      headers: headers(token),
    });
    integrationLatency.add(syncLead.timings.duration);
    check(syncLead, { 'crmv2 sync leads 202': (r) => r.status === 202 });
    errorRate.add(syncLead.status !== 202);
  });
}

// ─── integration test group: cross-system event stream ──────────
function testCrossSystemEvents(token) {
  group('Cross-System Events (Redis Streams)', () => {
    // Publish an integration event
    const eventPayload = JSON.stringify({
      source: 'sensei-load-test',
      type: 'order.sync.requested',
      payload: { orderId: 'LOADTEST-001', timestamp: Date.now() },
    });
    const publish = http.post(`${BASE}/api/v1/integration/events/publish`, eventPayload, {
      headers: headers(token),
    });
    integrationLatency.add(publish.timings.duration);
    check(publish, { 'event publish 202': (r) => r.status === 202 });
    errorRate.add(publish.status !== 202);

    // Consume pending events (check event bus health)
    const consume = http.get(`${BASE}/api/v1/integration/events/pending?limit=10`, {
      headers: headers(token),
    });
    integrationLatency.add(consume.timings.duration);
    check(consume, { 'event consume 200': (r) => r.status === 200 });
    errorRate.add(consume.status !== 200);
  });
}

// ─── default function (runs per VU iteration) ───────────────────
export default function (data) {
  const token = data.token;

  group('Health & Readiness', () => {
    const res = http.get(`${BASE}/api/v1/health`);
    healthLatency.add(res.timings.duration);
    check(res, { 'health 200': (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
  });

  if (token) {
    group('Authenticated API', () => {
      // Work orders list
      const wo = http.get(`${BASE}/api/v1/production/work-orders?limit=20`, {
        headers: headers(token),
      });
      apiLatency.add(wo.timings.duration);
      check(wo, { 'work-orders 200': (r) => r.status === 200 });
      errorRate.add(wo.status !== 200);

      // Quality inspections
      const qi = http.get(`${BASE}/api/v1/quality/inspections?limit=20`, {
        headers: headers(token),
      });
      apiLatency.add(qi.timings.duration);
      check(qi, { 'inspections 200': (r) => r.status === 200 });
      errorRate.add(qi.status !== 200);

      // HR employees
      const hr = http.get(`${BASE}/api/v1/hr/employees?limit=20`, {
        headers: headers(token),
      });
      apiLatency.add(hr.timings.duration);
      check(hr, { 'employees 200': (r) => r.status === 200 });
      errorRate.add(hr.status !== 200);

      // Dashboard stats
      const dash = http.get(`${BASE}/api/v1/analytics/dashboard`, {
        headers: headers(token),
      });
      apiLatency.add(dash.timings.duration);
      check(dash, { 'dashboard 200|401': (r) => [200, 401].includes(r.status) });
    });

    // Cross-system integration tests (only in the 'integration' scenario)
    // These are separated so smoke/average/stress scenarios don't depend on external systems
    if (__ENV.SCENARIO === 'integration' || __ENV.TEST_INTEGRATION === 'true') {
      testErpStarzIntegration(token);
      testCrmV2Integration(token);
      testCrossSystemEvents(token);
    }
  }

  sleep(1);
}
