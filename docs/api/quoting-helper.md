# Quoting Helper API

The Quoting Helper API manages the Stage-Gate workflow for Request for Quotations (RFQs), allowing parallel engineering contributions and deterministic costing.

## Endpoints

### Generate Work Packets
Initializes the parallel engineering workflow by creating work packets for all relevant disciplines (EE, ME, MfgE, Quality, Purchasing, etc.).

`POST /api/v1/quoting-helper/rfqs/{rfq_id}/workpackets/generate`

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "discipline": "ee",
      "status": "pending",
      "due_at": "2024-01-26T12:00:00Z"
    }
  ]
}
```

### Get Work Packets
Retrieves all work packets associated with an RFQ.

`GET /api/v1/quoting-helper/rfqs/{rfq_id}/workpackets`

### Update Work Packet
Updates technical inputs, status, or notes for a specific work packet.

`PATCH /api/v1/quoting-helper/workpackets/{packet_id}`

**Body:**
```json
{
  "status": "done",
  "outputs": {
    "fine_pitch_min_mm": 0.4,
    "needs_xray": true,
    "dfm_findings": "BGA detected on bottom side."
  },
  "notes": "Review completed. Complexity is high due to fine pitch components."
}
```

### Ingest RFQ Package (Stage 0)
Processes uploaded files using Smart Ingestion (OCR + AI) to extract technical metadata.

`POST /api/v1/quoting-helper/rfqs/{rfq_id}/ingest`

**Body:**
```json
[
  {
    "storage_key": "uploads/rfq_123/bom.xlsx",
    "filename": "bom.xlsx"
  }
]
```

### Build Quote Cost (Stage 3)
Performs a deterministic cost rollup for a quote using active Rate Cards.

`POST /api/v1/quoting-helper/quotes/{quote_id}/cost/build`

### Convert to NPI (Stage 6.10)
Converts an accepted quote into a formal New Product Introduction (NPI) project.

`POST /api/v1/quoting-helper/quotes/{quote_id}/convert-to-npi`

**Response:**
```json
{
  "success": true,
  "data": {
    "project_id": "uuid",
    "project_name": "NPI: Customer Project Name",
    "project_slug": "npi-q-2024-001"
  }
}
```

### AI Suggested Clarifications
Generates minimal clarification questions based on RFQ data completeness.

`GET /api/v1/quoting-helper/ai/clarifications/suggest/{rfq_id}`

### AI Quote Memory Retrieval
Finds historically similar jobs using semantic search to assist in assumption building.

`GET /api/v1/quoting-helper/ai/quote-memory/retrieve/{rfq_id}`
