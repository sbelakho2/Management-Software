# Performance Load Testing

This directory contains k6 load testing scripts for the Sensei application.

## Overview

Load tests validate system performance under realistic concurrent user loads:

- **Today Screen**: 10-100 concurrent users, P95 < 2s
- **Search API**: 20-200 concurrent users, P95 < 500ms
- **Concurrent Approvals**: 15-50 concurrent users, optimistic locking validation

## Prerequisites

1. **Install k6**:
   ```bash
   # macOS
   brew install k6

   # Linux (Debian/Ubuntu)
   sudo gpg -k
   sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
   echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
   sudo apt-get update
   sudo apt-get install k6

   # Windows (Chocolatey)
   choco install k6
   ```

2. **Ensure backend is running**:
   ```bash
   cd backend
   uvicorn sensei.main:app --reload
   ```

3. **Prepare test data**:
   - Run database migrations
   - Seed test users and data (see `tests/fixtures/`)

## Running Tests

### Today Screen Load Test

Tests the main Today screen endpoint with realistic user load:

```bash
# Run with default settings (localhost:8000)
k6 run load_test_today_screen.js

# Run with custom base URL
k6 run load_test_today_screen.js -e BASE_URL=https://staging.sensei.app

# Run with custom duration (shorter for quick validation)
k6 run load_test_today_screen.js --duration 2m --vus 10

# Run with results output to JSON
k6 run load_test_today_screen.js --out json=results_today_screen.json
```

**Expected Results**:
- P95 response time < 2 seconds
- Error rate < 1%
- Successful load with 100 concurrent users

### Search API Load Test

Tests full-text search performance:

```bash
# Run with default settings
k6 run load_test_search.js

# Run with custom base URL
k6 run load_test_search.js -e BASE_URL=https://staging.sensei.app

# Run with custom test user
k6 run load_test_search.js -e TEST_USER_EMAIL=test@example.com -e TEST_USER_PASSWORD=password123
```

**Expected Results**:
- P95 response time < 500ms
- Error rate < 1%
- Successful load with 200 concurrent users

### Concurrent Approvals Load Test

Tests approval workflow with concurrent users (validates optimistic locking):

```bash
# Run with default settings
k6 run load_test_concurrent_approvals.js

# Run with custom base URL
k6 run load_test_concurrent_approvals.js -e BASE_URL=https://staging.sensei.app
```

**Expected Results**:
- P95 response time < 2 seconds
- Some conflicts expected (optimistic locking working correctly)
- Error rate < 5% (excluding expected conflicts)

## Test Scenarios

### Normal Load
Simulates typical daily usage:
- 10-20 concurrent users
- 5 minutes duration
- Think time between actions (realistic user behavior)

### Peak Load
Simulates busy periods (shift changes, end of day):
- 50-100 concurrent users
- 2-3 minutes duration
- Validates system handles traffic spikes

### Stress Test
Identifies system breaking point:
- Ramp up to 100-200+ concurrent users
- Monitors error rates and response times
- Helps plan capacity

## Interpreting Results

k6 outputs comprehensive metrics:

```
     ✓ status is 200
     ✓ response time < 2s

     checks.........................: 98.50%  ✓ 1970      ✗ 30
     data_received..................: 5.2 MB  43 kB/s
     data_sent......................: 890 kB  7.4 kB/s
     http_req_blocked...............: avg=1.2ms    min=0s       med=1ms     max=50ms
     http_req_connecting............: avg=800µs    min=0s       med=700µs   max=30ms
     http_req_duration..............: avg=1.5s     min=200ms    med=1.2s    max=4s
       { expected_response:true }...: avg=1.5s     min=200ms    med=1.2s    max=4s
     http_req_failed................: 0.50%   ✗ 10        ✓ 1990
     http_req_receiving.............: avg=50ms     min=10ms     med=40ms    max=200ms
     http_req_sending...............: avg=5ms      min=1ms      med=4ms     max=20ms
     http_req_tls_handshaking.......: avg=0s       min=0s       med=0s      max=0s
     http_req_waiting...............: avg=1.4s     min=180ms    med=1.1s    max=3.8s
     http_reqs......................: 2000    16.67/s
     iteration_duration.............: avg=8.5s     min=6s       med=8s      max=15s
     iterations.....................: 400     3.33/s
     vus............................: 10      min=10      max=100
     vus_max........................: 100     min=100     max=100
```

**Key Metrics**:
- `http_req_duration`: Response time (P95 is critical)
- `http_req_failed`: Error rate (should be < 1%)
- `checks`: Validation pass rate (should be > 95%)
- Custom metrics: `*_errors`, `*_slow_responses`

## Performance Gates

Tests enforce these performance gates:

| Endpoint | P95 Response Time | Error Rate |
|----------|------------------|------------|
| Today Screen | < 2 seconds | < 1% |
| Search API | < 500ms | < 1% |
| Approvals | < 2 seconds | < 5% (with conflicts) |

**If tests fail**:
1. Check database query performance (add indexes)
2. Enable query caching (Redis)
3. Optimize serialization (pagination, field selection)
4. Scale horizontally (more workers)

## Continuous Monitoring

Integrate load tests into CI/CD:

```yaml
# .github/workflows/load-test.yml
name: Load Tests
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install k6
        run: |
          sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
          echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
          sudo apt-get update
          sudo apt-get install k6
      - name: Run Load Tests
        run: |
          k6 run backend/tests/performance/load_test_today_screen.js
          k6 run backend/tests/performance/load_test_search.js
```

## Cloud Load Testing

For distributed load testing from multiple regions:

```bash
# k6 Cloud (requires account)
k6 cloud load_test_today_screen.js

# Or use AWS/GCP to run k6 from multiple regions
```

## Troubleshooting

**Test fails immediately**:
- Check backend is running
- Verify BASE_URL is correct
- Ensure test users exist in database

**High error rates**:
- Check database connections (max pool size)
- Review application logs for errors
- Verify rate limiting is not triggered

**Slow response times**:
- Enable SQL query logging
- Check for N+1 queries
- Review database indexes
- Monitor CPU/memory usage

## Further Reading

- [k6 Documentation](https://k6.io/docs/)
- [Load Testing Best Practices](https://k6.io/docs/testing-guides/api-load-testing/)
- [Performance Testing Guide](https://k6.io/docs/test-types/load-testing/)
