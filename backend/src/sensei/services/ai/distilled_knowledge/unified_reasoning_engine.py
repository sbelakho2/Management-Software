"""
Unified Distilled Reasoning Engine

Combines all language-specific knowledge modules into a single
reasoning interface for Sensei OS.
"""

from typing import Dict, List, Any, Optional, cast
import logging

logger = logging.getLogger(__name__)


class UnifiedDistilledReasoning:
    """
    Unified reasoning engine that combines all language-specific
    TPS/Lean knowledge modules.
    
    Usage:
        engine = UnifiedDistilledReasoning()
        results = engine.reason("How to reduce inventory waste?", language="en")
    """
    
    SUPPORTED_LANGUAGES = ["en", "es", "fr", "de", "ar"]
    
    def __init__(self):
        self._modules = {}
        self._load_modules()
    
    def _load_modules(self):
        """Load all language modules."""
        try:
            from .tps_lean_knowledge_en import TPSLeanKnowledgeEN
            self._modules["en"] = TPSLeanKnowledgeEN
        except ImportError:
            logger.warning("EN knowledge module not available")
        
        try:
            from .tps_lean_knowledge_es import TPSLeanKnowledgeES
            self._modules["es"] = TPSLeanKnowledgeES
        except ImportError:
            logger.warning("ES knowledge module not available")
        
        try:
            from .tps_lean_knowledge_fr import TPSLeanKnowledgeFR
            self._modules["fr"] = TPSLeanKnowledgeFR
        except ImportError:
            logger.warning("FR knowledge module not available")
        
        try:
            from .tps_lean_knowledge_de import TPSLeanKnowledgeDE
            self._modules["de"] = TPSLeanKnowledgeDE
        except ImportError:
            logger.warning("DE knowledge module not available")
        
        try:
            from .tps_lean_knowledge_ar import TPSLeanKnowledgeAR
            self._modules["ar"] = TPSLeanKnowledgeAR
        except ImportError:
            logger.warning("AR knowledge module not available")
        
        logger.info(f"Loaded {len(self._modules)} language modules")
    
    def reason(
        self,
        query: str,
        language: str = "en",
        max_results: int = 5,
        domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform reasoning on a query in the specified language.
        
        Args:
            query: The reasoning query
            language: Language code (en, es, fr, de, ar)
            max_results: Maximum results to return
            domain: Optional domain filter
            
        Returns:
            List of relevant principles with confidence scores
        """
        if language not in self._modules:
            logger.warning(f"Language {language} not available, falling back to EN")
            language = "en"
        
        if language not in self._modules:
            return []
        
        module = self._modules[language]
        
        if domain:
            principles = module.get_by_domain(domain)
            # Manually reason over filtered principles
            results = self._reason_over_principles(query, principles, max_results)
        else:
            results = module.reason(query, max_results)
        
        return results
    
    def _reason_over_principles(
        self,
        query: str,
        principles: List[Dict],
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Reason over a filtered set of principles."""
        query_words = set(query.lower().split())
        results = []
        
        for principle in principles:
            principle_words = set(principle["principle"].lower().split())
            keyword_words = set(kw.lower() for kw in principle.get("keywords", []))
            
            p_overlap = len(query_words & principle_words) / max(1, len(query_words))
            k_overlap = len(query_words & keyword_words) / max(1, len(keyword_words)) if keyword_words else 0
            
            score = (p_overlap * 0.7) + (k_overlap * 0.3)
            
            if score > 0.1:
                results.append({
                    "principle": principle,
                    "relevance_score": score,
                    "match_type": "semantic" if p_overlap > k_overlap else "keyword"
                })
        
        results.sort(key=lambda x: cast(float, x["relevance_score"]), reverse=True)
        return results[:max_results]
    
    def get_countermeasures(
        self,
        waste_category: str,
        language: str = "en"
    ) -> List[str]:
        """Get countermeasures for a specific waste category."""
        if language not in self._modules:
            language = "en"
        
        if language not in self._modules:
            return []
        
        module = self._modules[language]
        principles = module.get_by_waste_category(waste_category)
        
        countermeasures = []
        for p in principles:
            countermeasures.extend(p.get("countermeasures", []))
        
        return list(set(countermeasures))[:10]
    
    def get_a3_guidance(
        self,
        phase: str,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """Get guidance for an A3 phase."""
        if language not in self._modules:
            language = "en"
        
        if language not in self._modules:
            return []
        
        module = self._modules[language]
        return module.get_by_a3_phase(phase)
    
    def get_expert_traces(
        self,
        language: str = "en"
    ) -> List[Dict[str, Any]]:
        """
        Get expert traces in format compatible with SenseiReasoningEngine.
        
        Returns traces formatted for load_seeded_knowledge().
        """
        if language not in self._modules:
            language = "en"
        
        if language not in self._modules:
            return []
        
        module = self._modules[language]
        traces = []
        
        for p in module.get_principles():
            trace = {
                "findings": {
                    "distilled_principle": p["principle"],
                    "source_book": p["source_books"][0] if p["source_books"] else "Distilled Knowledge",
                    "domain": p["domain"],
                    "keywords": p["keywords"]
                },
                "recommendations": p["countermeasures"],
                "confidence": 0.85
            }
            traces.append(trace)
        
        return traces
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded knowledge."""
        stats: Dict[str, Any] = {
            "languages_loaded": list(self._modules.keys()),
            "total_principles": 0,
            "by_language": {},
            "by_domain": {}
        }
        
        for lang, module in self._modules.items():
            principles = module.get_principles()
            count = len(principles)
            stats["by_language"][lang] = count
            stats["total_principles"] += count
            
            # Domain breakdown
            for p in principles:
                domain = p.get("domain", "general")
                if domain not in stats["by_domain"]:
                    stats["by_domain"][domain] = 0
                stats["by_domain"][domain] += 1
        
        return stats
