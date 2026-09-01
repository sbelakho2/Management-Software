//! Context cache architecture (fifteenth audit 3-5/17/23 + A5): L0
//! serialized sections, L1 resolved references, L2 assembled bundles.
//! Every key carries the TRUST DOMAIN + access digest — cache salting is
//! mandatory: restricted context for principal A is never reused for B.

/// The cache security domain (item 23): two principals share a cache
/// entry only when the digest matches.
#[derive(Debug, Clone, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub struct CacheDomain {
    pub org_id: String,
    pub policy_revision: u64,
    pub access_digest: [u8; 32],
    pub data_class: String,
}

impl CacheDomain {
    /// Deterministic access digest — CRYPTOGRAPHIC (seventeenth audit
    /// item: FNV is non-cryptographic and is no longer used for cache
    /// security). SHA-256 over the sorted roles, site scope, sensitivity
    /// ceiling AND the caller's effective permissions: identical inputs
    /// give identical digests; any authorization change shifts it.
    pub fn digest(
        roles: &[String],
        site_id: Option<uuid::Uuid>,
        sensitivity_ceiling: &str,
        permissions: &[String],
    ) -> [u8; 32] {
        use sha2::{Digest, Sha256};
        let mut hasher = Sha256::new();
        let mut sorted_roles = roles.to_vec();
        sorted_roles.sort();
        sorted_roles.dedup();
        let mut sorted_perms = permissions.to_vec();
        sorted_perms.sort();
        sorted_perms.dedup();
        hasher.update(format!(
            "roles={:?}|site={}|ceiling={}|perms={:?}",
            sorted_roles,
            site_id.unwrap_or(uuid::Uuid::nil()),
            sensitivity_ceiling,
            sorted_perms
        ));
        hasher.finalize().into()
    }
}

/// Capacity-bound cache helper: insertion-order eviction keeps every
/// cache bounded (seventeenth audit performance item) — the L0/L1/L2
/// maps and the tool replay store can no longer grow without limit.
#[derive(Debug, Clone)]
pub struct BoundedMap<V> {
    entries: std::collections::HashMap<String, V>,
    order: std::collections::VecDeque<String>,
    capacity: usize,
}

impl<V> BoundedMap<V> {
    pub fn new(capacity: usize) -> Self {
        Self {
            entries: std::collections::HashMap::new(),
            order: std::collections::VecDeque::new(),
            capacity: capacity.max(1),
        }
    }

    pub fn get(&self, key: &str) -> Option<&V> {
        self.entries.get(key)
    }

    pub fn insert(&mut self, key: String, value: V) {
        match self.entries.entry(key.clone()) {
            std::collections::hash_map::Entry::Occupied(mut e) => {
                e.insert(value);
                return;
            }
            std::collections::hash_map::Entry::Vacant(v) => {
                v.insert(value);
            }
        }
        self.order.push_back(key);
        while self.order.len() > self.capacity {
            if let Some(evicted) = self.order.pop_front() {
                self.entries.remove(&evicted);
            }
        }
    }

    pub fn remove(&mut self, key: &str) {
        self.entries.remove(key);
        self.order.retain(|k| k != key);
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

/// L0 — serialized canonical context sections (item 4): model-independent
/// prompt sections keyed by section id + revision. Cheap RAM, bounded.
#[derive(Debug)]
pub struct L0Cache {
    entries: BoundedMap<String>,
}
impl Default for L0Cache {
    fn default() -> Self {
        Self {
            entries: BoundedMap::new(4096),
        }
    }
}
impl L0Cache {
    pub fn get(&self, section_id: &str, revision: u64) -> Option<&str> {
        self.entries
            .get(&format!("{section_id}:v{revision}"))
            .map(|s| s.as_str())
    }
    pub fn put(&mut self, section_id: &str, revision: u64, content: String) {
        self.entries
            .insert(format!("{section_id}:v{revision}"), content);
    }
}

/// L1 — retrieval cache: resolved context references (query shape +
/// scope + knowledge revisions → source ids). Invalidate aggressively.
#[derive(Debug)]
pub struct L1Cache {
    entries: BoundedMap<Vec<String>>,
}
impl Default for L1Cache {
    fn default() -> Self {
        Self {
            entries: BoundedMap::new(2048),
        }
    }
}
impl L1Cache {
    pub fn get(&self, key: &str) -> Option<&Vec<String>> {
        self.entries.get(key)
    }
    pub fn put(&mut self, key: String, source_ids: Vec<String>) {
        self.entries.insert(key, source_ids);
    }
    pub fn invalidate(&mut self, key: &str) {
        self.entries.remove(key);
    }
}

/// L2 — assembled context bundle cache (item 4/23): keyed by the SECURITY
/// DOMAIN (salt) + source revision set + policy revision. A bundle is
/// reused only when the full key matches — restricted context never
/// crosses principals. Bounded.
#[derive(Debug)]
pub struct L2Cache {
    entries: BoundedMap<serde_json::Value>,
}
impl Default for L2Cache {
    fn default() -> Self {
        Self {
            entries: BoundedMap::new(1024),
        }
    }
}
impl L2Cache {
    pub fn key(domain: &CacheDomain, source_revisions: &[String]) -> String {
        format!(
            "{}|{}|{}|{}",
            hex(&domain.access_digest),
            domain.policy_revision,
            domain.data_class,
            source_revisions.join("&")
        )
    }
    pub fn get(&self, key: &str) -> Option<&serde_json::Value> {
        self.entries.get(key)
    }
    pub fn put(&mut self, key: String, bundle: serde_json::Value) {
        self.entries.insert(key, bundle);
    }
}

/// KV/prefix-cache key (item 5/23): model fingerprint + trust domain +
/// prefix hash. A KV cache is model-specific and domain-isolated.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct ModelFingerprint {
    pub architecture_hash: u128,
    pub weights_hash: u128,
    pub tokenizer_hash: u128,
    pub quantization_id: u32,
    pub context_format_version: u32,
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct PrefixCacheKey {
    pub model: ModelFingerprint,
    pub trust_domain: String,
    pub policy_revision: u64,
    pub prefix_hash: [u8; 32],
}

fn hex(bytes: &[u8; 32]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn domain(roles: &[&str], data_class: &str, policy_revision: u64) -> CacheDomain {
        let roles: Vec<String> = roles.iter().map(|s| s.to_string()).collect();
        CacheDomain {
            org_id: "org-1".into(),
            policy_revision,
            access_digest: CacheDomain::digest(&roles, None, "restricted", &[]),
            data_class: data_class.into(),
        }
    }

    #[test]
    fn different_roles_produce_different_digests() {
        let plant_manager = CacheDomain::digest(&["plant_manager".into()], None, "restricted", &[]);
        let auditor = CacheDomain::digest(&["auditor".into()], None, "restricted", &[]);
        assert_ne!(plant_manager, auditor);
    }

    #[test]
    fn same_authorization_state_produces_same_digest() {
        let a = CacheDomain::digest(
            &["plant_manager".into(), "operator".into()],
            Some(uuid::Uuid::parse_str("00000000-0000-0000-0000-000000000001").unwrap()),
            "restricted",
            &[],
        );
        let b = CacheDomain::digest(
            &["plant_manager".into(), "operator".into()],
            Some(uuid::Uuid::parse_str("00000000-0000-0000-0000-000000000001").unwrap()),
            "restricted",
            &[],
        );
        assert_eq!(a, b);
    }

    #[test]
    fn l2_key_salts_by_domain_even_for_identical_revisions() {
        let plant_manager = domain(&["plant_manager"], "restricted", 7);
        let auditor = domain(&["auditor"], "restricted", 7);
        let revisions = vec!["src-a@3".to_string(), "src-b@1".to_string()];
        assert_ne!(
            L2Cache::key(&plant_manager, &revisions),
            L2Cache::key(&auditor, &revisions)
        );
    }

    #[test]
    fn l2_key_reuse_allowed_within_same_domain() {
        let d1 = domain(&["plant_manager"], "restricted", 7);
        let d2 = domain(&["plant_manager"], "restricted", 7);
        let revisions = vec!["src-a@3".to_string()];
        assert_eq!(L2Cache::key(&d1, &revisions), L2Cache::key(&d2, &revisions));
        let mut cache = L2Cache::default();
        let key = L2Cache::key(&d1, &revisions);
        cache.put(key.clone(), serde_json::json!({"bundle": true}));
        assert_eq!(cache.get(&key), Some(&serde_json::json!({"bundle": true})));
    }

    #[test]
    fn l0_round_trip() {
        let mut cache = L0Cache::default();
        assert_eq!(cache.get("preamble", 1), None);
        cache.put("preamble", 1, "canonical preamble".into());
        assert_eq!(cache.get("preamble", 1), Some("canonical preamble"));
        assert_eq!(cache.get("preamble", 2), None);
    }

    #[test]
    fn l1_put_get_invalidate() {
        let mut cache = L1Cache::default();
        cache.put("query:scopes".into(), vec!["s1".into(), "s2".into()]);
        assert_eq!(
            cache.get("query:scopes"),
            Some(&vec!["s1".to_string(), "s2".to_string()])
        );
        cache.invalidate("query:scopes");
        assert_eq!(cache.get("query:scopes"), None);
    }

    #[test]
    fn prefix_cache_key_differs_across_model_fingerprints() {
        let a = ModelFingerprint {
            architecture_hash: 1,
            weights_hash: 2,
            tokenizer_hash: 3,
            quantization_id: 4,
            context_format_version: 1,
        };
        let b = ModelFingerprint {
            architecture_hash: 1,
            weights_hash: 2,
            tokenizer_hash: 9,
            quantization_id: 4,
            context_format_version: 1,
        };
        assert_ne!(a, b);
        let key_a = PrefixCacheKey {
            model: a,
            trust_domain: "org-1|restricted".into(),
            policy_revision: 7,
            prefix_hash: [0xAA; 32],
        };
        let key_b = PrefixCacheKey {
            model: b,
            trust_domain: "org-1|restricted".into(),
            policy_revision: 7,
            prefix_hash: [0xAA; 32],
        };
        assert_ne!(key_a, key_b);
    }

    #[test]
    fn prefix_cache_key_differs_across_trust_domains() {
        let model = ModelFingerprint {
            architecture_hash: 1,
            weights_hash: 2,
            tokenizer_hash: 3,
            quantization_id: 4,
            context_format_version: 1,
        };
        let key_a = PrefixCacheKey {
            model: model.clone(),
            trust_domain: "org-1|restricted".into(),
            policy_revision: 7,
            prefix_hash: [0xAA; 32],
        };
        let key_b = PrefixCacheKey {
            model,
            trust_domain: "org-2|restricted".into(),
            policy_revision: 7,
            prefix_hash: [0xAA; 32],
        };
        assert_ne!(key_a, key_b);
    }
}
