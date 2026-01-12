# Team Lead Starter Guide

## Sensei OS - Team Lead Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Team Lead Dashboard](#3-team-lead-dashboard)
4. [Team Management](#4-team-management)
5. [Daily Operations](#5-daily-operations)
6. [Work Assignment](#6-work-assignment)
7. [Performance Tracking](#7-performance-tracking)
8. [Quality Coordination](#8-quality-coordination)
9. [Training & Development](#9-training--development)
10. [Communication](#10-communication)
11. [Problem Solving](#11-problem-solving)
12. [Continuous Improvement](#12-continuous-improvement)
13. [Safety Leadership](#13-safety-leadership)
14. [Shift Handoffs](#14-shift-handoffs)
15. [Quick Reference](#15-quick-reference)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use stories/subtasks to coordinate day-to-day work and track completion.
- Use comments to document blockers, decisions, and handoffs across shifts.
- Use wiki pages for team runbooks, checklists, and “how we do it” documentation.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role as Team Lead

As a Team Lead, you are the **first line of leadership** on the production floor. You bridge the gap between operators and supervisors, ensuring your team succeeds. Your key responsibilities:

- **Lead your team** by example and support
- **Assign and monitor work** for your cell/area
- **Train and develop** team members
- **Ensure quality** at the source
- **Solve problems** quickly and effectively
- **Communicate** up, down, and across

### Team Lead Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Team Members | View + Lead | See team, assign tasks |
| Production | Full Cell | Track and report cell output |
| Quality | Record + Flag | Log quality, escalate issues |
| Time/Attendance | View Team | Monitor attendance, basic time |
| Training | View + Track | Monitor team certifications |
| Andon | Respond + Escalate | First responder for issues |
| Improvement | Submit + Lead | Drive Kaizen in your area |

### Leadership Philosophy

```
TEAM LEAD IMPACT

         YOU
          │
          ▼
    ┌───────────┐
    │ TEAM LEAD │
    └─────┬─────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌───────┐   ┌───────┐
│SUPPORT│   │ LEAD  │
│ Team  │   │ Work  │
└───────┘   └───────┘
    │           │
    └─────┬─────┘
          ▼
    ┌───────────┐
    │  RESULTS  │
    │ Quality   │
    │ Safety    │
    │ Delivery  │
    │ Morale    │
    └───────────┘
```

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter your credentials
3. Complete MFA if required
4. Review your team dashboard

### Initial Setup Tasks

- [ ] Verify your team members are assigned
- [ ] Review your cell/area work orders
- [ ] Check team training status
- [ ] Set notification preferences
- [ ] Configure mobile access
- [ ] Review escalation procedures

### Your Team Lead Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│               TEAM LEAD DASHBOARD                            │
│               Cell 3 - Assembly                              │
│               January 11, 2026 - 10:15 AM                   │
├─────────────────────────────────────────────────────────────┤
│  TODAY'S STATUS                                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │ Team       │ │ Output     │ │ Quality    │ │ Safety     ││
│  │  5/5 ✓     │ │  145/180   │ │  99.2%     │ │  0 issues  ││
│  │ present    │ │  81% pace  │ │            │ │            ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘│
├─────────────────────────────────────────────────────────────┤
│  CURRENT WORK ORDER                                          │
│  WO-2026-1234: Assembly A - Widget Final                    │
│  Progress: ████████████░░░░░░ 145/180 (81%)                 │
│  Target: Complete by 2:00 PM                                │
│                                                              │
│  TEAM                          ALERTS                        │
│  ├─ Maria G. - Station 1 ✓    ├─ ⚠️ Pace behind target      │
│  ├─ John S. - Station 2 ✓     └─ Parts delivery: 11 AM     │
│  ├─ David B. - Station 3 ✓                                  │
│  ├─ Sarah W. - Station 4 ✓                                  │
│  └─ Mike T. - Station 5 ✓                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Team Lead Dashboard

### Dashboard Widgets

#### Team Status
Real-time view of your team:

```
TEAM STATUS - Cell 3
┌─────────────────────────────────────────────────────────────┐
│ Member     │ Station │ Status   │ Current Task │ Output    │
├────────────┼─────────┼──────────┼──────────────┼───────────┤
│ Maria G.   │ Stn 1   │ ✓ Working│ Assembly-A   │ 32/36     │
│ John S.    │ Stn 2   │ ✓ Working│ Assembly-A   │ 30/36     │
│ David B.   │ Stn 3   │ ⏸ Break  │ -            │ 28/36     │
│ Sarah W.   │ Stn 4   │ ✓ Working│ Assembly-A   │ 29/36     │
│ Mike T.    │ Stn 5   │ ✓ Working│ Assembly-A   │ 26/36     │
└────────────┴─────────┴──────────┴──────────────┴───────────┘
```

#### Production Pace

```
PRODUCTION PACE
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Target: 180 units by 2:00 PM                                │
│ Current: 145 units at 10:15 AM                              │
│                                                              │
│ Pace Analysis:                                               │
│ ├─ Expected at this time: 162 units                         │
│ ├─ Actual: 145 units                                        │
│ ├─ Gap: -17 units (10% behind)                              │
│ └─ Projected finish: 2:35 PM (35 min late)                  │
│                                                              │
│ PACE TREND                                                   │
│ 8AM ─── 9AM ─── 10AM ─── 11AM ─── 12PM ─── 1PM ─── 2PM     │
│  ▓▓▓▓▓   ▓▓▓▓    ▓▓▓░                                       │
│  Target  ████    ███░     (Actual vs Target)                │
│                                                              │
│ ⚠️ Action Needed: Increase pace by 2 units/hour             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Quality Summary

```
QUALITY TODAY - Cell 3
┌─────────────────────────────────────────────────────────────┐
│ Units Produced: 145                                          │
│ Passed First Time: 144 (99.3%)                              │
│ Defects Found: 1                                             │
│                                                              │
│ Defect Details:                                              │
│ └─ 1x Assembly error - Wrong component (Station 5)          │
│                                                              │
│ Trend: ████████████████████ 99.3% (Target: 98%)             │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Team Management

### Your Team

Access: **Team → My Team**

```
MY TEAM - Cell 3 Assembly
┌─────────────────────────────────────────────────────────────┐
│ Member      │ Role       │ Seniority│ Certifications       │
├─────────────┼────────────┼──────────┼──────────────────────┤
│ Maria G.    │ Sr Operator│ 5 years  │ Assembly, Solder, QC │
│ John S.     │ Operator   │ 3 years  │ Assembly, Solder     │
│ David B.    │ Operator   │ 2 years  │ Assembly             │
│ Sarah W.    │ Operator   │ 1 year   │ Assembly, Training   │
│ Mike T.     │ Operator   │ 6 months │ Assembly (basic)     │
└─────────────┴────────────┴──────────┴──────────────────────┘
```

### Team Skills Matrix

```
SKILLS MATRIX - Cell 3
┌─────────────────────────────────────────────────────────────┐
│ Member    │Assembly│Solder│QC  │Test│Pack│Train│           │
├───────────┼────────┼──────┼────┼────┼────┼─────┤           │
│ Maria G.  │  ████  │ ███  │████│ ██ │ ██ │ ███ │ Can Train │
│ John S.   │  ███   │ ███  │ ██ │ ██ │ █  │ ██  │           │
│ David B.  │  ███   │ ██   │ █  │ █  │ █  │ █   │           │
│ Sarah W.  │  ██    │ █    │ █  │ ██ │ ██ │ █   │ Training  │
│ Mike T.   │  █     │ -    │ -  │ █  │ █  │ -   │ New       │
└───────────┴────────┴──────┴────┴────┴────┴─────┴───────────┘
Legend: ████ Expert  ███ Proficient  ██ Capable  █ Basic  - None
```

### One-on-One Notes

Track individual discussions:

```
┌─────────────────────────────────────────────────────────────┐
│  TEAM MEMBER: Mike T.                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ RECENT NOTES                                                 │
│ ├─ Jan 10: Discussed quality miss. Reviewed procedure.      │
│ │          Will shadow Maria tomorrow.                       │
│ ├─ Jan 5: 90-day review. Good progress on assembly.        │
│ │         Next: Start solder training.                      │
│ └─ Dec 20: Welcomed to team. Paired with John for training. │
│                                                              │
│ GOALS                                                        │
│ ├─ Complete solder certification by Feb 28                  │
│ └─ Achieve 98% first-pass quality by Feb 15                 │
│                                                              │
│ [Add Note]                                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Daily Operations

### Shift Start Routine

```
SHIFT START CHECKLIST
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ BEFORE TEAM ARRIVES (15 min early)                          │
│ □ Review overnight notes/issues                             │
│ □ Check today's work orders and targets                     │
│ □ Verify materials are staged                               │
│ □ Check equipment status                                    │
│ □ Prepare shift briefing topics                             │
│                                                              │
│ TEAM ARRIVAL                                                 │
│ □ Verify attendance (all present or covered)                │
│ □ Conduct shift briefing                                    │
│ □ Assign stations and work                                  │
│ □ Address questions                                         │
│ □ Start production                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Shift Briefing Template

```
SHIFT BRIEFING AGENDA (5-10 minutes)
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ 1. SAFETY (1 min)                                           │
│    - Any safety reminders or concerns                       │
│                                                              │
│ 2. YESTERDAY'S RESULTS (1 min)                              │
│    - Output: How did we do?                                 │
│    - Quality: Any issues to learn from?                     │
│                                                              │
│ 3. TODAY'S PLAN (2 min)                                     │
│    - Work orders and targets                                │
│    - Station assignments                                    │
│    - Any changes or special items                           │
│                                                              │
│ 4. UPDATES (1 min)                                          │
│    - Company/department news                                │
│    - Training, visitors, etc.                               │
│                                                              │
│ 5. QUESTIONS (1-2 min)                                      │
│    - Open floor for questions                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### During Shift

Key activities throughout the day:

| Time | Activity |
|------|----------|
| Continuous | Walk the cell, observe, assist |
| Hourly | Check pace, update board |
| As needed | Respond to Andons |
| As needed | Quality checks |
| Break times | Cover stations, check supplies |
| End of shift | Wrap-up, handoff |

### Shift End Routine

```
SHIFT END CHECKLIST
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ 30 MINUTES BEFORE END                                        │
│ □ Check final production count                              │
│ □ Note any carryover work                                   │
│ □ Document any issues                                       │
│ □ Begin cleanup                                             │
│                                                              │
│ SHIFT END                                                    │
│ □ Complete production reporting                             │
│ □ Quality summary entered                                   │
│ □ Write handoff notes                                       │
│ □ Conduct handoff with next lead                            │
│ □ Ensure team clocks out                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Work Assignment

### Assigning Stations

Balance skills and development:

```
STATION ASSIGNMENT - Cell 3
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Today's Work: WO-2026-1234 (Widget Final Assembly)          │
│                                                              │
│ STATION ASSIGNMENTS                                          │
│                                                              │
│ Station 1 - Sub-Assembly A (Complex)                         │
│ └─ Assigned: Maria G. (most experienced)                    │
│                                                              │
│ Station 2 - Sub-Assembly B                                   │
│ └─ Assigned: John S.                                        │
│                                                              │
│ Station 3 - Main Assembly                                    │
│ └─ Assigned: David B.                                       │
│                                                              │
│ Station 4 - Final Test                                       │
│ └─ Assigned: Sarah W. (good test skills)                    │
│                                                              │
│ Station 5 - Pack & Label                                     │
│ └─ Assigned: Mike T. (developing; simpler task)             │
│                                                              │
│ [Save Assignments]                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Assignment Considerations

| Factor | What to Consider |
|--------|------------------|
| Skills | Match skill to task complexity |
| Development | Stretch assignments for growth |
| Balance | Fair rotation over time |
| Special needs | Accommodations, preferences |
| Coverage | Cross-train for flexibility |

### Covering Absences

When team member is out:

1. Check who can cover the station
2. Review skills matrix
3. Adjust assignments
4. Communicate changes
5. Monitor closely if less experienced

---

## 7. Performance Tracking

### Individual Performance

Track each team member:

```
INDIVIDUAL PERFORMANCE - January 2026
┌─────────────────────────────────────────────────────────────┐
│ Member    │ Output Eff│ Quality │ Attendance│ Safety │ Trend│
├───────────┼───────────┼─────────┼───────────┼────────┼──────┤
│ Maria G.  │ 105%      │ 99.5%   │ 100%      │ ✓      │ ▲    │
│ John S.   │ 100%      │ 98.8%   │ 100%      │ ✓      │ ─    │
│ David B.  │ 98%       │ 99.0%   │ 95%       │ ✓      │ ─    │
│ Sarah W.  │ 95%       │ 99.2%   │ 100%      │ ✓      │ ▲    │
│ Mike T.   │ 85%       │ 97.5%   │ 100%      │ ✓      │ ▲    │
└───────────┴───────────┴─────────┴───────────┴────────┴──────┘
```

### Team Performance

Cell-level metrics:

```
TEAM PERFORMANCE - Cell 3
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ JANUARY MTD                                                  │
│ ├─ Output: 1,250 / 1,400 target (89%)                       │
│ ├─ Quality: 99.1% first-pass (Target: 98%)                  │
│ ├─ Attendance: 97% (Target: 95%)                            │
│ └─ Safety: 0 incidents (Target: 0)                          │
│                                                              │
│ TREND (Last 6 Months)                                        │
│ ┌────────────────────────────────────────────┐              │
│ │      │ Aug  Sep  Oct  Nov  Dec  Jan        │              │
│ │ 100% │      ▬▬▬  ▬▬▬  ▬▬▬  ▬▬▬  ▬▬▬        │              │
│ │  95% │ ▬▬▬                                  │ Output      │
│ │  90% │                       ▬▬▬            │              │
│ └────────────────────────────────────────────┘              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Giving Feedback

Effective feedback approach:

```
FEEDBACK MODEL

POSITIVE FEEDBACK                CORRECTIVE FEEDBACK
1. Specific action               1. Private setting
2. Impact/result                 2. Specific behavior
3. Recognition                   3. Impact/standard
4. Encouragement                 4. Expected behavior
                                 5. Support/follow-up
                                 6. Confirm understanding

Example:                         Example:
"Maria, great catch on that      "Mike, I noticed the component
quality issue. You prevented     was reversed on unit 42. The
defects from reaching the        standard requires the notch to
customer. Keep up the            face left. Let's review the
excellent attention to detail!"  work instruction together."
```

---

## 8. Quality Coordination

### Quality at the Source

Your role in quality:

```
TEAM LEAD QUALITY RESPONSIBILITIES
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ PREVENT                                                      │
│ ├─ Ensure work instructions are followed                    │
│ ├─ Verify setups before production                          │
│ ├─ Monitor process parameters                               │
│ └─ Coach on proper techniques                               │
│                                                              │
│ DETECT                                                       │
│ ├─ Conduct process checks                                   │
│ ├─ Review team's quality inspections                        │
│ ├─ Investigate defects found                                │
│ └─ Identify patterns                                        │
│                                                              │
│ RESPOND                                                      │
│ ├─ Stop production if quality at risk                       │
│ ├─ Escalate issues to supervisor/quality                    │
│ ├─ Implement immediate countermeasures                      │
│ └─ Document and communicate                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Quality Checks

Perform regular quality walks:

```
QUALITY CHECK - Cell 3
┌─────────────────────────────────────────────────────────────┐
│ Check Time: 10:00 AM                                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ WORKSTATION CHECKS                                           │
│ Station 1 (Maria):                                           │
│   ☑ Work instruction displayed and current                  │
│   ☑ Proper tools in use                                     │
│   ☑ Sample inspected - passes                               │
│                                                              │
│ Station 2 (John):                                            │
│   ☑ Work instruction displayed and current                  │
│   ☑ Proper tools in use                                     │
│   ☑ Sample inspected - passes                               │
│                                                              │
│ ... (continue for all stations)                             │
│                                                              │
│ OVERALL: All checks pass ✓                                  │
│                                                              │
│ [Save Check]                                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### When Quality Issues Occur

Response steps:

1. **Stop** - Prevent more defects
2. **Contain** - Segregate suspect product
3. **Investigate** - Find root cause
4. **Fix** - Implement countermeasure
5. **Verify** - Confirm fix works
6. **Document** - Record for learning

---

## 9. Training & Development

### Team Training Status

```
TRAINING STATUS - Cell 3
┌─────────────────────────────────────────────────────────────┐
│ Member    │ Required Training        │ Status    │ Due Date │
├───────────┼──────────────────────────┼───────────┼──────────┤
│ Maria G.  │ All current              │ ✓ Complete│ -        │
│ John S.   │ ESD Handling Refresher   │ Due Soon  │ Jan 31   │
│ David B.  │ All current              │ ✓ Complete│ -        │
│ Sarah W.  │ QC Inspector Level 1     │ In Progress│ Feb 15  │
│ Mike T.   │ Solder Training          │ Scheduled │ Jan 20   │
│ Mike T.   │ Safety Annual            │ Due       │ Jan 15   │
└───────────┴──────────────────────────┴───────────┴──────────┘
```

### On-the-Job Training

Conduct OJT for your team:

```
OJT PROCESS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ 1. TELL                                                      │
│    Explain the task and its importance                      │
│                                                              │
│ 2. SHOW                                                      │
│    Demonstrate the correct method                           │
│                                                              │
│ 3. DO                                                        │
│    Have them perform with guidance                          │
│                                                              │
│ 4. CHECK                                                     │
│    Verify understanding and competence                      │
│                                                              │
│ 5. FOLLOW UP                                                 │
│    Monitor and provide feedback                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Development Planning

Help team members grow:

```
DEVELOPMENT PLAN - Sarah W.
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ CURRENT LEVEL: Operator (1 year)                            │
│ GOAL: Senior Operator / Future Team Lead                    │
│                                                              │
│ DEVELOPMENT AREAS                                            │
│ ├─ Technical: Complete QC certification                     │
│ ├─ Technical: Cross-train on solder                         │
│ ├─ Leadership: Mentor new operators                         │
│ └─ Leadership: Lead cell in team lead's absence             │
│                                                              │
│ ACTIONS                                                      │
│ ├─ Q1: Complete QC Level 1 training                         │
│ ├─ Q2: Shadow Maria on solder operations                    │
│ ├─ Q3: Assign as mentor for new hire                        │
│ └─ Q4: Cover as team lead during vacation                   │
│                                                              │
│ CHECK-INS: Monthly                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 10. Communication

### Communication Channels

```
COMMUNICATION MATRIX
┌─────────────────────────────────────────────────────────────┐
│ Topic              │ Method          │ Frequency            │
├────────────────────┼─────────────────┼──────────────────────┤
│ Daily targets      │ Shift briefing  │ Start of shift       │
│ Urgent issues      │ Face-to-face    │ Immediately          │
│ Status updates     │ Huddle board    │ Hourly               │
│ Problem solving    │ Team discussion │ As needed            │
│ Policy updates     │ Team meeting    │ Weekly               │
│ Individual feedback│ 1-on-1          │ Weekly/as needed     │
│ Escalations        │ To supervisor   │ As needed            │
└────────────────────┴─────────────────┴──────────────────────┘
```

### The Huddle Board

Your cell's communication center:

```
CELL 3 HUDDLE BOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SAFETY          QUALITY         DELIVERY        COST        │
│ ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│ │ 45 days │    │ 99.1%   │    │ 89%     │    │ On       │   │
│ │ no      │    │ FPY     │    │ to plan │    │ target   │   │
│ │ injury  │    │         │    │         │    │          │   │
│ └─────────┘    └─────────┘    └─────────┘    └─────────┘   │
│                                                              │
│ TODAY'S TARGET          CURRENT OUTPUT                       │
│ ┌─────────────┐        ┌─────────────┐                      │
│ │    180      │        │    145      │                      │
│ │   units     │        │   units     │                      │
│ └─────────────┘        └─────────────┘                      │
│                                                              │
│ TOP ISSUES              IMPROVEMENTS                         │
│ 1. Pace behind         ✓ New fixture (Dec)                  │
│ 2. -                   ✓ 5S completed                       │
│                        ○ Lighting upgrade                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Escalating Issues

When to escalate to supervisor:

| Escalate | Examples |
|----------|----------|
| Safety | Any injury, near miss, hazard |
| Quality | Major defects, customer complaints |
| Equipment | Breakdown affecting production |
| People | Conflicts, attendance issues |
| Delivery | Will miss customer date |

---

## 11. Problem Solving

### Andon Response

When operator triggers Andon:

```
ANDON RESPONSE PROCESS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ 1. RESPOND QUICKLY (< 2 min)                                │
│    Go to the station immediately                            │
│                                                              │
│ 2. ASSESS                                                    │
│    - What's the issue?                                      │
│    - Can we fix it quickly?                                 │
│    - Is quality at risk?                                    │
│                                                              │
│ 3. ACT                                                       │
│    If fixable: Resolve and restart                          │
│    If not: Escalate to maintenance/supervisor               │
│                                                              │
│ 4. DOCUMENT                                                  │
│    Log the issue and resolution                             │
│                                                              │
│ 5. FOLLOW UP                                                 │
│    Is this a recurring issue?                               │
│    Do we need a permanent fix?                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Quick Problem Solving

5-Why technique:

```
5-WHY EXAMPLE
┌─────────────────────────────────────────────────────────────┐
│ Problem: Wrong component installed                           │
│                                                              │
│ Why 1: Operator didn't notice it was wrong                  │
│   Why 2: Components look similar                            │
│     Why 3: Parts not clearly labeled                        │
│       Why 4: Label came off                                 │
│         Why 5: Labels don't stick to this material          │
│                                                              │
│ Root Cause: Label adhesive not suitable for part material   │
│                                                              │
│ Countermeasure: Use labels with industrial adhesive         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Common Issue Quick Fixes

| Issue | Quick Response |
|-------|----------------|
| Missing parts | Check stock, expedite, notify planning |
| Equipment minor | Basic troubleshoot, call maintenance |
| Quality defect | Stop, contain, investigate |
| Operator error | Coach, verify understanding |
| Tooling worn | Replace, check frequency |

---

## 12. Continuous Improvement

### Leading Improvement

Your role in Kaizen:

```
TEAM LEAD IMPROVEMENT ROLE
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ ENCOURAGE                                                    │
│ ├─ Ask team for ideas                                       │
│ ├─ Listen actively                                          │
│ ├─ Recognize suggestions                                    │
│ └─ Create safe environment for input                        │
│                                                              │
│ LEAD                                                         │
│ ├─ Lead small improvements in your area                     │
│ ├─ Participate in Kaizen events                             │
│ ├─ Test ideas with team                                     │
│ └─ Measure results                                          │
│                                                              │
│ SUSTAIN                                                      │
│ ├─ Ensure changes stick                                     │
│ ├─ Update work instructions                                 │
│ └─ Train team on new methods                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Capturing Suggestions

When team has ideas:

```
┌─────────────────────────────────────────────────────────────┐
│  NEW IMPROVEMENT SUGGESTION                                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Submitted By: David B. (Operator)                           │
│ Logged By: You (Team Lead)                                  │
│ Area: Cell 3 Assembly                                        │
│                                                              │
│ Current Situation:                                           │
│ [Tools scattered across workstation, time wasted           ]│
│ [looking for right tool.                                   ]│
│                                                              │
│ Suggested Improvement:                                       │
│ [Create shadow board with outline for each tool at         ]│
│ [each station. Tools always in same place.                 ]│
│                                                              │
│ Expected Benefit:                                            │
│ [Save 2-3 minutes per setup. Reduce frustration.           ]│
│                                                              │
│ [Submit for Review]                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5S in Your Area

Lead 5S activities:

```
5S CHECKLIST - Cell 3
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SORT (Seiri)                                                 │
│ □ Remove unneeded items from work area                      │
│ □ Red tag questionable items                                │
│                                                              │
│ SET IN ORDER (Seiton)                                        │
│ □ Designated place for everything                           │
│ □ Labels and visual markers                                 │
│                                                              │
│ SHINE (Seiso)                                                │
│ □ Clean work area daily                                     │
│ □ Equipment cleaned and inspected                           │
│                                                              │
│ STANDARDIZE (Seiketsu)                                       │
│ □ Cleaning schedule posted                                  │
│ □ Standard work updated                                     │
│                                                              │
│ SUSTAIN (Shitsuke)                                           │
│ □ Regular audits                                            │
│ □ Team engagement                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Safety Leadership

### Safety Responsibilities

Your safety role:

```
TEAM LEAD SAFETY RESPONSIBILITIES
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ DAILY                                                        │
│ ├─ Safety moment in shift briefing                          │
│ ├─ Ensure PPE compliance                                    │
│ ├─ Watch for unsafe acts                                    │
│ └─ Address hazards immediately                              │
│                                                              │
│ WHEN ISSUES OCCUR                                            │
│ ├─ Report all incidents immediately                         │
│ ├─ Investigate near misses                                  │
│ ├─ Participate in incident reviews                          │
│ └─ Implement corrective actions                             │
│                                                              │
│ ONGOING                                                      │
│ ├─ Conduct safety observations                              │
│ ├─ Encourage reporting                                      │
│ └─ Model safe behavior                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Safety Observation

```
SAFETY OBSERVATION - Cell 3
┌─────────────────────────────────────────────────────────────┐
│ Date: Jan 11, 2026   Time: 9:30 AM   Observer: You          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ SAFE BEHAVIORS OBSERVED                                      │
│ ☑ All wearing required PPE                                  │
│ ☑ Proper lifting techniques                                 │
│ ☑ Workstations organized                                    │
│ ☑ Aisles clear                                              │
│                                                              │
│ AT-RISK BEHAVIORS                                            │
│ ☐ None observed                                             │
│                                                              │
│ HAZARDS IDENTIFIED                                           │
│ ☑ Cord across walkway at Station 3 - Corrected             │
│                                                              │
│ FEEDBACK PROVIDED                                            │
│ Thanked team for PPE compliance. Discussed cord hazard.    │
│                                                              │
│ [Save Observation]                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 14. Shift Handoffs

### Handoff Process

```
SHIFT HANDOFF CHECKLIST
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ OUTGOING LEAD PREPARES                                       │
│ □ Production status documented                              │
│ □ Quality issues noted                                      │
│ □ Equipment status                                          │
│ □ People issues (absences, concerns)                        │
│ □ Pending items for next shift                              │
│                                                              │
│ HANDOFF MEETING (5-10 min)                                   │
│ □ Walk the area together                                    │
│ □ Review status and issues                                  │
│ □ Discuss priorities                                        │
│ □ Answer questions                                          │
│                                                              │
│ INCOMING LEAD CONFIRMS                                       │
│ □ Understand current status                                 │
│ □ Clear on priorities                                       │
│ □ Aware of any issues                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Handoff Notes

Document for next shift:

```
┌─────────────────────────────────────────────────────────────┐
│  SHIFT HANDOFF NOTES                                         │
│  Cell 3 - Day Shift → Swing Shift                           │
│  Jan 11, 2026 2:00 PM                                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ PRODUCTION                                                   │
│ WO-2026-1234: Completed 180/180 units ✓                     │
│ WO-2026-1235: Started, 25 units complete                    │
│               Remaining: 150 units (priority)               │
│                                                              │
│ QUALITY                                                      │
│ No issues. 99.4% FPY today.                                 │
│                                                              │
│ EQUIPMENT                                                    │
│ All running. Station 2 fixture a bit sticky - works        │
│ but maintenance should check when available.                │
│                                                              │
│ PEOPLE                                                       │
│ All present. Mike doing well on pack station.               │
│                                                              │
│ MATERIALS                                                    │
│ Parts staged for WO-1235. Next delivery at 4 PM.           │
│                                                              │
│ FOLLOW-UP ITEMS                                              │
│ - Call maintenance re: Station 2 fixture                    │
│ - Supervisor wants pace update at 5 PM                      │
│                                                              │
│ Prepared by: [Your Name]                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 15. Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + T` | Team dashboard |
| `Ctrl + P` | Production status |
| `Ctrl + A` | Andon queue |
| `Ctrl + /` | Quick search |
| `F5` | Refresh |

### Daily Checklist

```
TEAM LEAD DAILY CHECKLIST

SHIFT START (15 min before)
□ Check overnight notes
□ Review work orders and targets
□ Verify materials and equipment
□ Prepare briefing

SHIFT START
□ Verify attendance
□ Conduct shift briefing
□ Assign stations
□ Start production

DURING SHIFT
□ Hourly pace check
□ Quality walkthrough
□ Respond to issues
□ Support team

SHIFT END
□ Final count and reporting
□ Document issues
□ Write handoff notes
□ Brief next lead
```

### Key Metrics to Track

| Metric | Target | How to Improve |
|--------|--------|----------------|
| Output % | 95%+ | Reduce stops, balance work |
| Quality % | 98%+ | Prevent defects, verify work |
| Attendance | 95%+ | Engagement, address issues |
| Safety | 0 incidents | Observations, correct hazards |

### Escalation Guide

| Issue | First Response | Escalate If |
|-------|---------------|--------------|
| Equipment | Basic troubleshoot | Not fixed in 5 min |
| Quality | Contain, investigate | Systematic or major |
| Attendance | Cover station | Pattern or conflict |
| Safety | Stop work, report | Any injury |
| Materials | Check stock, expedite | Will stop line |

### Emergency Contacts

| Emergency | Contact |
|-----------|---------|
| Supervisor | ext. 5100 |
| Maintenance | ext. 5200 |
| Quality | ext. 5300 |
| Safety | ext. 5555 |
| HR | ext. 3000 |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Operations*
