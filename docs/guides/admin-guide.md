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
- **AI Insight Access**: Configure role-based access to AI insights.

## User Management

### Creating Users
1. Go to **Admin > Users**.
2. Click **Add User**.
3. Enter user details and assign a role.
4. The user will receive an invitation email to set their password.

### RBAC Configuration
Permissions are grouped into roles. While default roles are provided, administrators can adjust permissions for each role in the **Admin > Roles** section.

### Role Hierarchy
The system supports 24 roles organized by hierarchy level (0-100):

| Level | Role | Description |
|-------|------|-------------|
| 0 | Admin | Full system access |
| 5 | CEO | Chief Executive Officer |
| 10 | GM | General Manager |
| 15 | Executive | C-suite and VP level |
| 20 | Finance, HR, Ops, Quality, IT | Department heads |
| 30-40 | Specialists | Accountant, Auditor, Sales, Purchasing |
| 50-60 | Technical | Maintenance, Engineering, Supervisor |
| 70-80 | Operational | Team Lead, Operator |
| 100 | Viewer | Read-only access |

Higher-level roles (lower numbers) inherit access from lower-level roles (higher numbers) as appropriate.

## AI Insight Access Control

### Overview
Sensei OS provides 57 AI insight categories. Access to these insights is controlled through role-based access control (RBAC).

### Configuring Role-Insight Mappings
1. Go to **Settings > Admin > Role-Insight Mappings**.
2. Use the **Access Matrix** to view/modify role-insight combinations.
3. Toggle access on/off using checkboxes.
4. Provide a reason for each change (required for audit trail).
5. Save changes.

**Note:** CEO and Admin access is locked and cannot be modified.

### Insight Categories
- **Production & Operations**: OEE, throughput, bottleneck analysis
- **Quality & Compliance**: SPC, defect predictions, audit readiness
- **Inventory & Supply Chain**: Inventory levels, supplier performance
- **Maintenance & Equipment**: Predictive maintenance, equipment health
- **Financial & Cost**: Profitability, margin trends, cash flow
- **Workforce & HR**: Productivity, skill gaps, retention predictions
- **Sales & Customer**: Pipeline, win/loss analysis, customer insights
- **Strategic & Executive**: KPI dashboards, competitive analysis

### Rate Limits
Factory-optimized rate limits are configured per role:
- Admin/CEO: 10,000 req/min
- Executives: 3,000-5,000 req/min
- Department Heads: 2,000-3,000 req/min
- Specialists: 1,000-1,500 req/min
- Operators: 500 req/min

### Audit Logging
All insight access is logged with:
- Timestamp
- User ID and role
- Insight accessed
- Access result (granted/denied)

Audit logs are cryptographically signed to prevent tampering.

For detailed documentation, see [AI Insights Access Reference](../Resources/AI_INSIGHTS_ACCESS.md).

## Security Management

### Configuring SSO
1. Obtain the SAML Metadata from your Identity Provider (IdP).
2. Go to **Admin > Security > SSO**.
3. Upload the metadata and configure the mapping fields (Email, Name, etc.).
4. Test the connection before enabling.

### 2FA Enforcement
Administrators can enforce 2FA globally or for specific roles. This is done in **Admin > Security > Authentication**.

## Data Migration

### StarzERP Import
Sensei OS provides a comprehensive data migration service for importing data from legacy StarzERP MySQL databases.

1. Go to **Admin > Data Migration > StarzERP Import**
2. Click "Preview Import" to see record counts
3. Select entity types to import (56 total entity types available)
4. Choose conflict resolution: Skip, Update, or Fail on duplicates
5. Click "Start Import"
6. Monitor real-time progress
7. Review results and address any errors

**Supported Modules:**
- Inventory/WMS (warehouses, locations, devices, LPNs)
- Products (articles, units, categories)
- HR (employees, contracts, leaves, clocking, training)
- Purchasing (suppliers, POs, receipts)
- Sales (customers, quotations, invoices)
- Shipping (shipments, pick lists)
- Finance (payments, bank transactions)
- Quality (scrap records)

For detailed entity mappings and API usage, see the [StarzERP Data Migration Guide](./starz-erp-data-migration.md).

## Troubleshooting
See the [Troubleshooting Guide](./troubleshooting.md) for common issues and their resolutions.
