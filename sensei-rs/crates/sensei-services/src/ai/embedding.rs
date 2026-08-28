//! Deterministic local embeddings (item 24): a 384-dim bag-of-token hash
//! embedding — NO external model required. It powers the DENSE leg of the
//! hybrid retrieval pipeline (lexical + dense + authority + recency).
//! Embeddings are locators, never truth: retrieved ids are hydrated
//! through canonical tools.

use std::collections::HashMap;

pub const DIM: usize = 384;

/// Deterministic tokenization (lowercase alphanumeric runs).
pub fn tokens(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    let mut out = Vec::new();
    let mut current = String::new();
    for c in lower.chars() {
        if c.is_alphanumeric() {
            current.push(c);
        } else if !current.is_empty() {
            out.push(std::mem::take(&mut current));
        }
    }
    if !current.is_empty() {
        out.push(current);
    }
    out
}

/// Stable bucket index for a token (deterministic across runs/processes).
fn bucket(token: &str, seed: u64) -> usize {
    let mut h: u64 = seed.wrapping_add(0x9E37_79B9_7F4A_7C15);
    for b in token.bytes() {
        h = (h ^ u64::from(b)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    }
    (h ^ (h >> 29)) as usize % DIM
}

/// Deterministic 384-dim embedding: term-frequency hashing with sign
/// hashing (each token lands in two buckets with signed weights), then
/// L2-normalized. Collision-tolerant; identical texts -> identical
/// vectors.
pub fn embed(text: &str) -> Vec<f32> {
    let mut vec = vec![0.0f32; DIM];
    let toks = tokens(text);
    let mut counts: HashMap<String, usize> = HashMap::new();
    for t in &toks {
        *counts.entry(t.clone()).or_insert(0) += 1;
    }
    for (t, count) in counts {
        let w = (count as f32).sqrt();
        for (b, sign) in [(bucket(&t, 1), 1.0f32), (bucket(&t, 2), -1.0f32)] {
            vec[b] += sign * w;
        }
    }
    // L2 normalize.
    let norm: f32 = vec.iter().map(|v| v * v).sum::<f32>().sqrt();
    if norm > 1e-9 {
        for v in vec.iter_mut() {
            *v /= norm;
        }
    }
    vec
}

/// Cosine similarity between two normalized vectors.
pub fn cosine(a: &[f32], b: &[f32]) -> f32 {
    a.iter().zip(b.iter()).map(|(x, y)| x * y).sum()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn embedding_is_deterministic() {
        let a = embed("solder bridge on the stencil printer");
        let b = embed("solder bridge on the stencil printer");
        assert_eq!(a, b);
        assert_eq!(a.len(), DIM);
        let norm: f32 = a.iter().map(|v| v * v).sum();
        assert!((norm - 1.0).abs() < 1e-3, "must be L2-normalized");
    }

    #[test]
    fn related_texts_are_more_similar() {
        let related = cosine(
            &embed("stencil printer solder defect"),
            &embed("solder bridge printer"),
        );
        let unrelated = cosine(
            &embed("stencil printer solder defect"),
            &embed("invoice payment ledger"),
        );
        assert!(
            related > unrelated,
            "related={related} unrelated={unrelated}"
        );
    }

    #[test]
    fn identical_texts_have_similarity_one() {
        let a = embed("kanban card replenishment");
        let b = embed("kanban card replenishment");
        assert!((cosine(&a, &b) - 1.0).abs() < 1e-5);
    }
}
