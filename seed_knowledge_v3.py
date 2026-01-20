#!/usr/bin/env python3
"""
Knowledge Seeder v3 - TPS & Recency Weighted
=============================================

Processes downloaded books and seeds Sensei OS with prioritization:
1. TPS/Lean content gets 3x weight
2. Newer books (2000+) get 2x weight  
3. Combines both: new TPS content gets 6x weight

Output:
- Expert traces with weighted confidence scores
- Knowledge chunks for RAG
- Distilled knowledge Python modules
"""

import json
import re
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field, asdict

# ============================================================================
# CONFIGURATION
# ============================================================================

BOOKS_DIR = Path("downloaded_books/txt")
OUTPUT_DIR = Path("seeded_knowledge")
DISTILLED_DIR = Path("backend/src/sensei/services/ai/distilled_knowledge")

# Weighting factors
TPS_WEIGHT = 3.0      # TPS/Lean content gets 3x
RECENCY_WEIGHT = 2.0  # Books from 2000+ get 2x
COMBINED_WEIGHT = TPS_WEIGHT * RECENCY_WEIGHT  # New TPS = 6x

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Domain patterns - TPS is most comprehensive
DOMAIN_PATTERNS = {
    "tps_lean": [
        r"\btoyota\b", r"\blean\b", r"\bkaizen\b", r"\bkanban\b",
        r"\bjidoka\b", r"\bheijunka\b", r"\bgemba\b", r"\bmuda\b",
        r"\bcontinuous improvement\b", r"\bvalue stream\b",
        r"\bjust.in.time\b", r"\bpull system\b", r"\bstandardized work\b",
        r"\btakt time\b", r"\bpoka.yoke\b", r"\b5s\b", r"\btpm\b",
        r"\btotal productive maintenance\b", r"\bhoshin\b", r"\ba3\b",
        r"\bpdca\b", r"\bflow\b", r"\bwaste\b", r"\boverproduction\b",
        r"\bsingle.piece\b", r"\bcellular\b", r"\bvisual management\b",
        r"\broot cause\b", r"\bprocess improvement\b"
    ],
    "quality": [
        r"\bquality\b", r"\bdefect\b", r"\binspection\b", r"\bcontrol chart\b",
        r"\bspc\b", r"\bstatistical process\b", r"\bdeming\b", r"\bjuran\b",
        r"\bsix sigma\b", r"\biso 9001\b", r"\baudit\b", r"\bfmea\b",
        r"\bprocess capability\b", r"\bcpk\b", r"\bzero defects\b"
    ],
    "psychology": [
        r"\bpsycholog\b", r"\bbehavior\b", r"\bmotivation\b", r"\bleadership\b",
        r"\bcognitive\b", r"\bdecision.making\b", r"\bteam\b", r"\bculture\b",
        r"\bengagement\b", r"\bempowerment\b", r"\bchange management\b"
    ],
    "operations": [
        r"\boperations\b", r"\bproduction\b", r"\bmanufacturing\b",
        r"\bcapacity\b", r"\bscheduling\b", r"\bplanning\b", r"\bfactory\b"
    ],
    "logistics": [
        r"\blogistics\b", r"\bsupply chain\b", r"\binventory\b", r"\bwarehouse\b",
        r"\btransportation\b", r"\bprocurement\b", r"\bmrp\b", r"\berp\b"
    ],
    "finance": [
        r"\baccounting\b", r"\bcost\b", r"\bbudget\b", r"\bfinance\b",
        r"\bvariance\b", r"\broi\b", r"\bthroughput accounting\b"
    ],
    "engineering": [
        r"\bengineering\b", r"\bmaintenance\b", r"\breliability\b",
        r"\bpredictive\b", r"\bautomation\b", r"\bequipment\b"
    ]
}

# Principle extraction patterns
PRINCIPLE_PATTERNS = [
    r"(?:principle|rule|law|key insight)[\s:]+([^.]{20,200}\.)",
    r"(?:important|fundamental|essential)[\s:]+([^.]{20,200}\.)",
    r"\"([^\"]{30,200})\"",
    r"'([^']{30,200})'",
]

@dataclass
class ExpertTrace:
    id: str
    principle: str
    source_book: str
    source_author: str
    domain: str
    language: str
    year: int
    recommendations: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    confidence: float = 0.8
    weight: float = 1.0  # TPS + recency weight

@dataclass
class KnowledgeChunk:
    id: str
    content: str
    source_book: str
    source_author: str
    domain: str
    language: str
    year: int
    chunk_index: int
    word_count: int
    weight: float = 1.0

@dataclass
class DistilledPrinciple:
    id: str
    principle: str
    explanation: str
    domain: str
    keywords: List[str]
    waste_categories: List[str]
    a3_phases: List[str]
    countermeasures: List[str]
    source_books: List[str]
    weight: float = 1.0


class WeightedKnowledgeSeeder:
    """Process books with TPS and recency weighting."""
    
    def __init__(self):
        self.expert_traces: List[ExpertTrace] = []
        self.knowledge_chunks: List[KnowledgeChunk] = []
        self.distilled_principles: Dict[str, List[DistilledPrinciple]] = defaultdict(list)
        self.stats = {
            "books_processed": 0,
            "tps_books": 0,
            "recent_books": 0,
            "traces_extracted": 0,
            "chunks_created": 0,
            "by_language": defaultdict(int),
            "by_domain": defaultdict(int),
            "avg_weight": 0.0
        }
    
    def _clean_text(self, text: str) -> str:
        """Clean text content."""
        # Remove Gutenberg/IA headers
        text = re.sub(r'\*\*\*\s*START.*?\*\*\*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'\*\*\*\s*END.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'Internet Archive.*?(?=\n\n)', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _detect_language(self, filename: str, text: str) -> str:
        """Detect language from filename prefix or text."""
        # Check filename prefix (e.g., en_, es_, fr_)
        name = Path(filename).stem
        if name.startswith(('en_', 'es_', 'fr_', 'de_', 'ar_')):
            return name[:2]
        
        sample = text[:3000].lower()
        indicators = {
            "en": ["the ", " and ", " of ", " to ", " is "],
            "es": [" el ", " la ", " de ", " que ", " en "],
            "fr": [" le ", " la ", " de ", " et ", " les "],
            "de": [" der ", " die ", " und ", " ist ", " das "],
            "ar": ["ال", "من", "في", "على"]
        }
        
        scores = {lang: sum(sample.count(w) for w in words) 
                  for lang, words in indicators.items()}
        return max(scores, key=scores.get) if scores else "en"
    
    def _extract_year(self, filename: str) -> int:
        """Extract year from filename."""
        # Look for year pattern like _2015_ or _2015.txt
        match = re.search(r'_(\d{4})[\._]', filename)
        if match:
            year = int(match.group(1))
            if 1900 <= year <= 2030:
                return year
        
        # Look for year in filename
        match = re.search(r'(19|20)\d{2}', filename)
        if match:
            return int(match.group())
        
        return 2000  # Default
    
    def _classify_domain(self, text: str) -> Tuple[str, bool]:
        """Classify domain and check if TPS-related."""
        text_lower = text.lower()
        
        domain_scores = {}
        for domain, patterns in DOMAIN_PATTERNS.items():
            score = sum(len(re.findall(p, text_lower)) for p in patterns)
            domain_scores[domain] = score
        
        best_domain = max(domain_scores, key=domain_scores.get) if domain_scores else "general"
        is_tps = best_domain == "tps_lean" or domain_scores.get("tps_lean", 0) > 5
        
        return best_domain, is_tps
    
    def _calculate_weight(self, year: int, is_tps: bool) -> float:
        """Calculate weight based on TPS and recency."""
        weight = 1.0
        
        if is_tps:
            weight *= TPS_WEIGHT
        
        if year >= 2000:
            weight *= RECENCY_WEIGHT
        elif year >= 1990:
            weight *= 1.5
        
        return weight
    
    def _extract_metadata(self, filename: str) -> Tuple[str, str]:
        """Extract title and author from filename."""
        name = Path(filename).stem
        # Remove language prefix and ID
        parts = name.split('_', 2)
        if len(parts) > 2:
            title = parts[2].replace('_', ' ')
        else:
            title = name.replace('_', ' ')
        return title[:100], "Unknown"
    
    def _extract_principles(self, text: str, weight: float) -> List[str]:
        """Extract principle statements."""
        principles = []
        for pattern in PRINCIPLE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                principle = match.strip()
                if 20 < len(principle) < 300:
                    principles.append(principle)
        
        # TPS-specific patterns get extra extraction
        if weight >= TPS_WEIGHT:
            tps_patterns = [
                r"(?:eliminate|reduce|minimize)\s+(?:waste|muda)[^.]+\.",
                r"(?:continuous|kaizen|improvement)\s+[^.]+\.",
                r"(?:standard|standardize|standardized)\s+work[^.]+\.",
            ]
            for pattern in tps_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                principles.extend(m.strip() for m in matches if 20 < len(m) < 300)
        
        return list(set(principles))[:100]
    
    def _extract_keywords(self, text: str, domain: str) -> List[str]:
        """Extract keywords relevant to domain."""
        text_lower = text.lower()
        keywords = []
        
        patterns = DOMAIN_PATTERNS.get(domain, []) + DOMAIN_PATTERNS.get("tps_lean", [])
        for pattern in patterns:
            matches = re.findall(pattern, text_lower)
            keywords.extend(matches)
        
        from collections import Counter
        return [kw for kw, _ in Counter(keywords).most_common(15)]
    
    def _infer_recommendations(self, principle: str, domain: str, is_tps: bool) -> List[str]:
        """Generate recommendations based on principle."""
        recs = []
        pl = principle.lower()
        
        if is_tps or domain == "tps_lean":
            if "waste" in pl or "muda" in pl:
                recs.extend([
                    "Conduct gemba walk to identify waste",
                    "Map value stream to visualize waste",
                    "Apply 5 Whys to find root cause"
                ])
            if "standard" in pl:
                recs.extend([
                    "Document current best practice",
                    "Create visual work instructions",
                    "Train team on standardized procedures"
                ])
            if "improve" in pl or "kaizen" in pl:
                recs.extend([
                    "Start kaizen event to address issue",
                    "Use PDCA cycle for improvement",
                    "Involve frontline workers in solutions"
                ])
            if "flow" in pl:
                recs.extend([
                    "Implement one-piece flow where possible",
                    "Balance line to takt time",
                    "Remove bottlenecks"
                ])
        
        if domain == "quality":
            recs.extend([
                "Implement source inspection",
                "Use statistical process control",
                "Apply poka-yoke error proofing"
            ])
        
        if not recs:
            recs = ["Analyze current situation", "Gather data before acting"]
        
        return recs[:5]
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), CHUNK_SIZE - CHUNK_OVERLAP):
            chunk_words = words[i:i + CHUNK_SIZE]
            if len(chunk_words) >= 50:
                chunks.append(" ".join(chunk_words))
        return chunks
    
    def _generate_id(self, *args) -> str:
        """Generate deterministic ID."""
        content = "_".join(str(a) for a in args)
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def process_book(self, filepath: Path) -> bool:
        """Process a single book with weighting."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
            
            if len(raw_text) < 1000:
                return False
            
            text = self._clean_text(raw_text)
            filename = filepath.name
            
            # Extract metadata
            title, author = self._extract_metadata(filename)
            language = self._detect_language(filename, text)
            year = self._extract_year(filename)
            domain, is_tps = self._classify_domain(text)
            weight = self._calculate_weight(year, is_tps)
            
            # Update stats
            self.stats["books_processed"] += 1
            self.stats["by_language"][language] += 1
            self.stats["by_domain"][domain] += 1
            if is_tps:
                self.stats["tps_books"] += 1
            if year >= 2000:
                self.stats["recent_books"] += 1
            
            # Extract principles with weighted confidence
            principles = self._extract_principles(text, weight)
            keywords = self._extract_keywords(text, domain)
            
            base_confidence = 0.7
            if is_tps:
                base_confidence += 0.15
            if year >= 2000:
                base_confidence += 0.1
            
            for i, principle in enumerate(principles):
                trace = ExpertTrace(
                    id=self._generate_id(filename, i),
                    principle=principle,
                    source_book=title,
                    source_author=author,
                    domain=domain,
                    language=language,
                    year=year,
                    recommendations=self._infer_recommendations(principle, domain, is_tps),
                    keywords=keywords[:7],
                    confidence=min(0.95, base_confidence),
                    weight=weight
                )
                self.expert_traces.append(trace)
                self.stats["traces_extracted"] += 1
            
            # Create weighted chunks
            chunks = self._chunk_text(text)
            for i, chunk_text in enumerate(chunks):
                chunk = KnowledgeChunk(
                    id=self._generate_id(filename, "chunk", i),
                    content=chunk_text,
                    source_book=title,
                    source_author=author,
                    domain=domain,
                    language=language,
                    year=year,
                    chunk_index=i,
                    word_count=len(chunk_text.split()),
                    weight=weight
                )
                self.knowledge_chunks.append(chunk)
                self.stats["chunks_created"] += 1
            
            return True
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return False
    
    def process_all_books(self):
        """Process all books with priority sorting."""
        print("=" * 70)
        print("PROCESSING BOOKS (TPS + RECENCY WEIGHTED)")
        print("=" * 70)
        
        if not BOOKS_DIR.exists():
            print(f"Books directory not found: {BOOKS_DIR}")
            return
        
        book_files = list(BOOKS_DIR.glob("*.txt"))
        print(f"Found {len(book_files)} book files")
        
        for i, filepath in enumerate(book_files, 1):
            self.process_book(filepath)
            if i % 50 == 0:
                print(f"  Processed {i}/{len(book_files)}...")
        
        # Calculate average weight
        if self.expert_traces:
            self.stats["avg_weight"] = sum(t.weight for t in self.expert_traces) / len(self.expert_traces)
        
        self._print_stats()
    
    def _print_stats(self):
        """Print processing statistics."""
        print(f"\nBooks processed: {self.stats['books_processed']}")
        print(f"  TPS books: {self.stats['tps_books']} ({100*self.stats['tps_books']/max(1,self.stats['books_processed']):.1f}%)")
        print(f"  Recent (2000+): {self.stats['recent_books']} ({100*self.stats['recent_books']/max(1,self.stats['books_processed']):.1f}%)")
        print(f"Expert traces: {self.stats['traces_extracted']}")
        print(f"Knowledge chunks: {self.stats['chunks_created']}")
        print(f"Average weight: {self.stats['avg_weight']:.2f}")
        
        print("\nBy Language:")
        for lang, count in sorted(self.stats["by_language"].items(), key=lambda x: -x[1]):
            print(f"  {lang.upper()}: {count}")
        
        print("\nBy Domain:")
        for domain, count in sorted(self.stats["by_domain"].items(), key=lambda x: -x[1]):
            print(f"  {domain}: {count}")
    
    def save_outputs(self):
        """Save weighted knowledge files."""
        print("\n" + "=" * 70)
        print("SAVING WEIGHTED KNOWLEDGE")
        print("=" * 70)
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Sort traces by weight (TPS + recent first)
        sorted_traces = sorted(self.expert_traces, key=lambda t: -t.weight)
        
        # Save expert traces
        traces_file = OUTPUT_DIR / "expert_traces.json"
        traces_data = [
            {
                "id": t.id,
                "findings": {
                    "distilled_principle": t.principle,
                    "source_book": t.source_book,
                    "domain": t.domain,
                    "keywords": t.keywords,
                    "year": t.year
                },
                "recommendations": t.recommendations,
                "confidence": t.confidence,
                "weight": t.weight,
                "language": t.language
            }
            for t in sorted_traces
        ]
        with open(traces_file, "w", encoding="utf-8") as f:
            json.dump(traces_data, f, indent=2, ensure_ascii=False)
        print(f"  Saved {len(traces_data)} expert traces")
        
        # Sort chunks by weight
        sorted_chunks = sorted(self.knowledge_chunks, key=lambda c: -c.weight)
        
        chunks_file = OUTPUT_DIR / "knowledge_chunks.json"
        chunks_data = [asdict(c) for c in sorted_chunks]
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        print(f"  Saved {len(chunks_data)} knowledge chunks")
        
        # Save stats
        stats_file = OUTPUT_DIR / "processing_stats.json"
        with open(stats_file, "w") as f:
            json.dump({
                **{k: v if not isinstance(v, defaultdict) else dict(v) 
                   for k, v in self.stats.items()},
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        print(f"  Saved stats")
    
    def generate_distilled_modules(self):
        """Generate weighted distilled knowledge modules."""
        print("\n" + "=" * 70)
        print("GENERATING DISTILLED MODULES")
        print("=" * 70)
        
        DISTILLED_DIR.mkdir(parents=True, exist_ok=True)
        
        # Group by language, sort by weight within each
        by_lang = defaultdict(list)
        for trace in self.expert_traces:
            by_lang[trace.language].append(trace)
        
        lang_names = {"en": "EN", "es": "ES", "fr": "FR", "de": "DE", "ar": "AR"}
        
        for lang, traces in by_lang.items():
            if lang not in lang_names:
                continue
            
            # Sort by weight (TPS + recent first)
            traces = sorted(traces, key=lambda t: -t.weight)[:500]
            
            class_name = f"TPSLeanKnowledge{lang_names[lang]}"
            filename = f"tps_lean_knowledge_{lang}.py"
            
            module = self._generate_module(lang, class_name, traces)
            
            filepath = DISTILLED_DIR / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(module)
            
            # Count high-weight traces
            high_weight = sum(1 for t in traces if t.weight >= TPS_WEIGHT)
            print(f"  {lang.upper()}: {len(traces)} principles ({high_weight} high-weight TPS)")
        
        # Generate unified engine
        self._generate_unified_engine()
    
    def _generate_module(self, lang: str, class_name: str, traces: List[ExpertTrace]) -> str:
        """Generate Python module for language."""
        def escape(s):
            return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        
        principles = []
        for t in traces:
            principles.append(f'''        {{
            "id": "{t.id}",
            "principle": "{escape(t.principle[:400])}",
            "domain": "{t.domain}",
            "year": {t.year},
            "weight": {t.weight:.1f},
            "keywords": {t.keywords[:5]},
            "recommendations": {[escape(r) for r in t.recommendations[:3]]}
        }}''')
        
        return f'''"""
Distilled TPS/Lean Knowledge - {lang.upper()}
Weighted by TPS relevance and recency.

TPS content: 3x weight
Recent (2000+): 2x weight  
Combined: 6x weight

Total: {len(traces)} principles
"""

from typing import Dict, List, Any


class {class_name}:
    LANGUAGE = "{lang}"
    
    # Sorted by weight (TPS + recent first)
    PRINCIPLES = [
{",".join(principles)}
    ]
    
    @classmethod
    def get_principles(cls, min_weight: float = 0) -> List[Dict]:
        """Get principles filtered by minimum weight."""
        return [p for p in cls.PRINCIPLES if p.get("weight", 1) >= min_weight]
    
    @classmethod
    def get_tps_principles(cls) -> List[Dict]:
        """Get high-weight TPS principles."""
        return [p for p in cls.PRINCIPLES if p.get("weight", 1) >= {TPS_WEIGHT}]
    
    @classmethod
    def get_by_domain(cls, domain: str) -> List[Dict]:
        return [p for p in cls.PRINCIPLES if p["domain"] == domain]
    
    @classmethod
    def reason(cls, query: str, max_results: int = 5) -> List[Dict]:
        """Weighted reasoning - TPS content prioritized."""
        query_words = set(query.lower().split())
        results = []
        
        for p in cls.PRINCIPLES:
            words = set(p["principle"].lower().split())
            keywords = set(kw.lower() for kw in p.get("keywords", []))
            
            overlap = len(query_words & (words | keywords))
            # Weight boost for TPS content
            score = overlap * p.get("weight", 1)
            
            if score > 0:
                results.append({{"principle": p, "score": score}})
        
        results.sort(key=lambda x: -x["score"])
        return results[:max_results]
'''
    
    def _generate_unified_engine(self):
        """Generate unified reasoning engine."""
        filepath = DISTILLED_DIR / "unified_reasoning_engine.py"
        
        content = '''"""
Unified Distilled Reasoning Engine - TPS Weighted
Prioritizes TPS/Lean content in all reasoning operations.
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class UnifiedDistilledReasoning:
    """
    Unified reasoning with TPS prioritization.
    Weight thresholds:
    - TPS content: >= 3.0
    - Recent content: >= 2.0
    - High priority: >= 6.0 (TPS + recent)
    """
    
    SUPPORTED_LANGUAGES = ["en", "es", "fr", "de", "ar"]
    TPS_WEIGHT_THRESHOLD = 3.0
    
    def __init__(self):
        self._modules = {}
        self._load_modules()
    
    def _load_modules(self):
        for lang in self.SUPPORTED_LANGUAGES:
            try:
                if lang == "en":
                    from .tps_lean_knowledge_en import TPSLeanKnowledgeEN
                    self._modules["en"] = TPSLeanKnowledgeEN
                elif lang == "es":
                    from .tps_lean_knowledge_es import TPSLeanKnowledgeES
                    self._modules["es"] = TPSLeanKnowledgeES
                elif lang == "fr":
                    from .tps_lean_knowledge_fr import TPSLeanKnowledgeFR
                    self._modules["fr"] = TPSLeanKnowledgeFR
                elif lang == "de":
                    from .tps_lean_knowledge_de import TPSLeanKnowledgeDE
                    self._modules["de"] = TPSLeanKnowledgeDE
                elif lang == "ar":
                    from .tps_lean_knowledge_ar import TPSLeanKnowledgeAR
                    self._modules["ar"] = TPSLeanKnowledgeAR
            except ImportError:
                logger.warning(f"{lang} module not available")
    
    def reason(self, query: str, language: str = "en", 
               prioritize_tps: bool = True,
               max_results: int = 5) -> List[Dict]:
        """
        Reason over query with optional TPS prioritization.
        
        Args:
            query: The question or problem
            language: Target language
            prioritize_tps: If True, TPS content gets weight boost
            max_results: Maximum results to return
        """
        if language not in self._modules:
            language = "en"
        
        module = self._modules.get(language)
        if not module:
            return []
        
        results = module.reason(query, max_results * 2)
        
        if prioritize_tps:
            # Boost TPS content
            for r in results:
                if r["principle"].get("weight", 1) >= self.TPS_WEIGHT_THRESHOLD:
                    r["score"] *= 1.5
            results.sort(key=lambda x: -x["score"])
        
        return results[:max_results]
    
    def get_tps_guidance(self, problem: str, language: str = "en") -> Dict:
        """Get TPS-specific guidance for a problem."""
        module = self._modules.get(language)
        if not module:
            return {}
        
        tps_principles = module.get_tps_principles()
        
        # Find relevant TPS principles
        problem_words = set(problem.lower().split())
        matches = []
        
        for p in tps_principles:
            words = set(p["principle"].lower().split())
            if problem_words & words:
                matches.append(p)
        
        return {
            "relevant_principles": matches[:5],
            "recommendations": [r for p in matches[:3] 
                              for r in p.get("recommendations", [])][:5],
            "tps_focus": True
        }
'''
        
        with open(filepath, "w") as f:
            f.write(content)
        print("  Generated unified reasoning engine")


def main():
    seeder = WeightedKnowledgeSeeder()
    seeder.process_all_books()
    seeder.save_outputs()
    seeder.generate_distilled_modules()
    
    print("\n" + "=" * 70)
    print("SEEDING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
