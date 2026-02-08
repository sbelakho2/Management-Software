/**
 * k6 load test — SenseiOS API endpoints
 *
 * Run:   k6 run k6/load-test.js --env BASE_URL=http://localhost:8000
 *
 * Scenarios:
 *   smoke   — 1 VU  × 30s   (quick sanity)
 *   average — 20 VU × 2 min (normal day)
 *   stress  — 100 VU ramp   (peak hour)
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ─── custom metrics ──────────────────────────────────────────────
const errorRate = new Rate('errors');
const healthLatency = new Trend('health_latency', true);
const authLatency = new Trend('auth_latency', true);
const apiLatency = new Trend('api_latency', true);

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
  },
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1500'],
    errors: ['rate<0.05'],
    health_latency: ['p(95)<100'],
    auth_latency: ['p(95)<300'],
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
  }

  sleep(1);
}
