# Operations Manager / Supervisor Starter Guide

> **Status:** The mobile app, PWA/offline mode, push notifications, barcode/camera
> capture, and battery/connectivity monitoring described in this guide are
> **planned — not implemented**. The web UI is the current interface.

## Sensei OS - Operations Supervisor Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Your Supervisor Dashboard](#3-your-supervisor-dashboard)
4. [Daily Shift Management](#4-daily-shift-management)
5. [Production Control](#5-production-control)
6. [Team Leadership](#6-team-leadership)
7. [Quality on the Floor](#7-quality-on-the-floor)
8. [Andon & Problem Response](#8-andon--problem-response)
9. [Time & Attendance](#9-time--attendance)
10. [Training & Development](#10-training--development)
11. [Standard Work](#11-standard-work)
12. [Safety Management](#12-safety-management)
13. [Continuous Improvement](#13-continuous-improvement)
14. [Mobile Tools](#14-mobile-tools)
15. [Escalation & Communication](#15-escalation--communication)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use sprint views to coordinate daily/weekly execution and surface blockers early.
- Keep stories and subtasks current (status + comments) to reduce handoff friction.
- Use issues to track recurring problems and ensure they don’t get lost in the backlog.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role as Supervisor

As Operations Supervisor, you are the **frontline leader** ensuring daily production goals are met safely and with quality. Sensei OS empowers you to:

- **Manage your team** and assign work effectively
- **Track production** in real-time
- **Respond to issues** quickly with Andon support
- **Maintain quality** at the source
- **Develop your people** through training and coaching

### Supervisor Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Production Schedule | View + Execute | See and act on today's schedule |
| Work Orders | Full | Start, pause, complete, report issues |
| Team Management | Your Team | Attendance, assignments, coaching |
| Quality | Log + Contain | Report issues, contain defects |
| Training | Assign + Track | Manage team certifications |
| Standard Work | View + Update | Access and improve work instructions |
| Equipment | Report + Request | Log issues, request maintenance |
| Approvals | Limited | Time off, minor schedule changes |

### What Makes Supervisor Access Unique

1. **Real-time Shop Floor View**: Live production status
2. **Team Dashboard**: Your team's attendance, skills, workload
3. **Andon Response**: First responder to production issues
4. **Training Matrix**: Skills visibility for your team
5. **Quick Logging**: Fast entry of production data

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter your username and password
3. Set up Multi-Factor Authentication (MFA)
4. Complete your profile

### Initial Profile Setup

- [ ] Upload photo (helps team identify you in system)
- [ ] Verify contact information
- [ ] Set notification preferences
- [ ] Configure mobile app
- [ ] Review your team roster

### Understanding Your Home Screen

When you log in, you'll see your **Supervisor Dashboard**:

```
┌─────────────────────────────────────────────────────────────┐
│               SUPERVISOR DASHBOARD                           │
│               Shift: Day | January 11, 2026                 │
├─────────────────────────────────────────────────────────────┤
│  MY TEAM TODAY          │  TODAY'S SCHEDULE                 │
│  ┌──────────────────┐   │  Jobs: 8                          │
│  │ Present: 10/11   │   │  On Track: 6 ✓                    │
│  │ Training: 1      │   │  At Risk: 1 ⚠️                     │
│  │ Absent: 0        │   │  Behind: 1 🔴                      │
│  └──────────────────┘   │                                   │
├─────────────────────────────────────────────────────────────┤
│  ACTIVE WORK ORDERS     │  ISSUES                           │
│  ▶ JOB-1234 (Cell 1)    │  🔴 Andon - Cell 3 (5 min)        │
│  ▶ JOB-1235 (Cell 2)    │  🟡 Material low - Cell 5         │
│  ⏸ JOB-1236 (Setup)     │  🟡 Quality check needed          │
│  ⏳ JOB-1237 (Queue)     │                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Your Supervisor Dashboard

### Dashboard Widgets

#### My Team Today
Shows current team status:
- **Present**: Clocked in and working
- **Training**: In scheduled training
- **Absent**: Not clocked in (with reason if known)

Click any number to see details.

#### Today's Schedule
Your production schedule status:
- **On Track** ✓: Proceeding as planned
- **At Risk** ⚠️: May miss target without action
- **Behind** 🔴: Already late, needs recovery

#### Active Work Orders
Live status of work in progress:
- ▶ **Running**: Actively producing
- ⏸ **Paused**: Setup, break, or issue
- ⏳ **Queue**: Next up
- ✓ **Complete**: Finished

#### Issues Panel
Problems requiring your attention:
- **Red**: Immediate action needed
- **Yellow**: Monitor or act soon
- **Blue**: Informational

### Customizing Your Dashboard

1. Click **⚙️** (settings icon)
2. Drag widgets to rearrange
3. Add/remove widgets as needed
4. Save as default

---

## 4. Daily Shift Management

### Start of Shift Checklist

```
SHIFT START CHECKLIST
□ Review overnight log / handover notes
□ Check team attendance
□ Review today's production schedule
□ Verify material availability
□ Check equipment status
□ Assign operators to stations
□ Brief team on priorities
□ Start first work orders
```

### Shift Handover

Access: **Production → Shift Handover**

At end of shift, complete handover:

```
┌─────────────────────────────────────────────────────────────┐
│              SHIFT HANDOVER REPORT                           │
│              Day Shift → Night Shift                        │
├─────────────────────────────────────────────────────────────┤
│ PRODUCTION SUMMARY                                           │
│ • Jobs completed: 6 of 8                                    │
│ • Jobs in progress: 2                                       │
│ • Quality issues: 1 NC (contained)                          │
│                                                              │
│ CARRY-OVER ITEMS                                             │
│ 1. JOB-1236 - 75% complete, continue on Cell 2              │
│ 2. JOB-1237 - Not started, material arriving at 8 PM       │
│                                                              │
│ WATCH ITEMS                                                  │
│ • CNC Mill 3 making unusual noise - monitor                 │
│ • New operator Sarah on Cell 5 - may need support           │
│                                                              │
│ EQUIPMENT ISSUES                                             │
│ • None                                                       │
│                                                              │
│ SAFETY NOTES                                                 │
│ • Wet floor near dock - cones placed                        │
├─────────────────────────────────────────────────────────────┤
│                    [Submit Handover]                         │
└─────────────────────────────────────────────────────────────┘
```

### Throughout the Shift

Regular check-ins you should make:

| Time | Activity |
|------|----------|
| Every hour | Walk the floor, check in with team |
| Every 2 hours | Check production progress vs plan |
| As needed | Respond to Andons and issues |
| Mid-shift | Review with next shift supervisor |
| End of shift | Complete handover report |

---

## 5. Production Control

### Work Order Management

Access: **Production → Work Orders**

Each work order contains:

| Field | Description |
|-------|-------------|
| WO Number | Unique identifier (e.g., JOB-1234) |
| Part Number | What's being made |
| Quantity | How many to produce |
| Due Date | When it needs to ship |
| Operations | Steps to complete |
| Status | Current state |
| Assigned | Operator(s) working on it |

### Work Order States

```
NOT STARTED → IN PROGRESS → COMPLETE
              ↓
            ON HOLD (if issue)
              ↓
            RESUME or SCRAP
```

### Starting a Work Order

1. Click the work order
2. Click **Start Work**
3. Select operator(s)
4. Select work center
5. Confirm start

The system timestamps the start and tracks labor.

### Logging Production

At each operation:

1. Open the work order
2. Go to current operation
3. Enter:
   - Quantity good
   - Quantity scrap (if any)
   - Actual time
4. Click **Complete Operation** or **Next**

### Handling Issues

If a problem occurs:

1. Click **Log Issue** on work order
2. Select issue type:
   - Material problem
   - Equipment issue
   - Quality defect
   - Missing information
   - Other
3. Add description
4. System notifies appropriate people

---

## 6. Team Leadership

### Your Team Roster

Access: **People → My Team**

```
┌─────────────────────────────────────────────────────────────┐
│                    MY TEAM                                   │
├─────────────────────────────────────────────────────────────┤
│ Name           │ Role      │ Shift │ Status    │ Cell      │
├────────────────┼───────────┼───────┼───────────┼───────────┤
│ John Smith     │ Operator  │ Day   │ ✓ Working │ CNC-1     │
│ Maria Garcia   │ Operator  │ Day   │ ✓ Working │ Assembly  │
│ David Chen     │ Lead      │ Day   │ ✓ Working │ Float     │
│ Sarah Johnson  │ Operator  │ Day   │ 📚 Training│ -         │
│ Mike Williams  │ Operator  │ Day   │ ✓ Working │ Lathe-2   │
└─────────────────────────────────────────────────────────────┘
```

### Assigning Operators

To assign operators to work centers:

1. Open the **Assignment Board**
2. Drag operator names to work centers
3. System validates skill requirements
4. Save assignments

```
ASSIGNMENT BOARD - Day Shift
┌─────────────────────────────────────────────────────────────┐
│ Work Center    │ Assigned           │ Skills Required       │
├────────────────┼────────────────────┼───────────────────────┤
│ CNC Mill 1     │ John Smith ✓       │ CNC ★★★               │
│ CNC Mill 2     │ [Drag operator]    │ CNC ★★                │
│ Lathe 1        │ Mike Williams ✓    │ Lathe ★★              │
│ Assembly 1     │ Maria Garcia ✓     │ Assembly ★★           │
└─────────────────────────────────────────────────────────────┘
```

### Team Skill Matrix

View your team's capabilities:

```
SKILL MATRIX - Your Team
┌─────────────────────────────────────────────────────────────┐
│ Operator       │ CNC │ Lathe │ Weld │ Assy │ Insp │        │
├────────────────┼─────┼───────┼──────┼──────┼──────┼────────┤
│ John Smith     │ ★★★ │ ★★    │ ○    │ ★    │ ★★   │ Primary│
│ Maria Garcia   │ ★   │ ★     │ ★★★  │ ★★★  │ ★★   │        │
│ David Chen     │ ★★★ │ ★★★   │ ★★   │ ★★   │ ★★★  │ Lead   │
│ Sarah Johnson  │ ★   │ ○     │ ○    │ ★★   │ ★    │ New    │
│ Mike Williams  │ ★★  │ ★★★   │ ★    │ ★    │ ★    │        │
└─────────────────────────────────────────────────────────────┘
★★★ = Expert | ★★ = Proficient | ★ = Basic | ○ = Not trained
```

### One-on-One Notes

Log coaching conversations:

1. Go to team member's profile
2. Click **Add Note**
3. Select type: Coaching | Recognition | Concern | Development
4. Enter details
5. Set follow-up if needed

---

## 7. Quality on the Floor

### Your Quality Responsibilities

As supervisor, you ensure:

- **First piece inspection** is completed
- **In-process checks** happen on schedule
- **Defects are contained** immediately
- **NCs are logged** properly
- **Operators follow** quality procedures

### Logging a Nonconformance (NC)

When you find a quality issue:

1. Go to **Quality → Log NC**
2. Enter details:

```
┌─────────────────────────────────────────────────────────────┐
│               LOG NONCONFORMANCE                             │
├─────────────────────────────────────────────────────────────┤
│ Work Order:     [JOB-1234        ▼]                         │
│ Part Number:    ABC-123                                     │
│ Quantity Affected: [5   ]                                   │
│ Defect Type:    [Dimensional     ▼]                         │
│ Description:    [Diameter 0.003" over max              ]    │
│ Severity:       [Minor           ▼]                         │
│                                                              │
│ Containment:                                                │
│ ☑ Parts segregated                                          │
│ ☑ Production stopped pending review                         │
│ ☐ Customer notification required                            │
│                                                              │
│ Photos:         [📷 Add Photos]                              │
├─────────────────────────────────────────────────────────────┤
│            [Cancel]              [Submit NC]                 │
└─────────────────────────────────────────────────────────────┘
```

### First Piece Inspection

Verify first piece before production run:

1. Operator produces first piece
2. Open work order → **First Piece**
3. Record measurements
4. Compare to spec
5. Mark Pass or Fail
6. If pass, authorize production

### SPC Charts

View Statistical Process Control:

```
SPC CHART - CNC Mill 1 - Diameter
Upper Limit: 1.005
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Target: 1.000                        ● ●   ●
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━●━●━●━━━●━●━━━━━
Lower Limit: 0.995      ●   ●   ●
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
                        8   9   10  11  12  1   2 PM
```

If you see trends or out-of-spec points, investigate immediately.

---

## 8. Andon & Problem Response

### What is Andon?

Andon is the immediate alert system for production issues. When an operator needs help:

1. They trigger the **Andon**
2. You receive **immediate notification**
3. You **respond** to the cell
4. You **resolve or escalate** the issue
5. The system **tracks response time**

### Andon Categories

| Color | Meaning | Response Time |
|-------|---------|---------------|
| 🔴 Red | Line Stop / Safety | Immediate |
| 🟡 Yellow | Quality Issue | < 5 minutes |
| 🔵 Blue | Material Needed | < 10 minutes |
| ⚪ White | Support Request | < 15 minutes |

### Responding to Andon

When you receive an Andon alert:

```
┌─────────────────────────────────────────────────────────────┐
│  🔴 ANDON ALERT - CELL 3 - CNC MILL 2                       │
│  Time: 10:32 AM | Elapsed: 3 minutes                        │
├─────────────────────────────────────────────────────────────┤
│  Operator: John Smith                                        │
│  Reason: Tool breakage                                       │
│  Work Order: JOB-1234                                        │
│  Current Status: Machine stopped                             │
├─────────────────────────────────────────────────────────────┤
│  [Acknowledge]  [On My Way]  [Assign to:]  [Escalate]       │
└─────────────────────────────────────────────────────────────┘
```

**Your options**:
- **Acknowledge**: You're aware (clock keeps running)
- **On My Way**: You're responding personally
- **Assign to**: Send team lead or maintenance
- **Escalate**: Send to GM or maintenance lead

### Closing an Andon

After resolving the issue:

1. Go to the Andon record
2. Click **Resolve**
3. Enter resolution:
   - What was the problem?
   - What action was taken?
   - Prevent recurrence? (Kaizen opportunity?)
4. Andon closes, metrics recorded

### Andon Metrics

Track your response performance:

```
ANDON METRICS - This Week
┌─────────────────────────────────────────────────────────────┐
│ Total Andons:        15                                      │
│ Average Response:    4.2 minutes (Target: < 5)              │
│ Average Resolution:  18 minutes                              │
│ Top Causes:                                                  │
│   1. Material shortage (5)                                   │
│   2. Tool wear (4)                                           │
│   3. Quality question (3)                                    │
│   4. Other (3)                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Time & Attendance

### Team Attendance View

Access: **People → Attendance**

```
TODAY'S ATTENDANCE - Your Team
┌─────────────────────────────────────────────────────────────┐
│ Name           │ Scheduled │ Clock In │ Status              │
├────────────────┼───────────┼──────────┼─────────────────────┤
│ John Smith     │ 6:00 AM   │ 5:55 AM  │ ✓ Working           │
│ Maria Garcia   │ 6:00 AM   │ 6:02 AM  │ ✓ Working           │
│ David Chen     │ 6:00 AM   │ 5:58 AM  │ ✓ Working           │
│ Sarah Johnson  │ 6:00 AM   │ -        │ ⚠️ Not clocked in    │
│ Mike Williams  │ 6:00 AM   │ 6:45 AM  │ ⚠️ Late (45 min)     │
└─────────────────────────────────────────────────────────────┘
```

### Approving Time-Off Requests

When team members request time off:

1. You receive a notification
2. Review the request:
   - Dates requested
   - Coverage impact
   - PTO balance
3. Approve or deny with reason

```
TIME OFF REQUEST
┌─────────────────────────────────────────────────────────────┐
│ Employee: John Smith                                         │
│ Dates: January 15-16, 2026 (2 days)                         │
│ Type: PTO                                                    │
│ Reason: Personal                                             │
│ PTO Balance: 80 hours available                             │
│                                                              │
│ Coverage Check: ✓ Adequate coverage available               │
│                                                              │
│ [Approve]  [Deny]  [Request More Info]                      │
└─────────────────────────────────────────────────────────────┘
```

### Overtime Management

Request overtime for your team:

1. Go to **Time → Request Overtime**
2. Enter:
   - Date
   - Employees
   - Hours needed
   - Reason (which job/why)
3. Submit for GM approval

---

## 10. Training & Development

### Training Matrix for Your Team

View required vs. actual training:

```
TRAINING MATRIX - Your Team
┌─────────────────────────────────────────────────────────────┐
│ Training        │ John │ Maria │ David │ Sarah │ Mike      │
├─────────────────┼──────┼───────┼───────┼───────┼───────────┤
│ Safety Orient.  │  ✓   │  ✓    │  ✓    │  ✓    │  ✓        │
│ Quality Basics  │  ✓   │  ✓    │  ✓    │  ⚠️    │  ✓        │
│ CNC Level 1     │  ✓   │  ⚠️    │  ✓    │  -    │  ✓        │
│ CNC Level 2     │  ✓   │  -    │  ✓    │  -    │  -        │
│ Lockout/Tagout  │  ✓   │  ✓    │  ✓    │  ✓    │  ⚠️        │
│ First Aid       │  ✓   │  -    │  ✓    │  -    │  -        │
└─────────────────────────────────────────────────────────────┘
✓ = Current | ⚠️ = Expiring Soon | - = Not Required/Trained
```

### Assigning Training

1. Go to team member's profile
2. Click **Assign Training**
3. Select course from catalog
4. Set due date
5. Employee receives notification

### Tracking Certifications

View certification status:

| Employee | Certification | Status | Expiry |
|----------|---------------|--------|--------|
| John Smith | Forklift | ✓ Current | Mar 2027 |
| David Chen | Crane | ⚠️ Expires Soon | Feb 2026 |
| Mike Williams | LOTO | ✓ Current | Aug 2026 |

### On-the-Job Training (OJT)

Log OJT for skill development:

1. Go to **Training → Log OJT**
2. Select trainee and trainer
3. Select skill
4. Log hours and assessment
5. Sign off when competent

---

## 11. Standard Work

### Accessing Work Instructions

Access: **Production → Standard Work** or from work order

Work instructions display:

```
┌─────────────────────────────────────────────────────────────┐
│  STANDARD WORK: Assembly - Model ABC                        │
│  Rev: 3.2 | Effective: Jan 5, 2026                          │
├─────────────────────────────────────────────────────────────┤
│  Step 1: Prepare Components                                  │
│  ┌─────────────┐                                             │
│  │  [Image]    │  • Gather parts A, B, C from kit           │
│  │             │  • Verify quantities match BOM             │
│  └─────────────┘  • Inspect for damage                      │
│                                                              │
│  ⚠️ Critical: Check for burrs on Part A                     │
│                                                              │
│  Step 2: Initial Assembly                                    │
│  ┌─────────────┐                                             │
│  │  [Video]    │  • Insert Part A into fixture              │
│  │   ▶ Play    │  • Torque to 25 N·m ± 2                    │
│  └─────────────┘  • Verify alignment with gauge             │
│                                                              │
│  [Previous]           [3 of 8]              [Next Step]     │
└─────────────────────────────────────────────────────────────┘
```

### Improvement Suggestions

Operators can suggest improvements to standard work:

1. On any work instruction, click **Suggest Improvement**
2. Describe the improvement
3. Add photos/markup if helpful
4. Submit for review

As supervisor, you review suggestions:

1. Go to **Standard Work → Suggestions**
2. Review each suggestion
3. Approve → Routes to engineering
4. Implement → Update immediately (minor changes)
5. Reject → With explanation

---

## 12. Safety Management

### Your Safety Responsibilities

- Ensure team works safely
- Conduct safety observations
- Report hazards immediately
- Investigate near-misses
- Verify PPE compliance

### Reporting Safety Issues

Access: **Safety → Report Hazard**

```
┌─────────────────────────────────────────────────────────────┐
│              REPORT SAFETY HAZARD                            │
├─────────────────────────────────────────────────────────────┤
│ Location:       [Cell 5 - Assembly     ▼]                   │
│ Hazard Type:    [Slip/Trip             ▼]                   │
│ Description:    [Oil leak on floor near machine        ]    │
│ Severity:       ○ Low  ● Medium  ○ High  ○ Critical         │
│ Immediate Action Taken:                                      │
│ [Placed warning cones, notified maintenance           ]     │
│ Photo:          [📷 Add Photo]                               │
│                                                              │
│                    [Submit]                                  │
└─────────────────────────────────────────────────────────────┘
```

### Safety Observations

Conduct regular safety observations:

1. Go to **Safety → Observation**
2. Select area/employee
3. Complete checklist:
   - PPE worn correctly?
   - Following safe procedures?
   - Housekeeping good?
   - Hazards present?
4. Log positive observations too!

### Near-Miss Reporting

Near-misses are learning opportunities:

1. Report in **Safety → Near Miss**
2. Encourage team to report without blame
3. Investigate root cause
4. Implement corrective action
5. Share lessons learned

---

## 13. Continuous Improvement

### Kaizen Suggestions

Encourage improvement ideas from team:

```
KAIZEN SUGGESTION
┌─────────────────────────────────────────────────────────────┐
│ From: Maria Garcia (Operator)                                │
│ Area: Assembly Cell 1                                        │
│ Date: January 11, 2026                                       │
├─────────────────────────────────────────────────────────────┤
│ Current State:                                               │
│ Tools stored in drawer - takes 15 seconds to retrieve        │
│                                                              │
│ Proposed Improvement:                                        │
│ Shadow board at workstation for commonly used tools          │
│                                                              │
│ Expected Benefit:                                            │
│ Save 5 minutes per shift, reduce ergonomic strain            │
├─────────────────────────────────────────────────────────────┤
│ Your Action:                                                 │
│ [Approve & Implement]  [Forward to Engineering]  [Reject]   │
└─────────────────────────────────────────────────────────────┘
```

### 5 Why Analysis

When problems occur, dig to root cause:

```
5 WHY ANALYSIS - Tool Breakage
┌─────────────────────────────────────────────────────────────┐
│ Problem: Tool broke during operation                         │
│                                                              │
│ 1. Why did the tool break?                                   │
│    → Excessive wear                                          │
│                                                              │
│ 2. Why was there excessive wear?                             │
│    → Tool wasn't changed on schedule                         │
│                                                              │
│ 3. Why wasn't it changed on schedule?                        │
│    → Operator didn't know tool life count                    │
│                                                              │
│ 4. Why didn't operator know?                                 │
│    → Tool counter not visible on machine                     │
│                                                              │
│ 5. Why isn't counter visible?                                │
│    → Screen layout doesn't prioritize it                     │
│                                                              │
│ Root Cause: Tool life counter not prominently displayed      │
│ Countermeasure: Move counter to main screen, add alert       │
└─────────────────────────────────────────────────────────────┘
```

### Participating in A3 Problem Solving

You may be asked to participate in A3s:

1. Provide frontline perspective
2. Contribute to root cause analysis
3. Test countermeasures
4. Provide feedback on effectiveness

---

## 14. Mobile Tools

### Sensei Mobile for Supervisors

Download the mobile app for on-the-floor use:

**Key features**:
- View team status
- Respond to Andons
- Complete Gemba walks
- Take and attach photos
- Log issues quickly
- Approve time-off

### Gemba Walk Mode

Structured floor walks:

1. Open app → **Gemba Walk**
2. Select route (or free-form)
3. At each station:
   - View metrics
   - Log observations
   - Take photos
   - Create action items
4. Complete walk summary

### Quick Actions from Mobile

| Action | How |
|--------|-----|
| Respond to Andon | Notification → Tap → Respond |
| Log Quality Issue | + → Quality → NC |
| Take Photo | 📷 → Attach to record |
| Message Team | → Team → Message |
| Check Schedule | Home → Production |

---

## 15. Escalation & Communication

### When to Escalate

| Situation | Escalate To | Method |
|-----------|-------------|--------|
| Safety incident | GM + Safety | Phone immediately |
| Customer-impacting quality | GM + Quality | Sensei + Phone |
| Major equipment breakdown | GM + Maintenance | Sensei + Radio |
| Staffing crisis | GM + HR | Sensei |
| Schedule cannot be met | GM | Sensei before end of shift |

### How to Escalate in Sensei

1. From any issue, click **Escalate**
2. Select escalation reason
3. Add context
4. Submit
5. System notifies appropriate people

### Communication Tools

| Tool | Use For |
|------|---------|
| Sensei Messages | Non-urgent, documented |
| @Mentions | Get someone's attention |
| Announcements | Shift-wide communications |
| Email | External or formal |
| Radio | Immediate floor communication |
| Phone | Emergencies |

### Daily Huddles

Use Sensei to run your daily huddle:

1. Open **Huddle** from dashboard
2. Review auto-generated agenda:
   - Yesterday's results
   - Today's priorities
   - Open issues
   - Safety moment
3. Log discussion notes
4. Assign action items

---

## Quick Reference Card

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + D` | Dashboard |
| `Ctrl + W` | Work Orders |
| `Ctrl + T` | My Team |
| `Ctrl + Q` | Log NC |
| `Ctrl + /` | Search/Commands |
| `F5` | Refresh |

### Daily Supervisor Checklist

```
Start of Shift:
□ Review handover notes
□ Check attendance
□ Review schedule
□ Assign operators
□ Brief team

Throughout Shift:
□ Hourly floor walks
□ Respond to Andons < 5 min
□ Monitor production progress
□ Quality verification
□ Coach and develop

End of Shift:
□ Production summary
□ Log issues/concerns
□ Complete handover
□ Recognize good work
```

### Emergency Contacts

| Emergency | Contact | Number |
|-----------|---------|--------|
| Medical | First Aid | ext. 5555 |
| Fire | Fire Warden | ext. 5911 |
| Equipment | Maintenance | Radio Ch. 3 |
| Security | Security | ext. 5000 |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Operations*
