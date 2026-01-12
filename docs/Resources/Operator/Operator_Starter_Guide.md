# Operator Starter Guide

## Sensei OS - Production Operator Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Your Operator Dashboard](#3-your-operator-dashboard)
4. [Clock In & Time Tracking](#4-clock-in--time-tracking)
5. [Work Orders & Job Execution](#5-work-orders--job-execution)
6. [Standard Work Instructions](#6-standard-work-instructions)
7. [Quality at Your Station](#7-quality-at-your-station)
8. [Andon - Getting Help](#8-andon---getting-help)
9. [Equipment & Tools](#9-equipment--tools)
10. [Material Handling](#10-material-handling)
11. [Safety First](#11-safety-first)
12. [Training & Skills](#12-training--skills)
13. [Communication](#13-communication)
14. [Continuous Improvement](#14-continuous-improvement)
15. [Quick Reference](#15-quick-reference)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- If you’re assigned work, focus on subtasks and mark them complete as you finish.
- Use story/issue comments to capture facts when blocked (what happened, when, and who you notified).
- Use wiki pages for quick reference runbooks when they’re provided by leads/engineering.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role as Operator

As a Production Operator, you are the **heart of manufacturing**. Every part you make matters. Sensei OS helps you:

- **Know what to work on** - Clear job queue and priorities
- **Do it right** - Easy access to work instructions
- **Flag problems fast** - One-touch Andon support
- **Track your progress** - Real-time production counting
- **Stay safe** - Safety information at your fingertips

### What You Can Do in Sensei

| Capability | Description |
|------------|-------------|
| View Jobs | See your work queue |
| Run Production | Start, complete, log production |
| Quality Checks | Perform and record inspections |
| Call for Help | Trigger Andon when you need support |
| View Instructions | Access standard work and drawings |
| Log Time | Clock in/out, log job time |
| Request Support | Material, maintenance, quality help |
| Improve | Submit Kaizen ideas |

### What Your Screen Looks Like

When you log in to your workstation:

```
┌─────────────────────────────────────────────────────────────┐
│              OPERATOR WORKSTATION                            │
│              Cell: CNC Mill 1 | John Smith                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   CURRENT JOB: JOB-1234                                     │
│   Part: ABC-123 (Widget Assembly)                           │
│   ┌────────────────────────────────────────────────────┐    │
│   │  Quantity Required: 50                              │    │
│   │  Completed: 32 ✓                                    │    │
│   │  Remaining: 18                                      │    │
│   │  ████████████████░░░░░░░░  64%                      │    │
│   └────────────────────────────────────────────────────┘    │
│                                                              │
│   [▶ Start]  [⏸ Pause]  [✓ Complete Part]  [🔴 Andon]       │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│   Next Up: JOB-1235 (20 pcs) | JOB-1236 (15 pcs)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Getting Started

### Your First Login

1. Go to the terminal at your workstation
2. Enter your username (usually your employee ID)
3. Enter your password
4. If prompted, set up MFA (follow the instructions)

### Setting Up Your Profile

First time? Complete these steps:

- [ ] Verify your name and photo
- [ ] Check your assigned work center
- [ ] Confirm notification preferences
- [ ] Take the Sensei basics training

### Logging Into Your Workstation

Some workstations use **badge login**:

1. Tap your badge on the reader
2. You're logged in!

Other workstations use **PIN login**:

1. Enter your 4-6 digit PIN
2. Press Enter

### Understanding Your Home Screen

Your home screen shows:

| Section | What It Shows |
|---------|---------------|
| Current Job | The job you're working on now |
| Progress | How many complete, how many to go |
| Actions | Buttons to control your work |
| Queue | Jobs coming up next |
| Messages | Important notifications |

---

## 3. Your Operator Dashboard

### Dashboard Overview

```
┌─────────────────────────────────────────────────────────────┐
│  👤 John Smith | Cell: CNC Mill 1 | Shift: Day              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MY SHIFT TODAY                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Parts Made  │  │ Efficiency  │  │ Quality     │         │
│  │    127      │  │    98%      │  │   100%      │         │
│  │ Target: 130 │  │ Target: 95% │  │ Target: 99% │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  CURRENT JOB                                                 │
│  ┌─────────────────────────────────────────────────┐        │
│  │ JOB-1234 | Part: ABC-123 | Op: 20 (Mill)       │        │
│  │ Progress: 32/50 | Due: Today 2:00 PM           │        │
│  │ [View Instructions] [Report Issue] [Complete]   │        │
│  └─────────────────────────────────────────────────┘        │
│                                                              │
│  UPCOMING                                                    │
│  • JOB-1235 - DEF-456 (20 pcs) - Due: Today 4 PM           │
│  • JOB-1236 - GHI-789 (15 pcs) - Due: Tomorrow             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Understanding Your Metrics

**Parts Made**: How many good parts you've completed this shift

**Efficiency**: Your actual time vs. standard time
- 100% = Right on target
- Above 100% = Faster than expected
- Below 95% = May need to investigate

**Quality**: Good parts vs. total parts
- 100% = No scrap or rework
- Target is usually 99%+

### Status Indicators

Look for these indicators on your dashboard:

| Indicator | Meaning |
|-----------|---------|
| 🟢 Green | On track |
| 🟡 Yellow | Watch - may need attention |
| 🔴 Red | Problem - needs action |
| ⏸ Paused | Job stopped temporarily |
| ⏳ Waiting | Waiting for material/setup |

---

## 4. Clock In & Time Tracking

### Clocking In

**Badge Clock-In**:
1. Tap badge at time clock (entry or workstation)
2. Screen shows "Clock In Successful"

**Manual Clock-In**:
1. Open Sensei at workstation
2. Click **Clock In**
3. Confirm

### Starting Work on a Job

When you begin working on a job:

1. Select the job from your queue
2. Click **Start** or **Begin Job**
3. Time starts tracking automatically

```
┌─────────────────────────────────────────────────────────────┐
│              START JOB                                       │
├─────────────────────────────────────────────────────────────┤
│  Job: JOB-1234                                               │
│  Part: ABC-123                                               │
│  Operation: 20 - CNC Mill                                    │
│                                                              │
│  What are you doing?                                         │
│  ○ Setup                                                     │
│  ● Production                                                │
│  ○ Inspection                                                │
│                                                              │
│                    [Start]                                   │
└─────────────────────────────────────────────────────────────┘
```

### Logging Time to Jobs

Sensei automatically tracks your time on jobs. You can:

- **Auto-track**: Time logs when you start/stop jobs
- **Manual entry**: If you forgot to start, enter manually

### Breaks

When taking a break:

1. Click **Pause** on current job
2. Select reason: **Break**
3. Take your break
4. When you return, click **Resume**

Your break time is tracked separately from production time.

### Clocking Out

At end of shift:

1. Complete or pause your current job
2. Click **Clock Out** or tap badge at time clock
3. Confirm any open time entries

---

## 5. Work Orders & Job Execution

### Your Job Queue

Your queue shows jobs in priority order:

```
MY JOB QUEUE
┌─────────────────────────────────────────────────────────────┐
│ Priority │ Job       │ Part    │ Qty │ Due       │ Status  │
├──────────┼───────────┼─────────┼─────┼───────────┼─────────┤
│ 1 ★      │ JOB-1234  │ ABC-123 │ 50  │ Today 2PM │ ▶ Active│
│ 2        │ JOB-1235  │ DEF-456 │ 20  │ Today 4PM │ ⏳ Queue │
│ 3        │ JOB-1236  │ GHI-789 │ 15  │ Tomorrow  │ ⏳ Queue │
│ 4        │ JOB-1237  │ JKL-012 │ 30  │ Tomorrow  │ ⏳ Queue │
└─────────────────────────────────────────────────────────────┘
```

**★ = Hot job** - This is top priority!

### Starting a Job

1. Click on the job in your queue
2. Review the job details
3. Make sure you have materials and tools
4. Click **Start**

### During the Job

While working:

- Complete parts one at a time or in batches
- Click **Log Production** to record completed parts
- Follow standard work instructions
- Perform quality checks as required

### Logging Production

After completing parts:

```
┌─────────────────────────────────────────────────────────────┐
│              LOG PRODUCTION                                  │
├─────────────────────────────────────────────────────────────┤
│  Good Parts:    [ 10 ]                                       │
│                                                              │
│  Scrap:         [  0 ]                                       │
│  Scrap Code:    [Not Applicable    ▼]                       │
│                                                              │
│  Rework:        [  0 ]                                       │
│  Rework Reason: [                  ▼]                       │
│                                                              │
│                    [Submit]                                  │
└─────────────────────────────────────────────────────────────┘
```

### Completing a Job

When all parts are done:

1. Log final production quantity
2. Perform final inspection if required
3. Click **Complete Job**
4. Confirm completion
5. Job moves to next operation

### If You Have a Problem

Don't struggle alone! If you encounter an issue:

- **Material problem** → Report and call for material support
- **Quality issue** → Stop production, call Andon
- **Equipment issue** → Report and call maintenance
- **Don't understand instructions** → Call supervisor

---

## 6. Standard Work Instructions

### Accessing Instructions

Every job has work instructions. To view them:

1. Open your current job
2. Click **Work Instructions** or **Standard Work**
3. Instructions display on screen

### Following Instructions

Instructions show you step-by-step:

```
┌─────────────────────────────────────────────────────────────┐
│  STANDARD WORK: CNC Mill Operation                          │
│  Part: ABC-123 | Rev: 4.1                                   │
├─────────────────────────────────────────────────────────────┤
│  STEP 3 of 8: Load Part in Fixture                          │
│                                                              │
│  ┌───────────────────┐                                       │
│  │                   │                                       │
│  │     [Image:       │  1. Place part on fixture locators   │
│  │      Part in      │  2. Push down firmly until seated    │
│  │      Fixture]     │  3. Tighten clamps (2 turns)         │
│  │                   │  4. Verify part is flat against base │
│  │                   │                                       │
│  └───────────────────┘                                       │
│                                                              │
│  ⚠️ CAUTION: Do not over-tighten clamps                     │
│                                                              │
│  [◀ Previous]          [3/8]          [Next Step ▶]         │
│                                                              │
│  [📹 Video] [📐 Drawing] [🔍 Zoom Image]                     │
└─────────────────────────────────────────────────────────────┘
```

### Key Elements in Instructions

| Element | What It Means |
|---------|---------------|
| ⚠️ CAUTION | Be careful here |
| 🛑 STOP | Critical check before proceeding |
| 📷 Photo | Visual example to follow |
| 📹 Video | Click to watch demonstration |
| 📐 Drawing | Reference drawing available |
| ✓ Checkpoint | You must verify this |

### If Instructions Are Unclear

If you don't understand an instruction:

1. **Do not guess** - Stop and ask
2. Click **Request Clarification** on the instruction
3. Describe what's unclear
4. Wait for support (Andon if urgent)

### Suggesting Improvements

If you know a better way:

1. Click **Suggest Improvement** on any instruction
2. Describe your idea
3. Your supervisor will review it
4. Good ideas get implemented!

---

## 7. Quality at Your Station

### First Piece Inspection

Before running production, verify the first piece:

1. Complete setup
2. Make one part
3. Perform all required checks
4. Click **First Piece Inspection**
5. Enter measurements
6. If PASS → Begin production
7. If FAIL → Adjust and re-run first piece

```
FIRST PIECE INSPECTION
┌─────────────────────────────────────────────────────────────┐
│ Part: ABC-123 | Job: JOB-1234                                │
├─────────────────────────────────────────────────────────────┤
│ Dimension         │ Spec        │ Actual  │ Result          │
├───────────────────┼─────────────┼─────────┼─────────────────┤
│ Diameter A        │ 1.000 ±.005 │ 1.002   │ ✓ PASS          │
│ Length B          │ 2.500 ±.010 │ 2.498   │ ✓ PASS          │
│ Hole Depth C      │ 0.500 ±.003 │ 0.501   │ ✓ PASS          │
├───────────────────┴─────────────┴─────────┴─────────────────┤
│                 All checks PASS                              │
│                                                              │
│ Supervisor Approval: [Request Approval]                      │
│                                                              │
│               [Cancel]    [Submit & Start Production]        │
└─────────────────────────────────────────────────────────────┘
```

### In-Process Checks

During production, you'll be prompted for quality checks:

- **Every X parts** (e.g., every 10th part)
- **At random times**
- **After any adjustment**

When prompted:

1. Stop and measure the part
2. Enter the readings
3. If PASS → Continue
4. If FAIL → Stop and call for help

### Using Measuring Equipment

The system tracks which gauges you use:

1. Scan gauge barcode (if applicable)
2. Enter measurements
3. System records gauge used

### When You Find a Defect

If you find a bad part:

1. **Stop production immediately**
2. **Separate the bad part** - Put in red bin or tag
3. **Check previous parts** - Look back in your completed work
4. **Call Andon** - Get help from Quality or Supervisor
5. **Log the NC** if asked to

### Quality Mindset

Remember:
- **Quality is your responsibility**
- **If in doubt, ask**
- **It's better to stop than make bad parts**
- **Every defect you catch saves money**

---

## 8. Andon - Getting Help

### What is Andon?

Andon is your **"help" button**. When you have a problem you can't solve in 1-2 minutes, call Andon.

### When to Use Andon

| Situation | Andon Type |
|-----------|------------|
| Equipment problem | 🔴 Red |
| Quality issue / defect found | 🟡 Yellow |
| Need material | 🔵 Blue |
| Question / need support | ⚪ White |
| Safety concern | 🔴 Red |

### How to Trigger Andon

**Button Method** (if you have a physical Andon button):
1. Press the button at your station
2. Select reason on screen (if prompted)

**Screen Method**:
1. Click **🔴 Andon** on your dashboard
2. Select type:

```
┌─────────────────────────────────────────────────────────────┐
│              CALL ANDON                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Why do you need help?                                      │
│                                                              │
│   [🔴 Machine Down]     [🟡 Quality Issue]                  │
│                                                              │
│   [🔵 Need Material]    [⚪ Support/Question]                │
│                                                              │
│   [🔴 Safety Concern]                                        │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│   Brief description (optional):                              │
│   [Tool broke during operation                         ]     │
│                                                              │
│                    [Submit Andon]                            │
└─────────────────────────────────────────────────────────────┘
```

### After You Call Andon

1. **Wait for response** - Help is on the way
2. **Don't try to fix complex problems yourself**
3. **Continue safe work** if possible (other tasks)
4. **When help arrives**, explain the issue
5. **Once resolved**, the Andon is closed

### Andon Response Times

| Type | Expected Response |
|------|-------------------|
| Safety / Red | Immediate |
| Quality / Yellow | < 5 minutes |
| Material / Blue | < 10 minutes |
| Support / White | < 15 minutes |

### Don't Be Afraid to Use Andon

- **It's there to help you**
- **You won't get in trouble for calling**
- **The sooner you call, the faster we fix it**
- **Trying to hide problems makes them worse**

---

## 9. Equipment & Tools

### Pre-Start Checks

Before starting your machine each shift:

1. Open **Equipment → Daily Check**
2. Complete the checklist:

```
DAILY EQUIPMENT CHECK - CNC Mill 1
┌─────────────────────────────────────────────────────────────┐
│ Check                              │ Status                 │
├────────────────────────────────────┼────────────────────────┤
│ Oil level OK                       │ ☑ OK  ☐ Not OK        │
│ Coolant level OK                   │ ☑ OK  ☐ Not OK        │
│ No unusual noises                  │ ☑ OK  ☐ Not OK        │
│ Safety guards in place             │ ☑ OK  ☐ Not OK        │
│ Work area clean                    │ ☑ OK  ☐ Not OK        │
│ Emergency stop works               │ ☑ OK  ☐ Not OK        │
├────────────────────────────────────┴────────────────────────┤
│                    [Submit Check]                            │
└─────────────────────────────────────────────────────────────┘
```

If anything is Not OK, the system alerts maintenance.

### Reporting Equipment Issues

If your equipment has a problem:

1. Call Andon if urgent
2. Or go to **Equipment → Report Issue**
3. Describe the problem
4. Maintenance is notified

### Tool Management

Some tools are tracked in Sensei:

**Checking Out a Tool**:
1. Go to tool crib or scan toolbox
2. Scan the tool barcode
3. Tool is logged to you

**Returning a Tool**:
1. Scan the tool
2. Select "Return"
3. Report if damaged

### Calibrated Gauges

Some gauges require calibration tracking:

- Check the calibration sticker
- If expired, do not use
- Report expired gauges

---

## 10. Material Handling

### Getting Your Materials

Before starting a job, gather materials:

1. View job → **Materials** tab
2. See what's needed:

```
MATERIALS NEEDED - JOB-1234
┌─────────────────────────────────────────────────────────────┐
│ Item              │ Qty Needed │ Location   │ Status        │
├───────────────────┼────────────┼────────────┼───────────────┤
│ Raw Bar 1" x 12"  │ 50 pcs     │ Rack A-12  │ ✓ Available   │
│ Fastener Kit #456 │ 50 kits    │ Bin B-23   │ ✓ Available   │
│ Insert ABC        │ 2 pcs      │ Tool Crib  │ ⚠️ Low Stock  │
└─────────────────────────────────────────────────────────────┘
```

3. Go to location and pick materials
4. Scan or confirm materials picked

### Material Shortages

If material isn't available:

1. Check if there's a substitute
2. If not, call Andon (Blue - Material)
3. Material handler will be notified
4. Do not use wrong material!

### Tracking Material Usage

When you complete parts:

- Good parts → Material consumed automatically
- Scrap → System tracks wasted material

### Returning Unused Material

At end of job:

1. Count remaining material
2. Return to proper location
3. Log in system if required

---

## 11. Safety First

### Your Safety Responsibilities

- **Follow all safety procedures**
- **Wear required PPE**
- **Report hazards immediately**
- **Never bypass safety devices**
- **Keep work area clean**

### Required PPE at Your Station

Check your work area for required PPE:

```
PPE REQUIREMENTS - CNC Mill Area
┌─────────────────────────────────────────────────────────────┐
│  ✓ Safety Glasses (Required at all times)                   │
│  ✓ Steel-Toed Shoes                                         │
│  ✓ Hearing Protection (When machines running)               │
│  ○ Gloves (NOT during machine operation)                    │
│  ○ Face Shield (When grinding)                              │
└─────────────────────────────────────────────────────────────┘
```

### Reporting Safety Hazards

If you see something unsafe:

1. **If immediate danger** → Stop work, move away, alert others
2. **If not immediate** → Report in Sensei:
   - Click **Safety → Report Hazard**
   - Describe what you saw
   - Add photo if possible

### Lockout/Tagout (LOTO)

Before working on equipment:

1. Only do LOTO if trained and authorized
2. Follow the LOTO procedure exactly
3. Verify energy isolation
4. Never remove someone else's lock

### Emergency Procedures

Know your:
- **Emergency exits**
- **Assembly point**
- **Fire extinguisher locations**
- **First aid kit location**
- **Emergency contact numbers**

If emergency occurs:
1. Sound alarm if needed
2. Stop equipment if safe
3. Evacuate following posted routes
4. Account for all personnel

---

## 12. Training & Skills

### Your Skills & Certifications

View your training status:

**My Skills → Training Status**

```
MY TRAINING STATUS
┌─────────────────────────────────────────────────────────────┐
│ Training                 │ Status    │ Valid Until          │
├──────────────────────────┼───────────┼──────────────────────┤
│ Safety Orientation       │ ✓ Current │ No expiry            │
│ CNC Mill - Level 1       │ ✓ Current │ No expiry            │
│ CNC Mill - Level 2       │ ✓ Current │ No expiry            │
│ Quality Basics           │ ✓ Current │ No expiry            │
│ Forklift                 │ ⚠️ Expiring│ Feb 15, 2026         │
│ Lockout/Tagout           │ ✓ Current │ Jun 30, 2026         │
└─────────────────────────────────────────────────────────────┘
```

### Completing Assigned Training

When training is assigned:

1. You'll receive a notification
2. Go to **Training → My Courses**
3. Click on the course
4. Complete all modules
5. Pass the quiz (if applicable)
6. Certificate is logged

### Requesting Training

Want to learn something new?

1. Go to **Training → Request**
2. Select the skill or course
3. Add why you want it
4. Your supervisor reviews

### On-the-Job Training (OJT)

Some skills are learned hands-on:

1. Trainer works with you
2. You practice with supervision
3. Trainer logs your progress in Sensei
4. Once proficient, you're signed off

---

## 13. Communication

### Viewing Messages

Check your messages regularly:

```
MY MESSAGES
┌─────────────────────────────────────────────────────────────┐
│ From           │ Subject                   │ Time           │
├────────────────┼───────────────────────────┼────────────────┤
│ Supervisor     │ Hot job priority change   │ 10:32 AM       │
│ Quality        │ Inspection reminder       │ 9:15 AM        │
│ HR             │ Timesheet approval needed │ Yesterday      │
│ Maintenance    │ Machine fixed - back up   │ Yesterday      │
└─────────────────────────────────────────────────────────────┘
```

### Sending Messages

To message someone:

1. Click **Messages → New**
2. Search for the person
3. Type your message
4. Send

### Shift Announcements

Important announcements appear on your dashboard. Read them!

Types of announcements:
- **Safety alerts** 🔴
- **Schedule changes** 🟡
- **General info** 🔵
- **Recognition** ⭐

### Daily Huddle

Your supervisor may run a daily huddle. Participate by:

- Sharing problems from yesterday
- Mentioning what you need today
- Bringing up safety observations
- Suggesting improvements

---

## 14. Continuous Improvement

### Submitting Kaizen Ideas

You know your job best! Share your ideas:

1. Go to **Kaizen → New Idea**
2. Fill out the form:

```
┌─────────────────────────────────────────────────────────────┐
│              KAIZEN SUGGESTION                               │
├─────────────────────────────────────────────────────────────┤
│ Area/Process:   [CNC Mill Setup             ]                │
│                                                              │
│ Current Problem:                                             │
│ [Takes 5 minutes to find correct collet each time     ]     │
│                                                              │
│ Your Suggestion:                                             │
│ [Add labeled slots above machine for each collet size ]     │
│                                                              │
│ Expected Benefit:                                            │
│ [Save 4 minutes per setup, prevent using wrong collet ]     │
│                                                              │
│ Photo (optional): [📷 Add Photo]                             │
│                                                              │
│                    [Submit Idea]                             │
└─────────────────────────────────────────────────────────────┘
```

3. Submit and track status
4. Implemented ideas may earn recognition!

### Kaizen Idea Status

Track your ideas:

| Status | Meaning |
|--------|---------|
| Submitted | Under review |
| Approved | Will be implemented |
| In Progress | Being worked on |
| Implemented | Done! |
| Recognized | You're awarded! |

### Participating in Improvements

You may be asked to join improvement activities:

- **5S Events**: Organize your work area
- **Kaizen Events**: Rapid improvement workshops
- **Standard Work Updates**: Help improve instructions
- **Problem Solving**: Contribute to root cause analysis

Your participation matters!

---

## 15. Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Spacebar` | Log 1 good part |
| `Enter` | Confirm action |
| `Esc` | Cancel / Close dialog |
| `F1` | Help |
| `F5` | Refresh screen |

### Status Icons Cheat Sheet

| Icon | Meaning |
|------|---------|
| ✓ | Complete / Good |
| ⚠️ | Warning / Attention needed |
| 🔴 | Problem / Stop |
| 🟢 | Running / Good |
| 🟡 | Caution / In progress |
| ⏸ | Paused |
| ⏳ | Waiting / Queue |
| ★ | Priority / Hot |

### Daily Operator Checklist

```
START OF SHIFT
□ Clock in
□ Check messages/announcements  
□ Review job queue
□ Complete equipment daily check
□ Gather materials
□ Start first job

DURING SHIFT
□ Follow standard work
□ Log production regularly
□ Complete quality checks
□ Call Andon when needed
□ Keep area clean

END OF SHIFT
□ Complete/pause current job
□ Log final production
□ Return tools
□ Clean work area
□ Handover notes if needed
□ Clock out
```

### Who to Contact

| Need | Contact |
|------|---------|
| Production question | Your Supervisor |
| Quality issue | Quality / Supervisor |
| Equipment problem | Maintenance (via Andon) |
| Material shortage | Material Handler (via Andon) |
| Time off / HR question | Supervisor → HR |
| Training | Supervisor |
| Safety concern | Supervisor / Safety |

### Emergency Numbers

| Emergency | Contact |
|-----------|---------|
| Medical | ext. 5555 |
| Fire | ext. 5911 |
| Spill | ext. 5000 |
| Security | ext. 5000 |

---

## Remember

> **"Quality at the source, safety first, continuous improvement always."**

You are the most important part of our manufacturing process. Sensei OS is here to support you, not replace you. Use it to:

- Know what to do
- Do it right
- Get help fast
- Track your success
- Make things better

If you have questions, ask your supervisor. If something in Sensei doesn't work, report it.

**Welcome to the team!**

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Operations*
