# Quality Manager / Inspector Starter Guide

## Sensei OS - Quality Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Quality Dashboard](#3-quality-dashboard)
4. [Inspection Management](#4-inspection-management)
5. [Nonconformance (NC) Management](#5-nonconformance-nc-management)
6. [Corrective Action (CAPA)](#6-corrective-action-capa)
7. [Document Control](#7-document-control)
8. [Statistical Process Control (SPC)](#8-statistical-process-control-spc)
9. [Supplier Quality](#9-supplier-quality)
10. [Calibration Management](#10-calibration-management)
11. [Audit Management](#11-audit-management)
12. [Quality Certifications](#12-quality-certifications)
13. [Customer Quality](#13-customer-quality)
14. [Reporting & Analytics](#14-reporting--analytics)
15. [Continuous Improvement](#15-continuous-improvement)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Track defects/NCR follow-ups as issues (severity/priority/status) and document investigation steps in comments.
- Use milestones for release/phase gate readiness and to monitor open vs closed work.
- Publish standards and checklists as wiki pages for consistent execution.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role in Quality

As Quality Manager/Inspector, you are the **guardian of product excellence**. Sensei OS empowers you to:

- **Ensure conformance** to specifications and standards
- **Manage inspections** efficiently and thoroughly
- **Track nonconformances** through resolution
- **Drive corrective action** to prevent recurrence
- **Maintain compliance** with quality standards (ISO, AS9100, etc.)
- **Enable continuous improvement** through data

### Quality Capabilities by Role

| Capability | Inspector | Quality Manager |
|------------|-----------|-----------------|
| Perform Inspections | ✓ | ✓ |
| Log NCs | ✓ | ✓ |
| Disposition NCs | Limited | Full |
| Manage CAPAs | Participate | Full |
| Document Control | View | Full |
| SPC Review | View | Full |
| Supplier Quality | View | Full |
| Audits | Participate | Full |
| Reports | View | Full |
| System Config | - | Full |

### Quality Workflow Overview

```
INCOMING → IN-PROCESS → FINAL → SHIP
    ↓           ↓         ↓
 Inspect    Inspect   Inspect
    ↓           ↓         ↓
    └───────────┴─────────┘
              ↓
    NC Found? → Containment → CAPA → Close
```

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter credentials
3. Complete MFA setup
4. Update your profile

### Initial Setup Tasks

- [ ] Verify your quality role permissions
- [ ] Review NC categories and codes
- [ ] Check calibration equipment assigned to you
- [ ] Review open NCs and CAPAs
- [ ] Set notification preferences

### Your Quality Home Screen

```
┌─────────────────────────────────────────────────────────────┐
│               QUALITY DASHBOARD                              │
│               January 11, 2026                              │
├─────────────────────────────────────────────────────────────┤
│  KEY METRICS                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ FPY MTD  │ │ Open NCs │ │ CAPAs    │ │ PPM      │       │
│  │  98.2%   │ │    12    │ │    5     │ │   850    │       │
│  │ ▲ 0.3%   │ │ ▼ from 15│ │ 2 due    │ │ ▼ 50     │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
├─────────────────────────────────────────────────────────────┤
│  ACTION REQUIRED                                             │
│  🔴 NC-2024-0892 - Disposition needed (3 days old)          │
│  🟡 CAPA-2024-0056 - Verification due tomorrow              │
│  🟡 Receiving inspection queue: 5 lots                      │
│  🔵 Calibration due: 3 gauges this week                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Quality Dashboard

### Dashboard Widgets

#### First Pass Yield (FPY)
Tracks parts passing inspection on first attempt:
- **Target**: Usually 98%+
- **Trend**: ▲ improving / ▼ declining

#### Open Nonconformances
Active NCs requiring attention:
- Click to see NC queue
- Sorted by age and severity

#### CAPA Status
Open corrective actions:
- Shows overdue items
- Click for CAPA workbench

#### PPM (Parts Per Million)
Defect rate metric:
- Lower is better
- Trend vs. last period

### Customizing Your Dashboard

1. Click **⚙️ Settings**
2. Add/remove widgets
3. Set refresh rate
4. Save as default

### Key Quality Metrics

| Metric | Description | Typical Target |
|--------|-------------|----------------|
| FPY | First Pass Yield | ≥98% |
| PPM | Defects per million | <1000 |
| NC Close Time | Days to close NC | <5 days |
| CAPA Effectiveness | CAPAs preventing recurrence | >90% |
| Supplier PPM | Supplier defect rate | <500 |
| On-Time Delivery | Quality not causing delay | 99% |

---

## 4. Inspection Management

### Inspection Types

| Type | When | Purpose |
|------|------|---------|
| Receiving | Material arrives | Verify incoming quality |
| First Piece | Before production run | Validate setup |
| In-Process | During production | Monitor quality |
| Final | Job complete | Release for shipment |
| Source | At supplier | Pre-ship verification |

### Receiving Inspection

Access: **Quality → Receiving Inspection**

```
RECEIVING INSPECTION QUEUE
┌─────────────────────────────────────────────────────────────┐
│ Lot      │ Part      │ Supplier    │ Qty   │ Arrived │     │
├──────────┼───────────┼─────────────┼───────┼─────────┼─────┤
│ RCV-1234 │ ABC-123   │ Acme Mfg    │ 500   │ Today   │ [→] │
│ RCV-1235 │ DEF-456   │ Best Parts  │ 200   │ Today   │ [→] │
│ RCV-1236 │ GHI-789   │ Acme Mfg    │ 100   │ Yester. │ [→] │
└─────────────────────────────────────────────────────────────┘
```

#### Performing Receiving Inspection

1. Select lot from queue
2. View inspection plan (sample size, checks required)
3. Perform measurements/visual checks
4. Enter results:

```
┌─────────────────────────────────────────────────────────────┐
│  RECEIVING INSPECTION - RCV-1234                             │
│  Part: ABC-123 | Supplier: Acme Mfg | Qty: 500              │
├─────────────────────────────────────────────────────────────┤
│  Sample Size: 13 (per AQL Table)                             │
│                                                              │
│  DIMENSIONAL CHECKS                                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Dim      │ Spec         │ S1    │ S2    │ S3    │...│    │
│  ├──────────┼──────────────┼───────┼───────┼───────┼───┤    │
│  │ Dia A    │ 1.000 ±.005  │ 1.002 │ 1.001 │ 0.999 │...│    │
│  │ Length B │ 2.500 ±.010  │ 2.503 │ 2.498 │ 2.501 │...│    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  VISUAL CHECKS                                               │
│  ☑ No visible damage                                         │
│  ☑ Correct packaging                                         │
│  ☑ Cert of Conformance present                              │
│                                                              │
│  RESULT: ○ Accept  ○ Reject  ○ Accept on Deviation          │
│                                                              │
│            [Save Draft]         [Submit Inspection]          │
└─────────────────────────────────────────────────────────────┘
```

### First Piece Inspection

First piece inspections are initiated by operators. You may be called to:

1. Review critical dimensions
2. Approve production start
3. Sign off on setup verification

Access: **Quality → First Piece Queue** or via notification

### In-Process Inspection

Monitor production quality:

1. Patrol inspection areas
2. Review operator-logged data
3. Check SPC charts
4. Perform random spot checks
5. Respond to quality Andons

### Final Inspection

Before shipment:

```
FINAL INSPECTION - JOB-1234
┌─────────────────────────────────────────────────────────────┐
│ Part: ABC-123 | Customer: Acme Corp | Qty: 500              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ INSPECTION CHECKLIST                                         │
│ ☑ All operations complete                                    │
│ ☑ In-process inspections passed                             │
│ ☑ Dimensional sampling (13 pcs) - All PASS                  │
│ ☑ Visual inspection - PASS                                   │
│ ☑ Functional test (if applicable) - N/A                     │
│ ☑ Packaging verification - PASS                             │
│ ☑ Labeling correct                                           │
│ ☑ Documentation complete                                     │
│                                                              │
│ RESULT: ● Accept  ○ Reject  ○ Hold                          │
│                                                              │
│ Notes: [                                              ]      │
│                                                              │
│         [Save]           [Submit & Release for Ship]         │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Nonconformance (NC) Management

### NC Workflow

```
DETECTED → LOGGED → CONTAINED → DISPOSITIONED → CLOSED
                                     ↓
                               CAPA (if needed)
```

### Logging a Nonconformance

Access: **Quality → Log NC**

```
┌─────────────────────────────────────────────────────────────┐
│              LOG NONCONFORMANCE                              │
├─────────────────────────────────────────────────────────────┤
│ NC Type:        [Internal            ▼]                     │
│                 • Internal  • Supplier  • Customer Return   │
│                                                              │
│ Source:         [In-Process Inspection▼]                    │
│ Job/Lot:        [JOB-1234            ▼]                     │
│ Part Number:    ABC-123 (auto-filled)                       │
│ Quantity Affected: [25  ]                                   │
│                                                              │
│ Defect Category: [Dimensional         ▼]                    │
│ Defect Code:     [DIM-003 Over Max    ▼]                    │
│                                                              │
│ Description:                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Diameter A measured 1.010" on 25 pcs.                   │ │
│ │ Spec: 1.000 ±.005. Parts are 0.005" over max.          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Severity:       ○ Minor  ● Major  ○ Critical                │
│                                                              │
│ Photos:         [📷 Add Photos] (3 attached)                 │
│                                                              │
│ CONTAINMENT ACTIONS                                          │
│ ☑ Parts segregated in hold area                             │
│ ☑ Production stopped on this operation                      │
│ ☐ Other lots being inspected                                │
│ ☐ Customer notification required                            │
│                                                              │
│              [Cancel]           [Submit NC]                  │
└─────────────────────────────────────────────────────────────┘
```

### NC Severity Levels

| Level | Definition | Response |
|-------|------------|----------|
| Minor | Cosmetic, no functional impact | Disposition within 5 days |
| Major | Functional impact, reworkable | Disposition within 3 days |
| Critical | Safety, regulatory, major cost | Immediate disposition |

### NC Disposition Options

| Disposition | Meaning |
|-------------|---------|
| **Use As-Is** | Accept with customer approval or deviation |
| **Rework** | Correct to meet specification |
| **Repair** | Fix but may not meet original spec |
| **Scrap** | Cannot be made conforming |
| **Return to Vendor** | Send back to supplier |
| **Sort** | 100% inspect to separate good from bad |

### Dispositioning an NC

1. Open the NC
2. Review all information
3. Select disposition:

```
┌─────────────────────────────────────────────────────────────┐
│  DISPOSITION NC-2024-0892                                    │
├─────────────────────────────────────────────────────────────┤
│  Affected Qty: 25 pcs                                        │
│                                                              │
│  Disposition: [Rework              ▼]                        │
│                                                              │
│  Rework Instructions:                                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Machine diameter to 1.000" +.000/-.005" (under min OK)  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Assigned To:    [John Smith         ▼]                     │
│  Due Date:       [Jan 13, 2026       ]                      │
│                                                              │
│  CAPA Required?  ● Yes  ○ No                                │
│  (Major severity, pattern detected)                          │
│                                                              │
│  Approvals Required:                                         │
│  ☑ Quality Manager                                           │
│  ☐ Engineering (if deviation)                                │
│  ☐ Customer (if customer-destined)                           │
│                                                              │
│              [Cancel]           [Submit Disposition]         │
└─────────────────────────────────────────────────────────────┘
```

### NC Analytics

View NC trends:

```
NC TREND - Last 12 Months
┌─────────────────────────────────────────────────────────────┐
│     │                           ▲                            │
│ 30  │                           █                            │
│     │              ▲            █ ▲                          │
│ 20  │    ▲        █ ▲          █ █                          │
│     │    █   ▲    █ █     ▲    █ █                          │
│ 10  │ ▲  █   █    █ █  ▲  █    █ █   ▲                      │
│     │ █  █   █    █ █  █  █    █ █   █                      │
│  0  └───────────────────────────────────────────────────────│
│      J  F  M  A  M  J  J  A  S  O  N  D                      │
│                                                              │
│ Top Defect Types:                                            │
│ 1. Dimensional (35%)                                         │
│ 2. Surface finish (22%)                                      │
│ 3. Missing features (18%)                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Corrective Action (CAPA)

### CAPA Workflow

```
INITIATE → INVESTIGATE → ROOT CAUSE → ACTION PLAN → IMPLEMENT → VERIFY → CLOSE
```

### When is CAPA Required?

- Major or critical NCs
- Repeat NCs (same issue recurring)
- Customer complaints
- Audit findings
- Safety incidents
- Regulatory requirements

### Creating a CAPA

Access: **Quality → CAPA → New**

```
┌─────────────────────────────────────────────────────────────┐
│              NEW CAPA                                        │
├─────────────────────────────────────────────────────────────┤
│ Source:         [Nonconformance      ▼]                     │
│ Reference:      [NC-2024-0892        ▼]                     │
│ Type:           ● Corrective  ○ Preventive                  │
│                                                              │
│ Problem Statement:                                           │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Dimensional nonconformance on Part ABC-123. Diameter A  │ │
│ │ out of tolerance on 25 pcs (5% of lot). Third          │ │
│ │ occurrence of this issue in last 6 months.             │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Impact:         [High              ▼]                       │
│ Assigned To:    [Mike Williams      ▼]                      │
│ Due Date:       [Jan 25, 2026       ]                       │
│                                                              │
│ Team Members:                                                │
│ [+ Add Team Member]                                          │
│ • John Smith (Operator)                                      │
│ • Maria Garcia (Engineering)                                 │
│                                                              │
│              [Cancel]           [Create CAPA]                │
└─────────────────────────────────────────────────────────────┘
```

### Root Cause Analysis

Document your investigation:

```
┌─────────────────────────────────────────────────────────────┐
│  CAPA-2024-0057 - ROOT CAUSE ANALYSIS                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  5 WHY ANALYSIS                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 1. Why? Parts out of tolerance                          │ │
│  │    → Tool wore past acceptable limit                    │ │
│  │                                                          │ │
│  │ 2. Why? Tool not changed in time                        │ │
│  │    → Operator didn't know tool life count               │ │
│  │                                                          │ │
│  │ 3. Why? Counter not visible                             │ │
│  │    → Display on secondary screen                        │ │
│  │                                                          │ │
│  │ 4. Why? Poor screen layout                              │ │
│  │    → Never updated after machine upgrade                │ │
│  │                                                          │ │
│  │ 5. Why? No standard for critical displays               │ │
│  │    → ROOT CAUSE: Lack of HMI standard for critical     │ │
│  │      process indicators                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Root Cause Category: [Process/Procedure   ▼]               │
│                                                              │
│  Supporting Evidence: [📎 3 files attached]                  │
│                                                              │
│                    [Save Root Cause]                         │
└─────────────────────────────────────────────────────────────┘
```

### Action Plan

Define corrective actions:

```
CAPA-2024-0057 - ACTION PLAN
┌─────────────────────────────────────────────────────────────┐
│ # │ Action                       │ Owner    │ Due    │ Stat │
├───┼──────────────────────────────┼──────────┼────────┼──────┤
│ 1 │ Move tool counter to main    │ M.Garcia │ Jan 15 │ Open │
│   │ HMI screen                   │          │        │      │
├───┼──────────────────────────────┼──────────┼────────┼──────┤
│ 2 │ Create HMI standard for      │ M.Garcia │ Jan 20 │ Open │
│   │ critical process indicators  │          │        │      │
├───┼──────────────────────────────┼──────────┼────────┼──────┤
│ 3 │ Apply standard to all CNC    │ D.Chen   │ Feb 01 │ Open │
│   │ machines                     │          │        │      │
├───┼──────────────────────────────┼──────────┼────────┼──────┤
│ 4 │ Train operators on new       │ J.Smith  │ Feb 05 │ Open │
│   │ display layout               │          │        │      │
└───┴──────────────────────────────┴──────────┴────────┴──────┘
│                                                              │
│ [+ Add Action]                                               │
└─────────────────────────────────────────────────────────────┘
```

### Verification

After actions implemented:

1. Wait appropriate time (30-90 days typically)
2. Check if problem has recurred
3. Review metrics
4. Document effectiveness:

```
CAPA-2024-0057 - VERIFICATION
┌─────────────────────────────────────────────────────────────┐
│ Verification Date: March 1, 2026                             │
│ Verified By: Quality Manager                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Effectiveness Evidence:                                      │
│ ☑ No recurrence of NC in 45 days                            │
│ ☑ Operator feedback positive                                │
│ ☑ SPC shows process in control                              │
│                                                              │
│ Metrics:                                                     │
│ • Tool-related NCs: 5 → 0 (last 45 days)                    │
│ • FPY on ABC-123: 95% → 99.5%                               │
│                                                              │
│ Recommendation: ● Close CAPA  ○ Extend Monitoring           │
│                                                              │
│                    [Submit Verification]                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Document Control

### Managing Quality Documents

Access: **Quality → Document Control**

Quality documents include:
- Work instructions
- Inspection procedures
- Quality manual
- Process specifications
- Forms and checklists

### Document States

```
DRAFT → REVIEW → APPROVED → RELEASED → OBSOLETE
          ↓
       REJECTED (back to draft)
```

### Creating/Revising Documents

1. Click **New Document** or **Revise** existing
2. Upload or edit content
3. Set document properties:
   - Document number
   - Title
   - Revision level
   - Effective date
   - Review cycle
4. Route for approval
5. Once approved, release

### Document Approval Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  DOCUMENT APPROVAL - WI-1234 Rev C                           │
│  Work Instruction: CNC Milling Process ABC-123              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Approval Chain:                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Role          │ Name         │ Status    │ Date        │ │
│  ├───────────────┼──────────────┼───────────┼─────────────┤ │
│  │ Author        │ M. Garcia    │ ✓ Complete│ Jan 10      │ │
│  │ Engineering   │ D. Chen      │ ✓ Approved│ Jan 11      │ │
│  │ Quality       │ You          │ ⏳ Pending │ -           │ │
│  │ Production    │ J. Williams  │ ○ Waiting │ -           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  Your Action:                                                │
│  [View Document] [View Redline] [View Comments]             │
│                                                              │
│  [✓ Approve]  [↩ Request Changes]  [✗ Reject]               │
└─────────────────────────────────────────────────────────────┘
```

### Document Access Control

Control who can view and edit:

| Level | View | Edit | Approve |
|-------|------|------|---------|
| Operator | ✓ | - | - |
| Supervisor | ✓ | Request | - |
| Quality | ✓ | ✓ | ✓ |
| Engineering | ✓ | ✓ | ✓ |
| Manager | ✓ | - | ✓ |

---

## 8. Statistical Process Control (SPC)

### SPC Dashboard

Access: **Quality → SPC**

```
SPC DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│  PROCESS CAPABILITY SUMMARY                                  │
├─────────────────────────────────────────────────────────────┤
│ Process           │ Cpk   │ Status │ Trend │ Last Update    │
├───────────────────┼───────┼────────┼───────┼────────────────┤
│ CNC Mill 1 - Dia A│ 1.45  │ ✓ Cpbl │ Stable│ 10 min ago     │
│ CNC Mill 2 - Dia A│ 1.12  │ ⚠️ Marg │ ↓     │ 25 min ago     │
│ Lathe 1 - Length  │ 1.67  │ ✓ Cpbl │ Stable│ 5 min ago      │
│ Assembly - Torque │ 0.89  │ 🔴 NCap │ ↓     │ 1 hr ago       │
└───────────────────┴───────┴────────┴───────┴────────────────┘
```

### Reading Control Charts

```
X-Bar Chart - CNC Mill 1 - Diameter A
┌─────────────────────────────────────────────────────────────┐
│ UCL  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  1.006     │
│                                                              │
│           ●       ●                                          │
│ CL   ──●────●──●────●──●──●──●──●──●──●──●──●──  1.000     │
│         ●                    ●     ●                         │
│                                                              │
│ LCL  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  0.994     │
│      1  2  3  4  5  6  7  8  9  10 11 12 13 14 15           │
│                     Subgroup                                 │
└─────────────────────────────────────────────────────────────┘
```

### SPC Rule Violations

Watch for these patterns:

| Rule | Pattern | Action |
|------|---------|--------|
| 1 point beyond control limit | Out of spec | Stop, investigate |
| 7 points in a row same side | Shift/drift | Investigate cause |
| 7 points trending up/down | Trend | Adjust process |
| 2 of 3 points in outer 1/3 | Warning | Monitor closely |

### Taking Action on SPC Alerts

When SPC violation occurs:

1. System alerts you
2. Review the chart
3. Go to the process
4. Identify cause
5. Take corrective action
6. Document in Sensei

---

## 9. Supplier Quality

### Supplier Quality Dashboard

Access: **Quality → Supplier Quality**

```
SUPPLIER QUALITY SUMMARY
┌─────────────────────────────────────────────────────────────┐
│ Supplier       │ Rating │ PPM   │ OTD   │ NCARs │ Status   │
├────────────────┼────────┼───────┼───────┼───────┼──────────┤
│ Acme Mfg       │ A      │ 250   │ 98%   │ 0     │ ✓ Active │
│ Best Parts     │ B      │ 1200  │ 95%   │ 2     │ ⚠️ Watch  │
│ Quality Corp   │ A      │ 0     │ 99%   │ 0     │ ✓ Active │
│ New Supplier   │ -      │ -     │ -     │ -     │ 🔵 Qual.  │
└────────────────┴────────┴───────┴───────┴───────┴──────────┘
```

### Supplier NCARs

Nonconformance Action Requests to suppliers:

1. Create NCAR from receiving NC
2. Send to supplier
3. Track their response
4. Verify corrective action
5. Adjust supplier rating

### Supplier Audits

Schedule and conduct supplier audits:

1. Go to **Supplier Quality → Audits**
2. Schedule audit
3. Use audit checklist
4. Record findings
5. Issue corrective actions if needed
6. Track closure

### Approved Supplier List (ASL)

Maintain your ASL:

- Add new suppliers after qualification
- Update ratings based on performance
- Set supplier status (Approved, Conditional, Probation, Removed)
- Track certifications (ISO, AS9100, etc.)

---

## 10. Calibration Management

### Calibration Dashboard

Access: **Quality → Calibration**

```
CALIBRATION STATUS
┌─────────────────────────────────────────────────────────────┐
│ Coming Due (Next 30 Days): 12                                │
│ Overdue: 0                                                   │
│ Out for Cal: 3                                               │
│ Total Managed: 156                                           │
├─────────────────────────────────────────────────────────────┤
│ UPCOMING CALIBRATIONS                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ID      │ Description      │ Due Date │ Location       │ │
│ ├─────────┼──────────────────┼──────────┼────────────────┤ │
│ │ MIC-001 │ Micrometer 0-1"  │ Jan 15   │ QC Lab         │ │
│ │ CAL-034 │ Caliper 6"       │ Jan 18   │ CNC Area       │ │
│ │ GAU-012 │ Pin Gauge Set    │ Jan 20   │ Tool Crib      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Managing Equipment

Each calibrated item has a record:

```
EQUIPMENT RECORD - MIC-001
┌─────────────────────────────────────────────────────────────┐
│ ID: MIC-001          │ Status: In Service                   │
│ Description: Micrometer 0-1"                                │
│ Manufacturer: Mitutoyo │ Model: 293-340                     │
│ Serial: 12345678     │ Location: QC Lab                     │
├─────────────────────────────────────────────────────────────┤
│ Calibration Interval: 6 months                              │
│ Last Calibration: July 15, 2025                             │
│ Next Due: January 15, 2026                                  │
│ Calibrated By: XYZ Calibration Labs                         │
├─────────────────────────────────────────────────────────────┤
│ CALIBRATION HISTORY                                          │
│ Date       │ Result  │ Certificate │ By                     │
│ Jul 2025   │ ✓ Pass  │ CAL-7890    │ XYZ Labs              │
│ Jan 2025   │ ✓ Pass  │ CAL-6543    │ XYZ Labs              │
│ Jul 2024   │ ⚠️ Adj   │ CAL-4321    │ XYZ Labs              │
└─────────────────────────────────────────────────────────────┘
```

### Recording Calibration Results

When calibration is completed:

1. Open equipment record
2. Click **Record Calibration**
3. Enter results:
   - Date
   - Pass/Fail/Adjusted
   - Certificate number
   - Calibration provider
   - As-found/As-left data (if applicable)
4. Upload certificate
5. Save

### Handling Failed Calibration

If equipment fails calibration:

1. Change status to **Out of Tolerance**
2. System triggers impact assessment:
   - What was measured with this gauge since last cal?
   - Are there products at risk?
3. Create NC if products affected
4. Repair or replace equipment
5. Recalibrate before returning to service

---

## 11. Audit Management

### Audit Types

| Type | Frequency | Conducted By |
|------|-----------|--------------|
| Internal | Monthly/Quarterly | Quality |
| Customer | As scheduled | Customer |
| Registrar | Annual | Certification body |
| Supplier | As needed | Quality |
| Process | Ongoing | Quality |

### Internal Audit Schedule

Access: **Quality → Audits → Schedule**

```
AUDIT SCHEDULE - 2026
┌─────────────────────────────────────────────────────────────┐
│ Month │ Process Area            │ Auditor    │ Status       │
├───────┼─────────────────────────┼────────────┼──────────────┤
│ Jan   │ Receiving Inspection    │ J. Smith   │ ✓ Complete   │
│ Feb   │ Production Control      │ M. Garcia  │ 🔵 Scheduled │
│ Mar   │ Document Control        │ D. Chen    │ 🔵 Scheduled │
│ Apr   │ CAPA Process            │ J. Smith   │ 🔵 Scheduled │
│ ...   │ ...                     │ ...        │ ...          │
└───────┴─────────────────────────┴────────────┴──────────────┘
```

### Conducting an Audit

1. Open scheduled audit
2. Use audit checklist
3. Record findings:

```
AUDIT FINDING
┌─────────────────────────────────────────────────────────────┐
│ Audit: 2026-02 Production Control                            │
│ Clause: 8.5.1 Control of Production                          │
├─────────────────────────────────────────────────────────────┤
│ Finding Type:   ○ Major NC  ● Minor NC  ○ Observation       │
│                                                              │
│ Requirement:                                                 │
│ [Work instructions shall be available at point of use    ]  │
│                                                              │
│ Evidence/Observation:                                        │
│ [Cell 3 had outdated Rev B of WI-1234; current is Rev D. ]  │
│ [Operator not aware of new revision.                     ]  │
│                                                              │
│ Objective Evidence: [📎 Photo attached]                      │
│                                                              │
│                    [Add Finding]                             │
└─────────────────────────────────────────────────────────────┘
```

### Tracking Audit Findings

All findings create CAPAs:

- Minor NC → CAPA with 30-day target
- Major NC → CAPA with 14-day target
- Observation → Logged for improvement

---

## 12. Quality Certifications

### Tracking Company Certifications

Access: **Quality → Certifications**

```
COMPANY CERTIFICATIONS
┌─────────────────────────────────────────────────────────────┐
│ Certification │ Scope            │ Registrar │ Expires      │
├───────────────┼──────────────────┼───────────┼──────────────┤
│ ISO 9001:2015 │ Mfg & Assembly   │ NSF-ISR   │ Mar 2027     │
│ AS9100D       │ Aerospace Parts  │ SAI Global│ Jun 2026     │
│ IATF 16949    │ Auto Components  │ DNV-GL    │ Sep 2027     │
│ NADCAP        │ Heat Treat, NDT  │ PRI       │ Dec 2026     │
└───────────────┴──────────────────┴───────────┴──────────────┘
```

### Certification Maintenance

Keep certifications current:

1. Schedule surveillance audits
2. Address findings promptly
3. Track recertification dates
4. Maintain required records
5. Report changes to registrar

---

## 13. Customer Quality

### Customer Complaints

Access: **Quality → Customer Quality**

```
CUSTOMER COMPLAINT LOG
┌─────────────────────────────────────────────────────────────┐
│ Complaint  │ Customer   │ Issue          │ Status   │ Age   │
├────────────┼────────────┼────────────────┼──────────┼───────┤
│ CC-2026-01 │ Acme Corp  │ Wrong part qty │ 🔵 New   │ 1 day │
│ CC-2026-02 │ Best Co    │ Dimension OOT  │ 🟡 Invest│ 5 days│
│ CC-2025-89 │ Quality Inc│ Surface damage │ 🟢 Closed│ -     │
└────────────┴────────────┴────────────────┴──────────┴───────┘
```

### 8D Process

For significant complaints, use 8D:

| Step | Name | Activities |
|------|------|------------|
| D1 | Team | Form cross-functional team |
| D2 | Problem | Define the problem |
| D3 | Containment | Immediate actions |
| D4 | Root Cause | Identify true cause |
| D5 | Corrective Actions | Define solutions |
| D6 | Implement | Execute actions |
| D7 | Prevent | Prevent recurrence |
| D8 | Congratulate | Recognize team |

### Customer Returns

Track returned products:

1. Log RMA receipt
2. Inspect returned product
3. Determine cause
4. Create NC
5. Process credit/replacement
6. Update customer

### 13.2 Industrial Quoting Contributions
Quality Engineers participate in the Stage-Gate quoting workflow to ensure compliance and inspection requirements are costed accurately.

#### Quality Work Packet:
1. Open the **Quality Review Packet** in the Quoting Workbench.
2. Define the **Inspection Level** (e.g., AQL Level II, 100% Inspection).
3. Identify **Compliance Documents** required (e.g., RoHS, REACH, First Article Inspection - FAI).
4. Provide **Internal Notes** on quality risks or special equipment needs (e.g., CMM, X-Ray).
5. Click **Sign Off** to unblock the quoting process.

---

## 14. Reporting & Analytics

### Standard Quality Reports

Access: **Quality → Reports**

| Report | Purpose | Frequency |
|--------|---------|-----------|
| NC Summary | All NCs by type, status | Weekly |
| CAPA Status | Open CAPAs, overdue | Weekly |
| FPY Trend | First pass yield over time | Monthly |
| PPM Report | Defect rate trending | Monthly |
| Supplier Quality | Supplier performance | Monthly |
| Audit Summary | Findings and status | Quarterly |
| Management Review | QMS performance | Quarterly |

### Management Review Package

Compile data for management review:

```
MANAGEMENT REVIEW - Q4 2025
┌─────────────────────────────────────────────────────────────┐
│ QUALITY OBJECTIVES STATUS                                    │
│ ├─ FPY: 98.2% vs 98% Target ✓                               │
│ ├─ Customer PPM: 850 vs 1000 Target ✓                       │
│ ├─ Supplier PPM: 1200 vs 500 Target ✗                       │
│ └─ CAPA Close Rate: 92% vs 90% Target ✓                     │
│                                                              │
│ NC SUMMARY                                                   │
│ ├─ Total NCs: 45                                             │
│ ├─ Internal: 38 | Supplier: 5 | Customer: 2                 │
│ └─ Top Issues: Dimensional (35%), Surface (22%)             │
│                                                              │
│ CAPA STATUS                                                  │
│ ├─ Opened: 12 | Closed: 10 | Open: 8                        │
│ └─ Overdue: 1                                                │
│                                                              │
│ AUDIT FINDINGS                                               │
│ ├─ Internal: 3 Minor, 0 Major                               │
│ └─ External: 1 Minor (AS9100 surveillance)                  │
│                                                              │
│ [Generate Full Report]  [Export to PDF]                      │
└─────────────────────────────────────────────────────────────┘
```

### Custom Reports

Build custom reports:

1. **Reports → Report Builder**
2. Select data source (NCs, CAPAs, Inspections, etc.)
3. Choose fields and filters
4. Add charts if desired
5. Save and schedule

---

## 15. Continuous Improvement

### Quality Improvement Projects

Track improvement initiatives:

```
QUALITY IMPROVEMENT PROJECTS
┌─────────────────────────────────────────────────────────────┐
│ Project               │ Owner    │ Target  │ Status          │
├───────────────────────┼──────────┼─────────┼─────────────────┤
│ Reduce CNC scrap 50%  │ M. Garcia│ Q1 2026 │ 🟡 On Track     │
│ SPC implementation    │ D. Chen  │ Q2 2026 │ 🟢 Phase 2      │
│ Supplier development  │ Quality  │ Ongoing │ 🟡 Active       │
│ Inspection automation │ Quality  │ Q3 2026 │ 🔵 Planning     │
└───────────────────────┴──────────┴─────────┴─────────────────┘
```

### Cost of Quality

Track quality costs:

| Category | Examples | Target |
|----------|----------|--------|
| Prevention | Training, SPC, audits | Invest more |
| Appraisal | Inspection, testing | Optimize |
| Internal Failure | Scrap, rework | Reduce |
| External Failure | Returns, warranty | Eliminate |

### Lessons Learned

Document and share learnings:

1. After significant events (NC, CAPA, audit finding)
2. Capture what happened
3. Document what was learned
4. Share with relevant teams
5. Update procedures if needed

---

## Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + N` | New NC |
| `Ctrl + I` | Inspection queue |
| `Ctrl + Q` | Quality dashboard |
| `Ctrl + /` | Search |
| `F5` | Refresh |

### Quality Checklist - Daily

```
□ Review inspection queues
□ Check open NC age
□ Review SPC alerts
□ Respond to quality Andons
□ Update CAPA actions
□ Check calibration due
```

### Quality Checklist - Weekly

```
□ NC summary review
□ CAPA status meeting
□ Supplier quality check
□ Audit finding follow-up
□ Quality metrics update
```

### Key Contacts

| Need | Contact |
|------|---------|
| Production issues | Operations / GM |
| Engineering questions | Engineering Manager |
| Supplier issues | Purchasing |
| Customer issues | Sales |
| System support | IT |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Quality*
