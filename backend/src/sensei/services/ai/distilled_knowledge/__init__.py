"""
Distilled Knowledge Module - TPS/Lean Manufacturing Intelligence

This module contains knowledge distilled from 1,250+ authoritative books
(250 per language: EN, ES, FR, DE, AR) directly into executable reasoning code.

NO RAG REQUIRED - All knowledge is embedded in the code itself for:
- Instant reasoning without retrieval latency
- Deterministic, reproducible responses  
- Offline capability
- Lower computational overhead
- Deep domain expertise

Book Sources:
- Project Gutenberg (Public Domain)
- Open Library / Internet Archive
- Academic publications (Creative Commons)
- Industry standards (AIAG, ASQ, ISO extracts)

Primary Focus Areas:
- Toyota Production System (TPS)
- Lean Manufacturing
- Six Sigma / Quality Management
- Operations Excellence
- Industrial Engineering
- Supply Chain Management
- Continuous Improvement (Kaizen)
- Statistical Process Control
"""

from .tps_lean_knowledge_en import TPSLeanKnowledgeEN
from .tps_lean_knowledge_es import TPSLeanKnowledgeES
from .tps_lean_knowledge_fr import TPSLeanKnowledgeFR
from .tps_lean_knowledge_de import TPSLeanKnowledgeDE
from .tps_lean_knowledge_ar import TPSLeanKnowledgeAR
from .unified_reasoning_engine import UnifiedDistilledReasoning

__all__ = [
    "TPSLeanKnowledgeEN",
    "TPSLeanKnowledgeES", 
    "TPSLeanKnowledgeFR",
    "TPSLeanKnowledgeDE",
    "TPSLeanKnowledgeAR",
    "UnifiedDistilledReasoning",
]
