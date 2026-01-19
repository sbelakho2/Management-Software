# Admin AI Insights Access Guide

## Complete System Access & Configuration

As Administrator, you have **unrestricted access** to all AI insights plus the ability to configure the role-insight access control system. Your access is locked at the system level and includes administrative functions.

---

## Your Capabilities

### Full Insight Access
- ✅ All 57 insight categories
- ✅ All 8 major domains
- ✅ All sensitivity levels (low, medium, high, critical)
- 🔒 Access is locked and cannot be restricted

### Administrative Functions
- 🔧 Configure role-insight mappings
- 🔧 View and export audit logs
- 🔧 Manage rate limits
- 🔧 System configuration

---

## Admin-Only Features

### Role-Insight Mappings UI

Access: **Settings → Admin → Role-Insight Mappings**

**Features:**
1. **Access Matrix View**: Visual grid showing all role-insight combinations
2. **By Role View**: Card-based view of each role's access profile
3. **Audit Log**: Complete history of access control changes
4. **Export/Import**: JSON export for backup and compliance

### Configuring Access

1. Navigate to Access Matrix
2. Find the role-insight intersection
3. Toggle access on/off (checkbox)
4. Enter a reason for the change (required)
5. Save changes

**Note:** CEO access cannot be modified. It is locked at the system level.

### Audit Log Management

View all access control changes:
- Timestamp
- Action (grant/revoke/bulk update)
- Role affected
- Insight affected
- Who made the change
- Reason provided

**Export for Compliance:**
```
Settings → Admin → Role-Insights → Audit Log → Export
```

### Rate Limit Configuration

Current factory-optimized limits (per role):
| Role Tier | Per Minute | Per Hour |
|-----------|------------|----------|
| Admin/CEO | 10,000 | 100,000 |
| Executives | 3,000-5,000 | 30,000-50,000 |
| Dept Heads | 2,000-3,000 | 20,000-30,000 |
| Specialists | 1,000-1,500 | 10,000-15,000 |
| Supervisors | 1,000-1,500 | 10,000-15,000 |
| Operators | 500 | 5,000 |
| Viewers | 300 | 3,000 |

---

## Security Administration

### Access Control Principles

1. **Least Privilege**: Users get minimum necessary access
2. **Role-Based**: Access tied to job function, not individual
3. **Audited**: All changes and access logged
4. **Tamper-Proof**: Cryptographic signing on audit logs

### Monitoring Suspicious Activity

The system automatically detects:
- Unusual access volume
- After-hours access to sensitive insights
- Access from new devices/locations
- Patterns suggesting data exfiltration

**Alert Dashboard:**
```
Settings → Security → Anomaly Alerts
```

### Compliance Reporting

Generate reports for:
- SOX (financial insight access)
- GDPR (personal data access)
- ISO 27001 (information security)
- Industry-specific requirements

---

## System Health Monitoring

### Insight Service Health
- Response times
- Error rates
- Cache hit rates
- AI model performance

### Audit System Health
- Log ingestion rate
- Storage utilization
- Signing verification status

---

## Best Practices for Admins

### Regular Reviews
- [ ] Monthly: Review access control changes
- [ ] Quarterly: Audit role-insight mappings
- [ ] Annually: Full access control review

### Change Management
1. Document the business need
2. Get approval from appropriate stakeholder
3. Make the change with clear reason
4. Verify the change works correctly
5. Monitor for issues

### Emergency Procedures

**To quickly revoke access:**
1. Settings → Admin → Role-Insights
2. Find the role
3. Toggle off affected insights
4. Reason: "Emergency revocation - [reason]"
5. Save immediately

**To investigate a breach:**
1. Export audit logs for the timeframe
2. Filter by affected user/role
3. Review access patterns
4. Coordinate with Security team

---

## API Administration

### Insight API Endpoints
- `GET /api/v1/insights/{category}` - Get insights
- `GET /api/v1/insights/access` - Check access
- `POST /api/v1/admin/insights/config` - Update config

### Rate Limit Headers
Responses include:
```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9987
X-RateLimit-Reset: 1705312800
```

---

## Configuration Files

### Role Insights Configuration
```
backend/src/sensei/services/core/role_insights_config.py
```

### Rate Limiter Configuration
```
backend/src/sensei/services/core/insight_rate_limiter.py
```

### Audit Logger Configuration
```
backend/src/sensei/services/core/insight_audit_logger.py
```

---

## Related Documentation

- [AI Insights Access Reference](../AI_INSIGHTS_ACCESS.md)
- [Security Documentation](../../maintenance/SECURITY.md)
- [Admin Guide](../../guides/admin-guide.md)
- [Configuration Reference](../../guides/configuration-reference.md)

---

*As Admin, you control the system. Use this power responsibly to protect data while enabling productivity.*
