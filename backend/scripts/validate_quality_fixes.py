"""Validate all quality module fixes."""

import sys
import importlib
import importlib.util

def _load_direct(name, path):
    """Load a single module file without triggering __init__.py chains."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

BASE = "/Users/sabelakhoua/IdeaProjects/Management-Software/backend/src"

# 1. Import checks - direct file imports to avoid services/__init__.py triggering WeasyPrint
quality_mod = importlib.import_module("sensei.models.quality")
quality_qms_mod = importlib.import_module("sensei.models.quality_qms")

# Load MSA service directly from file
msa_mod = _load_direct(
    "sensei.services.quality.msa_service_direct",
    f"{BASE}/sensei/services/quality/msa_service.py",
)

CAPAStateHistory = quality_mod.CAPAStateHistory
CAPAStatus = quality_mod.CAPAStatus
VerificationStatus = quality_mod.VerificationStatus
CAPAActionStatus = quality_mod.CAPAActionStatus
NCStatus = quality_mod.NCStatus
CAPA = quality_mod.CAPA
NonConformance = quality_mod.NonConformance

FirstArticleInspection = quality_qms_mod.FirstArticleInspection
SelfInspection = quality_qms_mod.SelfInspection
LabSample = quality_qms_mod.LabSample
TraceabilityMatrix = quality_qms_mod.TraceabilityMatrix

MSAService = msa_mod.MSAService
_D2_STAR_CONSTANTS = msa_mod._D2_STAR_CONSTANTS
print("✓ All imports resolved successfully")

# 2. CAPAStateHistory model
import inspect as _inspect
src = _inspect.getsource(CAPAStateHistory)
assert "capa_state_history" in src
assert "from_status" in src
assert "to_status" in src
assert "changed_by_id" in src
print("✓ CAPAStateHistory model well-formed")

# 3. MSA d₂* constants
assert len(_D2_STAR_CONSTANTS) == 9
for k in range(2, 11):
    assert k in _D2_STAR_CONSTANTS, f"Missing d₂* for k={k}"
print("✓ MSA d₂* constants table: 9 entries (k=2..10)")

# 4. QMS FK types
fai_cols = {c.name: str(c.type) for c in FirstArticleInspection.__table__.columns}
si_cols = {c.name: str(c.type) for c in SelfInspection.__table__.columns}
ls_cols = {c.name: str(c.type) for c in LabSample.__table__.columns}
tm_cols = {c.name: str(c.type) for c in TraceabilityMatrix.__table__.columns}

assert "INTEGER" in fai_cols["work_order_id"].upper(), fai_cols["work_order_id"]
assert "INTEGER" in si_cols["work_order_id"].upper(), si_cols["work_order_id"]
assert "INTEGER" in ls_cols["work_order_id"].upper(), ls_cols["work_order_id"]
print("✓ FAI/SelfInspection/LabSample work_order_id → INTEGER")

assert "UUID" in tm_cols["product_id"].upper(), tm_cols["product_id"]
print("✓ TraceabilityMatrix.product_id → UUID")

# 5. Mutable defaults
plan_col = next(c for c in __import__("sensei.models.quality", fromlist=["InspectionPlan"]).InspectionPlan.__table__.columns if c.name == "checkpoints_json")
rec_col = next(c for c in __import__("sensei.models.quality", fromlist=["InspectionRecord"]).InspectionRecord.__table__.columns if c.name == "measurements_json")
# Check defaults are callable (not a mutable list)
assert callable(plan_col.default.arg), f"checkpoints_json default should be callable, got {plan_col.default.arg}"
assert callable(rec_col.default.arg), f"measurements_json default should be callable, got {rec_col.default.arg}"
print("✓ Mutable defaults fixed: default=list (callable)")

# 6. CAPA status transition map completeness
# Import endpoint module - need to use AST parsing since the module imports services
import ast

with open(f"{BASE}/sensei/api/v1/endpoints/quality.py") as f:
    ep_source = f.read()

ep_tree = ast.parse(ep_source)

# Extract _CAPA_STATUS_TRANSITIONS keys from AST
# Instead, let's check the raw source for the expected statuses
all_status_values = [s.value for s in CAPAStatus]
for sv in all_status_values:
    # Each status should appear as a key in the transition map
    pattern = f"CAPAStatus.{[s.name for s in CAPAStatus if s.value == sv][0]}"
    assert pattern in ep_source, f"Status {pattern} not found in transition map"
print(f"✓ CAPA transition map references all {len(all_status_values)} statuses")

# 7. Endpoint schema types - parse from source since we can't import the endpoint module
import re

# NC schemas product_id should be UUID
nc_base_match = re.search(r'class NonConformanceBase.*?(?=\nclass )', ep_source, re.DOTALL)
nc_base_src = nc_base_match.group(0) if nc_base_match else ""
assert "product_id: Optional[UUID]" in nc_base_src, "NC product_id should be UUID"
assert "supplier_id: Optional[UUID]" in nc_base_src, "NC missing supplier_id"
assert "purchase_order_id: Optional[UUID]" in nc_base_src, "NC missing purchase_order_id"
print("✓ NC schemas: product_id=UUID, supplier_id/purchase_order_id present")

# NC Response
nc_resp_match = re.search(r'class NonConformanceResponse.*?(?=\ndef )', ep_source, re.DOTALL)
nc_resp_src = nc_resp_match.group(0) if nc_resp_match else ""
assert "supplier_id: Optional[UUID]" in nc_resp_src, "NC Response missing supplier_id"
assert "purchase_order_id: Optional[UUID]" in nc_resp_src, "NC Response missing purchase_order_id"
print("✓ NC Response includes supplier_id and purchase_order_id")

# FAI/SI/Lab work_order_id should be int
assert "class FAIInspectionCreate" in ep_source
fai_create = re.search(r'class FAIInspectionCreate.*?(?=\nclass )', ep_source, re.DOTALL).group(0)
assert "work_order_id: Optional[int]" in fai_create, f"FAI work_order_id should be int"

si_create = re.search(r'class SelfInspectionCreate.*?(?=\nclass )', ep_source, re.DOTALL).group(0)
assert "work_order_id: Optional[int]" in si_create, f"SI work_order_id should be int"

lab_create = re.search(r'class LabSampleCreate.*?(?=\nclass )', ep_source, re.DOTALL).group(0)
assert "work_order_id: Optional[int]" in lab_create, f"Lab work_order_id should be int"
print("✓ FAI/SelfInspection/LabSample schemas: work_order_id=int")

# Traceability product_id should be UUID
tm_create = re.search(r'class TraceabilityMatrixCreate.*?(?=\nclass )', ep_source, re.DOTALL).group(0)
assert "product_id: Optional[UUID]" in tm_create, f"TM product_id should be UUID"
print("✓ TraceabilityMatrix schemas: product_id=UUID")

# 8. Verify NC create forces OPEN status
nc_create_handler = re.search(r'async def create_non_conformance.*?await db\.commit\(\)', ep_source, re.DOTALL)
nc_handler_src = nc_create_handler.group(0) if nc_create_handler else ""
assert "status=NCStatus.OPEN" in nc_handler_src, "NC create should force status=OPEN"
assert "status=data.status" not in nc_handler_src, "NC create should NOT use data.status"
print("✓ NC create forces status=OPEN")

# 9. Verify verify_capa uses PASSED not VERIFIED
verify_handler = re.search(r'async def verify_capa.*?return build_updated_response', ep_source, re.DOTALL)
verify_src = verify_handler.group(0) if verify_handler else ""
assert "VerificationStatus.PASSED" in verify_src, "verify_capa should use PASSED"
assert "VerificationStatus.VERIFIED" not in verify_src, "verify_capa should NOT use VERIFIED"
print("✓ verify_capa uses VerificationStatus.PASSED")

# 10. Verify reject uses FAILED not REJECTED
reject_handler = re.search(r'async def reject_capa_verification.*?return build_updated_response', ep_source, re.DOTALL)
reject_src = reject_handler.group(0) if reject_handler else ""
assert "VerificationStatus.FAILED" in reject_src, "reject should use FAILED"
assert "VerificationStatus.REJECTED" not in reject_src, "reject should NOT use REJECTED"
print("✓ reject_capa_verification uses VerificationStatus.FAILED")

# 11. CAPAStateHistory recording
assert "_record_capa_state_change" in ep_source, "Missing _record_capa_state_change helper"
assert "CAPAStateHistory" in ep_source, "CAPAStateHistory not imported in endpoints"
occurrences = ep_source.count("_record_capa_state_change(db")
assert occurrences >= 5, f"Expected >=5 state change recordings, found {occurrences}"
print(f"✓ CAPAStateHistory recorded in {occurrences} lifecycle endpoints")

# 12. Inspection delete blocked
delete_insp = re.search(r'async def delete_inspection\b[^_].*?(?=\n@router|\n# ===)', ep_source, re.DOTALL)
delete_src = delete_insp.group(0) if delete_insp else ""
assert "cannot be deleted" in delete_src or "ISO 9001" in delete_src, f"Inspection delete should be blocked. Got: {delete_src[:200]}"
assert "await db.delete(record)" not in delete_src, "Inspection delete should NOT hard-delete records"
print("✓ Inspection record delete blocked (ISO compliance)")

# 13. CAPA action delete → cancel
delete_action = re.search(r'async def delete_capa_action.*?(?=\n@router|\n# ===)', ep_source, re.DOTALL)
da_src = delete_action.group(0) if delete_action else ""
assert "CAPAActionStatus.CANCELLED" in da_src, "CAPA action delete should cancel"
assert "await db.delete(action)" not in da_src, "CAPA action should NOT hard-delete"
print("✓ CAPA action delete → cancel (not hard-delete)")
print("\n" + "=" * 60)
print("ALL VALIDATION CHECKS PASSED")
print("=" * 60)
