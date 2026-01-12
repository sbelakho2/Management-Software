# Admin Starter Guide

## Sensei OS - System Administration Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Admin Dashboard](#3-admin-dashboard)
4. [Organizational Setup](#4-organizational-setup)
5. [Master Data Management](#5-master-data-management)
6. [User & Role Administration](#6-user--role-administration)
7. [System Configuration](#7-system-configuration)
8. [Workflow Management](#8-workflow-management)
9. [Notification & Alert Setup](#9-notification--alert-setup)
10. [Import & Export Tools](#10-import--export-tools)
11. [Audit & Compliance](#11-audit--compliance)
12. [Report Administration](#12-report-administration)
13. [Integration Configuration](#13-integration-configuration)
14. [Training & Documentation](#14-training--documentation)
15. [Quick Reference](#15-quick-reference)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use it to validate that project access controls and privacy settings match your security policy.
- Verify role permissions for **edit/comment/invite/delete** are applied as intended.
- Use the activity log for investigations and compliance/audit requests.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role as System Admin

As a System Administrator in Sensei OS, you are responsible for **configuring and maintaining** the application to support business operations. Your key responsibilities:

- **Configure the system** to match business processes
- **Manage master data** (items, BOMs, routings, etc.)
- **Administer users and roles** for proper access control
- **Set up workflows** for approvals and processes
- **Maintain system health** and data quality
- **Support end users** with configuration changes

### Admin Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Organization Setup | Full | Sites, departments, work centers |
| Master Data | Full | Items, BOMs, routings, resources |
| User Management | Full | Create, modify, assign roles |
| Role Management | Full | Define permissions |
| Workflow Config | Full | Approval flows, automations |
| System Settings | Full | Application configuration |
| Reports | Full | Create, modify, schedule |
| Integrations | Configure | Set up connections |

### Admin vs IT Admin

```
ADMIN RESPONSIBILITIES

SYSTEM ADMIN (You)              IT ADMIN
├─ Business configuration       ├─ Infrastructure
├─ Master data                  ├─ Security policies
├─ User setup                   ├─ Database admin
├─ Workflows                    ├─ Backups
├─ Reports                      ├─ Integrations (tech)
└─ End-user support             └─ System monitoring
```

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter your admin credentials
3. Complete MFA setup
4. Access Admin Console

### Initial Setup Tasks

- [ ] Review organization structure
- [ ] Verify master data accuracy
- [ ] Check user access setup
- [ ] Review workflow configurations
- [ ] Test key processes
- [ ] Document custom configurations

### Admin Console Access

```
┌─────────────────────────────────────────────────────────────┐
│               ADMIN CONSOLE                                  │
│               System Administration                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ ORGANIZATION │  │ MASTER DATA  │  │    USERS     │       │
│  │   Setup      │  │  Management  │  │    Roles     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  WORKFLOWS   │  │   SYSTEM     │  │   REPORTS    │       │
│  │  Approvals   │  │   Settings   │  │   Config     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                              │
│  QUICK STATS                                                 │
│  ├─ Users: 152 active                                       │
│  ├─ Items: 2,450 active                                     │
│  ├─ Pending Approvals: 8                                    │
│  └─ Last Config Change: Jan 10, 2026 by admin              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Admin Dashboard

### Dashboard Overview

Your admin view shows system status:

```
ADMIN DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SYSTEM HEALTH                                                │
│ ├─ Status: ✓ All systems operational                        │
│ ├─ Users Online: 45                                         │
│ ├─ Pending Tasks: 12                                        │
│ └─ Last Sync: 5 min ago                                     │
│                                                              │
│ RECENT ADMIN ACTIVITY                                        │
│ ├─ Jan 11: User jsmith password reset                       │
│ ├─ Jan 11: New item WIDGET-C300 created                     │
│ ├─ Jan 10: Workflow "PO Approval" modified                  │
│ └─ Jan 10: Role "Quality Inspector" updated                 │
│                                                              │
│ PENDING ACTIONS                                              │
│ ├─ 3 users pending activation                               │
│ ├─ 5 items pending approval                                 │
│ └─ 2 workflow requests                                      │
│                                                              │
│ DATA QUALITY ALERTS                                          │
│ ├─ ⚠️ 12 items missing cost data                            │
│ └─ ⚠️ 5 BOMs with inactive components                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Navigating Admin Functions

```
ADMIN MENU STRUCTURE

Admin Console
├── Organization
│   ├── Company Setup
│   ├── Sites & Locations
│   ├── Departments
│   └── Work Centers
├── Master Data
│   ├── Items
│   ├── Bills of Material
│   ├── Routings
│   ├── Resources
│   └── Customers/Vendors
├── Users & Access
│   ├── User Management
│   ├── Roles & Permissions
│   └── Security Settings
├── Configuration
│   ├── System Settings
│   ├── Workflows
│   ├── Notifications
│   └── Numbering Schemes
├── Tools
│   ├── Import/Export
│   ├── Bulk Updates
│   └── Data Validation
└── Reports
    ├── Report Builder
    └── Scheduled Reports
```

---

## 4. Organizational Setup

### Company Structure

Access: **Admin → Organization → Company Setup**

```
COMPANY STRUCTURE
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ COMPANY: Your Company, Inc.                                  │
│                                                              │
│ HIERARCHY                                                    │
│ └── Company (Legal Entity)                                  │
│     ├── Site: Main Plant                                    │
│     │   ├── Dept: Production                                │
│     │   │   ├── Work Center: Assembly                       │
│     │   │   ├── Work Center: Machining                      │
│     │   │   └── Work Center: Finishing                      │
│     │   ├── Dept: Quality                                   │
│     │   ├── Dept: Warehouse                                 │
│     │   └── Dept: Maintenance                               │
│     │                                                       │
│     └── Site: Distribution Center                           │
│         └── Dept: Shipping                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Managing Sites

```
┌─────────────────────────────────────────────────────────────┐
│  SITE: Main Plant                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ GENERAL                                                      │
│ Site Code:     [MAIN           ]                            │
│ Name:          [Main Manufacturing Plant     ]              │
│ Address:       [123 Industrial Pkwy          ]              │
│                [Newark, NJ 07102             ]              │
│ Time Zone:     [America/New_York        ▼]                  │
│                                                              │
│ OPERATIONS                                                   │
│ Calendar:      [Standard - M-F, 3 shifts ▼]                 │
│ Default Warehouse: [WH-MAIN             ▼]                  │
│ Cost Center:   [CC-1000                 ▼]                  │
│                                                              │
│ CONTACTS                                                     │
│ Site Manager:  [John Smith         ▼]                       │
│ Phone:         [555-123-4567             ]                  │
│                                                              │
│ [Save]  [Deactivate Site]                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Work Centers

Configure production work centers:

```
WORK CENTERS
┌─────────────────────────────────────────────────────────────┐
│ Code      │ Name          │ Site  │ Dept     │ Status      │
├───────────┼───────────────┼───────┼──────────┼─────────────┤
│ WC-ASM-01 │ Assembly 1    │ MAIN  │ Prod     │ Active      │
│ WC-ASM-02 │ Assembly 2    │ MAIN  │ Prod     │ Active      │
│ WC-MCH-01 │ CNC Machining │ MAIN  │ Prod     │ Active      │
│ WC-MCH-02 │ Manual Mach   │ MAIN  │ Prod     │ Active      │
│ WC-FIN-01 │ Finishing     │ MAIN  │ Prod     │ Active      │
│ WC-QC-01  │ Quality Lab   │ MAIN  │ Quality  │ Active      │
└───────────┴───────────────┴───────┴──────────┴─────────────┘

[+ Add Work Center]
```

---

## 5. Master Data Management

### Item Master

Access: **Admin → Master Data → Items**

```
ITEM MASTER
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search items...    [Filter ▼] [+ Add Item] [Import]      │
├─────────────────────────────────────────────────────────────┤
│ Item #      │ Description      │ Type │ UOM │ Cost  │Status│
├─────────────┼──────────────────┼──────┼─────┼───────┼──────┤
│ WIDGET-A100 │ Widget Type A    │ MFG  │ EA  │ $15.25│Active│
│ WIDGET-B200 │ Widget Type B    │ MFG  │ EA  │ $28.50│Active│
│ COMP-001    │ Component 1      │ PURCH│ EA  │ $3.50 │Active│
│ COMP-002    │ Component 2      │ PURCH│ EA  │ $2.25 │Active│
│ RAW-STEEL   │ Steel Bar Stock  │ RAW  │ LB  │ $2.45 │Active│
└─────────────┴──────────────────┴──────┴─────┴───────┴──────┘
```

### Item Detail

```
┌─────────────────────────────────────────────────────────────┐
│  ITEM: WIDGET-A100                                           │
│  Status: Active                                              │
├─────────────────────────────────────────────────────────────┤
│ TABS: [General] [Inventory] [Planning] [Cost] [Documents]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ GENERAL INFORMATION                                          │
│ Item Number:     [WIDGET-A100           ]                   │
│ Description:     [Widget Type A Standard    ]               │
│ Extended Desc:   [Standard widget for customer assemblies]  │
│                                                              │
│ Classification:                                              │
│ ├─ Item Type:    [Manufactured      ▼]                      │
│ ├─ Item Class:   [Finished Goods    ▼]                      │
│ ├─ Product Line: [Widgets           ▼]                      │
│ └─ ABC Class:    [A - High Volume   ▼]                      │
│                                                              │
│ Units:                                                       │
│ ├─ Stock UOM:    [Each (EA)         ▼]                      │
│ ├─ Purchase UOM: [Each (EA)         ▼]                      │
│ └─ Sell UOM:     [Each (EA)         ▼]                      │
│                                                              │
│ ATTRIBUTES                                                   │
│ ├─ Weight:       [0.5    ] LB                               │
│ ├─ Dimensions:   [4 × 3 × 2] inches                         │
│ └─ Lead Time:    [10     ] days                             │
│                                                              │
│ [Save] [Copy Item] [Deactivate]                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Bills of Material (BOM)

```
BOM: WIDGET-A100
┌─────────────────────────────────────────────────────────────┐
│ Parent: WIDGET-A100 - Widget Type A                         │
│ Revision: A | Effective: Jan 1, 2025 | Status: Active       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ COMPONENTS                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Seq│ Item       │ Description  │ Qty │ UOM │ Scrap    │ │
│ ├────┼────────────┼──────────────┼─────┼─────┼──────────┤ │
│ │ 10 │ COMP-001   │ Component 1  │ 2   │ EA  │ 1%       │ │
│ │ 20 │ COMP-002   │ Component 2  │ 1   │ EA  │ 0%       │ │
│ │ 30 │ COMP-003   │ Component 3  │ 4   │ EA  │ 2%       │ │
│ │ 40 │ RAW-STEEL  │ Steel Stock  │ 0.5 │ LB  │ 5%       │ │
│ │ 50 │ HARDWARE-A │ Hardware Kit │ 1   │ EA  │ 0%       │ │
│ │    │ [+ Add Component]                                 │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ TOTAL COMPONENT COST: $8.75                                  │
│                                                              │
│ [Save] [New Revision] [Copy BOM] [BOM Report]               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Routings

```
ROUTING: WIDGET-A100
┌─────────────────────────────────────────────────────────────┐
│ Item: WIDGET-A100 - Widget Type A                           │
│ Routing: Standard | Status: Active                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ OPERATIONS                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Op │ Work Center │ Operation     │ Setup │ Run   │ Unit │ │
│ ├────┼─────────────┼───────────────┼───────┼───────┼──────┤ │
│ │ 10 │ WC-MCH-01   │ Machine Base  │ 30 min│ 5 min │ /EA  │ │
│ │ 20 │ WC-ASM-01   │ Assembly      │ 15 min│ 8 min │ /EA  │ │
│ │ 30 │ WC-FIN-01   │ Finishing     │ 10 min│ 3 min │ /EA  │ │
│ │ 40 │ WC-QC-01    │ Final QC      │ 5 min │ 2 min │ /EA  │ │
│ │    │ [+ Add Operation]                                 │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ TOTALS                                                       │
│ ├─ Total Setup: 60 min                                      │
│ ├─ Total Run: 18 min/unit                                   │
│ └─ Labor Cost: $6.50/unit                                   │
│                                                              │
│ [Save] [Copy Routing]                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. User & Role Administration

### User Management

Access: **Admin → Users & Access → User Management**

```
USER ADMINISTRATION
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search...    [Active ▼] [Dept ▼] [+ Add User] [Import]   │
├─────────────────────────────────────────────────────────────┤
│ Name          │ Email           │ Role       │ Dept    │ St │
├───────────────┼─────────────────┼────────────┼─────────┼────┤
│ John Smith    │ jsmith@co.com   │ Operator   │ Prod    │ ✓  │
│ Maria Garcia  │ mgarcia@co.com  │ Supervisor │ Prod    │ ✓  │
│ David Brown   │ dbrown@co.com   │ Manager    │ Prod    │ ✓  │
│ Sarah Wilson  │ swilson@co.com  │ Quality    │ Quality │ ✓  │
│ Mike Johnson  │ mjohnson@co.com │ Operator   │ Prod    │ ⏳ │
└───────────────┴─────────────────┴────────────┴─────────┴────┘

Status: ✓ Active  ⏳ Pending  ✗ Disabled
```

### Creating Users

```
┌─────────────────────────────────────────────────────────────┐
│  CREATE NEW USER                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ PERSONAL INFORMATION                                         │
│ First Name:      [                    ]                     │
│ Last Name:       [                    ]                     │
│ Email:           [                    ]                     │
│ Employee ID:     [                    ]                     │
│                                                              │
│ ORGANIZATIONAL                                               │
│ Site:            [Main Plant          ▼]                    │
│ Department:      [Production          ▼]                    │
│ Manager:         [Maria Garcia        ▼]                    │
│ Shift:           [Day Shift           ▼]                    │
│                                                              │
│ ACCESS                                                       │
│ Primary Role:    [Operator            ▼]                    │
│ Additional Roles:                                            │
│   ☐ Quality Entry                                           │
│   ☐ Maintenance Request                                     │
│   ☐ Training View                                           │
│                                                              │
│ CREDENTIALS                                                  │
│ ☑ Send welcome email with temp password                     │
│ ☑ Require password change on first login                    │
│ ☐ Set password manually                                     │
│                                                              │
│ [Cancel]  [Create User]                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Role Configuration

```
ROLE: Supervisor
┌─────────────────────────────────────────────────────────────┐
│ Role Name:      [Supervisor                    ]            │
│ Description:    [Production floor supervision  ]            │
│ Assigned Users: 12                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ PERMISSIONS                                                  │
│                                                              │
│ PRODUCTION                                                   │
│ ☑ View work orders                                          │
│ ☑ Create/edit work orders                                   │
│ ☑ Report production                                         │
│ ☑ Approve production data                                   │
│ ☐ Delete work orders                                        │
│                                                              │
│ TEAM MANAGEMENT                                              │
│ ☑ View team members                                         │
│ ☑ View/approve time entries                                 │
│ ☐ Edit employee records                                     │
│ ☐ Manage compensation                                       │
│                                                              │
│ QUALITY                                                      │
│ ☑ View quality data                                         │
│ ☑ Record inspections                                        │
│ ☑ Create NCRs                                               │
│ ☐ Close NCRs                                                │
│                                                              │
│ REPORTING                                                    │
│ ☑ View production reports                                   │
│ ☑ View team reports                                         │
│ ☐ View financial reports                                    │
│ ☐ Create custom reports                                     │
│                                                              │
│ [Save Role]  [Copy Role]                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. System Configuration

### General Settings

Access: **Admin → Configuration → System Settings**

```
SYSTEM SETTINGS
┌─────────────────────────────────────────────────────────────┐
│ TABS: [General] [Production] [Quality] [Inventory] [HR]     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ GENERAL                                                      │
│                                                              │
│ Company Settings:                                            │
│ ├─ Company Name:     [Your Company, Inc.         ]          │
│ ├─ Default Language: [English                ▼]             │
│ ├─ Time Zone:        [America/New_York       ▼]             │
│ ├─ Date Format:      [MM/DD/YYYY             ▼]             │
│ ├─ Time Format:      [12 Hour                ▼]             │
│ └─ Currency:         [USD                    ▼]             │
│                                                              │
│ Session Settings:                                            │
│ ├─ Timeout:          [30     ] minutes                      │
│ └─ Auto-Save:        [5      ] minutes                      │
│                                                              │
│ Features:                                                    │
│ ├─ ☑ Enable Mobile Access                                   │
│ ├─ ☑ Enable Offline Mode                                    │
│ ├─ ☐ Enable AI Insights                                     │
│ └─ ☑ Enable Notifications                                   │
│                                                              │
│ [Save Changes]                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Numbering Schemes

Configure auto-numbering:

```
NUMBERING SCHEMES
┌─────────────────────────────────────────────────────────────┐
│ Document Type    │ Prefix │ Digits│ Next #  │ Example      │
├──────────────────┼────────┼───────┼─────────┼──────────────┤
│ Work Order       │ WO-    │ 6     │ 12500   │ WO-012500    │
│ Sales Order      │ SO-    │ 5     │ 8765    │ SO-08765     │
│ Purchase Order   │ PO-    │ 5     │ 4532    │ PO-04532     │
│ Item             │ ITEM-  │ 6     │ 2451    │ ITEM-002451  │
│ NCR              │ NCR-   │ 5     │ 890     │ NCR-00890    │
│ Employee         │ EMP-   │ 4     │ 155     │ EMP-0155     │
└──────────────────┴────────┴───────┴─────────┴──────────────┘

[+ Add Scheme]  [Edit]
```

### List Values (Lookups)

Manage dropdown values:

```
LIST VALUES
┌─────────────────────────────────────────────────────────────┐
│ List: Defect Types                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Values:                                                      │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Code        │ Display Text     │ Active │ Seq          │ │
│ ├─────────────┼──────────────────┼────────┼──────────────┤ │
│ │ DIM         │ Dimensional      │ ✓      │ 10           │ │
│ │ COS         │ Cosmetic         │ ✓      │ 20           │ │
│ │ FUN         │ Functional       │ ✓      │ 30           │ │
│ │ MAT         │ Material         │ ✓      │ 40           │ │
│ │ ASM         │ Assembly Error   │ ✓      │ 50           │ │
│ │ DOC         │ Documentation    │ ✓      │ 60           │ │
│ │             │ [+ Add Value]    │        │              │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Save List]                                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Workflow Management

### Workflow Configuration

Access: **Admin → Configuration → Workflows**

```
WORKFLOWS
┌─────────────────────────────────────────────────────────────┐
│ Workflow            │ Type     │ Status  │ Triggers        │
├─────────────────────┼──────────┼─────────┼─────────────────┤
│ PO Approval         │ Approval │ Active  │ PO Created      │
│ NCR Approval        │ Approval │ Active  │ NCR Created     │
│ Time Off Request    │ Approval │ Active  │ Request Submit  │
│ Item Setup          │ Approval │ Active  │ New Item Created│
│ Work Order Close    │ Process  │ Active  │ WO Complete     │
└─────────────────────┴──────────┴─────────┴─────────────────┘

[+ New Workflow]
```

### Workflow Designer

```
┌─────────────────────────────────────────────────────────────┐
│  WORKFLOW: Purchase Order Approval                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ TRIGGER: Purchase Order Created                              │
│                                                              │
│ FLOW:                                                        │
│                                                              │
│ ┌─────────┐    ┌─────────────┐    ┌─────────────┐          │
│ │ START   │───▶│ Amount      │───▶│ Assign      │          │
│ │ (PO     │    │ Check       │    │ Approver    │          │
│ │ Created)│    │             │    │             │          │
│ └─────────┘    └──────┬──────┘    └──────┬──────┘          │
│                       │                  │                   │
│              ┌────────┴────────┐         │                   │
│              ▼                 ▼         ▼                   │
│        ┌──────────┐      ┌──────────┐ ┌──────────┐          │
│        │ < $1,000 │      │ ≥ $1,000 │ │ Wait for │          │
│        │ Auto-    │      │ Manager  │ │ Approval │          │
│        │ Approve  │      │ Approval │ └────┬─────┘          │
│        └────┬─────┘      └────┬─────┘      │                │
│             │                 │            │                 │
│             │     ┌───────────┘            │                 │
│             ▼     ▼                        ▼                 │
│        ┌──────────────┐            ┌─────────────┐          │
│        │   APPROVED   │◀───────────│  Approved?  │          │
│        │   (Release)  │    Yes     └──────┬──────┘          │
│        └──────────────┘                   │ No               │
│                                           ▼                  │
│                                    ┌─────────────┐          │
│                                    │  REJECTED   │          │
│                                    │  (Return)   │          │
│                                    └─────────────┘          │
│                                                              │
│ APPROVAL LEVELS                                              │
│ ├─ Level 1: < $1,000 - Auto-approve                         │
│ ├─ Level 2: $1,000 - $10,000 - Dept Manager                 │
│ ├─ Level 3: $10,000 - $50,000 - Operations Director         │
│ └─ Level 4: > $50,000 - CFO                                 │
│                                                              │
│ [Save Workflow]  [Test]  [Deactivate]                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Notification & Alert Setup

### Notification Configuration

Access: **Admin → Configuration → Notifications**

```
NOTIFICATION SETTINGS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ NOTIFICATION CHANNELS                                        │
│ ├─ ☑ Email                                                  │
│ ├─ ☑ In-App                                                 │
│ ├─ ☑ Mobile Push                                            │
│ └─ ☐ SMS (Premium)                                          │
│                                                              │
│ NOTIFICATION RULES                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Event              │ Email│ App │ Push│ Recipients       │ │
│ ├────────────────────┼──────┼─────┼─────┼──────────────────┤ │
│ │ Approval Required  │  ✓   │  ✓  │  ✓  │ Approver         │ │
│ │ Approval Completed │  ✓   │  ✓  │  ☐  │ Requester        │ │
│ │ NCR Created        │  ✓   │  ✓  │  ✓  │ Quality Team     │ │
│ │ Andon Triggered    │  ☐   │  ✓  │  ✓  │ Maint + Super    │ │
│ │ Order Shipped      │  ✓   │  ✓  │  ☐  │ Sales Rep        │ │
│ │ Daily Digest       │  ✓   │  ☐  │  ☐  │ Managers         │ │
│ └────────────────────┴──────┴─────┴─────┴──────────────────┘ │
│                                                              │
│ [+ Add Rule]                                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Email Templates

```
EMAIL TEMPLATE: Approval Required
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Subject: Action Required: {{document_type}} Approval        │
│                                                              │
│ Body:                                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Hello {{approver_name}},                                │ │
│ │                                                         │ │
│ │ A new {{document_type}} requires your approval:        │ │
│ │                                                         │ │
│ │ Document: {{document_number}}                           │ │
│ │ Requested By: {{requester_name}}                        │ │
│ │ Date: {{request_date}}                                  │ │
│ │ Amount: {{amount}}                                      │ │
│ │                                                         │ │
│ │ Description:                                            │ │
│ │ {{description}}                                         │ │
│ │                                                         │ │
│ │ [Approve] [Reject] [View Details]                      │ │
│ │                                                         │ │
│ │ Best regards,                                           │ │
│ │ Sensei OS                                               │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Available Variables: {{...}}  [Insert Variable]             │
│                                                              │
│ [Save Template]  [Preview]  [Send Test]                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Import & Export Tools

### Data Import

Access: **Admin → Tools → Import/Export**

```
DATA IMPORT
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Step 1: Select Data Type                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ○ Items                                                 │ │
│ │ ○ Bills of Material                                     │ │
│ │ ○ Routings                                              │ │
│ │ ○ Customers                                             │ │
│ │ ○ Vendors                                               │ │
│ │ ● Users                                                 │ │
│ │ ○ Inventory Counts                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Step 2: Download Template                                    │
│ [📥 Download Template]  [📄 View Format Guide]              │
│                                                              │
│ Step 3: Upload File                                          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │     📁 Drag & Drop CSV/Excel file here                 │ │
│ │            or [Browse Files]                            │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Step 4: Validate & Import                                    │
│ [Validate Data]  [Import]                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Validation Results

```
IMPORT VALIDATION - Users
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ File: user_import_2026-01-11.csv                            │
│ Total Rows: 25                                               │
│                                                              │
│ VALIDATION RESULTS                                           │
│ ├─ ✓ Valid: 22                                              │
│ ├─ ⚠️ Warnings: 2                                           │
│ └─ ✗ Errors: 1                                              │
│                                                              │
│ ISSUES                                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Row │ Field    │ Issue              │ Severity          │ │
│ ├─────┼──────────┼────────────────────┼───────────────────┤ │
│ │ 5   │ Email    │ Duplicate email    │ ✗ Error          │ │
│ │ 12  │ Dept     │ Dept not found     │ ⚠️ Warning        │ │
│ │ 18  │ Role     │ Role typo, matched │ ⚠️ Warning        │ │
│ └─────┴──────────┴────────────────────┴───────────────────┘ │
│                                                              │
│ [Download Error Report]                                      │
│                                                              │
│ Import Options:                                              │
│ ☑ Skip rows with errors                                     │
│ ☐ Apply warnings (auto-correct)                             │
│                                                              │
│ [Back]  [Import Valid Records (22)]                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Data Export

Export data for analysis or backup:

```
DATA EXPORT
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Export Type: [Items           ▼]                            │
│                                                              │
│ Filters:                                                     │
│ ├─ Status: [Active Only ▼]                                  │
│ ├─ Type: [All ▼]                                            │
│ └─ Date Range: [All Time ▼]                                 │
│                                                              │
│ Columns to Export:                                           │
│ ├─ ☑ Item Number                                            │
│ ├─ ☑ Description                                            │
│ ├─ ☑ Type                                                   │
│ ├─ ☑ UOM                                                    │
│ ├─ ☑ Cost                                                   │
│ ├─ ☐ Extended Description                                   │
│ └─ ☐ Created Date                                           │
│                                                              │
│ Format: [Excel ▼]                                           │
│                                                              │
│ [Export]                                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Audit & Compliance

### Audit Log Access

Access: **Admin → Audit → Audit Log**

```
AUDIT LOG
┌─────────────────────────────────────────────────────────────┐
│ Filter: [All ▼] User: [All ▼] Date: [Today ▼] [Search...]  │
├─────────────────────────────────────────────────────────────┤
│ Time     │ User     │ Action      │ Object      │ Details  │
├──────────┼──────────┼─────────────┼─────────────┼──────────┤
│ 10:45 AM │ admin    │ Update      │ User:jsmith │ Role chg │
│ 10:30 AM │ mgarcia  │ Create      │ WO-012501   │          │
│ 10:15 AM │ jsmith   │ Login       │ -           │ Success  │
│ 10:00 AM │ admin    │ Update      │ Item:WDG-A  │ Cost chg │
│ 9:45 AM  │ system   │ Sync        │ Integration │ SAP sync │
└──────────┴──────────┴─────────────┴─────────────┴──────────┘

[Export Audit Log]  [Archive Old Logs]
```

### Change History

View detailed changes:

```
CHANGE HISTORY: Item WIDGET-A100
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Date       │ User   │ Field        │ Old Value │ New Value │
├────────────┼────────┼──────────────┼───────────┼───────────┤
│ Jan 11     │ admin  │ Standard Cost│ $15.00    │ $15.25    │
│ Jan 5      │ admin  │ Lead Time    │ 12 days   │ 10 days   │
│ Dec 15     │ admin  │ Description  │ Widget A  │ Widget... │
│ Oct 1      │ system │ Created      │ -         │ -         │
└────────────┴────────┴──────────────┴───────────┴───────────┘
│                                                              │
│ [Export History]                                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Report Administration

### Report Builder

Access: **Admin → Reports → Report Builder**

```
REPORT BUILDER
┌─────────────────────────────────────────────────────────────┐
│ Report Name: [Production Summary by Cell            ]       │
│ Description: [Daily production output by work cell  ]       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ DATA SOURCE                                                  │
│ Primary: [Production Entries    ▼]                          │
│ Related: [+ Add Related Data]                                │
│                                                              │
│ COLUMNS                                                      │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Field              │ Display Name │ Aggregate│ Format │  │
│ ├────────────────────┼──────────────┼──────────┼────────┤  │
│ │ Work Center        │ Cell         │ Group By │        │  │
│ │ Production Date    │ Date         │ Group By │ Date   │  │
│ │ Quantity           │ Output       │ Sum      │ Number │  │
│ │ Scrap Quantity     │ Scrap        │ Sum      │ Number │  │
│ │ Labor Hours        │ Hours        │ Sum      │ Decimal│  │
│ └────────────────────┴──────────────┴──────────┴────────┘  │
│ [+ Add Column]                                               │
│                                                              │
│ FILTERS                                                      │
│ ├─ Date Range: [Parameter - User Selected]                  │
│ └─ Work Center: [Parameter - Optional]                      │
│                                                              │
│ [Preview]  [Save Report]  [Save & Schedule]                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Report Scheduling

```
SCHEDULE REPORT: Production Summary
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SCHEDULE                                                     │
│ Frequency:    [Daily           ▼]                           │
│ Time:         [7:00 AM         ▼]                           │
│ Days:         ☑ Mon ☑ Tue ☑ Wed ☑ Thu ☑ Fri ☐ Sat ☐ Sun   │
│                                                              │
│ PARAMETERS                                                   │
│ Date Range:   [Previous Day    ▼]                           │
│ Work Center:  [All             ▼]                           │
│                                                              │
│ DISTRIBUTION                                                 │
│ Format:       [PDF              ▼]                          │
│ Recipients:                                                  │
│ ├─ ☑ Production Managers                                    │
│ ├─ ☑ Plant Manager                                          │
│ ├─ ☐ Executives                                             │
│ └─ [+ Add Recipient]                                        │
│                                                              │
│ [Save Schedule]                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Integration Configuration

### Integration Setup

Access: **Admin → Configuration → Integrations**

```
INTEGRATIONS
┌─────────────────────────────────────────────────────────────┐
│ Integration     │ Type      │ Status  │ Last Sync │ Action │
├─────────────────┼───────────┼─────────┼───────────┼────────┤
│ SAP ERP         │ ERP       │ ✓ Active│ 10 min    │[Config]│
│ QuickBooks      │ Finance   │ ⏸ Paused│ 2 days    │[Config]│
│ Kronos          │ Time/Att  │ ✓ Active│ 15 min    │[Config]│
│ Slack           │ Notify    │ ✓ Active│ Real-time │[Config]│
└─────────────────┴───────────┴─────────┴───────────┴────────┘

[+ Add Integration]
```

### Field Mapping

```
FIELD MAPPING: SAP → Sensei OS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Entity: Customers                                            │
│                                                              │
│ FIELD MAPPINGS                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ SAP Field        │ Sensei Field    │ Transform         │ │
│ ├──────────────────┼─────────────────┼───────────────────┤ │
│ │ KUNNR            │ customer_code   │ None              │ │
│ │ NAME1            │ name            │ None              │ │
│ │ STRAS            │ address_line1   │ None              │ │
│ │ ORT01            │ city            │ None              │ │
│ │ REGIO            │ state           │ Lookup: regions   │ │
│ │ PSTLZ            │ postal_code     │ None              │ │
│ │ LAND1            │ country         │ Lookup: countries │ │
│ └──────────────────┴─────────────────┴───────────────────┘ │
│                                                              │
│ [+ Add Mapping]                                              │
│                                                              │
│ SYNC SETTINGS                                                │
│ Direction:  [SAP → Sensei     ▼]                            │
│ Frequency:  [Every 15 min     ▼]                            │
│ On Conflict:[Sensei Wins      ▼]                            │
│                                                              │
│ [Save Mapping]  [Test Sync]                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. Training & Documentation

### Help Documentation

Maintain user documentation:

```
HELP DOCUMENTATION
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ DOCUMENTATION CATEGORIES                                     │
│ ├─ Getting Started (8 articles)                             │
│ ├─ Production (12 articles)                                 │
│ ├─ Quality (10 articles)                                    │
│ ├─ Inventory (8 articles)                                   │
│ ├─ HR & Time (6 articles)                                   │
│ └─ Admin Guide (15 articles)                                │
│                                                              │
│ RECENT UPDATES                                               │
│ ├─ Jan 10: Updated "Work Order Entry" procedure            │
│ ├─ Jan 5: New "Andon Response" article                      │
│ └─ Jan 2: Updated "New Employee Onboarding"                 │
│                                                              │
│ [+ Add Article]  [Manage Categories]  [Analytics]           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Training Management

Track training materials:

```
TRAINING MATERIALS
┌─────────────────────────────────────────────────────────────┐
│ Course            │ Type   │ Duration│ Assigned │ Completed│
├───────────────────┼────────┼─────────┼──────────┼──────────┤
│ System Basics     │ Video  │ 30 min  │ All Users│ 145/152  │
│ Production Entry  │ Video  │ 20 min  │ Prod     │ 95/98    │
│ Quality Inspect   │ Video  │ 25 min  │ Quality  │ 18/20    │
│ Supervisor Tools  │ Course │ 1 hour  │ Supers   │ 11/12    │
│ Admin Training    │ Course │ 2 hours │ Admins   │ 3/5      │
└───────────────────┴────────┴─────────┴──────────┴──────────┘

[+ Add Course]  [Assign Training]  [View Completion Report]
```

---

## 15. Quick Reference

### Admin Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + U` | User management |
| `Ctrl + I` | Items |
| `Ctrl + W` | Workflows |
| `Ctrl + L` | Audit log |
| `Ctrl + /` | Search |

### Common Admin Tasks

| Task | Navigation |
|------|------------|
| Add user | Admin → Users → + Add |
| Add item | Admin → Master Data → Items → + Add |
| Reset password | Users → [User] → Reset Password |
| Add BOM | Master Data → BOMs → + Add |
| Configure workflow | Configuration → Workflows |
| Import data | Tools → Import/Export |

### Admin Checklist

```
WEEKLY ADMIN CHECKLIST
□ Review pending user requests
□ Check data quality alerts
□ Review workflow backlog
□ Audit log review (security)
□ Backup verification
□ Integration sync status
□ Help desk tickets review

MONTHLY
□ User access review
□ Role permission audit
□ Master data cleanup
□ Report usage analysis
□ Training completion check
□ System configuration review
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| User can't login | Reset password, check status |
| Missing permissions | Review role assignment |
| Data not syncing | Check integration status |
| Report error | Verify data source, filters |
| Workflow stuck | Check approver, escalate |

### Support Contacts

| Need | Contact |
|------|---------|
| IT Admin | ext. 1100 |
| Vendor Support | support@sensei-os.com |
| Help Desk | ext. 4000 |
| Training | ext. 3500 |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: System Administration*
