//! Model program signatures + native constrained structured output
//! (fifteenth audit item 9 + laws A9/A10): every AI function has a typed
//! program signature; structured output is compiled/validated natively,
//! never "please return JSON"; FACT/INFERENCE/HYPOTHESIS are distinct
//! epistemic types.

/// Epistemic status (fifteenth audit A10 + item 79): a model must never
/// invent operational facts — FACT/INFERENCE/HYPOTHESIS are distinct.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EpistemicStatus {
    RecordedFact,
    DerivedFact,
    Inference,
    Hypothesis,
}

/// One typed field of a program's input/output signature.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct SignatureField {
    pub name: String,
    pub kind: FieldKind,
    pub required: bool,
    pub description: String,
}

#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FieldKind {
    String,
    Integer,
    Number,
    Boolean,
    Object,
    Array,
}

/// A model program (fifteenth audit item 9): signature + allowed models +
/// tools + evaluation suite — the DSPy-style contract, Starz-owned.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct ModelProgram {
    pub program_id: String,
    pub purpose: String,
    pub input: Vec<SignatureField>,
    pub output: Vec<SignatureField>,
    pub allowed_models: Vec<String>,
    pub tools: Vec<String>,
    pub risk_level: String, // low | medium | high
    pub fallback_program: Option<String>,
    pub evaluation_suite: Option<String>,
}

/// Native structured-output enforcement: parses a model's text output and
/// enforces the program signature — required fields present, correct
/// kinds, NO extra fields. A malformed/extra-field output is an error,
/// not a silent repair loop.
pub fn decode_structured(
    text: &str,
    signature: &[SignatureField],
) -> std::result::Result<serde_json::Value, String> {
    let value: serde_json::Value =
        serde_json::from_str(text).map_err(|e| format!("output is not valid JSON: {e}"))?;
    let obj = value.as_object().ok_or("output must be a JSON object")?;
    let mut out = serde_json::Map::new();
    for field in signature {
        match obj.get(&field.name) {
            None if field.required => {
                return Err(format!("missing required field '{}'", field.name));
            }
            None => {}
            Some(v) => {
                let ok = match field.kind {
                    FieldKind::String => v.is_string(),
                    FieldKind::Integer => v.is_i64() || v.is_u64(),
                    FieldKind::Number => v.is_number(),
                    FieldKind::Boolean => v.is_boolean(),
                    FieldKind::Object => v.is_object(),
                    FieldKind::Array => v.is_array(),
                };
                if !ok {
                    return Err(format!(
                        "field '{}' has wrong kind (expected {:?})",
                        field.name, field.kind
                    ));
                }
                out.insert(field.name.clone(), v.clone());
            }
        }
    }
    // Extra fields are rejected — the model must follow the contract.
    for key in obj.keys() {
        if !signature.iter().any(|f| f.name == *key) {
            return Err(format!(
                "unexpected field '{key}' — output must match the signature"
            ));
        }
    }
    Ok(serde_json::Value::Object(out))
}

/// A tiny program registry with two canonical programs (corrective-action
/// investigation + material-shortage resolution).
pub fn default_programs() -> Vec<ModelProgram> {
    vec![
        ModelProgram {
            program_id: "corrective_action.investigate".into(),
            purpose: "Investigate an abnormality: state the FACT, the gap, and a testable hypothesis — never a guessed root cause.".into(),
            input: vec![
                SignatureField { name: "condition_id".into(), kind: FieldKind::String, required: true, description: "operational condition id".into() },
                SignatureField { name: "observed_condition".into(), kind: FieldKind::String, required: true, description: "what was observed".into() },
            ],
            output: vec![
                SignatureField { name: "fact".into(), kind: FieldKind::String, required: true, description: "recorded fact, not inference".into() },
                SignatureField { name: "status".into(), kind: FieldKind::String, required: true, description: "EpistemicStatus".into() },
                SignatureField { name: "gap_hypothesis".into(), kind: FieldKind::String, required: false, description: "testable hypothesis if any".into() },
            ],
            allowed_models: vec!["glm-5.3".into(), "qwen3.5".into()],
            tools: vec!["read_condition".into(), "read_events".into()],
            risk_level: "high".into(),
            fallback_program: Some("corrective_action.simple".into()),
            evaluation_suite: Some("corrective_action_suite_v1".into()),
        },
        ModelProgram {
            program_id: "material_shortage.resolve".into(),
            purpose: "Resolve a material shortage: evidence first, action second.".into(),
            input: vec![
                SignatureField { name: "sku".into(), kind: FieldKind::String, required: true, description: "material sku".into() },
            ],
            output: vec![
                SignatureField { name: "evidence".into(), kind: FieldKind::String, required: true, description: "the evidence (qty, last sync)".into() },
                SignatureField { name: "action".into(), kind: FieldKind::String, required: true, description: "the recommended action".into() },
            ],
            allowed_models: vec!["functiongemma".into(), "ministral".into()],
            tools: vec!["read_inventory".into(), "read_purchase_orders".into()],
            risk_level: "medium".into(),
            fallback_program: None,
            evaluation_suite: None,
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    fn corrective_action_signature() -> Vec<SignatureField> {
        default_programs()
            .into_iter()
            .find(|p| p.program_id == "corrective_action.investigate")
            .unwrap()
            .output
    }

    #[test]
    fn decode_structured_accepts_valid_output() {
        let ok = decode_structured(
            r#"{"fact": "loss event recorded at 14:02", "status": "recorded_fact"}"#,
            &corrective_action_signature(),
        );
        assert!(ok.is_ok());
        assert_eq!(ok.unwrap()["fact"], "loss event recorded at 14:02");
    }

    #[test]
    fn decode_structured_rejects_missing_required_field() {
        let err = decode_structured(
            r#"{"status": "recorded_fact"}"#,
            &corrective_action_signature(),
        )
        .unwrap_err();
        assert!(err.contains("missing required field 'fact'"));
    }

    #[test]
    fn decode_structured_rejects_extra_field() {
        let err = decode_structured(
            r#"{"fact": "x", "status": "recorded_fact", "root_cause": "guessed"}"#,
            &corrective_action_signature(),
        )
        .unwrap_err();
        assert!(err.contains("unexpected field 'root_cause'"));
    }

    #[test]
    fn decode_structured_rejects_wrong_kind_field() {
        let err = decode_structured(
            r#"{"fact": 42, "status": "recorded_fact"}"#,
            &corrective_action_signature(),
        )
        .unwrap_err();
        assert!(err.contains("field 'fact' has wrong kind"));
    }

    #[test]
    fn epistemic_status_serializes_as_snake_case() {
        assert_eq!(
            serde_json::to_string(&EpistemicStatus::RecordedFact).unwrap(),
            "\"recorded_fact\""
        );
        assert_eq!(
            serde_json::to_string(&EpistemicStatus::DerivedFact).unwrap(),
            "\"derived_fact\""
        );
        assert_eq!(
            serde_json::to_string(&EpistemicStatus::Inference).unwrap(),
            "\"inference\""
        );
        assert_eq!(
            serde_json::to_string(&EpistemicStatus::Hypothesis).unwrap(),
            "\"hypothesis\""
        );
    }
}
