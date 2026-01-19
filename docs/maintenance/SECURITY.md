# Security Maintenance and Operations

This document describes the security architecture and maintenance procedures for Sensei OS.

## Secret Management

### ExternalSecrets Operator
In production, we use the `ExternalSecrets` Operator to inject sensitive credentials into Kubernetes pods. This allows us to store secrets in external providers like AWS Secrets Manager or HashiCorp Vault.

### Local Development
For local development, secrets are managed via a `.env` file. Never commit this file to version control.

### Rotating Secrets
1. Update the secret in the external provider.
2. The `ExternalSecrets` operator will automatically sync the changes to the Kubernetes `Secret`.
3. Pods may need to be restarted to pick up the new secret values (depending on the implementation).

## Authentication & Authorization

### RBAC (Role-Based Access Control)
Roles and permissions are defined in the database.

**Role Hierarchy (24 Roles):**
| Level | Roles |
|-------|-------|
| 0-5 | Admin, CEO (Full Access) |
| 10-15 | GM, Executive |
| 20 | Finance, HR, Ops, Quality, IT (Department Heads) |
| 30-40 | Accountant, Auditor, Sales Engineer, Estimator, Sales, Purchasing, Supply Chain |
| 45-50 | Logistics, Warehouse, Maintenance, Engineering |
| 60-70 | Supervisor, Team Lead |
| 80-100 | Operator, Viewer |

**Permission Types:**
- **Page Access**: Which pages/routes a role can access
- **Resource Actions**: Granular control (e.g., `rfq:create`, `work_order:approve`)
- **AI Insight Access**: Which AI insights a role can query

### AI Insight Access Control
The system provides role-based access to 57 AI insight categories:
- **Sensitivity Levels**: Low, Medium, High, Critical
- **Full Access Roles**: Admin and CEO have locked full access
- **Configurable Access**: Other roles can be customized via Admin UI
- **Audit Trail**: All insight access is logged with tamper-proof signing

See [AI Insights Access Reference](../Resources/AI_INSIGHTS_ACCESS.md) for details.

### Single Sign-On (SSO)
Sensei OS supports SAML 2.0 for enterprise SSO integration. Configuration is managed in the **Admin/Security** dashboard.

### Two-Factor Authentication (2FA)
2FA (TOTP) is enforced for administrative roles and can be enabled for all users.
- **Recovery Codes**: Users are provided with backup codes during setup.
- **Admin Reset**: Administrators can reset a user's 2FA secret if they lose access.

## Auditing

### Audit Logs
All critical actions (logins, data modifications, approvals) are recorded in the `audit_logs` table.
- **Retention**: Audit logs are partitioned by date. Old partitions can be archived to S3 for long-term compliance.
- **Viewing**: Logs can be viewed in the **Admin/Audit Log** page.

### AI Insight Audit Logs
AI insight access has dedicated audit logging:
- **Immutable Entries**: Each log entry is cryptographically signed (HMAC-SHA256)
- **Tamper Detection**: Any modification to logs is detectable
- **Anomaly Detection**: Automatic detection of suspicious access patterns
- **Compliance Ready**: Supports SOX, GDPR, ISO 27001 requirements

**What's Logged:**
- User ID, role, and session information
- Insight category and specific insight accessed
- Access result (granted/denied)
- Response time
- Client information (IP, user agent)

## Vulnerability Scanning

### Container Images
We recommend using tools like `Trivy` or `Snyk` to scan container images for vulnerabilities during the CI/CD pipeline.

### Dependency Updates
Regularly update Python packages in `backend/pyproject.toml` and NPM packages in `frontend/package.json` to receive security patches.
