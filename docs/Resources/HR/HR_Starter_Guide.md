# HR Manager Starter Guide

## Sensei OS - Human Resources Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [HR Dashboard](#3-hr-dashboard)
4. [Employee Management](#4-employee-management)
5. [Onboarding New Hires](#5-onboarding-new-hires)
6. [Time & Attendance](#6-time--attendance)
7. [Leave Management](#7-leave-management)
8. [Compensation & Benefits](#8-compensation--benefits)
9. [Performance Management](#9-performance-management)
10. [Training & Development](#10-training--development)
11. [Recruiting & Hiring](#11-recruiting--hiring)
12. [Organizational Management](#12-organizational-management)
13. [Compliance & Reporting](#13-compliance--reporting)
14. [Employee Self-Service](#14-employee-self-service)
15. [HR Analytics](#15-hr-analytics)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use project visibility to understand staffing constraints and training needs impacting delivery.
- Use comments to document coordination items (handoffs, coverage, escalations) when you have access.
- Use milestones for major events that affect staffing plans (launches, deadlines).

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role in HR

As HR Manager, you are the **steward of our people**. Sensei OS empowers you to:

- **Manage the employee lifecycle** from hire to retire
- **Track time and attendance** accurately
- **Administer leave and benefits** efficiently
- **Drive performance** through development
- **Ensure compliance** with policies and regulations
- **Support leaders** with people insights

### HR Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Employee Records | Full | Create, view, edit all employees |
| Onboarding | Full | Manage new hire process |
| Time & Attendance | Full | View all, approve, configure |
| Leave Administration | Full | Policies, balances, approvals |
| Compensation | Full | Pay rates, adjustments, reports |
| Benefits | Full | Enrollment, administration |
| Performance | Full | Reviews, goals, calibration |
| Training | Full | Programs, tracking, compliance |
| Recruiting | Full | Positions, candidates, hiring |
| Reports | Full | All HR analytics and reports |
| System Config | Full | HR settings, workflows, policies |

### What Makes HR Access Unique

1. **Full employee visibility** across organization
2. **Sensitive data access** (compensation, performance)
3. **Approval workflows** for HR-related requests
4. **Compliance tracking** and reporting
5. **Organization structure** management

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter your credentials
3. Complete Multi-Factor Authentication (MFA) setup
4. Update your profile

### Initial Setup Tasks

- [ ] Verify your HR permissions
- [ ] Review company organization structure
- [ ] Check leave policy configurations
- [ ] Review pending approvals
- [ ] Set up notification preferences

### Your HR Home Screen

```
┌─────────────────────────────────────────────────────────────┐
│                 HR DASHBOARD                                 │
│                 January 11, 2026                            │
├─────────────────────────────────────────────────────────────┤
│  WORKFORCE AT A GLANCE                                       │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │ Headcount  │ │ Open Req   │ │ Turnover   │ │ Attending  ││
│  │    247     │ │     5      │ │   8.2%     │ │   231/247  ││
│  │ ▲ 3 MTD    │ │ 2 urgent   │ │ ▼ 1.5%     │ │   93.5%    ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘│
├─────────────────────────────────────────────────────────────┤
│  ACTION REQUIRED                                             │
│  🔴 3 Leave requests pending > 3 days                       │
│  🟡 5 Performance reviews overdue                            │
│  🟡 New hire onboarding: 2 starting Monday                  │
│  🔵 Certification expiring: 8 employees this month          │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. HR Dashboard

### Dashboard Widgets

#### Workforce Summary
Key headcount metrics:
- **Total Headcount**: Active employees
- **MTD Change**: Hires minus terms this month
- **By Department**: Breakdown by org unit
- **By Status**: Full-time, part-time, temp

#### Recruiting Pipeline
Open positions and candidates:
- **Open Requisitions**: Active job postings
- **Candidates**: In pipeline by stage
- **Time to Fill**: Average days to fill

#### Attendance Overview
Today's attendance snapshot:
- **Attending**: Clocked in / scheduled
- **Absent**: Not present (planned/unplanned)
- **Late**: Arrived after scheduled time

#### Compliance Alerts
Upcoming expirations and requirements:
- **Certifications due**
- **Training compliance**
- **Document expirations**

### Customizing Your Dashboard

1. Click **⚙️ Settings**
2. Add/remove widgets
3. Set date ranges
4. Configure alerts
5. Save as default

---

## 4. Employee Management

### Employee Directory

Access: **HR → Employees**

```
EMPLOYEE DIRECTORY
┌─────────────────────────────────────────────────────────────┐
│ [🔍 Search] [+ New Employee] [📥 Export] [⚙️ Filters]       │
├─────────────────────────────────────────────────────────────┤
│ Name           │ Department │ Position       │ Status │ ... │
├────────────────┼────────────┼────────────────┼────────┼─────┤
│ Adams, John    │ Operations │ Operator       │ Active │ [→] │
│ Baker, Sarah   │ Quality    │ Inspector      │ Active │ [→] │
│ Chen, David    │ Production │ Team Lead      │ Active │ [→] │
│ Davis, Mike    │ Maintenance│ Technician     │ LOA    │ [→] │
└────────────────┴────────────┴────────────────┴────────┴─────┘
│ Showing 1-25 of 247         [< Prev] [1] [2] ... [10] [Next >]│
└─────────────────────────────────────────────────────────────┘
```

### Employee Profile

Each employee has a comprehensive profile:

```
┌─────────────────────────────────────────────────────────────┐
│  EMPLOYEE PROFILE                                            │
│  ┌────────┐                                                  │
│  │ Photo  │  John Adams                                      │
│  │        │  Employee ID: 10234                             │
│  └────────┘  Operations - Operator                          │
├─────────────────────────────────────────────────────────────┤
│  TABS: [Personal] [Employment] [Compensation] [Leave]        │
│        [Performance] [Training] [Documents] [Notes]          │
├─────────────────────────────────────────────────────────────┤
│  PERSONAL INFORMATION                                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ First Name:    John                                      │ │
│  │ Last Name:     Adams                                     │ │
│  │ Email:         john.adams@company.com                   │ │
│  │ Phone:         (555) 123-4567                           │ │
│  │ Address:       123 Main St, City, ST 12345              │ │
│  │ DOB:           March 15, 1985                           │ │
│  │ Emergency:     Jane Adams (555) 123-4568                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  [Edit] [View History] [Generate Letter]                     │
└─────────────────────────────────────────────────────────────┘
```

### Employee Profile Tabs

| Tab | Contents |
|-----|----------|
| Personal | Contact info, demographics, emergency contacts |
| Employment | Hire date, position history, status, supervisor |
| Compensation | Pay rate, salary history, deductions |
| Leave | Balances, history, upcoming time off |
| Performance | Reviews, goals, competencies |
| Training | Completed, assigned, certifications |
| Documents | Offer letter, policies signed, I-9, W-4 |
| Notes | HR notes, confidential memos |

### Creating a New Employee

1. Click **+ New Employee**
2. Enter required information:
   - Personal details
   - Employment information
   - Position and department
   - Compensation
   - Start date
3. System creates account and initiates onboarding

---

## 5. Onboarding New Hires

### Onboarding Dashboard

Access: **HR → Onboarding**

```
ONBOARDING DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│  UPCOMING START DATES                                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Jan 13 │ Sarah Chen      │ Engineer    │ 80% ready     │ │
│  │ Jan 13 │ Mike Johnson    │ Operator    │ 60% ready     │ │
│  │ Jan 20 │ Lisa Wang       │ Quality     │ 25% ready     │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  IN PROGRESS (First 90 Days)                                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Name         │ Started  │ Day │ Progress │ Status       │ │
│  │ Tom Brown    │ Jan 2    │ 9   │ ████░░   │ On Track    │ │
│  │ Amy Wilson   │ Dec 15   │ 27  │ █████░   │ Behind      │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Onboarding Checklist

Each new hire has an onboarding checklist:

```
ONBOARDING CHECKLIST - Sarah Chen
Starting: January 13, 2026 | Position: Engineer
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ PRE-START (HR Tasks)                          [60% Complete] │
│ ☑ Offer letter signed                                        │
│ ☑ Background check complete                                  │
│ ☑ I-9 verification scheduled                                 │
│ ☐ Benefits enrollment initiated                              │
│ ☐ Workstation assigned                                       │
│                                                              │
│ PRE-START (IT Tasks)                          [50% Complete] │
│ ☑ User account created                                       │
│ ☐ Email activated                                            │
│ ☐ Badge created                                              │
│ ☐ Equipment ordered                                          │
│                                                              │
│ PRE-START (Manager Tasks)                     [0% Complete]  │
│ ☐ First week schedule created                                │
│ ☐ Buddy assigned                                             │
│ ☐ Training plan created                                      │
│                                                              │
│ DAY 1                                         [Not Started]  │
│ ☐ Welcome meeting with HR                                    │
│ ☐ Paperwork completion                                       │
│ ☐ Facility tour                                              │
│ ☐ Manager introduction                                       │
│ ☐ Team introduction                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Automating Onboarding

Sensei automates onboarding tasks:

1. **Task assignment**: Auto-assigns tasks to HR, IT, Manager
2. **Reminders**: Sends reminders before start date
3. **Notifications**: Alerts when tasks complete/overdue
4. **Training**: Auto-enrolls in required training
5. **Document requests**: Sends forms for completion

### 90-Day Onboarding Milestones

| Day | Milestone | Responsible |
|-----|-----------|-------------|
| Pre-Start | All prep complete | HR, IT, Manager |
| Day 1 | Orientation complete | HR |
| Day 7 | First week check-in | Manager |
| Day 30 | 30-day review | Manager |
| Day 60 | 60-day check-in | Manager |
| Day 90 | Probation review | Manager, HR |

---

## 6. Time & Attendance

### Time & Attendance Dashboard

Access: **HR → Time & Attendance**

```
TIME & ATTENDANCE - Today
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  TODAY'S SUMMARY                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Scheduled   │ │ Clocked In  │ │ Absent      │            │
│  │    247      │ │    231      │ │    12       │            │
│  │             │ │ (5 late)    │ │ (4 unpln)   │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                              │
│  EXCEPTIONS                                                  │
│  ├─ 5 Late arrivals (>5 min)                                │
│  ├─ 2 Missed punches                                        │
│  ├─ 4 Unplanned absences                                    │
│  └─ 3 Overtime pending approval                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Reviewing Time Records

View and edit time entries:

```
TIME RECORDS - Week of Jan 6-12, 2026
Employee: John Adams
┌─────────────────────────────────────────────────────────────┐
│ Date    │ Sched    │ In      │ Out     │ Total │ Status    │
├─────────┼──────────┼─────────┼─────────┼───────┼───────────┤
│ Mon 1/6 │ 6A-2:30P │ 5:58 AM │ 2:32 PM │ 8.5h  │ ✓ OK      │
│ Tue 1/7 │ 6A-2:30P │ 6:05 AM │ 2:35 PM │ 8.5h  │ ⚠️ Late    │
│ Wed 1/8 │ 6A-2:30P │ 5:55 AM │ -       │ -     │ 🔴 Missing │
│ Thu 1/9 │ 6A-2:30P │ 5:52 AM │ 4:00 PM │ 10.1h │ ⚠️ OT Pend │
│ Fri 1/10│ 6A-2:30P │ 6:00 AM │ 2:30 PM │ 8.5h  │ ✓ OK      │
├─────────┴──────────┴─────────┴─────────┴───────┴───────────┤
│ Week Total: 35.6h (Reg) + 1.6h (OT Pending)                 │
│                                                              │
│ [Edit Punches] [Approve OT] [Add Exception]                 │
└─────────────────────────────────────────────────────────────┘
```

### Time Entry Corrections

HR can edit time records:

1. Open employee's time record
2. Click **Edit** on the entry
3. Enter correction
4. Add reason for change
5. System logs the edit with audit trail

### Approving Overtime

Review and approve overtime requests:

```
OVERTIME APPROVAL QUEUE
┌─────────────────────────────────────────────────────────────┐
│ Employee    │ Date   │ Hours │ Reason           │ Manager   │
├─────────────┼────────┼───────┼──────────────────┼───────────┤
│ J. Adams    │ Jan 9  │ 1.5h  │ Rush order       │ Approved  │
│ M. Garcia   │ Jan 9  │ 2.0h  │ Equipment issue  │ Approved  │
│ D. Chen     │ Jan 10 │ 3.0h  │ Inventory count  │ Pending   │
└─────────────┴────────┴───────┴──────────────────┴───────────┘
│                                                              │
│ [Approve Selected] [Deny] [Request More Info]               │
└─────────────────────────────────────────────────────────────┘
```

### Attendance Policies

Configure attendance rules:

| Policy | Setting |
|--------|---------|
| Grace period | 5 minutes |
| Late threshold | >5 min = late |
| Overtime approval | Required if >8 hrs |
| Meal deduction | Auto-deduct 30 min |
| Rounding | 15-minute rounding |

---

## 7. Leave Management

### Leave Dashboard

Access: **HR → Leave Management**

```
LEAVE DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  PENDING REQUESTS                                            │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Employee    │ Type │ Dates        │ Days │ Status       │ │
│  ├─────────────┼──────┼──────────────┼──────┼──────────────┤ │
│  │ J. Adams    │ PTO  │ Jan 20-21    │ 2    │ ⏳ Mgr Pend  │ │
│  │ S. Chen     │ Sick │ Jan 11       │ 1    │ 🔴 HR Pend   │ │
│  │ M. Wilson   │ PTO  │ Feb 1-14     │ 10   │ ⏳ Mgr Pend  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  TODAY'S ABSENCES                                            │
│  ├─ PTO: 8 employees                                         │
│  ├─ Sick: 3 employees                                        │
│  ├─ FMLA: 1 employee                                         │
│  └─ Bereavement: 0                                           │
│                                                              │
│  UPCOMING (Next 2 Weeks)                                     │
│  ├─ 12 PTO requests approved                                │
│  └─ Coverage OK in all departments                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Leave Types

| Type | Accrual | Carryover | Approval |
|------|---------|-----------|----------|
| PTO | Yes | Up to 40 hrs | Manager |
| Sick | Yes | Unlimited | Manager |
| Personal | Granted | No | Manager |
| FMLA | N/A | N/A | HR |
| Bereavement | Granted | N/A | HR |
| Jury Duty | Granted | N/A | HR |

### Processing Leave Requests

For requests requiring HR approval:

1. Open the request
2. Review details:
   - Employee eligibility
   - Balance available
   - Documentation (if required)
3. Approve or deny

```
LEAVE REQUEST DETAIL
┌─────────────────────────────────────────────────────────────┐
│ Employee: Sarah Chen                                         │
│ Request Type: Sick Leave                                     │
│ Dates: January 11, 2026 (1 day)                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Sick Balance: 40 hours available                            │
│ Hours Requested: 8 hours                                     │
│ Remaining: 32 hours                                          │
│                                                              │
│ Manager Approval: ✓ Approved (D. Williams - Jan 11 8:15 AM) │
│                                                              │
│ Documentation Required: No (single day)                      │
│                                                              │
│ HR Action: [Approve] [Deny] [Request Documentation]         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### FMLA Administration

Track FMLA leave:

1. Employee requests FMLA
2. HR provides eligibility notice
3. HR provides rights & responsibilities
4. Medical certification obtained
5. HR tracks 12-week entitlement
6. Return to work certification (if applicable)

```
FMLA TRACKER - Mike Davis
┌─────────────────────────────────────────────────────────────┐
│ FMLA Case: FMLA-2026-003                                     │
│ Type: Serious health condition (self)                        │
│ Start Date: December 1, 2025                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ENTITLEMENT (12-Month Period)                                │
│ ├─ Total Available: 480 hours (12 weeks)                    │
│ ├─ Used: 240 hours (6 weeks)                                │
│ ├─ Remaining: 240 hours (6 weeks)                           │
│ └─ Expected Return: February 15, 2026                        │
│                                                              │
│ DOCUMENTATION                                                │
│ ☑ Eligibility Notice sent - Nov 28                          │
│ ☑ Rights & Responsibilities - Nov 28                        │
│ ☑ Medical Certification received - Dec 2                    │
│ ☐ Return to work certification - Pending                    │
│                                                              │
│ NOTES                                                        │
│ [View FMLA Notes]                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Leave Policies

Configure leave policies:

- Accrual rates by tenure
- Carryover limits
- Waiting periods
- Blackout dates
- Approval workflows

---

## 8. Compensation & Benefits

### Compensation Overview

Access: **HR → Compensation**

```
COMPENSATION DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  PAYROLL SUMMARY                                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Total Headcount: 247                                    │ │
│  │ Monthly Payroll: $1,247,500                             │ │
│  │ Avg Salary: $5,050/month                                │ │
│  │ Compa-Ratio: 0.98 (within range)                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  RECENT CHANGES                                              │
│  ├─ 3 salary adjustments pending approval                   │
│  ├─ 2 promotions effective Jan 1                            │
│  └─ 5 annual reviews with increases pending                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Salary Administration

View and manage pay rates:

```
COMPENSATION DETAIL - John Adams
┌─────────────────────────────────────────────────────────────┐
│ Position: Operator | Grade: O-3                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ CURRENT COMPENSATION                                         │
│ Base Salary: $52,000/year ($25.00/hr)                       │
│ Shift Differential: +$2.00/hr (Night)                       │
│ Effective Date: January 1, 2025                             │
│                                                              │
│ PAY RANGE (Grade O-3)                                        │
│ Min: $45,000 | Mid: $52,500 | Max: $60,000                  │
│ Compa-Ratio: 0.99 (at midpoint)                             │
│                                                              │
│ HISTORY                                                      │
│ ├─ Jan 2025: $52,000 (3% annual increase)                   │
│ ├─ Jan 2024: $50,500 (2.5% annual increase)                 │
│ ├─ Jul 2023: $49,000 (promotion from O-2)                   │
│ └─ Jan 2022: $42,000 (hire rate)                            │
│                                                              │
│ [Request Adjustment] [View Full History]                     │
└─────────────────────────────────────────────────────────────┘
```

### Processing Pay Changes

1. Navigate to employee's compensation
2. Click **Request Adjustment**
3. Enter details:
   - New rate
   - Reason (merit, promotion, market)
   - Effective date
4. Route for approval
5. Sync to payroll when approved

### Benefits Administration

Track benefits enrollment:

```
BENEFITS ENROLLMENT - John Adams
┌─────────────────────────────────────────────────────────────┐
│ Current Enrollment Period: 2026 | Status: Enrolled          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ HEALTH & WELFARE                                             │
│ ├─ Medical: PPO Family (+$450/mo employee cost)             │
│ ├─ Dental: PPO Family (+$45/mo)                             │
│ ├─ Vision: Employee Only (+$8/mo)                           │
│ ├─ Life: 2x salary (company paid)                           │
│ └─ STD/LTD: Enrolled (company paid)                         │
│                                                              │
│ RETIREMENT                                                   │
│ ├─ 401(k): 6% contribution                                  │
│ └─ Company Match: 4% (vested)                               │
│                                                              │
│ OTHER                                                        │
│ ├─ FSA: $2,000/year                                         │
│ └─ HSA: N/A (PPO plan)                                      │
│                                                              │
│ [View Dependents] [Change Elections] [View Costs]           │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Performance Management

### Performance Dashboard

Access: **HR → Performance**

```
PERFORMANCE DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  REVIEW CYCLE STATUS - 2025 Annual Review                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Self-Assessments: 230/247 complete (93%)                │ │
│  │ Manager Reviews: 180/247 complete (73%)                 │ │
│  │ Calibration: 3 of 5 sessions complete                   │ │
│  │ Delivery: Scheduled Feb 1-15                             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  OVERDUE                                                     │
│  🔴 5 manager reviews overdue (Operations)                   │
│  🔴 2 self-assessments overdue                               │
│                                                              │
│  GOAL TRACKING                                               │
│  ├─ 2026 goals set: 180/247 (73%)                           │
│  └─ Q4 2025 goal check-ins: 85% complete                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Performance Review Cycle

| Phase | Timeline | HR Actions |
|-------|----------|------------|
| Launch | Dec 1 | Configure forms, communicate |
| Self-Assessment | Dec 1-15 | Monitor completion |
| Manager Review | Dec 15-31 | Support managers |
| Calibration | Jan 1-15 | Facilitate sessions |
| Delivery | Jan 15-31 | Track completion |
| Close | Feb 1 | Finalize records |

### Managing Review Forms

Configure review forms:

1. Go to **Performance → Settings → Forms**
2. Create or edit form
3. Add sections:
   - Goals review
   - Competencies
   - Development areas
   - Manager comments
   - Rating scale
4. Set workflow (self → manager → skip-level)

### Calibration Sessions

Facilitate fair ratings:

```
CALIBRATION SESSION - Operations Department
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  RATING DISTRIBUTION (Before Calibration)                    │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Rating         │ Count │ % of Dept │ Target %          │ │
│  ├────────────────┼───────┼───────────┼───────────────────┤ │
│  │ Exceptional    │ 12    │ 20%       │ 10%               │ │
│  │ Exceeds        │ 25    │ 42%       │ 25%               │ │
│  │ Meets          │ 18    │ 30%       │ 50%               │ │
│  │ Developing     │ 5     │ 8%        │ 10%               │ │
│  │ Below          │ 0     │ 0%        │ 5%                │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  [View Employee List] [Adjust Ratings] [Finalize]           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Performance Improvement Plans (PIPs)

Track PIPs:

1. Manager initiates PIP
2. HR reviews and approves
3. Define:
   - Performance gaps
   - Expectations
   - Timeline (30-90 days)
   - Support provided
   - Consequences
4. Track progress
5. Close or escalate

---

## 10. Training & Development

### Training Dashboard

Access: **HR → Training**

```
TRAINING DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  COMPLIANCE STATUS                                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Training              │ Complete │ Due Soon │ Overdue  │ │
│  ├───────────────────────┼──────────┼──────────┼──────────┤ │
│  │ Safety Orientation    │ 247      │ 0        │ 0        │ │
│  │ Harassment Prevention │ 240      │ 5        │ 2        │ │
│  │ Cybersecurity         │ 235      │ 8        │ 4        │ │
│  │ Quality Basics        │ 220      │ 15       │ 12       │ │
│  └───────────────────────┴──────────┴──────────┴──────────┘ │
│                                                              │
│  CERTIFICATIONS EXPIRING (Next 30 Days)                      │
│  ├─ Forklift: 3 employees                                   │
│  ├─ First Aid: 2 employees                                  │
│  └─ LOTO: 3 employees                                       │
│                                                              │
│  TRAINING REQUESTS                                           │
│  ├─ 5 pending manager approval                              │
│  └─ 3 pending HR approval (external)                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Required Training Matrix

Define training requirements by role:

```
TRAINING REQUIREMENTS MATRIX
┌─────────────────────────────────────────────────────────────┐
│ Training              │ All │ Ops │ Qual │ Maint │ Mgmt    │
├───────────────────────┼─────┼─────┼──────┼───────┼─────────┤
│ Safety Orientation    │ ✓   │ ✓   │ ✓    │ ✓     │ ✓       │
│ Harassment Prevention │ ✓   │ ✓   │ ✓    │ ✓     │ ✓       │
│ Quality Basics        │     │ ✓   │ ✓    │       │         │
│ LOTO                  │     │ ✓   │      │ ✓     │         │
│ First Aid             │     │ ★   │      │ ★     │ ★       │
│ Leadership Basics     │     │     │      │       │ ✓       │
└───────────────────────┴─────┴─────┴──────┴───────┴─────────┘
✓ = Required | ★ = Required for some roles
```

### Managing Training Records

View employee training history:

```
TRAINING RECORD - John Adams
┌─────────────────────────────────────────────────────────────┐
│ COMPLETED TRAINING                                           │
├─────────────────────────────────────────────────────────────┤
│ Course                  │ Completed  │ Expires  │ Status    │
│ Safety Orientation      │ Jan 2022   │ Never    │ ✓ Current │
│ Harassment Prevention   │ Nov 2025   │ Nov 2027 │ ✓ Current │
│ Quality Basics          │ Feb 2022   │ Never    │ ✓ Current │
│ CNC Level 1             │ Mar 2022   │ Never    │ ✓ Current │
│ Forklift                │ Jan 2025   │ Jan 2026 │ ⚠️ Expiring│
│ LOTO                    │ Jun 2024   │ Jun 2026 │ ✓ Current │
├─────────────────────────────────────────────────────────────┤
│ ASSIGNED (Not Complete)                                      │
│ Cybersecurity Refresh   │ Due: Jan 31│          │ 🔵 Pending│
└─────────────────────────────────────────────────────────────┘
```

### Certification Tracking

Track required certifications:

1. Define certification requirements
2. Record certification dates
3. Set expiration reminders
4. Track recertification
5. Report on compliance

---

## 11. Recruiting & Hiring

### Recruiting Dashboard

Access: **HR → Recruiting**

```
RECRUITING DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  OPEN REQUISITIONS                                           │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Req #    │ Position       │ Dept    │ Status │ Days    │ │
│  ├──────────┼────────────────┼─────────┼────────┼─────────┤ │
│  │ REQ-101  │ CNC Operator   │ Ops     │ Active │ 15      │ │
│  │ REQ-102  │ Quality Insp   │ Quality │ Active │ 8       │ │
│  │ REQ-103  │ Engineer       │ Eng     │ Draft  │ -       │ │
│  │ REQ-099  │ Supervisor     │ Ops     │ Offer  │ 32      │ │
│  └──────────┴────────────────┴─────────┴────────┴─────────┘ │
│                                                              │
│  PIPELINE SUMMARY                                            │
│  ├─ Total Candidates: 45                                    │
│  ├─ In Interview: 8                                         │
│  └─ Offers Pending: 2                                       │
│                                                              │
│  METRICS                                                     │
│  ├─ Avg Time to Fill: 28 days                               │
│  ├─ Offer Acceptance Rate: 85%                              │
│  └─ Source Effectiveness: Indeed 40%, Referral 35%          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Requisition Management

Create and manage job requisitions:

1. Click **+ New Requisition**
2. Fill out details:
   - Position title
   - Department
   - Hiring manager
   - Compensation range
   - Job requirements
   - Posting preferences
3. Route for approval
4. Post to job boards

### Candidate Tracking

Track candidates through pipeline:

```
CANDIDATE PIPELINE - REQ-101 (CNC Operator)
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ Applied (15)  Screen (8)  Interview (4)  Offer (1)  Hire    │
│ ●●●●●●●●●●●   ●●●●●●●●    ●●●●           ●          ○       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ Candidate      │ Stage     │ Rating │ Next Action │ Due     │
├────────────────┼───────────┼────────┼─────────────┼─────────┤
│ John Smith     │ Offer     │ ★★★★   │ Accept?     │ Jan 12  │
│ Maria Garcia   │ Interview │ ★★★★   │ Panel       │ Jan 14  │
│ David Chen     │ Interview │ ★★★    │ Technical   │ Jan 13  │
│ Sarah Wilson   │ Interview │ ★★★    │ Manager     │ Jan 15  │
│ Mike Johnson   │ Interview │ ★★     │ Decision    │ Jan 11  │
└────────────────┴───────────┴────────┴─────────────┴─────────┘
```

### Offer Management

Process offers:

1. Create offer in system
2. Generate offer letter
3. Set approval workflow
4. Send to candidate
5. Track acceptance
6. Initiate onboarding on accept

---

## 12. Organizational Management

### Organization Chart

Access: **HR → Organization**

```
ORGANIZATION CHART
┌─────────────────────────────────────────────────────────────┐
│                        ┌─────────────┐                       │
│                        │    CEO      │                       │
│                        │  A. Smith   │                       │
│                        └──────┬──────┘                       │
│              ┌─────────────┬──┴───────────┬─────────────┐   │
│        ┌─────┴─────┐ ┌─────┴─────┐ ┌──────┴─────┐ ┌─────┴──┐│
│        │    CFO    │ │    COO    │ │    VP      │ │   HR   ││
│        │  B. Jones │ │  C. Brown │ │  D. Davis  │ │  E. Wil││
│        └───────────┘ └─────┬─────┘ └────────────┘ └────────┘│
│                      ┌─────┴─────┐                           │
│                ┌─────┴────┐ ┌────┴─────┐                    │
│                │ Plant Mgr│ │ Qual Mgr │                    │
│                │ F. Garcia│ │ G. Lee   │                    │
│                └─────┬────┘ └──────────┘                    │
│              ┌───────┴───────┐                               │
│         ┌────┴───┐     ┌─────┴───┐                          │
│         │ Sup 1  │     │  Sup 2  │                          │
│         └────────┘     └─────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

### Department Management

Configure departments:

| Department | Manager | Headcount | Budget FTE |
|------------|---------|-----------|------------|
| Operations | F. Garcia | 120 | 125 |
| Quality | G. Lee | 25 | 28 |
| Maintenance | H. Kim | 15 | 15 |
| Engineering | I. Patel | 20 | 22 |
| HR | E. Williams | 8 | 8 |

### Position Management

Maintain positions:

1. Define job titles
2. Set pay grades
3. Map to org structure
4. Define requirements
5. Track incumbents vs. budgeted

### Reporting Structure

Manage reporting relationships:

- View direct reports
- Change supervisors
- Track span of control
- Identify gaps/issues

---

## 13. Compliance & Reporting

### Compliance Dashboard

Access: **HR → Compliance**

```
COMPLIANCE DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  I-9 COMPLIANCE                                              │
│  ├─ Active I-9s: 247                                        │
│  ├─ Reverification due (next 90 days): 5                    │
│  └─ Overdue: 0 ✓                                            │
│                                                              │
│  EEO / AFFIRMATIVE ACTION                                    │
│  ├─ EEO-1 filing: Due March 31                              │
│  └─ AAP update: Due December                                │
│                                                              │
│  REQUIRED POSTINGS                                           │
│  ├─ All federal postings current ✓                          │
│  └─ State postings current ✓                                │
│                                                              │
│  TRAINING COMPLIANCE                                         │
│  ├─ Sexual Harassment: 97% complete                         │
│  └─ Safety Training: 100% complete ✓                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Standard HR Reports

| Report | Purpose | Frequency |
|--------|---------|-----------|
| Headcount | Current employees | Monthly |
| Turnover | Terms and reasons | Monthly |
| Time to Fill | Recruiting efficiency | Monthly |
| Leave Usage | Leave patterns | Monthly |
| Training Compliance | Requirement status | Monthly |
| EEO Summary | Diversity metrics | Quarterly |
| Compensation Analysis | Pay equity | Annually |

### EEO Reporting

Generate EEO-1 report:

```
EEO-1 COMPONENT 1 - EMPLOYEE COUNTS
┌─────────────────────────────────────────────────────────────┐
│ Job Category        │ White │ Black │ Hispanic │ Asian │...│
├─────────────────────┼───────┼───────┼──────────┼───────┼───┤
│ Executive/Sr Mgmt   │   4   │   1   │    0     │   1   │...│
│ First/Mid Mgmt      │  12   │   3   │    2     │   2   │...│
│ Professionals       │  25   │   8   │    5     │  10   │...│
│ Technicians         │  15   │   5   │    8     │   3   │...│
│ Admin Support       │   8   │   4   │    6     │   2   │...│
│ Craft Workers       │  35   │  12   │   15     │   5   │...│
│ Operatives          │  30   │  15   │   20     │   8   │...│
│ Laborers            │  10   │   8   │   12     │   2   │...│
│ Service Workers     │   5   │   3   │    4     │   1   │...│
└─────────────────────┴───────┴───────┴──────────┴───────┴───┘
```

### Document Retention

HR documents are retained per policy:

| Document Type | Retention |
|---------------|-----------|
| Application materials | 3 years |
| I-9 | 3 years post-term |
| Payroll records | 7 years |
| Performance reviews | 7 years |
| Benefits records | 6 years |
| FMLA records | 3 years |

---

## 14. Employee Self-Service

### What Employees Can Do

Employees access self-service for:

| Feature | Capability |
|---------|------------|
| Personal Info | View, request changes |
| Pay Stubs | View, download |
| Leave Requests | Submit, view balance |
| Benefits | View enrollment |
| Training | Complete assigned |
| Time | View time records |
| Directory | Search colleagues |

### Supporting Self-Service

HR monitors self-service requests:

1. Change requests requiring approval
2. Questions/issues
3. System access problems

### Enabling Features

Configure what employees can access:

- Open enrollment periods
- Self-service information updates
- Leave request workflows
- Document access

---

## 15. HR Analytics

### HR Metrics Dashboard

Access: **HR → Analytics**

```
HR ANALYTICS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  KEY METRICS - 2026                                          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Metric           │ Current │ Target  │ Status           │ │
│  ├──────────────────┼─────────┼─────────┼──────────────────┤ │
│  │ Turnover Rate    │ 8.2%    │ <10%    │ ✓ On Target      │ │
│  │ Time to Fill     │ 28 days │ <30     │ ✓ On Target      │ │
│  │ Training Comp.   │ 94%     │ 100%    │ ⚠️ Watch          │ │
│  │ Employee Engage. │ 4.2/5   │ 4.0     │ ✓ Above Target   │ │
│  │ Absence Rate     │ 3.5%    │ <4%     │ ✓ On Target      │ │
│  └──────────────────┴─────────┴─────────┴──────────────────┘ │
│                                                              │
│  TURNOVER ANALYSIS                                           │
│  ├─ Voluntary: 6.5%                                         │
│  ├─ Involuntary: 1.7%                                       │
│  ├─ Top Reason: Better opportunity (35%)                    │
│  └─ Highest Dept: Operations (12%)                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Trend Analysis

View trends over time:

```
HEADCOUNT TREND - Last 12 Months
┌─────────────────────────────────────────────────────────────┐
│     │                                          260 ─ ─ ─    │
│ 260 │                                      ●───●───●        │
│     │                                  ●───●                │
│ 250 │                      ●───●───●───●                    │
│     │          ●───●───●───●                                │
│ 240 │ ●───●───●                                             │
│     └───────────────────────────────────────────────────────│
│       J   F   M   A   M   J   J   A   S   O   N   D         │
│                                                              │
│ Hires: 42 | Terms: 22 | Net Change: +20                     │
└─────────────────────────────────────────────────────────────┘
```

### Predictive Analytics

Use AI-powered insights:

- **Flight Risk**: Employees likely to leave
- **High Performers**: Promotion candidates
- **Skill Gaps**: Training needs
- **Succession Planning**: Leadership pipeline

---

## Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + E` | Employee search |
| `Ctrl + H` | HR Dashboard |
| `Ctrl + L` | Leave management |
| `Ctrl + /` | Global search |
| `F5` | Refresh |

### HR Checklist - Daily

```
□ Review pending approvals
□ Check attendance exceptions
□ Monitor onboarding tasks
□ Respond to employee questions
□ Review expiring certifications
```

### HR Checklist - Weekly

```
□ Leave balance review
□ Open position status
□ Training compliance check
□ Performance review tracking
□ HR metrics review
```

### Key Contacts

| Need | Contact |
|------|---------|
| Payroll questions | Finance |
| IT access | IT |
| Benefits questions | Benefits carrier |
| Legal | Legal counsel |
| Workers' comp | Insurance carrier |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Human Resources*
