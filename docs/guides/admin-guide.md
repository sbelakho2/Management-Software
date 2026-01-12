# Administrator Guide

This guide provides information for system administrators to configure and manage Sensei OS.

## System Configuration

### Environment Variables
Most system settings are controlled via environment variables. See the [Configuration Reference](./configuration-reference.md) for a complete list.

### Admin Dashboard
Access the admin dashboard at `/admin` (requires `Admin` role).
- **User Management**: Create, edit, and deactivate users.
- **Role Assignment**: Assign roles and granular permissions.
- **System Settings**: Configure global settings like site name, support email, etc.
- **Security**: Configure SAML 2.0 SSO and enforce 2FA.

## User Management

### Creating Users
1. Go to **Admin > Users**.
2. Click **Add User**.
3. Enter user details and assign a role.
4. The user will receive an invitation email to set their password.

### RBAC Configuration
Permissions are grouped into roles. While default roles are provided, administrators can adjust permissions for each role in the **Admin > Roles** section.

## Security Management

### Configuring SSO
1. Obtain the SAML Metadata from your Identity Provider (IdP).
2. Go to **Admin > Security > SSO**.
3. Upload the metadata and configure the mapping fields (Email, Name, etc.).
4. Test the connection before enabling.

### 2FA Enforcement
Administrators can enforce 2FA globally or for specific roles. This is done in **Admin > Security > Authentication**.

## Troubleshooting
See the [Troubleshooting Guide](./troubleshooting.md) for common issues and their resolutions.
