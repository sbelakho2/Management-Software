# User Guide

Complete guide to using Starz Morocco Manufacturing Management System.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Dashboard Overview](#dashboard-overview)
- [Managing Opportunities](#managing-opportunities)
- [RFQ Process](#rfq-process)
- [Creating Quotes](#creating-quotes)
- [Quality Management](#quality-management)
- [Obeya Room](#obeya-room)
- [A3 Problem Solving](#a3-problem-solving)
- [Training & Skills](#training--skills)
- [Today Screen](#today-screen)
- [Settings & Profile](#settings--profile)

## 🚀 Getting Started

### Logging In

1. Navigate to your URL (e.g., `https://app.flopsen.tech`)
2. Enter your email and password
3. Click "Sign In"

**First Time Login**:
- You'll receive a welcome email with temporary credentials
- Change your password on first login
- Set up two-factor authentication (recommended)

### Dashboard Overview

After logging in, you'll see the main dashboard with:

- **Quick Stats**: Open opportunities, pending RFQs, active quotes
- **Recent Activity**: Latest updates across the system
- **My Tasks**: Tasks assigned to you
- **Upcoming Deadlines**: Important dates and milestones
- **Quick Actions**: Common tasks (Create RFQ, New Quote, etc.)

### Navigation

**Sidebar Menu**:
- 🏠 **Dashboard** - Main overview
- 📊 **Pipeline** - Opportunity management
- 📝 **RFQs** - Request for Quotes
- 💰 **Quotes** - Quote management
- 📦 **Products** - Product catalog
- ✅ **Quality** - Quality inspections
- 🎯 **Obeya** - Project management
- 🔍 **A3** - Problem solving
- 📚 **Training** - Skills & training

**Command Palette** (⌘K or Ctrl+K):
- Quick search across all entities
- Navigate to any page
- Execute common actions

## 📊 Managing Opportunities

### Creating an Opportunity

1. Click **Pipeline** in sidebar
2. Click **New Opportunity** button
3. Fill in required fields:
   - **Name**: Project or part name
   - **Account**: Customer name
   - **Value**: Estimated annual revenue
   - **Stage**: Current stage in pipeline
   - **Close Date**: Expected decision date
4. Add optional details:
   - **Description**: Project details
   - **Next Step**: Next action item
   - **Probability**: Win probability (%)
   - **Tags**: Categorization tags
5. Click **Create Opportunity**

### Pipeline Stages

**Default Stages**:
1. **Prospecting** - Initial contact
2. **Qualification** - Needs assessment
3. **RFQ** - Request for quote received
4. **Quoting** - Preparing quote
5. **Negotiation** - Discussing terms
6. **Won** - Deal closed successfully
7. **Lost** - Deal lost (with reason)

**Moving Opportunities**:
- Drag and drop between stages (Kanban view)
- Or use dropdown in detail view
- Add notes when changing stages

### Opportunity Details

Click any opportunity to view:
- **Overview**: Key information and metrics
- **Activities**: Timeline of all actions
- **RFQs**: Associated RFQs
- **Quotes**: Quotes generated
- **Tasks**: Related tasks
- **Files**: Attached documents
- **Notes**: Discussion and updates

### Filtering & Sorting

**Filter By**:
- Stage (dropdown)
- Owner (team member)
- Account (customer)
- Value range
- Date range
- Tags

**Sort By**:
- Value (high to low)
- Close date (nearest first)
- Probability (% win)
- Last updated

## 📝 RFQ Process

### Creating an RFQ

1. Navigate to **RFQs** page
2. Click **New RFQ**
3. Select or create **Account** (customer)
4. Link to **Opportunity** (optional)
5. Fill in RFQ details:
   - **Title**: Brief description
   - **Due Date**: When quote is needed
   - **Priority**: High/Medium/Low
   - **Requirements**: Detailed specifications
6. Add **Questions** for customer clarification
7. Upload **Attachments** (drawings, specs)
8. Click **Create RFQ**

### RFQ Workflow

**Stages**:
1. **Draft** - Initial creation, not submitted
2. **Submitted** - Sent to customer
3. **In Review** - Customer reviewing
4. **Answered** - Customer responded
5. **Ready for Quote** - All info gathered
6. **Quoted** - Quote generated
7. **Closed** - Process complete

### RFQ Completeness Check

System automatically checks:
- ✅ Required fields completed
- ✅ Technical specifications provided
- ✅ All questions answered
- ✅ Drawings/specs attached

**Completeness Score**: 0-100%
- <50%: Incomplete (red)
- 50-79%: Partial (yellow)
- 80-100%: Complete (green)

### Requesting Missing Information

1. Open RFQ detail page
2. Click **Request Info** button
3. System generates email with missing items
4. Email sent to customer contact
5. Task created to follow up

## 💰 Creating Quotes

### Quote Builder

1. Navigate to **Quotes** page
2. Click **New Quote**
3. Select **Account** and **RFQ**
4. Add **Line Items**:
   - Search for product or create custom item
   - Enter quantity
   - Set unit price
   - Add notes/assumptions
5. Review **Totals**:
   - Subtotal
   - Tax (if applicable)
   - Shipping
   - Total
6. Add **Terms & Conditions**
7. Add **Assumptions** (important!)
8. Click **Save Draft**

### Quote Versions

Every quote can have multiple versions:

**Creating New Version**:
1. Open existing quote
2. Click **New Version**
3. Modify pricing or items
4. Save with version notes

**Version History**:
- All versions preserved
- Compare versions side-by-side
- See what changed between versions

### Quote Approval Workflow

**Approval Thresholds** (configurable by admin):
- Under $10K: Auto-approved
- $10K - $50K: Manager approval
- $50K - $100K: Director approval
- Over $100K: VP approval

**Approval Process**:
1. Submit quote for approval
2. Approvers notified via email
3. Approvers review and approve/reject
4. If rejected, add comments and resubmit
5. Once approved, quote is locked

### Generating Quote PDF

1. Open approved quote
2. Click **Generate PDF**
3. PDF includes:
   - Company branding
   - Quote details
   - Line items with pricing
   - Terms & conditions
   - Assumptions
   - Signature block
4. Download or email to customer

### Supplier Quotes

For parts you need to source:

1. Click **Add Supplier Quote**
2. Select supplier
3. Enter supplier's pricing
4. Add lead time
5. Track multiple supplier quotes
6. Compare pricing automatically

## ✅ Quality Management

### Inspections

**Creating Inspection Plan**:
1. Navigate to **Quality** > **Inspections**
2. Click **New Inspection Plan**
3. Select product or part
4. Define inspection points:
   - Dimension/characteristic
   - Specification/tolerance
   - Measurement method
   - Sample size
5. Set inspection frequency
6. Assign inspector

**Recording Inspection**:
1. Open inspection plan
2. Click **Record Inspection**
3. Enter measurements
4. Mark pass/fail
5. Add photos (optional)
6. Submit inspection record

### Non-Conformances (NCRs)

**Creating NCR**:
1. Click **Quality** > **Non-Conformances**
2. Click **New NCR**
3. Fill in details:
   - Part/product affected
   - Defect description
   - Quantity affected
   - Severity (Critical/Major/Minor)
   - Root cause (initial assessment)
4. Upload photos
5. Submit NCR

**NCR Workflow**:
1. **Open** - NCR created
2. **Under Review** - Quality team reviewing
3. **Disposition** - Decide action (rework/scrap/use-as-is)
4. **In Progress** - Corrective action underway
5. **Closed** - Resolved and verified

### CAPA (Corrective & Preventive Action)

**Creating CAPA**:
1. From NCR, click **Create CAPA**
2. Or navigate to **Quality** > **CAPA**
3. Define:
   - Problem statement
   - Root cause analysis
   - Containment action (immediate)
   - Corrective action (fix)
   - Preventive action (prevent recurrence)
4. Assign owner and due date
5. Submit CAPA

**CAPA Actions**:
- Track multiple action items
- Assign to team members
- Set deadlines
- Verify effectiveness

## 🎯 Obeya Room

Digital "war room" for project management.

### Creating Obeya Board

1. Navigate to **Obeya**
2. Click **New Board**
3. Enter board name (project name)
4. Add team members
5. Click **Create**

### Obeya Items

**Types of Items**:
- 🎯 **Milestone** - Key project milestone
- 📋 **Action Item** - Task to complete
- 🔴 **Issue** - Problem blocking progress
- 💡 **Idea** - Improvement suggestion
- 📊 **Metric** - KPI to track

**Adding Items**:
1. Click **Add Item**
2. Select type
3. Fill in details:
   - Title
   - Description
   - Owner
   - Due date
   - Status
4. Click **Add**

### Obeya Meetings

**Running Obeya Meeting**:
1. Open Obeya board
2. Click **Start Meeting**
3. Review each item:
   - Update status
   - Add comments
   - Assign actions
   - Update timeline
4. Click **End Meeting**
5. Meeting notes auto-generated

### Visual Management

**Board Layout**:
- **Top Row**: Project timeline
- **Left Column**: Key metrics
- **Center**: Items by status
- **Right Column**: Team roster

**Status Colors**:
- 🟢 **Green** - On track
- 🟡 **Yellow** - At risk
- 🔴 **Red** - Behind/blocked

## 🔍 A3 Problem Solving

Structured problem-solving using A3 methodology.

### Creating an A3

1. Navigate to **A3**
2. Click **New A3**
3. Select trigger:
   - Manual (general problem)
   - From Andon event
   - From quality issue
   - From missed metric
4. Enter problem title
5. Click **Create**

### A3 Sections

**1. Background**
- What is the problem?
- Why is it important?
- Current state data

**2. Current Condition**
- Detailed analysis
- Data and charts
- Process flow

**3. Goal/Target Condition**
- What does success look like?
- Measurable targets
- Timeline

**4. Root Cause Analysis**
- 5 Whys technique
- Fishbone diagram
- Failure mode analysis

**5. Countermeasures**
- Proposed solutions
- Action plan
- Owners and deadlines

**6. Implementation Plan**
- Step-by-step plan
- Resources needed
- Timeline with milestones

**7. Follow-Up**
- Verification of results
- Lessons learned
- Standard work updates

### A3 Workflow

1. **Draft** - Creating A3
2. **In Progress** - Implementing countermeasures
3. **Verification** - Checking effectiveness
4. **Closed** - Completed and documented

### Collaboration

- Add team members as contributors
- Comment on sections
- @mention people for input
- Attach supporting documents
- Link related A3s

## 📚 Training & Skills

### Training Matrix

View your team's skills:

1. Navigate to **Training**
2. View **Training Matrix** tab
3. See:
   - Employees (rows)
   - Skills (columns)
   - Proficiency levels (colors)

**Proficiency Levels**:
- ⚪ **None** - No training
- 🔵 **Trained** - Basic knowledge
- 🟢 **Competent** - Can work independently
- 🟡 **Proficient** - Expert level
- 🟠 **Trainer** - Can train others

### Recording Training

**As Manager**:
1. Click **Record Training**
2. Select employee
3. Select skill
4. Enter training details:
   - Date completed
   - Trainer name
   - Proficiency achieved
   - Certification (if applicable)
5. Upload certificate
6. Click **Save**

**As Employee**:
1. View **My Training** tab
2. See completed training
3. See upcoming requirements
4. Request additional training

### Skills Gap Analysis

System automatically identifies:
- Required skills for job role
- Current skill levels
- Gaps to address
- Recommended training

### Certification Tracking

- Track certification expiration dates
- Automatic renewal reminders
- Upload certification documents
- Maintain compliance

## 📅 Today Screen

Daily operational dashboard for managers.

### What's on Today Screen

**Key Sections**:
1. **Top Priorities** - Most urgent items
2. **Production Status** - Shop floor summary
3. **Quality Alerts** - Recent issues
4. **Pending Approvals** - Items needing your approval
5. **Team Status** - Your direct reports
6. **Andon Events** - Active alerts
7. **Daily Metrics** - KPI snapshot

### Leader Standard Work (LSW)

Daily checklist for managers:

**Morning Routine**:
- [ ] Review production schedule
- [ ] Check quality metrics
- [ ] Review open A3s
- [ ] Check inventory levels
- [ ] Review safety incidents

**Afternoon Routine**:
- [ ] Production status update
- [ ] Review training compliance
- [ ] Check open tasks
- [ ] Update Obeya board

**End of Day**:
- [ ] Complete daily report
- [ ] Review tomorrow's schedule
- [ ] Address open issues

### Daily Snapshot

At end of day, system generates:
- PDF summary of key metrics
- Issues encountered
- Actions taken
- Follow-up items
- Auto-emailed to stakeholders

## ⚙️ Settings & Profile

### User Profile

1. Click profile icon (top right)
2. Select **Profile**
3. Update:
   - Name
   - Email
   - Phone
   - Department
   - Role
4. Change password
5. Upload profile photo

### Notification Settings

Control what notifications you receive:

**Email Notifications**:
- [ ] Task assignments
- [ ] Approval requests
- [ ] Quality alerts
- [ ] Andon events
- [ ] A3 updates
- [ ] Daily digest

**In-App Notifications**:
- [ ] Real-time alerts
- [ ] Badge counts
- [ ] Sound notifications

### Two-Factor Authentication

**Enable 2FA**:
1. Go to **Security** settings
2. Click **Enable 2FA**
3. Scan QR code with authenticator app
4. Enter verification code
5. Save backup codes

**Disable 2FA**:
1. Go to **Security** settings
2. Click **Disable 2FA**
3. Enter current password
4. Confirm

### Theme & Display

**Dark Mode**:
- Toggle in settings
- Or use system preference

**Language**:
- Select preferred language
- English (default)
- Spanish
- French

**Accessibility**:
- High contrast mode
- Font size adjustment
- Keyboard shortcuts

## 📞 Getting Help

### In-App Help

- **Help Center** - Click ? icon
- **Tooltips** - Hover over fields
- **Guided Tours** - First-time user walkthroughs

### Support

- **Email**: contact@starzmorocco.com
- **Phone**: Coming soon
- **Live Chat**: Available 9am-5pm EST

### Training Resources

- **Video Tutorials**: https://docs.flopsen.tech/videos
- **Knowledge Base**: https://docs.flopsen.tech/kb
- **Webinars**: Weekly training sessions

---

**Need more help?** Contact your system administrator or email contact@starzmorocco.com
