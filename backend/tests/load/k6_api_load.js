/**
 * k6 Load Testing Script for SenseiOS API.
 *
 * Tests critical API endpoints under simulated production load.
 * Run with: k6 run tests/load/k6_api_load.js
 *
 * Checklist item: #485
 */

import http from "k6/http";
import { check, sleep, group } from "k6";
import { Rate, Trend, Counter } from "k6/metrics";

// ─── Custom Metrics ──────────────────────────────────────────────

const errorRate = new Rate("errors");
const loginDuration = new Trend("login_duration", true);
const apiDuration = new Trend("api_duration", true);
const failedRequests = new Counter("failed_requests");

// ─── Configuration ───────────────────────────────────────────────

const BASE_URL = __ENV.API_URL || "http://localhost:8000";
const API_PREFIX = `${BASE_URL}/api/v1`;

export const options = {
  stages: [
    { duration: "30s", target: 10 },   // Ramp up to 10 users
    { duration: "1m", target: 50 },    // Ramp up to 50 users
    { duration: "2m", target: 50 },    // Sustain 50 users
    { duration: "1m", target: 100 },   // Spike to 100 users
    { duration: "30s", target: 100 },  // Sustain spike
    { duration: "1m", target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: [
      "p(95)<500",   // 95% of requests under 500ms
      "p(99)<2000",  // 99% under 2s
    ],
    errors: ["rate<0.05"],         // Error rate < 5%
    login_duration: ["p(95)<1000"], // Login under 1s at p95
    api_duration: ["p(95)<500"],    // API calls under 500ms at p95
  },
};

// ─── Setup ───────────────────────────────────────────────────────

export function setup() {
  // Login to get an auth token
  const loginRes = http.post(
    `${API_PREFIX}/auth/login`,
    JSON.stringify({
      email: __ENV.TEST_EMAIL || "admin@example.com",
      password: __ENV.TEST_PASSWORD || "admin123",
    }),
    { headers: { "Content-Type": "application/json" } }
  );

  if (loginRes.status !== 200) {
    console.error(`Login failed: ${loginRes.status} ${loginRes.body}`);
    return { token: "" };
  }

  const body = JSON.parse(loginRes.body);
  return { token: body.access_token };
}

// ─── Main Test Scenario ──────────────────────────────────────────

export default function (data) {
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${data.token}`,
  };
  const params = { headers };

  group("Health Check", () => {
    const res = http.get(`${API_PREFIX}/health`);
    check(res, {
      "health status 200": (r) => r.status === 200,
      "health response time < 200ms": (r) => r.timings.duration < 200,
    }) || errorRate.add(1);
  });

  sleep(0.5);

  group("Quality - List Inspections", () => {
    const res = http.get(`${API_PREFIX}/quality/inspections?page=1&page_size=20`, params);
    const ok = check(res, {
      "inspections status 200": (r) => r.status === 200,
      "inspections has data": (r) => {
        try { return Array.isArray(JSON.parse(r.body)); } catch { return false; }
      },
    });
    if (!ok) { errorRate.add(1); failedRequests.add(1); }
    apiDuration.add(res.timings.duration);
  });

  sleep(0.5);

  group("Quality - List NCRs", () => {
    const res = http.get(`${API_PREFIX}/quality/ncrs?page=1&page_size=20`, params);
    check(res, {
      "NCRs status 200": (r) => r.status === 200,
    }) || errorRate.add(1);
    apiDuration.add(res.timings.duration);
  });

  sleep(0.5);

  group("KPI Metrics", () => {
    const res = http.get(`${API_PREFIX}/kpi/metrics`, params);
    check(res, {
      "KPI status 200": (r) => r.status === 200,
    }) || errorRate.add(1);
    apiDuration.add(res.timings.duration);
  });

  sleep(0.5);

  group("Maintenance - Work Orders", () => {
    const res = http.get(`${API_PREFIX}/maintenance/work-orders?page=1&page_size=20`, params);
    check(res, {
      "work orders status 200": (r) => r.status === 200,
    }) || errorRate.add(1);
    apiDuration.add(res.timings.duration);
  });

  sleep(0.5);

  group("Production - Schedules", () => {
    const res = http.get(`${API_PREFIX}/production/schedules`, params);
    check(res, {
      "schedules status 200 or 404": (r) => r.status === 200 || r.status === 404,
    }) || errorRate.add(1);
    apiDuration.add(res.timings.duration);
  });

  sleep(0.5);

  group("AI - Search", () => {
    const res = http.post(
      `${API_PREFIX}/search`,
      JSON.stringify({ query: "quality inspection procedures", limit: 10 }),
      params
    );
    check(res, {
      "search status 200": (r) => r.status === 200,
      "search response time < 2s": (r) => r.timings.duration < 2000,
    }) || errorRate.add(1);
    apiDuration.add(res.timings.duration);
  });

  sleep(1);
}

// ─── Teardown ────────────────────────────────────────────────────

export function teardown(data) {
  console.log("Load test complete.");
}
