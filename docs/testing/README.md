# Testing Guide Index

Comprehensive testing documentation for Starz Morocco Manufacturing Management System.

## 📋 Testing Overview

### Test Types

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between components
- **E2E Tests**: Test complete user workflows
- **API Tests**: Test API endpoints and responses
- **Component Tests**: Test UI components
- **Performance Tests**: Test system performance under load

### Test Coverage

**Current Coverage**:
- Backend: 359 tests across 78 files
- Frontend: 165 Jest tests + 22 Playwright E2E tests
- **Total**: 546+ tests

**Coverage Goals**:
- Unit test coverage: >80%
- Integration test coverage: >70%
- Critical path E2E coverage: 100%

## 🧪 Backend Testing

### Running Tests

```bash
# Run all tests
cd backend
pytest tests/ -v

# Run specific test file
pytest tests/api/test_quotes.py -v

# Run specific test
pytest tests/api/test_quotes.py::test_create_quote -v

# Run with coverage
pytest tests/ --cov=sensei --cov-report=html

# Run in parallel (faster)
pytest tests/ -n auto
```

### Test Structure

```
tests/
├── __init__.py
├── conftest.py          # Shared fixtures
├── api/                 # API endpoint tests
│   ├── test_auth.py
│   ├── test_quotes.py
│   ├── test_rfqs.py
│   └── v1/
├── core/                # Core functionality tests
│   ├── test_auth.py
│   ├── test_config.py
│   └── test_security.py
├── middleware/          # Middleware tests
│   └── test_middleware.py
├── models/              # Model tests
│   ├── test_account.py
│   ├── test_quote.py
│   └── test_user.py
└── services/            # Service layer tests
    ├── test_quote_service.py
    └── test_rfq_service.py
```

### Writing Unit Tests

**Example - Model Test**:

```python
# tests/models/test_quote.py
import pytest
from sensei.models.quote import Quote, QuoteStatus

def test_quote_creation():
    """Test creating a quote."""
    quote = Quote(
        account_id=1,
        rfq_id=1,
        total_amount=10000.00,
        status=QuoteStatus.DRAFT
    )
    assert quote.account_id == 1
    assert quote.status == QuoteStatus.DRAFT
    assert quote.total_amount == 10000.00

def test_quote_status_transition():
    """Test quote status transitions."""
    quote = Quote(account_id=1, status=QuoteStatus.DRAFT)
    
    # Valid transition
    quote.status = QuoteStatus.PENDING_APPROVAL
    assert quote.status == QuoteStatus.PENDING_APPROVAL
    
    # Invalid transition should raise error
    with pytest.raises(ValueError):
        quote.status = QuoteStatus.APPROVED  # Skipping approval step
```

### Writing Integration Tests

**Example - API Test**:

```python
# tests/api/test_quotes.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_quote(client: AsyncClient, admin_token):
    """Test creating a new quote via API."""
    response = await client.post(
        "/api/v1/quotes",
        json={
            "account_id": 1,
            "rfq_id": 1,
            "items": [
                {
                    "product_id": 1,
                    "quantity": 10,
                    "unit_price": 100.00
                }
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["account_id"] == 1
    assert len(data["items"]) == 1
    assert data["total_amount"] == 1000.00

@pytest.mark.asyncio
async def test_create_quote_unauthorized(client: AsyncClient):
    """Test creating quote without authentication fails."""
    response = await client.post(
        "/api/v1/quotes",
        json={"account_id": 1}
    )
    assert response.status_code == 401
```

### Common Fixtures

Located in `tests/conftest.py`:

```python
@pytest.fixture
async def db_session():
    """Provide a database session for testing."""
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client(db_session):
    """Provide an HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("password"),
        role=Role.ADMIN
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def admin_token(admin_user):
    """Generate JWT token for admin user."""
    return create_access_token({"sub": admin_user.email})
```

### Test Best Practices

**DO**:
- ✅ Use descriptive test names
- ✅ Follow AAA pattern (Arrange, Act, Assert)
- ✅ Test one thing per test
- ✅ Use fixtures for setup
- ✅ Mock external dependencies
- ✅ Test edge cases and error conditions
- ✅ Keep tests fast

**DON'T**:
- ❌ Test implementation details
- ❌ Make tests depend on each other
- ❌ Use sleep() for timing
- ❌ Hit real external APIs
- ❌ Hardcode environment-specific values
- ❌ Ignore failing tests

### Running Specific Test Categories

```bash
# Run only unit tests
pytest tests/models/ tests/services/ -v

# Run only API tests
pytest tests/api/ -v

# Run tests matching pattern
pytest -k "quote" -v

# Run failed tests from last run
pytest --lf

# Stop on first failure
pytest -x

# Show print statements
pytest -s
```

## 🎭 Frontend Testing

### Running Tests

```bash
# Run all tests
cd frontend
npm test

# Run in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test -- QuoteCard.test.tsx

# Update snapshots
npm test -- -u
```

### Test Structure

```
frontend/
├── src/
│   └── components/
│       ├── QuoteCard.tsx
│       └── QuoteCard.test.tsx
├── e2e/
│   ├── login.spec.ts
│   ├── navigation.spec.ts
│   └── gm-day1-flow.spec.ts
└── jest.config.js
```

### Writing Component Tests

**Example - Component Test**:

```typescript
// src/components/QuoteCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { QuoteCard } from './QuoteCard';

describe('QuoteCard', () => {
  const mockQuote = {
    id: 1,
    accountId: 1,
    accountName: 'Acme Corp',
    status: 'draft',
    totalAmount: 10000.00,
    items: [],
  };

  it('renders quote information', () => {
    render(<QuoteCard quote={mockQuote} />);
    
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('$10,000.00')).toBeInTheDocument();
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  it('calls onEdit when edit button clicked', () => {
    const onEdit = jest.fn();
    render(<QuoteCard quote={mockQuote} onEdit={onEdit} />);
    
    fireEvent.click(screen.getByText('Edit'));
    expect(onEdit).toHaveBeenCalledWith(1);
  });

  it('shows approve button only for approved role', () => {
    render(<QuoteCard quote={mockQuote} canApprove={true} />);
    
    expect(screen.getByText('Approve')).toBeInTheDocument();
  });

  it('does not show approve button for non-approved role', () => {
    render(<QuoteCard quote={mockQuote} canApprove={false} />);
    
    expect(screen.queryByText('Approve')).not.toBeInTheDocument();
  });
});
```

### Testing Custom Hooks

```typescript
// src/hooks/useQuotes.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useQuotes } from './useQuotes';

describe('useQuotes', () => {
  it('fetches quotes on mount', async () => {
    const { result } = renderHook(() => useQuotes());
    
    expect(result.current.isLoading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
    
    expect(result.current.quotes).toHaveLength(3);
  });

  it('handles errors', async () => {
    // Mock API to return error
    jest.spyOn(api, 'getQuotes').mockRejectedValue(new Error('API Error'));
    
    const { result } = renderHook(() => useQuotes());
    
    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });
  });
});
```

## 🎪 E2E Testing

For complete E2E testing documentation, see [E2E Testing Guide](./e2e-testing.md).

### Running E2E Tests

```bash
cd frontend

# Run all E2E tests
npm run test:e2e

# Run in headed mode (see browser)
npm run test:e2e -- --headed

# Run specific test
npm run test:e2e -- login.spec.ts

# Debug mode
npm run test:e2e -- --debug
```

### Writing E2E Tests

**Example - E2E Test**:

```typescript
// e2e/quotes.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Quote Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[name="email"]', 'test@example.com');
    await page.fill('[name="password"]', 'password');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('create new quote', async ({ page }) => {
    // Navigate to quotes
    await page.click('text=Quotes');
    await expect(page).toHaveURL('/quotes');
    
    // Click new quote button
    await page.click('text=New Quote');
    
    // Fill form
    await page.selectOption('[name="accountId"]', '1');
    await page.fill('[name="items[0].quantity"]', '10');
    await page.fill('[name="items[0].unitPrice"]', '100');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Verify success
    await expect(page.locator('.toast')).toContainText('Quote created');
    await expect(page).toHaveURL(/\/quotes\/\d+/);
  });

  test('approve quote workflow', async ({ page }) => {
    // Create quote first
    // ... (setup code)
    
    // Submit for approval
    await page.click('text=Submit for Approval');
    await expect(page.locator('.status')).toContainText('Pending Approval');
    
    // Approve (as manager)
    await page.click('text=Approve');
    await page.fill('[name="approvalNotes"]', 'Looks good');
    await page.click('button:has-text("Confirm Approval")');
    
    // Verify approved
    await expect(page.locator('.status')).toContainText('Approved');
  });
});
```

## 📊 Test Coverage

### Viewing Coverage Reports

```bash
# Backend coverage
cd backend
pytest tests/ --cov=sensei --cov-report=html
open htmlcov/index.html

# Frontend coverage
cd frontend
npm test -- --coverage
open coverage/lcov-report/index.html
```

### Coverage Goals

**Minimum Coverage**:
- New code: 80% coverage required
- Critical paths: 100% coverage required
- Bug fixes: Add test that would have caught the bug

**Measuring Coverage**:
- Line coverage: % of lines executed
- Branch coverage: % of branches taken
- Function coverage: % of functions called

## 🔄 Continuous Integration

### GitHub Actions

Located in `.github/workflows/test.yml`:

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -e ".[dev]"
      - name: Run tests
        run: |
          cd backend
          pytest tests/ --cov=sensei --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm install
      - name: Run tests
        run: |
          cd frontend
          npm test -- --coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install Playwright
        run: |
          cd frontend
          npx playwright install --with-deps
      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e
      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

## 🐛 Debugging Tests

### Backend Debugging

```bash
# Run with debugger
pytest tests/api/test_quotes.py::test_create_quote --pdb

# Show print statements
pytest tests/ -s

# Increase verbosity
pytest tests/ -vv

# Show locals on failure
pytest tests/ -l
```

### Frontend Debugging

```typescript
// Add debugger statement
test('my test', () => {
  debugger;  // Execution will pause here
  // ... rest of test
});

// Run in debug mode
npm test -- --debug

// Use console.log
test('my test', () => {
  console.log('Current state:', state);
  // ... assertions
});
```

### E2E Debugging

```bash
# Run in headed mode
npm run test:e2e -- --headed

# Debug mode (pause execution)
npm run test:e2e -- --debug

# Screenshot on failure (automatic)
# Videos saved to test-results/
```

## 📚 Additional Resources

- [E2E Testing Guide](./e2e-testing.md) - Detailed Playwright guide
- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright Documentation](https://playwright.dev/)

---

**Questions about testing?** Open an issue or contact contact@starzmorocco.com
