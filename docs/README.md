# Starz Morocco Manufacturing Management System - Documentation

Complete documentation for developers, administrators, and end users.

## 📚 Documentation Structure

### For Developers

- **[Getting Started](./development/getting-started.md)** - Set up your development environment
- **[Architecture Overview](./architecture/README.md)** - System design and architecture
- **[API Reference](./api/README.md)** - Complete API documentation
- **[Testing Guide](./testing/e2e-testing.md)** - Write and run tests

### For DevOps/Administrators

- **[Deployment Guide](./deployment/DEPLOYMENT.md)** - Production deployment instructions
- **[Kubernetes Quick Start](./deployment/QUICKSTART.md)** - Local development with Minikube
- **[Hetzner Deployment](./deployment/HETZNER-DEPLOYMENT.md)** - Deploy on Hetzner Cloud
- **[Helm Chart](./deployment/helm-chart-readme.md)** - Helm chart configuration
-**[Helm Dependencies](./deployment/helm-dependencies.md)** - Managing chart dependencies

### For End Users

- **[User Guide](./guides/user-guide.md)** - How to use Sensei (coming soon)
- **[Admin Guide](./guides/admin-guide.md)** - System administration (coming soon)

## 🚀 Quick Links

### Most Common Tasks

**I want to...**

- **Start developing locally** → [Development Guide](./development/getting-started.md)
- **Deploy to production** → [Deployment Guide](./deployment/DEPLOYMENT.md)
- **Deploy on Hetzner** → [Hetzner Guide](./deployment/HETZNER-DEPLOYMENT.md)
- **Make API requests** → [API Documentation](./api/README.md)
- **Understand the architecture** → [Architecture](./architecture/README.md)
- **Write tests** → [Testing Guide](./testing/e2e-testing.md)
- **Configure Kubernetes** → [Helm Chart](./deployment/helm-chart-readme.md)

## 📖 Documentation Categories

### 1. Architecture

Understand the system design and technical decisions.

- [Architecture Overview](./architecture/README.md) - Complete system architecture
- [Technology Stack](./architecture/1.1-technology-stack.md) - Technologies used
- [Database Schema](./architecture/1.2-database-schema.md) - Data model

### 2. Development

Set up your development environment and start contributing.

- [Getting Started](./development/getting-started.md) - Environment setup and workflow
- [Project Structure](./development/getting-started.md#project-structure) - Code organization
- [Coding Standards](./development/getting-started.md#coding-standards) - Style guides
- [Testing](./development/getting-started.md#testing) - Test strategy
- [Contributing](./development/getting-started.md#contributing) - How to contribute

### 3. API

Complete API reference for integrations.

- [API Overview](./api/README.md) - Authentication, patterns, SDKs
- Accounts API - Customer/supplier management (coming soon)
- RFQs API - Request for Quote (coming soon)
- Quotes API - Quote management (coming soon)
- Products API - Product catalog (coming soon)
- Quality API - Quality inspections (coming soon)

### 4. Deployment

Deploy Sensei to various environments.

- [Production Deployment](./deployment/DEPLOYMENT.md) - Full production guide
- [Kubernetes Quick Start](./deployment/QUICKSTART.md) - Local Minikube setup
- [Hetzner Cloud](./deployment/HETZNER-DEPLOYMENT.md) - Deploy on Hetzner
- [Helm Chart](./deployment/helm-chart-readme.md) - Chart configuration
- [Helm Dependencies](./deployment/helm-dependencies.md) - Bitnami charts
- [Kubernetes Completion Summary](./deployment/kubernetes-completion-summary.md) - Implementation details

### 5. Testing

Comprehensive testing documentation.

- [E2E Testing](./testing/e2e-testing.md) - Playwright end-to-end tests
- Unit Testing - Backend tests (coming soon)
- Component Testing - Frontend tests (coming soon)
- Integration Testing - API tests (coming soon)

### 6. Guides

User and administrator guides.

- User Guide - End-user documentation (coming soon)
- Admin Guide - System administration (coming soon)
- Authentication Guide - OAuth, SSO (coming soon)
- Backup & Recovery - Data protection (coming soon)
- Monitoring Guide - Prometheus setup (coming soon)

## 🎯 By Role

### Software Engineer

1. [Getting Started](./development/getting-started.md) - Setup environment
2. [Architecture](./architecture/README.md) - Understand design
3. [API Reference](./api/README.md) - API endpoints
4. [Testing](./testing/e2e-testing.md) - Write tests

### DevOps Engineer

1. [Deployment Guide](./deployment/DEPLOYMENT.md) - Production deployment
2. [Helm Chart](./deployment/helm-chart-readme.md) - Kubernetes config
3. [Hetzner Guide](./deployment/HETZNER-DEPLOYMENT.md) - Cloud provider
4. [Architecture](./architecture/README.md) - Infrastructure design

### QA Engineer

1. [E2E Testing](./testing/e2e-testing.md) - Playwright tests
2. [API Reference](./api/README.md) - API testing
3. [Getting Started](./development/getting-started.md) - Setup environment

### Product Manager

1. [Architecture](./architecture/README.md) - System capabilities
2. [Development Plan](../Development_Plan.md) - Roadmap
3. User Guide - Feature documentation (coming soon)

### System Administrator

1. [Deployment Guide](./deployment/DEPLOYMENT.md) - Installation
2. Admin Guide - Configuration (coming soon)
3. Backup & Recovery - Data protection (coming soon)
4. [Monitoring](./architecture/README.md#monitoring--observability) - System health

## 📝 Documentation Standards

### Writing Guidelines

- **Clear and Concise**: Use simple language
- **Examples**: Include code examples
- **Structure**: Use headings and lists
- **Links**: Cross-reference related docs
- **Updates**: Keep docs synchronized with code

### Markdown Style

```markdown
# Title (H1 - once per document)

## Section (H2)

### Subsection (H3)

**Bold** for emphasis
*Italic* for terms
`code` for inline code

- Bullet list
1. Numbered list

[Link text](./relative/path.md)

\`\`\`language
Code block
\`\`\`
```

## 🔄 Keeping Documentation Updated

### When to Update Docs

- **New Feature**: Update relevant guides and API docs
- **Breaking Change**: Update migration guide and changelog
- **Bug Fix**: Update troubleshooting if applicable
- **Architecture Change**: Update architecture docs
- **Deployment Change**: Update deployment guides

### Documentation Checklist

When adding a new feature:

- [ ] Update API documentation (if applicable)
- [ ] Update user guide (if user-facing)
- [ ] Update architecture docs (if structural change)
- [ ] Update deployment guide (if config changes)
- [ ] Add examples and code samples
- [ ] Cross-link related documentation
- [ ] Update README if major feature

## 📚 Additional Resources

### External Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Backend framework
- [Next.js Documentation](https://nextjs.org/docs) - Frontend framework
- [React Documentation](https://react.dev/) - UI library
- [PostgreSQL Documentation](https://www.postgresql.org/docs/) - Database
- [Kubernetes Documentation](https://kubernetes.io/docs/) - Orchestration
- [Helm Documentation](https://helm.sh/docs/) - Package manager

### Community

- **GitHub**: https://github.com/sbelakho2/Management-Software
- **Issues**: https://github.com/sbelakho2/Management-Software/issues
- **Discussions**: https://github.com/sbelakho2/Management-Software/discussions
- **Email**: contact@starzmorocco.com

### Support

- **Technical Support**: contact@starzmorocco.com
- **Sales**: contact@starzmorocco.com
- **Website**: https://flopsen.tech

## 🤝 Contributing to Documentation

Found an issue or want to improve the docs?

1. **Small fixes**: Edit directly on GitHub
2. **Larger changes**: Create a branch and PR
3. **New documentation**: Follow existing structure
4. **Questions**: Open an issue or discussion

See [Contributing Guide](./development/getting-started.md#contributing) for details.

## 📄 License

Documentation licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

Code licensed under MIT License (see [LICENSE](../LICENSE))

---

**Last Updated**: January 8, 2026  
**Version**: 1.0.0  
**Maintained By**: Starz Morocco Development Team
