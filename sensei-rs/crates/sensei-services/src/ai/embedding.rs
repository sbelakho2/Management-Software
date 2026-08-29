//! Deterministic local embeddings (item 24): a 384-dim bag-of-token hash
//! embedding — NO external model required. It powers the DENSE leg of the
//! hybrid retrieval pipeline (lexical + dense + authority + recency).
//! Embeddings are locators, never truth: retrieved ids are hydrated
//! through canonical tools.
//!
//! Semantic layer (item 22): before hashing, tokens are EXPANDED through a
//! TPS concept lexicon — surface language maps onto canonical concepts, so
//! "the line keeps starving after changeover" and "material presentation
//! and pull are interrupted during setup" share concept buckets WITHOUT
//! sharing tokens. The lexicon is bilingual (English/French core; the
//! system's operating languages) and every mapping is explicit and
//! testable — this is a deterministic semantic feature, not a bag of
//! opaque hashes.

use std::collections::HashMap;

pub const DIM: usize = 384;

/// Canonical TPS concepts (internal vocabulary — the user never sees them).
/// Each maps several surface expressions (en/fr) onto ONE concept bucket.
const CONCEPT_LEXICON: &[(&str, &[&str])] = &[
    // Flow
    (
        "concept_flow",
        &[
            "flow",
            "flux",
            "starve",
            "starving",
            "starvation",
            "manque",
            "asphyxie",
            "blocked",
            "blockage",
            "bloque",
            "bouchon",
            "interruption",
            "waiting",
            "wait",
            "attente",
            "idle",
            "inactif",
        ],
    ),
    // Pull
    (
        "concept_pull",
        &[
            "pull",
            "tirer",
            "kanban",
            "just in time",
            "jit",
            "demand pull",
            "traction",
            "replenish",
            "replenishment",
            "reapprovisionnement",
            "consume",
            "consumption",
            "consommation",
        ],
    ),
    // Unevenness / mura
    (
        "concept_unevenness",
        &[
            "uneven",
            "unevenness",
            "irregular",
            "swing",
            "swings",
            "swinging",
            "fluctuation",
            "fluctuations",
            "volatile",
            "variability",
            "variation",
            "irregulier",
            "oscillation",
            "surge",
            "peaks",
            "waves",
        ],
    ),
    // Overproduction / batching
    (
        "concept_overproduction",
        &[
            "overproduce",
            "overproduction",
            "surproduction",
            "excess",
            "excès",
            "surplus",
            "too much",
            "trop",
            "batch",
            "batches",
            "lot",
            "lots",
            "large lot",
            "run size",
            "make ahead",
            "ahead of demand",
        ],
    ),
    // Standard WIP
    (
        "concept_standard_wip",
        &[
            "standard wip",
            "work in process",
            "wip",
            "encours",
            "en cours",
            "buffer",
            "tampon",
            "inventory level",
            "niveau de stock",
            "stock level",
        ],
    ),
    // Material presentation
    (
        "concept_material_presentation",
        &[
            "material presentation",
            "presentation",
            "presentation of materials",
            "kitting",
            "kit",
            "kits",
            "kits de",
            "parts presentation",
            "presentation des pieces",
            "feeding",
            "alimentation",
            "delivery to line",
            "livraison",
        ],
    ),
    // Changeover
    (
        "concept_changeover",
        &[
            "changeover",
            "changement de serie",
            "setup",
            "set up",
            "reglage",
            "reconfig",
            "switchover",
            "model change",
        ],
    ),
    // Shortage
    (
        "concept_shortage",
        &[
            "shortage",
            "shortages",
            "rupture",
            "pénurie",
            "missing",
            "manquant",
            "out of stock",
            "stockout",
            "stock out",
            "backorder",
        ],
    ),
    // Quality at source
    (
        "concept_quality_source",
        &[
            "quality at source",
            "qualite a la source",
            "defect",
            "defects",
            "défaut",
            "défauts",
            "nonconformity",
            "non-conformity",
            "ncr",
            "rework",
            "retouche",
            "scrap",
            "rebut",
            "inspection",
            "controle",
        ],
    ),
    // Jidoka / stop
    (
        "concept_jidoka",
        &[
            "stop the line",
            "andon",
            "line stop",
            "arret de ligne",
            "stop",
            "stopped",
            "arrêt",
            "help needed",
            "j' ai besoin d'aide",
            "need help",
            "cannot keep pace",
        ],
    ),
    // Heijunka / leveling
    (
        "concept_leveling",
        &[
            "leveling",
            "lissage",
            "heijunka",
            "level schedule",
            "level production",
            "even out",
        ],
    ),
    // Standard work
    (
        "concept_standard_work",
        &[
            "standard work",
            "travail standard",
            "standardized work",
            "work standard",
            "job instruction",
            "operation sheet",
            "fichier de poste",
        ],
    ),
    // Gemba / observation
    (
        "concept_gemba",
        &[
            "gemba",
            "go see",
            "allez voir",
            "observe",
            "observation",
            "observer",
            "actual condition",
            "condition reelle",
            "genchi genbutsu",
        ],
    ),
    // Kaizen / improvement
    (
        "concept_improvement",
        &[
            "improve",
            "improvement",
            "amelioration",
            "kaizen",
            "countermeasure",
            "contremesure",
            "corrective action",
            "action corrective",
            "pdca",
        ],
    ),
    // Load / muri
    (
        "concept_overburden",
        &[
            "overburden",
            "surcharge",
            "muri",
            "too fast",
            "trop rapide",
            "strain",
            "fatigue",
            "ergonomics",
            "ergonomie",
            "hard to do",
            "difficile",
            "awkward",
            "workaround",
            "contournement",
        ],
    ),
    // Recurrence
    (
        "concept_recurrence",
        &[
            "recur",
            "recurring",
            "recurrence",
            "recidive",
            "again",
            "encore",
            "repeat",
            "repetition",
            "repetitif",
            "comes back",
            "returns",
        ],
    ),
    // Constraint / bottleneck
    (
        "concept_constraint",
        &[
            "constraint",
            "contrainte",
            "bottleneck",
            "goulot",
            "accumulate",
            "accumulating",
            "accumulation",
            "piling up",
            "s'accumule",
            "queued",
            "queue",
            "file d'attente",
        ],
    ),
];

/// Multilingual stopword-ish filter: function words carry no concept
/// signal and only add collision noise.
const CONCEPT_STOPWORDS: &[&str] = &[
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "at", "by", "is", "are",
    "was", "were", "be", "been", "has", "have", "had", "it", "its", "this", "that", "these",
    "those", "we", "you", "they", "i", "he", "she", "le", "la", "les", "un", "une", "des", "du",
    "de", "et", "ou", "en", "sur", "pour", "avec", "par", "est", "sont", "ce", "cette", "ces",
    "je", "nous", "vous",
];

/// Tokenize (lowercase alphanumeric runs), preserving multi-word surface
/// phrases that the lexicon matches ("standard wip", "just in time").
pub fn tokens(text: &str) -> Vec<String> {
    let lower = text.to_lowercase();
    let mut out = Vec::new();
    let mut current = String::new();
    for c in lower.chars() {
        if c.is_alphanumeric() || c == ' ' || c == '-' || c == '\'' || c == '’' {
            current.push(c);
        } else if !current.trim().is_empty() {
            out.push(current.trim().to_string());
            current.clear();
        }
    }
    if !current.trim().is_empty() {
        out.push(current.trim().to_string());
    }
    // Split multi-word runs back into single tokens for unigram hashing,
    // keeping the raw run for phrase matching.
    let mut singles = Vec::new();
    for tok in &out {
        for part in tok.split([' ', '-', '\'', '’']) {
            if !part.is_empty() {
                singles.push(part.to_string());
            }
        }
    }
    singles
}

/// Stable bucket index for a token (deterministic across runs/processes).
fn bucket(token: &str, seed: u64) -> usize {
    let mut h: u64 = seed.wrapping_add(0x9E37_79B9_7F4A_7C15);
    for b in token.bytes() {
        h = (h ^ u64::from(b)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
    }
    (h ^ (h >> 29)) as usize % DIM
}

/// Concept expansion (item 22): every surface token/phrase is checked
/// against the lexicon; matching concepts are emitted ALONGSIDE the
/// surface token (surface signal is preserved, concepts add the semantic
/// bridge). Stopwords are dropped — they carry no concept.
fn expanded_tokens(text: &str) -> Vec<String> {
    let singles = tokens(text);
    let lower_joined = singles.join(" ");
    let mut out: Vec<String> = Vec::new();
    for t in &singles {
        if !CONCEPT_STOPWORDS.contains(&t.as_str()) {
            out.push(t.clone());
        }
    }
    // Phrase matches: the multi-word surface expression -> concept.
    let lower = text.to_lowercase();
    for (concept, surface) in CONCEPT_LEXICON {
        for expr in *surface {
            if expr.contains(' ') {
                if lower.contains(expr) {
                    out.push((*concept).to_string());
                }
            } else if singles.iter().any(|t| t == expr) {
                out.push((*concept).to_string());
            }
        }
    }
    let _ = lower_joined;
    out
}

/// Deterministic 384-dim embedding: term-frequency hashing with sign
/// hashing (each token lands in two buckets with signed weights), then
/// L2-normalized. Collision-tolerant; identical texts -> identical
/// vectors. Concept-expanded (item 22): surface synonyms in en/fr land in
/// the same concept buckets, so the dense leg connects semantically
/// related expressions WITHOUT shared surface tokens.
pub fn embed(text: &str) -> Vec<f32> {
    let mut vec = vec![0.0f32; DIM];
    let toks = expanded_tokens(text);
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

    #[test]
    fn semantic_synonyms_connect_without_shared_tokens() {
        // Item 22: "line starving after changeover" and "material
        // presentation interrupted during setup" share NO surface token,
        // yet both map to flow + material-presentation + changeover
        // concept buckets and must be closer than an unrelated text.
        let a = embed("the line keeps starving after changeover");
        let b = embed("material presentation interrupted during setup");
        let unrelated = embed("invoice payment ledger reconciliation");
        let sim_ab = cosine(&a, &b);
        let sim_unrelated = cosine(&a, &unrelated);
        assert!(
            sim_ab > sim_unrelated,
            "semantic bridge failed: ab={sim_ab} unrelated={sim_unrelated}"
        );
    }

    #[test]
    fn multilingual_equivalence() {
        // Item 22: English and French surface expressions for the same
        // condition must land closer than an unrelated topic.
        let en = embed("the line is starving, waiting for kits");
        let fr = embed("la ligne manque de pieces, attente des kits");
        let unrelated = embed("monthly financial close");
        let sim = cosine(&en, &fr);
        let sim_unrelated = cosine(&en, &unrelated);
        assert!(
            sim > sim_unrelated,
            "multilingual equivalence failed: sim={sim} unrelated={sim_unrelated}"
        );
    }

    #[test]
    fn overproduction_vs_flow_distinction() {
        // The lexicon must not collapse DIFFERENT concepts: overproduction
        // and pull are distinct; batching-related text must be closer to
        // overproduction than to flow vocabulary.
        let batch = embed("large batches made ahead of demand");
        let overprod = embed("overproduction excess stock");
        let flow = embed("smooth flow pull replenishment");
        assert!(
            cosine(&batch, &overprod) > cosine(&batch, &flow),
            "batch should cluster with overproduction, not flow"
        );
    }
}
