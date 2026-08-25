//! Semantic Anomaly Detection — Sentiment Analysis, Sequence Validation, and Alerting.
//!
//! Ported from [`semantic_anomaly_detection.py`](backend/src/sensei/services/ai/semantic_anomaly_detection.py).
//!
//! # Components
//!
//! - [`SentimentAnalyzer`] — Keyword-based sentiment and urgency scoring with
//!   negation detection, frustration pattern recognition, and escalation tracking.
//! - [`SequenceAnalyzer`] — Learns expected process flows and detects ordering,
//!   missing-event, and timing anomalies.
//! - [`AlertManager`] — Manages alert lifecycle with cooldowns and rate limiting.
//! - [`AnomalyDetectionEngine`] — Orchestrates all analyzers.

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet, VecDeque};
use uuid::Uuid;

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

/// Alert sensitivity level controlling how easily anomalies trigger alerts.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AlertSensitivity {
    Low,
    Medium,
    High,
    Critical,
}

/// Type of anomaly detected.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Hash)]
pub enum AnomalyType {
    Sentiment,
    Urgency,
    Frustration,
    SequenceOrdering,
    MissingEvent,
    Timing,
    Escalation,
    PatternDeviation,
}

/// Type of process event.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum EventType {
    QuoteCreated,
    QuoteSent,
    QuoteAccepted,
    QuoteRejected,
    OrderPlaced,
    OrderConfirmed,
    OrderShipped,
    OrderDelivered,
    NcrCreated,
    NcrReviewed,
    NcrResolved,
    MaintenanceRequested,
    MaintenanceStarted,
    MaintenanceCompleted,
    Other(String),
}

/// Sentiment level classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum SentimentLevel {
    VeryNegative,
    Negative,
    Neutral,
    Positive,
    VeryPositive,
}

/// Urgency level classification.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum UrgencyLevel {
    Low,
    Medium,
    High,
    Critical,
}

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// A process event to be analyzed.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProcessEvent {
    pub id: Uuid,
    pub entity_id: String,
    pub event_type: EventType,
    pub description: String,
    pub timestamp: DateTime<Utc>,
    pub metadata: HashMap<String, String>,
}

/// Result of sentiment analysis.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SentimentResult {
    pub score: f64,
    pub level: SentimentLevel,
    pub urgency_score: f64,
    pub urgency_level: UrgencyLevel,
    pub frustration_patterns: Vec<String>,
    pub is_escalated: bool,
}

/// A learned sequence pattern.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SequencePattern {
    pub events: Vec<EventType>,
    pub expected_duration_mean: f64,
    pub expected_duration_std: f64,
    pub frequency: usize,
}

/// A timing anomaly.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimingAnomaly {
    pub event_a: String,
    pub event_b: String,
    pub actual_duration_minutes: f64,
    pub expected_duration_minutes: f64,
    pub deviation_std: f64,
}

/// A detected anomaly.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Anomaly {
    pub id: Uuid,
    pub anomaly_type: AnomalyType,
    pub severity: f64,
    pub entity_id: String,
    pub description: String,
    pub detected_at: DateTime<Utc>,
    pub event_id: Option<Uuid>,
    pub timing: Option<TimingAnomaly>,
}

impl Anomaly {
    /// Determine whether this anomaly should trigger an alert at the given sensitivity.
    pub fn should_alert(&self, sensitivity: AlertSensitivity) -> bool {
        let threshold = match sensitivity {
            AlertSensitivity::Low => 0.8,
            AlertSensitivity::Medium => 0.6,
            AlertSensitivity::High => 0.4,
            AlertSensitivity::Critical => 0.2,
        };
        self.severity >= threshold
    }
}

/// Configuration for alert management.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlertConfig {
    pub cooldown_minutes: i64,
    pub max_alerts_per_hour: usize,
    pub thresholds: HashMap<AnomalyType, f64>,
}

impl Default for AlertConfig {
    fn default() -> Self {
        let mut thresholds = HashMap::new();
        thresholds.insert(AnomalyType::Sentiment, 0.5);
        thresholds.insert(AnomalyType::Urgency, 0.6);
        thresholds.insert(AnomalyType::Frustration, 0.4);
        thresholds.insert(AnomalyType::SequenceOrdering, 0.7);
        thresholds.insert(AnomalyType::MissingEvent, 0.8);
        thresholds.insert(AnomalyType::Timing, 0.5);
        thresholds.insert(AnomalyType::Escalation, 0.3);
        thresholds.insert(AnomalyType::PatternDeviation, 0.6);

        Self {
            cooldown_minutes: 30,
            max_alerts_per_hour: 10,
            thresholds,
        }
    }
}

impl AlertConfig {
    /// Get the threshold for a specific anomaly type.
    pub fn get_threshold(&self, anomaly_type: AnomalyType) -> f64 {
        self.thresholds
            .get(&anomaly_type)
            .copied()
            .unwrap_or(0.5)
    }
}

/// An alert triggered by an anomaly.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Alert {
    pub id: Uuid,
    pub anomaly_id: Uuid,
    pub entity_id: String,
    pub anomaly_type: AnomalyType,
    pub severity: f64,
    pub description: String,
    pub created_at: DateTime<Utc>,
    pub acknowledged_at: Option<DateTime<Utc>>,
    pub suppressed_at: Option<DateTime<Utc>>,
    pub resolved_at: Option<DateTime<Utc>>,
}

// ---------------------------------------------------------------------------
// Sentiment Keyword Data
// ---------------------------------------------------------------------------

/// Positive sentiment keywords.
const POSITIVE_KEYWORDS: &[&str] = &[
    "good", "great", "excellent", "satisfied", "happy", "pleased",
    "impressed", "outstanding", "fantastic", "positive", "improved",
    "improving", "efficient", "smooth", "successful", "helpful",
    "responsive", "clear", "effective", "well done", "thank you",
    "appreciate", "perfect", "amazing", "wonderful",
];

/// Negative sentiment keywords.
const NEGATIVE_KEYWORDS: &[&str] = &[
    "bad", "terrible", "unhappy", "dissatisfied", "frustrated",
    "angry", "upset", "disappointed", "poor", "worst", "horrible",
    "awful", "negative", "declining", "worse", "failure", "failed",
    "broken", "useless", "unacceptable", "problem", "issue",
    "complaint", "slow", "unreliable", "rude", "unhelpful",
    "damaged", "incorrect", "wrong",
];

/// Negation words that flip sentiment.
const NEGATION_WORDS: &[&str] = &[
    "not", "no", "never", "neither", "nor", "nothing", "nowhere",
    "hardly", "barely", "doesn't", "don't", "didn't", "won't",
    "wouldn't", "couldn't", "shouldn't", "isn't", "aren't", "wasn't",
    "weren't", "haven't", "hasn't", "hadn't", "can't", "cannot",
];

/// Frustration patterns (compiled as strings for regex-like matching).
const FRUSTRATION_PATTERNS: &[&str] = &[
    "this is the third time",
    "already told you",
    "not the first time",
    "how many times",
    "still not resolved",
    "no one responded",
    "nobody cares",
    "waste of time",
    "unbelievable",
    "ridiculous",
    "totally unacceptable",
    "complete failure",
    "utterly disappointed",
    "fed up",
    "had enough",
    "at my wit's end",
];

/// Urgency indicators.
const URGENCY_INDICATORS: &[&str] = &[
    "urgent", "asap", "immediately", "emergency", "critical",
    "deadline", "overdue", "priority", "important", "time-sensitive",
    "rush", "expedite", "pressing", "now", "today",
];

/// Emergency escalation keywords.
const ESCALATION_KEYWORDS: &[&str] = &[
    "escalate", "manager", "supervisor", "complaint", "legal",
    "regulatory", "compliance", "violation", "safety",
    "shutdown", "stop production", "recall", "lawsuit",
];

// ---------------------------------------------------------------------------
// SentimentAnalyzer
// ---------------------------------------------------------------------------

/// Analyzes text for sentiment, urgency, and frustration indicators.
pub struct SentimentAnalyzer {
    /// Maximum history entries per entity.
    max_history: usize,
    /// Sentiment score history per entity.
    entity_history: HashMap<String, VecDeque<f64>>,
    /// Escalation state per entity.
    entity_escalated: HashMap<String, bool>,
}

impl SentimentAnalyzer {
    /// Create a new [`SentimentAnalyzer`].
    pub fn new(max_history: usize) -> Self {
        Self {
            max_history,
            entity_history: HashMap::new(),
            entity_escalated: HashMap::new(),
        }
    }

    /// Analyze text for sentiment and urgency, returning a [`SentimentResult`].
    pub fn analyze(&mut self, text: &str, entity_id: &str) -> SentimentResult {
        let sentiment_score = self.calculate_sentiment_score(text);
        let urgency_score = self.calculate_urgency_score(text);
        let frustration_patterns = self.detect_frustration_patterns(text);
        let is_escalated = self.check_escalation(entity_id, sentiment_score);

        // Track history
        self.entity_history
            .entry(entity_id.to_string())
            .or_insert_with(|| VecDeque::with_capacity(self.max_history))
            .push_back(sentiment_score);

        // Trim history if needed
        if let Some(history) = self.entity_history.get(entity_id) {
            if history.len() > self.max_history {
                self.entity_history
                    .get_mut(entity_id)
                    .unwrap()
                    .pop_front();
            }
        }

        SentimentResult {
            score: sentiment_score,
            level: self.score_to_sentiment_level(sentiment_score),
            urgency_score,
            urgency_level: self.score_to_urgency_level(urgency_score),
            frustration_patterns,
            is_escalated,
        }
    }

    /// Check if a keyword is negated in the text (simple proximity check).
    fn is_negated(&self, text: &str, keyword: &str) -> bool {
        let lower = text.to_lowercase();
        if let Some(pos) = lower.find(keyword) {
            // Look for negation words within 5 words before the keyword
            let before = &lower[..pos];
            let words: Vec<&str> = before.split_whitespace().collect();
            let start = words.len().saturating_sub(5);
            for i in start..words.len() {
                let word = words[i].trim_matches(|c: char| !c.is_alphanumeric());
                if NEGATION_WORDS.contains(&word) {
                    return true;
                }
            }
        }
        false
    }

    /// Calculate sentiment score for text. Range: -1.0 (very negative) to +1.0 (very positive).
    fn calculate_sentiment_score(&self, text: &str) -> f64 {
        let lower = text.to_lowercase();
        let mut score = 0.0f64;

        // Score positive keywords
        for &kw in POSITIVE_KEYWORDS {
            if lower.contains(kw) {
                if self.is_negated(&lower, kw) {
                    score -= 0.2;
                } else {
                    score += 0.2;
                }
            }
        }

        // Score negative keywords
        for &kw in NEGATIVE_KEYWORDS {
            if lower.contains(kw) {
                if self.is_negated(&lower, kw) {
                    score += 0.2;
                } else {
                    score -= 0.2;
                }
            }
        }

        // Normalize to [-1.0, 1.0]
        score.clamp(-1.0, 1.0)
    }

    /// Calculate urgency score. Range: 0.0 (normal) to 1.0 (critical).
    fn calculate_urgency_score(&self, text: &str) -> f64 {
        let mut score = 0.0f64;

        // Check urgency keywords
        let lower = text.to_lowercase();
        for &kw in URGENCY_INDICATORS {
            if lower.contains(kw) {
                score += 0.15;
            }
        }

        // Check escalation keywords
        for &kw in ESCALATION_KEYWORDS {
            if lower.contains(kw) {
                score += 0.2;
            }
        }

        // Check ALL-CAPS words (urgency indicator)
        let all_caps_count: usize = text
            .split_whitespace()
            .filter(|w| w.len() > 2 && w.chars().all(|c| c.is_uppercase() || !c.is_alphabetic()))
            .count();
        score += (all_caps_count as f64).min(3.0) * 0.1;

        // Check exclamation marks
        let exclaim_count = text.chars().filter(|&c| c == '!').count();
        score += (exclaim_count as f64).min(3.0) * 0.1;

        // Normalize
        score.clamp(0.0, 1.0)
    }

    /// Detect frustration patterns in text.
    fn detect_frustration_patterns(&self, text: &str) -> Vec<String> {
        let lower = text.to_lowercase();
        FRUSTRATION_PATTERNS
            .iter()
            .filter(|&&pattern| lower.contains(pattern))
            .map(|&s| s.to_string())
            .collect()
    }

    /// Convert a numeric score to a [`SentimentLevel`].
    fn score_to_sentiment_level(&self, score: f64) -> SentimentLevel {
        if score <= -0.6 {
            SentimentLevel::VeryNegative
        } else if score <= -0.2 {
            SentimentLevel::Negative
        } else if score < 0.2 {
            SentimentLevel::Neutral
        } else if score < 0.6 {
            SentimentLevel::Positive
        } else {
            SentimentLevel::VeryPositive
        }
    }

    /// Convert a numeric urgency score to an [`UrgencyLevel`].
    fn score_to_urgency_level(&self, score: f64) -> UrgencyLevel {
        if score >= 0.7 {
            UrgencyLevel::Critical
        } else if score >= 0.4 {
            UrgencyLevel::High
        } else if score >= 0.2 {
            UrgencyLevel::Medium
        } else {
            UrgencyLevel::Low
        }
    }

    /// Check if an entity should be escalated based on consistently negative sentiment.
    fn check_escalation(&mut self, entity_id: &str, current_score: f64) -> bool {
        let history = self
            .entity_history
            .entry(entity_id.to_string())
            .or_insert_with(|| VecDeque::with_capacity(self.max_history));

        // Escalate if current score is very negative or if we have 3+ consecutive negative scores
        if current_score <= -0.6 {
            self.entity_escalated.insert(entity_id.to_string(), true);
            return true;
        }

        let recent_negative: usize = history
            .iter()
            .rev()
            .take(3)
            .filter(|&&s| s <= -0.3)
            .count();

        if recent_negative >= 3 {
            self.entity_escalated.insert(entity_id.to_string(), true);
            return true;
        }

        self.entity_escalated
            .get(entity_id)
            .copied()
            .unwrap_or(false)
    }

    /// Get the sentiment trend for an entity (recent scores).
    pub fn get_entity_sentiment_trend(&self, entity_id: &str) -> Vec<f64> {
        self.entity_history
            .get(entity_id)
            .map(|h| h.iter().copied().collect())
            .unwrap_or_default()
    }

    /// Export internal state.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "entity_count".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.entity_history.len() as u64)),
        );
        state.insert(
            "escalated_count".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.entity_escalated.len() as u64)),
        );
        state
    }
}

impl Default for SentimentAnalyzer {
    fn default() -> Self {
        Self::new(1000)
    }
}

// ---------------------------------------------------------------------------
// SequenceAnalyzer
// ---------------------------------------------------------------------------

/// Analyses event sequences to learn expected patterns and detect anomalies.
pub struct SequenceAnalyzer {
    /// Learned patterns keyed by first event type (as string).
    patterns: HashMap<String, SequencePattern>,
    /// Maximum patterns to track.
    max_patterns: usize,
}

impl SequenceAnalyzer {
    /// Create a new [`SequenceAnalyzer`].
    pub fn new(max_patterns: usize) -> Self {
        Self {
            patterns: HashMap::new(),
            max_patterns,
        }
    }

    /// Learn a pattern from a sequence of events.
    ///
    /// Computes expected duration statistics and stores the pattern.
    pub fn learn_pattern(&mut self, events: &[ProcessEvent]) {
        if events.len() < 2 {
            return;
        }

        let event_types: Vec<EventType> = events.iter().map(|e| e.event_type.clone()).collect();
        let key = self.event_type_key(&event_types[0]);

        // Calculate durations between subsequent events
        let mut durations = Vec::new();
        for i in 1..events.len() {
            let dur = (events[i].timestamp - events[i - 1].timestamp)
                .num_seconds() as f64 / 60.0; // minutes
            durations.push(dur);
        }

        let n = durations.len() as f64;
        let mean = if n > 0.0 {
            durations.iter().sum::<f64>() / n
        } else {
            0.0
        };
        let variance = if n > 1.0 {
            durations.iter().map(|d| (d - mean).powi(2)).sum::<f64>() / (n - 1.0)
        } else {
            0.0
        };
        let std_dev = variance.sqrt();

        let frequency = self.patterns.get(&key).map_or(0, |p| p.frequency) + 1;

        // Evict LRU pattern if needed
        if self.patterns.len() >= self.max_patterns {
            if let Some(oldest_key) = self.patterns.keys().next().cloned() {
                self.patterns.remove(&oldest_key);
            }
        }

        self.patterns.insert(
            key,
            SequencePattern {
                events: event_types,
                expected_duration_mean: mean,
                expected_duration_std: std_dev,
                frequency,
            },
        );
    }

    /// Detect sequence anomalies in a list of events.
    pub fn detect_sequence_anomalies(&self, events: &[ProcessEvent]) -> Vec<Anomaly> {
        let mut anomalies = Vec::new();

        anomalies.extend(self.check_ordering(events));
        anomalies.extend(self.check_missing_events(events));
        anomalies.extend(self.check_timing(events));

        anomalies
    }

    /// Check for ordering anomalies in the event sequence.
    fn check_ordering(&self, events: &[ProcessEvent]) -> Vec<Anomaly> {
        let mut anomalies = Vec::new();
        if events.is_empty() {
            return anomalies;
        }

        // Check if we have a pattern for the first event type
        let first_key = self.event_type_key(&events[0].event_type);
        let pattern = match self.patterns.get(&first_key) {
            Some(p) => p,
            None => return anomalies,
        };

        let expected_types: Vec<String> = pattern
            .events
            .iter()
            .map(|e| self.event_type_key(e))
            .collect();

        let actual_types: Vec<String> = events
            .iter()
            .map(|e| self.event_type_key(&e.event_type))
            .collect();

        // Simple ordering check: look for deviations from expected order
        let mut expected_idx = 0;
        for (i, actual) in actual_types.iter().enumerate() {
            if expected_idx < expected_types.len() && actual == &expected_types[expected_idx] {
                expected_idx += 1;
            } else if expected_idx > 0
                && expected_idx < expected_types.len()
                && actual == &expected_types[expected_idx - 1]
            {
                // Duplicate - might be normal, skip
                continue;
            } else {
                // Unexpected event in sequence
                anomalies.push(Anomaly {
                    id: Uuid::new_v4(),
                    anomaly_type: AnomalyType::SequenceOrdering,
                    severity: 0.6,
                    entity_id: events[0].entity_id.clone(),
                    description: format!(
                        "Unexpected event '{}' at position {} (expected '{}')",
                        actual,
                        i,
                        if expected_idx < expected_types.len() {
                            &expected_types[expected_idx]
                        } else {
                            "end of sequence"
                        }
                    ),
                    detected_at: Utc::now(),
                    event_id: Some(events[i].id),
                    timing: None,
                });
            }
        }

        anomalies
    }

    /// Check for missing events in the sequence.
    fn check_missing_events(&self, events: &[ProcessEvent]) -> Vec<Anomaly> {
        let mut anomalies = Vec::new();
        if events.is_empty() {
            return anomalies;
        }

        let first_key = self.event_type_key(&events[0].event_type);
        let pattern = match self.patterns.get(&first_key) {
            Some(p) => p,
            None => return anomalies,
        };

        let expected_types: Vec<String> = pattern
            .events
            .iter()
            .map(|e| self.event_type_key(e))
            .collect();

        let actual_types: HashSet<String> = events
            .iter()
            .map(|e| self.event_type_key(&e.event_type))
            .collect();

        // Find expected events that are missing from actual sequence
        for expected in &expected_types {
            if !actual_types.contains(expected) {
                anomalies.push(Anomaly {
                    id: Uuid::new_v4(),
                    anomaly_type: AnomalyType::MissingEvent,
                    severity: 0.7,
                    entity_id: events[0].entity_id.clone(),
                    description: format!("Missing expected event '{}' in sequence", expected),
                    detected_at: Utc::now(),
                    event_id: None,
                    timing: None,
                });
            }
        }

        anomalies
    }

    /// Check for timing anomalies (events taking too long or too short).
    fn check_timing(&self, events: &[ProcessEvent]) -> Vec<Anomaly> {
        let mut anomalies = Vec::new();
        if events.len() < 2 {
            return anomalies;
        }

        let first_key = self.event_type_key(&events[0].event_type);
        let pattern = match self.patterns.get(&first_key) {
            Some(p) => p,
            None => return anomalies,
        };

        for i in 1..events.len() {
            let duration_minutes = (events[i].timestamp - events[i - 1].timestamp)
                .num_seconds() as f64 / 60.0;

            // Check if this duration is anomalous (> 3 std devs from mean)
            if pattern.expected_duration_std > 0.0 {
                let deviation = (duration_minutes - pattern.expected_duration_mean).abs()
                    / pattern.expected_duration_std;

                if deviation > 3.0 {
                    let event_a = self.event_type_key(&events[i - 1].event_type);
                    let event_b = self.event_type_key(&events[i].event_type);

                    anomalies.push(Anomaly {
                        id: Uuid::new_v4(),
                        anomaly_type: AnomalyType::Timing,
                        severity: (deviation / 5.0).min(1.0),
                        entity_id: events[0].entity_id.clone(),
                        description: format!(
                            "Timing anomaly: '{}' → '{}' took {:.1} min (expected {:.1} min, {:.1}σ deviation)",
                            event_a, event_b, duration_minutes,
                            pattern.expected_duration_mean, deviation
                        ),
                        detected_at: Utc::now(),
                        event_id: Some(events[i].id),
                        timing: Some(TimingAnomaly {
                            event_a,
                            event_b,
                            actual_duration_minutes: duration_minutes,
                            expected_duration_minutes: pattern.expected_duration_mean,
                            deviation_std: deviation,
                        }),
                    });
                }
            }
        }

        anomalies
    }

    /// Calculate standard deviation for a set of values.
    #[allow(dead_code)]
    fn std_dev(&self, values: &[f64]) -> f64 {
        let n = values.len() as f64;
        if n <= 1.0 {
            return 0.0;
        }
        let mean = values.iter().sum::<f64>() / n;
        let variance = values.iter().map(|v| (v - mean).powi(2)).sum::<f64>() / (n - 1.0);
        variance.sqrt()
    }

    /// Convert an EventType to a simple string key for pattern matching.
    fn event_type_key(&self, event_type: &EventType) -> String {
        match event_type {
            EventType::QuoteCreated => "quote_created".to_string(),
            EventType::QuoteSent => "quote_sent".to_string(),
            EventType::QuoteAccepted => "quote_accepted".to_string(),
            EventType::QuoteRejected => "quote_rejected".to_string(),
            EventType::OrderPlaced => "order_placed".to_string(),
            EventType::OrderConfirmed => "order_confirmed".to_string(),
            EventType::OrderShipped => "order_shipped".to_string(),
            EventType::OrderDelivered => "order_delivered".to_string(),
            EventType::NcrCreated => "ncr_created".to_string(),
            EventType::NcrReviewed => "ncr_reviewed".to_string(),
            EventType::NcrResolved => "ncr_resolved".to_string(),
            EventType::MaintenanceRequested => "maintenance_requested".to_string(),
            EventType::MaintenanceStarted => "maintenance_started".to_string(),
            EventType::MaintenanceCompleted => "maintenance_completed".to_string(),
            EventType::Other(s) => s.clone(),
        }
    }

    /// Export internal state.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "pattern_count".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.patterns.len() as u64)),
        );
        state
    }
}

impl Default for SequenceAnalyzer {
    fn default() -> Self {
        Self::new(100)
    }
}

// ---------------------------------------------------------------------------
// AlertManager
// ---------------------------------------------------------------------------

/// Manages alert lifecycle including cooldowns, rate limiting, and state tracking.
pub struct AlertManager {
    config: AlertConfig,
    /// Active (not acknowledged/suppressed/resolved) alerts.
    active_alerts: Vec<Alert>,
    /// Timestamps of alerts created in the last hour (for rate limiting).
    recent_alert_timestamps: VecDeque<DateTime<Utc>>,
    /// Cooldown tracking: entity_id → last alert time.
    cooldowns: HashMap<String, DateTime<Utc>>,
}

impl AlertManager {
    /// Create a new [`AlertManager`] with the given configuration.
    pub fn new(config: AlertConfig) -> Self {
        Self {
            config,
            active_alerts: Vec::new(),
            recent_alert_timestamps: VecDeque::new(),
            cooldowns: HashMap::new(),
        }
    }

    /// Check whether an anomaly should trigger an alert, considering sensitivity,
    /// cooldowns, and rate limits.
    pub fn should_alert(&mut self, anomaly: &Anomaly) -> bool {
        // 1. Check severity threshold for this anomaly type
        let threshold = self.config.get_threshold(anomaly.anomaly_type);
        if anomaly.severity < threshold {
            return false;
        }

        // 2. Check cooldown for this entity
        if let Some(last_alert) = self.cooldowns.get(&anomaly.entity_id) {
            let elapsed = Utc::now() - *last_alert;
            if elapsed.num_minutes() < self.config.cooldown_minutes {
                return false;
            }
        }

        // 3. Check global rate limit
        if !self.check_rate_limit() {
            return false;
        }

        true
    }

    /// Create an alert from an anomaly (if it passes all checks).
    pub fn create_alert(&mut self, anomaly: &Anomaly) -> Option<Alert> {
        if !self.should_alert(anomaly) {
            return None;
        }

        let now = Utc::now();
        let alert = Alert {
            id: Uuid::new_v4(),
            anomaly_id: anomaly.id,
            entity_id: anomaly.entity_id.clone(),
            anomaly_type: anomaly.anomaly_type,
            severity: anomaly.severity,
            description: anomaly.description.clone(),
            created_at: now,
            acknowledged_at: None,
            suppressed_at: None,
            resolved_at: None,
        };

        // Track cooldown
        self.cooldowns
            .insert(anomaly.entity_id.clone(), now);

        // Track rate limit
        self.recent_alert_timestamps.push_back(now);
        while self.recent_alert_timestamps.len() > self.config.max_alerts_per_hour {
            self.recent_alert_timestamps.pop_front();
        }

        self.active_alerts.push(alert.clone());
        Some(alert)
    }

    /// Acknowledge an alert.
    pub fn acknowledge_alert(&mut self, alert_id: Uuid) -> Option<Alert> {
        // Step 1: Find and acknowledge (drops mutable borrow of active_alerts)
        let mut found_alert = None;
        if let Some(alert) = self
            .active_alerts
            .iter_mut()
            .find(|a| a.id == alert_id)
        {
            alert.acknowledged_at = Some(Utc::now());
            found_alert = Some(alert.clone());
        }

        // Step 2: If found, clean up resolved alerts and keep acknowledged one
        if let Some(ref alert) = found_alert {
            self.active_alerts.retain(|a| a.resolved_at.is_none());
            self.active_alerts.push(alert.clone());
        }

        found_alert
    }

    /// Suppress an alert.
    pub fn suppress_alert(&mut self, alert_id: Uuid) -> Option<&Alert> {
        if let Some(alert) = self
            .active_alerts
            .iter_mut()
            .find(|a| a.id == alert_id)
        {
            alert.suppressed_at = Some(Utc::now());
            Some(alert)
        } else {
            None
        }
    }

    /// Get all active (non-suppressed, non-resolved) alerts.
    pub fn get_active_alerts(&self) -> Vec<Alert> {
        self.active_alerts
            .iter()
            .filter(|a| a.suppressed_at.is_none() && a.resolved_at.is_none())
            .cloned()
            .collect()
    }

    /// Check rate limit: max N alerts per hour.
    fn check_rate_limit(&mut self) -> bool {
        let now = Utc::now();
        let one_hour_ago = now - Duration::hours(1);

        // Remove timestamps older than 1 hour
        while let Some(&ts) = self.recent_alert_timestamps.front() {
            if ts < one_hour_ago {
                self.recent_alert_timestamps.pop_front();
            } else {
                break;
            }
        }

        self.recent_alert_timestamps.len() < self.config.max_alerts_per_hour
    }

    /// Export internal state.
    pub fn export_state(&self) -> HashMap<String, serde_json::Value> {
        let mut state = HashMap::new();
        state.insert(
            "active_alerts".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.active_alerts.len() as u64)),
        );
        state.insert(
            "cooldowns_active".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.cooldowns.len() as u64)),
        );
        state
    }
}

impl Default for AlertManager {
    fn default() -> Self {
        Self::new(AlertConfig::default())
    }
}

// ---------------------------------------------------------------------------
// AnomalyDetectionEngine
// ---------------------------------------------------------------------------

/// Unified anomaly detection engine that orchestrates sentiment analysis,
/// sequence analysis, and alert management.
pub struct AnomalyDetectionEngine {
    pub sentiment_analyzer: SentimentAnalyzer,
    pub sequence_analyzer: SequenceAnalyzer,
    pub alert_manager: AlertManager,
    /// All anomalies detected by this engine.
    anomalies: Vec<Anomaly>,
    /// Maximum anomalies to retain.
    max_anomalies: usize,
    /// Current alert sensitivity.
    sensitivity: AlertSensitivity,
    /// Recent events seen by the engine, used for pattern learning and
    /// multi-event sequence checks.
    event_history: VecDeque<ProcessEvent>,
    /// Maximum events retained in the history window.
    max_history: usize,
}

impl AnomalyDetectionEngine {
    /// Create a new [`AnomalyDetectionEngine`].
    pub fn new() -> Self {
        Self {
            sentiment_analyzer: SentimentAnalyzer::default(),
            sequence_analyzer: SequenceAnalyzer::default(),
            alert_manager: AlertManager::default(),
            anomalies: Vec::new(),
            max_anomalies: 1000,
            sensitivity: AlertSensitivity::Medium,
            event_history: VecDeque::new(),
            max_history: 500,
        }
    }

    /// Process a single event through all analysis stages.
    ///
    /// The event is appended to the engine's history window; once at least two
    /// events exist for an entity, sequence patterns are learned and
    /// multi-event sequence checks run against that entity's recent history.
    ///
    /// Returns a list of alerts triggered by this event.
    pub fn process_event(&mut self, event: ProcessEvent) -> Vec<Alert> {
        let mut alerts = Vec::new();

        // 1. Sentiment analysis
        let sentiment_anomalies = self.analyze_sentiment_anomaly(&event);
        for anomaly in &sentiment_anomalies {
            if anomaly.should_alert(self.sensitivity) {
                if let Some(alert) = self.alert_manager.create_alert(anomaly) {
                    alerts.push(alert);
                }
            }
        }
        self.anomalies.extend(sentiment_anomalies);

        // 2. Append to the history window (bounded).
        self.event_history.push_back(event.clone());
        while self.event_history.len() > self.max_history {
            self.event_history.pop_front();
        }

        // 3. Sequence analysis — only meaningful once an entity has ≥2 events.
        let entity_events: Vec<ProcessEvent> = self
            .event_history
            .iter()
            .filter(|e| e.entity_id == event.entity_id)
            .cloned()
            .collect();
        if entity_events.len() >= 2 {
            // Learn the observed sequence before scoring it.
            self.sequence_analyzer.learn_pattern(&entity_events);
            let sequence_anomalies = self.sequence_analyzer.detect_sequence_anomalies(&entity_events);
            for anomaly in &sequence_anomalies {
                if anomaly.should_alert(self.sensitivity) {
                    if let Some(alert) = self.alert_manager.create_alert(anomaly) {
                        alerts.push(alert);
                    }
                }
            }
            self.anomalies.extend(sequence_anomalies);
        }

        // Trim anomalies
        if self.anomalies.len() > self.max_anomalies {
            let excess = self.anomalies.len() - self.max_anomalies;
            self.anomalies.drain(..excess);
        }

        alerts
    }

    /// Process multiple events.
    ///
    /// Appends the whole batch to the history window, learns patterns from the
    /// batch, then runs multi-event sequence checks for every entity that has
    /// at least two events (combining the batch with prior history).
    pub fn process_events(&mut self, events: &[ProcessEvent]) -> Vec<Alert> {
        let mut all_alerts = Vec::new();

        if events.is_empty() {
            return all_alerts;
        }

        // Learn from the batch itself (≥2 events) so multi-event checks have a
        // baseline even on the very first call.
        if events.len() >= 2 {
            self.sequence_analyzer.learn_pattern(events);
        }

        for event in events {
            // Per-event sentiment analysis + alert creation.
            let sentiment_anomalies = self.analyze_sentiment_anomaly(event);
            for anomaly in &sentiment_anomalies {
                if anomaly.should_alert(self.sensitivity) {
                    if let Some(alert) = self.alert_manager.create_alert(anomaly) {
                        all_alerts.push(alert);
                    }
                }
            }
            self.anomalies.extend(sentiment_anomalies);

            // Append to the history window (bounded).
            self.event_history.push_back(event.clone());
            while self.event_history.len() > self.max_history {
                self.event_history.pop_front();
            }
        }

        // Multi-event sequence checks per entity (history + batch).
        let mut entity_ids: Vec<String> = events
            .iter()
            .map(|e| e.entity_id.clone())
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();
        entity_ids.sort();
        for entity_id in entity_ids {
            let entity_events: Vec<ProcessEvent> = self
                .event_history
                .iter()
                .filter(|e| e.entity_id == entity_id)
                .cloned()
                .collect();
            if entity_events.len() < 2 {
                continue;
            }
            let sequence_anomalies =
                self.sequence_analyzer.detect_sequence_anomalies(&entity_events);
            for anomaly in &sequence_anomalies {
                if anomaly.should_alert(self.sensitivity) {
                    if let Some(alert) = self.alert_manager.create_alert(anomaly) {
                        all_alerts.push(alert);
                    }
                }
            }
            self.anomalies.extend(sequence_anomalies);
        }

        // Trim anomalies
        if self.anomalies.len() > self.max_anomalies {
            let excess = self.anomalies.len() - self.max_anomalies;
            self.anomalies.drain(..excess);
        }

        all_alerts
    }

    /// Analyze an entity by its ID (returns anomalies found in stored data).
    pub fn analyze_entity(&self, _entity_id: &str) -> Vec<Anomaly> {
        // In a full implementation, this would query stored anomalies for that entity.
        // For now, return all anomalies (the caller can filter).
        self.anomalies.clone()
    }

    /// Analyze sentiment for a single event.
    fn analyze_sentiment_anomaly(&mut self, event: &ProcessEvent) -> Vec<Anomaly> {
        let mut anomalies = Vec::new();

        let result = self
            .sentiment_analyzer
            .analyze(&event.description, &event.entity_id);

        // Check for negative sentiment
        if result.score <= -0.3 {
            anomalies.push(Anomaly {
                id: Uuid::new_v4(),
                anomaly_type: AnomalyType::Sentiment,
                severity: (-result.score).clamp(0.0, 1.0),
                entity_id: event.entity_id.clone(),
                description: format!(
                    "Negative sentiment detected (score: {:.2}, level: {:?})",
                    result.score, result.level
                ),
                detected_at: Utc::now(),
                event_id: Some(event.id),
                timing: None,
            });
        }

        // Check for high urgency
        if result.urgency_score >= 0.5 {
            anomalies.push(Anomaly {
                id: Uuid::new_v4(),
                anomaly_type: AnomalyType::Urgency,
                severity: result.urgency_score,
                entity_id: event.entity_id.clone(),
                description: format!(
                    "High urgency detected (score: {:.2}, level: {:?})",
                    result.urgency_score, result.urgency_level
                ),
                detected_at: Utc::now(),
                event_id: Some(event.id),
                timing: None,
            });
        }

        // Check for frustration patterns
        if !result.frustration_patterns.is_empty() {
            anomalies.push(Anomaly {
                id: Uuid::new_v4(),
                anomaly_type: AnomalyType::Frustration,
                severity: 0.7f64.min(
                    result.frustration_patterns.len() as f64 * 0.25,
                ),
                entity_id: event.entity_id.clone(),
                description: format!(
                    "Frustration detected: {}",
                    result.frustration_patterns.join("; ")
                ),
                detected_at: Utc::now(),
                event_id: Some(event.id),
                timing: None,
            });
        }

        // Check for escalation
        if result.is_escalated {
            anomalies.push(Anomaly {
                id: Uuid::new_v4(),
                anomaly_type: AnomalyType::Escalation,
                severity: 0.8,
                entity_id: event.entity_id.clone(),
                description: "Entity meets escalation criteria due to persistent negative sentiment"
                    .to_string(),
                detected_at: Utc::now(),
                event_id: Some(event.id),
                timing: None,
            });
        }

        anomalies
    }

    /// Get a summary of the current anomaly state.
    pub fn get_anomaly_summary(&self) -> HashMap<String, serde_json::Value> {
        let mut summary = HashMap::new();
        summary.insert(
            "total_anomalies".to_string(),
            serde_json::Value::Number(serde_json::Number::from(self.anomalies.len() as u64)),
        );
        summary.insert(
            "active_alerts".to_string(),
            serde_json::Value::Number(serde_json::Number::from(
                self.alert_manager.get_active_alerts().len() as u64,
            )),
        );
        summary
    }

    /// Set the alert sensitivity level.
    pub fn set_sensitivity(&mut self, sensitivity: AlertSensitivity) {
        self.sensitivity = sensitivity;
    }
}

impl Default for AnomalyDetectionEngine {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    // -- SentimentAnalyzer Tests ---------------------------------------------

    #[test]
    fn test_positive_sentiment() {
        let mut analyzer = SentimentAnalyzer::new(100);
        let result = analyzer.analyze("The service was excellent and very helpful", "entity-1");
        assert!(result.score > 0.0);
        assert_eq!(result.level, SentimentLevel::Positive);
    }

    #[test]
    fn test_negative_sentiment() {
        let mut analyzer = SentimentAnalyzer::new(100);
        let result = analyzer.analyze("This is a terrible and unacceptable problem", "entity-1");
        assert!(result.score < 0.0);
        assert_eq!(result.level, SentimentLevel::Negative);
    }

    #[test]
    fn test_negation_flips_sentiment() {
        let mut analyzer = SentimentAnalyzer::new(100);
        // "not good" should be negative
        let result = analyzer.analyze("This is not good at all", "entity-1");
        assert!(result.score < 0.0);
    }

    #[test]
    fn test_urgency_detection() {
        let mut analyzer = SentimentAnalyzer::new(100);
        let result = analyzer.analyze("URGENT: This is a CRITICAL issue requiring immediate attention!", "entity-1");
        assert!(result.urgency_score > 0.5);
        assert_eq!(result.urgency_level, UrgencyLevel::High);
    }

    #[test]
    fn test_frustration_patterns() {
        let mut analyzer = SentimentAnalyzer::new(100);
        let result = analyzer.analyze(
            "This is the third time I've reported this. Still not resolved. Unbelievable!",
            "entity-1",
        );
        assert!(!result.frustration_patterns.is_empty());
    }

    #[test]
    fn test_escalation_on_consecutive_negative() {
        let mut analyzer = SentimentAnalyzer::new(10);
        let text = "This is a terrible problem";

        // First negative
        let r1 = analyzer.analyze(text, "entity-escalate");
        // Second negative
        let r2 = analyzer.analyze(text, "entity-escalate");
        // Third negative — should trigger escalation
        let r3 = analyzer.analyze(text, "entity-escalate");

        // Check escalation after 3 consecutive negatives
        let r4 = analyzer.analyze(text, "entity-escalate");
        assert!(r4.is_escalated);
    }

    // -- SequenceAnalyzer Tests ----------------------------------------------

    #[test]
    fn test_learn_pattern() {
        let mut analyzer = SequenceAnalyzer::new(10);
        let now = Utc::now();

        let events = vec![
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-1".to_string(),
                event_type: EventType::QuoteCreated,
                description: "Quote created".to_string(),
                timestamp: now,
                metadata: HashMap::new(),
            },
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-1".to_string(),
                event_type: EventType::QuoteSent,
                description: "Quote sent".to_string(),
                timestamp: now + Duration::minutes(30),
                metadata: HashMap::new(),
            },
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-1".to_string(),
                event_type: EventType::QuoteAccepted,
                description: "Quote accepted".to_string(),
                timestamp: now + Duration::minutes(120),
                metadata: HashMap::new(),
            },
        ];

        analyzer.learn_pattern(&events);
        let state = analyzer.export_state();
        assert_eq!(
            state.get("pattern_count").unwrap().as_u64().unwrap(),
            1
        );
    }

    #[test]
    fn test_timing_anomaly() {
        let mut analyzer = SequenceAnalyzer::new(10);
        let now = Utc::now();

        // Learn a pattern where quote → sent takes ~30 min
        let normal_events = vec![
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-norm".to_string(),
                event_type: EventType::QuoteCreated,
                description: "".to_string(),
                timestamp: now,
                metadata: HashMap::new(),
            },
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-norm".to_string(),
                event_type: EventType::QuoteSent,
                description: "".to_string(),
                timestamp: now + Duration::minutes(30),
                metadata: HashMap::new(),
            },
        ];
        analyzer.learn_pattern(&normal_events);

        // Test with an anomalous timing (10 hours between events)
        let test_events = vec![
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-test".to_string(),
                event_type: EventType::QuoteCreated,
                description: "".to_string(),
                timestamp: now,
                metadata: HashMap::new(),
            },
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-test".to_string(),
                event_type: EventType::QuoteSent,
                description: "".to_string(),
                timestamp: now + Duration::hours(10),
                metadata: HashMap::new(),
            },
        ];

        let anomalies = analyzer.detect_sequence_anomalies(&test_events);
        let timing_anomalies: Vec<&Anomaly> = anomalies
            .iter()
            .filter(|a| a.anomaly_type == AnomalyType::Timing)
            .collect();
        assert!(!timing_anomalies.is_empty());
    }

    #[test]
    fn test_missing_event_detection() {
        let mut analyzer = SequenceAnalyzer::new(10);
        let now = Utc::now();

        // Learn a pattern with 3 events
        let full_events = vec![
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "order-1".to_string(),
                event_type: EventType::OrderPlaced,
                description: "".to_string(),
                timestamp: now,
                metadata: HashMap::new(),
            },
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "order-1".to_string(),
                event_type: EventType::OrderConfirmed,
                description: "".to_string(),
                timestamp: now + Duration::minutes(10),
                metadata: HashMap::new(),
            },
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "order-1".to_string(),
                event_type: EventType::OrderShipped,
                description: "".to_string(),
                timestamp: now + Duration::minutes(60),
                metadata: HashMap::new(),
            },
        ];
        analyzer.learn_pattern(&full_events);

        // Test with missing "OrderConfirmed"
        let incomplete = vec![
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "order-2".to_string(),
                event_type: EventType::OrderPlaced,
                description: "".to_string(),
                timestamp: now,
                metadata: HashMap::new(),
            },
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "order-2".to_string(),
                event_type: EventType::OrderShipped,
                description: "".to_string(),
                timestamp: now + Duration::minutes(60),
                metadata: HashMap::new(),
            },
        ];

        let anomalies = analyzer.detect_sequence_anomalies(&incomplete);
        let missing: Vec<&Anomaly> = anomalies
            .iter()
            .filter(|a| a.anomaly_type == AnomalyType::MissingEvent)
            .collect();
        assert!(!missing.is_empty());
    }

    // -- AlertManager Tests --------------------------------------------------

    #[test]
    fn test_alert_creation() {
        let mut manager = AlertManager::default();
        let anomaly = Anomaly {
            id: Uuid::new_v4(),
            anomaly_type: AnomalyType::Sentiment,
            severity: 0.8,
            entity_id: "entity-1".to_string(),
            description: "Test anomaly".to_string(),
            detected_at: Utc::now(),
            event_id: None,
            timing: None,
        };

        let alert = manager.create_alert(&anomaly);
        assert!(alert.is_some());
        assert_eq!(manager.get_active_alerts().len(), 1);
    }

    #[test]
    fn test_cooldown() {
        let config = AlertConfig {
            cooldown_minutes: 30,
            ..AlertConfig::default()
        };
        let mut manager = AlertManager::new(config);

        let anomaly = Anomaly {
            id: Uuid::new_v4(),
            anomaly_type: AnomalyType::Sentiment,
            severity: 0.8,
            entity_id: "entity-1".to_string(),
            description: "Test".to_string(),
            detected_at: Utc::now(),
            event_id: None,
            timing: None,
        };

        // First alert should succeed
        assert!(manager.create_alert(&anomaly).is_some());

        // Second alert (same entity, within cooldown) should fail
        assert!(manager.create_alert(&anomaly).is_none());
    }

    #[test]
    fn test_rate_limiting() {
        let config = AlertConfig {
            max_alerts_per_hour: 3,
            ..AlertConfig::default()
        };
        let mut manager = AlertManager::new(config);

        let anomaly = Anomaly {
            id: Uuid::new_v4(),
            anomaly_type: AnomalyType::Sentiment,
            severity: 0.8,
            entity_id: "entity-1".to_string(),
            description: "Test".to_string(),
            detected_at: Utc::now(),
            event_id: None,
            timing: None,
        };

        // Create 3 alerts (should all succeed with different entity IDs)
        for i in 0..3 {
            let mut a = anomaly.clone();
            a.entity_id = format!("entity-{}", i);
            assert!(
                manager.create_alert(&a).is_some(),
                "Alert {} should succeed",
                i
            );
        }

        // 4th should fail rate limit
        let mut a4 = anomaly.clone();
        a4.entity_id = "entity-4".to_string();
        assert!(manager.create_alert(&a4).is_none());
    }

    // -- AnomalyDetectionEngine Integration Tests ----------------------------

    #[test]
    fn test_process_event_with_sentiment() {
        let mut engine = AnomalyDetectionEngine::new();

        let event = ProcessEvent {
            id: Uuid::new_v4(),
            entity_id: "customer-1".to_string(),
            event_type: EventType::Other("support_ticket".to_string()),
            description: "This is a TERRIBLE experience! URGENT - we need help NOW!"
                .to_string(),
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        };

        let alerts = engine.process_event(event);
        // Should trigger sentiment and urgency anomalies
        assert!(!alerts.is_empty(), "Should generate alerts for negative+urgent text");
    }

    #[test]
    fn test_process_events_empty() {
        let mut engine = AnomalyDetectionEngine::new();
        let alerts = engine.process_events(&[]);
        assert!(alerts.is_empty());
    }

    #[test]
    fn test_engine_learns_patterns_and_detects_sequence_anomalies() {
        let mut engine = AnomalyDetectionEngine::new();
        let now = Utc::now();

        // Feed a healthy quote lifecycle twice so the pattern is learned.
        for entity in ["quote-ok-1", "quote-ok-2"] {
            let events = vec![
                ProcessEvent {
                    id: Uuid::new_v4(),
                    entity_id: entity.to_string(),
                    event_type: EventType::QuoteCreated,
                    description: "created".to_string(),
                    timestamp: now,
                    metadata: HashMap::new(),
                },
                ProcessEvent {
                    id: Uuid::new_v4(),
                    entity_id: entity.to_string(),
                    event_type: EventType::QuoteSent,
                    description: "sent".to_string(),
                    timestamp: now + Duration::minutes(30),
                    metadata: HashMap::new(),
                },
                ProcessEvent {
                    id: Uuid::new_v4(),
                    entity_id: entity.to_string(),
                    event_type: EventType::QuoteAccepted,
                    description: "accepted".to_string(),
                    timestamp: now + Duration::minutes(120),
                    metadata: HashMap::new(),
                },
            ];
            engine.process_events(&events);
        }

        // The engine must have learned patterns from the batch.
        let pattern_count = engine
            .sequence_analyzer
            .export_state()
            .get("pattern_count")
            .unwrap()
            .as_u64()
            .unwrap();
        assert!(pattern_count >= 1, "expected learned patterns, got {pattern_count}");

        // A wildly different sequence for the same event family must produce
        // a sequence-level anomaly once the entity has ≥2 events.
        let before = engine.anomalies.len();
        let bad_events = vec![
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-bad-1".to_string(),
                event_type: EventType::QuoteCreated,
                description: "created".to_string(),
                timestamp: now,
                metadata: HashMap::new(),
            },
            ProcessEvent {
                id: Uuid::new_v4(),
                entity_id: "quote-bad-1".to_string(),
                event_type: EventType::QuoteRejected,
                description: "rejected out of order".to_string(),
                timestamp: now + Duration::minutes(5),
                metadata: HashMap::new(),
            },
        ];
        engine.process_events(&bad_events);
        assert!(
            engine.anomalies.len() > before,
            "sequence anomalies should be recorded after a deviating multi-event sequence"
        );
    }

    #[test]
    fn test_sensitivity_filtering() {
        let mut engine = AnomalyDetectionEngine::new();
        engine.set_sensitivity(AlertSensitivity::Critical);

        let event = ProcessEvent {
            id: Uuid::new_v4(),
            entity_id: "customer-1".to_string(),
            event_type: EventType::Other("support_ticket".to_string()),
            description: "Minor issue".to_string(),
            timestamp: Utc::now(),
            metadata: HashMap::new(),
        };

        let alerts = engine.process_event(event);
        // With Critical sensitivity, only severity >= 0.2 should alert
        // Minor sentiment might not trigger
        assert!(alerts.is_empty());
    }

    #[test]
    fn test_anomaly_should_alert() {
        let high_severity = Anomaly {
            id: Uuid::new_v4(),
            anomaly_type: AnomalyType::Sentiment,
            severity: 0.9,
            entity_id: "e1".to_string(),
            description: "High severity".to_string(),
            detected_at: Utc::now(),
            event_id: None,
            timing: None,
        };
        assert!(high_severity.should_alert(AlertSensitivity::High));

        let low_severity = Anomaly {
            id: Uuid::new_v4(),
            anomaly_type: AnomalyType::Sentiment,
            severity: 0.1,
            entity_id: "e2".to_string(),
            description: "Low severity".to_string(),
            detected_at: Utc::now(),
            event_id: None,
            timing: None,
        };
        assert!(!low_severity.should_alert(AlertSensitivity::High));
    }
}
