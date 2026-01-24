# General Manager (GM) Starter Guide

## Sensei OS - General Manager Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Day 1 Onboarding](#2-day-1-onboarding)
3. [Your GM Dashboard](#3-your-gm-dashboard)
4. [Daily Operations Management](#4-daily-operations-management)
5. [SQDCP & Obeya](#5-sqdcp--obeya)
6. [Production Management](#6-production-management)
7. [Quality Oversight](#7-quality-oversight)
8. [Team Management](#8-team-management)
9. [Sales & Quoting](#9-sales--quoting)
10. [Inventory & Warehouse](#10-inventory--warehouse)
11. [Approvals & Escalations](#11-approvals--escalations)
12. [Exception Management](#12-exception-management)
13. [Reports & Analytics](#13-reports--analytics)
14. [AI Tools for GM](#14-ai-tools-for-gm)
15. [Mobile Access](#15-mobile-access)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use sprints to set delivery cadence and keep cross-team commitments visible.
- Use stories/subtasks for execution; use issues for defects, NCR-style follow-ups, and recurring problems.
- Keep milestones aligned to customer dates and internal phase gates.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role as General Manager

As GM, you are the **tactical commander** of factory operations. Sensei OS gives you:

- **Complete factory visibility** across all departments
- **Real-time operational data** from the shop floor
- **Exception-based alerts** when issues need attention
- **Decision support tools** for resource allocation
- **Team performance insights** for coaching opportunities

### GM Capabilities Matrix

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Production Dashboard | Full | Real-time shop floor visibility |
| Quality Systems | Full | NC, CAPA, inspections |
| Warehouse | Full | Inventory, receiving, shipping |
| Sales Pipeline | View + Approve | Quote approval authority |
| HR Data | View | Team rosters, training status |
| Financial Data | Operational | Costing, budgets (not GL) |
| Approvals | Extended | Quotes, POs, schedules |
| Personnel | Supervisors | Manage supervisors and below |

### GM vs Other Roles

| Function | CEO | **GM** | Supervisor |
|----------|-----|--------|------------|
| Strategic Planning | ✓ | Contribute | View |
| Factory Operations | Overview | **Full Control** | Team Only |
| Quote Approval | >$100K | **$10K-$100K** | None |
| Hiring | Approve | **Recommend** | Request |
| Capital Expenditure | Approve | **Recommend** | None |
| Discipline | Final | **Action** | Document |

---

## 2. Day 1 Onboarding

### Your Guided Onboarding Journey

When you first log in, Sensei OS provides a structured onboarding experience:

```
┌─────────────────────────────────────────────────────────────┐
│                GM ONBOARDING PROGRESS                        │
│  ████████░░░░░░░░░░░░░░░░░░░░░░░░░  25% Complete            │
├─────────────────────────────────────────────────────────────┤
│  ✓ Welcome & Profile Setup                                  │
│  ✓ Team Introduction                                        │
│  → Dashboard Tour (Current Step)                            │
│  ○ Key Metrics Overview                                     │
│  ○ Workflow Walkthrough                                     │
│  ○ First Actions                                            │
│  ○ Completion & Certification                               │
└─────────────────────────────────────────────────────────────┘
```

### Day 1 Checklist

#### Hour 1: Account Setup
- [ ] Log in with provided credentials
- [ ] Set up MFA (Multi-Factor Authentication)
- [ ] Complete profile (photo, contact info)
- [ ] Set notification preferences
- [ ] Review organization chart

#### Hour 2: Dashboard Tour
- [ ] Complete guided dashboard tour
- [ ] Customize widget layout
- [ ] Set up favorite reports
- [ ] Configure alert thresholds

#### Hour 3: Meet Your Teams
- [ ] Review direct reports
- [ ] Check training matrix
- [ ] Review open issues by department
- [ ] Introduction to supervisors

#### Hour 4: First Actions
- [ ] Review pending approvals
- [ ] Check today's production schedule
- [ ] Review open quality issues
- [ ] Walk the floor (with Sensei mobile app)

### Key Contacts During Onboarding

| Contact | Role | For |
|---------|------|-----|
| IT Help Desk | Tech Support | Login issues, access problems |
| HR Business Partner | HR | People questions |
| Previous GM | Transition | Handover items |
| CEO | Executive | Strategic questions |

---

## 3. Your GM Dashboard

### Default GM Dashboard Layout

```
┌─────────────────────────────────────────────────────────────┐
│                   GM COMMAND CENTER                          │
├─────────────────────────────────────────────────────────────┤
│  SQDCP STATUS                    │  PRODUCTION SCHEDULE     │
│  ┌─────┬─────┬─────┬─────┬─────┐ │  Today: 12/15 jobs ✓     │
│  │  S  │  Q  │  D  │  C  │  P  │ │  At Risk: 2 jobs ⚠️       │
│  │  🟢 │  🟢 │  🟡 │  🟢 │  🟢 │ │  Behind: 1 job 🔴         │
│  └─────┴─────┴─────┴─────┴─────┘ │                          │
├─────────────────────────────────────────────────────────────┤
│  EXCEPTIONS (7)                  │  APPROVALS (4)           │
│  🔴 Andon active - Cell 3        │  Quote #2456 - $45K      │
│  🔴 Quality hold - Job 1234      │  PO #8901 - $12K         │
│  🟡 Capacity warning tomorrow    │  Schedule change request │
│  🟡 Material shortage alert      │  OT approval - 8 hours   │
├─────────────────────────────────────────────────────────────┤
│  TEAM STATUS                     │  KEY METRICS TODAY       │
│  On Floor: 42/45 (93%)           │  OEE: 84% (Target: 85%)  │
│  Training: 2                     │  Scrap: 1.2% (Max: 2%)   │
│  Absent: 1                       │  OTD: 95% (Target: 95%)  │
└─────────────────────────────────────────────────────────────┘
```

### Dashboard Widgets Explained

#### SQDCP Status
- **S (Safety)**: Days since incident, open hazards
- **Q (Quality)**: PPM, open NCs, customer complaints
- **D (Delivery)**: OTD %, late orders, at-risk jobs
- **C (Cost)**: Actual vs budget, scrap $, OT hours
- **P (People)**: Attendance, training, engagement

Click any letter to drill into details.

#### Production Schedule
- Live status from shop floor
- Color coding: ✓ On Track | ⚠️ At Risk | 🔴 Behind
- Click to open full schedule view

#### Exceptions Panel
- Priority-sorted issues needing your attention
- Click to action immediately
- Filters: All | Production | Quality | Personnel

#### Approvals Queue
- Items waiting for your decision
- Age indicator (new/aging)
- Quick approve/reject from dashboard

### Customizing Your Dashboard

1. Click **⚙️ Customize** button
2. Available actions:
   - Drag widgets to rearrange
   - Resize widgets (collapse/expand)
   - Add new widgets from catalog
   - Remove widgets you don't need
3. Save as "My Default" or create named views

---

## 4. Daily Operations Management

### GM Daily Routine (Recommended)

#### Start of Shift (15 minutes)
```
06:45  Check overnight exceptions (Sensei email digest)
07:00  Quick dashboard review
07:15  Brief with night shift supervisor (handover)
07:30  Stand-up meeting at Obeya board
```

#### Mid-Morning (30 minutes)
```
09:00  Gemba walk (use mobile app)
09:30  Process approvals queue
10:00  Check production progress vs schedule
```

#### Midday (15 minutes)
```
12:00  Review OTD risk report
12:15  Address any escalated issues
```

#### Afternoon (30 minutes)
```
15:00  End-of-day production review
15:30  Quality summary review
16:00  Set up tomorrow (priorities, staffing)
16:30  Clear approvals queue
```

### Gemba Walk with Sensei

Use the mobile app during floor walks:

1. Open **Sensei Mobile → Gemba**
2. Select your route (configurable)
3. At each station:
   - View station metrics
   - Log observations
   - Create immediate actions
   - Take photos for documentation
4. Auto-generates walk summary

### Daily Stand-up Support

Sensei prepares stand-up materials automatically:

```
┌─────────────────────────────────────────────────────────────┐
│               DAILY STAND-UP PACKAGE                         │
│               January 11, 2026 - 7:30 AM                    │
├─────────────────────────────────────────────────────────────┤
│ YESTERDAY'S RESULTS                                          │
│ • Shipped: 14 jobs (Target: 15) - 1 pushed to today         │
│ • Quality: 2 NCs logged (both contained)                    │
│ • Safety: No incidents                                       │
│ • OT: 12 hours (within budget)                              │
├─────────────────────────────────────────────────────────────┤
│ TODAY'S PRIORITIES                                           │
│ 1. ACME Corp order - ships by 3 PM (expedite)               │
│ 2. Cell 3 recovery from yesterday's breakdown               │
│ 3. New customer audit at 10 AM                              │
├─────────────────────────────────────────────────────────────┤
│ WATCH ITEMS                                                  │
│ • Material arrival expected 9 AM (for Job 2345)             │
│ • Inspector out - QA coverage arranged                       │
│ • Weather alert may affect afternoon delivery               │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. SQDCP & Obeya

### Understanding SQDCP

SQDCP is the heartbeat of Lean operations, tracking five critical dimensions:

| Dimension | What It Measures | Your Target |
|-----------|------------------|-------------|
| **Safety** | Incidents, near-misses, hazards | 0 incidents |
| **Quality** | PPM, NCs, complaints, audits | <1000 PPM |
| **Delivery** | OTD %, lead time, schedule adherence | ≥95% OTD |
| **Cost** | Scrap, rework, OT, variances | Within budget |
| **People** | Attendance, training, engagement | ≥95% attendance |

### Accessing the Obeya

Navigate: **Obeya** in main menu (or `Ctrl + O`)

```
┌─────────────────────────────────────────────────────────────┐
│                     DIGITAL OBEYA                            │
├───────────────┬───────────────┬───────────────┬─────────────┤
│   STRATEGY    │  PERFORMANCE  │   PROBLEMS    │  PROJECTS   │
│               │               │               │             │
│ • Vision      │ • SQDCP       │ • Active A3s  │ • Kaizen    │
│ • Goals       │ • Trends      │ • 5 Whys      │ • Initiatives│
│ • Initiatives │ • Pareto      │ • Countermeasures│ • Milestones│
│               │               │               │             │
└───────────────┴───────────────┴───────────────┴─────────────┘
```

### Daily Obeya Board Meeting

Sensei facilitates your daily meeting:

1. **Auto-populates** board with fresh data
2. **Highlights** items that changed since yesterday
3. **Tracks** action item completion
4. **Records** meeting notes and decisions
5. **Assigns** follow-ups with due dates

### Updating SQDCP Metrics

Some metrics update automatically (from MES, quality system). Others need manual input:

| Metric | Update Method |
|--------|---------------|
| Production counts | Automatic from work orders |
| Quality NCs | Automatic from quality module |
| Safety incidents | Manual entry or supervisor input |
| Attendance | Automatic from time system |
| Customer complaints | Manual entry |

---

## 6. Production Management

### Production Schedule View

Access: **Production → Schedule**

```
┌─────────────────────────────────────────────────────────────┐
│         PRODUCTION SCHEDULE - January 11, 2026              │
├─────────────────────────────────────────────────────────────┤
│ Cell/Work Center │ 6AM │ 8AM │ 10AM │ 12PM │ 2PM │ 4PM     │
├──────────────────┼─────┼─────┼──────┼──────┼─────┼─────────┤
│ CNC Mill 1       │████ JOB-1234 ████│████ JOB-1235 ████│    │
│ CNC Mill 2       │████████ JOB-1236 ████████│ Setup │ 1237 │
│ Lathe 1          │█ JOB-1238 █│███ JOB-1239 ███│ Avail │    │
│ Assembly 1       │████████████ JOB-1240 ████████████│      │
│ Inspection       │ Q │ Q │ Q │ Q │ Q │ Final │             │
└─────────────────────────────────────────────────────────────┘
Legend: ████ = Scheduled | Q = Queue | Red outline = At risk
```

### Schedule Actions

| Action | How To |
|--------|--------|
| View job details | Click on job block |
| Reschedule job | Drag to new time slot |
| Split job | Right-click → Split |
| Expedite | Right-click → Mark Expedite |
| Hold job | Right-click → Place on Hold |

### Capacity Dashboard

View capacity utilization and bottlenecks:

```
Capacity Utilization - This Week
┌─────────────────────────────────────────────────────────────┐
│ Work Center    │ Mon │ Tue │ Wed │ Thu │ Fri │ Week Avg    │
├────────────────┼─────┼─────┼─────┼─────┼─────┼─────────────┤
│ CNC Mills      │ 92% │ 88% │ 95% │ 85% │ 78% │ 88% ████▓  │
│ Lathes         │ 75% │ 80% │ 82% │ 79% │ 70% │ 77% ███▓   │
│ Assembly       │ 85% │ 90% │ 88% │ 92% │ 85% │ 88% ████▓  │
│ Inspection     │ 95% │ 98% │ 96% │ 94% │ 90% │ 95% █████  │
└─────────────────────────────────────────────────────────────┘
⚠️ Inspection at capacity - may bottleneck
```

### Work Order Management

Every job is tracked via work orders:

| Field | Description |
|-------|-------------|
| WO Number | Unique identifier |
| Customer | Customer name |
| Part Number | What we're making |
| Quantity | How many |
| Due Date | Customer required date |
| Priority | Normal / Expedite / Rush |
| Status | Not Started / In Progress / Complete / On Hold |
| Traveler | Digital work instructions |

### Andon Response

When an Andon is triggered:

1. **Alert appears** on your dashboard (and mobile)
2. **Details show**: Cell, operator, reason, time
3. **Your actions**:
   - Acknowledge (I'm aware)
   - Assign (send someone)
   - Respond (going myself)
   - Resolve (clear the Andon)

---

## 7. Quality Oversight

### Quality Dashboard

Access: **Quality → Dashboard**

```
┌─────────────────────────────────────────────────────────────┐
│                  QUALITY DASHBOARD                           │
├─────────────────────────────────────────────────────────────┤
│  PPM This Month: 850          │  Open NCs: 12               │
│  Customer Complaints: 2       │  Open CAPAs: 3              │
│  Audit Score: 94%             │  Inspection Backlog: 4 jobs │
├─────────────────────────────────────────────────────────────┤
│  QUALITY TREND (Last 12 Months)                             │
│  PPM: ▁▂▂▃▂▂▃▂▁▁▂▁                                          │
│        J F M A M J J A S O N D                              │
└─────────────────────────────────────────────────────────────┘
```

### Nonconformance (NC) Management

Your role in NC process:

| NC Stage | Your Action |
|----------|-------------|
| New NC Logged | Notified for awareness |
| Containment | Approve containment action |
| Disposition | Approve scrap/rework/return |
| RCA Required | Assign investigator |
| CAPA Created | Review and approve |
| Customer Notification | Approve communication |

### Quality Holds

When quality places a hold:

1. **Production stops** for affected parts
2. **You're notified** immediately
3. **Your options**:
   - Review with Quality Manager
   - Authorize sort/contain
   - Approve scrap or rework
   - Release hold when resolved

### Customer Audit Support

Sensei helps you prepare for audits:

```
┌─────────────────────────────────────────────────────────────┐
│           UPCOMING AUDIT: ACME Corp - Feb 1                 │
├─────────────────────────────────────────────────────────────┤
│ Preparation Status: 75% Ready                               │
│                                                              │
│ ✓ Quality Manual - Current                                   │
│ ✓ Control Plans - Updated                                    │
│ ✓ Training Records - Complete                                │
│ ○ Calibration Records - 2 instruments due                   │
│ ○ Corrective Actions - 1 CAPA overdue                       │
│ ○ Internal Audit - Due before customer audit                │
│                                                              │
│ [Generate Audit Readiness Report]                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Team Management

### Your Team Overview

Access: **People → My Team**

```
┌─────────────────────────────────────────────────────────────┐
│                    MY TEAM - GM VIEW                         │
├─────────────────────────────────────────────────────────────┤
│ Direct Reports (6)                                           │
│ ├── Production Supervisor - John Smith (12 direct)          │
│ ├── Quality Manager - Maria Garcia (4 direct)               │
│ ├── Warehouse Lead - David Chen (6 direct)                  │
│ ├── Maintenance Supervisor - Sarah Johnson (3 direct)       │
│ ├── Shift 2 Supervisor - Mike Williams (10 direct)          │
│ └── Administrative Assistant - Lisa Brown                    │
│                                                              │
│ Total Under Your Organization: 45                           │
└─────────────────────────────────────────────────────────────┘
```

### Training Matrix

View skill coverage for your facility:

```
SKILL MATRIX - Production Team
┌─────────────────────────────────────────────────────────────┐
│ Employee        │ CNC │ Lathe│ Weld │ Assy │ Insp │ Setup │
├─────────────────┼─────┼──────┼──────┼──────┼──────┼───────┤
│ Smith, John     │ ★★★ │ ★★★  │ ★★   │ ★★★  │ ★★★  │ ★★★   │
│ Garcia, Maria   │ ★★  │ ★★   │ ★★★  │ ★★★  │ ★★★  │ ★★    │
│ Chen, David     │ ★★★ │ ★    │ ○    │ ★★   │ ★★   │ ★★★   │
│ Johnson, Sarah  │ ★   │ ★★★  │ ★★   │ ★★★  │ ★    │ ★     │
└─────────────────────────────────────────────────────────────┘
Legend: ★★★ = Expert | ★★ = Proficient | ★ = Basic | ○ = None
```

### Certification Tracking

Monitor certifications across your teams:

| Status | Count | Action |
|--------|-------|--------|
| Current | 142 | None |
| Expiring (30 days) | 8 | Schedule training |
| Expired | 2 | Immediate action |
| Not Started | 5 | Assign training |

### Time & Attendance

Access: **People → Attendance**

- View who's in today
- Approve time-off requests
- Monitor overtime trends
- See absence patterns

---

## 9. Sales & Quoting

### Pipeline Visibility

Access: **Sales → Pipeline**

As GM, you see the sales pipeline for:
- Capacity planning
- Quote approval
- Customer relationship awareness

```
┌─────────────────────────────────────────────────────────────┐
│                   SALES PIPELINE                             │
├─────────────────────────────────────────────────────────────┤
│ Stage            │ Count │ Value     │ Avg Age │ Win Rate  │
├──────────────────┼───────┼───────────┼─────────┼───────────┤
│ New Inquiry      │  12   │ $180,000  │  3 days │    -      │
│ Quoting          │   8   │ $320,000  │  7 days │    -      │
│ Quoted           │  15   │ $580,000  │ 14 days │   35%     │
│ Negotiating      │   5   │ $245,000  │ 21 days │   60%     │
│ Verbal PO        │   3   │ $125,000  │  5 days │   95%     │
├──────────────────┼───────┼───────────┼─────────┼───────────┤
│ TOTAL ACTIVE     │  43   │ $1.45M    │         │           │
└─────────────────────────────────────────────────────────────┘
```

### Quote Approval Workflow

Quotes requiring your approval:

| Quote Value | Approval Required |
|-------------|-------------------|
| < $10,000 | Auto-approved |
| $10,000 - $100,000 | **GM Approval** |
| > $100,000 | GM + CEO Approval |

When reviewing quotes:

1. Click quote in approval queue
2. Review details:
   - Customer and requirements
   - Pricing and margin
   - Capacity impact
   - Lead time promise
   - Risk assessment
3. Approve, Reject, or Request Changes

### Capacity Impact Analysis

For larger quotes, Sensei shows capacity impact:

```
CAPACITY IMPACT - Quote #2456 (ACME Corp)
┌─────────────────────────────────────────────────────────────┐
│ If awarded, this job would:                                  │
│                                                              │
│ • Consume 15% of CNC capacity for 4 weeks                   │
│ • Require 2 additional overtime shifts                       │
│ • Impact delivery of 3 existing orders (see list)           │
│ • Generate estimated margin of $12,500 (28%)                │
│                                                              │
│ Risk Level: MEDIUM                                           │
│ Recommendation: Approve with extended lead time              │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Industrial Quoting & NPI
As GM, you oversee the transition from high-value Sales opportunities to Production through the **Quoting Helper** and **NPI Handoff** workflows.

#### Quote Approvals
- Review engineering inputs from all disciplines (EE, ME, Quality) in the **Quoting Workbench**.
- Analyze **Margin Analysis** against floor policies.
- Use **AI Quote Memory** to validate assumptions based on historical performance.

#### NPI Handoff (Quote → Production)
- Once a strategic quote is accepted, trigger the **NPI Handoff**.
- Sensei OS automatically creates an **Obeya Project**, baselines the **Traveler**, and freezes the **BOM**.
- This ensures a deterministic path to execution without data loss between Sales and the Shop Floor.

---

## 10. Inventory & Warehouse

### Inventory Dashboard

Access: **Warehouse → Inventory**

```
┌─────────────────────────────────────────────────────────────┐
│                 INVENTORY OVERVIEW                           │
├─────────────────────────────────────────────────────────────┤
│ Total Value: $1,234,567        │ Turnover: 8.5 (Target: 12) │
│ Active SKUs: 2,456             │ Slow Moving: 145 items     │
│ Below Reorder: 23 items        │ Excess: $45,000            │
├─────────────────────────────────────────────────────────────┤
│ INVENTORY HEALTH                                             │
│ Raw Materials:    ████████░░ 82% of target                  │
│ WIP:              ██████░░░░ 65% of target                  │
│ Finished Goods:   ███████░░░ 71% of target                  │
│ Consumables:      █████████░ 94% of target                  │
└─────────────────────────────────────────────────────────────┘
```

### Material Shortage Alerts

Sensei proactively alerts you:

```
⚠️ MATERIAL SHORTAGE ALERT

Material: Aluminum Bar 6061 2"
Current Stock: 45 lbs
Required for Active Jobs: 120 lbs
Shortage: 75 lbs

Jobs Affected:
• JOB-1234 (ACME) - Due Jan 15 - CRITICAL
• JOB-1238 (Beta Corp) - Due Jan 18

Recommended Action: Expedite PO #4567 (ETA Jan 13)
[Create Expedite Request]
```

### Shipping Dashboard

Monitor outbound logistics:

| Metric | Today | This Week |
|--------|-------|-----------|
| Orders to Ship | 15 | 62 |
| On Track | 13 | 58 |
| At Risk | 2 | 4 |
| Shipped | 8 | 34 |
| On Time | 100% | 96% |

---

## 11. Approvals & Escalations

### Your Approval Authority

As GM, you can approve:

| Item Type | Authority Range | Requires CEO Above |
|-----------|-----------------|-------------------|
| Quotes | $10K - $100K | $100K+ |
| Purchase Orders | Up to $50K | $50K+ |
| Expense Reports | Up to $5K | $5K+ |
| Schedule Changes | All | If impacts customer |
| Overtime | All | If >20% budget |
| Time Off | Supervisors | None |

### Approval Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                  PENDING APPROVALS (6)                       │
├─────────────────────────────────────────────────────────────┤
│ 🔴 Quote #2456 - $45,000 - ACME Corp (3 days old)           │
│    Requestor: Sales Engineer                                 │
│    [Approve] [Reject] [Request Info]                        │
├─────────────────────────────────────────────────────────────┤
│ 🟡 PO #8901 - $12,500 - Tooling (1 day old)                 │
│    Requestor: Maintenance Supervisor                        │
│    [Approve] [Reject] [Request Info]                        │
├─────────────────────────────────────────────────────────────┤
│ 🟢 OT Request - 8 hours - Production (New)                  │
│    Requestor: Production Supervisor                         │
│    [Approve] [Reject]                                        │
└─────────────────────────────────────────────────────────────┘
```

### Escalation Handling

When items escalate to you:

1. **Review context** (history, previous decisions)
2. **Check authority** (can you decide or must escalate?)
3. **Make decision** with documented rationale
4. **Communicate** back to escalator

---

## 12. Exception Management

### Exception Types You'll See

| Exception Type | Severity | Typical Response |
|----------------|----------|------------------|
| Machine Down | Critical | Immediate action |
| Quality Hold | Critical | Same-day resolution |
| Late Shipment Risk | High | Expedite review |
| Material Shortage | High | Procurement action |
| Staffing Gap | Medium | Coverage planning |
| Capacity Warning | Medium | Schedule adjustment |
| Training Due | Low | Scheduling |

### Exception Workflow

```
NEW EXCEPTION → ASSESS → ASSIGN → RESOLVE → CLOSE

Your role at each stage:
• NEW: Review and prioritize
• ASSESS: Determine severity and impact
• ASSIGN: Delegate to appropriate person
• RESOLVE: Monitor and support
• CLOSE: Verify resolution
```

### Exception Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│              EXCEPTION MANAGEMENT CENTER                     │
├─────────────────────────────────────────────────────────────┤
│ Active Exceptions: 12      │ Avg Resolution Time: 4.2 hours │
├─────────────────────────────────────────────────────────────┤
│ By Severity:               │ By Age:                        │
│ 🔴 Critical: 2             │ < 1 hour: 3                    │
│ 🟡 High: 4                 │ 1-4 hours: 5                   │
│ 🟢 Medium: 6               │ 4-24 hours: 3                  │
│                            │ > 24 hours: 1 (escalated)      │
├─────────────────────────────────────────────────────────────┤
│ By Department:             │                                │
│ Production: 6 | Quality: 3 | Warehouse: 2 | Maintenance: 1 │
└─────────────────────────────────────────────────────────────┘
```

---

## 13. Reports & Analytics

### Standard Reports for GM

| Report | Frequency | Description |
|--------|-----------|-------------|
| Daily Production Summary | Daily | Yesterday's results |
| Weekly SQDCP | Weekly | Week performance vs targets |
| Monthly Operations | Monthly | Comprehensive review |
| OEE Report | Weekly | Equipment effectiveness |
| Quality Summary | Weekly | NC, CAPA, trends |
| Inventory Report | Weekly | Levels, turns, aging |

### Creating Custom Reports

1. Navigate to **Analytics → Report Builder**
2. Select data sources
3. Choose metrics and dimensions
4. Set filters and date ranges
5. Choose visualization type
6. Save and schedule

### Scheduling Reports

Set up automatic delivery:

```
SCHEDULE REPORT: Daily Production Summary
┌─────────────────────────────────────────────────────────────┐
│ Frequency: Daily                                             │
│ Time: 6:00 AM                                               │
│ Recipients: GM, Production Supervisor                       │
│ Format: PDF + Excel                                         │
│ Include: Charts, Tables, Exceptions                         │
└─────────────────────────────────────────────────────────────┘
```

### Analytics Deep Dive

Access: **Analytics → Explorer**

Create ad-hoc analysis:
- Drag-and-drop dimensions
- Real-time pivoting
- Export to Excel/PDF
- Share with team

---

## 14. AI Tools for GM

### Sensei AI Assistant

Access via command palette (`Ctrl + /`) or chat icon

**Example GM queries**:
- "What are today's top 3 risks?"
- "Why did OTD drop this week?"
- "Show me overtime trends by department"
- "What should I focus on in tomorrow's meeting?"
- "Predict next week's capacity issues"

### AI-Powered Features

#### 1. Predictive Maintenance
```
⚠️ AI PREDICTION: CNC Mill #3

Predicted issue: Spindle bearing wear
Confidence: 87%
Predicted failure window: 7-14 days
Recommended action: Schedule PM this weekend

[Schedule Maintenance] [Dismiss]
```

#### 2. Schedule Optimization
AI suggests optimal schedule:
- Minimizes changeovers
- Balances workload
- Considers operator skills
- Accounts for maintenance windows

#### 3. Exception Prediction
AI identifies potential issues before they occur:
- Material shortages
- Capacity conflicts
- Quality risks
- Delivery delays

### AI Meeting Prep

Before any meeting, click **AI Prep**:
```
MEETING: Weekly Production Review
Attendees: Supervisors, Quality, Maintenance

AI Preparation:
• Key metrics and trends (attached)
• Open issues with attendees
• Previous action item status
• Suggested agenda topics
• Talking points for problem areas
```

---

## 15. Mobile Access

### Sensei Mobile for GM

Download: iOS App Store / Google Play

**Optimized for GM workflow**:
- Dashboard view (condensed)
- Approval queue (quick actions)
- Andon notifications (immediate)
- Gemba walk tool
- Camera integration
- Offline capability

### Mobile-Specific Features

| Feature | Description |
|---------|-------------|
| Quick Approve | Swipe to approve/reject |
| Gemba Mode | Structured floor walk |
| Photo Capture | Document issues with camera |
| Voice Notes | Audio memos linked to records |
| Notifications | Push for critical alerts |

### Push Notification Settings

Configure what alerts you receive:

```
MOBILE NOTIFICATIONS - GM
┌─────────────────────────────────────────────────────────────┐
│ ✓ Andon alerts (all)                                        │
│ ✓ Quality holds                                             │
│ ✓ Approvals > $10,000                                       │
│ ○ Approvals < $10,000 (daily digest instead)               │
│ ✓ Critical exceptions                                       │
│ ○ High exceptions (email instead)                          │
│ ✓ Machine down > 30 min                                     │
│ ✓ Customer escalations                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Reference Card

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + D` | GM Dashboard |
| `Ctrl + O` | Obeya |
| `Ctrl + P` | Production Schedule |
| `Ctrl + Q` | Quality Dashboard |
| `Ctrl + E` | Exceptions |
| `Ctrl + /` | Command Palette / AI |
| `F5` | Refresh current view |

### Daily GM Checklist

```
Morning:
□ Check overnight exceptions
□ Review Sensei daily digest email
□ Quick dashboard review
□ Production handover
□ Daily stand-up meeting

Midday:
□ Process approval queue
□ Check OTD risk report
□ Gemba walk (minimum 30 min)

Afternoon:
□ Production progress review
□ Address escalated issues
□ Clear approvals queue
□ Set up tomorrow
```

### Emergency Contacts

| Situation | Contact | Method |
|-----------|---------|--------|
| System down | IT Help Desk | ext. 5000 |
| Safety incident | EHS | ext. 5555 |
| Customer escalation | CEO | Mobile |
| Quality crisis | Quality Manager | Direct |
| Equipment emergency | Maintenance | Radio Ch. 3 |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Operations*
