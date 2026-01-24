# Quotes API

The Quotes API manages customer-facing quotations, including versioning, approval workflows, and PDF generation.

## Endpoints

### List Quotes
Retrieves a paginated list of quotes.

`GET /api/v1/quotes/`

### Create Quote
Creates a new quote, usually associated with an RFQ.

`POST /api/v1/quotes/`

### Get Quote Details
Retrieves full details for a specific quote, including line items and margin analysis.

`GET /api/v1/quotes/{id}`

### Update Quote
Updates an existing quote.

`PATCH /api/v1/quotes/{id}`

### Request Approval
Submits a quote for internal approval if it exceeds risk or margin thresholds.

`POST /api/v1/quotes/{id}/approve/request`

### Publish (Freeze Version)
Generates a customer-ready PDF and freezes the current quote version.

`POST /api/v1/quotes/{id}/publish`

### Advanced Costing
For deterministic cost rollups based on active Rate Cards, refer to the [Quoting Helper API](./quoting-helper.md).
