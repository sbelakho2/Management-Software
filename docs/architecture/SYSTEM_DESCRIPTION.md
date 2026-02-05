# Sensei OS - System Description

## Overview

Sensei OS is a comprehensive Manufacturing Operating System designed to integrate all aspects of a modern factory, from sales and engineering to production and quality. It leverages advanced AI/ML to provide prescriptive insights and drive continuous improvement.

## Core Modules

### 1. Sales & Commercial
- **Quoting Helper (Stage-Gate Workflow)**: Accelerates RFQ → Quote from days to hours by splitting technical reviews across parallel engineering work packets (EE, ME, MfgE, Quality, Purchasing).
- **AI Quote Memory**: Domain-adapted embeddings for manufacturing quote analysis using ONNX-optimized local models.
- **Smart Ingestion**: Automated extraction of technical requirements (MPNs, quantities, PCB specs) from emails and PDF packages.
- **Deterministic Costing**: Rule-based costing engine utilizing active Rate Cards for material rollups and labor estimation.

### 2. Engineering & NPI (New Product Introduction)
- **Document Intelligence**: AI-powered extraction of metadata from engineering drawings and PDFs.
- **CTQ (Critical to Quality)**: Definition and tracking of critical parameters from design to delivery.
- **BOM Management**: Integrated bill of materials linked to inventory and production.

### 3. Production & Shop Floor (MES)
- **Work Order Orchestration**: Real-time management of production orders across stations.
- **Digital Shift Handover**: Structured SQDCP-based communication between shifts to ensure operational continuity.
- **Standard Work**: Digital work instructions with version control and operator sign-off.
- **Andon Board**: Instant visual signals for shop floor abnormalities.
- **Maintenance (TPM)**: Condition-based maintenance driven by sensor data and ML.

### 4. Quality Management (QMS)
- **Inspections**: Integrated quality gates at critical production steps.
- **NCR/CAPA**: Streamlined handling of non-conformances and corrective/preventive actions.
- **Visual AI**: Automated defect detection using computer vision at the station level.

### 5. Supply Chain & Logistics
- **Global Disruption Simulation**: ML-driven analysis of supply chain risks.
- **Supplier Portal**: Secure interface for suppliers to manage quotes and shipments.
- **Inventory Intelligence**: Real-time tracking with predictive reorder points.

### 6. Executive & Intelligence
- **Cognitive Obeya**: Digital "war room" with prescriptive metrics and Heijunka (leveling) advice.
- **The Sensei Pulse**: Site-wide, real-time announcement system for alignment on goals and critical status.
- **North Star Dashboard**: High-level metrics for executive decision-making.
- **NL2SQL Query Engine**: Natural language interface for querying enterprise data.

## Key Architectural Principles

### Data Lineage (The "Common Thread")
The system maintains a deterministic data genealogy across all modules. An `RFQ` evolves into a `Quote`, which triggers a `Work Order`, which might result in an `NCR`. This lineage is traceable via the `CommonThreadService`.

### Local-First AI
Inference happens as close to the data source as possible. Visual quality checks use ONNX models running on the shop floor station, ensuring high reliability and low latency.

### Context-Aware Intelligence
The `ContextBus` ensures that AI insights are always relevant to the current user's role and task.

### Multi-Persona UX
Sensei OS provides tailored experiences for over 14 manufacturing personas, from the CEO and GM to the Operator and Maintenance Technician.
