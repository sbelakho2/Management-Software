# IT Administrator Starter Guide

## Sensei OS - IT Administration Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [System Administration Dashboard](#3-system-administration-dashboard)
4. [User Management](#4-user-management)
5. [Role & Permission Management](#5-role--permission-management)
6. [Security Administration](#6-security-administration)
7. [System Configuration](#7-system-configuration)
8. [Integration Management](#8-integration-management)
9. [Database Administration](#9-database-administration)
10. [Monitoring & Logging](#10-monitoring--logging)
11. [Backup & Recovery](#11-backup--recovery)
12. [Performance Tuning](#12-performance-tuning)
13. [Deployment & Updates](#13-deployment--updates)
14. [Troubleshooting](#14-troubleshooting)
15. [Quick Reference](#15-quick-reference)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Support access troubleshooting: private projects require explicit membership.
- Use the activity log to investigate reports of unexpected changes.
- For integrations, use the PM APIs to sync milestones/issues with external tools (when approved).

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role in IT Administration

As an IT Administrator for Sensei OS, you are the **guardian of the system**. Your responsibilities include:

- **User lifecycle management** - onboarding, access, offboarding
- **Security administration** - authentication, authorization, audits
- **System configuration** - settings, integrations, customizations
- **Performance monitoring** - health, metrics, optimization
- **Disaster recovery** - backups, restoration, continuity
- **Technical support** - troubleshooting, escalation

### IT Admin Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| User Management | Full | Create, modify, disable users |
| Role Management | Full | Define and assign roles |
| Security Settings | Full | Auth, passwords, sessions |
| System Config | Full | All system settings |
| Integrations | Full | API, SSO, external systems |
| Audit Logs | Full | View all system activity |
| Backups | Full | Configure and execute |
| Monitoring | Full | System health and metrics |

### System Architecture Overview

```
SENSEI OS ARCHITECTURE

┌─────────────────────────────────────────────────────────────┐
│                        USERS                                 │
│     (Browsers / Mobile Apps / API Clients)                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     LOAD BALANCER                            │
│                   (NGINX / Traefik)                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION TIER                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Frontend  │  │  Backend   │  │    API     │            │
│  │  (Next.js) │  │  (FastAPI) │  │  Gateway   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATA TIER                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │ PostgreSQL │  │   Redis    │  │   Object   │            │
│  │     DB     │  │   Cache    │  │   Store    │            │
│  └────────────┘  └────────────┘  └────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Getting Started

### First Login as IT Admin

1. Navigate to `https://your-company.sensei-os.com`
2. Log in with admin credentials
3. Complete MFA setup (required for admins)
4. Change default password immediately

### Initial Setup Tasks

- [ ] Configure admin MFA
- [ ] Review default security settings
- [ ] Set up admin backup account
- [ ] Configure alerting/notifications
- [ ] Review integration requirements
- [ ] Test backup and recovery
- [ ] Document admin procedures

### Admin Access Point

Access administration at: `https://your-company.sensei-os.com/admin`

```
┌─────────────────────────────────────────────────────────────┐
│               IT ADMINISTRATION                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    USERS     │  │    ROLES     │  │   SECURITY   │       │
│  │     152      │  │      12      │  │   ✓ Good     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   SYSTEM     │  │ INTEGRATIONS │  │    LOGS      │       │
│  │   ✓ OK       │  │      5       │  │   View →     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  SYSTEM STATUS                                               │
│  ├─ API: ✓ Healthy         ├─ Database: ✓ Connected        │
│  ├─ Cache: ✓ Running       └─ Storage: ✓ Available         │
│                                                              │
│  RECENT ALERTS                                               │
│  └─ No critical alerts                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. System Administration Dashboard

### Dashboard Overview

The admin dashboard provides:

- **System Health** - Component status
- **User Statistics** - Active users, sessions
- **Security Alerts** - Failed logins, anomalies
- **Resource Usage** - CPU, memory, storage
- **Recent Activity** - Admin actions log

### System Health Panel

```
SYSTEM HEALTH
┌─────────────────────────────────────────────────────────────┐
│ Component      │ Status │ Response │ Details               │
├────────────────┼────────┼──────────┼───────────────────────┤
│ API Server     │ ✓ OK   │ 45ms     │ v1.0.0, 3 instances   │
│ Database       │ ✓ OK   │ 12ms     │ PostgreSQL 15.2       │
│ Cache (Redis)  │ ✓ OK   │ 2ms      │ 85% hit rate          │
│ Object Storage │ ✓ OK   │ 88ms     │ 12.5 TB used          │
│ Background Jobs│ ✓ OK   │ -        │ 3 workers, 0 pending  │
└────────────────┴────────┴──────────┴───────────────────────┘
```

### Active Sessions

```
ACTIVE SESSIONS
┌─────────────────────────────────────────────────────────────┐
│ Total Active: 45                                             │
│ By Role:                                                     │
│ ├─ Operators: 28                                            │
│ ├─ Supervisors: 8                                           │
│ ├─ Managers: 5                                              │
│ └─ Admins: 4                                                │
│                                                              │
│ By Location:                                                 │
│ ├─ Plant Floor: 32                                          │
│ ├─ Office: 11                                               │
│ └─ Remote: 2                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. User Management

### User List

Access: **Admin → Users**

```
USER MANAGEMENT
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search users...    [Filter ▼] [+ Add User]               │
├─────────────────────────────────────────────────────────────┤
│ User          │ Email           │ Role       │ Status│ Last │
├───────────────┼─────────────────┼────────────┼───────┼──────┤
│ John Smith    │ jsmith@co.com   │ Operator   │ Active│ Today│
│ Maria Garcia  │ mgarcia@co.com  │ Supervisor │ Active│ Today│
│ David Brown   │ dbrown@co.com   │ Manager    │ Active│ Yest │
│ Sarah Wilson  │ swilson@co.com  │ Admin      │ Active│ Today│
│ [Former User] │ former@co.com   │ -          │ Disabled│ - │
└───────────────┴─────────────────┴────────────┴───────┴──────┘
```

### Creating a New User

```
┌─────────────────────────────────────────────────────────────┐
│  CREATE NEW USER                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ BASIC INFORMATION                                            │
│ First Name:     [                    ]                       │
│ Last Name:      [                    ]                       │
│ Email:          [                    ]                       │
│ Employee ID:    [                    ] (optional)            │
│                                                              │
│ ACCESS                                                       │
│ Role:           [Select Role         ▼]                      │
│ Department:     [Select Department   ▼]                      │
│ Location:       [Select Location     ▼]                      │
│                                                              │
│ AUTHENTICATION                                               │
│ ☐ Generate temporary password (email to user)               │
│ ☐ Set initial password manually                             │
│ ☑ Require password change on first login                    │
│ ☑ Enable MFA requirement                                    │
│                                                              │
│ [Cancel]  [Create User]                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### User Profile Management

View and edit user details:

```
┌─────────────────────────────────────────────────────────────┐
│  USER: John Smith                                            │
│  ID: USR-00152 | Created: Jan 5, 2025                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ACCOUNT                                                      │
│ ├─ Email: jsmith@company.com                                │
│ ├─ Status: Active ✓                                         │
│ ├─ Last Login: Jan 11, 2026 10:30 AM                        │
│ └─ MFA: Enabled (Authenticator)                             │
│                                                              │
│ ACCESS                                                       │
│ ├─ Primary Role: Operator                                   │
│ ├─ Department: Production                                   │
│ ├─ Location: Plant A                                        │
│ └─ Shift: Day (6 AM - 2 PM)                                 │
│                                                              │
│ PERMISSIONS (via role)                                       │
│ ├─ Workstation access                                       │
│ ├─ Time entry                                               │
│ ├─ Quality entry                                            │
│ └─ Basic reporting                                          │
│                                                              │
│ ACTIONS                                                      │
│ [Edit] [Reset Password] [Disable] [View Activity]           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### User Lifecycle

```
USER LIFECYCLE

   Create          Activate          Active           Disable         Archive
     │                │                 │                │               │
     ▼                ▼                 ▼                ▼               ▼
┌─────────┐     ┌─────────┐       ┌─────────┐     ┌─────────┐     ┌─────────┐
│ Pending │ ──▶ │  Setup  │  ──▶  │ Active  │ ──▶ │Disabled │ ──▶ │Archived │
│         │     │ MFA/Pwd │       │         │     │         │     │         │
└─────────┘     └─────────┘       └─────────┘     └─────────┘     └─────────┘
                                       │
                                       ▼
                                  ┌─────────┐
                                  │ Locked  │ (failed logins)
                                  └─────────┘
```

### Bulk User Operations

Import/export users:

```
BULK OPERATIONS
├─ Import Users from CSV
│  └─ Template: [Download Template]
├─ Export User List
│  └─ Format: [CSV ▼] [Export]
├─ Bulk Update
│  └─ Select users → [Update Role] [Update Dept]
└─ Bulk Disable
   └─ For terminated employees
```

---

## 5. Role & Permission Management

### Role Overview

Access: **Admin → Roles & Permissions**

```
ROLES
┌─────────────────────────────────────────────────────────────┐
│ Role            │ Users │ Permissions │ Description         │
├─────────────────┼───────┼─────────────┼─────────────────────┤
│ Super Admin     │ 2     │ Full        │ Complete access     │
│ IT Admin        │ 3     │ 85          │ System admin        │
│ Executive       │ 4     │ 65          │ Read all + reports  │
│ General Manager │ 2     │ 55          │ Plant management    │
│ HR Admin        │ 3     │ 45          │ HR functions        │
│ Finance         │ 4     │ 40          │ Financial data      │
│ Supervisor      │ 12    │ 35          │ Team + floor ops    │
│ Operator        │ 120   │ 15          │ Workstation only    │
└─────────────────┴───────┴─────────────┴─────────────────────┘
```

### Permission Structure

```
PERMISSION HIERARCHY

┌─────────────────────────────────────────────────────────────┐
│ Module        │ Permissions                                  │
├───────────────┼──────────────────────────────────────────────┤
│ Users         │ view | create | edit | delete | manage_roles│
│ Production    │ view | enter_data | approve | manage        │
│ Inventory     │ view | adjust | transfer | manage           │
│ Quality       │ view | inspect | ncr_create | ncr_manage    │
│ Maintenance   │ view | work_orders | pm_complete | admin    │
│ HR            │ view | employee_edit | time_manage | admin  │
│ Finance       │ view | ap_ar | gl | reports | admin         │
│ Reports       │ view_basic | view_advanced | create | admin │
│ System        │ view_config | edit_config | integrations    │
│ Audit         │ view_logs | export_logs                     │
└───────────────┴──────────────────────────────────────────────┘
```

### Creating/Editing Roles

```
┌─────────────────────────────────────────────────────────────┐
│  EDIT ROLE: Supervisor                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Role Name:        [Supervisor                 ]              │
│ Description:      [Production floor supervision]             │
│                                                              │
│ PERMISSIONS                                                  │
│                                                              │
│ PRODUCTION                                                   │
│ ☑ View production data                                      │
│ ☑ Enter production data                                     │
│ ☑ Approve production entries                                │
│ ☐ Manage production setup                                   │
│                                                              │
│ TEAM MANAGEMENT                                              │
│ ☑ View team members                                         │
│ ☑ Manage time/attendance                                    │
│ ☑ Approve time entries                                      │
│ ☐ Manage employee records                                   │
│                                                              │
│ QUALITY                                                      │
│ ☑ View quality data                                         │
│ ☑ Record inspections                                        │
│ ☑ Create NCRs                                               │
│ ☐ Manage NCRs                                               │
│                                                              │
│ [Cancel]  [Save Role]                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Role Assignment

Assign roles to users:
- Users can have one primary role
- Additional permissions via groups or direct grants

---

## 6. Security Administration

### Security Settings

Access: **Admin → Security**

```
SECURITY CONFIGURATION
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ AUTHENTICATION                                               │
│ ├─ MFA Requirement:     [Required for Admins ▼]             │
│ ├─ MFA Methods:         [Authenticator ✓] [SMS ☐] [Email ☐]│
│ ├─ Session Timeout:     [30     ] minutes                   │
│ └─ Concurrent Sessions: [3      ] maximum                   │
│                                                              │
│ PASSWORD POLICY                                              │
│ ├─ Minimum Length:      [12     ] characters                │
│ ├─ Require Uppercase:   [Yes ▼]                             │
│ ├─ Require Numbers:     [Yes ▼]                             │
│ ├─ Require Symbols:     [Yes ▼]                             │
│ ├─ Password History:    [12     ] remembered                │
│ └─ Max Age:             [90     ] days                      │
│                                                              │
│ LOCKOUT                                                      │
│ ├─ Failed Attempts:     [5      ] before lockout            │
│ ├─ Lockout Duration:    [30     ] minutes                   │
│ └─ Admin Unlock:        [Enabled ▼]                         │
│                                                              │
│ [Save Changes]                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Security Dashboard

Monitor security posture:

```
SECURITY OVERVIEW
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ MFA STATUS                                                   │
│ ├─ Admins with MFA:     5/5 (100%) ✓                        │
│ ├─ Users with MFA:      89/152 (58%)                        │
│ └─ MFA Not Setup:       63 users                            │
│                                                              │
│ PASSWORD HEALTH                                              │
│ ├─ Compliant:           140 users                           │
│ ├─ Expiring Soon:       8 users (< 14 days)                 │
│ └─ Expired:             4 users                             │
│                                                              │
│ RECENT SECURITY EVENTS                                       │
│ ├─ Failed Logins (24h): 12                                  │
│ ├─ Account Lockouts:    2                                   │
│ └─ Permission Changes:  5                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Failed Login Monitoring

```
FAILED LOGIN ATTEMPTS
┌─────────────────────────────────────────────────────────────┐
│ Time        │ Username     │ IP Address   │ Reason         │
├─────────────┼──────────────┼──────────────┼────────────────┤
│ 10:45 AM    │ jsmith       │ 192.168.1.50 │ Wrong password │
│ 10:43 AM    │ jsmith       │ 192.168.1.50 │ Wrong password │
│ 9:30 AM     │ mgarcia      │ 192.168.1.55 │ Account locked │
│ 8:15 AM     │ unknown_user │ 45.33.22.11  │ User not found │
└─────────────┴──────────────┴──────────────┴────────────────┘
```

### SSO Configuration

Configure Single Sign-On:

```
SSO CONFIGURATION
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SSO Provider:     [Azure AD           ▼]                    │
│                                                              │
│ SAML SETTINGS                                                │
│ ├─ Entity ID:     [https://sensei.company.com/saml    ]     │
│ ├─ SSO URL:       [https://login.microsoft.com/...    ]     │
│ ├─ Certificate:   [Upload Certificate]                      │
│ └─ Attribute Map: [Configure Mappings]                       │
│                                                              │
│ OPTIONS                                                      │
│ ├─ ☐ Allow password login fallback                          │
│ ├─ ☑ Auto-provision users from SSO                          │
│ └─ ☑ Sync groups from SSO                                   │
│                                                              │
│ [Test Connection]  [Save]                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. System Configuration

### Global Settings

Access: **Admin → System → Settings**

```
SYSTEM SETTINGS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ GENERAL                                                      │
│ ├─ Company Name:     [Your Company Inc.           ]         │
│ ├─ Time Zone:        [America/New_York       ▼]             │
│ ├─ Date Format:      [MM/DD/YYYY             ▼]             │
│ └─ Currency:         [USD                    ▼]             │
│                                                              │
│ LOCALIZATION                                                 │
│ ├─ Default Language: [English                ▼]             │
│ ├─ Available:        [English ✓] [Spanish ✓] [French ☐]    │
│ └─ Units:            [Imperial               ▼]             │
│                                                              │
│ FEATURES                                                     │
│ ├─ ☑ Production Module                                      │
│ ├─ ☑ Quality Module                                         │
│ ├─ ☑ Maintenance Module                                     │
│ ├─ ☑ HR Module                                              │
│ ├─ ☐ Advanced Analytics (Premium)                           │
│ └─ ☐ AI Features (Premium)                                  │
│                                                              │
│ [Save Changes]                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Environment Variables

Key configuration settings:

| Variable | Purpose | Example |
|----------|---------|---------|
| `DATABASE_URL` | DB connection | `postgresql://...` |
| `REDIS_URL` | Cache connection | `redis://...` |
| `SECRET_KEY` | JWT signing | `<generated>` |
| `SMTP_*` | Email config | Server, port, creds |
| `STORAGE_*` | Object storage | S3 or MinIO config |

### Email Configuration

```
EMAIL SETTINGS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SMTP CONFIGURATION                                           │
│ ├─ Server:      [smtp.company.com          ]                │
│ ├─ Port:        [587     ]                                  │
│ ├─ Username:    [sensei@company.com        ]                │
│ ├─ Password:    [••••••••••••] [Change]                     │
│ └─ Encryption:  [TLS                  ▼]                    │
│                                                              │
│ FROM ADDRESS                                                 │
│ ├─ Name:        [Sensei OS                  ]               │
│ └─ Email:       [noreply@company.com        ]               │
│                                                              │
│ [Test Email] [Save]                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Integration Management

### Active Integrations

Access: **Admin → Integrations**

```
INTEGRATIONS
┌─────────────────────────────────────────────────────────────┐
│ Integration      │ Type    │ Status  │ Last Sync │ Actions │
├──────────────────┼─────────┼─────────┼───────────┼─────────┤
│ SAP ERP          │ ERP     │ ✓ Active│ 5 min ago │ [Config]│
│ Azure AD         │ SSO     │ ✓ Active│ Real-time │ [Config]│
│ Kronos           │ Time    │ ✓ Active│ 15 min ago│ [Config]│
│ Slack            │ Notify  │ ✓ Active│ Real-time │ [Config]│
│ Power BI         │ BI      │ ⚠️ Error │ 2 hrs ago │ [Config]│
└──────────────────┴─────────┴─────────┴───────────┴─────────┘
```

### API Management

Configure API access:

```
API CONFIGURATION
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ API KEYS                                                     │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Key Name   │ Created    │ Last Used │ Scope   │ Status│   │
│ ├────────────┼────────────┼───────────┼─────────┼───────┤   │
│ │ SAP-Integ  │ Jan 1, 2025│ Today     │ Read/W  │ Active│   │
│ │ BI-Dashb   │ Mar 5, 2025│ Today     │ Read    │ Active│   │
│ │ Mobile-App │ Jun 10,2025│ Today     │ Full    │ Active│   │
│ └────────────┴────────────┴───────────┴─────────┴───────┘   │
│                                                              │
│ [+ Create API Key]                                           │
│                                                              │
│ RATE LIMITING                                                │
│ ├─ Default Limit:    [1000] requests/minute                 │
│ ├─ Burst Limit:      [100 ] requests/second                 │
│ └─ Per-Key Override: [Configure]                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Webhook Configuration

```
WEBHOOKS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ OUTGOING WEBHOOKS                                            │
│                                                              │
│ [+ Add Webhook]                                              │
│                                                              │
│ Name: Slack Notifications                                    │
│ URL: https://hooks.slack.com/services/...                   │
│ Events:                                                      │
│   ☑ Production alerts                                       │
│   ☑ Quality NCRs                                            │
│   ☑ Maintenance Andons                                      │
│   ☐ User logins                                             │
│ Status: Active ✓                                            │
│ [Edit] [Test] [Disable]                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Database Administration

### Database Overview

Access: **Admin → System → Database**

```
DATABASE STATUS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ CONNECTION                                                   │
│ ├─ Server:      db.sensei-cloud.com                         │
│ ├─ Database:    sensei_production                           │
│ ├─ Version:     PostgreSQL 15.2                             │
│ └─ Status:      ✓ Connected (12ms latency)                  │
│                                                              │
│ STORAGE                                                      │
│ ├─ Size:        45.2 GB                                     │
│ ├─ Tables:      156                                         │
│ ├─ Indexes:     312                                         │
│ └─ Growth:      +2.1 GB/month                               │
│                                                              │
│ CONNECTIONS                                                  │
│ ├─ Active:      24                                          │
│ ├─ Idle:        8                                           │
│ └─ Max:         100                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Database Migrations

```
MIGRATIONS
┌─────────────────────────────────────────────────────────────┐
│ Version      │ Name                     │ Applied     │ St  │
├──────────────┼──────────────────────────┼─────────────┼─────┤
│ 2026-01-10   │ Add audit_logs index     │ Jan 10, 2026│ ✓   │
│ 2026-01-05   │ Quality module updates   │ Jan 5, 2026 │ ✓   │
│ 2026-01-01   │ Initial schema           │ Jan 1, 2026 │ ✓   │
└──────────────┴──────────────────────────┴─────────────┴─────┘
│                                                              │
│ Pending Migrations: 0                                        │
│ [Check for Updates]                                          │
└─────────────────────────────────────────────────────────────┘
```

### Data Maintenance

Schedule maintenance tasks:

| Task | Frequency | Purpose |
|------|-----------|---------|
| VACUUM | Daily | Reclaim storage |
| ANALYZE | Daily | Update statistics |
| REINDEX | Weekly | Optimize indexes |
| Archive | Monthly | Move old data |

---

## 10. Monitoring & Logging

### System Monitoring

Access: **Admin → Monitoring**

```
SYSTEM METRICS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ CPU USAGE (Application Servers)                              │
│ ██████████████░░░░░░  65%  (3 instances)                    │
│                                                              │
│ MEMORY USAGE                                                 │
│ ████████████░░░░░░░░  58%  (4.6 GB / 8 GB)                  │
│                                                              │
│ DATABASE CONNECTIONS                                         │
│ ████████░░░░░░░░░░░░  32%  (32 / 100)                       │
│                                                              │
│ API REQUESTS (last hour)                                     │
│ Total: 15,234 | Avg: 45ms | Errors: 12 (0.08%)              │
│                                                              │
│ CACHE HIT RATE                                               │
│ ██████████████████░░  89%                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Audit Logs

Access: **Admin → Audit Logs**

```
AUDIT LOG
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Filter: [All ▼] Date: [Today ▼]  [Search...]  [Export]  │
├─────────────────────────────────────────────────────────────┤
│ Time     │ User     │ Action           │ Resource   │ IP    │
├──────────┼──────────┼──────────────────┼────────────┼───────┤
│ 10:45 AM │ admin    │ User Updated     │ jsmith     │ .1.50 │
│ 10:30 AM │ jsmith   │ Login Success    │ -          │ .1.50 │
│ 10:28 AM │ jsmith   │ Login Failed     │ -          │ .1.50 │
│ 10:15 AM │ mgarcia  │ Production Entry │ WO-1234    │ .1.55 │
│ 10:10 AM │ system   │ Backup Completed │ full_backup│ -     │
└──────────┴──────────┴──────────────────┴────────────┴───────┘
```

### Log Categories

| Category | Contents |
|----------|----------|
| Authentication | Logins, logouts, failures |
| User Management | Creates, updates, deletes |
| Security | Permission changes, lockouts |
| Data Changes | CRUD operations |
| System | Backups, config changes |
| Errors | Application errors |

### Alerting

Configure alerts:

```
ALERT CONFIGURATION
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Alert: Failed Login Threshold                                │
│ ├─ Trigger: 10 failed logins in 5 minutes                   │
│ ├─ Severity: Warning                                        │
│ ├─ Notify: IT Team (Slack #security)                        │
│ └─ Status: Active ✓                                         │
│                                                              │
│ Alert: Database Connection Error                             │
│ ├─ Trigger: Connection failure                              │
│ ├─ Severity: Critical                                       │
│ ├─ Notify: IT Admin (Email + SMS)                           │
│ └─ Status: Active ✓                                         │
│                                                              │
│ Alert: High CPU Usage                                        │
│ ├─ Trigger: CPU > 90% for 5 minutes                         │
│ ├─ Severity: Warning                                        │
│ ├─ Notify: IT Team (Slack)                                  │
│ └─ Status: Active ✓                                         │
│                                                              │
│ [+ Add Alert]                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Backup & Recovery

### Backup Configuration

Access: **Admin → System → Backup**

```
BACKUP CONFIGURATION
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SCHEDULED BACKUPS                                            │
│                                                              │
│ Full Backup                                                  │
│ ├─ Schedule: Daily at 2:00 AM                               │
│ ├─ Retention: 30 days                                       │
│ ├─ Location: s3://backups/sensei/full/                      │
│ └─ Last: Jan 11, 2026 2:05 AM ✓                            │
│                                                              │
│ Incremental Backup                                           │
│ ├─ Schedule: Every 4 hours                                  │
│ ├─ Retention: 7 days                                        │
│ ├─ Location: s3://backups/sensei/incremental/               │
│ └─ Last: Jan 11, 2026 10:00 AM ✓                           │
│                                                              │
│ ACTIONS                                                      │
│ [Run Full Backup Now]  [Restore from Backup]                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Backup History

```
BACKUP HISTORY
┌─────────────────────────────────────────────────────────────┐
│ Date         │ Type        │ Size    │ Duration │ Status   │
├──────────────┼─────────────┼─────────┼──────────┼──────────┤
│ Jan 11, 2:00 │ Full        │ 12.5 GB │ 45 min   │ ✓ Success│
│ Jan 10, 2:00 │ Full        │ 12.4 GB │ 44 min   │ ✓ Success│
│ Jan 9, 2:00  │ Full        │ 12.3 GB │ 43 min   │ ✓ Success│
│ Jan 8, 2:00  │ Full        │ 12.2 GB │ 42 min   │ ✓ Success│
└──────────────┴─────────────┴─────────┴──────────┴──────────┘
```

### Disaster Recovery

Recovery procedures:

```
DISASTER RECOVERY RUNBOOK

1. ASSESS
   └─ Identify scope of failure

2. NOTIFY
   └─ Alert stakeholders

3. RESTORE
   ├─ Select appropriate backup
   ├─ Restore to recovery environment
   └─ Verify data integrity

4. VALIDATE
   ├─ Run validation scripts
   ├─ Spot-check critical data
   └─ Test key functions

5. SWITCH
   ├─ Update DNS/load balancer
   └─ Monitor closely

6. DOCUMENT
   └─ Post-incident report
```

---

## 12. Performance Tuning

### Performance Dashboard

```
PERFORMANCE METRICS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ API RESPONSE TIMES (P95)                                     │
│ ├─ Current: 145ms                                           │
│ ├─ Target: <200ms                                           │
│ └─ Status: ✓ Good                                           │
│                                                              │
│ PAGE LOAD TIMES (P95)                                        │
│ ├─ Current: 1.8s                                            │
│ ├─ Target: <3s                                              │
│ └─ Status: ✓ Good                                           │
│                                                              │
│ SLOW QUERIES (>1s)                                           │
│ ├─ Last Hour: 3                                             │
│ ├─ Today: 12                                                │
│ └─ [View Details]                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Slow Query Analysis

```
SLOW QUERIES
┌─────────────────────────────────────────────────────────────┐
│ Time     │ Duration │ Query                      │ Action   │
├──────────┼──────────┼────────────────────────────┼──────────┤
│ 10:30 AM │ 2.3s     │ SELECT * FROM audit_logs...│ [Analyze]│
│ 9:45 AM  │ 1.8s     │ SELECT COUNT(*) FROM...   │ [Analyze]│
│ 9:15 AM  │ 1.2s     │ SELECT * FROM production..│ [Analyze]│
└──────────┴──────────┴────────────────────────────┴──────────┘
```

### Caching Configuration

```
CACHE SETTINGS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ REDIS CACHE                                                  │
│ ├─ Status: ✓ Connected                                      │
│ ├─ Memory: 2.1 GB / 4 GB                                    │
│ ├─ Hit Rate: 89%                                            │
│ └─ Keys: 45,231                                             │
│                                                              │
│ CACHE POLICIES                                               │
│ ├─ Session Data: 30 min TTL                                 │
│ ├─ API Responses: 5 min TTL                                 │
│ └─ Static Data: 24 hour TTL                                 │
│                                                              │
│ [Clear All Cache]  [Clear Session Cache]                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Deployment & Updates

### Version Information

```
VERSION INFO
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Current Version: 1.0.5                                      │
│ Released: January 5, 2026                                   │
│                                                              │
│ Components:                                                  │
│ ├─ Frontend: v1.0.5                                         │
│ ├─ Backend: v1.0.5                                          │
│ ├─ API: v1.0.5                                              │
│ └─ Database Schema: v2026.01.10                             │
│                                                              │
│ Latest Available: 1.0.6                                     │
│ [View Changelog] [Schedule Update]                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Process

```
DEPLOYMENT WORKFLOW

1. Pre-Deployment
   ├─ Review changelog
   ├─ Backup database
   ├─ Notify stakeholders
   └─ Schedule maintenance window

2. Deployment
   ├─ Enable maintenance mode
   ├─ Deploy new containers
   ├─ Run migrations
   └─ Verify health checks

3. Post-Deployment
   ├─ Disable maintenance mode
   ├─ Monitor for errors
   ├─ Verify key functions
   └─ Document completion
```

### Kubernetes/Helm Management

For K8s deployments:

```bash
# Check status
kubectl get pods -n sensei

# View logs
kubectl logs -f deployment/sensei-api -n sensei

# Scale
kubectl scale deployment/sensei-api --replicas=5 -n sensei

# Update
helm upgrade sensei ./helm/sensei -f values.yaml
```

---

## 14. Troubleshooting

### Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Slow performance | High response times | Check DB, cache, scale |
| Login failures | 401 errors | Verify auth config, SSO |
| Data sync issues | Stale data | Check integrations |
| Email not sending | Missing notifications | Verify SMTP config |

### Diagnostic Tools

```
DIAGNOSTIC TOOLS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ [Health Check] - Verify all system components               │
│ [Connection Test] - Test database/cache/storage             │
│ [Email Test] - Send test email                              │
│ [API Test] - Check API endpoints                            │
│ [Log Export] - Export logs for analysis                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Health Check Output

```
SYSTEM HEALTH CHECK
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ ✓ API Server - Responding (45ms)                            │
│ ✓ Database - Connected (12ms)                               │
│ ✓ Redis Cache - Connected (2ms)                             │
│ ✓ Object Storage - Accessible (88ms)                        │
│ ✓ Email - SMTP Connection OK                                │
│ ⚠️ Background Jobs - 5 pending (check queue)                 │
│ ✓ Integrations - 4/5 healthy                                │
│                                                              │
│ Overall Status: HEALTHY (1 warning)                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Log Analysis

Search logs for issues:

```bash
# View recent errors
grep ERROR /var/log/sensei/api.log | tail -100

# Search for user
grep "jsmith" /var/log/sensei/audit.log

# Count error types
grep ERROR /var/log/sensei/api.log | cut -d: -f3 | sort | uniq -c
```

---

## 15. Quick Reference

### Keyboard Shortcuts (Admin)

| Shortcut | Action |
|----------|--------|
| `Ctrl + A` | Admin panel |
| `Ctrl + U` | User management |
| `Ctrl + L` | Audit logs |
| `Ctrl + /` | Global search |
| `F5` | Refresh |

### Critical URLs

| Resource | URL |
|----------|-----|
| Admin Panel | `/admin` |
| User Management | `/admin/users` |
| System Settings | `/admin/settings` |
| Audit Logs | `/admin/logs` |
| API Docs | `/api/docs` |
| Health Check | `/health` |

### Emergency Procedures

```
EMERGENCY RUNBOOK

SYSTEM DOWN:
1. Check health endpoints
2. Check K8s pods/containers
3. Check database connectivity
4. Review error logs
5. Rollback if recent deploy
6. Notify stakeholders

SECURITY INCIDENT:
1. Disable affected accounts
2. Revoke API keys if needed
3. Enable additional logging
4. Preserve evidence
5. Notify security team
6. Document timeline

DATA ISSUE:
1. Stop affected processes
2. Assess scope
3. Restore from backup if needed
4. Verify data integrity
5. Resume operations
6. Root cause analysis
```

### Support Escalation

| Level | When | Contact |
|-------|------|---------|
| L1 | Basic issues | Helpdesk |
| L2 | Complex issues | IT Admin |
| L3 | Critical/Data | Sr. IT Admin |
| Vendor | Product issues | Support ticket |

### Weekly IT Admin Checklist

```
WEEKLY CHECKLIST
□ Review security alerts
□ Check backup status
□ Verify integration sync
□ Review slow queries
□ Check disk/storage usage
□ Review pending updates
□ Audit user access
□ Test recovery procedures (monthly)
```

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: IT Administration*
