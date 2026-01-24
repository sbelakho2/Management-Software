# AI Insights Access Reference

## Role-Based AI Insight Access Control System

This document provides comprehensive documentation on the role-based AI insight access control system in Sensei OS. Each role has carefully calibrated access to AI-powered insights based on their responsibilities, security level, and operational needs.

---

## Table of Contents

1. [Overview](#overview)
2. [Role Hierarchy](#role-hierarchy)
3. [Insight Categories](#insight-categories)
4. [Access Levels by Role](#access-levels-by-role)
5. [Rate Limiting](#rate-limiting)
6. [Audit & Compliance](#audit--compliance)
7. [Configuration Guide](#configuration-guide)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### What is Role-Based Insight Access?

Sensei OS provides over 50 AI-powered insight categories covering every aspect of manufacturing operations. Access to these insights is controlled through a sophisticated role-based access control (RBAC) system that:

- **Protects sensitive data** by limiting access based on need-to-know
- **Optimizes performance** by focusing each role on relevant insights
- **Ensures compliance** with data privacy and security regulations
- **Provides audit trails** for all insight access

### Key Principles

1. **Least Privilege**: Users only see insights relevant to their role
2. **Hierarchy Inheritance**: Higher-level roles inherit appropriate lower-level access
3. **Full Executive Access**: CEO and Admin have unrestricted access
4. **Audit Everything**: All insight access is logged for compliance

---

## Role Hierarchy

The system supports 24 distinct roles organized in a hierarchy from most privileged (level 0) to least privileged (level 100):

| Level | Role | Description |
|-------|------|-------------|
| 0 | Admin | Full system access, configuration |
| 5 | CEO | Chief Executive Officer |
| 10 | GM (General Manager) | Site/plant leadership |
| 15 | Executive | C-suite and VP level |
| 20 | Finance | Financial operations |
| 20 | HR | Human resources |
| 20 | Operations | Operations management |
| 20 | Quality | Quality assurance |
| 20 | IT | Information technology |
| 30 | Accountant | Financial staff |
| 30 | Auditor | Internal/external audit |
| 35 | Sales Engineer | Technical sales |
| 35 | Estimator | Cost estimation |
| 40 | Sales | Sales representatives |
| 40 | Purchasing | Procurement |
| 40 | Supply Chain | Supply chain specialist |
| 45 | Logistics | Logistics coordination |
| 45 | Warehouse | Warehouse operations |
| 50 | Maintenance | Equipment maintenance |
| 50 | Engineering | Process engineering |
| 60 | Supervisor | Production supervision |
| 70 | Team Lead | Team leadership |
| 80 | Operator | Machine operation |
| 100 | Viewer | Read-only access |

---

## Insight Categories

AI insights are organized into 8 major categories with 57 individual insight types:

### 1. Production & Operations
- Production Efficiency (OEE, throughput, cycle times)
- Bottleneck Analysis
- Downtime Analysis
- Capacity Utilization
- Production Forecasts
- Scheduling Optimization
- Real-time Production Status
- Yield Analysis

### 2. Quality & Compliance
- Quality Metrics (PPM, defect rates)
- SPC Analysis (Statistical Process Control)
- Defect Predictions
- Compliance Status
- Audit Readiness
- CAPA Management
- Customer Complaint Analysis
- First Pass Yield

### 3. Inventory & Supply Chain
- Inventory Levels
- Reorder Recommendations
- Supplier Performance
- Supply Chain Risks
- Cost Optimization
- Lead Time Analysis
- Stock-out Predictions
- ABC Analysis

### 4. Maintenance & Equipment
- Equipment Health Monitoring
- Predictive Maintenance Alerts
- Maintenance Cost Analysis
- Asset Lifecycle Insights
- Reliability Metrics (MTBF, MTTR)
- Spare Parts Optimization
- Energy Consumption Analysis

### 5. Financial & Cost Analysis
- Cost Analysis
- Profitability Analysis
- Margin Trends
- Revenue Forecasts
- Cash Flow Insights
- Budget Variance Analysis
- Cost of Quality
- Activity-Based Costing

### 6. Workforce & HR
- Workforce Productivity
- Attendance Patterns
- Skill Gap Analysis
- Retention Risk Predictions
- Compensation Insights
- Training Effectiveness
- Safety Compliance
- Labor Cost Analysis

### 7. Sales & Customer
- Sales Pipeline Health
- Win/Loss Analysis
- Customer Insights
- Quote Optimization (AI recommendations for margin/pricing)
- Quoting Memory (Semantic job similarity retrieval)
- Smart RFQ Ingestion (Technical metadata extraction)
- Market Trends
- Customer Satisfaction

### 8. Strategic & Executive
- KPI Dashboard
- Competitive Analysis
- Strategic Recommendations
- Risk Assessment
- Scenario Planning
- Board Report Generation
- M&A Impact Analysis
- ESG Metrics

---

## Access Levels by Role

### Full Access Roles (All Insights)

**Admin & CEO** have unrestricted access to all 57 insight categories. This access is locked and cannot be modified.

### Executive Roles

**General Manager (GM)**
- ✅ All Production insights
- ✅ All Quality insights
- ✅ All Inventory insights
- ✅ KPI Dashboard
- ✅ Workforce Productivity
- ✅ Financial summaries (not detailed)
- ❌ Compensation details
- ❌ Retention risk (individual level)

**Executive**
- ✅ KPI Dashboard
- ✅ All Strategic insights
- ✅ All Financial insights
- ✅ High-level operational metrics
- ❌ Detailed shop floor data

### Department Heads

**Finance**
- ✅ All Financial insights
- ✅ Cost Analysis
- ✅ Profitability metrics
- ✅ Budget insights
- ❌ HR compensation details
- ❌ Detailed production data

**HR**
- ✅ All Workforce insights
- ✅ Attendance and productivity
- ✅ Training and development
- ✅ Retention predictions
- ❌ Financial details
- ❌ Production specifics

**Operations**
- ✅ All Production insights
- ✅ All Quality insights
- ✅ All Inventory insights
- ✅ Maintenance overview
- ❌ Detailed financial data
- ❌ HR specifics

**Quality**
- ✅ All Quality insights
- ✅ SPC and compliance
- ✅ Audit readiness
- ✅ Customer complaints
- ❌ Financial details
- ❌ HR data

**IT**
- ✅ Equipment health
- ✅ System reliability
- ✅ Performance metrics
- ❌ Financial data
- ❌ HR data

### Specialized Roles

**Accountant**
- ✅ Cost Analysis
- ✅ Cash Flow insights
- ✅ Budget variance
- ❌ Strategic insights
- ❌ Profitability (executive only)

**Auditor**
- ✅ All Compliance insights
- ✅ Audit readiness
- ✅ Financial audit data
- ✅ Process compliance
- ❌ Strategic recommendations
- ❌ Compensation details

**Sales & Sales Engineer**
- ✅ Sales Pipeline
- ✅ Customer Insights
- ✅ Quote Optimization
- ✅ Win/Loss Analysis
- ❌ Cost breakdowns
- ❌ HR data

### Operational Roles

**Supervisor**
- ✅ Production Efficiency
- ✅ Workforce Productivity
- ✅ Quality Metrics
- ✅ Equipment Status
- ❌ Financial data
- ❌ Strategic insights

**Maintenance**
- ✅ Equipment Health
- ✅ Predictive Maintenance
- ✅ Reliability Metrics
- ✅ Spare Parts
- ❌ Financial data
- ❌ HR data

**Operator**
- ✅ Production Efficiency (own area)
- ✅ Equipment Health (assigned machines)
- ✅ Quality metrics (own work)
- ❌ Cross-functional data
- ❌ Financial data

**Viewer**
- ✅ KPI Dashboard (summary only)
- ❌ All other insights

---

## Rate Limiting

To ensure system stability and fair usage, insight queries are rate-limited by role. These limits are generous for factory environments:

| Role | Per Minute | Per Hour | Burst (5s) |
|------|------------|----------|------------|
| Admin/CEO | 10,000 | 100,000 | 500 |
| GM | 5,000 | 50,000 | 250 |
| Executive | 3,000 | 30,000 | 150 |
| Department Heads | 2,000-3,000 | 20,000-30,000 | 100-150 |
| Specialized Roles | 1,000-1,500 | 10,000-15,000 | 75-100 |
| Supervisors | 1,500 | 15,000 | 100 |
| Team Leads | 1,000 | 10,000 | 75 |
| Operators | 500 | 5,000 | 50 |
| Viewers | 300 | 3,000 | 30 |

These limits support:
- Dashboard auto-refresh (5-10 second intervals)
- Multiple concurrent users per shift
- Heavy batch operations during shift changes
- Report generation spikes

---

## Audit & Compliance

### What is Logged

Every insight access is logged with:
- Timestamp (millisecond precision)
- User ID and role
- Insight category and specific insight
- Access result (granted/denied)
- Response time
- Client information

### Tamper Protection

Audit logs are cryptographically signed to prevent tampering:
- HMAC-SHA256 signatures
- Immutable log entries
- Anomaly detection for suspicious patterns

### Compliance Features

- **GDPR**: Data access tracking and right-to-audit
- **SOX**: Financial insight access controls
- **ISO 27001**: Information security audit trails
- **Industry-specific**: Manufacturing compliance tracking

### Anomaly Detection

The system automatically detects:
- Unusual access patterns
- After-hours access to sensitive insights
- Bulk data extraction attempts
- Access from new locations/devices

---

## Configuration Guide

### For Administrators

Access the Role-Insight Mappings UI at:
```
Settings → Admin → Role-Insight Mappings
```

Features:
1. **Access Matrix**: Visual grid of all role-insight combinations
2. **By Role View**: Card-based view of each role's access
3. **Audit Log**: History of all access changes
4. **Export/Import**: JSON export for backup and compliance

### Modifying Access

1. Navigate to Access Matrix
2. Find the role-insight intersection
3. Toggle access on/off
4. Provide a reason (required for audit)
5. Save changes

**Note**: CEO and Admin access is locked and cannot be modified.

### Bulk Updates

For bulk changes:
1. Export current configuration
2. Modify the JSON file
3. Import the updated configuration
4. Review and confirm changes

---

## Troubleshooting

### "Access Denied" Errors

1. Verify your role has access to the insight
2. Check if you've exceeded rate limits
3. Ensure your session is still valid
4. Contact your administrator if access should be granted

### Rate Limit Exceeded

1. Wait for the limit window to reset
2. Reduce dashboard refresh frequency
3. Use batch queries instead of individual requests
4. Contact admin if limits need adjustment

### Missing Insights

1. Some insights require specific data to be available
2. Check if the relevant data sources are connected
3. Verify the insight is enabled for your facility
4. Contact support if data should be available

### Audit Questions

For audit inquiries:
1. Access the Audit Log in Role-Insight Mappings
2. Export logs for the required date range
3. Filter by user, role, or insight category
4. Provide logs to auditors as needed

---

## Role Validation Matrix (All 24 Roles)

This section provides a comprehensive validation that all 24 roles are properly configured for both Page Access (RBAC) and AI Insights.

### Complete Role Coverage

| # | Role | Page Access Groups | AI Insights | Status |
|---|------|-------------------|-------------|--------|
| 1 | `admin` | ALL (full access) | ALL (57 categories) | ✅ |
| 2 | `ceo` | ALL (full access) | ALL (57 categories) | ✅ |
| 3 | `gm` | EXECUTIVE, FINANCE, SALES, OPS, HR, QUALITY, SUPPLY_CHAIN, ANALYTICS | 48 categories | ✅ |
| 4 | `exec` | EXECUTIVE, FINANCE, SALES, OPS, QUALITY | 18 categories | ✅ |
| 5 | `finance` | FINANCE, PURCHASE | 13 categories | ✅ |
| 6 | `accountant` | FINANCE, PURCHASE | 7 categories | ✅ |
| 7 | `hr` | HR, TRAINING | 11 categories | ✅ |
| 8 | `ops` | OPS, MAINTENANCE, SUPPLY_CHAIN, QUALITY, ANALYTICS | 17 categories | ✅ |
| 9 | `quality` | QUALITY, OPS | 13 categories | ✅ |
| 10 | `auditor` | QUALITY | 8 categories | ✅ |
| 11 | `it` | IT | 9 categories | ✅ |
| 12 | `supervisor` | OPS, HR, TRAINING, QUALITY, MAINTENANCE, SUPPLY_CHAIN, ANALYTICS | 12 categories | ✅ |
| 13 | `team_lead` | OPS, TRAINING, QUALITY, MAINTENANCE, OPERATOR | 8 categories | ✅ |
| 14 | `operator` | OPERATOR, TRAINING, QUALITY, MAINTENANCE | 7 categories | ✅ |
| 15 | `viewer` | /today, /tasks only (read-only) | 4 categories (general) | ✅ |
| 16 | `sales_engineer` | SALES, OPS, ANALYTICS | 12 categories | ✅ |
| 17 | `estimator` | SALES | 11 categories | ✅ |
| 18 | `supply_chain` | SUPPLY_CHAIN | 11 categories | ✅ |
| 19 | `maintenance` | MAINTENANCE | 10 categories | ✅ |
| 20 | `warehouse` | SUPPLY_CHAIN | 8 categories | ✅ |
| 21 | `sales` | SALES | 10 categories | ✅ |
| 22 | `purchasing` | SUPPLY_CHAIN, PURCHASE | 9 categories | ✅ |
| 23 | `logistics` | SUPPLY_CHAIN | 8 categories | ✅ |
| 24 | `engineering` | OPS, QUALITY, ANALYTICS, PROJECTS | 10 categories | ✅ |

### PageGuard Implementation Summary

All protected routes now have PageGuard components:

| Route Pattern | PageGuard Location | Protected By |
|--------------|-------------------|--------------|
| `/admin/*` | `(admin)/layout.tsx` | `['admin', 'ceo']` |
| `/settings/(admin-only)/*` | `settings/(admin-only)/layout.tsx` | `['admin', 'ceo']` |
| `/finance/*` | `finance/layout.tsx` | `FINANCE_ROLES` |
| `/pipeline/*`, `/rfqs/*` | `(sales)/layout.tsx`, dedicated layouts | `SALES_ROLES` |
| `/ops/*`, `/production/*` | `(ops)/layout.tsx` | `OPS_ROLES` |
| `/shop-floor/*` | `(shop-floor)/layout.tsx` | `OPS_ROLES` |
| `/quality/*` | Page-level | `QUALITY_ROLES` |
| `/mrp/*` | `mrp/layout.tsx` | MRP roles |
| `/purchase/*` | `purchase/layout.tsx` | Purchase roles |
| `/projects/*` | `projects/layout.tsx` | PM roles |
| `/project-management/*` | `project-management/layout.tsx` | PM roles |
| `/executive/*` | Page-level | `EXECUTIVE_ROLES` |
| `/analytics/*` | Page-level | `ANALYTICS_ROLES` |
| `/hr/*` | Page-level | `HR_ROLES` |
| `/it/*` | Page-level | `IT_ROLES` |
| `/warehouse/*` | Page-level | `SUPPLY_CHAIN_ROLES` |
| `/supply-chain/*` | Page-level | `SUPPLY_CHAIN_ROLES` |
| `/auditor/*` | Page-level | `QUALITY_ROLES` |

### Security Enforcement

1. **Fail-Closed Design**: Unknown routes default to deny
2. **CEO Parity**: CEO has identical access to Admin
3. **Operator Isolation**: Operators limited to shop floor & training
4. **Viewer Restrictions**: Viewers can only access /today and /tasks

---

## Related Documentation

- [CEO Starter Guide](./CEO/CEO_Starter_Guide.md)
- [Admin Guide](../guides/admin-guide.md)
- [Security Documentation](../maintenance/SECURITY.md)
- [User Guide](../guides/user-guide.md)

---

*Last Updated: January 2026*
*Document Version: 1.1 - Added complete role validation matrix*
