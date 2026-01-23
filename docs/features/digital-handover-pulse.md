# Digital Shift Handover & The Sensei Pulse

This document details the implementation and usage of the Digital Shift Handover and The Sensei Pulse features in Sensei OS.

## 1. Digital Shift Handover

The Digital Shift Handover system is designed to eliminate communication gaps between shifts on the factory floor. It follows the Lean **SQDCP** (Safety, Quality, Delivery, Cost, People) framework to ensure structured and comprehensive knowledge transfer.

### Key Components
- **Structured Notes**: Operators and Team Leads record status updates categorized by Safety, Quality, Delivery, etc.
- **Station-Specific**: Notes are tied to specific Stations and Work Orders, providing context for the incoming shift.
- **Acknowledgement Loop**: Incoming operators must acknowledge handover notes, creating a clear audit trail of knowledge transfer.
- **Today Screen Integration**: Active, unacknowledged handovers are surfaced immediately on the operator's Today screen dashboard.

### Technical Implementation
- **Model**: `ShiftHandoverNote` in `backend/src/sensei/models/production.py`.
- **Service**: `HandoverService` in `backend/src/sensei/services/production/handover_service.py`.
- **API**: `/api/v1/production/handovers`.

## 2. The Sensei Pulse

The Sensei Pulse is a real-time site-wide announcement system that serves as the "common thread" for all 24 user roles. It ensures that everyone from the shop floor operator to the CEO is aligned with critical site status, goals, and announcements.

### Key Components
- **Global Visibility**: Pulses are displayed at the top of the Today screen for all users.
- **Severity Levels**: Support for `info`, `warning`, and `critical` severity, with corresponding high-visibility styling (following RAMS industrial standards).
- **Metric Highlights**: Pulses can highlight specific KPIs (e.g., "Daily Output: 1,200 units") to drive immediate alignment.
- **Expiry Logic**: Announcements can be scheduled to expire automatically after a set period.

### Technical Implementation
- **Model**: `GlobalPulse` in `backend/src/sensei/models/production.py`.
- **Service**: `PulseService` in `backend/src/sensei/services/ops/pulse_service.py`.
- **API**: `/api/v1/pulse`.

## UI/UX Standards (Sensei RAMS)

Both features strictly follow the **Sensei RAMS 3.0** industrial design language:
- **Aggressive Industrial Typography**: Using `font-black` and `uppercase` for high-impact labels.
- **Functional Color Palette**: Utilizing `rams-orange` for warnings and `rams-red` for critical alerts.
- **Module Layout**: Components are wrapped in RAMS modules (`bg-rams-module`) with consistent borders (`border-rams-line`) and headers (`bg-rams-panel`).
- **High Visibility**: Critical pulses use animation and distinctive icons to ensure immediate attention.
