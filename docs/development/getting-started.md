# Development Guide

Complete guide for developers working on the Sensei Manufacturing Management System.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Contributing](#contributing)

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Setup Local Environment

#### Backend Setup

```bash
# Clone repository
git clone https://github.com/sbelakho2/Management-Software.git
cd Management-Software

# Create virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your local settings

# Run database migrations
alembic upgrade head

# Create admin user
python -m sensei.cli.user create-admin \
  --email admin@local.dev \
  --password admin123

# Start development server
uvicorn sensei.main:app --reload --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your local settings

# Start development server
npm run dev
```

#### Database Setup

```bash
# Start PostgreSQL with Docker
docker run -d \
  --name sensei-postgres \
  -e POSTGRES_DB=sensei \
  -e POSTGRES_USER=sensei \
  -e POSTGRES_PASSWORD=sensei \
  -p 5432:5432 \
  pgvector/pgvector:pg15

# Or install locally and create database
createdb sensei
psql sensei -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

#### Redis Setup

```bash
# Start Redis with Docker
docker run -d \
  --name sensei-redis \
  -p 6379:6379 \
  redis:7-alpine

# Or install locally
sudo systemctl start redis
```

## Project Structure

```
Management-Software/
├── backend/
│   ├── alembic/              # Database migrations
│   ├── src/sensei/
│   │   ├── api/              # API endpoints
│   │   │   ├── v1/endpoints/ # API v1 endpoints
│   │   │   ├── deps.py       # Dependencies
│   │   │   ├── schemas.py    # Pydantic schemas
│   │   │   └── repository.py # Data access layer
│   │   ├── cli/              # CLI commands
│   │   ├── core/             # Core functionality
│   │   │   ├── auth.py       # Authentication
│   │   │   ├── config.py     # Configuration
│   │   │   ├── database.py   # Database connection
│   │   │   ├── redis.py      # Redis connection
│   │   │   ├── security.py   # Security utilities
│   │   │   └── storage.py    # File storage
│   │   ├── middleware/       # Custom middleware
│   │   ├── models/           # SQLAlchemy models
│   │   ├── services/         # Business logic
│   │   └── main.py           # FastAPI application
│   ├── tests/                # Test suite
│   └── pyproject.toml        # Python dependencies
│
├── frontend/
│   ├── e2e/                  # Playwright E2E tests
│   ├── public/               # Static assets
│   ├── src/
│   │   ├── api/              # API client
│   │   ├── app/              # Next.js pages
│   │   ├── components/       # React components
│   │   │   ├── ui/           # UI components
│   │   │   └── ...           # Feature components
│   │   ├── hooks/            # Custom React hooks
│   │   ├── lib/              # Utilities
│   │   ├── services/         # Business logic
│   │   ├── stores/           # State management
│   │   └── types/            # TypeScript types
│   ├── package.json          # Node dependencies
│   └── tsconfig.json         # TypeScript config
│
├── k8s/                      # Kubernetes manifests
│   └── helm/sensei/          # Helm chart
│
├── docs/                     # Documentation
│   ├── api/                  # API documentation
│   ├── architecture/         # Architecture docs
│   ├── deployment/           # Deployment guides
│   ├── development/          # Development guides
│   ├── guides/               # User guides
│   └── testing/              # Testing documentation
│
└── Development_Plan.md       # Project roadmap
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/add-supplier-portal
```

### 2. Make Changes

Follow [Coding Standards](#coding-standards) and write tests.

### 3. Run Tests

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=sensei

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

### 4. Lint and Format

```bash
# Backend
cd backend
ruff check src/
black src/
mypy src/

# Frontend
cd frontend
npm run lint
npm run format
```

### 5. Commit Changes

```bash
git add .
git commit -m "feat: add supplier portal API endpoints"
```

Commit message format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Build/tooling changes

### 6. Push and Create PR

```bash
git push origin feature/add-supplier-portal
```

Create pull request on GitHub with:
- Description of changes
- Related issue number
- Screenshots (if UI changes)
- Test coverage

## Coding Standards

### Python (Backend)

#### Style Guide

Follow PEP 8 and use Black formatter:

```python
# Good
def calculate_total_cost(
    base_price: Decimal,
    quantity: int,
    discount_percent: Decimal = Decimal("0")
) -> Decimal:
    """Calculate total cost with discount applied.
    
    Args:
        base_price: Unit price before discount
        quantity: Number of units
        discount_percent: Discount percentage (0-100)
        
    Returns:
        Total cost after discount
    """
    subtotal = base_price * quantity
    discount = subtotal * (discount_percent / 100)
    return subtotal - discount
```

#### Type Hints

Always use type hints:

```python
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

class Product(BaseModel):
    id: int
    name: str
    sku: str
    price: Decimal
    created_at: datetime
    tags: Optional[List[str]] = None
```

#### Error Handling

Use custom exceptions:

```python
from sensei.api.exceptions import NotFoundError, ValidationError

def get_product(product_id: int) -> Product:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError(f"Product {product_id} not found")
    return product
```

#### Async/Await

Use async for I/O operations:

```python
from sqlalchemy.ext.asyncio import AsyncSession

async def get_products(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[Product]:
    result = await session.execute(
        select(Product).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

### TypeScript (Frontend)

#### Style Guide

Use ESLint and Prettier:

```typescript
// Good
interface ProductProps {
  id: number;
  name: string;
  price: number;
  onSelect?: (id: number) => void;
}

export const ProductCard: React.FC<ProductProps> = ({
  id,
  name,
  price,
  onSelect,
}) => {
  const handleClick = () => {
    onSelect?.(id);
  };

  return (
    <Card onClick={handleClick}>
      <CardHeader>
        <CardTitle>{name}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-lg font-bold">${price.toFixed(2)}</p>
      </CardContent>
    </Card>
  );
};
```

#### Hooks Pattern

```typescript
// Custom hook
export const useProducts = (accountId?: number) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        const data = await api.products.list({ accountId });
        setProducts(data);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, [accountId]);

  return { products, loading, error };
};
```

#### State Management

Use Zustand for global state:

```typescript
import { create } from 'zustand';

interface AuthState {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  login: async (email, password) => {
    const { user, token } = await api.auth.login(email, password);
    set({ user, token });
  },
  logout: () => set({ user: null, token: null }),
}));
```

## Testing

### Backend Testing

#### Unit Tests

```python
import pytest
from sensei.services.quote_quality import QuoteQualityService

@pytest.fixture
def quality_service():
    return QuoteQualityService()

def test_calculate_quality_score(quality_service):
    # Arrange
    quote = {
        "completeness": 0.95,
        "accuracy": 0.90,
        "risk_level": "low"
    }
    
    # Act
    score = quality_service.calculate_score(quote)
    
    # Assert
    assert score >= 0.0
    assert score <= 1.0
    assert score > 0.85  # High completeness and accuracy
```

#### Integration Tests

```python
import pytest
from httpx import AsyncClient
from sensei.main import app

@pytest.mark.asyncio
async def test_create_product():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "Test Product",
                "sku": "TEST-001",
                "price": "99.99"
            },
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Product"
        assert "id" in data
```

### Frontend Testing

#### Component Tests

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { ProductCard } from './product-card';

describe('ProductCard', () => {
  it('renders product information', () => {
    render(
      <ProductCard
        id={1}
        name="Test Product"
        price={99.99}
      />
    );

    expect(screen.getByText('Test Product')).toBeInTheDocument();
    expect(screen.getByText('$99.99')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const handleSelect = jest.fn();
    render(
      <ProductCard
        id={1}
        name="Test Product"
        price={99.99}
        onSelect={handleSelect}
      />
    );

    fireEvent.click(screen.getByText('Test Product'));
    expect(handleSelect).toHaveBeenCalledWith(1);
  });
});
```

#### E2E Tests

```typescript
import { test, expect } from '@playwright/test';

test('create new product', async ({ page }) => {
  // Login
  await page.goto('/login');
  await page.fill('[name="email"]', 'admin@test.com');
  await page.fill('[name="password"]', 'admin123');
  await page.click('button[type="submit"]');

  // Navigate to products
  await page.goto('/products');
  await page.click('text=New Product');

  // Fill form
  await page.fill('[name="name"]', 'Test Product');
  await page.fill('[name="sku"]', 'TEST-001');
  await page.fill('[name="price"]', '99.99');

  // Submit
  await page.click('button:has-text("Create")');

  // Verify
  await expect(page.locator('text=Test Product')).toBeVisible();
});
```

## Debugging

### Backend Debugging

#### VSCode Launch Configuration

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: FastAPI",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "sensei.main:app",
        "--reload",
        "--port",
        "8000"
      ],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

#### Logging

```python
import logging

logger = logging.getLogger(__name__)

def process_order(order_id: int):
    logger.info(f"Processing order {order_id}")
    try:
        # Process order
        logger.debug(f"Order details: {order}")
    except Exception as e:
        logger.error(f"Failed to process order {order_id}: {e}", exc_info=True)
        raise
```

### Frontend Debugging

#### React DevTools

Install browser extension:
- [Chrome](https://chrome.google.com/webstore/detail/react-developer-tools)
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/react-devtools/)

#### Console Debugging

```typescript
// Use console.log sparingly, prefer debugger
const handleSubmit = async (data: FormData) => {
  console.log('Form data:', data);  // Remove before commit
  debugger;  // Breakpoint for DevTools
  
  const result = await api.submit(data);
  console.log('Result:', result);  // Remove before commit
};
```

#### Network Tab

Use browser DevTools Network tab to inspect API calls:
1. Open DevTools (F12)
2. Go to Network tab
3. Filter by XHR/Fetch
4. Click on request to see headers, payload, response

## Contributing

### Pull Request Process

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Run full test suite
5. Update documentation
6. Submit pull request
7. Address review comments
8. Merge after approval

### Code Review Guidelines

Reviewers check for:
- [ ] Tests pass
- [ ] Code follows style guide
- [ ] No security vulnerabilities
- [ ] Performance considerations
- [ ] Documentation updated
- [ ] Breaking changes noted

### Release Process

1. Update version in `pyproject.toml` and `package.json`
2. Update CHANGELOG.md
3. Create release branch: `release/v1.2.0`
4. Test release candidate
5. Merge to main
6. Tag release: `git tag v1.2.0`
7. Deploy to production

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Playwright Documentation](https://playwright.dev/)

## Getting Help

- **Slack**: #sensei-dev
- **Email**: dev-team@sensei.com
- **Issues**: https://github.com/yourorg/Management-Software/issues
