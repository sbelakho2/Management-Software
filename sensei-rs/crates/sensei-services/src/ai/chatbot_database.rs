//! PostgreSQL-backed chatbot service using sqlx.
//!
//! Persists conversations and messages in the `chat_conversations` and
//! `chat_messages` tables, providing a durable chatbot backend suitable
//! for production deployments.
//!
//! When an [`AiService`](crate::ai::AiService) is provided, the chatbot
//! can leverage AI-generated insights (anomaly context, quality predictions,
//! maintenance recommendations) to enrich its responses. When no AI service
//! is configured, it falls back to keyword-based pattern matching.

use async_trait::async_trait;
use chrono::Utc;
use sensei_core::error::{Result, SenseiError};
use sensei_core::types::EntityId;
use sensei_db::models::ChatMessageModel;
use sqlx::PgPool;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::{mpsc, RwLock};
use uuid::Uuid;

use crate::ai::chatbot::{
    fallback_chat, ChatMessage, ChatResponse, ChatSamplingParams, ChatbotConfig, ChatbotService,
};

/// PostgreSQL-backed implementation of [`ChatbotService`].
///
/// Stores conversations and messages in the database for durability.
/// Uses conversation history from the database to provide context-aware
/// responses. When an optional AI service is provided, it can enrich
/// responses with AI-generated insights. Falls back to pattern matching
/// when no AI service is configured.
/// Identity of a conversation cache entry: (tenant, user, conversation).
type ConversationCacheKey = (String, String, String);

pub struct DatabaseChatbotService {
    pool: PgPool,
    config: ChatbotConfig,
    /// Optional AI service for generating context-aware responses.
    ai_service: Option<Arc<dyn crate::ai::AiService>>,
    /// In-memory cache of recent conversation IDs to avoid extra DB lookups
    /// for the `stream_chat` method which needs to share state across tasks.
    /// Keyed by (tenant, user, conversation) — a conversation cached for
    /// ONE caller must never skip ownership validation for another.
    conversation_cache: Arc<RwLock<HashMap<ConversationCacheKey, bool>>>,
}

impl DatabaseChatbotService {
    /// Create a new [`DatabaseChatbotService`] with the given connection pool.
    pub fn new(pool: PgPool) -> Self {
        Self {
            pool,
            config: ChatbotConfig::default(),
            ai_service: None,
            conversation_cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create a new [`DatabaseChatbotService`] with a custom configuration.
    pub fn with_config(pool: PgPool, config: ChatbotConfig) -> Self {
        Self {
            pool,
            config,
            ai_service: None,
            conversation_cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Create a new [`DatabaseChatbotService`] with an AI service for
    /// generating context-aware responses.
    pub fn with_ai_service(
        pool: PgPool,
        config: ChatbotConfig,
        ai_service: Arc<dyn crate::ai::AiService>,
    ) -> Self {
        Self {
            pool,
            config,
            ai_service: Some(ai_service),
            conversation_cache: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    /// Generate a unique conversation ID.
    fn generate_conversation_id() -> String {
        Uuid::new_v4().to_string()
    }

    /// Ensure a conversation exists, creating it if necessary.
    async fn ensure_conversation(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        conversation_id: &str,
    ) -> Result<()> {
        // Check the in-memory cache first to avoid a DB round-trip. The
        // cache key includes tenant + user + conversation: ownership is
        // validated on EVERY caller, never skipped via the cache.
        let cache_key = (
            tenant_id.to_string(),
            user_id.to_string(),
            conversation_id.to_string(),
        );
        {
            let cache = self.conversation_cache.read().await;
            if cache.get(&cache_key).copied().unwrap_or(false) {
                return Ok(());
            }
        }

        // Check if the conversation exists in the database.
        let exists = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(*) FROM chat_conversations WHERE id = $1::uuid AND tenant_id = $2",
        )
        .bind(Uuid::parse_str(conversation_id).map_err(|_| {
            SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}"))
        })?)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to check conversation: {e}")))?;

        if exists == 0 {
            // Create the conversation.
            let conv_id = Uuid::parse_str(conversation_id).map_err(|_| {
                SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}"))
            })?;
            let now = Utc::now();
            sqlx::query(
                r#"
                INSERT INTO chat_conversations (id, tenant_id, user_id, title, is_active, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                "#,
            )
            .bind(conv_id)
            .bind(tenant_id)
            .bind(user_id)
            .bind("")
            .bind(true)
            .bind(serde_json::Value::Object(serde_json::Map::new()))
            .bind(now)
            .bind(now)
            .execute(&self.pool)
            .await
            .map_err(|e| SenseiError::Database(format!("Failed to create conversation: {e}")))?;
        }

        // Update cache (scoped to this tenant+user).
        {
            let mut cache = self.conversation_cache.write().await;
            cache.insert(cache_key, true);
        }

        Ok(())
    }

    /// Insert a message into the database.
    async fn insert_message(&self, conversation_id: &str, role: &str, content: &str) -> Result<()> {
        let conv_uuid = Uuid::parse_str(conversation_id).map_err(|_| {
            SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}"))
        })?;
        let now = Utc::now();

        sqlx::query(
            r#"
            INSERT INTO chat_messages (id, conversation_id, role, content, metadata, created_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            "#,
        )
        .bind(Uuid::new_v4())
        .bind(conv_uuid)
        .bind(role)
        .bind(content)
        .bind(serde_json::Value::Object(serde_json::Map::new()))
        .bind(now)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to insert message: {e}")))?;

        // Update the conversation's updated_at timestamp.
        sqlx::query("UPDATE chat_conversations SET updated_at = $1 WHERE id = $2")
            .bind(now)
            .bind(conv_uuid)
            .execute(&self.pool)
            .await
            .map_err(|e| {
                SenseiError::Database(format!("Failed to update conversation timestamp: {e}"))
            })?;

        Ok(())
    }

    /// Load recent conversation history from the database.
    ///
    /// Returns up to 20 most recent messages for the given conversation,
    /// ordered chronologically.
    async fn load_conversation_history(&self, conversation_id: &str) -> Result<Vec<ChatMessage>> {
        let conv_uuid = Uuid::parse_str(conversation_id).map_err(|_| {
            SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}"))
        })?;

        let models = sqlx::query_as::<_, ChatMessageModel>(
            r#"
            SELECT id, conversation_id, role, content, metadata, created_at
            FROM chat_messages
            WHERE conversation_id = $1
            ORDER BY created_at DESC
            LIMIT 20
            "#,
        )
        .bind(conv_uuid)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to fetch conversation history: {e}")))?;

        // Reverse to get chronological order (oldest first)
        let mut messages: Vec<ChatMessage> = models
            .into_iter()
            .map(|m| ChatMessage {
                role: m.role,
                content: m.content,
                timestamp: m.created_at,
            })
            .collect();
        messages.reverse();
        Ok(messages)
    }

    /// Generate a context-aware response using conversation history,
    /// optional AI service insights, and pattern-matching fallback.
    ///
    /// Returns `(response_text, is_fallback)` where `is_fallback` is `false`
    /// when the AI service or conversation context contributed to the response.
    async fn generate_context_aware_response(
        &self,
        tenant_id: EntityId,
        message: &str,
        conversation_id: &str,
    ) -> (String, bool) {
        // Load conversation history for context
        let history = self.load_conversation_history(conversation_id).await.ok();
        let has_history = history.as_ref().is_some_and(|h| !h.is_empty());

        // If an AI service is available, attempt to enrich the response
        // with AI-generated insights based on the user's message.
        if let Some(ref ai_service) = self.ai_service {
            let enriched = self
                .try_ai_enriched_response(ai_service, tenant_id, message, history.as_deref())
                .await;
            if let Some(response) = enriched {
                return (response, false);
            }
        }

        // Build a context-aware response using conversation history
        if has_history {
            if let Some(contextual_response) =
                self.build_contextual_response(message, history.as_deref().unwrap())
            {
                return (contextual_response, false);
            }
        }

        // Fall back to pattern matching
        (fallback_chat(message), true)
    }

    /// Attempt to generate an AI-enriched response using the AI service.
    ///
    /// Examines the user's message for domain-specific keywords, resolves the
    /// referenced entity (product / equipment / NCR / work order) by name or
    /// number in the database, and queries the AI service for relevant
    /// predictions. Enrichment is skipped when no entity can be resolved, so
    /// the tenant id is never passed as a fake product/equipment/entity id.
    async fn try_ai_enriched_response(
        &self,
        ai_service: &Arc<dyn crate::ai::AiService>,
        tenant_id: EntityId,
        message: &str,
        history: Option<&[ChatMessage]>,
    ) -> Option<String> {
        let lower = message.to_lowercase();

        // Check for quality-related queries
        if lower.contains("quality")
            || lower.contains("defect")
            || lower.contains("ncr")
            || lower.contains("inspection")
        {
            // Resolve the product the user is asking about; skip enrichment
            // when nothing in the message matches a real product.
            let product_id = self.resolve_product_id(tenant_id, message).await?;
            if let Ok(prediction) = ai_service
                .predict_quality(
                    tenant_id,
                    product_id,
                    serde_json::Value::Object(serde_json::Map::new()),
                )
                .await
            {
                let history_context = history.map_or(String::new(), |h| {
                    let len = h.len();
                    h.iter()
                        .skip(len.saturating_sub(4))
                        .map(|m| format!("{}: {}", m.role, m.content))
                        .collect::<Vec<_>>()
                        .join("\n")
                });

                // Item 27/42: TPS reasoning order — observation FIRST, never
                // a jump from prediction straight to a countermeasure. The
                // model output is a HYPOTHESIS, not a verified fact; the
                // reply asks the questions that distinguish causes before
                // any recommendation is offered.
                let rate = prediction.predicted_defect_rate.unwrap_or(0.0);
                let cpk = prediction.predicted_cpk.unwrap_or(0.0);
                let mut response = format!(
                    "A model estimate suggests a defect rate of {:.1}% (CpK {:.2}). \
                     This is a HYPOTHESIS about the current condition, not a \
                     verified measurement. Before acting on it:",
                    rate * 100.0,
                    cpk,
                );
                response.push_str(
                    "  1. What is the CURRENT STANDARD for this parameter set — and is \
                       the process actually running to it?\n\
                       2. What was OBSERVED directly at the process (measurements, \
                       samples, timestamps), not inferred from the model?\n\
                       3. When and where did the deviation first appear?\n\
                       4. What changed immediately before it (material, method, \
                       machine, operator, setup)?\n\
                       5. Which possible cause can we TEST, and what result would \
                       confirm or refute it?",
                );
                if rate > 0.05 {
                    response.push_str(
                        "The estimate is above the 5% threshold — worth a \
                         CONTAINMENT step while the observation questions above \
                         are answered: contain the risk to the customer first, \
                         then compare actual vs standard at the process.",
                    );
                }

                if !history_context.is_empty() {
                    response.push_str(&format!(
                        "\n\nConsidering our previous discussion:\n{history_context}"
                    ));
                }

                return Some(response);
            }
        }

        // Check for maintenance-related queries
        if lower.contains("maintenance")
            || lower.contains("equipment")
            || lower.contains("failure")
            || lower.contains("predict")
        {
            // Resolve the equipment by name/number; skip when unknown.
            let equipment_id = self.resolve_equipment_id(tenant_id, message).await?;
            if let Ok(maintenance) = ai_service
                .predict_maintenance(tenant_id, equipment_id)
                .await
            {
                return Some(format!(
                    "Maintenance model estimate (HYPOTHESIS, not a verified fact):\n\
                     - Failure probability: {:.1}%\n\
                     - Estimated remaining life: {}\n\
                     - Risk level: {}\n\
                     - Model-suggested maintenance date: {}\n\
                     \nBefore acting, compare with the actual condition: is the \
                     equipment running to its standard, what was directly observed \
                     (noise, vibration, temperature, output trend), and what changed \
                     since the last maintenance? Then decide whether the suggested \
                     actions below are supported by the observation.\n\
                     \nCandidate actions to evaluate:\n{}",
                    maintenance.failure_probability * 100.0,
                    maintenance
                        .estimated_remaining_life_hours
                        .map(|h| format!("{h:.0} hours"))
                        .unwrap_or_else(|| "unavailable".to_string()),
                    maintenance.risk_level,
                    maintenance
                        .recommended_maintenance_date
                        .map(|d| d.format("%Y-%m-%d").to_string())
                        .unwrap_or_else(|| "unavailable".to_string()),
                    maintenance
                        .suggested_actions
                        .iter()
                        .map(|a| format!("• {a}"))
                        .collect::<Vec<_>>()
                        .join("\n"),
                ));
            }
        }

        // Check for anomaly-related queries
        if lower.contains("anomaly")
            || lower.contains("unusual")
            || lower.contains("abnormal")
            || lower.contains("detect")
        {
            // Determine the entity type the user is referring to and resolve a
            // real entity id; skip enrichment when nothing matches.
            let (entity_type, entity_id) = self.resolve_anomaly_entity(tenant_id, message).await?;
            if let Ok(anomalies) = ai_service
                .detect_anomalies(tenant_id, &entity_type, entity_id)
                .await
            {
                if !anomalies.is_empty() {
                    let anomaly_reports: Vec<String> = anomalies
                        .iter()
                        .take(3)
                        .map(|a| {
                            format!(
                                "• {} (confidence: {:.0}%, score: {:.2}): {}",
                                a.predicted_failure,
                                a.confidence * 100.0,
                                a.anomaly_score,
                                a.recommended_action,
                            )
                        })
                        .collect();

                    return Some(format!(
                        "The system flags the following anomalies as HYPOTHESES, not \
                         verified facts:\n{}\n\n\
                         For each one, the useful next step is to go see the actual \
                         condition: what is the standard, what was observed, what \
                         changed, and what evidence would confirm or refute the \
                         hypothesis? A countermeasure chosen without that comparison \
                         is a guess.",
                        anomaly_reports.join("\n"),
                    ));
                }
            }
        }

        None
    }

    /// Extract candidate lookup tokens from a message (bounded, non-trivial).
    fn lookup_tokens(message: &str) -> Vec<String> {
        message
            .split(|c: char| !c.is_alphanumeric())
            .filter(|t| t.len() >= 3)
            .map(|t| t.to_lowercase())
            .take(5)
            .collect()
    }

    /// Resolve a product id referenced in the message by product number or
    /// name. Returns `None` when nothing matches.
    async fn resolve_product_id(&self, tenant_id: EntityId, message: &str) -> Option<Uuid> {
        let tokens = Self::lookup_tokens(message);
        if tokens.is_empty() {
            return None;
        }
        let patterns: Vec<String> = tokens.iter().map(|t| format!("{t}%")).collect();
        sqlx::query_scalar::<_, Uuid>(
            "SELECT id FROM products \
             WHERE tenant_id = $1 AND (product_number ILIKE ANY($2) OR name ILIKE ANY($2)) \
             ORDER BY created_at LIMIT 1",
        )
        .bind(tenant_id)
        .bind(&patterns)
        .fetch_optional(&self.pool)
        .await
        .ok()
        .flatten()
    }

    /// Resolve an equipment id referenced in the message by equipment number
    /// or name. Returns `None` when nothing matches.
    async fn resolve_equipment_id(&self, tenant_id: EntityId, message: &str) -> Option<Uuid> {
        let tokens = Self::lookup_tokens(message);
        if tokens.is_empty() {
            return None;
        }
        let patterns: Vec<String> = tokens.iter().map(|t| format!("{t}%")).collect();
        sqlx::query_scalar::<_, Uuid>(
            "SELECT id FROM equipment \
             WHERE tenant_id = $1 AND (equipment_number ILIKE ANY($2) OR name ILIKE ANY($2)) \
             ORDER BY created_at LIMIT 1",
        )
        .bind(tenant_id)
        .bind(&patterns)
        .fetch_optional(&self.pool)
        .await
        .ok()
        .flatten()
    }

    /// Resolve the (entity_type, entity_id) for an anomaly query by looking up
    /// the referenced entity by its number/name. Returns `None` when the
    /// message does not clearly reference a known entity.
    async fn resolve_anomaly_entity(
        &self,
        tenant_id: EntityId,
        message: &str,
    ) -> Option<(String, Uuid)> {
        let tokens = Self::lookup_tokens(message);
        if tokens.is_empty() {
            return None;
        }
        let patterns: Vec<String> = tokens.iter().map(|t| format!("{t}%")).collect();

        // Explicit UUIDs are resolved directly.
        for token in &tokens {
            if let Ok(id) = Uuid::parse_str(token) {
                return Some(("entity".to_string(), id));
            }
        }

        // NCR: match nc_number or title in the JSONB quality_ncrs rows.
        if message.to_lowercase().contains("ncr") {
            if let Ok(Some(id)) = sqlx::query_scalar::<_, Uuid>(
                "SELECT id FROM quality_ncrs \
                 WHERE tenant_id = $1 \
                   AND (data->>'nc_number' ILIKE ANY($2) OR data->>'title' ILIKE ANY($2)) \
                 ORDER BY created_at DESC LIMIT 1",
            )
            .bind(tenant_id)
            .bind(&patterns)
            .fetch_optional(&self.pool)
            .await
            {
                return Some(("ncr".to_string(), id));
            }
            return None;
        }

        // Work orders.
        if message.to_lowercase().contains("work order") || message.to_lowercase().contains("wo ") {
            if let Ok(Some(id)) = sqlx::query_scalar::<_, Uuid>(
                "SELECT id FROM work_orders \
                 WHERE tenant_id = $1 AND work_order_number ILIKE ANY($2) \
                 ORDER BY created_at DESC LIMIT 1",
            )
            .bind(tenant_id)
            .bind(&patterns)
            .fetch_optional(&self.pool)
            .await
            {
                return Some(("work_order".to_string(), id));
            }
            return None;
        }

        // Equipment (matches "equipment", "machine", "asset" queries).
        if let Ok(Some(id)) = sqlx::query_scalar::<_, Uuid>(
            "SELECT id FROM equipment \
             WHERE tenant_id = $1 AND (equipment_number ILIKE ANY($2) OR name ILIKE ANY($2)) \
             ORDER BY created_at LIMIT 1",
        )
        .bind(tenant_id)
        .bind(&patterns)
        .fetch_optional(&self.pool)
        .await
        {
            return Some(("equipment".to_string(), id));
        }

        None
    }

    /// Build a contextual response using conversation history.
    ///
    /// Analyzes the conversation history to provide continuity and
    /// references to previous topics discussed.
    fn build_contextual_response(&self, message: &str, history: &[ChatMessage]) -> Option<String> {
        // Extract topics from recent conversation
        let recent_topics: Vec<&str> = history
            .iter()
            .filter(|m| m.role == "user")
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .take(3)
            .flat_map(|m| {
                let lower = m.content.to_lowercase();
                let mut topics = Vec::new();
                if lower.contains("quality")
                    || lower.contains("ncr")
                    || lower.contains("inspection")
                {
                    topics.push("quality");
                }
                if lower.contains("maintenance") || lower.contains("equipment") {
                    topics.push("maintenance");
                }
                if lower.contains("production") || lower.contains("work order") {
                    topics.push("production");
                }
                if lower.contains("supply chain") || lower.contains("inventory") {
                    topics.push("supply chain");
                }
                if lower.contains("finance") || lower.contains("invoice") {
                    topics.push("finance");
                }
                topics
            })
            .collect();

        if recent_topics.is_empty() {
            return None;
        }

        // Get the base pattern-matched response
        let base_response = fallback_chat(message);

        // Add context from previous conversation
        let primary_topic = recent_topics.first().unwrap_or(&"");
        let context_suffix = format!(
            "\n\n*Based on our conversation about {primary_topic}, I'm providing this response with your previous questions in mind.*"
        );

        Some(format!("{base_response}{context_suffix}"))
    }
}

#[async_trait]
impl ChatbotService for DatabaseChatbotService {
    async fn chat(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        message: &str,
        conversation_id: Option<&str>,
        sampling: Option<ChatSamplingParams>,
    ) -> Result<ChatResponse> {
        let conv_id = conversation_id
            .map(|s| s.to_string())
            .unwrap_or_else(Self::generate_conversation_id);

        // Ensure the conversation exists.
        self.ensure_conversation(tenant_id, user_id, &conv_id)
            .await?;

        // Save the user message.
        self.insert_message(&conv_id, "user", message).await?;

        // Generate a context-aware response using conversation history
        // and optional AI service.
        let (response_text, is_fallback) = self
            .generate_context_aware_response(tenant_id, message, &conv_id)
            .await;

        // Bound the response length with the effective token budget (an
        // approximation: one whitespace-delimited word ≈ one token). A
        // per-request sampling override takes precedence over the config.
        let max_tokens = sampling
            .as_ref()
            .map(|s| s.max_tokens_or(self.config.max_tokens))
            .unwrap_or(self.config.max_tokens);
        let response_text = if max_tokens > 0 {
            response_text
                .split_whitespace()
                .take(max_tokens)
                .collect::<Vec<_>>()
                .join(" ")
        } else {
            response_text
        };

        // Save the assistant message.
        self.insert_message(&conv_id, "assistant", &response_text)
            .await?;

        Ok(ChatResponse {
            message: ChatMessage::assistant(response_text),
            conversation_id: conv_id,
            is_fallback,
        })
    }

    async fn stream_chat(
        &self,
        tenant_id: EntityId,
        user_id: EntityId,
        message: &str,
        conversation_id: Option<&str>,
        sampling: Option<ChatSamplingParams>,
    ) -> Result<mpsc::Receiver<Result<String>>> {
        let (tx, rx) = mpsc::channel(64);

        // Perform the chat to persist messages.
        let response = self
            .chat(tenant_id, user_id, message, conversation_id, sampling)
            .await?;

        let response_text = response.message.content;

        tokio::spawn(async move {
            for word in response_text.split(' ') {
                if tx.send(Ok(format!("{word} "))).await.is_err() {
                    break;
                }
                tokio::time::sleep(std::time::Duration::from_millis(20)).await;
            }
        });

        Ok(rx)
    }

    async fn get_conversation_history(
        &self,
        tenant_id: EntityId,
        conversation_id: &str,
    ) -> Result<Vec<ChatMessage>> {
        let conv_uuid = Uuid::parse_str(conversation_id).map_err(|_| {
            SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}"))
        })?;

        // Verify the conversation exists and belongs to this tenant.
        let conv_exists = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(*) FROM chat_conversations WHERE id = $1 AND tenant_id = $2",
        )
        .bind(conv_uuid)
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to check conversation: {e}")))?;

        if conv_exists == 0 {
            return Err(SenseiError::NotFound(format!(
                "Conversation {conversation_id} not found"
            )));
        }

        let models = sqlx::query_as::<_, ChatMessageModel>(
            r#"
            SELECT id, conversation_id, role, content, metadata, created_at
            FROM chat_messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            "#,
        )
        .bind(conv_uuid)
        .fetch_all(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to fetch messages: {e}")))?;

        Ok(models
            .into_iter()
            .map(|m| ChatMessage {
                role: m.role,
                content: m.content,
                timestamp: m.created_at,
            })
            .collect())
    }
}
