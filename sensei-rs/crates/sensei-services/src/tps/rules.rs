//! TPS hard rules (item 126): deterministic invariants that NO model and
//! NO route can override. Each rule is a pure check over domain state;
//! the routes call them before executing the guarded transition.

use uuid::Uuid;

/// The set of hard TPS rules and their outcomes.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RuleViolation {
    /// A critical-safety Andon keeps the line stopped until a
    /// RestartAuthorization exists.
    CriticalSafetyAndonNeedsRestartAuthorization,
    /// A material/quality hold blocks the affected lot from shipping.
    LotOnHoldCannotShip,
    /// An effective/approved controlled document cannot be mutated.
    EffectiveDocumentImmutable,
    /// A capability claim requires an acceptable measurement system.
    CapabilityRequiresValidMsa,
    /// An inventory transfer must balance (Σ deltas = 0).
    TransferMustBalance,
    /// Production completion must reconcile produced + scrap + short close.
    CompletionRequiresReconciliation,
}

impl RuleViolation {
    pub fn message(&self) -> &'static str {
        match self {
            RuleViolation::CriticalSafetyAndonNeedsRestartAuthorization => {
                "HARD RULE: a critical-safety Andon keeps the line stopped until an authorized \
                 restart exists"
            }
            RuleViolation::LotOnHoldCannotShip => {
                "HARD RULE: material on a quality hold cannot ship"
            }
            RuleViolation::EffectiveDocumentImmutable => {
                "HARD RULE: effective/approved controlled documents are immutable"
            }
            RuleViolation::CapabilityRequiresValidMsa => {
                "HARD RULE: a capability result is invalid when the required MSA state is not \
                 acceptable"
            }
            RuleViolation::TransferMustBalance => {
                "HARD RULE: an inventory transfer must balance (Σ location deltas = 0)"
            }
            RuleViolation::CompletionRequiresReconciliation => {
                "HARD RULE: production completion requires quantity reconciliation"
            }
        }
    }
}

/// Check whether a critical-safety Andon may be resolved/restarted:
/// a RestartAuthorization (issued by an authorized responder) must exist.
pub fn check_safety_restart(
    is_critical_safety: bool,
    has_restart_authorization: bool,
) -> Result<(), RuleViolation> {
    if is_critical_safety && !has_restart_authorization {
        Err(RuleViolation::CriticalSafetyAndonNeedsRestartAuthorization)
    } else {
        Ok(())
    }
}

/// Check whether a lot on hold may ship.
pub fn check_lot_release(on_hold: bool, has_release_decision: bool) -> Result<(), RuleViolation> {
    if on_hold && !has_release_decision {
        Err(RuleViolation::LotOnHoldCannotShip)
    } else {
        Ok(())
    }
}

/// An inventory transfer must balance: the sum of all location deltas is
/// zero (double-entry-like ledger invariant).
pub fn check_transfer_balance(deltas: &[(Uuid, i64)]) -> Result<(), RuleViolation> {
    if deltas.iter().map(|(_, d)| d).sum::<i64>() == 0 {
        Ok(())
    } else {
        Err(RuleViolation::TransferMustBalance)
    }
}

/// A capability claim requires an acceptable measurement system.
pub fn check_capability_msa(msa_acceptable: bool) -> Result<(), RuleViolation> {
    if msa_acceptable {
        Ok(())
    } else {
        Err(RuleViolation::CapabilityRequiresValidMsa)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn safety_restart_requires_authorization() {
        assert_eq!(
            check_safety_restart(true, false),
            Err(RuleViolation::CriticalSafetyAndonNeedsRestartAuthorization)
        );
        assert!(check_safety_restart(true, true).is_ok());
        assert!(check_safety_restart(false, false).is_ok());
    }

    #[test]
    fn holds_block_shipping() {
        assert_eq!(
            check_lot_release(true, false),
            Err(RuleViolation::LotOnHoldCannotShip)
        );
        assert!(check_lot_release(true, true).is_ok());
    }

    #[test]
    fn transfers_must_balance() {
        let a = Uuid::new_v4();
        let b = Uuid::new_v4();
        assert!(check_transfer_balance(&[(a, -50), (b, 50)]).is_ok());
        assert_eq!(
            check_transfer_balance(&[(a, -50), (b, 40)]),
            Err(RuleViolation::TransferMustBalance)
        );
    }

    #[test]
    fn capability_requires_msa() {
        assert!(check_capability_msa(true).is_ok());
        assert_eq!(
            check_capability_msa(false),
            Err(RuleViolation::CapabilityRequiresValidMsa)
        );
    }
}
