# Finance / Accountant Starter Guide

## Sensei OS - Finance & Accounting Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Finance Dashboard](#3-finance-dashboard)
4. [General Ledger](#4-general-ledger)
5. [Accounts Payable (AP)](#5-accounts-payable-ap)
6. [Accounts Receivable (AR)](#6-accounts-receivable-ar)
7. [Cash Management](#7-cash-management)
8. [Period Close Process](#8-period-close-process)
9. [Fixed Assets](#9-fixed-assets)
10. [Cost Accounting](#10-cost-accounting)
11. [Budgeting & Forecasting](#11-budgeting--forecasting)
12. [Financial Reporting](#12-financial-reporting)
13. [Tax & Compliance](#13-tax--compliance)
14. [Audit Support](#14-audit-support)
15. [System Integration](#15-system-integration)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use milestones and due dates to understand delivery commitments that affect invoicing/cash timing.
- Track cost drivers and risk items via issues (especially recurring defect trends).
- Use the activity log when you need traceability for approvals or audit requests.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role in Finance

As a Finance/Accounting professional, you are the **financial steward** of the organization. Sensei OS empowers you to:

- **Maintain accurate records** through proper bookkeeping
- **Process transactions** efficiently and accurately
- **Close periods** on time with confidence
- **Generate reports** for decision-making
- **Ensure compliance** with regulations and standards
- **Support audits** with proper documentation

### Finance Capabilities by Role

| Capability | Staff Accountant | Finance Manager | Controller |
|------------|------------------|-----------------|------------|
| View GL | ✓ | ✓ | ✓ |
| Post Journals | ✓ | ✓ | ✓ |
| Approve Journals | - | ✓ | ✓ |
| AP Processing | ✓ | ✓ | ✓ |
| AP Payment Approval | - | ✓ | ✓ |
| AR Processing | ✓ | ✓ | ✓ |
| Credit Memos | ✓ | ✓ | ✓ |
| Period Close | Participate | Execute | ✓ |
| Reports | View | All | All |
| System Config | - | Limited | Full |
| Bank Reconciliation | ✓ | ✓ | ✓ |
| Budget Management | View | Edit | Full |

### Finance Module Overview

```
SENSEI OS FINANCE
├── General Ledger (GL)
│   ├── Chart of Accounts
│   ├── Journal Entries
│   └── Trial Balance
├── Accounts Payable (AP)
│   ├── Vendor Management
│   ├── Invoice Processing
│   └── Payment Processing
├── Accounts Receivable (AR)
│   ├── Customer Management
│   ├── Invoicing
│   └── Collections
├── Cash Management
│   ├── Bank Accounts
│   ├── Reconciliation
│   └── Cash Flow
├── Fixed Assets
│   ├── Asset Register
│   ├── Depreciation
│   └── Disposal
└── Reporting
    ├── Financial Statements
    ├── Management Reports
    └── Regulatory Reports
```

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter your credentials
3. Complete Multi-Factor Authentication (MFA)
4. Update your profile

### Initial Setup Tasks

- [ ] Verify your finance role permissions
- [ ] Review Chart of Accounts
- [ ] Understand period calendar
- [ ] Check approval workflows
- [ ] Set notification preferences

### Your Finance Home Screen

```
┌─────────────────────────────────────────────────────────────┐
│                 FINANCE DASHBOARD                            │
│                 Period: January 2026                        │
├─────────────────────────────────────────────────────────────┤
│  PERIOD STATUS                                               │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │ AP Open    │ │ AR Open    │ │ GL Entries │ │ Cash Pos   ││
│  │  $145,230  │ │  $287,450  │ │     23     │ │ $1.2M      ││
│  │  12 inv    │ │  18 inv    │ │  pending   │ │            ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘│
├─────────────────────────────────────────────────────────────┤
│  ACTION REQUIRED                                             │
│  🔴 3 invoices overdue for approval                          │
│  🟡 Bank reconciliation due: Checking account                │
│  🟡 Period close checklist: 75% complete                     │
│  🔵 Month-end journal entries: 5 pending                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Finance Dashboard

### Key Metrics

| Metric | Description | Your Role |
|--------|-------------|-----------|
| AP Aging | Outstanding payables | Monitor, process |
| AR Aging | Outstanding receivables | Monitor, follow up |
| Cash Position | Current cash balance | Manage cash flow |
| Period Status | Close progress | Complete tasks |

### Dashboard Widgets

#### AP Summary
```
ACCOUNTS PAYABLE SUMMARY
┌─────────────────────────────────────────────────────────────┐
│ Current       │ 1-30 Days   │ 31-60 Days │ 61-90 Days │ 90+│
│ $85,230       │ $42,100     │ $12,400    │ $3,500     │ $2K│
├─────────────────────────────────────────────────────────────┤
│ Total Open: $145,230 | Invoices: 45 | Due Today: 3         │
└─────────────────────────────────────────────────────────────┘
```

#### AR Summary
```
ACCOUNTS RECEIVABLE SUMMARY  
┌─────────────────────────────────────────────────────────────┐
│ Current       │ 1-30 Days   │ 31-60 Days │ 61-90 Days │ 90+│
│ $175,300      │ $78,200     │ $22,150    │ $8,800     │ $3K│
├─────────────────────────────────────────────────────────────┤
│ Total Open: $287,450 | Invoices: 68 | Overdue: 15          │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. General Ledger

### Chart of Accounts

Access: **Finance → GL → Chart of Accounts**

```
CHART OF ACCOUNTS
┌─────────────────────────────────────────────────────────────┐
│ Account     │ Description              │ Type    │ Status   │
├─────────────┼──────────────────────────┼─────────┼──────────┤
│ 1000        │ Cash - Operating         │ Asset   │ Active   │
│ 1010        │ Cash - Payroll           │ Asset   │ Active   │
│ 1100        │ Accounts Receivable      │ Asset   │ Active   │
│ 1200        │ Inventory - Raw Material │ Asset   │ Active   │
│ 1500        │ Fixed Assets             │ Asset   │ Active   │
│ 2000        │ Accounts Payable         │ Liab    │ Active   │
│ 2100        │ Accrued Expenses         │ Liab    │ Active   │
│ 3000        │ Common Stock             │ Equity  │ Active   │
│ 4000        │ Sales Revenue            │ Revenue │ Active   │
│ 5000        │ Cost of Goods Sold       │ Expense │ Active   │
│ 6000        │ Operating Expenses       │ Expense │ Active   │
└─────────────┴──────────────────────────┴─────────┴──────────┘
```

### Journal Entries

Access: **Finance → GL → Journal Entries**

#### Creating a Journal Entry

```
┌─────────────────────────────────────────────────────────────┐
│              NEW JOURNAL ENTRY                               │
├─────────────────────────────────────────────────────────────┤
│ Entry Date:      [01/11/2026    ]                           │
│ Entry Type:      [Standard       ▼]                         │
│ Reference:       [JE-2026-0234  ] (auto)                    │
│ Description:     [January rent accrual               ]      │
│                                                              │
│ LINES                                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Account │ Description    │ Debit    │ Credit  │ Dept   │ │
│ ├─────────┼────────────────┼──────────┼─────────┼────────┤ │
│ │ 6100    │ Rent Expense   │ 15,000   │         │ Admin  │ │
│ │ 2100    │ Accrued Expense│          │ 15,000  │        │ │
│ ├─────────┼────────────────┼──────────┼─────────┼────────┤ │
│ │         │ TOTALS         │ 15,000   │ 15,000  │ ✓ Bal  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Attachments: [📎 Add File]                                   │
│                                                              │
│ [Save Draft]  [Submit for Approval]  [Post] (if authorized) │
└─────────────────────────────────────────────────────────────┘
```

#### Journal Entry Types

| Type | Purpose | Approval |
|------|---------|----------|
| Standard | Normal entries | Manager for >$10K |
| Recurring | Monthly repeating | Setup approval |
| Adjusting | Period adjustments | Always |
| Reversing | Auto-reverse next period | Setup approval |
| Closing | Period close entries | Always |

### Trial Balance

View the trial balance:

```
TRIAL BALANCE
Period: January 2026 (Open)
┌─────────────────────────────────────────────────────────────┐
│ Account │ Description           │ Debit       │ Credit      │
├─────────┼───────────────────────┼─────────────┼─────────────┤
│ 1000    │ Cash - Operating      │ 1,247,500   │             │
│ 1100    │ Accounts Receivable   │   287,450   │             │
│ 1200    │ Inventory             │   425,000   │             │
│ 1500    │ Fixed Assets (net)    │   850,000   │             │
│ 2000    │ Accounts Payable      │             │   145,230   │
│ 2100    │ Accrued Expenses      │             │    85,000   │
│ 2500    │ Notes Payable         │             │   500,000   │
│ 3000    │ Equity                │             │ 1,500,000   │
│ 3500    │ Retained Earnings     │             │   425,720   │
│ 4000    │ Revenue               │             │   750,000   │
│ 5000    │ COGS                  │   412,500   │             │
│ 6000    │ Operating Expenses    │   183,500   │             │
├─────────┼───────────────────────┼─────────────┼─────────────┤
│         │ TOTALS                │ 3,405,950   │ 3,405,950   │
│         │                       │         ✓ BALANCED        │
└─────────┴───────────────────────┴─────────────┴─────────────┘
```

---

## 5. Accounts Payable (AP)

### AP Dashboard

Access: **Finance → AP**

```
ACCOUNTS PAYABLE DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  INVOICE STATUS                                              │
│  ├─ Open Invoices: 45 ($145,230)                            │
│  ├─ Pending Approval: 12 ($42,500)                          │
│  ├─ Ready to Pay: 28 ($87,230)                              │
│  └─ On Hold: 5 ($15,500)                                    │
│                                                              │
│  UPCOMING PAYMENTS                                           │
│  ├─ Due Today: $23,450 (3 invoices)                         │
│  ├─ Due This Week: $65,780 (15 invoices)                    │
│  └─ Due Next Week: $48,200 (12 invoices)                    │
│                                                              │
│  ACTIONS                                                     │
│  [Enter Invoice] [Process Payments] [Vendor Lookup]         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Entering an Invoice

1. Click **Enter Invoice**
2. Select or create vendor
3. Enter invoice details:

```
┌─────────────────────────────────────────────────────────────┐
│              AP INVOICE ENTRY                                │
├─────────────────────────────────────────────────────────────┤
│ Vendor:         [Acme Supply Co.     ▼] [+ New]             │
│ Invoice #:      [INV-12345           ]                      │
│ Invoice Date:   [01/05/2026          ]                      │
│ Due Date:       [02/04/2026          ] (Net 30)             │
│ PO Reference:   [PO-2026-0089        ▼] (optional)          │
│                                                              │
│ INVOICE LINES                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Description        │ GL Account │ Amount   │ Dept      │ │
│ ├────────────────────┼────────────┼──────────┼───────────┤ │
│ │ Raw materials      │ 1200       │ 8,500.00 │ Production│ │
│ │ Freight            │ 5100       │   250.00 │ Production│ │
│ ├────────────────────┼────────────┼──────────┼───────────┤ │
│ │ Subtotal           │            │ 8,750.00 │           │ │
│ │ Tax                │ 2150       │   656.25 │           │ │
│ │ TOTAL              │            │ 9,406.25 │           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Attachments: [📎 Invoice PDF attached]                       │
│                                                              │
│ [Save Draft]  [Submit for Approval]  [Post]                 │
└─────────────────────────────────────────────────────────────┘
```

### Three-Way Match

For PO-based invoices:

```
THREE-WAY MATCH - Invoice INV-12345
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ PURCHASE ORDER: PO-2026-0089                                 │
│ ├─ Line 1: Raw material ABC - 100 units @ $85 = $8,500     │
│ └─ Freight: $250                                            │
│                                                              │
│ RECEIVING: RCV-2026-0456                                     │
│ ├─ Received: 100 units ✓                                    │
│ └─ Received Date: Jan 3, 2026                               │
│                                                              │
│ INVOICE: INV-12345                                           │
│ ├─ Material: $8,500 ✓ Matches PO                            │
│ ├─ Freight: $250 ✓ Matches PO                               │
│ └─ Tax: $656.25                                              │
│                                                              │
│ MATCH STATUS: ✓ FULL MATCH                                   │
│                                                              │
│ [Post Invoice]                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Payment Processing

Process payments:

```
PAYMENT BATCH CREATION
┌─────────────────────────────────────────────────────────────┐
│ Payment Date:    [01/11/2026        ]                       │
│ Bank Account:    [Operating Checking ▼]                     │
│ Payment Method:  [ACH               ▼]                      │
│                                                              │
│ SELECT INVOICES TO PAY                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ☑ │ Vendor       │ Invoice   │ Due Date │ Amount       │ │
│ ├───┼──────────────┼───────────┼──────────┼──────────────┤ │
│ │ ☑ │ Acme Supply  │ INV-12345 │ 02/04    │ $9,406.25    │ │
│ │ ☑ │ Best Parts   │ BP-8876   │ 01/15    │ $3,245.00    │ │
│ │ ☑ │ Best Parts   │ BP-8901   │ 01/18    │ $1,890.00    │ │
│ │ ☐ │ XYZ Corp     │ XYZ-456   │ 01/25    │ $12,500.00   │ │
│ └───┴──────────────┴───────────┴──────────┴──────────────┘ │
│                                                              │
│ Selected: 3 invoices | Total: $14,541.25                    │
│                                                              │
│ [Preview] [Submit for Approval] [Process Payment]           │
└─────────────────────────────────────────────────────────────┘
```

### Vendor Management

Maintain vendor records:

| Field | Description |
|-------|-------------|
| Vendor Name | Legal name |
| Address | Payment address |
| Payment Terms | Net 30, etc. |
| Payment Method | Check, ACH, wire |
| Bank Info | For ACH payments |
| Tax ID | W-9 on file |
| 1099 Required | Yes/No |

---

## 6. Accounts Receivable (AR)

### AR Dashboard

Access: **Finance → AR**

```
ACCOUNTS RECEIVABLE DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  RECEIVABLES SUMMARY                                         │
│  ├─ Total Outstanding: $287,450                             │
│  ├─ Current: $175,300 (61%)                                 │
│  ├─ Past Due: $112,150 (39%)                                │
│  └─ Oldest Invoice: 95 days                                 │
│                                                              │
│  COLLECTION FOCUS                                            │
│  ├─ 90+ Days: 3 customers, $3,000                           │
│  ├─ 60-90 Days: 5 customers, $8,800                         │
│  └─ 30-60 Days: 8 customers, $22,150                        │
│                                                              │
│  RECENT ACTIVITY                                             │
│  ├─ Payments received today: $45,230                        │
│  └─ Invoices sent today: 5 ($67,800)                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Customer Invoicing

Access: **Finance → AR → Invoicing**

Invoices are typically generated from:
- **Sales Orders** (automatic)
- **Service Charges** (manual)
- **Recurring Billing** (automated)

Manual invoice creation:

```
┌─────────────────────────────────────────────────────────────┐
│              CREATE INVOICE                                  │
├─────────────────────────────────────────────────────────────┤
│ Customer:       [ABC Corporation    ▼]                      │
│ Invoice Date:   [01/11/2026        ]                        │
│ Due Date:       [02/10/2026        ] (Net 30)               │
│ PO Number:      [CUST-PO-12345     ]                        │
│                                                              │
│ INVOICE LINES                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Item         │ Description      │ Qty │ Price  │ Amount │ │
│ ├──────────────┼──────────────────┼─────┼────────┼────────┤ │
│ │ PART-ABC     │ Widget Assembly  │ 100 │ $45.00 │ $4,500 │ │
│ │ PART-DEF     │ Bracket          │ 200 │ $12.50 │ $2,500 │ │
│ ├──────────────┼──────────────────┼─────┼────────┼────────┤ │
│ │              │ Subtotal         │     │        │ $7,000 │ │
│ │              │ Tax (8.25%)      │     │        │  $577  │ │
│ │              │ TOTAL            │     │        │ $7,577 │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Save Draft]  [Send Invoice]                                │
└─────────────────────────────────────────────────────────────┘
```

### Payment Application

Apply customer payments:

```
┌─────────────────────────────────────────────────────────────┐
│              APPLY PAYMENT                                   │
├─────────────────────────────────────────────────────────────┤
│ Customer:       ABC Corporation                              │
│ Payment Amount: $10,000.00                                   │
│ Payment Date:   01/11/2026                                   │
│ Payment Method: Wire Transfer                                │
│ Reference:      WT-789012                                    │
│                                                              │
│ OPEN INVOICES                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Invoice  │ Date    │ Amount   │ Balance  │ Apply       │ │
│ ├──────────┼─────────┼──────────┼──────────┼─────────────┤ │
│ │ INV-1001 │ 12/01   │ $5,500   │ $5,500   │ [$5,500  ]  │ │
│ │ INV-1015 │ 12/15   │ $3,200   │ $3,200   │ [$3,200  ]  │ │
│ │ INV-1025 │ 12/28   │ $7,577   │ $7,577   │ [$1,300  ]  │ │
│ └──────────┴─────────┴──────────┴──────────┴─────────────┘ │
│                                                              │
│ Applied: $10,000.00 | Remaining: $0.00 ✓                    │
│                                                              │
│ [Apply Payment]                                              │
└─────────────────────────────────────────────────────────────┘
```

### Collections Management

Track collection activities:

```
COLLECTION QUEUE
┌─────────────────────────────────────────────────────────────┐
│ Customer    │ Balance  │ Days Old │ Last Contact │ Action  │
├─────────────┼──────────┼──────────┼──────────────┼─────────┤
│ XYZ Corp    │ $12,500  │ 45       │ Jan 5        │ Call    │
│ Smith LLC   │ $3,800   │ 62       │ Dec 20       │ Letter  │
│ Jones Inc   │ $1,200   │ 95       │ Nov 15       │ Escalate│
└─────────────┴──────────┴──────────┴──────────────┴─────────┘
```

---

## 7. Cash Management

### Bank Accounts

Access: **Finance → Cash → Bank Accounts**

```
BANK ACCOUNTS
┌─────────────────────────────────────────────────────────────┐
│ Account          │ Bank       │ Balance     │ Last Recon   │
├──────────────────┼────────────┼─────────────┼──────────────┤
│ Operating Check  │ First Bank │ $1,247,500  │ Dec 31 ✓     │
│ Payroll          │ First Bank │ $125,000    │ Dec 31 ✓     │
│ Money Market     │ First Bank │ $500,000    │ Dec 31 ✓     │
│ Credit Card      │ AmEx       │ ($15,230)   │ Dec 31 ✓     │
└──────────────────┴────────────┴─────────────┴──────────────┘
```

### Bank Reconciliation

Monthly bank reconciliation:

```
┌─────────────────────────────────────────────────────────────┐
│              BANK RECONCILIATION                             │
│              Operating Checking - January 2026              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Bank Statement Balance (01/31):        $1,285,420.00        │
│                                                              │
│ ADD: Deposits in Transit                                     │
│   01/30 Customer Payment    $25,000.00                      │
│   01/31 Customer Payment    $18,500.00                      │
│   Total Deposits in Transit:            +$43,500.00         │
│                                                              │
│ LESS: Outstanding Checks                                     │
│   #10234  Vendor ABC         $5,420.00                      │
│   #10235  Vendor XYZ        $12,000.00                      │
│   #10238  Utilities          $2,500.00                      │
│   Total Outstanding Checks:             -$19,920.00         │
│                                                              │
│ ADJUSTED BANK BALANCE:                  $1,309,000.00       │
│                                                              │
│ BOOK BALANCE (GL):                      $1,309,000.00       │
│                                                              │
│ DIFFERENCE:                             $0.00 ✓              │
│                                                              │
│ [Mark Reconciled]                                            │
└─────────────────────────────────────────────────────────────┘
```

### Cash Flow Forecast

View projected cash position:

```
CASH FLOW FORECAST - Next 30 Days
┌─────────────────────────────────────────────────────────────┐
│         │ Week 1   │ Week 2   │ Week 3   │ Week 4   │ Total│
├─────────┼──────────┼──────────┼──────────┼──────────┼──────┤
│ Begin   │ 1,247K   │ 1,302K   │ 1,185K   │ 1,240K   │      │
├─────────┼──────────┼──────────┼──────────┼──────────┼──────┤
│ AR Rcpt │ +150K    │ +120K    │ +180K    │ +135K    │ +585K│
│ AP Pay  │ -65K     │ -187K    │ -95K     │ -120K    │ -467K│
│ Payroll │          │ -50K     │          │ -50K     │ -100K│
│ Other   │ -30K     │          │ -30K     │          │ -60K │
├─────────┼──────────┼──────────┼──────────┼──────────┼──────┤
│ End     │ 1,302K   │ 1,185K   │ 1,240K   │ 1,205K   │      │
└─────────┴──────────┴──────────┴──────────┴──────────┴──────┘
```

---

## 8. Period Close Process

### Period Calendar

Access: **Finance → Periods**

```
FISCAL PERIODS - 2026
┌─────────────────────────────────────────────────────────────┐
│ Period   │ Start    │ End      │ Status    │ Closed       │
├──────────┼──────────┼──────────┼───────────┼──────────────┤
│ Jan 2026 │ 01/01    │ 01/31    │ 🟢 Open   │              │
│ Dec 2025 │ 12/01    │ 12/31    │ 🟡 Closing│ Target: 1/10 │
│ Nov 2025 │ 11/01    │ 11/30    │ 🔵 Closed │ 12/08        │
│ Oct 2025 │ 10/01    │ 10/31    │ 🔵 Closed │ 11/07        │
└──────────┴──────────┴──────────┴───────────┴──────────────┘
```

### Month-End Close Checklist

```
MONTH-END CLOSE CHECKLIST - December 2025
Due Date: January 10, 2026
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ CUTOFF & COMPLETION                              [Day 1-2]  │
│ ☑ All AP invoices entered                                   │
│ ☑ All AR invoices sent                                      │
│ ☑ All cash receipts posted                                  │
│ ☐ Intercompany entries complete                             │
│                                                              │
│ ACCOUNT RECONCILIATION                           [Day 3-5]  │
│ ☑ Bank reconciliation - Operating                           │
│ ☑ Bank reconciliation - Payroll                             │
│ ☐ AP subledger to GL                                        │
│ ☐ AR subledger to GL                                        │
│ ☐ Inventory valuation                                       │
│ ☐ Prepaids and accruals                                     │
│                                                              │
│ ADJUSTMENTS                                      [Day 5-7]  │
│ ☐ Depreciation entry                                        │
│ ☐ Accrued expenses                                          │
│ ☐ Revenue recognition                                       │
│ ☐ Reserve adjustments                                       │
│                                                              │
│ REVIEW & CLOSE                                   [Day 8-10] │
│ ☐ Trial balance review                                      │
│ ☐ Variance analysis                                         │
│ ☐ Manager review                                            │
│ ☐ Close period                                              │
│                                                              │
│ Progress: 45% | Due: 2 days                                 │
└─────────────────────────────────────────────────────────────┘
```

### Closing a Period

When ready to close:

1. Complete all checklist items
2. Run trial balance
3. Review for errors
4. Get manager approval
5. Click **Close Period**

```
┌─────────────────────────────────────────────────────────────┐
│              CLOSE PERIOD                                    │
│              December 2025                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ PRE-CLOSE CHECKS                                             │
│ ✓ All subledgers reconciled                                 │
│ ✓ All journal entries approved                              │
│ ✓ Trial balance balanced                                    │
│ ✓ Variance analysis complete                                │
│                                                              │
│ WARNINGS                                                     │
│ ⚠️ 2 journal entries pending approval (override required)    │
│                                                              │
│ Approved By: [Manager Name     ▼]                           │
│ Close Notes: [Year-end close per schedule           ]       │
│                                                              │
│ [Cancel]  [Close Period]                                    │
│                                                              │
│ ⚠️ This action cannot be undone without Controller approval │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Fixed Assets

### Asset Register

Access: **Finance → Fixed Assets**

```
FIXED ASSET REGISTER
┌─────────────────────────────────────────────────────────────┐
│ Asset ID │ Description     │ Cost     │ Accum Dep │ NBV    │
├──────────┼─────────────────┼──────────┼───────────┼────────┤
│ FA-001   │ CNC Mill #1     │ $250,000 │ $150,000  │$100,000│
│ FA-002   │ CNC Mill #2     │ $250,000 │ $100,000  │$150,000│
│ FA-015   │ Office Furniture│ $25,000  │ $20,000   │ $5,000 │
│ FA-020   │ Delivery Truck  │ $45,000  │ $27,000   │$18,000 │
└──────────┴─────────────────┴──────────┴───────────┴────────┘
│ Total:                     │$1,250,000│ $400,000  │$850,000│
└─────────────────────────────────────────────────────────────┘
```

### Asset Record

Each asset has detailed information:

```
ASSET DETAIL - FA-001
┌─────────────────────────────────────────────────────────────┐
│ Description: CNC Milling Machine #1                          │
│ Serial #: 123456789                                          │
│ Location: Production Floor - Cell 1                          │
│ Responsible: Operations                                      │
├─────────────────────────────────────────────────────────────┤
│ FINANCIAL INFORMATION                                        │
│ ├─ Acquisition Date: January 15, 2020                       │
│ ├─ Original Cost: $250,000                                  │
│ ├─ Useful Life: 10 years                                    │
│ ├─ Depreciation Method: Straight-line                       │
│ ├─ Annual Depreciation: $25,000                             │
│ ├─ Accumulated Depreciation: $150,000                       │
│ └─ Net Book Value: $100,000                                 │
├─────────────────────────────────────────────────────────────┤
│ GL ACCOUNTS                                                  │
│ ├─ Asset Account: 1500 - Fixed Assets                       │
│ ├─ Accum Depr: 1550 - Accumulated Depreciation              │
│ └─ Expense Account: 6500 - Depreciation Expense             │
└─────────────────────────────────────────────────────────────┘
```

### Depreciation Run

Run monthly depreciation:

1. Go to **Fixed Assets → Run Depreciation**
2. Select period
3. Preview entries
4. Post depreciation

---

## 10. Cost Accounting

### Job Costing

Track costs by production job:

```
JOB COST SUMMARY - JOB-2026-0089
┌─────────────────────────────────────────────────────────────┐
│ Part: ABC-123 | Quantity: 500 | Status: Complete            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ COST BREAKDOWN                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Category        │ Estimated │ Actual   │ Variance       │ │
│ ├─────────────────┼───────────┼──────────┼────────────────┤ │
│ │ Material        │ $12,500   │ $12,350  │ $150 Fav       │ │
│ │ Direct Labor    │ $8,000    │ $8,450   │ $450 Unfav     │ │
│ │ Overhead        │ $4,800    │ $5,070   │ $270 Unfav     │ │
│ ├─────────────────┼───────────┼──────────┼────────────────┤ │
│ │ TOTAL           │ $25,300   │ $25,870  │ $570 Unfav     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ UNIT COST                                                    │
│ ├─ Estimated: $50.60                                        │
│ └─ Actual: $51.74                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Inventory Valuation

Track inventory costs:

| Method | Description |
|--------|-------------|
| Standard | Predetermined cost per item |
| FIFO | First In, First Out |
| Average | Weighted average cost |

### Variance Analysis

Analyze cost variances:

```
VARIANCE ANALYSIS - January 2026
┌─────────────────────────────────────────────────────────────┐
│ Variance Type           │ Amount    │ % of Standard        │
├─────────────────────────┼───────────┼──────────────────────┤
│ Material Price Variance │ $2,500 F  │ 1.2% favorable       │
│ Material Usage Variance │ $1,800 U  │ 0.9% unfavorable     │
│ Labor Rate Variance     │ $500 U    │ 0.3% unfavorable     │
│ Labor Efficiency Var    │ $3,200 U  │ 1.8% unfavorable     │
│ Overhead Volume Var     │ $1,500 F  │ 0.8% favorable       │
├─────────────────────────┼───────────┼──────────────────────┤
│ NET VARIANCE            │ $2,500 U  │ 1.0% unfavorable     │
└─────────────────────────┴───────────┴──────────────────────┘
F = Favorable | U = Unfavorable
```

---

## 11. Budgeting & Forecasting

### Budget Overview

Access: **Finance → Budget**

```
BUDGET VS ACTUAL - January 2026
┌─────────────────────────────────────────────────────────────┐
│ Account          │ Budget    │ Actual   │ Variance │ %     │
├──────────────────┼───────────┼──────────┼──────────┼───────┤
│ Revenue          │ $750,000  │ $765,000 │ $15,000 F│ 2.0%  │
│ COGS             │ $400,000  │ $412,500 │ $12,500 U│ 3.1%  │
│ Gross Profit     │ $350,000  │ $352,500 │ $2,500 F │ 0.7%  │
│ Operating Exp    │ $175,000  │ $183,500 │ $8,500 U │ 4.9%  │
│ Net Income       │ $175,000  │ $169,000 │ $6,000 U │ 3.4%  │
└──────────────────┴───────────┴──────────┴──────────┴───────┘
```

### Creating Budgets

Budget entry methods:

1. **Manual Entry**: Enter by account and period
2. **Spread**: Allocate annual total across months
3. **Prior Year + %**: Base on prior year with growth
4. **Upload**: Import from Excel

### Forecast Updates

Update forecasts during the year:

```
FORECAST UPDATE - Q2 2026
┌─────────────────────────────────────────────────────────────┐
│ Metric          │ Original │ Revised  │ Change   │ Reason  │
├─────────────────┼──────────┼──────────┼──────────┼─────────┤
│ Revenue         │ $2.4M    │ $2.6M    │ +$200K   │ New cust│
│ COGS            │ $1.3M    │ $1.4M    │ +$100K   │ Vol incr│
│ Gross Margin    │ 45%      │ 46%      │ +1%      │ Mix     │
└─────────────────┴──────────┴──────────┴──────────┴─────────┘
```

---

## 12. Financial Reporting

### Standard Reports

Access: **Finance → Reports**

| Report | Purpose | Frequency |
|--------|---------|-----------|
| Income Statement | P&L by period | Monthly |
| Balance Sheet | Financial position | Monthly |
| Cash Flow Statement | Cash movements | Monthly |
| Trial Balance | GL balances | Monthly |
| AP Aging | Payables by age | Weekly |
| AR Aging | Receivables by age | Weekly |
| Budget vs Actual | Variance analysis | Monthly |

### Running Reports

```
RUN REPORT - Income Statement
┌─────────────────────────────────────────────────────────────┐
│ Report: Income Statement                                     │
│                                                              │
│ PARAMETERS                                                   │
│ Period: [January 2026       ▼]                              │
│ Compare To: [January 2025   ▼]                              │
│ Detail Level: [Summary      ▼]                              │
│ Department: [All            ▼]                              │
│                                                              │
│ OUTPUT FORMAT                                                │
│ ○ View on Screen                                             │
│ ● Export to Excel                                            │
│ ○ Export to PDF                                              │
│                                                              │
│ [Run Report]                                                 │
└─────────────────────────────────────────────────────────────┘
```

### Income Statement Example

```
INCOME STATEMENT
For the Month Ended January 31, 2026
┌─────────────────────────────────────────────────────────────┐
│                              │ Current   │ Prior Year│ Var │
├──────────────────────────────┼───────────┼───────────┼─────┤
│ REVENUE                                                      │
│   Sales                      │ $765,000  │ $720,000  │ 6.3%│
│   Other Income               │ $5,000    │ $3,000    │     │
│   Total Revenue              │ $770,000  │ $723,000  │ 6.5%│
│                                                              │
│ COST OF GOODS SOLD                                           │
│   Materials                  │ $225,000  │ $210,000  │     │
│   Labor                      │ $125,000  │ $115,000  │     │
│   Overhead                   │ $62,500   │ $58,000   │     │
│   Total COGS                 │ $412,500  │ $383,000  │ 7.7%│
│                                                              │
│ GROSS PROFIT                 │ $357,500  │ $340,000  │ 5.1%│
│   Gross Margin %             │ 46.4%     │ 47.0%     │     │
│                                                              │
│ OPERATING EXPENSES                                           │
│   Salaries & Benefits        │ $95,000   │ $88,000   │     │
│   Rent                       │ $15,000   │ $15,000   │     │
│   Utilities                  │ $12,500   │ $11,000   │     │
│   Depreciation               │ $25,000   │ $24,000   │     │
│   Other                      │ $36,000   │ $32,000   │     │
│   Total Operating Expenses   │ $183,500  │ $170,000  │ 7.9%│
│                                                              │
│ NET INCOME                   │ $174,000  │ $170,000  │ 2.4%│
│   Net Margin %               │ 22.6%     │ 23.5%     │     │
└──────────────────────────────┴───────────┴───────────┴─────┘
```

---

## 13. Tax & Compliance

### Sales Tax

Track and remit sales tax:

```
SALES TAX SUMMARY - January 2026
┌─────────────────────────────────────────────────────────────┐
│ Jurisdiction    │ Taxable Sales │ Tax Rate │ Tax Due       │
├─────────────────┼───────────────┼──────────┼───────────────┤
│ State           │ $650,000      │ 6.25%    │ $40,625.00    │
│ County          │ $650,000      │ 1.00%    │ $6,500.00     │
│ City            │ $650,000      │ 1.00%    │ $6,500.00     │
├─────────────────┼───────────────┼──────────┼───────────────┤
│ TOTAL           │               │ 8.25%    │ $53,625.00    │
└─────────────────┴───────────────┴──────────┴───────────────┘
│ Due Date: February 20, 2026                                 │
│ [Generate Filing] [Mark as Filed]                           │
└─────────────────────────────────────────────────────────────┘
```

### 1099 Processing

Year-end 1099 processing:

1. Review vendor 1099 flags
2. Verify payment totals
3. Generate 1099 forms
4. Review and approve
5. Submit to IRS
6. Mail to vendors

---

## 14. Audit Support

### Audit Preparation

Support internal and external audits:

```
AUDIT REQUEST TRACKER
┌─────────────────────────────────────────────────────────────┐
│ Request # │ Item Requested          │ Due     │ Status     │
├───────────┼─────────────────────────┼─────────┼────────────┤
│ PBC-001   │ Bank reconciliations    │ Feb 1   │ ✓ Complete │
│ PBC-002   │ AP aging detail         │ Feb 1   │ ✓ Complete │
│ PBC-003   │ Revenue cutoff test     │ Feb 3   │ 🟡 Working │
│ PBC-004   │ Fixed asset roll-forward│ Feb 5   │ ○ Not Start│
│ PBC-005   │ Payroll test samples    │ Feb 5   │ ○ Not Start│
└───────────┴─────────────────────────┴─────────┴────────────┘
```

### Document Requests

Respond to audit requests:

1. Receive request list
2. Gather documents from Sensei
3. Export/download as needed
4. Upload to auditor portal
5. Mark complete

### Audit Trail

Sensei maintains complete audit trails:

- All transaction history
- Journal entry approvals
- User activity logs
- Document version history
- Change tracking

---

## 15. System Integration

### Integrated Processes

Finance integrates with other Sensei modules:

| Process | Integration |
|---------|-------------|
| Purchasing | POs create AP accruals |
| Receiving | Receipts update inventory |
| Sales Orders | Ship creates AR invoice |
| Payroll | Time feeds payroll journals |
| Inventory | Counts adjust GL |

### Data Flow

```
           ┌─────────────┐
           │  PURCHASING │
           └──────┬──────┘
                  │ PO
                  ▼
           ┌─────────────┐
           │  RECEIVING  │
           └──────┬──────┘
                  │ Receipt
                  ▼
┌──────────────────────────────────────┐
│           GENERAL LEDGER             │
│  ┌────────┐ ┌────────┐ ┌────────┐   │
│  │   AP   │ │   AR   │ │  INV   │   │
│  └────────┘ └────────┘ └────────┘   │
└──────────────────────────────────────┘
                  ▲
                  │ Invoice
           ┌──────┴──────┐
           │    SALES    │
           └─────────────┘
```

### External Integrations

Connect with external systems:

- Bank feeds (automatic transaction import)
- Payroll system sync
- Credit card processing
- Tax filing systems
- ERP integrations

---

## Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + J` | New journal entry |
| `Ctrl + G` | GL account lookup |
| `Ctrl + V` | Vendor lookup |
| `Ctrl + C` | Customer lookup |
| `Ctrl + /` | Global search |
| `F5` | Refresh |

### Daily Checklist

```
□ Review cash position
□ Process AP invoices
□ Apply AR payments
□ Review pending approvals
□ Check bank activity
```

### Month-End Timeline

| Day | Activity |
|-----|----------|
| 1-2 | Cutoff, last entries |
| 3-5 | Reconciliations |
| 5-7 | Adjustments |
| 8-10 | Review & close |

### Key GL Accounts

| Account | Description |
|---------|-------------|
| 1000 | Cash |
| 1100 | Accounts Receivable |
| 1200 | Inventory |
| 2000 | Accounts Payable |
| 4000 | Revenue |
| 5000 | COGS |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Finance*
