# Contributing to Starz Morocco Manufacturing Management System

Thank you for your interest in contributing to the Starz Morocco Management Software! This document provides guidelines and instructions for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## 📜 Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have:

- Python 3.11 or higher
- Node.js 18 or higher
- PostgreSQL 15 or higher with pgvector extension
- Redis 7 or higher
- Docker and Docker Compose (optional, for containerized development)
- Git

### Setup Development Environment

1. **Fork the repository** on GitHub

2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Management-Software.git
   cd Management-Software
   ```

3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/sbelakho2/Management-Software.git
   ```

4. **Set up the backend**:
   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```

5. **Set up the database**:
   ```bash
   # Start PostgreSQL (Docker)
   docker run -d \
     --name sensei-postgres \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=sensei \
     -p 5432:5432 \
     ankane/pgvector
   
   # Run migrations
   alembic upgrade head
   
   # Create admin user
   python -m sensei.cli.user create-admin \
     --email admin@local.dev \
     --password admin123
   ```

6. **Set up the frontend**:
   ```bash
   cd ../frontend
   npm install
   
   # Create .env.local
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

7. **Verify setup**:
   ```bash
   # Terminal 1: Start backend
   cd backend
   uvicorn sensei.main:app --reload
   
   # Terminal 2: Start frontend
   cd frontend
   npm run dev
   
   # Terminal 3: Run tests
   cd backend
   pytest tests/ -v
   ```

See [Development Guide](./docs/development/getting-started.md) for detailed instructions.

## 🔄 Development Workflow

### 1. Stay Synchronized

Before starting work, sync with upstream:

```bash
git checkout main
git fetch upstream
git merge upstream/main
git push origin main
```

### 2. Create a Branch

Create a descriptive branch for your work:

```bash
# Feature branch
git checkout -b feature/add-supplier-portal

# Bug fix branch
git checkout -b fix/quote-calculation-error

# Documentation branch
git checkout -b docs/update-api-guide
```

**Branch naming convention**:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Adding or updating tests
- `chore/` - Maintenance tasks

### 3. Make Changes

- Write clean, readable code
- Follow coding standards (see below)
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 4. Test Your Changes

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=sensei

# Frontend tests
cd frontend
npm test

# Linting
cd backend
ruff check src/
black src/ --check
mypy src/

cd frontend
npm run lint

# E2E tests (optional)
cd frontend
npm run test:e2e
```

### 5. Commit Your Changes

Follow [commit message guidelines](#commit-message-guidelines):

```bash
git add .
git commit -m "feat: add supplier portal dashboard"
```

### 6. Push and Create Pull Request

```bash
git push origin feature/add-supplier-portal
```

Then create a Pull Request on GitHub.

## 📝 Coding Standards

### Python (Backend)

**Style Guide**: Follow PEP 8 with these tools:

- **Black**: Code formatting (line length: 100)
- **Ruff**: Fast linting
- **MyPy**: Type checking
- **isort**: Import sorting

**Configuration**:

```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/

# Sort imports
isort src/ tests/
```

**Best Practices**:

```python
# ✅ Good
from typing import List, Optional
from pydantic import BaseModel

class QuoteCreate(BaseModel):
    """Schema for creating a new quote."""
    
    account_id: int
    rfq_id: Optional[int] = None
    items: List[QuoteItemCreate]
    
    async def validate_account(self, db: AsyncSession) -> None:
        """Validate that the account exists."""
        account = await db.get(Account, self.account_id)
        if not account:
            raise ValueError(f"Account {self.account_id} not found")

# ❌ Bad
class QuoteCreate(BaseModel):
    account_id = None  # No type hints
    rfq_id = None
    items = []  # Mutable default
```

**Key Rules**:
- Always use type hints
- Write docstrings for public functions/classes
- Use async/await for I/O operations
- Handle exceptions explicitly
- Log important events
- No mutable default arguments
- Prefer composition over inheritance

### TypeScript (Frontend)

**Style Guide**: ESLint + Prettier

**Configuration**:

```bash
# Lint code
npm run lint

# Format code
npm run format

# Type check
npm run type-check
```

**Best Practices**:

```typescript
// ✅ Good
interface Quote {
  id: number;
  accountId: number;
  status: 'draft' | 'pending' | 'approved';
  items: QuoteItem[];
}

export const QuoteCard: React.FC<{ quote: Quote }> = ({ quote }) => {
  const { mutate: updateQuote, isLoading } = useUpdateQuote();
  
  const handleApprove = useCallback(() => {
    updateQuote({ id: quote.id, status: 'approved' });
  }, [quote.id, updateQuote]);
  
  return (
    <Card>
      <CardHeader>
        <CardTitle>Quote #{quote.id}</CardTitle>
      </CardHeader>
      <CardContent>
        <Button onClick={handleApprove} disabled={isLoading}>
          Approve
        </Button>
      </CardContent>
    </Card>
  );
};

// ❌ Bad
export const QuoteCard = (props: any) => {  // No type safety
  const handleApprove = () => {  // Missing dependencies
    fetch(`/api/quotes/${props.quote.id}`, {  // Direct fetch
      method: 'PATCH',
      body: JSON.stringify({ status: 'approved' })
    });
  };
  
  return <div>...</div>;  // Missing accessibility
};
```

**Key Rules**:
- Always use TypeScript (no `.js` files)
- Define interfaces for all data structures
- Use React hooks properly (useCallback, useMemo)
- Prefer functional components
- Use React Query for data fetching
- Implement proper error boundaries
- Add accessibility attributes (ARIA)
- Use semantic HTML

## 🧪 Testing Requirements

All contributions must include appropriate tests.

### Backend Testing

**Required**:
- Unit tests for services and utilities
- Integration tests for API endpoints
- Minimum 80% code coverage for new code

**Example**:

```python
# tests/services/test_quote_service.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_quote(client: AsyncClient, db_session, admin_token):
    """Test creating a new quote."""
    response = await client.post(
        "/api/v1/quotes",
        json={
            "account_id": 1,
            "items": [{"product_id": 1, "quantity": 10}]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["account_id"] == 1
    assert len(data["items"]) == 1
```

### Frontend Testing

**Required**:
- Component tests for UI components
- Integration tests for complex interactions
- E2E tests for critical user flows

**Example**:

```typescript
// src/components/QuoteCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { QuoteCard } from './QuoteCard';

describe('QuoteCard', () => {
  it('displays quote information', () => {
    const quote = { id: 1, accountId: 1, status: 'draft', items: [] };
    render(<QuoteCard quote={quote} />);
    
    expect(screen.getByText('Quote #1')).toBeInTheDocument();
  });
  
  it('calls onApprove when approve button clicked', () => {
    const quote = { id: 1, accountId: 1, status: 'draft', items: [] };
    const onApprove = jest.fn();
    render(<QuoteCard quote={quote} onApprove={onApprove} />);
    
    fireEvent.click(screen.getByText('Approve'));
    expect(onApprove).toHaveBeenCalledWith(1);
  });
});
```

### Test Guidelines

- **Descriptive names**: `test_create_quote_with_invalid_account_fails`
- **AAA pattern**: Arrange, Act, Assert
- **One assertion per test**: Test one thing at a time
- **Use fixtures**: Share setup code
- **Mock external services**: Don't hit real APIs
- **Test edge cases**: Null values, empty lists, errors

## 🔀 Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] Commits follow message guidelines
- [ ] Branch is up to date with main

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Breaking change (fix or feature that causes existing functionality to change)
- [ ] Documentation update

## How Has This Been Tested?
Describe the tests you ran

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Code commented where necessary
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests added and passing
- [ ] Dependent changes merged

## Screenshots (if applicable)
Add screenshots for UI changes

## Related Issues
Closes #123
```

### Review Process

1. **Automated Checks**: CI runs tests, linting, type checking
2. **Code Review**: At least one maintainer reviews
3. **Feedback**: Address review comments
4. **Approval**: Maintainer approves PR
5. **Merge**: Maintainer merges to main

### After Merge

- Delete your branch (optional)
- Sync your fork with upstream
- Close related issues

## 💬 Commit Message Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, missing semicolons)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks (dependencies, build)
- `perf`: Performance improvements
- `ci`: CI/CD changes

### Scope (Optional)

- `api`: API changes
- `ui`: UI changes
- `db`: Database changes
- `auth`: Authentication changes
- `quote`: Quote module
- `rfq`: RFQ module

### Examples

```bash
# Simple feature
git commit -m "feat: add supplier portal dashboard"

# Bug fix with scope
git commit -m "fix(quote): correct total calculation for multi-item quotes"

# Breaking change
git commit -m "feat(api)!: change quote API response format

BREAKING CHANGE: Quote API now returns items as array instead of object"

# Multiple changes
git commit -m "chore: update dependencies

- Update FastAPI to 0.104.1
- Update Next.js to 14.0.4
- Update SQLAlchemy to 2.0.23"
```

## 📚 Documentation

Documentation is as important as code. Please update documentation when:

- Adding new features
- Changing existing behavior
- Fixing bugs (if relevant)
- Updating dependencies

### Documentation Locations

- **API docs**: `docs/api/`
- **Architecture**: `docs/architecture/`
- **Deployment**: `docs/deployment/`
- **Development**: `docs/development/`
- **User guides**: `docs/guides/`

### Documentation Standards

- Use clear, concise language
- Include code examples
- Add screenshots for UI features
- Update table of contents
- Cross-link related documentation
- Keep formatting consistent

## 🤝 Community

### Getting Help

- **Documentation**: Check [docs/](./docs/)
- **Issues**: Search [existing issues](https://github.com/sbelakho2/Management-Software/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/sbelakho2/Management-Software/discussions)
- **Email**: contact@starzmorocco.com

### Reporting Bugs

Create an issue with:

- Clear title
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)
- Screenshots (if applicable)
- Error logs

### Suggesting Features

Create an issue with:

- Clear title
- Problem description
- Proposed solution
- Alternative solutions
- Additional context

### Questions

- Check documentation first
- Search existing issues
- Ask in GitHub Discussions
- Join Slack community

## 🏆 Recognition

Contributors are recognized in:

- README.md contributors section
- Release notes
- Project website

Significant contributions may result in:

- Maintainer status
- Direct repository access
- Speaking opportunities

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 🙏 Thank You

Thank you for contributing to Starz Morocco Management Software! Your efforts help make this project better for everyone.

---

**Questions?** Open an issue or reach out to contact@starzmorocco.com
