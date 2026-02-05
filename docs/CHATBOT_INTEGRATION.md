# Sensei OS Chatbot Integration Guide

## Overview

The Sensei OS Chatbot is an RBAC-aware conversational AI assistant for manufacturing operations. It provides natural language interface for:
- **Data Queries**: RFQs, quotes, work orders with role-based filtering
- **Email Drafting**: Context-aware email composition using existing email service
- **Task Management**: Creating, listing, and completing tasks
- **Problem Solving**: A3 reports, 5 Whys analysis guidance
- **Knowledge Queries**: TPS/Lean manufacturing knowledge base

All responses are filtered through RBAC and PII controls to ensure data security.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Chat API Endpoint                           │
│                    POST /api/v1/chat/message                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ChatService                                  │
│  ┌────────────┐  ┌────────────────┐  ┌────────────────────┐        │
│  │  Intent    │  │   Context      │  │    Action          │        │
│  │ Classifier │  │   Builder      │  │   Executor         │        │
│  └─────┬──────┘  └───────┬────────┘  └─────────┬──────────┘        │
│        │                 │                     │                    │
│        ▼                 ▼                     ▼                    │
│  ┌────────────────────────────────────────────────────────┐        │
│  │           LLM Response Generation (llama-cpp)          │        │
│  └────────────────────────┬───────────────────────────────┘        │
│                           │                                         │
│  ┌────────────────────────┴───────────────────────────────┐        │
│  │  ┌─────────────────┐  ┌─────────────────────────────┐  │        │
│  │  │  RBAC Filter    │  │  Response Sanitizer (PII)   │  │        │
│  │  └─────────────────┘  └─────────────────────────────┘  │        │
│  └────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```

## VPS Deployment Configuration

The chatbot is optimized for VPS deployment with CPU-only inference. Configuration settings in `core/config.py`:

```python
# Model settings
CHATBOT_MODEL_PATH: str = "backend/models/llm/qwen2.5-3b-instruct-q4_k_m.gguf"
CHATBOT_CONTEXT_LENGTH: int = 2048  # Reduced for VPS memory
CHATBOT_MAX_TOKENS: int = 256       # Shorter responses for faster inference

# VPS optimization
CHATBOT_N_GPU_LAYERS: int = 0       # CPU only - no GPU
CHATBOT_N_THREADS: int = 2          # Conservative for shared VPS
CHATBOT_BATCH_SIZE: int = 128       # Small batch for low memory
CHATBOT_ENABLE_MMAP: bool = True    # Memory mapping for efficiency
CHATBOT_ENABLE_MLOCK: bool = False  # Don't lock memory on shared VPS
CHATBOT_ROPE_SCALING_TYPE: int = 0  # Linear context scaling
CHATBOT_TEMPERATURE: float = 0.7    # Balanced creativity/accuracy
```

## Quick Start

### 1. Download Model

```bash
# Download recommended model for VPS (Qwen2.5-3B)
python backend/scripts/download_chatbot_model.py --model qwen3b

# Or for very limited resources
python backend/scripts/download_chatbot_model.py --model tinyllama
```

### 2. Install Dependencies

```bash
# Install llama-cpp-python with CPU support
pip install llama-cpp-python

# Or with OpenBLAS for better performance
CMAKE_ARGS="-DGGML_BLAS=ON" pip install llama-cpp-python --force-reinstall
```

### 3. Use the Service

```python
from sensei.services.ai.chatbot import ChatService, create_chat_service
from sensei.services.ai.chatbot.context_builder import UserContext

# Create service
chat_service = create_chat_service()

# Create user context
user = UserContext(
    user_id=uuid4(),
    email="user@example.com",
    name="John Doe",
    roles={"sales_engineer"},
    permissions={"read:rfq", "write:rfq"},
)

# Send message
response = await chat_service.chat("Show my pending RFQs", user)
print(response.message)
```

## API Endpoints

### POST /api/v1/chat/message
Send a chat message and receive a response.

**Request:**
```json
{
    "message": "Show my pending RFQs",
    "session_id": "optional-uuid-for-continuity"
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        "message": "Here are your 3 pending RFQs...",
        "intent": "data_lookup",
        "action_result": {
            "action_type": "data_lookup",
            "status": "completed",
            "message": "Found 3 RFQs",
            "data": {...}
        },
        "suggestions": [
            "Show details for RFQ-123",
            "Draft follow-up email"
        ],
        "session_id": "uuid"
    }
}
```

### GET /api/v1/chat/sessions
List active chat sessions for the current user.

### DELETE /api/v1/chat/sessions/{session_id}
End a specific chat session.

### GET /api/v1/chat/intents
List all supported intent types.

### GET /api/v1/chat/health
Health check for the chat service.

## Intent Classification

The classifier recognizes these intent types:

| Intent | Description | Example |
|--------|-------------|---------|
| `DATA_LOOKUP` | Query for information | "Show pending RFQs" |
| `EMAIL_DRAFT` | Draft an email | "Draft email to customer about quote" |
| `TASK_CREATE` | Create a task | "Remind me to follow up tomorrow" |
| `TASK_LIST` | List tasks | "What's on my plate?" |
| `APPROVAL_LIST` | List pending approvals | "Show my approvals" |
| `REPORT_GENERATE` | Generate reports | "Weekly sales summary" |
| `KNOWLEDGE_QUERY` | TPS/Lean questions | "Explain kaizen" |
| `A3_ASSIST` | A3 report help | "Help me with an A3" |
| `FIVE_WHYS` | Root cause analysis | "Start 5 whys analysis" |
| `NAVIGATION` | Navigate to page | "Go to the RFQ dashboard" |
| `HELP` | Help requests | "What can you do?" |

## RBAC Integration

### Role-Based Access Matrix

The chatbot respects the existing 24-role RBAC hierarchy:

| Data Type | Roles with Access |
|-----------|-------------------|
| RFQ Data | admin, ceo, gm, exec, sales, sales_engineer, estimator, quality, ops, engineering |
| Quote Data | admin, ceo, gm, exec, sales, sales_engineer, estimator, finance, quality |
| Work Orders | admin, ceo, gm, exec, ops, quality, engineering, supervisor, operator |
| User Info | admin, hr |
| Financial Data | admin, ceo, gm, exec, finance |
| Salary/Compensation | admin, hr, ceo |

### Sensitive Field Protection

Fields automatically masked/filtered:
- SSN: Masked to `***-**-XXXX`
- Credit Cards: Masked to `**** **** **** XXXX`
- Salaries: Filtered unless user has HR/Admin/CEO role
- Personal contact info: Masked for non-authorized roles

## Role-Specific System Prompts

Each role category has tailored system prompts:

- **Executive**: Focus on KPIs, strategic decisions, high-level summaries
- **Manager**: Operational metrics, team performance, approval workflows
- **Sales**: Customer focus, RFQs, quotes, follow-ups
- **Engineering**: Technical specs, work orders, quality metrics
- **Operator**: Task lists, work instructions, shift information
- **Viewer**: Read-only access, basic inquiries

## Email Integration

The chatbot integrates with the existing `AIEmailDraftingService`:

```python
# When user says "Draft follow-up email for RFQ-123"
# The chatbot will:
# 1. Look up RFQ-123 details (RBAC filtered)
# 2. Use AIEmailDraftingService to generate draft
# 3. Return draft for review
# 4. Wait for confirmation before sending
```

## Performance Optimization

### VPS Memory Usage

| Model | VRAM/RAM | Response Time |
|-------|----------|---------------|
| TinyLlama 1.1B | ~1GB | ~1-2s |
| Qwen2.5 1.5B | ~1.5GB | ~2-3s |
| Qwen2.5 3B | ~2.5GB | ~3-5s |
| Phi-3.5 mini | ~3GB | ~2-4s |

### Optimization Tips

1. **Use Q4_K_M quantization** - Best quality/size ratio
2. **Enable mmap** - Memory-efficient model loading
3. **Limit context** - 2048 tokens is sufficient for most queries
4. **Batch requests** - Group multiple users' requests when possible
5. **Session cleanup** - Automatically cleanup inactive sessions (24h default)

## Testing

Run the test suite:

```bash
# Run all chatbot tests
pytest tests/services/ai/chatbot/ -v

# Run API tests
pytest tests/api/v1/test_chat.py -v

# Run with coverage
pytest tests/services/ai/chatbot/ --cov=sensei.services.ai.chatbot
```

## Troubleshooting

### Common Issues

**Model not loading:**
```bash
# Verify model exists
ls -la backend/models/llm/

# Re-download if needed
python scripts/download_chatbot_model.py --model qwen3b --force
```

**Out of memory:**
```python
# Reduce context length
CHATBOT_CONTEXT_LENGTH = 1024

# Use smaller model
python scripts/download_chatbot_model.py --model tinyllama
```

**Slow responses:**
```python
# Increase threads (if VPS allows)
CHATBOT_N_THREADS = 4

# Reduce max tokens
CHATBOT_MAX_TOKENS = 128
```

## Security Considerations

1. **All queries are RBAC filtered** - Users only see data they're authorized to access
2. **PII is masked** - Sensitive information is automatically redacted
3. **Audit logging** - All interactions are logged for compliance
4. **Session isolation** - Each user's context is isolated
5. **Injection protection** - LLM outputs are sanitized for prompt injection attempts

## Future Enhancements

- [ ] Voice input/output support
- [ ] Multi-language support
- [ ] Custom knowledge base training
- [ ] Integration with external systems (ERP, CRM)
- [ ] Proactive notifications/suggestions
- [ ] Analytics dashboard for usage patterns
