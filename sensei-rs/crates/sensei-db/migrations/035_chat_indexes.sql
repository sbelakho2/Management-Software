-- Chat history indexes.
--
-- Support the chatbot service's conversation-scoped message queries and
-- tenant-scoped conversation lookups.

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation
    ON chat_messages (conversation_id, created_at);
CREATE INDEX IF NOT EXISTS idx_chat_conversations_tenant_user
    ON chat_conversations (tenant_id, user_id);
