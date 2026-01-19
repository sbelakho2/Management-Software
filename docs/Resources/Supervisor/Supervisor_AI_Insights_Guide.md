# Supervisor AI Insights Access Guide

## Shift-Level AI Intelligence

As a Supervisor, you have access to production efficiency, workforce productivity, and quality metrics for your shift and work area. Your insights help you manage daily operations and your team effectively.

---

## Your Insight Access Summary

| Category | Access Level | Details |
|----------|--------------|---------|
| Production & Operations | ⚠️ Your Area | Efficiency, throughput for your shift |
| Quality & Compliance | ⚠️ Your Area | Quality metrics for your team |
| Workforce & HR | ⚠️ Your Team | Productivity and attendance |
| Maintenance & Equipment | ⚠️ Status Only | Equipment status (no cost data) |
| All Other Categories | ❌ None | Contact department heads |

---

## Your Insight Categories

### 🏭 Production (Your Shift/Area)

| Insight | What You See | Use For |
|---------|--------------|---------|
| Production Efficiency | OEE for your area | Daily targets |
| Throughput | Parts per hour/shift | Performance tracking |
| Cycle Times | Actual vs. standard | Problem identification |
| Downtime | Your equipment downtime | Improvement focus |

### ✅ Quality (Your Team)

| Insight | What You See | Use For |
|---------|--------------|---------|
| Quality Metrics | Defect rates, FPY | Team performance |
| SPC Alerts | Out-of-control signals | Quick response |
| Quality Holds | Items on hold | Production planning |

### 👥 Workforce (Your Team)

| Insight | What You See | Use For |
|---------|--------------|---------|
| Team Productivity | Output per person | Fair work distribution |
| Attendance | Today's attendance | Coverage planning |
| Skills Matrix | Team capabilities | Task assignment |

### 🔧 Equipment (Status Only)

| Insight | What You See | Use For |
|---------|--------------|---------|
| Equipment Status | Running/stopped | Production planning |
| Maintenance Alerts | Upcoming PMs | Coordination |

---

## Shift Management Dashboard

```
┌───────────────────────────────────────────────────┐
│            SHIFT A - LINE 3 - SUPERVISOR          │
├───────────────────────────────────────────────────┤
│ Target: 1,200 units │ Actual: 1,087 │ Pace: 91%  │
├───────────────────────────────────────────────────┤
│ OEE: 84%  │ Quality: 98.7%  │ Availability: 92%  │
├───────────────────────────────────────────────────┤
│ Team: 8/8 present │ Equipment: 5 running, 1 PM   │
├───────────────────────────────────────────────────┤
│ ⚠️ Alert: CNC-002 cycle time 12% above standard  │
└───────────────────────────────────────────────────┘
```

---

## Daily Supervisor Workflow

### Pre-Shift (30 min before)

1. **Check Team Status**
   - Who's working today
   - Any absences to cover
   - Skills available

2. **Review Production Targets**
   - Today's goals
   - Priority items
   - Schedule changes

3. **Check Equipment Status**
   - Any machines down
   - Scheduled maintenance
   - Quality holds

### Start of Shift

4. **Shift Briefing**
   - Share targets with team
   - Assign positions
   - Note any concerns

### During Shift

5. **Monitor Progress**
   - Check dashboard hourly
   - Address bottlenecks
   - Support team needs

6. **Respond to Alerts**
   - Quality issues
   - Equipment problems
   - Efficiency drops

### End of Shift

7. **Shift Summary**
   - Review actual vs. target
   - Document issues
   - Handoff to next supervisor

---

## Rate Limits

Your access supports shift management:
- **1,500 requests per minute**
- **15,000 requests per hour**
- **Burst: 100 in 10 seconds**

These limits support:
- Dashboard refresh every 10 seconds
- Team monitoring
- Shift start/end data pulls
- Ad-hoc checks

---

## Common Scenarios

### "We're Behind Target"

1. Check which machines are underperforming
2. Review cycle time vs. standard
3. Check for quality issues causing rework
4. Identify if attendance is affecting output
5. Decide: Speed up, add resources, or adjust target

### "Quality Alert"

1. Check SPC dashboard for pattern
2. Identify affected machine/operator
3. Contain suspect product
4. Notify Quality department
5. Implement reaction plan

### "Equipment Issue"

1. Check equipment health status
2. Determine severity
3. Call maintenance if needed
4. Reassign team to working equipment
5. Adjust production plan

### "Team Member Absent"

1. Check available skills
2. Reassign tasks
3. Adjust daily targets if needed
4. Document in shift log

---

## What You Don't Have Access To

| Category | Why | Who Has It |
|----------|-----|------------|
| Other shifts' details | Shift focus | GM/Ops Manager |
| Financial data | Cost sensitivity | Finance |
| Individual HR data | Privacy | HR Department |
| Maintenance costs | Budget control | Maintenance Manager |
| Strategic planning | Executive level | GM/Executives |

---

## Escalation Guide

### Escalate to Operations Manager
- Significant production shortfall (>15%)
- Multiple equipment failures
- Quality crisis
- Safety incident

### Escalate to Quality
- Out-of-control processes
- Customer quality issue
- Compliance concern

### Escalate to Maintenance
- Equipment breakdown
- Safety hazard
- Predicted failure alert

### Escalate to HR
- Attendance patterns
- Team conflict
- Training needs

---

## Related Documentation

- [AI Insights Access Reference](../AI_INSIGHTS_ACCESS.md)
- [Supervisor Guide](../../guides/user-guide.md)
- [Shift Management](../../guides/admin-guide.md)

---

*Your insights help your team succeed. Monitor, respond, and improve every shift.*
