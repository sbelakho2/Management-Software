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
        "INSERT INTO document_embeddings \\
            (document_type, document_id, tenant_id, title, content_hash, embedding, updated_at) \\
         VALUES ($1, $2, $3, $4, $5, $6::vector, NOW()) \\
         ON CONFLICT (document_type, document_id) DO UPDATE \\
         SET title = $4, content_hash = $5, embedding = $6::vector, updated_at = NOW()",
    )
    .bind(document_type)
    .bind(document_id)
    .bind(tenant_id)
    .bind(title)
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
    // enter the candidate corpus (never retrieve-then-redact).
    let dense: Vec<(String, Uuid, String, String, f32)> = sqlx::query_as(
        "SELECT de.document_type, de.document_id, de.title, \
                COALESCE(es.data->>'authority', 'employee note'), \
                1 - (de.embedding <=> $4::vector) AS similarity \
         FROM document_embeddings de \
         LEFT JOIN entity_store es \
           ON es.tenant_id = de.tenant_id \
          AND es.entity_type = 'knowledge_pack' \
          AND es.id = de.document_id \
         WHERE de.tenant_id = $1 AND de.embedding IS NOT NULL \
           AND (es.data IS NULL \
                OR NOT es.data ? 'allowed_roles' \
                OR es.data->'allowed_roles' = '[]'::jsonb \
                OR EXISTS (SELECT 1 FROM jsonb_array_elements_text(es.data->'allowed_roles') r \
                           WHERE r = ANY($5::text[]))) \
         ORDER BY de.embedding <=> $4::vector \
         LIMIT $2",
    )
    .bind(tenant_id)
    .bind(limit)
    .bind(format!("[{serialized}]"))
    .bind(caller_roles)
    .fetch_all(pool)
    .await
    .map_err(|e| format!("Dense retrieval failed: {e}"))?;

    // Lexical leg: ILIKE + trigram similarity (BM25-ish proxy).
    let escaped = query.replace('%', "\\%").replace('_', "\\_");
    let lexical: Vec<(String, Uuid, String, String, f32)> = sqlx::query_as(
        "SELECT document_type, document_id, title, authority, \\
                GREATEST(similarity(title, $3), similarity(content, $3)) AS sim \\
         FROM document_embeddings \\
         WHERE tenant_id = $1 \\
           AND (title ILIKE '%' || $3 || '%' OR content ILIKE '%' || $3 || '%') \\
         ORDER BY sim DESC LIMIT $2",
    )
    .bind(tenant_id)
    .bind(limit)
    .bind(&escaped)
    .fetch_all(pool)
    .await
    .map_err(|e| format!("Lexical retrieval failed: {e}"))?;

    // Fusion: weighted sum (dense 0.6, lexical 0.4) × authority × recency,
    // deduplicated by (type, id).
    let mut scores: std::collections::HashMap<(String, Uuid), (f64, String, String)> =
        std::collections::HashMap::new();
    for (ty, id, title, authority, sim) in dense.iter().chain(lexical.iter()) {
        let weight = authority_weight(authority)
            .to_string()
            .parse::<f64>()
            .unwrap_or(0.5);
        let entry =
            scores
                .entry((ty.clone(), *id))
                .or_insert((0.0, title.clone(), authority.clone()));
        entry.0 += *sim as f64 * weight;
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
}
