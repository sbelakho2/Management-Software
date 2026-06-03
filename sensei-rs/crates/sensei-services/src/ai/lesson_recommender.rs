//! Lesson Recommendation System.
//!
//! Recommends relevant training lessons to users based on:
//! - Current role and responsibilities
//! - Skills gap analysis
//! - Recent quality issues in their area
//! - Peer learning patterns
//! - Mandatory compliance requirements
//!
//! Hybrid recommendation system combining:
//! 1. Content-based filtering (skill/topic matching via TF-IDF)
//! 2. Collaborative filtering (similar user patterns)
//! 3. Context-aware rules (role, compliance, recency)

use chrono::{DateTime, Duration, Utc};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

// ---------------------------------------------------------------------------
// Data Models
// ---------------------------------------------------------------------------

/// A training lesson.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Lesson {
    pub id: String,
    pub title: String,
    pub description: String,
    pub tags: Vec<String>,
    pub skills_taught: Vec<String>,
    pub target_roles: Vec<String>,
    pub is_mandatory: bool,
    pub compliance_required: bool,
    pub average_rating: Option<f64>,
    pub created_at: Option<DateTime<Utc>>,
}

/// A user who takes lessons.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: String,
    pub role: String,
    pub skills: Vec<String>,
}

/// Record of a lesson completion.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LessonCompletion {
    pub user_id: String,
    pub lesson_id: String,
    pub completed: bool,
    pub rating: Option<f64>,
}

/// A recommendation result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Recommendation {
    pub lesson_id: String,
    pub score: f64,
    pub explanations: HashMap<String, String>,
}

/// Training metrics for the recommender.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingMetrics {
    pub precision_at_5: f64,
    pub recall_at_5: f64,
    pub coverage: f64,
}

// ---------------------------------------------------------------------------
// TF-IDF Vectorizer (reused concept)
// ---------------------------------------------------------------------------

/// Lightweight TF-IDF vectorizer for lesson content.
#[derive(Debug, Clone)]
struct TextVectorizer {
    vocab: HashMap<String, usize>,
    idf: Vec<f64>,
    max_features: usize,
    fitted: bool,
}

impl TextVectorizer {
    fn new(max_features: usize) -> Self {
        Self {
            vocab: HashMap::new(),
            idf: Vec::new(),
            max_features,
            fitted: false,
        }
    }

    fn fit(&mut self, documents: &[String]) {
        let n_docs = documents.len() as f64;
        let mut doc_freq: HashMap<String, usize> = HashMap::new();

        for doc in documents {
            let tokens = tokenize_text(doc);
            let mut seen = HashSet::new();
            for token in tokens {
                if seen.insert(token.clone()) {
                    *doc_freq.entry(token).or_insert(0) += 1;
                }
            }
        }

        let mut freq_vec: Vec<(String, usize)> = doc_freq.into_iter().collect();
        freq_vec.sort_by(|a, b| b.1.cmp(&a.1));
        freq_vec.truncate(self.max_features);

        self.vocab.clear();
        self.idf.clear();
        for (term, df) in &freq_vec {
            let idx = self.vocab.len();
            self.vocab.insert(term.clone(), idx);
            let idf = 1.0 + ((1.0 + n_docs) / (1.0 + *df as f64)).ln() + 1.0;
            self.idf.push(idf);
        }

        self.fitted = true;
    }

    fn transform(&self, documents: &[String]) -> Vec<Vec<f64>> {
        if !self.fitted {
            return vec![vec![]; documents.len()];
        }

        documents
            .iter()
            .map(|doc| {
                let tokens = tokenize_text(doc);
                let mut tf = vec![0usize; self.vocab.len()];
                for token in &tokens {
                    if let Some(&idx) = self.vocab.get(token) {
                        tf[idx] += 1;
                    }
                }

                let max_tf = tf.iter().copied().max().unwrap_or(1).max(1) as f64;
                let mut vec = vec![0.0_f64; self.vocab.len()];
                for (idx, &count) in tf.iter().enumerate() {
                    if count > 0 && idx < self.idf.len() {
                        vec[idx] = (count as f64 / max_tf) * self.idf[idx];
                    }
                }

                // L2 normalize
                let norm: f64 = vec.iter().map(|&v| v * v).sum::<f64>().sqrt();
                if norm > 0.0 {
                    for v in &mut vec {
                        *v /= norm;
                    }
                }
                vec
            })
            .collect()
    }
}

fn tokenize_text(text: &str) -> Vec<String> {
    text.to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| s.len() >= 2)
        .map(|s| s.to_string())
        .collect()
}

// ---------------------------------------------------------------------------
// Cosine Similarity
// ---------------------------------------------------------------------------

/// Compute cosine similarity between two vectors.
fn cosine_similarity(a: &[f64], b: &[f64]) -> f64 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }
    let dot: f64 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f64 = a.iter().map(|&v| v * v).sum::<f64>().sqrt();
    let norm_b: f64 = b.iter().map(|&v| v * v).sum::<f64>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        0.0
    } else {
        dot / (norm_a * norm_b)
    }
}

/// Compute cosine similarity between a vector and a matrix.
fn cosine_similarity_matrix(vec: &[f64], matrix: &[Vec<f64>]) -> Vec<f64> {
    matrix.iter().map(|row| cosine_similarity(vec, row)).collect()
}

// ---------------------------------------------------------------------------
// Lesson Recommender
// ---------------------------------------------------------------------------

/// Hybrid recommendation system for training lessons.
#[derive(Debug, Clone)]
pub struct LessonRecommender {
    /// TF-IDF vectorizer for lesson content
    vectorizer: Option<TextVectorizer>,
    /// Lesson embeddings (TF-IDF vectors)
    lesson_embeddings: Option<Vec<Vec<f64>>>,
    /// Lesson IDs in order
    lesson_ids: Vec<String>,
    /// O(1) lookup: lesson_id -> index
    lesson_id_to_idx: HashMap<String, usize>,
    /// User similarity matrix (collaborative filtering)
    user_similarity: Option<Vec<Vec<f64>>>,
    /// Whether the model is trained
    is_trained: bool,
}

impl Default for LessonRecommender {
    fn default() -> Self {
        Self::new()
    }
}

impl LessonRecommender {
    pub fn new() -> Self {
        Self {
            vectorizer: None,
            lesson_embeddings: None,
            lesson_ids: Vec::new(),
            lesson_id_to_idx: HashMap::new(),
            user_similarity: None,
            is_trained: false,
        }
    }

    /// Train the recommendation model.
    pub fn train(
        &mut self,
        lessons: &[Lesson],
        completions: &[LessonCompletion],
        users: &[User],
    ) -> TrainingMetrics {
        if lessons.is_empty() {
            return TrainingMetrics {
                precision_at_5: 0.0,
                recall_at_5: 0.0,
                coverage: 0.0,
            };
        }

        // Build lesson content embeddings (TF-IDF)
        let lesson_texts: Vec<String> = lessons
            .iter()
            .map(|l| {
                format!(
                    "{} {} {}",
                    l.title,
                    l.description,
                    l.tags.join(" ")
                )
            })
            .collect();

        let vectorizer = TextVectorizer::new(500);
        let embeddings = vectorizer.transform(&lesson_texts);
        self.vectorizer = Some(vectorizer);
        self.lesson_embeddings = Some(embeddings);
        self.lesson_ids = lessons.iter().map(|l| l.id.clone()).collect();
        self.lesson_id_to_idx = self
            .lesson_ids
            .iter()
            .enumerate()
            .map(|(i, id)| (id.clone(), i))
            .collect();

        // Build user-lesson interaction matrix for collaborative filtering
        let user_similarity = self.build_interaction_matrix(completions, users, lessons);
        self.user_similarity = Some(user_similarity);

        self.is_trained = true;

        // Evaluate model
        self.evaluate(completions, users, lessons)
    }

    /// Generate lesson recommendations for a user.
    pub fn recommend(
        &self,
        user: &User,
        user_completions: &[LessonCompletion],
        all_lessons: &[Lesson],
        top_k: usize,
        exclude_completed: bool,
    ) -> Vec<Recommendation> {
        if !self.is_trained {
            return vec![];
        }

        // Get completed lesson IDs
        let completed_ids: HashSet<String> = user_completions
            .iter()
            .map(|c| c.lesson_id.clone())
            .collect();

        // Filter available lessons
        let available: Vec<&Lesson> = all_lessons
            .iter()
            .filter(|l| !exclude_completed || !completed_ids.contains(&l.id))
            .collect();

        if available.is_empty() {
            return vec![];
        }

        // Score each available lesson
        let mut scored: Vec<Recommendation> = available
            .iter()
            .map(|lesson| {
                let (score, explanations) =
                    self.score_lesson(user, lesson, user_completions, all_lessons);
                Recommendation {
                    lesson_id: lesson.id.clone(),
                    score,
                    explanations,
                }
            })
            .collect();

        // Sort by score descending and take top-k
        scored.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(top_k);
        scored
    }

    // -----------------------------------------------------------------------
    // Internal scoring
    // -----------------------------------------------------------------------

    /// Score a single lesson for a user using hybrid approach.
    fn score_lesson(
        &self,
        user: &User,
        lesson: &Lesson,
        user_completions: &[LessonCompletion],
        all_lessons: &[Lesson],
    ) -> (f64, HashMap<String, String>) {
        let mut explanations = HashMap::new();
        let mut score = 0.0_f64;

        // 1. Role match (30% weight)
        let role_match = self.check_role_match(user, lesson);
        if role_match {
            score += 0.3;
            explanations.insert(
                "role".into(),
                format!("Matches {} role requirements", user.role),
            );
        }

        // 2. Skills gap (25% weight)
        let skills_gap = self.calculate_skills_gap(user, lesson);
        score += skills_gap * 0.25;
        if skills_gap > 0.5 {
            explanations.insert("skills".into(), "Addresses critical skills gap".into());
        }

        // 3. Content similarity to completed lessons (20% weight)
        if !user_completions.is_empty() {
            let content_sim =
                self.calculate_content_similarity(lesson, user_completions, all_lessons);
            score += content_sim * 0.20;
            if content_sim > 0.6 {
                explanations
                    .insert("similar".into(), "Similar to lessons you've completed".into());
            }
        }

        // 4. Compliance/mandatory (25% weight)
        if lesson.is_mandatory || lesson.compliance_required {
            score += 0.25;
            explanations.insert("mandatory".into(), "Compliance training required".into());
        }

        // 5. Boost for recently added lessons (5%)
        if let Some(created) = lesson.created_at {
            if (Utc::now() - created) < Duration::days(30) {
                score += 0.05;
                explanations.insert("new".into(), "Recently added content".into());
            }
        }

        // 6. Boost for high-rated lessons (5%)
        if let Some(rating) = lesson.average_rating {
            if rating >= 4.5 {
                score += 0.05;
                explanations.insert(
                    "popular".into(),
                    format!("Highly rated ({:.1}★)", rating),
                );
            }
        }

        (score, explanations)
    }

    /// Check if lesson target roles match user role.
    fn check_role_match(&self, user: &User, lesson: &Lesson) -> bool {
        if lesson.target_roles.is_empty() {
            return true; // Available to all
        }
        lesson.target_roles.contains(&user.role)
    }

    /// Calculate how well lesson addresses user's skills gap.
    fn calculate_skills_gap(&self, user: &User, lesson: &Lesson) -> f64 {
        let user_skills: HashSet<&str> = user.skills.iter().map(|s| s.as_str()).collect();
        let lesson_skills: HashSet<&str> =
            lesson.skills_taught.iter().map(|s| s.as_str()).collect();

        if lesson_skills.is_empty() {
            return 0.5; // Neutral if no skills specified
        }

        // Skills in lesson but not in user profile
        let gap: Vec<&&str> = lesson_skills.difference(&user_skills).collect();

        if gap.is_empty() {
            return 0.2; // Already have these skills
        }

        // More gap = more relevant
        let gap_ratio = gap.len() as f64 / lesson_skills.len() as f64;
        gap_ratio.min(1.0)
    }

    /// Calculate content similarity between lesson and user's completed lessons.
    fn calculate_content_similarity(
        &self,
        lesson: &Lesson,
        user_completions: &[LessonCompletion],
        _all_lessons: &[Lesson],
    ) -> f64 {
        let embeddings = match &self.lesson_embeddings {
            Some(e) => e,
            None => return 0.0,
        };

        let lesson_idx = match self.lesson_id_to_idx.get(&lesson.id) {
            Some(&idx) => idx,
            None => return 0.0,
        };

        if lesson_idx >= embeddings.len() {
            return 0.0;
        }

        let lesson_vec = &embeddings[lesson_idx];

        // Get completed lesson vectors
        let completed_indices: Vec<usize> = user_completions
            .iter()
            .filter_map(|c| self.lesson_id_to_idx.get(&c.lesson_id).copied())
            .collect();

        if completed_indices.is_empty() {
            return 0.0;
        }

        // Calculate average similarity to completed lessons
        let mut total_sim = 0.0;
        for &idx in &completed_indices {
            if idx < embeddings.len() {
                total_sim += cosine_similarity(lesson_vec, &embeddings[idx]);
            }
        }
        total_sim / completed_indices.len() as f64
    }

    /// Build user-lesson interaction matrix for collaborative filtering.
    fn build_interaction_matrix(
        &self,
        completions: &[LessonCompletion],
        users: &[User],
        lessons: &[Lesson],
    ) -> Vec<Vec<f64>> {
        let user_ids: Vec<&str> = users.iter().map(|u| u.id.as_str()).collect();
        let lesson_ids: Vec<&str> = lessons.iter().map(|l| l.id.as_str()).collect();

        let user_id_to_idx: HashMap<&str, usize> = user_ids
            .iter()
            .enumerate()
            .map(|(i, &id)| (id, i))
            .collect();
        let lesson_id_to_idx: HashMap<&str, usize> = lesson_ids
            .iter()
            .enumerate()
            .map(|(i, &id)| (id, i))
            .collect();

        let mut matrix = vec![vec![0.0_f64; lesson_ids.len()]; user_ids.len()];

        for completion in completions {
            if let (Some(&u_idx), Some(&l_idx)) = (
                user_id_to_idx.get(completion.user_id.as_str()),
                lesson_id_to_idx.get(completion.lesson_id.as_str()),
            ) {
                let mut score = 1.0;
                if completion.completed {
                    score += 0.5;
                }
                if let Some(rating) = completion.rating {
                    score += (rating - 3.0) * 0.2;
                }
                matrix[u_idx][l_idx] = score;
            }
        }

        // Compute user-user similarity
        let n_users = user_ids.len();
        if n_users == 0 {
            return vec![];
        }

        let mut similarity = vec![vec![0.0_f64; n_users]; n_users];
        for i in 0..n_users {
            for j in 0..n_users {
                if i == j {
                    similarity[i][j] = 1.0;
                } else {
                    similarity[i][j] = cosine_similarity(&matrix[i], &matrix[j]);
                }
            }
        }

        similarity
    }

    /// Evaluate model using precision@k and recall@k.
    fn evaluate(
        &self,
        completions: &[LessonCompletion],
        users: &[User],
        lessons: &[Lesson],
    ) -> TrainingMetrics {
        // Group completions by user
        let mut user_completions_map: HashMap<String, Vec<&LessonCompletion>> = HashMap::new();
        for c in completions {
            user_completions_map
                .entry(c.user_id.clone())
                .or_default()
                .push(c);
        }

        let mut precisions = Vec::new();
        let mut recalls = Vec::new();

        for user in users {
            let user_comps = match user_completions_map.get(&user.id) {
                Some(c) if c.len() >= 5 => c,
                _ => continue,
            };

            // Leave one out for testing
            let test_lesson_id = &user_comps.last().unwrap().lesson_id;
            let train_comps: Vec<LessonCompletion> = user_comps[..user_comps.len() - 1]
                .iter()
                .map(|c| (*c).clone())
                .collect();

            // Get recommendations
            let recommendations = self.recommend(
                user,
                &train_comps,
                lessons,
                5,
                true,
            );

            let recommended_ids: HashSet<&str> =
                recommendations.iter().map(|r| r.lesson_id.as_str()).collect();

            if recommended_ids.contains(test_lesson_id.as_str()) {
                precisions.push(1.0);
                recalls.push(1.0);
            } else {
                precisions.push(0.0);
                recalls.push(0.0);
            }
        }

        let precision = if precisions.is_empty() {
            0.0
        } else {
            precisions.iter().sum::<f64>() / precisions.len() as f64
        };
        let recall = if recalls.is_empty() {
            0.0
        } else {
            recalls.iter().sum::<f64>() / recalls.len() as f64
        };
        let coverage = if lessons.is_empty() {
            0.0
        } else {
            self.lesson_ids.len() as f64 / lessons.len() as f64
        };

        TrainingMetrics {
            precision_at_5: precision,
            recall_at_5: recall,
            coverage,
        }
    }
}

// ---------------------------------------------------------------------------
// Batch Recommendation Pipeline
// ---------------------------------------------------------------------------

/// Generate recommendations for all users in batch.
pub fn generate_recommendations_for_all_users(
    recommender: &LessonRecommender,
    users: &[User],
    completions: &[LessonCompletion],
    lessons: &[Lesson],
    top_k: usize,
) -> HashMap<String, Vec<Recommendation>> {
    // Group completions by user
    let mut user_completions_map: HashMap<String, Vec<LessonCompletion>> = HashMap::new();
    for c in completions {
        user_completions_map
            .entry(c.user_id.clone())
            .or_default()
            .push(c.clone());
    }

    let mut all_recommendations = HashMap::new();
    for user in users {
        let user_comps = user_completions_map
            .remove(&user.id)
            .unwrap_or_default();
        let recs = recommender.recommend(user, &user_comps, lessons, top_k, true);
        all_recommendations.insert(user.id.clone(), recs);
    }

    all_recommendations
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_lesson(id: &str, title: &str, tags: &[&str], skills: &[&str], mandatory: bool) -> Lesson {
        Lesson {
            id: id.into(),
            title: title.into(),
            description: format!("Description for {}", title),
            tags: tags.iter().map(|&s| s.to_string()).collect(),
            skills_taught: skills.iter().map(|&s| s.to_string()).collect(),
            target_roles: vec![],
            is_mandatory: mandatory,
            compliance_required: false,
            average_rating: Some(4.0),
            created_at: Some(Utc::now()),
        }
    }

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        assert!((cosine_similarity(&a, &b) - 1.0).abs() < 1e-10);

        let c = vec![0.0, 1.0, 0.0];
        assert!((cosine_similarity(&a, &c)).abs() < 1e-10);
    }

    #[test]
    fn test_tokenize_text() {
        let tokens = tokenize_text("Machine Learning Basics");
        assert!(tokens.contains(&"machine".into()));
        assert!(tokens.contains(&"learning".into()));
        assert!(tokens.contains(&"basics".into()));
    }

    #[test]
    fn test_check_role_match() {
        let recommender = LessonRecommender::new();
        let user = User {
            id: "u1".into(),
            role: "engineer".into(),
            skills: vec![],
        };

        let lesson_all = Lesson {
            target_roles: vec![],
            ..make_lesson("l1", "Test", &[], &[], false)
        };
        assert!(recommender.check_role_match(&user, &lesson_all));

        let lesson_restricted = Lesson {
            target_roles: vec!["manager".into()],
            ..make_lesson("l2", "Test", &[], &[], false)
        };
        assert!(!recommender.check_role_match(&user, &lesson_restricted));
    }

    #[test]
    fn test_calculate_skills_gap() {
        let recommender = LessonRecommender::new();

        let user = User {
            id: "u1".into(),
            role: "engineer".into(),
            skills: vec!["python".into(), "sql".into()],
        };

        let lesson = make_lesson("l1", "Rust Programming", &[], &["rust", "systems"], false);
        let gap = recommender.calculate_skills_gap(&user, &lesson);
        assert!((gap - 1.0).abs() < 0.01); // All skills are new

        let lesson2 = make_lesson("l2", "Python Advanced", &[], &["python"], false);
        let gap2 = recommender.calculate_skills_gap(&user, &lesson2);
        assert!((gap2 - 0.2).abs() < 0.01); // Already has this skill
    }

    #[test]
    fn test_text_vectorizer() {
        let docs = vec![
            "machine learning basics".into(),
            "advanced machine learning".into(),
            "deep neural networks".into(),
        ];
        let mut vec = TextVectorizer::new(10);
        let embeddings = vec.fit_transform(&docs);
        assert_eq!(embeddings.len(), 3);
        assert!(vec.vocab.len() > 0);
    }

    #[test]
    fn test_recommend() {
        let mut recommender = LessonRecommender::new();

        let lessons = vec![
            make_lesson("l1", "Python Basics", &["python"], &["python"], false),
            make_lesson("l2", "SQL Fundamentals", &["sql"], &["sql"], false),
            make_lesson(
                "l3",
                "Machine Learning",
                &["ml", "python"],
                &["ml", "python"],
                false,
            ),
        ];

        let users = vec![User {
            id: "u1".into(),
            role: "engineer".into(),
            skills: vec!["python".into()],
        }];

        let completions = vec![LessonCompletion {
            user_id: "u1".into(),
            lesson_id: "l1".into(),
            completed: true,
            rating: Some(5.0),
        }];

        let metrics = recommender.train(&lessons, &completions, &users);
        assert!(metrics.coverage > 0.0);

        let recs = recommender.recommend(&users[0], &completions, &lessons, 5, true);
        assert!(!recs.is_empty());
        // l1 should be excluded (completed), so recs should include l2 and/or l3
        assert!(!recs.iter().any(|r| r.lesson_id == "l1"));
    }

    #[test]
    fn test_empty_training() {
        let mut recommender = LessonRecommender::new();
        let metrics = recommender.train(&[], &[], &[]);
        assert!((metrics.precision_at_5 - 0.0).abs() < 1e-10);
    }

    #[test]
    fn test_batch_recommendations() {
        let mut recommender = LessonRecommender::new();
        let lessons = vec![make_lesson("l1", "Test", &[], &[], false)];
        let users = vec![User {
            id: "u1".into(),
            role: "engineer".into(),
            skills: vec![],
        }];
        recommender.train(&lessons, &[], &users);

        let all_recs = generate_recommendations_for_all_users(
            &recommender,
            &users,
            &[],
            &lessons,
            5,
        );
        assert!(all_recs.contains_key("u1"));
    }
}
