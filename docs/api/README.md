# API Documentation Index

Complete API reference for Sensei Manufacturing Management System.

## Base URL

```
Production: https://sensei.yourdomain.com/api
Development: http://localhost:8000/api
```

## Authentication

All API requests require authentication using JWT tokens.

```http
Authorization: Bearer <your_jwt_token>
```

See [Authentication Guide](../guides/authentication.md) for details.

## API Endpoints

### Core Resources

#### Accounts & Contacts
- [Accounts API](./accounts.md) - Customer and supplier accounts
- [Contacts API](./contacts.md) - Contact management

#### Opportunities & Sales
- [Opportunities API](./opportunities.md) - Sales pipeline management
- [RFQs API](./rfqs.md) - Request for Quote processing
- [Quotes API](./quotes.md) - Quote creation and management
- [Quoting Helper API](./quoting-helper.md) - Parallel engineering work packets and costing

#### Products & Manufacturing
- [Products API](./products.md) - Product catalog
- [Work Centers API](./work-centers.md) - Manufacturing work centers
- [Work Orders API](./work-orders.md) - Production work orders
- [Production Cells API](./production-cells.md) - Cell management

#### Quality & Compliance
- [Quality API](./quality.md) - Quality inspection and control
- [CTQ API](./ctq.md) - Critical to Quality characteristics
- [Risk API](./risk.md) - Risk management and FMEA
- [A3 API](./a3.md) - A3 problem-solving

#### Project Management
- [Obeya API](./obeya.md) - Obeya room management
- [Kanban API](./kanban.md) - Kanban board management
- [Tasks API](./tasks.md) - Task tracking

#### Training & Learning
- [Training API](./training.md) - Training records
- [Training Matrix API](./training-matrix.md) - Skills matrix
- [Learning API](./learning.md) - Learning recommendations

#### Operations
- [Today Screen API](./today.md) - Daily operations dashboard
- [LSW API](./lsw.md) - Leader Standard Work
- [Andon API](./andon.md) - Andon alerts and escalation
- [Standard Work API](./standard-work.md) - Standard work instructions

#### System & Admin
- [Users API](./users.md) - User management
- [Auth API](./auth.md) - Authentication and authorization
- [Health API](./health.md) - System health checks
- [Audit Logs API](./audit-logs.md) - Audit trail
- [Attachments API](./attachments.md) - File attachments
- [Search API](./search.md) - Global search

#### Advanced Features
- [Knowledge Pack API](./knowledge-pack.md) - Knowledge base management
- [Smart Ingestion API](./smart-ingestion.md) - OCR and AI document processing
- [State Machines API](./state-machines.md) - Workflow state machines
- [KPI Metrics API](./kpi.md) - Key Performance Indicators
- [Saved Views API](./saved-views.md) - User-defined views
- [Notification Triggers API](./notification-triggers.md) - Event notifications
- [Escalation Policies API](./escalation-policy.md) - Alert escalation

## Common Patterns

### Pagination

List endpoints support pagination:

```http
GET /api/v1/accounts?page=1&page_size=50
```

Response:
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 50,
  "pages": 3
}
```

### Filtering

Most list endpoints support filtering:

```http
GET /api/v1/accounts?status=active&created_after=2024-01-01
```

### Sorting

Sort results using `sort_by` and `sort_order`:

```http
GET /api/v1/accounts?sort_by=created_at&sort_order=desc
```

### Error Responses

Standard error response format:

```json
{
  "detail": "Error message",
  "error_code": "RESOURCE_NOT_FOUND",
  "status_code": 404
}
```

Common status codes:
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### Rate Limiting

API requests are rate-limited:
- **Authenticated**: 1000 requests/hour
- **Unauthenticated**: 100 requests/hour

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1609459200
```

## Webhooks

Subscribe to events using webhooks. See [Webhooks Guide](../guides/webhooks.md).

## SDKs

Official SDKs:
- [Python SDK](https://github.com/sensei/python-sdk)
- [JavaScript/TypeScript SDK](https://github.com/sensei/js-sdk)
- [Go SDK](https://github.com/sensei/go-sdk)

## Interactive Documentation

Explore the API interactively:
- **Swagger UI**: https://sensei.yourdomain.com/api/docs
- **ReDoc**: https://sensei.yourdomain.com/api/redoc

## Support

- **API Status**: https://status.sensei.com
- **Support Email**: api-support@sensei.com
- **Developer Forum**: https://community.sensei.com

## Versioning

Current API version: **v1**

Version is specified in the URL path: `/api/v1/`

Breaking changes will result in a new API version.

## Changelog

See [API Changelog](./changelog.md) for version history.
