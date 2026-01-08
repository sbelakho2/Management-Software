import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

/**
 * Load Test: Today Screen API
 * 
 * Simulates realistic load on the Today screen endpoint with:
 * - Authenticated users
 * - Realistic data volume (50 commitments, 20 risks, 10 approvals)
 * - Performance target: P95 < 2 seconds
 * 
 * Test Scenarios:
 * 1. Normal Load: 10 VUs for 5 minutes
 * 2. Peak Load: 50 VUs for 2 minutes
 * 3. Stress Test: Ramp to 100 VUs
 */

// Custom metrics
const todayScreenErrors = new Rate('today_screen_errors');
const todayScreenSlow = new Rate('today_screen_slow_responses');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 10 },   // Stay at 10 users (normal load)
    { duration: '2m', target: 50 },   // Spike to 50 users (peak load)
    { duration: '3m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Stress test: ramp to 100 users
    { duration: '1m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% of requests must be < 2s
    http_req_failed: ['rate<0.01'],     // Error rate must be < 1%
    today_screen_errors: ['rate<0.01'],
    today_screen_slow_responses: ['rate<0.05'], // < 5% slow responses
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_VERSION = 'v1';

// Test users (would come from environment or setup script)
const TEST_USERS = [
  { email: 'gm@sensei.test', password: 'Test123!@#' },
  { email: 'engineer1@sensei.test', password: 'Test123!@#' },
  { email: 'engineer2@sensei.test', password: 'Test123!@#' },
  { email: 'supervisor@sensei.test', password: 'Test123!@#' },
  { email: 'qa@sensei.test', password: 'Test123!@#' },
];

/**
 * Login and get access token
 */
function login(user) {
  const loginRes = http.post(`${BASE_URL}/api/${API_VERSION}/auth/login`, JSON.stringify({
    email: user.email,
    password: user.password,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(loginRes, {
    'login successful': (r) => r.status === 200,
    'token received': (r) => r.json('access_token') !== undefined,
  });

  if (loginRes.status !== 200) {
    console.error(`Login failed for ${user.email}: ${loginRes.body}`);
    return null;
  }

  return loginRes.json('access_token');
}

/**
 * Fetch Today screen data
 */
function fetchTodayScreen(token) {
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const startTime = new Date();
  const res = http.get(`${BASE_URL}/api/${API_VERSION}/today`, { headers });
  const duration = new Date() - startTime;

  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 2s': (r) => r.timings.duration < 2000,
    'response time < 3s': (r) => r.timings.duration < 3000,
    'has commitments': (r) => r.json('commitments') !== undefined,
    'has risks': (r) => r.json('risks') !== undefined,
    'has approvals': (r) => r.json('pending_approvals') !== undefined,
    'has metrics': (r) => r.json('quick_metrics') !== undefined,
  });

  // Track slow responses
  if (res.timings.duration > 2000) {
    todayScreenSlow.add(1);
    console.warn(`Slow response: ${res.timings.duration}ms`);
  } else {
    todayScreenSlow.add(0);
  }

  // Track errors
  if (!success || res.status !== 200) {
    todayScreenErrors.add(1);
  } else {
    todayScreenErrors.add(0);
  }

  return res;
}

/**
 * Fetch individual commitment details (simulates user clicking)
 */
function fetchCommitmentDetails(token, commitmentId) {
  const headers = {
    'Authorization': `Bearer ${token}`,
  };

  const res = http.get(`${BASE_URL}/api/${API_VERSION}/commitments/${commitmentId}`, { headers });

  check(res, {
    'commitment details fetched': (r) => r.status === 200,
  });

  return res;
}

/**
 * Main test scenario
 */
export default function () {
  // Select a random user
  const user = TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];

  // Login
  const token = login(user);
  if (!token) {
    return; // Skip this iteration if login failed
  }

  sleep(1); // Think time after login

  // Fetch Today screen
  const todayRes = fetchTodayScreen(token);

  sleep(2); // User reads the screen

  // If we got commitments, fetch details for the first one (simulate click)
  if (todayRes.status === 200) {
    try {
      const commitments = todayRes.json('commitments');
      if (commitments && commitments.length > 0) {
        const firstCommitmentId = commitments[0].id;
        fetchCommitmentDetails(token, firstCommitmentId);
        sleep(1); // User reads commitment details
      }
    } catch (e) {
      console.error('Error parsing commitments:', e);
    }
  }

  // Refresh Today screen (simulate user refreshing)
  fetchTodayScreen(token);

  sleep(3); // Think time before next iteration
}

/**
 * Setup: Run once at the start
 */
export function setup() {
  console.log('=== Today Screen Load Test Starting ===');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Test Users: ${TEST_USERS.length}`);
  console.log('Performance Target: P95 < 2 seconds');
  console.log('=====================================');
}

/**
 * Teardown: Run once at the end
 */
export function teardown(data) {
  console.log('=== Today Screen Load Test Complete ===');
}
