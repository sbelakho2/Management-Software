# Maintenance Technician Starter Guide

> **Status:** The mobile app, PWA/offline mode, push notifications, barcode/camera
> capture, and battery/connectivity monitoring described in this guide are
> **planned — not implemented**. The web UI is the current interface.

## Sensei OS - Maintenance Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Maintenance Dashboard](#3-maintenance-dashboard)
4. [Work Order Management](#4-work-order-management)
5. [Preventive Maintenance](#5-preventive-maintenance)
6. [Reactive Maintenance](#6-reactive-maintenance)
7. [Equipment Management](#7-equipment-management)
8. [Spare Parts & Inventory](#8-spare-parts--inventory)
9. [Safety & Lockout/Tagout](#9-safety--lockouttagout)
10. [Downtime Tracking](#10-downtime-tracking)
11. [Documentation & History](#11-documentation--history)
12. [Mobile Maintenance](#12-mobile-maintenance)
13. [Predictive Maintenance](#13-predictive-maintenance)
14. [Vendor & Contractor Management](#14-vendor--contractor-management)
15. [Quick Reference](#15-quick-reference)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Track repair work and improvement actions as stories/subtasks (or issues for recurring defects).
- Add completion notes in comments for traceability and shift handoff.
- Use milestones for planned downtime, PM windows, and major maintenance events.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role in Maintenance

As a Maintenance Technician, you are the **keeper of equipment health**. Sensei OS empowers you to:

- **Respond to breakdowns** quickly and effectively
- **Perform preventive maintenance** systematically
- **Track equipment history** for informed decisions
- **Manage spare parts** to ensure availability
- **Reduce downtime** through proactive care
- **Ensure safety** in all maintenance activities

### Maintenance Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Work Orders | Full | Create, view, complete |
| PM Schedules | Execute | Perform scheduled PMs |
| Equipment Records | View + Update | Access history, log repairs |
| Parts Inventory | Request + Use | Check stock, request parts |
| Downtime Logging | Full | Record and categorize |
| Safety Procedures | View | Access LOTO procedures |
| Documentation | View + Add | Manuals, procedures |

### Maintenance Philosophy

```
HIERARCHY OF MAINTENANCE

         ┌─────────────────┐
         │   PREDICTIVE    │  ← Best: Anticipate failures
         │   (Condition)   │
         ├─────────────────┤
         │   PREVENTIVE    │  ← Good: Scheduled care
         │   (Time-based)  │
         ├─────────────────┤
         │   REACTIVE      │  ← Avoid: Fix when broken
         │   (Breakdown)   │
         └─────────────────┘
```

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter credentials
3. Complete MFA setup
4. Set up mobile app for floor use

### Initial Setup Tasks

- [ ] Verify your maintenance role permissions
- [ ] Review equipment assigned to you
- [ ] Check your PM schedule
- [ ] Set notification preferences (esp. Andons)
- [ ] Configure mobile scanner

### Your Maintenance Home Screen

```
┌─────────────────────────────────────────────────────────────┐
│               MAINTENANCE DASHBOARD                          │
│               January 11, 2026 - 10:15 AM                   │
├─────────────────────────────────────────────────────────────┤
│  MY WORK                                                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │ Open WOs   │ │ PM Due     │ │ Parts Req  │ │ Andons     ││
│  │     3      │ │     5      │ │     2      │ │  🔴 1      ││
│  │  assigned  │ │ this week  │ │  pending   │ │  active    ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘│
├─────────────────────────────────────────────────────────────┤
│  ACTIVE ANDON                                                │
│  🔴 CNC Mill 2 - Tool breakage (5 min ago) [Respond]        │
│                                                              │
│  TODAY'S SCHEDULE                                            │
│  ├─ 8 AM: PM-2026-045 - Hydraulic press weekly              │
│  ├─ 10 AM: WO-9876 - Lathe bearing replacement              │
│  └─ 2 PM: PM-2026-046 - Air compressor monthly              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Maintenance Dashboard

### Dashboard Widgets

#### Open Work Orders
Your assigned work orders:
- Emergency (Red)
- Urgent (Yellow)
- Normal (Blue)
- Low (Gray)

#### PM Due
Preventive maintenance coming due:
- Overdue (Red)
- Due This Week (Yellow)
- Upcoming (Blue)

#### Active Andons
Equipment-related Andons requiring response

#### Equipment Status
Overall equipment health:
```
EQUIPMENT STATUS
┌─────────────────────────────────────────────────────────────┐
│ ✓ Running: 45   │ ⚠️ Degraded: 3   │ 🔴 Down: 2            │
└─────────────────────────────────────────────────────────────┘
```

### Customizing Your View

1. Click **⚙️ Settings**
2. Select widgets to display
3. Set refresh interval
4. Save preferences

---

## 4. Work Order Management

### Work Order Types

| Type | Description | Priority |
|------|-------------|----------|
| Emergency | Equipment down, production stopped | Immediate |
| Urgent | Equipment degraded, risk of failure | Same day |
| Normal | Scheduled work, improvements | Planned |
| Low | Nice-to-have, when time permits | Backlog |

### Work Order Queue

Access: **Maintenance → Work Orders**

```
MY WORK ORDERS
┌─────────────────────────────────────────────────────────────┐
│ WO #     │ Equipment    │ Issue          │ Priority│ Status│
├──────────┼──────────────┼────────────────┼─────────┼───────┤
│ WO-9880  │ CNC Mill 2   │ Tool breakage  │ 🔴 Emerg│ New   │
│ WO-9876  │ Lathe 1      │ Bearing noise  │ 🟡 Urgent│ Open  │
│ WO-9850  │ Conveyor 3   │ Belt alignment │ 🔵 Normal│ Open  │
└──────────┴──────────────┴────────────────┴─────────┴───────┘
```

### Viewing a Work Order

```
┌─────────────────────────────────────────────────────────────┐
│  WORK ORDER: WO-9876                                         │
│  Status: Open | Priority: Urgent                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ EQUIPMENT                                                    │
│ ├─ ID: LATHE-001                                            │
│ ├─ Name: CNC Lathe #1                                       │
│ └─ Location: Cell 5                                         │
│                                                              │
│ PROBLEM DESCRIPTION                                          │
│ Unusual noise from spindle bearing during operation.         │
│ Intermittent vibration increasing over past 3 days.         │
│                                                              │
│ REPORTED BY                                                  │
│ John Smith (Operator) on Jan 10, 2026 at 3:45 PM           │
│                                                              │
│ ASSIGNED TO                                                  │
│ You - Assigned Jan 10, 2026                                 │
│                                                              │
│ ATTACHMENTS                                                  │
│ [📄 Equipment Manual] [📸 Photo from operator]               │
│                                                              │
│ [Start Work] [Request Parts] [Add Notes] [Escalate]         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Starting Work on a WO

1. Click **Start Work**
2. System logs start time
3. Select work type:
   - Diagnosis
   - Repair
   - Testing
4. Perform the work
5. Log activities as you go

### Logging Work

```
┌─────────────────────────────────────────────────────────────┐
│  LOG WORK - WO-9876                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Activity Type:   [Repair            ▼]                       │
│ Time Spent:      [2    ] hours                              │
│                                                              │
│ Work Performed:                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Removed spindle assembly. Found bearing 6205RS worn.   │ │
│ │ Replaced with new bearing from stock. Reassembled      │ │
│ │ and tested. Vibration eliminated.                       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Root Cause:      [Normal Wear       ▼]                       │
│ Failure Code:    [MECH-BEARING-WORN ▼]                       │
│                                                              │
│ Parts Used:                                                  │
│ ├─ 6205RS Bearing × 1 (from stock)                          │
│ └─ [+ Add Part]                                             │
│                                                              │
│ Photos:          [📷 Add Photo]                              │
│                                                              │
│ [Save Notes]  [Complete Work Order]                         │
└─────────────────────────────────────────────────────────────┘
```

### Completing a Work Order

1. Log all work performed
2. Record parts used
3. Add photos if applicable
4. Set equipment status (Running/Degraded/Down)
5. Click **Complete Work Order**
6. Rate repair effectiveness (for trending)

---

## 5. Preventive Maintenance

### PM Schedule

Access: **Maintenance → Preventive Maintenance**

```
PM SCHEDULE - My Assignments
┌─────────────────────────────────────────────────────────────┐
│ PM #       │ Equipment     │ Task              │ Due    │ St│
├────────────┼───────────────┼───────────────────┼────────┼───┤
│ PM-2026-045│ Hydr Press 1  │ Weekly inspection │ Today  │ ⏳│
│ PM-2026-046│ Air Compressor│ Monthly service   │ Today  │ ⏳│
│ PM-2026-047│ CNC Mill 1    │ Quarterly lube    │ Jan 15 │ ⏳│
│ PM-2026-048│ Conveyor 1    │ Belt inspection   │ Jan 18 │ ⏳│
└────────────┴───────────────┴───────────────────┴────────┴───┘
```

### Performing a PM

1. Open the PM task
2. Review the checklist:

```
┌─────────────────────────────────────────────────────────────┐
│  PM: PM-2026-045                                             │
│  Equipment: Hydraulic Press #1                               │
│  Task: Weekly Inspection                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ CHECKLIST                                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Step │ Task                           │ Status │ Notes  │ │
│ ├──────┼────────────────────────────────┼────────┼────────┤ │
│ │ 1    │ Check hydraulic fluid level    │ ☑ Pass │        │ │
│ │ 2    │ Inspect hoses for leaks        │ ☑ Pass │        │ │
│ │ 3    │ Check pressure gauge           │ ☑ Pass │ 2850psi│ │
│ │ 4    │ Inspect safety guards          │ ☑ Pass │        │ │
│ │ 5    │ Test emergency stop            │ ☑ Pass │        │ │
│ │ 6    │ Clean and wipe down            │ ☐      │        │ │
│ └──────┴────────────────────────────────┴────────┴────────┘ │
│                                                              │
│ READINGS                                                     │
│ ├─ Hydraulic Pressure: [2850 ] PSI (Normal: 2800-3000)      │
│ ├─ Oil Temperature: [145  ] °F (Normal: <160)               │
│ └─ Operating Hours: [12,456]                                 │
│                                                              │
│ Issues Found:                                                │
│ [None - equipment in good condition                   ]     │
│                                                              │
│ [Save Progress]  [Complete PM]                               │
└─────────────────────────────────────────────────────────────┘
```

3. Complete each checklist item
4. Record readings and measurements
5. Note any issues found
6. Complete the PM

### If Issues Are Found

When PM reveals problems:

1. Document the issue in PM notes
2. Click **Create Work Order**
3. System creates WO linked to PM
4. Complete the PM
5. Address WO separately (or escalate)

### PM Types

| Frequency | Examples |
|-----------|----------|
| Daily | Operator checks, clean-up |
| Weekly | Inspections, minor lubrication |
| Monthly | Filter changes, belt checks |
| Quarterly | Deep cleaning, calibration |
| Annual | Overhauls, major service |

---

## 6. Reactive Maintenance

### Responding to Breakdowns

When equipment fails:

1. **Andon Alert** appears on dashboard
2. Click **Respond** or **Acknowledge**
3. Go to the equipment
4. Assess the situation
5. Create work order (if not auto-created)
6. Begin repair

### Emergency Response

```
🔴 EMERGENCY ANDON
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ EQUIPMENT: CNC Mill 2                                        │
│ LOCATION: Cell 3                                             │
│ TIME: 10:10 AM (5 minutes ago)                              │
│                                                              │
│ REPORTED ISSUE:                                              │
│ Tool broke during operation. Machine stopped.               │
│ Error code: E-234                                            │
│                                                              │
│ OPERATOR: Maria Garcia                                       │
│                                                              │
│ [I'm Responding]  [Assign to:]  [Escalate]                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Troubleshooting Steps

1. **Safety First**
   - Ensure equipment is safe
   - LOTO if required

2. **Gather Information**
   - Talk to operator
   - Check error codes
   - Review recent history

3. **Diagnose**
   - Systematic troubleshooting
   - Use manuals and docs
   - Check similar past issues

4. **Repair**
   - Fix the root cause
   - Not just symptoms

5. **Test and Return**
   - Test thoroughly
   - Return to production
   - Monitor for recurrence

### Error Code Lookup

Access equipment-specific error codes:

```
ERROR CODE LOOKUP - CNC Mill 2
┌─────────────────────────────────────────────────────────────┐
│ Error Code: E-234                                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Description: Spindle overload detected                       │
│                                                              │
│ Possible Causes:                                             │
│ 1. Tool breakage or excessive wear                          │
│ 2. Incorrect feeds/speeds                                    │
│ 3. Spindle drive fault                                       │
│ 4. Coolant flow issue                                        │
│                                                              │
│ Recommended Actions:                                         │
│ 1. Check tool condition                                      │
│ 2. Verify program parameters                                 │
│ 3. Check spindle motor current draw                         │
│ 4. Verify coolant system operation                          │
│                                                              │
│ Related Documents:                                           │
│ [📄 Spindle Service Manual] [📄 Error Code Reference]        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Equipment Management

### Equipment Registry

Access: **Maintenance → Equipment**

```
EQUIPMENT LIST
┌─────────────────────────────────────────────────────────────┐
│ ID        │ Name           │ Location │ Status │ Last PM   │
├───────────┼────────────────┼──────────┼────────┼───────────┤
│ CNC-001   │ CNC Mill #1    │ Cell 1   │ ✓ Run  │ Jan 8     │
│ CNC-002   │ CNC Mill #2    │ Cell 3   │ 🔴 Down│ Jan 5     │
│ LATHE-001 │ CNC Lathe #1   │ Cell 5   │ ⚠️ Degr│ Jan 3     │
│ PRESS-001 │ Hydr Press #1  │ Cell 7   │ ✓ Run  │ Today     │
└───────────┴────────────────┴──────────┴────────┴───────────┘
```

### Equipment Detail

```
EQUIPMENT: CNC-001
┌─────────────────────────────────────────────────────────────┐
│ CNC Milling Machine #1                                       │
│ Manufacturer: Haas | Model: VF-2 | S/N: 12345               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ GENERAL                                                      │
│ ├─ Location: Cell 1                                         │
│ ├─ Install Date: March 15, 2018                             │
│ ├─ Criticality: A (Critical)                                │
│ └─ Status: ✓ Running                                        │
│                                                              │
│ OPERATING DATA                                               │
│ ├─ Operating Hours: 24,567                                  │
│ ├─ Parts Produced: 145,230                                  │
│ ├─ MTBF: 720 hours                                          │
│ └─ MTTR: 2.5 hours                                          │
│                                                              │
│ MAINTENANCE                                                  │
│ ├─ Last PM: Jan 8, 2026                                     │
│ ├─ Next PM: Jan 15, 2026 (Weekly)                           │
│ ├─ Open WOs: 0                                              │
│ └─ YTD Downtime: 12.5 hours                                 │
│                                                              │
│ [View History] [View PMs] [Create WO] [View Manuals]        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Equipment Hierarchy

Understand equipment structure:

```
EQUIPMENT HIERARCHY
└── CNC-001 (CNC Mill #1)
    ├── SPINDLE (Spindle Assembly)
    │   ├── SPINDLE-MOTOR
    │   └── SPINDLE-BEARING
    ├── AXIS-X (X-Axis Assembly)
    │   ├── SERVO-X
    │   └── BALLSCREW-X
    ├── AXIS-Y (Y-Axis Assembly)
    ├── AXIS-Z (Z-Axis Assembly)
    ├── COOLANT (Coolant System)
    │   ├── COOLANT-PUMP
    │   └── COOLANT-TANK
    └── ELECTRIC (Electrical System)
```

### Equipment Criticality

| Class | Definition | PM Priority | Spare Parts |
|-------|------------|-------------|-------------|
| A | Critical - production stops | Highest | Full stock |
| B | Important - degraded production | High | Key items |
| C | Support - workarounds exist | Normal | Order as needed |

---

## 8. Spare Parts & Inventory

### Parts Lookup

Access: **Maintenance → Spare Parts**

```
SPARE PARTS SEARCH
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search: [bearing 6205              ]                     │
├─────────────────────────────────────────────────────────────┤
│ Part #   │ Description        │ Qty On Hand │ Bin Location │
├──────────┼────────────────────┼─────────────┼──────────────┤
│ BRG-6205 │ Bearing 6205RS     │ 5           │ MAINT-A-01   │
│ BRG-6205Z│ Bearing 6205ZZ     │ 3           │ MAINT-A-01   │
└──────────┴────────────────────┴─────────────┴──────────────┘
```

### Requesting Parts

When you need parts not in stock:

```
┌─────────────────────────────────────────────────────────────┐
│  REQUEST PARTS                                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Work Order:     [WO-9876           ▼]                       │
│ Equipment:      LATHE-001 (auto-filled)                     │
│                                                              │
│ PARTS NEEDED                                                 │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Part #    │ Description     │ Qty │ Urgency │ Status   │ │
│ ├───────────┼─────────────────┼─────┼─────────┼──────────┤ │
│ │ BRG-6208  │ Bearing 6208RS  │ 1   │ Urgent  │ + Added  │ │
│ │           │ [+ Add Part]    │     │         │          │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                              │
│ Reason: [Spindle bearing replacement               ]        │
│                                                              │
│ [Submit Request]                                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Checking Out Parts

When using parts from stock:

1. Scan part barcode
2. Enter quantity
3. Link to work order
4. System updates inventory

```
PARTS ISSUE
┌─────────────────────────────────────────────────────────────┐
│ Part: BRG-6205RS - Bearing 6205RS                           │
│ On Hand: 5                                                   │
│                                                              │
│ Issue Qty:   [1   ]                                         │
│ Work Order:  [WO-9876        ▼]                             │
│ Equipment:   LATHE-001                                       │
│                                                              │
│ [Issue Part]                                                 │
└─────────────────────────────────────────────────────────────┘
```

### Parts Where Used

See where parts are used:

```
PART: BRG-6205RS
WHERE USED:
├─ CNC-001 (Spindle, Qty: 2)
├─ CNC-002 (Spindle, Qty: 2)
├─ LATHE-001 (Spindle, Qty: 1)
└─ PUMP-001 (Motor, Qty: 2)
```

---

## 9. Safety & Lockout/Tagout

### LOTO Procedures

Access: **Maintenance → Safety → LOTO**

Before working on equipment:

```
┌─────────────────────────────────────────────────────────────┐
│  LOCKOUT/TAGOUT PROCEDURE                                    │
│  Equipment: CNC Mill 2                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ⚠️ ENERGY SOURCES                                           │
│ ├─ Electrical: 480V 3-phase, Panel A, Breaker 12            │
│ ├─ Pneumatic: Main air supply, Valve V-12                   │
│ └─ Hydraulic: None                                           │
│                                                              │
│ PROCEDURE                                                    │
│ 1. Notify operator and supervisor                           │
│ 2. Shut down machine using normal controls                  │
│ 3. Disconnect main power at Panel A, Breaker 12             │
│ 4. Apply lock to breaker                                    │
│ 5. Close pneumatic valve V-12                               │
│ 6. Apply lock to valve                                      │
│ 7. Verify zero energy:                                       │
│    - Try to start machine (should not start)               │
│    - Check pneumatic gauge (should read zero)              │
│ 8. Attach LOTO tag with your name and date                 │
│                                                              │
│ [Begin LOTO] (Logs your lock application)                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Logging LOTO

When applying locks:

1. Click **Begin LOTO**
2. System records:
   - Your name
   - Date/time
   - Equipment
   - Lock number
3. When complete, click **Remove LOTO**
4. Verify all your locks removed
5. System confirms

### Safety Reminders

| Before Working | During Work | After Work |
|----------------|-------------|------------|
| LOTO applied | Maintain LOTO | Remove LOTO |
| PPE worn | Follow procedures | Clean up |
| Area secured | No shortcuts | Test safely |
| Permits (if needed) | Ask if unsure | Report issues |

---

## 10. Downtime Tracking

### Logging Downtime

Every equipment stoppage is tracked:

```
┌─────────────────────────────────────────────────────────────┐
│  DOWNTIME LOG                                                │
│  Equipment: CNC Mill 2                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Downtime Start:  Jan 11, 2026 10:10 AM                      │
│ Downtime End:    [In Progress           ]                   │
│ Duration:        1 hour 25 minutes                          │
│                                                              │
│ Category:        [Mechanical Failure   ▼]                    │
│ Reason:          [Tool Breakage        ▼]                    │
│                                                              │
│ Root Cause:      [Worn bearing caused vibration leading    ]│
│                  [to tool breakage                         ]│
│                                                              │
│ Actions Taken:   [Replaced bearing and broken tool.        ]│
│                  [Verified spindle runout in spec.         ]│
│                                                              │
│ [End Downtime]                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Downtime Categories

| Category | Examples |
|----------|----------|
| Mechanical | Bearing, motor, pump failures |
| Electrical | Drive, sensor, wiring issues |
| Tooling | Tool breakage, wear |
| Programming | Code errors, setup issues |
| Operator | User error, training gap |
| Material | Bad material, wrong material |
| Planned | PM, changeover, cleanup |

### Downtime Analysis

View downtime trends:

```
DOWNTIME SUMMARY - January 2026
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ BY CATEGORY                                                  │
│ Mechanical   ████████████████  45%  (18 hours)              │
│ Electrical   ██████            15%  (6 hours)               │
│ Tooling      ████              10%  (4 hours)               │
│ Planned      ████████          20%  (8 hours)               │
│ Other        ████              10%  (4 hours)               │
│                                                              │
│ TOTAL: 40 hours | Target: <30 hours                         │
│                                                              │
│ TOP OFFENDERS                                                │
│ 1. CNC Mill 2 - 12 hours (Spindle issues)                  │
│ 2. Lathe 1 - 8 hours (Bearing failure)                     │
│ 3. Conveyor 3 - 5 hours (Belt issues)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 11. Documentation & History

### Equipment History

Access full maintenance history:

```
EQUIPMENT HISTORY - CNC-001
┌─────────────────────────────────────────────────────────────┐
│ Date      │ Type   │ Reference │ Description        │ Tech  │
├───────────┼────────┼───────────┼────────────────────┼───────┤
│ Jan 11    │ PM     │ PM-045    │ Weekly inspection  │ You   │
│ Jan 5     │ WO     │ WO-9820   │ Coolant pump       │ DBrow │
│ Jan 1     │ PM     │ PM-038    │ Quarterly lube     │ You   │
│ Dec 20    │ WO     │ WO-9750   │ Spindle alignment  │ MJone │
│ Dec 15    │ PM     │ PM-032    │ Weekly inspection  │ DBrow │
└───────────┴────────┴───────────┴────────────────────┴───────┘
```

### Accessing Manuals

Find equipment documentation:

```
DOCUMENTATION - CNC-001
┌─────────────────────────────────────────────────────────────┐
│ MANUALS                                                      │
│ ├─ [📄 Operator Manual]                                      │
│ ├─ [📄 Service Manual]                                       │
│ ├─ [📄 Parts Catalog]                                        │
│ └─ [📄 Electrical Schematics]                               │
│                                                              │
│ PROCEDURES                                                   │
│ ├─ [📄 PM Checklist - Weekly]                               │
│ ├─ [📄 PM Checklist - Quarterly]                            │
│ ├─ [📄 Spindle Replacement]                                 │
│ └─ [📄 LOTO Procedure]                                      │
│                                                              │
│ DRAWINGS                                                     │
│ ├─ [📐 Mechanical Layout]                                   │
│ └─ [📐 Electrical Diagram]                                  │
└─────────────────────────────────────────────────────────────┘
```

### Adding Documentation

Upload new documents:

1. Go to equipment record
2. Click **Add Document**
3. Select file
4. Categorize (Manual, Procedure, etc.)
5. Add description
6. Upload

---

## 12. Mobile Maintenance

### Mobile App Features

Use the mobile app for floor work:

- View and update work orders
- Complete PM checklists
- Scan equipment barcodes
- Take and attach photos
- Check parts availability
- Look up error codes
- Access documentation

### Scanning Equipment

1. Open mobile app
2. Tap **Scan**
3. Scan equipment barcode/QR
4. View equipment info
5. Quick actions:
   - Create WO
   - View history
   - Check PM status

### Taking Photos

Document your work:

1. On work order, tap **📷**
2. Take photo
3. Add caption (optional)
4. Photo attaches to WO

---

## 13. Predictive Maintenance

### Condition Monitoring

Track equipment condition:

```
CONDITION MONITORING - CNC-001
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ VIBRATION (Spindle)                                          │
│ Current: 2.1 mm/s | Normal: <3.0 | Alert: >4.0             │
│ ████████████░░░░░░░░  70%                                    │
│ Trend: Stable ✓                                              │
│                                                              │
│ TEMPERATURE (Spindle Motor)                                  │
│ Current: 145°F | Normal: <160 | Alert: >175                 │
│ ██████████████░░░░░░  75%                                    │
│ Trend: Stable ✓                                              │
│                                                              │
│ OIL ANALYSIS (Hydraulic)                                     │
│ Last Sample: Dec 15, 2025 | Status: Good                    │
│ Next Sample: Mar 15, 2026                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Alerts

System alerts when conditions change:

| Alert Type | Trigger | Action |
|------------|---------|--------|
| Warning | Approaching limit | Monitor closely |
| Alert | At limit | Plan maintenance |
| Critical | Over limit | Stop and repair |

### Trending

View trends over time to predict failures:

```
VIBRATION TREND - CNC-001 Spindle
┌─────────────────────────────────────────────────────────────┐
│      │                                          Alert ───   │
│  4.0 │                                                      │
│      │                                                      │
│  3.0 │                              ●   ●   ●              │
│      │                      ●   ●   ●                       │
│  2.0 │  ●   ●   ●   ●   ●                                   │
│      │                                                      │
│  1.0 │                                                      │
│      └──────────────────────────────────────────────────────│
│        Oct   Nov   Dec   Jan   Feb   Mar   Apr              │
│                                                              │
│ ⚠️ Trend increasing - schedule inspection                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. Vendor & Contractor Management

### External Service

Track outside maintenance:

```
SERVICE CONTRACTORS
┌─────────────────────────────────────────────────────────────┐
│ Vendor          │ Service          │ Contract │ Contact    │
├─────────────────┼──────────────────┼──────────┼────────────┤
│ ABC Drives      │ VFD Repair       │ Current  │ 555-1234   │
│ XYZ Calibration │ Gauge Cal        │ Current  │ 555-2345   │
│ PQR Welding     │ Structural       │ On-Call  │ 555-3456   │
│ Machine Builder │ OEM Service      │ Warranty │ 555-4567   │
└─────────────────┴──────────────────┴──────────┴────────────┘
```

### Logging External Work

When vendors perform work:

1. Create work order as usual
2. Assign to "External Vendor"
3. Record vendor name
4. Attach vendor work order/invoice
5. Log work performed
6. Complete as normal

---

## 15. Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + W` | Work orders |
| `Ctrl + E` | Equipment search |
| `Ctrl + P` | PM schedule |
| `Ctrl + /` | Global search |
| `F5` | Refresh |

### Daily Maintenance Checklist

```
SHIFT START
□ Check Andon queue
□ Review assigned WOs
□ Check PM schedule
□ Review overnight issues

DURING SHIFT
□ Respond to breakdowns
□ Complete assigned PMs
□ Log all work
□ Document parts used

SHIFT END
□ Complete open WOs if possible
□ Update in-progress work
□ Handover notes
□ Report pending issues
```

### Priority Response Times

| Priority | Response | Resolution |
|----------|----------|------------|
| Emergency | Immediate | ASAP |
| Urgent | < 1 hour | Same day |
| Normal | Same day | 1-3 days |
| Low | 1-2 days | 1 week |

### MTBF/MTTR Goals

| Metric | Target |
|--------|--------|
| MTBF (Mean Time Between Failures) | Increasing |
| MTTR (Mean Time To Repair) | < 2 hours |
| OEE (Overall Equipment Effectiveness) | > 85% |
| PM Compliance | 100% |

### Emergency Contacts

| Emergency | Contact |
|-----------|---------|
| Electrical | Maintenance Lead ext. 5100 |
| Safety | Safety Manager ext. 5555 |
| Vendor (OEM) | See vendor list |
| Supervisor | Maintenance Sup ext. 5050 |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Maintenance*
