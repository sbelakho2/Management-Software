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
- **Roles**: `Admin`, `Manager`, `User`, `Viewer`.
- **Permissions**: Granular control over resources (e.g., `rfq:create`, `work_order:approve`).

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

## Vulnerability Scanning

### Container Images
We recommend using tools like `Trivy` or `Snyk` to scan container images for vulnerabilities during the CI/CD pipeline.

### Dependency Updates
Regularly update Python packages in `backend/pyproject.toml` and NPM packages in `frontend/package.json` to receive security patches.
