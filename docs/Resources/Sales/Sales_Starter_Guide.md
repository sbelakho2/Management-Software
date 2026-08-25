# Sales Starter Guide

> **Status:** The mobile app, PWA/offline mode, push notifications, barcode/camera
> capture, and battery/connectivity monitoring described in this guide are
> **planned — not implemented**. The web UI is the current interface.

## Sensei OS - Sales Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Sales Dashboard](#3-sales-dashboard)
4. [Customer Management](#4-customer-management)
5. [Quoting & Pricing](#5-quoting--pricing)
6. [Order Management](#6-order-management)
7. [Order Status & Tracking](#7-order-status--tracking)
8. [Forecasting](#8-forecasting)
9. [Sales Analytics](#9-sales-analytics)
10. [Territory Management](#10-territory-management)
11. [Commission Tracking](#11-commission-tracking)
12. [Customer Service Integration](#12-customer-service-integration)
13. [Mobile Sales Tools](#13-mobile-sales-tools)
14. [CRM Integration](#14-crm-integration)
15. [Quick Reference](#15-quick-reference)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use milestones and sprint status for customer-facing delivery expectations.
- Use comments to request clarifications and record customer-impacting decisions when permitted.
- Track customer-reported problems as issues to ensure accountability and closure.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role in Sales

As a Sales Representative in Sensei OS, you are the **customer champion**. You have access to:

- **Customer information** for informed conversations
- **Real-time inventory** to make delivery promises
- **Production status** to update customers accurately
- **Pricing and quoting** tools for quick responses
- **Order tracking** for proactive communication
- **Analytics** to identify opportunities

### Sales Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Customers | Full | View, create, manage accounts |
| Quotes | Full | Create, send, convert quotes |
| Orders | Create + View | Submit and track orders |
| Pricing | View + Discount | See prices, apply approved discounts |
| Inventory | View | Check available stock |
| Production | View Status | Track order progress |
| Reports | Sales Reports | Pipeline, performance, forecasts |

### Sales Success in Sensei OS

```
CUSTOMER SUCCESS CYCLE

┌─────────────────────────────────────────────────────────────┐
│                                                              │
│            ┌─────────┐                                       │
│       ┌────│ PROSPECT│────┐                                  │
│       │    └─────────┘    │                                  │
│       ▼                   ▼                                  │
│  ┌─────────┐         ┌─────────┐                            │
│  │ QUALIFY │         │ NURTURE │                            │
│  └────┬────┘         └─────────┘                            │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │  QUOTE  │───▶│  CLOSE  │───▶│ FULFILL │                  │
│  └─────────┘    └─────────┘    └────┬────┘                  │
│                                      │                       │
│                                      ▼                       │
│                                 ┌─────────┐                  │
│               ┌────────────────│ SUPPORT │                  │
│               │                └────┬────┘                  │
│               ▼                     │                       │
│          ┌─────────┐                │                       │
│          │ REORDER │◀───────────────┘                       │
│          └─────────┘                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter your credentials
3. Complete MFA setup
4. Set up mobile app for field sales

### Initial Setup Tasks

- [ ] Review your assigned customers
- [ ] Check your territory assignments
- [ ] Review price lists and discount limits
- [ ] Set up email integration
- [ ] Configure mobile app
- [ ] Review open quotes and orders

### Your Sales Home Screen

```
┌─────────────────────────────────────────────────────────────┐
│               SALES DASHBOARD                                │
│               January 11, 2026 - 10:15 AM                   │
├─────────────────────────────────────────────────────────────┤
│  MY PERFORMANCE                                              │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │ MTD Sales  │ │ Pipeline   │ │ Open Quotes│ │ Orders     ││
│  │ $125,000   │ │ $450,000   │ │     8      │ │  In Prod   ││
│  │ 83% target │ │            │ │            │ │    12      ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘│
├─────────────────────────────────────────────────────────────┤
│  ACTION ITEMS                                                │
│  ├─ Quote Q-2026-089 expires tomorrow (Acme Corp)           │
│  ├─ Order SO-12456 shipped - notify customer                │
│  └─ Follow up: ABC Inc inquiry (2 days old)                 │
│                                                              │
│  TODAY'S ACTIVITIES                                          │
│  ├─ 10:30 AM: Call with XYZ Manufacturing                   │
│  ├─ 2:00 PM: Quote review - New Customer Corp               │
│  └─ 4:00 PM: Pipeline review meeting                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Sales Dashboard

### Dashboard Widgets

#### Performance Metrics
Your sales performance vs. targets:

```
SALES PERFORMANCE
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ MONTH-TO-DATE         │ QUARTER-TO-DATE    │ YEAR-TO-DATE   │
│ $125,000 / $150,000   │ $380,000 / $450,000│ $1.2M / $1.8M  │
│ ████████████░░░░ 83%  │ ████████████░░ 84% │ ████████████ 67%│
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### Pipeline Summary
Open opportunities by stage:

```
PIPELINE
┌─────────────────────────────────────────────────────────────┐
│ Stage          │ Count │ Value      │ Weighted              │
├────────────────┼───────┼────────────┼───────────────────────┤
│ Qualification  │ 5     │ $125,000   │ $12,500 (10%)         │
│ Proposal       │ 3     │ $85,000    │ $42,500 (50%)         │
│ Negotiation    │ 2     │ $150,000   │ $112,500 (75%)        │
│ Closing        │ 2     │ $90,000    │ $81,000 (90%)         │
├────────────────┼───────┼────────────┼───────────────────────┤
│ TOTAL          │ 12    │ $450,000   │ $248,500              │
└────────────────┴───────┴────────────┴───────────────────────┘
```

#### Order Status
Orders in progress:

```
ORDERS IN PRODUCTION
┌─────────────────────────────────────────────────────────────┐
│ Order      │ Customer     │ Value    │ Ship Date │ Status  │
├────────────┼──────────────┼──────────┼───────────┼─────────┤
│ SO-12456   │ Acme Corp    │ $45,000  │ Jan 15    │ 75% ████│
│ SO-12452   │ XYZ Mfg      │ $28,000  │ Jan 18    │ 50% ██░░│
│ SO-12448   │ ABC Inc      │ $62,000  │ Jan 22    │ 25% █░░░│
└────────────┴──────────────┴──────────┴───────────┴─────────┘
```

---

## 4. Customer Management

### Customer List

Access: **Sales → Customers**

```
CUSTOMERS
┌─────────────────────────────────────────────────────────────┐
│ 🔍 Search customers...    [Filter ▼] [+ Add Customer]       │
├─────────────────────────────────────────────────────────────┤
│ Customer       │ Contact      │ YTD Sales │ Last Order│ Rep │
├────────────────┼──────────────┼───────────┼───────────┼─────┤
│ Acme Corp      │ John Smith   │ $245,000  │ Jan 8     │ You │
│ XYZ Mfg        │ Maria Garcia │ $180,000  │ Jan 5     │ You │
│ ABC Inc        │ David Brown  │ $320,000  │ Jan 2     │ You │
│ Global Tech    │ Sarah Wilson │ $125,000  │ Dec 28    │ You │
└────────────────┴──────────────┴───────────┴───────────┴─────┘
```

### Customer Detail View

```
┌─────────────────────────────────────────────────────────────┐
│  CUSTOMER: Acme Corporation                                  │
│  Account #: CUST-00125 | Since: 2018                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ OVERVIEW                                                     │
│ ├─ Industry: Manufacturing                                  │
│ ├─ Territory: Northeast                                     │
│ ├─ Sales Rep: You                                           │
│ ├─ Credit Limit: $100,000                                   │
│ └─ Terms: Net 30                                            │
│                                                              │
│ CONTACTS                                                     │
│ ├─ John Smith (Primary) - Purchasing Mgr                    │
│ │   📞 555-1234  ✉️ jsmith@acme.com                          │
│ ├─ Lisa Johnson - Operations                                 │
│ │   📞 555-1235  ✉️ ljohnson@acme.com                        │
│ └─ [+ Add Contact]                                          │
│                                                              │
│ ADDRESSES                                                    │
│ ├─ Bill To: 123 Main St, New York, NY 10001                │
│ └─ Ship To: 456 Industrial Pkwy, Newark, NJ 07102          │
│                                                              │
│ QUICK STATS                                                  │
│ ├─ YTD Sales: $245,000                                      │
│ ├─ Open Orders: 2 ($73,000)                                 │
│ ├─ Open Quotes: 1 ($35,000)                                 │
│ └─ Last Order: Jan 8, 2026                                  │
│                                                              │
│ [View Orders] [View Quotes] [New Quote] [View History]      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Customer History

View complete customer relationship:

```
CUSTOMER HISTORY - Acme Corp
┌─────────────────────────────────────────────────────────────┐
│ TABS: [Orders] [Quotes] [Shipments] [Notes] [Payments]      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ORDERS (Last 12 months)                                      │
│ Date      │ Order    │ Amount   │ Status    │ Notes         │
│ Jan 8     │ SO-12456 │ $45,000  │ In Prod   │               │
│ Dec 15    │ SO-12380 │ $28,000  │ Shipped   │               │
│ Nov 20    │ SO-12289 │ $52,000  │ Complete  │               │
│ Oct 5     │ SO-12156 │ $38,000  │ Complete  │               │
│ ...                                                          │
│                                                              │
│ SALES TREND                                                  │
│ 2024: $185,000 → 2025: $245,000 (+32%)                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Quoting & Pricing

### Creating a Quote

Access: **Sales → Quotes → New Quote**

```
┌─────────────────────────────────────────────────────────────┐
│  NEW QUOTE                                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ CUSTOMER                                                     │
│ Customer:    [Acme Corporation        ▼]                    │
│ Contact:     [John Smith              ▼]                    │
│ Ship To:     [456 Industrial Pkwy...  ▼]                    │
│                                                              │
│ QUOTE DETAILS                                                │
│ Valid Until: [Jan 25, 2026  📅]                             │
│ Reference:   [Customer RFQ #12345         ]                 │
│                                                              │
│ LINE ITEMS                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ # │ Item         │ Desc      │ Qty │ Price │ Ext      │ │
│ ├───┼──────────────┼───────────┼─────┼───────┼──────────┤ │
│ │ 1 │ WIDGET-A100  │ Widget A  │ 100 │ $25.00│ $2,500.00│ │
│ │ 2 │ WIDGET-B200  │ Widget B  │ 50  │ $45.00│ $2,250.00│ │
│ │   │ [+ Add Line] │           │     │       │          │ │
│ └───┴──────────────┴───────────┴─────┴───────┴──────────┘ │
│                                                              │
│ PRICING                                                      │
│ ├─ Subtotal:    $4,750.00                                   │
│ ├─ Discount:    10% (-$475.00)                              │
│ ├─ Freight:     $125.00 (estimated)                         │
│ └─ TOTAL:       $4,400.00                                   │
│                                                              │
│ NOTES TO CUSTOMER                                            │
│ [Lead time 2-3 weeks from order confirmation.          ]    │
│                                                              │
│ [Save Draft] [Preview] [Send to Customer]                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Industrial Quoting (Quoting Helper)

For complex industrial jobs (PCBA, Wire Harness, Box Build), use the **Quoting Helper** workflow to leverage engineering expertise and AI.

#### When to use Quoting Helper:
- Multi-layer PCBAs requiring DFM review.
- Custom mechanical enclosures.
- New Product Introductions (NPI).
- High-value/High-risk opportunities.

#### How to use Quoting Helper:
1. **Initialize**: From the RFQ screen, click **Quoting Workbench** → **Initialize Quoting Packets**.
2. **Collaborate**: Monitor the **Stage-Gate Tracker** as EE, ME, and MfgE disciplines provide technical inputs.
3. **AI Assistance**: Use **Quote Memory** to see how similar jobs were quoted in the past.
4. **Interactive Explorer**: Use the sliders to see how price changes with different **Quantity Ladders** and **Test Levels**.
5. **Finalize**: Once engineering sign-off is complete, the **Estimator** generates the final cost build.

### 5.3 Price Lookup

Check pricing and availability:

```
┌─────────────────────────────────────────────────────────────┐
│  ITEM LOOKUP                                                 │
│  🔍 [WIDGET-A100                        ] [Search]          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ WIDGET-A100 - Standard Widget Type A                        │
│                                                              │
│ PRICING                                                      │
│ ├─ List Price:      $28.00                                  │
│ ├─ Customer Price:  $25.00 (Acme - 10% off list)           │
│ └─ Your Discount:   Up to 15% additional                    │
│                                                              │
│ QUANTITY BREAKS                                              │
│ ├─ 1-99:     $25.00                                        │
│ ├─ 100-499:  $23.50 (6% off)                               │
│ └─ 500+:     $22.00 (12% off)                              │
│                                                              │
│ AVAILABILITY                                                 │
│ ├─ On Hand:      250 units                                  │
│ ├─ Available:    180 units (70 allocated)                  │
│ ├─ In Production: 500 units (due Jan 20)                   │
│ └─ Lead Time:    2-3 weeks if not in stock                 │
│                                                              │
│ [Add to Quote]                                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Discount Authority

Your discount levels:

| Discount Level | Your Authority |
|----------------|----------------|
| Up to 10% | Approved automatically |
| 11-15% | Requires manager approval |
| 16-20% | Requires director approval |
| Over 20% | Requires VP approval |

### Quote Workflow

```
QUOTE STATUS FLOW

┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│  DRAFT  │──▶│  SENT   │──▶│REVIEWED │──▶│ ACCEPTED│
└─────────┘   └─────────┘   └─────────┘   └────┬────┘
                  │                            │
                  ▼                            ▼
             ┌─────────┐                 ┌─────────┐
             │ EXPIRED │                 │  ORDER  │
             └─────────┘                 └─────────┘
                  ▲
                  │
             ┌────┴────┐
             │DECLINED │
             └─────────┘
```

---

## 6. Order Management

### Converting Quote to Order

When customer accepts quote:

1. Open the accepted quote
2. Click **Convert to Order**
3. Confirm details:

```
┌─────────────────────────────────────────────────────────────┐
│  CONVERT QUOTE TO ORDER                                      │
│  Quote: Q-2026-089 → Order                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ CONFIRM DETAILS                                              │
│                                                              │
│ Customer:       Acme Corporation ✓                          │
│ PO Number:      [PO-2026-1234        ]  ← Required          │
│ Requested Ship: [Jan 25, 2026  📅]                          │
│                                                              │
│ LINE ITEMS                                                   │
│ ├─ WIDGET-A100 × 100 @ $23.50 = $2,350.00 ✓                │
│ ├─ WIDGET-B200 × 50 @ $45.00 = $2,250.00 ✓                 │
│ └─ Freight: $125.00                                         │
│                                                              │
│ TOTAL: $4,725.00                                            │
│                                                              │
│ CREDIT CHECK                                                 │
│ ├─ Credit Limit: $100,000                                   │
│ ├─ Current Balance: $45,000                                 │
│ ├─ This Order: $4,725                                       │
│ └─ Status: ✓ Approved                                       │
│                                                              │
│ [Cancel]  [Create Order]                                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Manual Order Entry

Create orders directly:

Access: **Sales → Orders → New Order**

Follow similar process to quoting, adding customer PO and ship dates.

### Order Confirmation

After order creation:
- System generates order number
- Confirmation email sent to customer
- Order flows to production planning
- Inventory allocated

---

## 7. Order Status & Tracking

### Order Status View

```
┌─────────────────────────────────────────────────────────────┐
│  ORDER: SO-12456                                             │
│  Customer: Acme Corporation | PO: PO-2026-1234              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ STATUS TIMELINE                                              │
│ ════════════════════════════════════════════                │
│ ✓ Order Placed    ✓ Scheduled    ◐ In Production  ○ Shipped │
│   Jan 8            Jan 9          Jan 11           Jan 15   │
│ ════════════════════════════════════════════                │
│                                                              │
│ PRODUCTION STATUS                                            │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Line │ Item        │ Ordered│ Complete│ Status         │ │
│ ├──────┼─────────────┼────────┼─────────┼────────────────┤ │
│ │ 1    │ WIDGET-A100 │ 100    │ 85      │ In Production  │ │
│ │ 2    │ WIDGET-B200 │ 50     │ 50      │ ✓ Complete     │ │
│ └──────┴─────────────┴────────┴─────────┴────────────────┘ │
│                                                              │
│ Overall Progress: 75% ████████████████░░░░                   │
│                                                              │
│ DATES                                                        │
│ ├─ Ordered: Jan 8, 2026                                     │
│ ├─ Requested Ship: Jan 15, 2026                             │
│ ├─ Estimated Ship: Jan 15, 2026 ✓ On Track                  │
│ └─ Delivery: Jan 18, 2026 (estimated)                       │
│                                                              │
│ [Email Customer] [Add Note] [View Production Details]       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Shipment Tracking

When order ships:

```
SHIPMENT DETAILS - SO-12456
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SHIPMENT: SHP-2026-0890                                     │
│ Ship Date: Jan 15, 2026                                     │
│                                                              │
│ CARRIER INFORMATION                                          │
│ ├─ Carrier: FedEx Freight                                   │
│ ├─ Tracking: 7891234567890                                  │
│ ├─ PRO #: 123456789                                         │
│ └─ [Track Shipment →]                                       │
│                                                              │
│ CONTENTS                                                     │
│ ├─ WIDGET-A100 × 100                                        │
│ └─ WIDGET-B200 × 50                                         │
│                                                              │
│ DELIVERY                                                     │
│ ├─ Ship To: 456 Industrial Pkwy, Newark, NJ                │
│ └─ ETA: Jan 18, 2026                                        │
│                                                              │
│ [Email Tracking to Customer] [Print BOL]                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Proactive Communication

Set up alerts:
- Order delayed → Auto-email customer
- Order shipped → Send tracking info
- Order delivered → Follow-up reminder

---

## 8. Forecasting

### Sales Forecast

Access: **Sales → Forecasting**

```
SALES FORECAST - Q1 2026
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ YOUR FORECAST                                                │
│                                                              │
│ Month    │ Committed │ Best Case │ Pipeline │ Target        │
│ January  │ $125,000  │ $145,000  │ $180,000 │ $150,000      │
│ February │ $95,000   │ $130,000  │ $200,000 │ $150,000      │
│ March    │ $80,000   │ $120,000  │ $225,000 │ $150,000      │
├──────────┼───────────┼───────────┼──────────┼───────────────┤
│ Q1 Total │ $300,000  │ $395,000  │ $605,000 │ $450,000      │
│                                                              │
│ Commit vs Target: 67% ████████████░░░░░░                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Forecast Categories

| Category | Definition | % Weight |
|----------|------------|----------|
| Committed | PO received or verbal commit | 100% |
| Best Case | High probability to close | 75% |
| Pipeline | Active opportunities | Variable |
| Upside | Possible but uncertain | 25% |

### Updating Forecast

```
┌─────────────────────────────────────────────────────────────┐
│  UPDATE FORECAST - January 2026                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ COMMITTED DEALS                                              │
│ ├─ Acme Corp - SO-12456 ────────────── $45,000             │
│ ├─ XYZ Mfg - Verbal commit ─────────── $28,000             │
│ └─ [+ Add Committed]                                        │
│                                                              │
│ BEST CASE                                                    │
│ ├─ Global Tech - Quote sent ─────────── $35,000             │
│ ├─ NewCo - Final negotiation ────────── $42,000             │
│ └─ [+ Add Best Case]                                        │
│                                                              │
│ COMMENTS                                                     │
│ [Acme order in production, will ship by 15th.          ]   │
│ [XYZ expected PO by end of week.                        ]  │
│                                                              │
│ [Save Forecast]                                              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 9. Sales Analytics

### Performance Reports

Access: **Sales → Reports**

```
MY SALES PERFORMANCE
┌─────────────────────────────────────────────────────────────┐
│ Period: [Year to Date ▼]  Compare: [Previous Year ▼]        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ REVENUE                                                      │
│ ████████████████████░░░░░░░░  $1.2M / $1.8M (67%)           │
│                                                              │
│ VS LAST YEAR                                                 │
│ 2025: $1,200,000                                            │
│ 2024: $980,000                                              │
│ Growth: +22% ▲                                               │
│                                                              │
│ BY QUARTER                                                   │
│ ┌────────────────────────────────────────────────┐          │
│ │  $450K │                         ███                     │
│ │  $400K │             ███         ███                     │
│ │  $350K │ ███         ███         ███                     │
│ │        │ Q1          Q2          Q3          Q4           │
│ │        │ Actual      Actual      Actual      Forecast     │
│ └────────────────────────────────────────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Customer Analysis

```
TOP CUSTOMERS - YTD
┌─────────────────────────────────────────────────────────────┐
│ Rank │ Customer     │ Revenue   │ Orders │ Trend │ Growth  │
├──────┼──────────────┼───────────┼────────┼───────┼─────────┤
│ 1    │ ABC Inc      │ $320,000  │ 15     │ ████▲ │ +25%    │
│ 2    │ Acme Corp    │ $245,000  │ 12     │ ███▲  │ +18%    │
│ 3    │ XYZ Mfg      │ $180,000  │ 8      │ ██▼   │ -5%     │
│ 4    │ Global Tech  │ $125,000  │ 6      │ ███▲  │ +32%    │
│ 5    │ NewCo        │ $95,000   │ 4      │ ████▲ │ +50%    │
└──────┴──────────────┴───────────┴────────┴───────┴─────────┘
```

### Product Analysis

```
TOP PRODUCTS - YTD
┌─────────────────────────────────────────────────────────────┐
│ Rank │ Product      │ Revenue   │ Units  │ Avg Price │ GM% │
├──────┼──────────────┼───────────┼────────┼───────────┼─────┤
│ 1    │ WIDGET-A100  │ $425,000  │ 17,000 │ $25.00    │ 35% │
│ 2    │ WIDGET-B200  │ $315,000  │ 7,000  │ $45.00    │ 40% │
│ 3    │ ASSEMBLY-C   │ $180,000  │ 900    │ $200.00   │ 45% │
│ 4    │ CUSTOM-X     │ $145,000  │ 290    │ $500.00   │ 50% │
└──────┴──────────────┴───────────┴────────┴───────────┴─────┘
```

---

## 10. Territory Management

### Your Territory

Access: **Sales → Territory**

```
MY TERRITORY: Northeast Region
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ COVERAGE                                                     │
│ States: NY, NJ, CT, MA, PA, NH, VT, ME, RI                  │
│                                                              │
│ ACCOUNTS                                                     │
│ ├─ Total Accounts: 45                                       │
│ ├─ Active (order in 6 mo): 32                               │
│ ├─ At Risk (no order 6-12 mo): 8                            │
│ └─ Dormant (>12 mo): 5                                      │
│                                                              │
│ PERFORMANCE                                                  │
│ ├─ YTD Revenue: $1,200,000                                  │
│ ├─ Target: $1,800,000                                       │
│ ├─ Achievement: 67%                                         │
│ └─ Rank: 3 of 8 territories                                 │
│                                                              │
│ TOP OPPORTUNITIES                                            │
│ ├─ ABC Inc - $50,000 (Proposal stage)                       │
│ ├─ NewCo - $35,000 (Negotiation)                            │
│ └─ BigCorp - $75,000 (Qualification)                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Account Classification

```
ACCOUNT TIERS
┌─────────────────────────────────────────────────────────────┐
│ Tier │ Revenue/Year │ Accounts │ Service Level             │
├──────┼──────────────┼──────────┼───────────────────────────┤
│ A    │ >$200,000    │ 5        │ Weekly contact, QBRs      │
│ B    │ $50-200K     │ 12       │ Bi-weekly, monthly review │
│ C    │ $10-50K      │ 18       │ Monthly contact           │
│ D    │ <$10K        │ 10       │ Quarterly/As needed       │
└──────┴──────────────┴──────────┴───────────────────────────┘
```

---

## 11. Commission Tracking

### Commission Dashboard

Access: **Sales → Commissions**

```
COMMISSION SUMMARY - 2026
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ YEAR TO DATE                                                 │
│ ├─ Booked Sales: $1,200,000                                 │
│ ├─ Commission Rate: 5%                                      │
│ ├─ Base Commission: $60,000                                 │
│ ├─ Bonus (>100% target): $0 (not yet achieved)             │
│ └─ Total Earned: $60,000                                    │
│                                                              │
│ PAID                                                         │
│ ├─ YTD Paid: $48,000                                        │
│ └─ Pending: $12,000                                         │
│                                                              │
│ BY MONTH                                                     │
│ ┌────────────────────────────────────────────────┐          │
│ │ Month   │ Sales     │ Commission │ Status     │          │
│ ├─────────┼───────────┼────────────┼────────────┤          │
│ │ Jan     │ $125,000  │ $6,250     │ Pending    │          │
│ │ Dec     │ $145,000  │ $7,250     │ Paid       │          │
│ │ Nov     │ $132,000  │ $6,600     │ Paid       │          │
│ └─────────┴───────────┴────────────┴────────────┘          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Commission Plan Details

```
YOUR COMMISSION PLAN
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ BASE STRUCTURE                                               │
│ ├─ Base Rate: 5% of booked sales                            │
│ └─ Paid: Monthly, 30 days after order ships                 │
│                                                              │
│ ACCELERATORS                                                 │
│ ├─ 100-110% of quota: 6% on overage                         │
│ ├─ 110-125% of quota: 7% on overage                         │
│ └─ >125% of quota: 8% on overage                            │
│                                                              │
│ BONUSES                                                      │
│ ├─ New Customer: $500 first order                           │
│ └─ Annual Target: $10,000 if hit annual quota               │
│                                                              │
│ QUOTA                                                        │
│ └─ 2026 Annual: $1,800,000                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 12. Customer Service Integration

### View Customer Issues

See open customer issues:

```
CUSTOMER ISSUES - My Accounts
┌─────────────────────────────────────────────────────────────┐
│ Case #   │ Customer   │ Issue              │ Status│ Age   │
├──────────┼────────────┼────────────────────┼───────┼───────┤
│ CS-4521  │ Acme Corp  │ Delivery question  │ Open  │ 1 day │
│ CS-4515  │ XYZ Mfg    │ Quality concern    │ Pending│3 days│
│ CS-4498  │ ABC Inc    │ Invoice discrepancy│ Resolved│-     │
└──────────┴────────────┴────────────────────┴───────┴───────┘
```

### Collaborating on Issues

Work with customer service:
1. View issue details
2. Add sales notes/context
3. Escalate if needed
4. Track resolution

### Quality & Returns

Monitor product issues:

```
RETURNS/QUALITY - My Accounts (Last 90 Days)
┌─────────────────────────────────────────────────────────────┐
│ Customer    │ RMA #    │ Product     │ Issue        │ $     │
├─────────────┼──────────┼─────────────┼──────────────┼───────┤
│ XYZ Mfg     │ RMA-890  │ WIDGET-A100 │ Dimension OOS│ $500  │
│ ABC Inc     │ RMA-875  │ ASSEMBLY-C  │ Missing part │ $200  │
└─────────────┴──────────┴─────────────┴──────────────┴───────┘
```

---

## 13. Mobile Sales Tools

### Mobile App Features

Use the mobile app in the field:

- **Customer lookup** - Full account info
- **Inventory check** - Real-time availability
- **Quick quote** - Create quotes on the go
- **Order status** - Track any order
- **Contact management** - Call, email, log visits
- **Visit logging** - Record customer visits

### Quick Actions

From mobile dashboard:

```
┌─────────────────────────────────────────┐
│     SENSEI SALES MOBILE                 │
├─────────────────────────────────────────┤
│                                         │
│  [🔍 Customer Search]                   │
│                                         │
│  [📦 Check Inventory]                   │
│                                         │
│  [📝 New Quote]                         │
│                                         │
│  [📋 Order Status]                      │
│                                         │
│  [📍 Log Visit]                         │
│                                         │
│  [📞 Recent Contacts]                   │
│                                         │
└─────────────────────────────────────────┘
```

### Logging Customer Visits

Record visit notes:

1. Tap **Log Visit**
2. Select customer
3. Add notes
4. Log next action
5. Set follow-up reminder

---

## 14. CRM Integration

### Connected Systems

Sensei OS integrates with your CRM:

```
CRM SYNC STATUS
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ SALESFORCE INTEGRATION                                       │
│ Status: ✓ Connected                                         │
│ Last Sync: 5 minutes ago                                    │
│                                                              │
│ SYNCED DATA                                                  │
│ ├─ Accounts ←→ Customers                                    │
│ ├─ Opportunities ←→ Quotes                                  │
│ ├─ Orders → Salesforce (one-way)                            │
│ └─ Contacts ←→ Customer Contacts                            │
│                                                              │
│ RECENT SYNC ACTIVITY                                         │
│ ├─ Account update: Acme Corp                                │
│ ├─ New opportunity: Global Tech                             │
│ └─ Order created: SO-12456                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Working Across Systems

Best practices:
- **Leads/Opportunities**: Manage in CRM
- **Quotes**: Create in Sensei (syncs to CRM)
- **Orders**: Submit through Sensei
- **Production/Inventory**: Always in Sensei

---

## 15. Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Q` | New quote |
| `Ctrl + O` | Order search |
| `Ctrl + C` | Customer search |
| `Ctrl + /` | Global search |
| `F5` | Refresh |

### Order Status Codes

| Status | Meaning |
|--------|---------|
| Entered | Order received |
| Confirmed | Acknowledged, scheduled |
| In Production | Manufacturing |
| Complete | Ready to ship |
| Shipped | In transit |
| Delivered | At customer |
| Invoiced | Billed |

### Quick Actions Checklist

```
DAILY SALES ACTIVITIES
□ Review dashboard and action items
□ Check order status for key customers
□ Follow up on expiring quotes
□ Update forecast
□ Log customer contacts
□ Review production schedule for promises

WEEKLY
□ Pipeline review
□ Forecast update
□ Customer outreach (at-risk accounts)
□ Quote follow-up

MONTHLY
□ Territory analysis
□ Commission review
□ Customer satisfaction check
```

### Key Contacts

| Need | Contact |
|------|---------|
| Order issues | Customer Service ext. 2100 |
| Credit questions | Finance ext. 3100 |
| Shipping | Warehouse ext. 4100 |
| Production status | Planning ext. 5100 |
| Pricing approval | Sales Manager |

### Sales Formulas

```
USEFUL CALCULATIONS

Gross Margin % = (Sell Price - Cost) / Sell Price × 100

Markup % = (Sell Price - Cost) / Cost × 100

Weighted Pipeline = Σ (Opportunity Value × Probability %)

Win Rate = Won Opportunities / Total Closed × 100

Average Deal Size = Total Revenue / Number of Deals
```

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Sales*
