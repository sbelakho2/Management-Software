import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter } from 'k6/metrics';

/**
 * Load Test: Concurrent Approvals
 * 
 * Simulates realistic approval workflow load with:
 * - Multiple users approving/rejecting simultaneously
 * - Optimistic locking validation
 * - Audit trail creation
 * 
 * Test Scenarios:
 * 1. Normal Load: 15 VUs processing approvals
 * 2. Peak Load: 50 VUs (shift change scenario)
 * 3. Contention Test: Multiple users approving same item
 */

// Custom metrics
const approvalErrors = new Rate('approval_errors');
const approvalConflicts = new Counter('approval_conflicts');
const approvalSuccess = new Counter('approval_success');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 15 },   // Ramp up to 15 users
    { duration: '5m', target: 15 },   // Stay at 15 users (normal load)
    { duration: '2m', target: 50 },   // Spike to 50 users (shift change)
    { duration: '3m', target: 50 },   // Stay at 50 users
    { duration: '1m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% of requests must be < 2s
    http_req_failed: ['rate<0.02'],     // Error rate must be < 2% (allowing for conflicts)
    approval_errors: ['rate<0.05'],     // < 5% errors (excluding expected conflicts)
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_VERSION = 'v1';

// Test users (multiple approvers)
const APPROVERS = [
  { email: 'gm@sensei.test', password: 'Test123!@#', role: 'gm' },
  { email: 'supervisor1@sensei.test', password: 'Test123!@#', role: 'supervisor' },
  { email: 'supervisor2@sensei.test', password: 'Test123!@#', role: 'supervisor' },
  { email: 'engineer1@sensei.test', password: 'Test123!@#', role: 'engineer' },
  { email: 'engineer2@sensei.test', password: 'Test123!@#', role: 'engineer' },
];

const APPROVAL_DECISIONS = ['approved', 'rejected'];
const RATIONALE_TEMPLATES = [
  'Reviewed and approved based on technical merit.',
  'Rejected due to insufficient justification.',
  'Approved with minor concerns noted.',
  'Rejected pending additional analysis.',
  'Approved - aligns with quality standards.',
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
 * Fetch pending approvals
 */
function fetchPendingApprovals(token) {
  const headers = {
    'Authorization': `Bearer ${token}`,
  };

  const res = http.get(`${BASE_URL}/api/${API_VERSION}/approvals?status=pending`, { headers });

  check(res, {
    'approvals fetched': (r) => r.status === 200,
    'has approvals': (r) => r.json('items') !== undefined,
  });

  return res;
}

/**
 * Process approval (approve or reject)
 */
function processApproval(token, approvalId, decision, rationale) {
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  };

  const payload = JSON.stringify({
    decision: decision,
    rationale: rationale,
  });

  const res = http.put(`${BASE_URL}/api/${API_VERSION}/approvals/${approvalId}`, payload, { headers });

  const success = check(res, {
    'approval processed': (r) => r.status === 200 || r.status === 409,
    'response time < 2s': (r) => r.timings.duration < 2000,
  });

  if (res.status === 200) {
    approvalSuccess.add(1);
    approvalErrors.add(0);
  } else if (res.status === 409) {
    // Conflict - someone else approved it first (expected in high concurrency)
    approvalConflicts.add(1);
    approvalErrors.add(0);
    console.log(`Approval conflict for ID ${approvalId} (optimistic locking)`);
  } else {
    approvalErrors.add(1);
    console.error(`Approval error for ID ${approvalId}: ${res.status} - ${res.body}`);
  }

  return res;
}

/**
 * Fetch approval details
 */
function fetchApprovalDetails(token, approvalId) {
  const headers = {
    'Authorization': `Bearer ${token}`,
  };

  const res = http.get(`${BASE_URL}/api/${API_VERSION}/approvals/${approvalId}`, { headers });

  check(res, {
    'approval details fetched': (r) => r.status === 200,
    'has audit trail': (r) => r.json('audit_trail') !== undefined,
  });

  return res;
}

/**
 * Main test scenario
 */
export default function () {
  // Select a random approver
  const approver = APPROVERS[Math.floor(Math.random() * APPROVERS.length)];

  // Login
  const token = login(approver);
  if (!token) {
    return; // Skip this iteration if login failed
  }

  sleep(1); // Think time after login

  // Fetch pending approvals
  const approvalsRes = fetchPendingApprovals(token);

  if (approvalsRes.status !== 200) {
    return; // Skip if we can't fetch approvals
  }

  let approvals = [];
  try {
    approvals = approvalsRes.json('items') || [];
  } catch (e) {
    console.error('Error parsing approvals:', e);
    return;
  }

  if (approvals.length === 0) {
    console.log('No pending approvals available');
    sleep(5); // Wait before trying again
    return;
  }

  // Select a random approval to process
  const approval = approvals[Math.floor(Math.random() * approvals.length)];
  const approvalId = approval.id;

  // Fetch approval details (simulate user reading)
  fetchApprovalDetails(token, approvalId);

  sleep(2); // User reads approval details

  // Make a decision
  const decision = APPROVAL_DECISIONS[Math.floor(Math.random() * APPROVAL_DECISIONS.length)];
  const rationale = RATIONALE_TEMPLATES[Math.floor(Math.random() * RATIONALE_TEMPLATES.length)];

  // Process the approval
  processApproval(token, approvalId, decision, rationale);

  sleep(1); // Think time after processing

  // Fetch updated list (simulate user checking what's left)
  fetchPendingApprovals(token);

  sleep(3); // Think time before next iteration
}

/**
 * Setup: Run once at the start
 */
export function setup() {
  console.log('=== Concurrent Approvals Load Test Starting ===');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Approvers: ${APPROVERS.length}`);
  console.log('Performance Target: P95 < 2 seconds');
  console.log('Testing optimistic locking under concurrent load');
  console.log('===============================================');
}

/**
 * Teardown: Run once at the end
 */
export function teardown(data) {
  console.log('=== Concurrent Approvals Load Test Complete ===');
  console.log(`Successful Approvals: ${approvalSuccess.value || 0}`);
  console.log(`Conflicts (expected): ${approvalConflicts.value || 0}`);
}
