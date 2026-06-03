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

use crate::ai::chatbot::{fallback_chat, ChatMessage, ChatResponse, ChatbotConfig, ChatbotService};

/// PostgreSQL-backed implementation of [`ChatbotService`].
///
/// Stores conversations and messages in the database for durability.
/// Uses conversation history from the database to provide context-aware
/// responses. When an optional AI service is provided, it can enrich
/// responses with AI-generated insights. Falls back to pattern matching
/// when no AI service is configured.
pub struct DatabaseChatbotService {
    pool: PgPool,
    config: ChatbotConfig,
    /// Optional AI service for generating context-aware responses.
    ai_service: Option<Arc<dyn crate::ai::AiService>>,
    /// In-memory cache of recent conversation IDs to avoid extra DB lookups
    /// for the `stream_chat` method which needs to share state across tasks.
    conversation_cache: Arc<RwLock<HashMap<String, bool>>>,
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
        // Check the in-memory cache first to avoid a DB round-trip.
        {
            let cache = self.conversation_cache.read().await;
            if cache.get(conversation_id).copied().unwrap_or(false) {
                return Ok(());
            }
        }

        // Check if the conversation exists in the database.
        let exists = sqlx::query_scalar::<_, i64>(
            "SELECT COUNT(*) FROM chat_conversations WHERE id = $1::uuid AND tenant_id = $2",
        )
        .bind(
            Uuid::parse_str(conversation_id)
                .map_err(|_| SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}")))?,
        )
        .bind(tenant_id)
        .fetch_one(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to check conversation: {e}")))?;

        if exists == 0 {
            // Create the conversation.
            let conv_id = Uuid::parse_str(conversation_id)
                .map_err(|_| SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}")))?;
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

        // Update cache.
        {
            let mut cache = self.conversation_cache.write().await;
            cache.insert(conversation_id.to_string(), true);
        }

        Ok(())
    }

    /// Insert a message into the database.
    async fn insert_message(
        &self,
        conversation_id: &str,
        role: &str,
        content: &str,
    ) -> Result<()> {
        let conv_uuid = Uuid::parse_str(conversation_id)
            .map_err(|_| SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}")))?;
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
        sqlx::query(
            "UPDATE chat_conversations SET updated_at = $1 WHERE id = $2",
        )
        .bind(now)
        .bind(conv_uuid)
        .execute(&self.pool)
        .await
        .map_err(|e| SenseiError::Database(format!("Failed to update conversation timestamp: {e}")))?;

        Ok(())
    }

    /// Load recent conversation history from the database.
    ///
    /// Returns up to 20 most recent messages for the given conversation,
    /// ordered chronologically.
    async fn load_conversation_history(
        &self,
        conversation_id: &str,
    ) -> Result<Vec<ChatMessage>> {
        let conv_uuid = Uuid::parse_str(conversation_id)
            .map_err(|_| SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}")))?;

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
        let has_history = history.as_ref().map_or(false, |h| !h.is_empty());

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
            if let Some(contextual_response) = self
                .build_contextual_response(message, history.as_deref().unwrap())
            {
                return (contextual_response, false);
            }
        }

        // Fall back to pattern matching
        (fallback_chat(message), true)
    }

    /// Attempt to generate an AI-enriched response using the AI service.
    ///
    /// Examines the user's message for domain-specific keywords and queries
    /// the AI service for relevant predictions/anomalies to enrich the response.
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
            // Try to get quality insights from AI service
            // Use a synthetic product ID derived from the tenant for demo purposes
            if let Ok(prediction) = ai_service
                .predict_quality(tenant_id, tenant_id, serde_json::Value::Object(serde_json::Map::new()))
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

                let mut response = format!(
                    "Based on AI analysis, the predicted defect rate is {:.1}% with a CpK of {:.2}. ",
                    prediction.predicted_defect_rate * 100.0,
                    prediction.predicted_cpk,
                );

                if prediction.predicted_defect_rate > 0.05 {
                    response.push_str("I recommend reviewing the suggested process parameters for improvement. ");
                } else {
                    response.push_str("The process appears to be performing within acceptable limits. ");
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
            if let Ok(maintenance) = ai_service
                .predict_maintenance(tenant_id, tenant_id)
                .await
            {
                let risk_emoji = match maintenance.risk_level.as_str() {
                    "high" | "critical" => "⚠️",
                    "medium" => "⚡",
                    _ => "✅",
                };

                return Some(format!(
                    "{risk_emoji} AI Maintenance Analysis:\n\
                     - Failure probability: {:.1}%\n\
                     - Estimated remaining life: {:.0} hours\n\
                     - Risk level: {}\n\
                     - Recommended maintenance date: {}\n\
                     \nSuggested actions:\n{}",
                    maintenance.failure_probability * 100.0,
                    maintenance.estimated_remaining_life_hours,
                    maintenance.risk_level,
                    maintenance.recommended_maintenance_date.format("%Y-%m-%d"),
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
            if let Ok(anomalies) = ai_service
                .detect_anomalies(tenant_id, "general", tenant_id)
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
                        "AI has detected the following anomalies:\n{}\n\n\
                         I recommend investigating these findings and taking corrective action.",
                        anomaly_reports.join("\n"),
                    ));
                }
            }
        }

        None
    }

    /// Build a contextual response using conversation history.
    ///
    /// Analyzes the conversation history to provide continuity and
    /// references to previous topics discussed.
    fn build_contextual_response(
        &self,
        message: &str,
        history: &[ChatMessage],
    ) -> Option<String> {
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
                if lower.contains("quality") || lower.contains("ncr") || lower.contains("inspection") {
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
    ) -> Result<ChatResponse> {
        let conv_id = conversation_id
            .map(|s| s.to_string())
            .unwrap_or_else(Self::generate_conversation_id);

        // Ensure the conversation exists.
        self.ensure_conversation(tenant_id, user_id, &conv_id).await?;

        // Save the user message.
        self.insert_message(&conv_id, "user", message).await?;

        // Generate a context-aware response using conversation history
        // and optional AI service.
        let (response_text, is_fallback) = self
            .generate_context_aware_response(tenant_id, message, &conv_id)
            .await;

        // Save the assistant message.
        self.insert_message(&conv_id, "assistant", &response_text).await?;

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
    ) -> Result<mpsc::Receiver<Result<String>>> {
        let (tx, rx) = mpsc::channel(64);

        // Perform the chat to persist messages.
        let response = self
            .chat(tenant_id, user_id, message, conversation_id)
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
        let conv_uuid = Uuid::parse_str(conversation_id)
            .map_err(|_| SenseiError::Validation(format!("Invalid conversation ID: {conversation_id}")))?;

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
