import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

/**
 * Load Test: Search API
 * 
 * Simulates realistic search load with:
 * - Full-text search across multiple entity types
 * - Realistic search terms (common keywords)
 * - Performance target: P95 < 500ms
 * 
 * Test Scenarios:
 * 1. Normal Load: 20 VUs for 5 minutes
 * 2. Peak Load: 100 VUs for 2 minutes
 * 3. Stress Test: Ramp to 200 VUs
 */

// Custom metrics
const searchErrors = new Rate('search_errors');
const searchSlow = new Rate('search_slow_responses');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 20 },   // Ramp up to 20 users
    { duration: '5m', target: 20 },   // Stay at 20 users (normal load)
    { duration: '2m', target: 100 },  // Spike to 100 users (peak load)
    { duration: '3m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 200 },  // Stress test: ramp to 200 users
    { duration: '1m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],   // 95% of requests must be < 500ms
    http_req_failed: ['rate<0.01'],     // Error rate must be < 1%
    search_errors: ['rate<0.01'],
    search_slow_responses: ['rate<0.10'], // < 10% slow responses (>500ms)
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_VERSION = 'v1';

// Test user
const TEST_USER = {
  email: __ENV.TEST_USER_EMAIL || 'gm@sensei.test',
  password: __ENV.TEST_USER_PASSWORD || 'Test123!@#',
};

// Realistic search terms (from automotive manufacturing context)
const SEARCH_TERMS = [
  'quality',
  'defect',
  'inspection',
  'assembly',
  'welding',
  'paint',
  'dashboard',
  'supplier',
  'kaizen',
  'andon',
  'poka-yoke',
  'jidoka',
  'heijunka',
  'takt time',
  'line balance',
  'first pass yield',
  'scrap rate',
  'downtime',
  'OEE',
  'safety',
  'ergonomics',
  'training',
  'standard work',
  'visual management',
  'problem solving',
];

// Entity types to search
const ENTITY_TYPES = [
  'commitments',
  'tasks',
  'approvals',
  'rfqs',
  'quotes',
  'lessons',
  'a3',
  'attachments',
];

let authToken = null;

/**
 * Login and get access token
 */
function login() {
  const loginRes = http.post(`${BASE_URL}/api/${API_VERSION}/auth/login`, JSON.stringify({
    email: TEST_USER.email,
    password: TEST_USER.password,
  }), {
    headers: { 'Content-Type': 'application/json' },
  });

  check(loginRes, {
    'login successful': (r) => r.status === 200,
    'token received': (r) => r.json('access_token') !== undefined,
  });

  if (loginRes.status !== 200) {
    console.error(`Login failed: ${loginRes.body}`);
    return null;
  }

  return loginRes.json('access_token');
}

/**
 * Perform search
 */
function performSearch(token, query, entityType = null) {
  const headers = {
    'Authorization': `Bearer ${token}`,
  };

  let url = `${BASE_URL}/api/${API_VERSION}/search?q=${encodeURIComponent(query)}`;
  if (entityType) {
    url += `&type=${entityType}`;
  }

  const startTime = new Date();
  const res = http.get(url, { headers });
  const duration = new Date() - startTime;

  const success = check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
    'response time < 1s': (r) => r.timings.duration < 1000,
    'has results': (r) => r.json('results') !== undefined,
    'has total count': (r) => r.json('total') !== undefined,
  });

  // Track slow responses (> 500ms)
  if (res.timings.duration > 500) {
    searchSlow.add(1);
    console.warn(`Slow search: "${query}" took ${res.timings.duration}ms`);
  } else {
    searchSlow.add(0);
  }

  // Track errors
  if (!success || res.status !== 200) {
    searchErrors.add(1);
  } else {
    searchErrors.add(0);
  }

  return res;
}

/**
 * Main test scenario
 */
export default function () {
  // Login if we don't have a token
  if (!authToken) {
    authToken = login();
    if (!authToken) {
      return; // Skip this iteration if login failed
    }
  }

  // Select a random search term
  const searchTerm = SEARCH_TERMS[Math.floor(Math.random() * SEARCH_TERMS.length)];

  // Perform global search (all entity types)
  performSearch(authToken, searchTerm);

  sleep(1); // User reads results

  // Perform filtered search (specific entity type)
  const entityType = ENTITY_TYPES[Math.floor(Math.random() * ENTITY_TYPES.length)];
  performSearch(authToken, searchTerm, entityType);

  sleep(2); // User reads filtered results

  // Perform another search with partial term (simulate typing)
  if (searchTerm.length > 3) {
    const partialTerm = searchTerm.substring(0, Math.floor(searchTerm.length / 2));
    performSearch(authToken, partialTerm);
  }

  sleep(2); // Think time before next search
}

/**
 * Setup: Run once at the start
 */
export function setup() {
  console.log('=== Search API Load Test Starting ===');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Search Terms: ${SEARCH_TERMS.length}`);
  console.log(`Entity Types: ${ENTITY_TYPES.length}`);
  console.log('Performance Target: P95 < 500ms');
  console.log('====================================');

  // Pre-login to get token
  const token = login();
  return { token };
}

/**
 * Teardown: Run once at the end
 */
export function teardown(data) {
  console.log('=== Search API Load Test Complete ===');
}
