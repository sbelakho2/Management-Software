# Maintenance Team AI Insights Access Guide

> **Status:** The maintenance mobile app features described in this guide are
> **planned — not implemented**. The web UI is the current interface.

## Equipment Intelligence for Proactive Maintenance

As a Maintenance team member, you have full access to equipment health, predictive maintenance, and reliability insights. Your access is optimized to help prevent breakdowns and maintain equipment at peak performance.

---

## Your Insight Access Summary

| Category | Access Level | Details |
|----------|--------------|---------|
| Maintenance & Equipment | ✅ Full | All equipment and maintenance insights |
| Production & Operations | ⚠️ Equipment-Related | Downtime analysis, OEE by machine |
| Quality & Compliance | ⚠️ Limited | Equipment-related quality issues |
| All Other Categories | ❌ None | Contact appropriate department |

---

## Your Insight Categories

### 🔧 Maintenance & Equipment (Full Access)

| Insight | Description | Priority |
|---------|-------------|----------|
| Equipment Health | Real-time machine status | ⚡ Check Daily |
| Predictive Maintenance | AI failure predictions | ⚡ Check Daily |
| Reliability Metrics | MTBF, MTTR analysis | 📊 Weekly Review |
| Maintenance Costs | Cost tracking by asset | 📊 Monthly Review |
| Asset Lifecycle | Equipment age/condition | 📆 Quarterly Review |
| Spare Parts Optimization | Parts inventory insights | 📊 Weekly Review |
| Energy Consumption | Equipment energy usage | 📊 Weekly Review |
| PM Compliance | Preventive maintenance tracking | ⚡ Check Daily |

### Equipment Health Dashboard

**What You Monitor:**
- Temperature anomalies
- Vibration patterns
- Pressure variations
- Electrical signatures
- Lubrication status
- Runtime hours

**Alert Levels:**
| Level | Color | Action |
|-------|-------|--------|
| Normal | 🟢 Green | Continue monitoring |
| Watch | 🟡 Yellow | Plan inspection |
| Warning | 🟠 Orange | Schedule maintenance |
| Critical | 🔴 Red | Immediate attention |

### Predictive Maintenance AI

**How It Works:**
The AI analyzes:
- Historical failure patterns
- Current sensor readings
- Operating conditions
- Maintenance history
- Similar equipment data

**What You See:**
```
┌─────────────────────────────────────────┐
│ PREDICTIVE ALERT: CNC-003               │
├─────────────────────────────────────────┤
│ Predicted Issue: Spindle bearing wear   │
│ Confidence: 87%                         │
│ Recommended Action: Replace bearing     │
│ Optimal Window: 5-10 days               │
│ Risk if Delayed: Spindle failure        │
│ Estimated Cost: $1,200 planned          │
│                 $15,000 unplanned        │
└─────────────────────────────────────────┘
```

### Reliability Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| MTBF | Mean Time Between Failures | Maximize |
| MTTR | Mean Time To Repair | Minimize |
| Availability | Uptime percentage | >95% |
| OEE | Overall Equipment Effectiveness | >85% |

---

## Daily Workflow

### Morning Check (Start of Shift)

1. **Check Equipment Health Dashboard**
   - Review all warning/critical alerts
   - Note any overnight changes
   - Prioritize inspection list

2. **Review Predictive Alerts**
   - Check new AI predictions
   - Plan proactive maintenance
   - Coordinate with production

3. **Check PM Schedule**
   - Review today's PM tasks
   - Verify parts availability
   - Confirm crew assignments

### During Shift

4. **Monitor Real-time Alerts**
   - Respond to critical alerts immediately
   - Document all interventions
   - Update work orders

5. **Track Spare Parts**
   - Log parts used
   - Note reorder needs
   - Update inventory

### End of Shift

6. **Update Maintenance Logs**
   - Complete all work orders
   - Document findings
   - Handoff to next shift

---

## Rate Limits

Your access supports continuous monitoring:
- **2,000 requests per minute**
- **20,000 requests per hour**
- **Burst: 100 in 10 seconds**

These limits support:
- Dashboard refresh every 5 seconds
- Multiple equipment monitoring
- Mobile device access on floor
- Shift change data review

---

## Dashboard Configurations

### Critical Equipment Monitor
```
Equipment Health (Critical Assets) | Predictive Alerts | PM Compliance
```

### Reliability Analysis
```
MTBF Trends | MTTR Analysis | Availability Charts | Root Cause
```

### Cost Control
```
Maintenance Costs | Spare Parts Usage | Energy Consumption
```

### Shift Handover
```
Active Alerts | Open Work Orders | Today's PM Tasks | Parts Low Stock
```

---

## Using Predictive Maintenance Effectively

### Trust the AI (But Verify)
- AI predictions are 85%+ accurate
- Always do visual inspection
- Document any AI misses for improvement

### Planning Window
- 7-day predictions allow scheduling
- Coordinate with production
- Order parts in advance

### Cost Justification
The AI shows:
- Planned maintenance cost
- Unplanned failure cost
- ROI of proactive action

### Continuous Improvement
- Feedback loop improves AI
- Report actual outcomes
- Share tribal knowledge

---

## Collaboration Points

### With Production
- Coordinate maintenance windows
- Share equipment status
- Joint root cause analysis

### With Engineering
- Design improvements
- Modification requests
- Reliability engineering

### With Purchasing
- Spare parts procurement
- Vendor specifications
- Emergency orders

### With Quality
- Equipment impact on quality
- Calibration schedules
- Process capability

---

## What You Don't Have Access To

| Category | Why | Who to Contact |
|----------|-----|----------------|
| Financial details | Cost sensitivity | Finance |
| HR data | Privacy | HR Department |
| Sales data | Not relevant | Sales Team |
| Strategic plans | Executive level | GM/CEO |

---

## Mobile Access

The maintenance mobile app provides:
- Real-time equipment alerts
- Work order management
- Parts lookup and ordering
- Photo documentation
- Offline capability for floor access

---

## Related Documentation

- [AI Insights Access Reference](../AI_INSIGHTS_ACCESS.md)
- [Equipment Maintenance Guide](../../maintenance/ML_SYSTEMS.md)
- [Troubleshooting Guide](../../guides/troubleshooting.md)

---

*Your predictive insights prevent failures before they happen. Be proactive, not reactive.*
