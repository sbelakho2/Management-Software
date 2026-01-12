# Auditor Starter Guide

## Sensei OS - Auditor Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Auditor Dashboard](#3-auditor-dashboard)
4. [Audit Planning](#4-audit-planning)
5. [Conducting Audits](#5-conducting-audits)
6. [Audit Checklists](#6-audit-checklists)
7. [Finding Management](#7-finding-management)
8. [Evidence Collection](#8-evidence-collection)
9. [Report Generation](#9-report-generation)
10. [Corrective Action Tracking](#10-corrective-action-tracking)
11. [Compliance Monitoring](#11-compliance-monitoring)
12. [Data Access & Analysis](#12-data-access--analysis)
13. [Audit History & Trends](#13-audit-history--trends)
14. [External Audit Support](#14-external-audit-support)
15. [Quick Reference](#15-quick-reference)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use the activity log as an audit trail for who changed what and when.
- Review issues and milestones to understand risk handling and corrective actions.
- Use comments for supporting evidence and decision rationale.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role as Auditor

As an Auditor in Sensei OS, you have **independent access** to verify compliance and process effectiveness. Your access is designed for:

- **Read-only visibility** across all operational data
- **Audit management** tools for planning and execution
- **Finding documentation** with evidence attachment
- **Corrective action tracking** for closure verification
- **Report generation** for audit results
- **Trend analysis** for systemic issues

### Auditor Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Operational Data | Read Only | View all transactions, no edit |
| Audit Management | Full | Plan, execute, report audits |
| Findings | Full | Create, track, close findings |
| Evidence | Full | Attach, store, retrieve |
| Reports | Audit Reports | Generate audit-specific reports |
| System Config | View Only | See settings, no changes |
| User Data | View Only | See access, activity logs |

### Auditor Independence

```
AUDITOR ACCESS MODEL

┌─────────────────────────────────────────────────────────────┐
│                    AUDITOR ROLE                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  READ ACCESS (All Areas)        WRITE ACCESS (Audit Only)   │
│  ├─ Production Data             ├─ Audit Plans              │
│  ├─ Quality Records             ├─ Findings                 │
│  ├─ Inventory Data              ├─ Evidence                 │
│  ├─ HR Records                  ├─ Audit Reports            │
│  ├─ Financial Data              └─ Corrective Actions       │
│  ├─ Maintenance                                              │
│  ├─ Audit Logs                                              │
│  └─ System Config                                           │
│                                                              │
│  RESTRICTED                                                  │
│  ├─ Cannot modify operational data                          │
│  ├─ Cannot change system settings                           │
│  └─ Cannot modify user access                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter your auditor credentials
3. Complete MFA setup (required)
4. Access Auditor Dashboard

### Initial Setup Tasks

- [ ] Review audit schedule
- [ ] Check assigned audits
- [ ] Review open findings
- [ ] Set notification preferences
- [ ] Familiarize with data access
- [ ] Review audit procedures

### Your Auditor Home Screen

```
┌─────────────────────────────────────────────────────────────┐
│               AUDITOR DASHBOARD                              │
│               January 11, 2026 - 10:15 AM                   │
├─────────────────────────────────────────────────────────────┤
│  AUDIT STATUS                                                │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │ Planned    │ │ In Progress│ │ Open       │ │ Overdue    ││
│  │     3      │ │     1      │ │ Findings   │ │ Actions    ││
│  │  audits    │ │  audit     │ │    12      │ │     2      ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘│
├─────────────────────────────────────────────────────────────┤
│  CURRENT AUDIT                                               │
│  Quality Management System Audit - Q1 2026                  │
│  Status: In Progress | Due: Jan 31, 2026                    │
│  Progress: ████████████░░░░░░ 65%                           │
│                                                              │
│  UPCOMING AUDITS                                             │
│  ├─ Jan 25: Production Control Audit                        │
│  ├─ Feb 5: Inventory Accuracy Audit                         │
│  └─ Feb 20: Safety Program Audit                            │
│                                                              │
│  RECENT ACTIVITY                                             │
│  ├─ Finding F-2026-042 closed (Jan 10)                      │
│  └─ CA-2026-018 action due tomorrow                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Auditor Dashboard

### Dashboard Widgets

#### Audit Calendar
View scheduled audits:

```
AUDIT CALENDAR - January 2026
┌─────────────────────────────────────────────────────────────┐
│ Sun   Mon   Tue   Wed   Thu   Fri   Sat                     │
│                     1     2     3     4                      │
│  5     6     7     8     9    10    11                      │
│                                ─── [QMS Audit ongoing] ───  │
│ 12    13    14    15    16    17    18                      │
│ ─────────────────────────────────────────                   │
│ 19    20    21    22    23    24    25                      │
│                               [Prod Control Audit]          │
│ 26    27    28    29    30    31                            │
│                               [QMS Due]                     │
└─────────────────────────────────────────────────────────────┘
```

#### Finding Status
Summary of audit findings:

```
FINDING STATUS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ BY STATUS                                                    │
│ Open         ████████████████  12                           │
│ In Progress  ████████          8                            │
│ Pending Ver  ████              4                            │
│ Closed       ████████████████████████████████  32           │
│                                                              │
│ BY SEVERITY                                                  │
│ Major        ██████            6                            │
│ Minor        ████████████      12                           │
│ Observation  ████              4                            │
│ Opportunity  ██                2                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Overdue Actions
Items requiring attention:

```
OVERDUE CORRECTIVE ACTIONS
┌─────────────────────────────────────────────────────────────┐
│ CA #       │ Finding  │ Owner      │ Due Date │ Days Over  │
├────────────┼──────────┼────────────┼──────────┼────────────┤
│ CA-2026-015│ F-038    │ J. Smith   │ Jan 5    │ 6 days     │
│ CA-2026-018│ F-041    │ M. Garcia  │ Jan 10   │ 1 day      │
└────────────┴──────────┴────────────┴──────────┴────────────┘
```

---

## 4. Audit Planning

### Annual Audit Schedule

Access: **Audit → Planning → Schedule**

```
ANNUAL AUDIT SCHEDULE - 2026
┌─────────────────────────────────────────────────────────────┐
│ Audit                    │ Type     │ Freq  │ Q1│ Q2│ Q3│ Q4│
├──────────────────────────┼──────────┼───────┼───┼───┼───┼───┤
│ Quality Management System│ Internal │ Annual│ ★ │   │   │   │
│ Production Control       │ Internal │ Qtrly │ ★ │ ★ │ ★ │ ★ │
│ Inventory Accuracy       │ Internal │ Qtrly │ ★ │ ★ │ ★ │ ★ │
│ Safety Program           │ Internal │ Semi  │ ★ │   │ ★ │   │
│ Environmental            │ Internal │ Annual│   │ ★ │   │   │
│ ISO 9001 Surveillance    │ External │ Annual│   │   │ ★ │   │
│ Financial Controls       │ External │ Annual│   │   │   │ ★ │
│ Supplier Audits (6)      │ External │ Varies│ ★ │ ★ │ ★ │ ★ │
└──────────────────────────┴──────────┴───────┴───┴───┴───┴───┘

Legend: ★ = Scheduled  ✓ = Completed  ⏳ = In Progress
```

### Creating an Audit Plan

```
┌─────────────────────────────────────────────────────────────┐
│  NEW AUDIT PLAN                                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ AUDIT DETAILS                                                │
│ Audit Name:      [Production Control Audit Q1 2026    ]     │
│ Audit Type:      [Internal              ▼]                  │
│ Standard/Ref:    [Internal Procedure PC-001         ]       │
│                                                              │
│ SCHEDULE                                                     │
│ Start Date:      [Jan 25, 2026    📅]                       │
│ End Date:        [Jan 27, 2026    📅]                       │
│ Report Due:      [Feb 3, 2026     📅]                       │
│                                                              │
│ TEAM                                                         │
│ Lead Auditor:    [You                  ▼]                   │
│ Co-Auditor(s):   [Sarah Wilson         ▼] [+ Add]           │
│                                                              │
│ SCOPE                                                        │
│ Departments:     ☑ Production  ☑ Quality  ☐ Warehouse       │
│ Processes:       [Work order management, production         │
│                   reporting, scrap control                 ] │
│                                                              │
│ OBJECTIVES                                                   │
│ [1. Verify production procedures are followed              ]│
│ [2. Assess data accuracy in Sensei OS                      ]│
│ [3. Evaluate effectiveness of controls                     ]│
│                                                              │
│ CHECKLIST                                                    │
│ Template:        [Production Control v2.0   ▼]              │
│                                                              │
│ [Save Draft]  [Submit for Approval]                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Audit Notification

System notifies auditees:

```
AUDIT NOTIFICATION
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ To: Production, Quality Departments                          │
│ Subject: Internal Audit Notification - Jan 25-27, 2026      │
│                                                              │
│ You are hereby notified of an upcoming internal audit:      │
│                                                              │
│ Audit: Production Control Audit Q1 2026                     │
│ Dates: January 25-27, 2026                                  │
│ Auditors: [Auditor Name], Sarah Wilson                      │
│                                                              │
│ Scope:                                                       │
│ - Work order management                                     │
│ - Production reporting                                      │
│ - Scrap control                                             │
│                                                              │
│ Please ensure relevant records and personnel are            │
│ available during the audit period.                          │
│                                                              │
│ Opening Meeting: Jan 25, 8:00 AM, Conference Room A         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Conducting Audits

### Audit Execution

Access: **Audit → My Audits → [Select Audit]**

```
AUDIT: Quality Management System Q1 2026
┌─────────────────────────────────────────────────────────────┐
│ Status: In Progress                                          │
│ Progress: 65% ████████████████████░░░░░░░░░░                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ TABS: [Overview] [Checklist] [Findings] [Evidence] [Report] │
│                                                              │
│ CHECKLIST PROGRESS                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Section              │ Items │ Complete │ Findings      │ │
│ ├──────────────────────┼───────┼──────────┼───────────────┤ │
│ │ Document Control     │ 10    │ 10/10 ✓  │ 1 minor       │ │
│ │ Management Review    │ 8     │ 8/8   ✓  │ 0             │ │
│ │ Internal Audit       │ 6     │ 6/6   ✓  │ 0             │ │
│ │ Corrective Action    │ 8     │ 5/8      │ 1 observation │ │
│ │ Training             │ 7     │ 4/7      │ In progress   │ │
│ │ Customer Focus       │ 6     │ 0/6      │ Not started   │ │
│ └──────────────────────┴───────┴──────────┴───────────────┘ │
│                                                              │
│ SCHEDULE                                                     │
│ ├─ Jan 11, AM: Corrective Action process                   │
│ ├─ Jan 11, PM: Training records review                      │
│ └─ Jan 12, AM: Customer focus, closing meeting              │
│                                                              │
│ [Continue Checklist]  [Add Finding]  [View Evidence]        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Interview Documentation

Record audit interviews:

```
INTERVIEW RECORD
┌─────────────────────────────────────────────────────────────┐
│ Audit: QMS Q1 2026                                           │
│ Date/Time: Jan 11, 2026 10:30 AM                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ INTERVIEWEE                                                  │
│ Name:        [Maria Garcia            ]                     │
│ Title:       [Production Supervisor   ]                     │
│ Department:  [Production              ]                     │
│                                                              │
│ TOPICS COVERED                                               │
│ ☑ Awareness of quality policy                               │
│ ☑ Knowledge of relevant procedures                          │
│ ☑ Corrective action process                                 │
│ ☐ Training requirements                                     │
│                                                              │
│ NOTES                                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Interviewee demonstrated good knowledge of procedures.  │ │
│ │ Explained the NCR process clearly. Noted that CA       │ │
│ │ status tracking could be improved - currently uses     │ │
│ │ spreadsheet outside system.                             │ │
│ │                                                         │ │
│ │ Potential finding: CA tracking not fully in Sensei OS  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Save]  [Create Finding from Notes]                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Audit Checklists

### Checklist Execution

```
CHECKLIST: QMS Audit - Corrective Action Process
┌─────────────────────────────────────────────────────────────┐
│ Section: Corrective Action (ISO 9001:2015 Clause 10.2)      │
│ Progress: 5/8 items complete                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ┌──┬───────────────────────────────────────────┬──────────┐ │
│ │# │ Question/Requirement                       │ Status   │ │
│ ├──┼───────────────────────────────────────────┼──────────┤ │
│ │1 │ Is there a documented CA procedure?       │ ✓ Conform│ │
│ │2 │ Are NCRs reviewed for CA determination?   │ ✓ Conform│ │
│ │3 │ Is root cause analysis performed?         │ ✓ Conform│ │
│ │4 │ Are actions tracked to closure?           │ ⚠️ Minor │ │
│ │5 │ Is effectiveness verified?                │ ✓ Conform│ │
│ │6 │ Are trends analyzed?                      │ ◯ Pending│ │
│ │7 │ Is management informed of status?         │ ◯ Pending│ │
│ │8 │ Are records maintained properly?          │ ◯ Pending│ │
│ └──┴───────────────────────────────────────────┴──────────┘ │
│                                                              │
│ CURRENT ITEM: #6 - Are trends analyzed?                     │
│                                                              │
│ Evidence Required: Trend analysis records/reports           │
│                                                              │
│ Status:    [Select         ▼]                               │
│            ├─ Conforming                                    │
│            ├─ Minor Nonconformance                          │
│            ├─ Major Nonconformance                          │
│            ├─ Observation                                   │
│            └─ Opportunity for Improvement                   │
│                                                              │
│ Notes:     [                                           ]    │
│ Evidence:  [📎 Attach]                                      │
│                                                              │
│ [Previous]  [Save & Next]  [Skip]                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Sampling Records

Document sample selection:

```
SAMPLING RECORD
┌─────────────────────────────────────────────────────────────┐
│ Audit: QMS Q1 2026                                           │
│ Area: Corrective Actions                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ POPULATION                                                   │
│ Total CAs in period: 45                                     │
│ Period: Oct 1, 2025 - Dec 31, 2025                          │
│                                                              │
│ SAMPLE                                                       │
│ Method: Random + Targeted                                   │
│ Size: 10 (22%)                                              │
│                                                              │
│ RECORDS SELECTED                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ CA #       │ Type     │ Date     │ Status   │ Result   │ │
│ ├────────────┼──────────┼──────────┼──────────┼──────────┤ │
│ │ CA-2025-089│ Customer │ Oct 5    │ Closed   │ ✓ OK     │ │
│ │ CA-2025-095│ Internal │ Oct 18   │ Closed   │ ✓ OK     │ │
│ │ CA-2025-102│ Supplier │ Nov 2    │ Closed   │ ⚠️ Issue │ │
│ │ ...                                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ RATIONALE                                                    │
│ Random selection of 8 records, plus 2 targeted (customer    │
│ complaints) to ensure coverage of high-risk areas.          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Finding Management

### Creating a Finding

```
┌─────────────────────────────────────────────────────────────┐
│  NEW AUDIT FINDING                                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ FINDING DETAILS                                              │
│ Finding #:      [F-2026-052] (auto-generated)               │
│ Audit:          [QMS Q1 2026               ▼]               │
│ Checklist Item: [4 - CA tracking           ▼]               │
│                                                              │
│ CLASSIFICATION                                               │
│ Type:           [Minor Nonconformance      ▼]               │
│                 ├─ Major Nonconformance                     │
│                 ├─ Minor Nonconformance                     │
│                 ├─ Observation                              │
│                 └─ Opportunity for Improvement              │
│                                                              │
│ Standard Ref:   [ISO 9001:2015 Clause 10.2.1        ]       │
│ Procedure Ref:  [QP-008 Corrective Action           ]       │
│                                                              │
│ FINDING STATEMENT                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Corrective action status is tracked using an external  │ │
│ │ spreadsheet rather than within Sensei OS. This creates │ │
│ │ risk of incomplete tracking and does not meet the      │ │
│ │ documented procedure QP-008 Section 5.3 which requires │ │
│ │ all CA status to be maintained in the quality system.  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ OBJECTIVE EVIDENCE                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ - Interview with Production Supervisor M. Garcia        │ │
│ │ - Spreadsheet "CA_Tracker.xlsx" observed (screenshot   │ │
│ │   attached)                                             │ │
│ │ - 3 of 10 sampled CAs (CA-2025-102, 115, 122) not      │ │
│ │   updated in Sensei OS                                  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ EVIDENCE ATTACHMENTS                                         │
│ [📄 CA_tracker_screenshot.png] [📄 Interview_notes.pdf]     │
│ [+ Attach Evidence]                                          │
│                                                              │
│ ASSIGNMENT                                                   │
│ Responsible:    [Quality Manager          ▼]                │
│ Due Date:       [Feb 15, 2026       📅]                     │
│                                                              │
│ [Save Draft]  [Issue Finding]                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Finding Classification Guide

| Type | Definition | Example |
|------|------------|---------|
| Major NC | System failure, high risk | No procedure exists |
| Minor NC | Isolated failure | Procedure not followed 1x |
| Observation | Potential issue | Trend toward nonconformance |
| OFI | Improvement opportunity | Good, could be better |

### Finding List

```
AUDIT FINDINGS
┌─────────────────────────────────────────────────────────────┐
│ Filter: [All ▼]  Audit: [All ▼]  Status: [Open ▼]          │
├─────────────────────────────────────────────────────────────┤
│ Finding   │ Audit     │ Type  │ Area      │ Status│ Due    │
├───────────┼───────────┼───────┼───────────┼───────┼────────┤
│ F-2026-052│ QMS Q1    │ Minor │ Quality   │ Open  │ Feb 15 │
│ F-2026-051│ QMS Q1    │ Obs   │ Quality   │ Open  │ Feb 28 │
│ F-2026-048│ Prod Q4   │ Minor │ Production│ In CA │ Jan 20 │
│ F-2026-045│ Inv Q4    │ Major │ Warehouse │ Ver   │ Jan 15 │
│ F-2026-042│ Safety    │ Minor │ EHS       │Closed │ -      │
└───────────┴───────────┴───────┴───────────┴───────┴────────┘
```

---

## 8. Evidence Collection

### Evidence Types

Document evidence for findings:

| Evidence Type | Use For |
|---------------|---------|
| Documents | Procedures, records, forms |
| Photos | Visual observations |
| Screenshots | System data, screens |
| Interviews | Verbal statements |
| Data Exports | Reports, lists |

### Collecting System Evidence

Access data directly from Sensei OS:

```
EVIDENCE COLLECTION - System Data
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Finding: F-2026-052 (CA Tracking)                           │
│                                                              │
│ DATA EXPORT                                                  │
│ Module:        [Quality → Corrective Actions    ▼]          │
│ Date Range:    [Oct 1, 2025] to [Dec 31, 2025]              │
│ Filters:       [Status: All                     ▼]          │
│                                                              │
│ Preview:                                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ CA #       │ Status  │ Last Updated │ Updated By        │ │
│ ├────────────┼─────────┼──────────────┼───────────────────┤ │
│ │ CA-2025-089│ Closed  │ Nov 5, 2025  │ mgarcia           │ │
│ │ CA-2025-102│ Open    │ Nov 10, 2025 │ system            │ │
│ │ ...                                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Export as Evidence]  [Attach to Finding F-2026-052]        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Evidence Repository

```
EVIDENCE - Finding F-2026-052
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ ATTACHED EVIDENCE                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Type      │ File Name           │ Added    │ By        │ │
│ ├───────────┼─────────────────────┼──────────┼───────────┤ │
│ │ Screenshot│ CA_tracker.png      │ Jan 11   │ auditor   │ │
│ │ Interview │ interview_mgarcia.pdf│ Jan 11  │ auditor   │ │
│ │ Data      │ CA_list_export.xlsx │ Jan 11   │ auditor   │ │
│ │ Procedure │ QP-008_v3.pdf       │ Jan 11   │ auditor   │ │
│ └───────────┴─────────────────────┴──────────┴───────────┘ │
│                                                              │
│ [+ Add Evidence]  [Download All]                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Report Generation

### Audit Report

Access: **Audit → [Select Audit] → Report**

```
AUDIT REPORT GENERATOR
┌─────────────────────────────────────────────────────────────┐
│ Audit: Quality Management System Q1 2026                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ REPORT SECTIONS                                              │
│ ├─ ☑ Executive Summary                                      │
│ ├─ ☑ Audit Scope & Objectives                               │
│ ├─ ☑ Audit Criteria                                         │
│ ├─ ☑ Audit Team & Schedule                                  │
│ ├─ ☑ Finding Summary                                        │
│ ├─ ☑ Detailed Findings                                      │
│ ├─ ☑ Positive Observations                                  │
│ ├─ ☐ Checklist Results (Appendix)                           │
│ └─ ☐ Evidence List (Appendix)                               │
│                                                              │
│ EXECUTIVE SUMMARY (Edit)                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ This audit assessed the Quality Management System       │ │
│ │ against ISO 9001:2015 requirements. The audit found    │ │
│ │ the QMS to be generally effective with 1 minor         │ │
│ │ nonconformance and 1 observation identified.           │ │
│ │                                                         │ │
│ │ Overall Rating: Satisfactory with Opportunities        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ CONCLUSION                                                   │
│ Rating:         [Satisfactory                    ▼]         │
│                 ├─ Satisfactory                             │
│                 ├─ Satisfactory with Opportunities          │
│                 ├─ Needs Improvement                        │
│                 └─ Unsatisfactory                           │
│                                                              │
│ [Preview Report]  [Generate PDF]  [Submit for Review]       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Report Preview

```
┌─────────────────────────────────────────────────────────────┐
│                    INTERNAL AUDIT REPORT                     │
│                                                              │
│           Quality Management System Audit - Q1 2026          │
│                                                              │
│ ─────────────────────────────────────────────────────────── │
│                                                              │
│ 1. EXECUTIVE SUMMARY                                         │
│                                                              │
│ This audit assessed the Quality Management System against   │
│ ISO 9001:2015 requirements. The audit found the QMS to be  │
│ generally effective with 1 minor nonconformance and 1      │
│ observation identified.                                     │
│                                                              │
│ Overall Rating: SATISFACTORY WITH OPPORTUNITIES             │
│                                                              │
│ ─────────────────────────────────────────────────────────── │
│                                                              │
│ 2. AUDIT DETAILS                                             │
│                                                              │
│ Audit Dates: January 8-12, 2026                             │
│ Lead Auditor: [Your Name]                                   │
│ Co-Auditor: Sarah Wilson                                    │
│                                                              │
│ Scope: All QMS elements per ISO 9001:2015                   │
│ Departments: Quality, Production, Warehouse                 │
│                                                              │
│ ─────────────────────────────────────────────────────────── │
│                                                              │
│ 3. FINDINGS SUMMARY                                          │
│                                                              │
│ │ Type                 │ Count │                            │
│ │ Major Nonconformance │   0   │                            │
│ │ Minor Nonconformance │   1   │                            │
│ │ Observation          │   1   │                            │
│ │ Total                │   2   │                            │
│                                                              │
│ [Continue...]                                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Corrective Action Tracking

### CA Workflow

```
CORRECTIVE ACTION FLOW

Finding Issued
      │
      ▼
┌─────────────┐
│ CA Required │──────────────────────────────────────┐
└──────┬──────┘                                      │
       │                                             │
       ▼                                             │
┌─────────────┐                                      │
│ Root Cause  │ ← Auditee investigates              │
│ Analysis    │                                      │
└──────┬──────┘                                      │
       │                                             │
       ▼                                             │
┌─────────────┐                                      │
│ Action Plan │ ← Auditee proposes actions          │
│ Submitted   │                                      │
└──────┬──────┘                                      │
       │                                             │
       ▼                                             │
┌─────────────┐                                      │
│ Auditor     │ ← You review and approve            │
│ Review      │                                      │
└──────┬──────┘                                      │
       │                                             │
       ▼                                             │
┌─────────────┐                                      │
│ Actions     │ ← Auditee implements                │
│ Implemented │                                      │
└──────┬──────┘                                      │
       │                                             │
       ▼                                             │
┌─────────────┐                                      │
│ Verification│ ← You verify effectiveness          │
│ by Auditor  │                                      │
└──────┬──────┘                                      │
       │                                             │
       ▼                                             │
┌─────────────┐                                      │
│  CLOSED     │──────────────────────────────────────┘
└─────────────┘
```

### Reviewing Corrective Actions

```
CORRECTIVE ACTION: CA-2026-052
┌─────────────────────────────────────────────────────────────┐
│ Finding: F-2026-052 - CA Tracking not in system            │
│ Status: Pending Auditor Review                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ROOT CAUSE ANALYSIS (Submitted by Quality Manager)          │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Method: 5-Why Analysis                                  │ │
│ │                                                         │ │
│ │ Problem: CA status tracked in spreadsheet               │ │
│ │ Why 1: Spreadsheet easier to share with supervisors    │ │
│ │ Why 2: Sensei OS CA module not fully deployed          │ │
│ │ Why 3: Training not completed for all users            │ │
│ │ Why 4: Training delayed due to resource constraints    │ │
│ │ Why 5: Implementation plan did not include training    │ │
│ │                                                         │ │
│ │ Root Cause: Incomplete implementation planning         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ PROPOSED ACTIONS                                             │
│ ┌────┬──────────────────────────────────┬────────┬────────┐ │
│ │ #  │ Action                           │ Owner  │ Due    │ │
│ ├────┼──────────────────────────────────┼────────┼────────┤ │
│ │ 1  │ Complete CA module training      │ QA Mgr │ Feb 1  │ │
│ │ 2  │ Migrate data from spreadsheet    │ QA Eng │ Feb 8  │ │
│ │ 3  │ Retire spreadsheet               │ QA Mgr │ Feb 15 │ │
│ │ 4  │ Verify all users trained         │ QA Mgr │ Feb 15 │ │
│ └────┴──────────────────────────────────┴────────┴────────┘ │
│                                                              │
│ AUDITOR REVIEW                                               │
│ ☑ Root cause adequately addresses the finding              │
│ ☑ Actions are appropriate to prevent recurrence            │
│ ☐ Timelines are reasonable                                  │
│                                                              │
│ Comments:                                                    │
│ [Actions 1-3 are good. Action 4 due date should be       ] │
│ [after action 1 completion to allow time for training.   ] │
│                                                              │
│ [Request Revision]  [Approve CA Plan]                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Verification

```
CA VERIFICATION: CA-2026-052
┌─────────────────────────────────────────────────────────────┐
│ Status: Implementation Complete - Pending Verification      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ACTIONS COMPLETED                                            │
│ ┌────┬──────────────────────────────────┬────────┬────────┐ │
│ │ #  │ Action                           │ Status │ Date   │ │
│ ├────┼──────────────────────────────────┼────────┼────────┤ │
│ │ 1  │ Complete CA module training      │ ✓ Done │ Jan 30 │ │
│ │ 2  │ Migrate data from spreadsheet    │ ✓ Done │ Feb 6  │ │
│ │ 3  │ Retire spreadsheet               │ ✓ Done │ Feb 12 │ │
│ │ 4  │ Verify all users trained         │ ✓ Done │ Feb 14 │ │
│ └────┴──────────────────────────────────┴────────┴────────┘ │
│                                                              │
│ COMPLETION EVIDENCE (Submitted)                              │
│ ├─ Training records for 8 users                             │
│ ├─ Screenshot of migrated CA records in system              │
│ └─ Email confirmation spreadsheet retired                   │
│                                                              │
│ VERIFICATION                                                 │
│ Verification Method:                                         │
│ [System check to verify CAs are being entered directly     ]│
│ [and training records reviewed.                            ]│
│                                                              │
│ Verification Result:                                         │
│ ○ Effective - Close finding                                 │
│ ○ Partially effective - Additional action needed            │
│ ○ Not effective - Reopen                                    │
│                                                              │
│ Evidence:                                                    │
│ [📎 Attach verification evidence]                           │
│                                                              │
│ [Save]  [Close Finding]                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Compliance Monitoring

### Compliance Dashboard

Monitor ongoing compliance status:

```
COMPLIANCE DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ CERTIFICATIONS                                               │
│ ├─ ISO 9001:2015 - Valid until Sep 2027 ✓                   │
│ ├─ ISO 14001:2015 - Valid until Sep 2027 ✓                  │
│ └─ AS9100D - Valid until Mar 2026 ⚠️ (Renewal due)          │
│                                                              │
│ REGULATORY                                                   │
│ ├─ EPA Permits - Current ✓                                  │
│ ├─ OSHA Compliance - Last inspection: Aug 2025 ✓            │
│ └─ State Licenses - All current ✓                           │
│                                                              │
│ AUDIT STATUS                                                 │
│ ├─ Internal Audits: 8/10 planned for year (80%)            │
│ ├─ Findings: 12 open, 2 overdue                             │
│ └─ External Audits: ISO surveillance due Q3                 │
│                                                              │
│ TRAINING COMPLIANCE                                          │
│ ├─ Mandatory Training: 92% complete ⚠️                      │
│ └─ Certification Required: 95% current ✓                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Compliance Calendar

```
COMPLIANCE CALENDAR
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ UPCOMING COMPLIANCE ITEMS                                    │
│                                                              │
│ January 2026                                                 │
│ ├─ Jan 15: Q4 Management Review due                         │
│ ├─ Jan 20: Annual safety training deadline                  │
│ └─ Jan 31: QMS internal audit completion                    │
│                                                              │
│ February 2026                                                │
│ ├─ Feb 15: Environmental monitoring report                  │
│ └─ Feb 28: AS9100 renewal application due                   │
│                                                              │
│ March 2026                                                   │
│ ├─ Mar 15: AS9100D surveillance audit                       │
│ └─ Mar 31: Annual document review                           │
│                                                              │
│ [View Full Calendar]  [Set Reminders]                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Data Access & Analysis

### Cross-System Data Access

As an auditor, you have read access to all data:

```
DATA ACCESS MENU
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ OPERATIONAL DATA                                             │
│ ├─ Production → Work orders, output, scrap                  │
│ ├─ Quality → NCRs, CAPAs, inspections                       │
│ ├─ Inventory → Counts, adjustments, transactions            │
│ ├─ Maintenance → Work orders, PMs, downtime                 │
│ ├─ Purchasing → POs, receipts, suppliers                    │
│ └─ Sales → Orders, shipments, returns                       │
│                                                              │
│ HUMAN RESOURCES                                              │
│ ├─ Training → Records, certifications                       │
│ ├─ Time/Attendance → Hours, absences                        │
│ └─ Performance → Reviews, goals                             │
│                                                              │
│ SYSTEM                                                       │
│ ├─ Audit Logs → All system activity                         │
│ ├─ User Access → Permissions, login history                 │
│ └─ Configuration → Settings (view only)                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Audit Analytics

Generate analytical reports:

```
AUDIT ANALYTICS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ FINDING TRENDS (12 Months)                                   │
│ ┌────────────────────────────────────────────┐              │
│ │  8 │ ▓▓▓                                   │              │
│ │  6 │ ▓▓▓  ▓▓▓       ▓▓▓                   │              │
│ │  4 │ ▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓       ▓▓▓   │              │
│ │  2 │ ▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓  ▓▓▓   │              │
│ │  0 └────────────────────────────────────── │              │
│ │     Q1   Q2   Q3   Q4   Q1   Q2   Q3      │              │
│ │          2025             2026 (proj)      │              │
│ └────────────────────────────────────────────┘              │
│                                                              │
│ FINDINGS BY AREA                                             │
│ Quality    ████████████████  35%                            │
│ Production ████████████      28%                            │
│ Warehouse  ████████          18%                            │
│ HR         ████              10%                            │
│ Other      ████              9%                             │
│                                                              │
│ REPEAT FINDINGS                                              │
│ ├─ Training records: 4 findings (recurring)                 │
│ └─ Document control: 3 findings (recurring)                 │
│                                                              │
│ [Export Analysis]  [Schedule Report]                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Audit History & Trends

### Audit History

Access: **Audit → History**

```
AUDIT HISTORY
┌─────────────────────────────────────────────────────────────┐
│ Year: [2025 ▼]  Type: [All ▼]  Status: [All ▼]             │
├─────────────────────────────────────────────────────────────┤
│ Audit            │ Type   │ Date     │ Findings│ Rating    │
├──────────────────┼────────┼──────────┼─────────┼───────────┤
│ QMS Q4 2025      │Internal│ Oct 2025 │ 3       │ Satisfact │
│ Production Q3    │Internal│ Jul 2025 │ 2       │ Satisfact │
│ ISO Surveillance │External│ Jun 2025 │ 1       │ Pass      │
│ Inventory Q2     │Internal│ Apr 2025 │ 4       │ NeedsImpv │
│ Safety Annual    │Internal│ Mar 2025 │ 2       │ Satisfact │
│ QMS Q1 2025      │Internal│ Jan 2025 │ 3       │ Satisfact │
└──────────────────┴────────┴──────────┴─────────┴───────────┘

[View Audit]  [Compare]  [Export]
```

### Trend Reports

```
AUDIT TREND REPORT - 3 Year Summary
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ FINDINGS BY YEAR                                             │
│           2023        2024        2025        Change        │
│ Major       3           2           0          ▼ 100%       │
│ Minor      12          10           8          ▼ 33%        │
│ Obs        18          15          12          ▼ 33%        │
│ Total      33          27          20          ▼ 39%        │
│                                                              │
│ CA CLOSURE PERFORMANCE                                       │
│           2023        2024        2025                      │
│ On-time    72%         80%         88%         ▲            │
│ Avg Days   45          38          28          ▼            │
│                                                              │
│ REPEAT FINDING RATE                                          │
│           2023        2024        2025                      │
│ Repeat %   25%         20%         15%         ▼            │
│                                                              │
│ CONCLUSION                                                   │
│ Positive trend: Findings decreasing, closure improving,     │
│ repeat findings declining. Continue current approach.       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. External Audit Support

### Preparing for External Audits

```
EXTERNAL AUDIT PREPARATION
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Upcoming: ISO 9001 Surveillance Audit - Q3 2026             │
│ Registrar: ABC Certification Body                           │
│ Expected Dates: September 15-16, 2026                       │
│                                                              │
│ PREPARATION CHECKLIST                                        │
│ ☐ Confirm audit dates with registrar                        │
│ ☐ Review previous audit findings - all closed               │
│ ☐ Complete internal audit cycle                             │
│ ☐ Verify management review conducted                        │
│ ☐ Update documentation as needed                            │
│ ☐ Prepare audit room and logistics                          │
│ ☐ Brief key personnel                                       │
│ ☐ Gather objective evidence                                 │
│                                                              │
│ PREVIOUS AUDIT FINDINGS                                      │
│ ├─ F-2025-001: Calibration records (Closed Jun 2025) ✓     │
│ └─ All findings from previous audit closed                  │
│                                                              │
│ INTERNAL AUDIT STATUS                                        │
│ Required for 2026: 10 | Completed: 8 | Remaining: 2        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### External Audit Tracking

```
EXTERNAL AUDIT: ISO 9001 Surveillance Sep 2026
┌─────────────────────────────────────────────────────────────┐
│ Status: Completed                                            │
│ Result: Continued Certification ✓                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ AUDIT SUMMARY                                                │
│ ├─ Auditor: Jane Doe (ABC Certification)                    │
│ ├─ Dates: September 15-16, 2026                             │
│ ├─ Duration: 2 days (16 hours)                              │
│ └─ Areas Covered: All ISO 9001 clauses                      │
│                                                              │
│ FINDINGS                                                     │
│ ├─ Major: 0                                                 │
│ ├─ Minor: 1 (Training records)                              │
│ └─ Opportunities: 2                                         │
│                                                              │
│ ACTIONS                                                      │
│ Minor finding CA submitted: Oct 1, 2026                     │
│ Status: Accepted by registrar                               │
│                                                              │
│ DOCUMENTS                                                    │
│ ├─ [📄 Audit Report]                                        │
│ ├─ [📄 Finding Details]                                     │
│ └─ [📄 CA Response]                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 15. Quick Reference

### Auditor Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + A` | Audit list |
| `Ctrl + F` | Findings |
| `Ctrl + C` | Checklists |
| `Ctrl + /` | Search |
| `F5` | Refresh |

### Finding Severity Guide

| Type | Criteria | CA Required | Timeline |
|------|----------|-------------|----------|
| Major NC | System failure | Yes | 30 days |
| Minor NC | Isolated issue | Yes | 60 days |
| Observation | Potential issue | Optional | 90 days |
| OFI | Improvement idea | No | As appropriate |

### Audit Status Codes

| Status | Meaning |
|--------|---------|
| Planned | Scheduled, not started |
| In Progress | Actively conducting |
| Draft Report | Fieldwork complete |
| Issued | Report distributed |
| Closed | All findings resolved |

### Auditor Checklist

```
AUDIT EXECUTION CHECKLIST

PLANNING
□ Review previous audits
□ Prepare checklist
□ Notify auditees
□ Schedule interviews
□ Gather relevant documents

EXECUTION
□ Opening meeting
□ Execute checklist
□ Conduct interviews
□ Collect evidence
□ Document findings
□ Closing meeting

REPORTING
□ Write draft report
□ Review with auditee
□ Issue final report
□ Track CAs to closure
□ Verify effectiveness
```

### Report Templates

| Report | Use |
|--------|-----|
| Internal Audit Report | Standard audit report |
| Finding Report | Individual finding detail |
| CA Status Report | Track corrective actions |
| Trend Analysis | Historical trends |
| Management Summary | Executive overview |

### Contacts

| Need | Contact |
|------|---------|
| Quality Manager | ext. 5300 |
| Management Rep | ext. 1005 |
| Registrar | [Contact info] |
| Training | ext. 3500 |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Quality Assurance*
