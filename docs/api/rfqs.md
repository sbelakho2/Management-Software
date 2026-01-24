# RFQs API

The RFQs API manages the lifecycle of customer Requests for Quotation (RFQs), from initial intake to final outcome tracking.

## Endpoints

### List RFQs
Retrieves a paginated list of RFQs with optional filtering by status, priority, and customer.

`GET /api/v1/rfqs/`

### Create RFQ
Creates a new RFQ record. This is typically the first step in the sales pipeline.

`POST /api/v1/rfqs/`

### Get RFQ Details
Retrieves full details for a specific RFQ, including line items and associated metadata.

`GET /api/v1/rfqs/{id}`

### Update RFQ
Updates an existing RFQ.

`PATCH /api/v1/rfqs/{id}`

### Set RFQ Outcome (Decision)
Marks an RFQ as Won, Lost, or No-Bid. Requires elevated permissions (Admin, GM, Sales Engineer).

`POST /api/v1/rfqs/{id}/decision`

**Body:**
```json
{
  "status": "won",
  "reason": "Competitive pricing and lead time.",
  "competitor_id": "uuid"
}
```

### Advanced Workflows
For complex industrial RFQs, refer to the [Quoting Helper API](./quoting-helper.md) which handles:
- Parallel engineering reviews.
- Smart ingestion of technical packages.
- Deterministic costing.
