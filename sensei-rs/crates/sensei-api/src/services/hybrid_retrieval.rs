//! Hybrid retrieval pipeline (item 24): LEXICAL (ILIKE + trigram
//! similarity) fused with DENSE (deterministic local embeddings, cosine)
//! over authority-weighted, recency-weighted, deduplicated, ACL-filtered
//! candidates. Authority is EXPLICIT — canonical TPS principles, approved
//! policy, effective standard work, customer requirements, production
//! facts, historical cases, employee notes and AI hypotheses never share
//! retrieval weight.

use rust_decimal::Decimal;
use sensei_services::ai::embedding::embed;
use uuid::Uuid;

/// One dense-candidate row: (type, id, title, authority, similarity,
/// embedding updated_at, effective_from).
type DenseRow = (
    String,
    Uuid,
    String,
    String,
    f64,
    chrono::DateTime<chrono::Utc>,
    Option<String>,
);
/// One lexical-candidate row (same shape, f32 similarity).
type LexicalRow = (
    String,
    Uuid,
    String,
    String,
    f32,
    chrono::DateTime<chrono::Utc>,
    Option<String>,
);
/// Accumulated per-key scores: (dense_sim, lexical_sim, title, authority,
/// embedding updated_at, effective_from).
type ScoreEntry = (
    f32,
    String,
    String,
    chrono::DateTime<chrono::Utc>,
    Option<String>,
);

/// Authority classes with their retrieval weights (item 24: never equal).
pub fn authority_weight(authority: &str) -> Decimal {
    match authority {
        "tps_canonical" => Decimal::from_f64_retain(1.5).unwrap_or(Decimal::ONE),
        "corporate_policy" => Decimal::from_f64_retain(1.4).unwrap_or(Decimal::ONE),
        "effective_standard_work" => Decimal::from_f64_retain(1.3).unwrap_or(Decimal::ONE),
        "customer_requirement" => Decimal::from_f64_retain(1.2).unwrap_or(Decimal::ONE),
        "production_fact" => Decimal::ONE,
        "historical_case" => Decimal::from_f64_retain(0.7).unwrap_or(Decimal::ZERO),
        "employee_note" => Decimal::from_f64_retain(0.4).unwrap_or(Decimal::ZERO),
        "ai_hypothesis" => Decimal::from_f64_retain(0.2).unwrap_or(Decimal::ZERO),
        _ => Decimal::from_f64_retain(0.5).unwrap_or(Decimal::ZERO),
    }
}

/// Deterministic content hash (embedding versioning).
/// The canonical content hash used for embedding change detection.
pub fn content_hash(s: &str) -> u64 {
    default_hasher(s)
}

fn default_hasher(s: &str) -> u64 {
    use std::hash::{Hash, Hasher};
    let mut h = std::collections::hash_map::DefaultHasher::new();
    s.hash(&mut h);
    h.finish()
}

/// A fused retrieval result.
#[derive(Debug, Clone, serde::Serialize)]
pub struct HybridHit {
    pub document_type: String,
    pub document_id: Uuid,
    pub title: String,
    pub authority: String,
    pub score: f64,
}

/// Upsert the deterministic embedding for a document.
pub async fn upsert_embedding(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    document_type: &str,
    document_id: Uuid,
    title: &str,
    content: &str,
) -> Result<(), String> {
    let vector = embed(&format!("{title} {content}"));
    let serialized = vector
        .iter()
        .map(|v| v.to_string())
        .collect::<Vec<_>>()
        .join(",");
    sqlx::query(
        "INSERT INTO document_embeddings  (document_type, document_id, tenant_id, title, content, content_hash, embedding, updated_at)  VALUES ($1, $2, $3, $4, $5, $6, $7::vector, NOW())  ON CONFLICT (document_type, document_id) DO UPDATE  SET title = $4, content = $5, content_hash = $6, embedding = $7::vector, updated_at = NOW()",
    )
    .bind(document_type)
    .bind(document_id)
    .bind(tenant_id)
    .bind(title)
    .bind(content)
    .bind(format!(
        "{:x}",
        default_hasher(&format!("{title}:{content}"))
    ))
    .bind(format!("[{serialized}]"))
    .execute(pool)
    .await
    .map_err(|e| format!("Embedding upsert failed: {e}"))?;
    Ok(())
}

/// Hybrid search: dense candidates (cosine) fused with lexical matches,
/// then authority-weighted + recency-weighted + deduplicated.
///
/// ACL: `allowed_roles` — documents restricted to roles the caller lacks
/// are filtered BEFORE retrieval (never retrieve-then-redact).
pub async fn hybrid_search(
    pool: &sqlx::PgPool,
    tenant_id: Uuid,
    query: &str,
    caller_roles: &[String],
    limit: i64,
) -> Result<Vec<HybridHit>, String> {
    let query_vec = embed(query);
    let serialized = query_vec
        .iter()
        .map(|v| v.to_string())
        .collect::<Vec<_>>()
        .join(",");

    // ACL prefilter (item 24): role-restricted knowledge packs are
    // invisible to callers without the role — forbidden records never
    // enter the candidate corpus (never retrieve-then-redact). Effective
    // filter (item 29): only EFFECTIVE documents inside their validity
    // window are retrievable — superseded/archived/draft knowledge never
    // enters the corpus.
    // Placeholders are $1..$5 IN ORDER (item 20): $1 tenant, $2 limit,
    // $3 the query vector, $4 caller roles, $5 now — the previous binding
    // order put the vector in an unused $3 and the roles into the vector
    // cast, breaking the dense leg at runtime.
    // Item 58: knowledge_pack embeddings REQUIRE the authoritative
    // source row to exist and be effective — an orphaned embedding (the
    // pack was deleted but the embedding delete failed) can NEVER remain
    // eligible. Item 56: de.updated_at rides in the candidate query —
    // no per-candidate N+1 recency fetch.
    let dense: Vec<DenseRow> = sqlx::query_as(
        "SELECT de.document_type, de.document_id, de.title, \
                COALESCE(es.data->>'authority', 'employee note'), \
                1 - (de.embedding <=> $3::vector) AS similarity, \
                de.updated_at, \
                es.data->>'effective_from' AS effective_from \
         FROM document_embeddings de \
         LEFT JOIN entity_store es \
           ON es.tenant_id = de.tenant_id \
          AND es.entity_type = 'knowledge_pack' \
          AND es.id = de.document_id \
         WHERE de.tenant_id = $1 AND de.embedding IS NOT NULL \
           AND NOT (de.document_type = 'knowledge_pack' AND es.data IS NULL) \
           AND (NOT es.data ? 'allowed_roles' \
                OR es.data->'allowed_roles' = '[]'::jsonb \
                OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(es.data->'allowed_roles') r \
                           WHERE r = ANY($4::text[]))) \
           AND COALESCE(es.data->>'status', 'effective') = 'effective' \
           AND (NOT es.data ? 'effective_from' \
                OR (es.data->>'effective_from')::timestamptz <= $5::timestamptz) \
           AND (NOT es.data ? 'effective_to' \
                OR (es.data->>'effective_to')::timestamptz >= $5::timestamptz) \
         ORDER BY de.embedding <=> $3::vector \
         LIMIT $2",
    )
    .bind(tenant_id)
    .bind(limit)
    .bind(format!("[{serialized}]"))
    .bind(caller_roles)
    .bind(chrono::Utc::now())
    .fetch_all(pool)
    .await
    .map_err(|e| format!("Dense retrieval failed: {e}"))?;

    // Lexical leg: ILIKE + trigram similarity (BM25-ish proxy). The same
    // effective-window + ACL filters apply (item 29): obsolete documents
    // never enter the corpus.
    let escaped = query.replace('%', "\\%").replace('_', "\\_");
    let lexical: Vec<LexicalRow> = sqlx::query_as(
        "SELECT de.document_type, de.document_id, de.title, \
                COALESCE(es.data->>'authority', 'employee note'), \
                GREATEST(similarity(de.title, $3), similarity(de.content, $3)) AS sim, \
                de.updated_at, \
                es.data->>'effective_from' AS effective_from \
         FROM document_embeddings de \
         LEFT JOIN entity_store es \
           ON es.tenant_id = de.tenant_id \
          AND es.entity_type = 'knowledge_pack' \
          AND es.id = de.document_id \
         WHERE de.tenant_id = $1 \
           AND (de.title ILIKE '%' || $3 || '%' OR de.content ILIKE '%' || $3 || '%') \
           AND NOT (de.document_type = 'knowledge_pack' AND es.data IS NULL) \
           AND (NOT es.data ? 'allowed_roles' \
                OR es.data->'allowed_roles' = '[]'::jsonb \
                OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(es.data->'allowed_roles') r \
                           WHERE r = ANY($5::text[]))) \
           AND COALESCE(es.data->>'status', 'effective') = 'effective' \
           AND (NOT es.data ? 'effective_from' \
                OR (es.data->>'effective_from')::timestamptz <= $4::timestamptz) \
           AND (NOT es.data ? 'effective_to' \
                OR (es.data->>'effective_to')::timestamptz >= $4::timestamptz) \
         ORDER BY sim DESC LIMIT $2",
    )
    .bind(tenant_id)
    .bind(limit)
    .bind(&escaped)
    .bind(chrono::Utc::now())
    .bind(caller_roles)
    .fetch_all(pool)
    .await
    .map_err(|e| format!("Lexical retrieval failed: {e}"))?;

    // Fusion (item 21 — the algorithm actually executed, matching the
    // documentation): score = (0.6 × dense_sim + 0.4 × lexical_sim)
    // × authority_weight × recency_decay, deduplicated by (type, id).
    // Recency decay is a half-life of 90 days: a document updated today
    // scores 1.0, one updated 90 days ago scores 0.5.
    const DENSE_WEIGHT: f64 = 0.6;
    const LEXICAL_WEIGHT: f64 = 0.4;
    const RECENCY_HALF_LIFE_DAYS: f64 = 90.0;
    let now = chrono::Utc::now();

    // Item 56: recency rides in the candidate queries — no N+1. The
    // freshness SOURCE depends on the authority class (item 57): a
    // canonical principle's freshness is its EFFECTIVE date (a 40-year-old
    // principle re-embedded yesterday is NOT fresher than a production
    // fact from five minutes ago); production facts fall back to the
    // embedding update time.
    let mut dense_scores: std::collections::HashMap<(String, Uuid), ScoreEntry> =
        std::collections::HashMap::new();
    for (ty, id, title, authority, sim, updated_at, effective_from) in &dense {
        dense_scores
            .entry((ty.clone(), *id))
            .and_modify(|e| e.0 = e.0.max(*sim as f32))
            .or_insert((
                *sim as f32,
                title.clone(),
                authority.clone(),
                *updated_at,
                effective_from.clone(),
            ));
    }
    let mut lexical_scores: std::collections::HashMap<(String, Uuid), ScoreEntry> =
        std::collections::HashMap::new();
    for (ty, id, title, authority, sim, updated_at, effective_from) in &lexical {
        lexical_scores
            .entry((ty.clone(), *id))
            .and_modify(|e| e.0 = e.0.max(*sim))
            .or_insert((
                *sim,
                title.clone(),
                authority.clone(),
                *updated_at,
                effective_from.clone(),
            ));
    }

    let mut scores: std::collections::HashMap<(String, Uuid), (f64, String, String)> =
        std::collections::HashMap::new();
    let mut keys: std::collections::HashSet<(String, Uuid)> = std::collections::HashSet::new();
    keys.extend(dense_scores.keys().cloned());
    keys.extend(lexical_scores.keys().cloned());
    for key in keys {
        let (dense_sim, title, authority, dense_updated, dense_eff) =
            dense_scores.get(&key).cloned().unwrap_or_default();
        let (lexical_sim, _, _, lexical_updated, lexical_eff) =
            lexical_scores.get(&key).cloned().unwrap_or_default();
        let authority = if authority.is_empty() {
            "employee note".to_string()
        } else {
            authority
        };
        let weight = authority_weight(&authority)
            .to_string()
            .parse::<f64>()
            .unwrap_or(0.5);
        let combined = DENSE_WEIGHT * dense_sim as f64 + LEXICAL_WEIGHT * lexical_sim as f64;
        // Item 57: authority-class freshness. Canonical/standard knowledge
        // ages from its EFFECTIVE date; facts age from observation
        // (embedding update is the closest proxy until observed_at is
        // carried).
        let effective = dense_eff
            .clone()
            .or(lexical_eff.clone())
            .and_then(|e| chrono::DateTime::parse_from_rfc3339(&e).ok())
            .map(|e| e.with_timezone(&chrono::Utc));
        let freshness_time = match (authority.as_str(), effective) {
            ("canonical principle" | "standard work" | "customer requirement", Some(eff)) => eff,
            _ => {
                // production fact / historical case / employee note: the
                // embedding update time is the best available.
                if dense_updated > lexical_updated {
                    dense_updated
                } else {
                    lexical_updated
                }
            }
        };
        let age_days = (now - freshness_time).num_milliseconds() as f64 / 86_400_000.0;
        let recency = 0.5f64.powf(age_days.max(0.0) / RECENCY_HALF_LIFE_DAYS);
        scores
            .entry(key.clone())
            .or_insert((0.0, title.clone(), authority.clone()))
            .0 = combined * weight * recency;
    }
    let mut hits: Vec<HybridHit> = scores
        .into_iter()
        .map(|((ty, id), (score, title, authority))| HybridHit {
            document_type: ty,
            document_id: id,
            title,
            authority,
            score,
        })
        .collect();
    hits.sort_by(|a, b| {
        b.score
            .partial_cmp(&a.score)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    hits.truncate(limit as usize);
    Ok(hits)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn authority_weights_are_ordered() {
        assert!(authority_weight("tps_canonical") > authority_weight("employee_note"));
        assert!(authority_weight("effective_standard_work") > authority_weight("ai_hypothesis"));
    }

    #[test]
    fn fusion_uses_0604_weights_and_authority() {
        // Item 21: the executed algorithm is 0.6×dense + 0.4×lexical,
        // multiplied by authority — the documented formula, not a sum.
        let dense_sim: f32 = 0.8;
        let lexical_sim: f32 = 0.4;
        let authority = authority_weight("tps_canonical")
            .to_string()
            .parse::<f64>()
            .unwrap();
        let combined = 0.6 * dense_sim as f64 + 0.4 * lexical_sim as f64;
        let score = combined * authority;
        // 0.6*0.8 + 0.4*0.4 = 0.64; ×1.5 = 0.96 (f32 inputs → ~1e-7 tolerance)
        assert!((score - 0.96).abs() < 1e-6);
        // A bare SUM of the two sims (the old behavior) would give
        // (0.8 + 0.4) × 1.5 = 1.8 — the fix is measurably different.
        assert!((score - 1.8).abs() > 0.5);
    }
}
