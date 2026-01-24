# Estimator Starter Guide

## Sensei OS - Estimator Complete Reference

---

## 1. Welcome & Role Overview

As an **Estimator**, you are the architect of the quote. You orchestrate the collection of engineering data and build deterministic cost models that ensure profitability and competitiveness.

### Key Responsibilities:
- Orchestrate the **Quoting Helper** Stage-Gate workflow.
- Validate engineering inputs from all disciplines.
- Apply **Rate Cards** for labor and NRE costing.
- Perform **Margin Analysis** and handle exception approvals.
- Manage the **NPI Handoff** once a quote is won.

---

## 2. The Quoting Workbench

The Workbench is your primary tool for managing high-complexity industrial RFQs.

### Workflow:
1. **Intake (Stage 0)**: Ingest RFQ packages. Use **Smart Ingestion** to auto-extract BOMs and technical specs.
2. **Parallel Engineering (Stage 2)**: Initialize work packets. Monitor progress as EE, ME, and MfgE contribute their findings.
3. **Cost Engine (Stage 3)**: Consolidated material rollups and labor estimates. Select the active **Rate Card** to apply standard shop floor rates.
4. **Approval**: Submit quotes for GM/CEO approval if they fall outside standard margin floors.
5. **NPI Handoff**: Once accepted, click **Convert to NPI** to bridge the gap to production.

---

## 3. AI Assistance for Estimators

### AI Quote Memory
When starting a new quote, use the **Quote Memory** tab. Sensei OS uses semantic search to find similar historical jobs and pulls:
- Past labor assumptions.
- Actual vs. Quoted yield rates.
- Proven supplier choices.

### Interactive Quote Explorer
Use the interactive toggles to simulate price impacts:
- **Quantity Ladder**: See cost breaks at 100, 500, 1000 units.
- **Jidoka Test Levels**: Toggle AOI, X-Ray, and FCT to see the impact on labor and NRE.

---

## 4. Standard Work for Estimating

### Definition of Ready (DoR) for Quoting:
- [ ] BOM normalized with MPNs.
- [ ] Centroid data provided (for PCBAs).
- [ ] Drawings and fab notes attached.
- [ ] Quantity ladder defined.

### Definition of Done (DoD) for Quoted:
- [ ] All engineering gates signed off.
- [ ] Risks (Andon) acknowledged or mitigated.
- [ ] Margin passes floor or has override.
- [ ] Quote PDF generated and versioned.

---

*Last Updated: January 2026*
*Sensei OS Version: 3.0*
*Document Owner: Sales & Engineering*
