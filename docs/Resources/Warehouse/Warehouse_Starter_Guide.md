# Warehouse Manager Starter Guide

> **Status:** The mobile app, PWA/offline mode, push notifications, barcode/camera
> capture, and battery/connectivity monitoring described in this guide are
> **planned — not implemented**. The web UI is the current interface.

## Sensei OS - Warehouse & Inventory Complete Reference

---

## Table of Contents

1. [Welcome & Role Overview](#1-welcome--role-overview)
2. [Getting Started](#2-getting-started)
3. [Warehouse Dashboard](#3-warehouse-dashboard)
4. [Inventory Management](#4-inventory-management)
5. [Receiving Operations](#5-receiving-operations)
6. [Put-Away & Storage](#6-put-away--storage)
7. [Picking & Kitting](#7-picking--kitting)
8. [Shipping Operations](#8-shipping-operations)
9. [Cycle Counting](#9-cycle-counting)
10. [Warehouse Layout](#10-warehouse-layout)
11. [Equipment & Tools](#11-equipment--tools)
12. [Team Management](#12-team-management)
13. [Performance Metrics](#13-performance-metrics)
14. [Integration with Production](#14-integration-with-production)
15. [Quick Reference](#15-quick-reference)

---

## Project Management (Taiga-like)

Sensei OS includes a Taiga-like project module for planning and execution.

- Use project visibility to anticipate material needs and shipping deadlines.
- Use comments to coordinate constraints (shortages, receiving delays, expedite requests) when permitted.
- Use milestones to track key dates tied to shipments and customer deliveries.

See the shared [Project Management guide](../../guides/project-management.md).

## 1. Welcome & Role Overview

### Your Role as Warehouse Manager

As Warehouse Manager, you are the **guardian of inventory** and the **engine of material flow**. Sensei OS empowers you to:

- **Control inventory** with real-time visibility
- **Manage receiving** efficiently and accurately
- **Optimize storage** for space and accessibility
- **Fulfill production needs** through timely picking
- **Execute shipping** to meet customer expectations
- **Maintain accuracy** through systematic counting

### Warehouse Capabilities

| Capability | Access Level | Description |
|------------|--------------|-------------|
| Inventory View | Full | All locations and quantities |
| Receiving | Full | Process inbound shipments |
| Put-Away | Full | Direct storage locations |
| Picking | Full | Manage picks and kits |
| Shipping | Full | Process outbound shipments |
| Cycle Counting | Full | Schedule and execute counts |
| Adjustments | With Approval | Quantity and location changes |
| Location Management | Full | Configure warehouse layout |
| Reporting | Full | All warehouse analytics |

### Warehouse Module Overview

```
SENSEI OS WAREHOUSE
├── Inventory
│   ├── Item Master
│   ├── Locations
│   ├── Quantities
│   └── Transactions
├── Inbound
│   ├── Receiving
│   ├── Inspection
│   └── Put-Away
├── Internal
│   ├── Transfers
│   ├── Cycle Counts
│   └── Adjustments
└── Outbound
    ├── Picking
    ├── Kitting
    ├── Packing
    └── Shipping
```

---

## 2. Getting Started

### First Login

1. Navigate to `https://your-company.sensei-os.com`
2. Enter credentials
3. Complete MFA setup
4. Configure mobile device (for floor work)

### Initial Setup Tasks

- [ ] Verify your warehouse role permissions
- [ ] Review warehouse layout in system
- [ ] Check location naming conventions
- [ ] Review team roster and assignments
- [ ] Set up mobile scanner

### Your Warehouse Home Screen

```
┌─────────────────────────────────────────────────────────────┐
│               WAREHOUSE DASHBOARD                            │
│               January 11, 2026 - 2:35 PM                    │
├─────────────────────────────────────────────────────────────┤
│  ACTIVITY STATUS                                             │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐│
│  │ Receiving  │ │ Put-Away   │ │ Picking    │ │ Shipping   ││
│  │    5       │ │    3       │ │   12       │ │    8       ││
│  │  pending   │ │  pending   │ │   open     │ │  ready     ││
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘│
├─────────────────────────────────────────────────────────────┤
│  ALERTS                                                      │
│  🔴 Low stock: RAW-123 (below safety stock)                 │
│  🔴 Expedite pick: PO-5678 (ship today)                     │
│  🟡 3 receiving inspections pending QC                      │
│  🔵 Cycle count scheduled: Zone A (tomorrow)                │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Warehouse Dashboard

### Real-Time Status

Your dashboard shows live warehouse activity:

```
WAREHOUSE ACTIVITY - LIVE
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  INBOUND                          OUTBOUND                   │
│  ┌────────────────────┐           ┌────────────────────┐    │
│  │ Dock 1: 🚛 Unload  │           │ Dock A: 📦 Loading │    │
│  │ Dock 2: ✓ Clear    │           │ Dock B: ⏳ Waiting │    │
│  │ Dock 3: ✓ Clear    │           │ Dock C: ✓ Clear   │    │
│  └────────────────────┘           └────────────────────┘    │
│                                                              │
│  ACTIVE TASKS                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ User        │ Task          │ Location │ Status        │ │
│  ├─────────────┼───────────────┼──────────┼───────────────┤ │
│  │ J. Garcia   │ RCV-1234      │ Dock 1   │ ▶ In Progress │ │
│  │ M. Smith    │ PUT-5678      │ Zone A   │ ▶ In Progress │ │
│  │ D. Johnson  │ PICK-9012     │ Zone B   │ ▶ In Progress │ │
│  │ S. Lee      │ SHIP-3456     │ Dock A   │ ▶ In Progress │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Metrics Display

| Metric | Today | Target | Status |
|--------|-------|--------|--------|
| Receiving Accuracy | 99.5% | 99% | ✓ |
| Pick Accuracy | 99.8% | 99.5% | ✓ |
| On-Time Shipment | 97% | 98% | ⚠️ |
| Inventory Accuracy | 99.2% | 99% | ✓ |

---

## 4. Inventory Management

### Item Master

Access: **Warehouse → Inventory → Items**

```
ITEM MASTER
┌─────────────────────────────────────────────────────────────┐
│ [🔍 Search] [+ New Item] [📥 Export] [⚙️ Filters]           │
├─────────────────────────────────────────────────────────────┤
│ Part #    │ Description        │ On Hand │ Available│ UOM  │
├───────────┼────────────────────┼─────────┼──────────┼──────┤
│ RAW-123   │ Steel Bar 1"       │ 500     │ 450      │ EA   │
│ RAW-456   │ Aluminum Sheet     │ 200     │ 175      │ EA   │
│ COMP-789  │ Motor Assembly     │ 50      │ 35       │ EA   │
│ FG-001    │ Widget Complete    │ 125     │ 125      │ EA   │
└───────────┴────────────────────┴─────────┴──────────┴──────┘
```

### Item Detail

```
ITEM DETAIL - RAW-123
┌─────────────────────────────────────────────────────────────┐
│ Part #: RAW-123                                              │
│ Description: Steel Bar 1" Diameter x 12" Length             │
│ Category: Raw Material | ABC Class: A                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ QUANTITIES                                                   │
│ ├─ On Hand: 500 EA                                          │
│ ├─ Allocated: 50 EA (2 jobs)                                │
│ ├─ Available: 450 EA                                        │
│ ├─ On Order: 200 EA (PO-2026-089)                           │
│ └─ Backordered: 0 EA                                        │
│                                                              │
│ PLANNING                                                     │
│ ├─ Safety Stock: 100 EA                                     │
│ ├─ Reorder Point: 150 EA                                    │
│ ├─ Reorder Qty: 200 EA                                      │
│ └─ Lead Time: 14 days                                       │
│                                                              │
│ LOCATIONS                                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Location   │ Quantity │ Lot #     │ Status              │ │
│ ├────────────┼──────────┼───────────┼─────────────────────┤ │
│ │ A-01-01    │ 300      │ L2025-123 │ ✓ Available         │ │
│ │ A-01-02    │ 150      │ L2025-124 │ ✓ Available         │ │
│ │ A-01-03    │ 50       │ L2025-125 │ 🔒 Allocated        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [Adjust Qty] [Transfer] [View History] [Create Count]       │
└─────────────────────────────────────────────────────────────┘
```

### Inventory Transactions

All inventory movements are tracked:

| Transaction Type | Description |
|-----------------|-------------|
| Receipt | Incoming from PO |
| Issue | Outgoing to production |
| Transfer | Location to location |
| Adjustment | Quantity correction |
| Return | Back from production |
| Ship | Outgoing to customer |
| Count | Cycle count adjustment |

### Viewing Transaction History

```
TRANSACTION HISTORY - RAW-123
┌─────────────────────────────────────────────────────────────┐
│ Date     │ Type     │ Qty    │ Location │ Reference │ User │
├──────────┼──────────┼────────┼──────────┼───────────┼──────┤
│ 01/11/26 │ Issue    │ -25    │ A-01-01  │ JOB-1234  │ MSmi │
│ 01/10/26 │ Receipt  │ +200   │ A-01-01  │ PO-2026-88│ JGar │
│ 01/09/26 │ Transfer │ +50/-50│ A-01-03  │ TRF-567   │ DJoh │
│ 01/08/26 │ Issue    │ -30    │ A-01-02  │ JOB-1230  │ MSmi │
└──────────┴──────────┴────────┴──────────┴───────────┴──────┘
```

---

## 5. Receiving Operations

### Receiving Dashboard

Access: **Warehouse → Receiving**

```
RECEIVING DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  EXPECTED TODAY                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ PO #      │ Vendor      │ Items │ ETA   │ Status       │ │
│  ├───────────┼─────────────┼───────┼───────┼──────────────┤ │
│  │ PO-2026-89│ Acme Supply │ 3     │ 10 AM │ ✓ Arrived    │ │
│  │ PO-2026-90│ Best Parts  │ 1     │ 2 PM  │ 🚛 En Route  │ │
│  │ PO-2026-91│ Steel Co    │ 5     │ 3 PM  │ 🚛 En Route  │ │
│  └───────────┴─────────────┴───────┴───────┴──────────────┘ │
│                                                              │
│  PENDING RECEIPT                                             │
│  ├─ 5 shipments at dock                                     │
│  ├─ 3 pending inspection                                    │
│  └─ 8 pending put-away                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Receiving a Shipment

Step-by-step receiving process:

1. **Shipment Arrives**
   - Verify carrier and paperwork
   - Assign dock door
   - Log arrival in system

2. **Unload and Count**
   ```
   ┌─────────────────────────────────────────────────────────────┐
   │              RECEIVE SHIPMENT                                │
   │              PO-2026-089 | Acme Supply                       │
   ├─────────────────────────────────────────────────────────────┤
   │                                                              │
   │ LINE ITEMS                                                   │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ Part    │ Description  │ Ordered │ Received │ Status   │ │
   │ ├─────────┼──────────────┼─────────┼──────────┼──────────┤ │
   │ │ RAW-123 │ Steel Bar    │ 200     │ [200   ] │ ✓ Match  │ │
   │ │ RAW-456 │ Aluminum     │ 100     │ [100   ] │ ✓ Match  │ │
   │ │ COMP-789│ Motor Assy   │ 25      │ [20    ] │ ⚠️ Short │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                              │
   │ Packing Slip #: [PS-12345         ]                         │
   │ Condition: [Good              ▼]                            │
   │ Notes: [5 units backordered per vendor              ]       │
   │                                                              │
   │ [Save Draft]  [Submit for Inspection]  [Direct to Stock]   │
   └─────────────────────────────────────────────────────────────┘
   ```

3. **Inspection (if required)**
   - Quality performs incoming inspection
   - Pass/Fail/Partial disposition
   - System routes next steps

4. **Complete Receipt**
   - Generate lot numbers
   - Print labels
   - Trigger put-away tasks

### Handling Discrepancies

| Discrepancy | Action |
|-------------|--------|
| Short shipment | Note on receipt, contact vendor |
| Over shipment | Receive to PO qty, note overage |
| Damaged | Segregate, log claim, notify vendor |
| Wrong item | Reject, contact vendor |

---

## 6. Put-Away & Storage

### Put-Away Queue

Access: **Warehouse → Put-Away**

```
PUT-AWAY QUEUE
┌─────────────────────────────────────────────────────────────┐
│ Receipt  │ Part     │ Qty   │ Suggested │ Status           │
├──────────┼──────────┼───────┼───────────┼──────────────────┤
│ RCV-1234 │ RAW-123  │ 200   │ A-01-01   │ ⏳ Pending       │
│ RCV-1234 │ RAW-456  │ 100   │ B-02-03   │ ⏳ Pending       │
│ RCV-1233 │ COMP-789 │ 50    │ C-03-02   │ ▶ In Progress   │
└──────────┴──────────┴───────┴───────────┴──────────────────┘
```

### Put-Away Process

1. **Get Assignment**
   - System suggests location based on:
     - Item's default location
     - Available space
     - ABC classification
     - Pick frequency

2. **Confirm Put-Away**
   ```
   ┌─────────────────────────────────────────────────────────────┐
   │              PUT-AWAY TASK                                   │
   │              Task: PUT-5678                                  │
   ├─────────────────────────────────────────────────────────────┤
   │                                                              │
   │ Item: RAW-123 - Steel Bar 1"                                │
   │ Quantity: 200 EA                                             │
   │ Lot #: L2026-001                                             │
   │                                                              │
   │ FROM: Receiving Dock 1                                       │
   │ TO:   A-01-01 (Suggested)                                    │
   │                                                              │
   │ Scan Location: [____________] or [Override Location]        │
   │                                                              │
   │ [Confirm Put-Away]                                           │
   └─────────────────────────────────────────────────────────────┘
   ```

3. **Override Location**
   - If suggested location not suitable
   - Select alternative location
   - System updates item location

### Storage Strategies

| Strategy | Description | Use For |
|----------|-------------|---------|
| Fixed | Item always in same location | High-volume, frequent picks |
| Random | Next available location | Space optimization |
| Zone | Items grouped by category | Organization, picking efficiency |
| ABC | A items in prime locations | Reduce travel time |

---

## 7. Picking & Kitting

### Pick Queue

Access: **Warehouse → Picking**

```
PICK QUEUE
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ PRIORITY PICKS                                               │
│ 🔴 PICK-9012 | JOB-1234 | 5 items | Due: NOW | Hot!         │
│ 🟡 PICK-9013 | JOB-1235 | 3 items | Due: 3 PM               │
│ 🟡 PICK-9014 | JOB-1236 | 8 items | Due: 4 PM               │
│                                                              │
│ STANDARD PICKS                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Pick #   │ Order/Job │ Lines │ Due      │ Status       │ │
│ ├──────────┼───────────┼───────┼──────────┼──────────────┤ │
│ │ PICK-9015│ JOB-1237  │ 4     │ Tomorrow │ ⏳ Pending   │ │
│ │ PICK-9016│ JOB-1238  │ 2     │ Tomorrow │ ⏳ Pending   │ │
│ │ PICK-9017│ SHIP-4567 │ 6     │ Tomorrow │ ⏳ Pending   │ │
│ └──────────┴───────────┴───────┴──────────┴──────────────┘ │
│                                                              │
│ [Assign Picker] [Wave Planning] [Batch Picks]               │
└─────────────────────────────────────────────────────────────┘
```

### Performing a Pick

```
PICK TASK - PICK-9012
For: JOB-1234 (Priority: Hot!)
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ LINE 1 of 5                                                  │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Part: RAW-123 - Steel Bar 1"                            │ │
│ │ Quantity: 25 EA                                          │ │
│ │                                                          │ │
│ │ LOCATION: A-01-01                                        │ │
│ │ Available: 300 EA | Lot: L2025-123                      │ │
│ │                                                          │ │
│ │ Scan Location: [____________]                            │ │
│ │ Qty Picked:    [25         ]                             │ │
│ │                                                          │ │
│ │ [Confirm Pick] [Short Pick] [Skip - Next Line]          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Progress: 0/5 lines | Est. Time: 8 min                      │
└─────────────────────────────────────────────────────────────┘
```

### Pick Methods

| Method | Description | Best For |
|--------|-------------|----------|
| Discrete | One order at a time | Simple, accurate |
| Batch | Multiple orders together | Efficiency |
| Wave | Grouped by time/zone | Large volumes |
| Zone | Picker stays in zone | Large warehouse |

### Kitting

Assemble kits for production:

```
KIT ASSEMBLY - KIT-2026-001
For: JOB-1240 (Part: ASSY-500)
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ KIT COMPONENTS                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Line │ Part    │ Required │ Picked │ Status             │ │
│ ├──────┼─────────┼──────────┼────────┼────────────────────┤ │
│ │ 1    │ COMP-A  │ 10       │ 10     │ ✓ Complete         │ │
│ │ 2    │ COMP-B  │ 10       │ 10     │ ✓ Complete         │ │
│ │ 3    │ COMP-C  │ 20       │ 20     │ ✓ Complete         │ │
│ │ 4    │ COMP-D  │ 10       │ 8      │ ⚠️ Short (2)        │ │
│ │ 5    │ COMP-E  │ 10       │ 0      │ ⏳ Pending         │ │
│ └──────┴─────────┴──────────┴────────┴────────────────────┘ │
│                                                              │
│ Kit Status: Partial | 3/5 complete                          │
│                                                              │
│ [Continue Picking] [Deliver Partial Kit] [Hold]             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Shipping Operations

### Shipping Dashboard

Access: **Warehouse → Shipping**

```
SHIPPING DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  READY TO SHIP                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ Order    │ Customer   │ Carrier │ Ship By  │ Status    │ │
│  ├──────────┼────────────┼─────────┼──────────┼───────────┤ │
│  │ SO-5678  │ Acme Corp  │ FedEx   │ Today 5P │ 📦 Packed │ │
│  │ SO-5679  │ Best Co    │ UPS     │ Today 5P │ 📦 Packed │ │
│  │ SO-5680  │ XYZ Inc    │ LTL     │ Today 6P │ ⏳ Packing│ │
│  └──────────┴────────────┴─────────┴──────────┴───────────┘ │
│                                                              │
│  DOCK STATUS                                                 │
│  ├─ Dock A: SO-5678 loading                                 │
│  ├─ Dock B: Truck expected 4:30 PM                          │
│  └─ Dock C: Available                                        │
│                                                              │
│  TODAY'S METRICS                                             │
│  ├─ Orders shipped: 12 of 15                                │
│  ├─ On-time: 100%                                           │
│  └─ Packages: 45                                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Shipping Process

1. **Verify Pick Complete**
   - All items picked and staged
   - Quality check passed (if required)

2. **Pack and Label**
   ```
   ┌─────────────────────────────────────────────────────────────┐
   │              PACK & SHIP                                     │
   │              Order: SO-5678 | Acme Corp                      │
   ├─────────────────────────────────────────────────────────────┤
   │                                                              │
   │ ITEMS TO SHIP                                                │
   │ ┌─────────────────────────────────────────────────────────┐ │
   │ │ Part    │ Description      │ Qty  │ Packed │ Carton    │ │
   │ ├─────────┼──────────────────┼──────┼────────┼───────────┤ │
   │ │ FG-001  │ Widget Complete  │ 25   │ ✓ 25   │ Box 1, 2  │ │
   │ │ FG-002  │ Gadget Complete  │ 10   │ ✓ 10   │ Box 3     │ │
   │ └─────────────────────────────────────────────────────────┘ │
   │                                                              │
   │ PACKAGING                                                    │
   │ ├─ Box 1: 15 × FG-001 | 25 lbs | 12×12×10"                  │
   │ ├─ Box 2: 10 × FG-001 | 17 lbs | 12×12×10"                  │
   │ └─ Box 3: 10 × FG-002 | 12 lbs | 8×8×8"                     │
   │                                                              │
   │ CARRIER: FedEx Ground                                        │
   │ Ship To: Acme Corp, 123 Main St, City, ST 12345             │
   │                                                              │
   │ [Generate Labels] [Print Packing Slip] [Ship Confirm]       │
   └─────────────────────────────────────────────────────────────┘
   ```

3. **Generate Shipping Labels**
   - Carrier integration generates labels
   - Tracking numbers assigned

4. **Confirm Shipment**
   - Record actual ship date
   - System updates inventory
   - Customer notified

### Carrier Integration

| Carrier | Services | Label Type |
|---------|----------|------------|
| FedEx | Ground, Express, Freight | Thermal |
| UPS | Ground, 2-Day, Next Day | Thermal |
| USPS | Priority, First Class | Thermal |
| LTL | Various carriers | BOL |

---

## 9. Cycle Counting

### Cycle Count Dashboard

Access: **Warehouse → Cycle Counting**

```
CYCLE COUNT DASHBOARD
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  CURRENT PERIOD: January 2026                                │
│                                                              │
│  COUNT STATUS                                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ ABC Class │ Items │ Counted │ Remaining │ Accuracy     │ │
│  ├───────────┼───────┼─────────┼───────────┼──────────────┤ │
│  │ A Items   │ 50    │ 45      │ 5         │ 99.5%        │ │
│  │ B Items   │ 150   │ 120     │ 30        │ 99.2%        │ │
│  │ C Items   │ 300   │ 100     │ 200       │ 98.8%        │ │
│  └───────────┴───────┴─────────┴───────────┴──────────────┘ │
│                                                              │
│  SCHEDULED COUNTS                                            │
│  ├─ Today: Zone A, Rows 1-3 (25 locations)                  │
│  ├─ Tomorrow: Zone A, Rows 4-6 (25 locations)               │
│  └─ This Week: Complete Zone A                              │
│                                                              │
│  [Create Count] [Schedule Counts] [View History]            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Creating a Cycle Count

```
┌─────────────────────────────────────────────────────────────┐
│              CREATE CYCLE COUNT                              │
├─────────────────────────────────────────────────────────────┤
│ Count Type:     ○ Location Based                            │
│                 ● Item Based                                 │
│                 ○ ABC Cycle Count                            │
│                                                              │
│ Selection:                                                   │
│ Items:          [RAW-123, RAW-456, COMP-789        ] [Add]  │
│ Or Zone:        [Zone A           ▼]                        │
│ Or ABC Class:   [A Items          ▼]                        │
│                                                              │
│ Options:                                                     │
│ ☐ Freeze locations during count                             │
│ ☑ Blind count (don't show expected qty)                     │
│ ☐ Require recount if variance > [5 ]%                       │
│                                                              │
│ Assign To:      [J. Garcia        ▼]                        │
│ Due Date:       [01/12/2026       ]                         │
│                                                              │
│ [Create Count]                                               │
└─────────────────────────────────────────────────────────────┘
```

### Performing a Count

```
CYCLE COUNT - CC-2026-0045
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ LOCATION: A-01-01                                            │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Part       │ Lot #       │ Expected │ Counted │ Var    │ │
│ ├────────────┼─────────────┼──────────┼─────────┼────────┤ │
│ │ RAW-123    │ L2025-123   │ (Blind)  │ [298  ] │        │ │
│ │ RAW-123    │ L2025-124   │ (Blind)  │ [    ] │        │ │
│ └────────────┴─────────────┴──────────┴─────────┴────────┘ │
│                                                              │
│ [Previous Location]  [Save & Next]  [Complete Count]        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Reconciling Variances

```
COUNT RECONCILIATION - CC-2026-0045
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ VARIANCES FOUND                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Location │ Part    │ System │ Counted │ Variance│ Action│ │
│ ├──────────┼─────────┼────────┼─────────┼─────────┼───────┤ │
│ │ A-01-01  │ RAW-123 │ 300    │ 298     │ -2      │ [Adj] │ │
│ │ B-02-03  │ RAW-456 │ 50     │ 55      │ +5      │ [Inv] │ │
│ └──────────┴─────────┴────────┴─────────┴─────────┴───────┘ │
│                                                              │
│ Net Variance Value: -$125.00                                 │
│                                                              │
│ Options:                                                     │
│ [Adjust Inventory]  [Recount]  [Investigate]                │
│                                                              │
│ Approval Required: Yes (variance > $100)                    │
│ Approver: [Warehouse Manager ▼]                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### ABC Classification

| Class | % of Items | % of Value | Count Frequency |
|-------|------------|------------|-----------------|
| A | 10-20% | 70-80% | Monthly |
| B | 20-30% | 15-20% | Quarterly |
| C | 50-60% | 5-10% | Annually |

---

## 10. Warehouse Layout

### Location Structure

```
WAREHOUSE LAYOUT
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ LOCATION FORMAT: Zone-Aisle-Rack-Level                      │
│ Example: A-01-03-2 = Zone A, Aisle 01, Rack 03, Level 2    │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │                    ZONE A (Raw Materials)               │ │
│ │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │ │
│ │  │A-01 │ │A-02 │ │A-03 │ │A-04 │ │A-05 │              │ │
│ │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘              │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │                    ZONE B (Components)                  │ │
│ │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │ │
│ │  │B-01 │ │B-02 │ │B-03 │ │B-04 │ │B-05 │              │ │
│ │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘              │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │                    ZONE C (Finished Goods)              │ │
│ │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │ │
│ │  │C-01 │ │C-02 │ │C-03 │ │C-04 │ │C-05 │              │ │
│ │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘              │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ [📍 DOCK 1] [📍 DOCK 2] [📍 DOCK 3]  [📍 DOCK A] [📍 DOCK B]│
│ (Receiving)                          (Shipping)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Managing Locations

Access: **Warehouse → Locations**

```
LOCATION MANAGEMENT
┌─────────────────────────────────────────────────────────────┐
│ Location │ Zone    │ Type     │ Max Capacity │ Status      │
├──────────┼─────────┼──────────┼──────────────┼─────────────┤
│ A-01-01  │ Zone A  │ Rack     │ 500 EA       │ ✓ Active    │
│ A-01-02  │ Zone A  │ Rack     │ 500 EA       │ ✓ Active    │
│ A-01-03  │ Zone A  │ Rack     │ 500 EA       │ ✓ Active    │
│ STAGE-01 │ Staging │ Floor    │ 10 pallets   │ ✓ Active    │
│ QC-HOLD  │ QC      │ Hold     │ -            │ ✓ Active    │
└──────────┴─────────┴──────────┴──────────────┴─────────────┘
```

### Location Types

| Type | Purpose |
|------|---------|
| Rack | Standard storage |
| Bin | Small parts |
| Floor | Bulk/pallet storage |
| Staging | Temporary holding |
| QC Hold | Inspection holding |
| Dock | Receiving/shipping |

---

## 11. Equipment & Tools

### Warehouse Equipment

Track and manage equipment:

```
EQUIPMENT STATUS
┌─────────────────────────────────────────────────────────────┐
│ Equipment    │ Type     │ Status    │ Assigned │ Cert Due  │
├──────────────┼──────────┼───────────┼──────────┼───────────┤
│ FL-001       │ Forklift │ ✓ Active  │ J. Garcia│ Mar 2026  │
│ FL-002       │ Forklift │ ⚠️ Maint   │ -        │ -         │
│ PJ-001       │ Pallet Jk│ ✓ Active  │ Pool     │ -         │
│ SC-001       │ Scanner  │ ✓ Active  │ M. Smith │ -         │
│ SC-002       │ Scanner  │ ✓ Active  │ D. Johns │ -         │
└──────────────┴──────────┴───────────┴──────────┴───────────┘
```

### Mobile Scanners

Configure and manage scanners:

1. Assign to users
2. Configure for warehouse tasks
3. Monitor battery and connectivity
4. Troubleshoot issues

### Forklift Safety

Track operator certifications:

| Operator | Certified | Expires | Status |
|----------|-----------|---------|--------|
| J. Garcia | Yes | Mar 2026 | ✓ Current |
| M. Smith | Yes | Jun 2026 | ✓ Current |
| D. Johnson | Yes | Jan 2026 | ⚠️ Due |

---

## 12. Team Management

### Team Roster

Access: **Warehouse → Team**

```
WAREHOUSE TEAM
┌─────────────────────────────────────────────────────────────┐
│ Name         │ Role        │ Shift │ Zone    │ Status      │
├──────────────┼─────────────┼───────┼─────────┼─────────────┤
│ J. Garcia    │ Lead        │ Day   │ All     │ ✓ Active    │
│ M. Smith     │ Picker      │ Day   │ A, B    │ ✓ Active    │
│ D. Johnson   │ Receiver    │ Day   │ Dock    │ ✓ Active    │
│ S. Lee       │ Shipper     │ Day   │ Dock    │ ✓ Active    │
│ R. Martinez  │ Picker      │ Night │ A, B    │ ✓ Active    │
└──────────────┴─────────────┴───────┴─────────┴─────────────┘
```

### Task Assignment

Assign and monitor tasks:

```
TASK ASSIGNMENT
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│ PENDING TASKS                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Task      │ Type     │ Priority│ Assigned │ Status     │ │
│ ├───────────┼──────────┼─────────┼──────────┼────────────┤ │
│ │ PUT-5680  │ Put-Away │ Normal  │ [Assign] │ ⏳ Pending │ │
│ │ PICK-9020 │ Pick     │ High    │ [Assign] │ ⏳ Pending │ │
│ │ CC-0046   │ Count    │ Normal  │ [Assign] │ ⏳ Pending │ │
│ └───────────┴──────────┴─────────┴──────────┴────────────┘ │
│                                                              │
│ STAFF WORKLOAD                                               │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Staff       │ Current │ Completed │ Available          │ │
│ ├─────────────┼─────────┼───────────┼────────────────────┤ │
│ │ J. Garcia   │ 1       │ 8         │ 🟢                  │ │
│ │ M. Smith    │ 2       │ 12        │ 🟡 Busy             │ │
│ │ D. Johnson  │ 1       │ 5         │ 🟢                  │ │
│ └─────────────┴─────────┴───────────┴────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Productivity Tracking

Monitor team performance:

| Metric | Target | J. Garcia | M. Smith | D. Johnson |
|--------|--------|-----------|----------|------------|
| Picks/Hour | 50 | 55 | 48 | - |
| Receives/Hour | 30 | - | - | 35 |
| Accuracy | 99.5% | 99.8% | 99.2% | 100% |

---

## 13. Performance Metrics

### Warehouse KPIs

Access: **Warehouse → Analytics**

```
WAREHOUSE PERFORMANCE - January 2026
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  KEY METRICS                                                 │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐            │
│  │ Inv Accuracy│ │ Pick Accuracy│ │ Ship OnTime │            │
│  │   99.2%     │ │   99.8%      │ │   97.5%     │            │
│  │ Target: 99% │ │ Target: 99.5%│ │ Target: 98% │            │
│  │ ✓ On Target │ │ ✓ On Target  │ │ ⚠️ Below    │            │
│  └─────────────┘ └─────────────┘ └─────────────┘            │
│                                                              │
│  THROUGHPUT                                                  │
│  ├─ Lines Received: 450 (vs. 420 LM)                        │
│  ├─ Lines Picked: 1,250 (vs. 1,180 LM)                      │
│  └─ Lines Shipped: 1,100 (vs. 1,050 LM)                     │
│                                                              │
│  SPACE UTILIZATION                                           │
│  ├─ Zone A: 85% (Optimal: 80-90%)                           │
│  ├─ Zone B: 72%                                              │
│  └─ Zone C: 90% ⚠️ Near Capacity                             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Metric Definitions

| Metric | Calculation | Target |
|--------|-------------|--------|
| Inventory Accuracy | (Accurate counts / Total counts) × 100 | ≥99% |
| Pick Accuracy | (Correct picks / Total picks) × 100 | ≥99.5% |
| On-Time Shipment | (On-time ships / Total ships) × 100 | ≥98% |
| Receiving Accuracy | (Correct receipts / Total receipts) × 100 | ≥99% |
| Space Utilization | (Used space / Available space) × 100 | 80-90% |

---

## 14. Integration with Production

### Production Material Requests

Production jobs generate material requests:

```
MATERIAL REQUESTS - Today
┌─────────────────────────────────────────────────────────────┐
│ Job      │ Part     │ Qty Needed │ Qty Available │ Status  │
├──────────┼──────────┼────────────┼───────────────┼─────────┤
│ JOB-1234 │ RAW-123  │ 25         │ 450           │ ✓ Ready │
│ JOB-1234 │ COMP-789 │ 10         │ 35            │ ✓ Ready │
│ JOB-1235 │ RAW-456  │ 50         │ 175           │ ✓ Ready │
│ JOB-1236 │ COMP-ABC │ 20         │ 15            │ ⚠️ Short│
└──────────┴──────────┴────────────┴───────────────┴─────────┘
```

### Kanban Integration

Manage kanban signals:

| Part | Kanban Type | Quantity | Status |
|------|-------------|----------|--------|
| RAW-123 | Two-bin | 100/bin | ✓ Full |
| COMP-456 | Card | 50/card | 🟡 Trigger |
| FG-001 | Min-Max | 100 min | ✓ Above |

### WIP to Warehouse

Track work-in-progress returns:

1. Production completes job
2. Finished goods staged
3. Warehouse inspects (if required)
4. Put-away to FG location
5. Available for shipping

---

## 15. Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + R` | Receiving |
| `Ctrl + P` | Picking |
| `Ctrl + S` | Shipping |
| `Ctrl + I` | Inventory lookup |
| `Ctrl + /` | Search |
| `F5` | Refresh |

### Daily Warehouse Checklist

```
SHIFT START
□ Review pending receiving
□ Check pick queue and priorities
□ Verify shipping requirements
□ Assign tasks to team
□ Check equipment status

DURING SHIFT
□ Monitor task completion
□ Respond to Andons
□ Address shortages
□ Quality checks

SHIFT END
□ Complete in-progress tasks
□ Update handover notes
□ Secure warehouse
□ Log equipment status
```

### Location Quick Reference

| Zone | Contents | Pick Priority |
|------|----------|---------------|
| A | Raw Materials | Medium |
| B | Components | High |
| C | Finished Goods | High |
| STAGE | Temporary | - |
| QC | Hold area | - |

### Scanner Commands

| Command | Action |
|---------|--------|
| *RECEIVE | Start receiving mode |
| *PICK | Start picking mode |
| *PUTAWAY | Start put-away mode |
| *COUNT | Start counting mode |
| *TRANSFER | Start transfer mode |

### Emergency Contacts

| Emergency | Contact |
|-----------|---------|
| Equipment breakdown | Maintenance ext. 5100 |
| Safety incident | Safety ext. 5555 |
| IT/Scanner issue | IT ext. 5200 |
| Supervisor | Warehouse Lead ext. 5050 |

---

*Last Updated: January 2026*
*Sensei OS Version: 1.0*
*Document Owner: Warehouse Operations*
