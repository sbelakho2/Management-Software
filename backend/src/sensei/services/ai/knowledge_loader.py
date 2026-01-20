"""
Knowledge Loader for Sensei OS Startup

This module loads seeded knowledge (expert traces) from JSON files
into the SenseiReasoningEngine at application startup.

Usage in app startup (e.g., main.py or lifespan handler):
    from sensei.services.ai.knowledge_loader import load_seeded_knowledge
    
    async def startup():
        await load_seeded_knowledge()
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Default paths for seeded knowledge
SEEDED_KNOWLEDGE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent.parent / "seeded_knowledge"
EXPERT_TRACES_FILE = SEEDED_KNOWLEDGE_DIR / "expert_traces.json"

# Alternative: Use distilled knowledge modules directly
USE_DISTILLED_MODULES = True


def load_expert_traces_from_file(filepath: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Load expert traces from JSON file.
    
    Args:
        filepath: Path to expert_traces.json file
        
    Returns:
        List of expert trace dictionaries
    """
    filepath = filepath or EXPERT_TRACES_FILE
    
    if not filepath.exists():
        logger.warning(f"Expert traces file not found: {filepath}")
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            traces = json.load(f)
        logger.info(f"Loaded {len(traces)} expert traces from {filepath}")
        return traces
    except Exception as e:
        logger.error(f"Error loading expert traces: {e}")
        return []


def load_expert_traces_from_modules(language: str = "en") -> List[Dict[str, Any]]:
    """
    Load expert traces from distilled knowledge modules.
    
    Args:
        language: Language code (en, es, fr, de, ar)
        
    Returns:
        List of expert trace dictionaries formatted for SenseiReasoningEngine
    """
    try:
        from sensei.services.ai.distilled_knowledge import UnifiedDistilledReasoning
        
        engine = UnifiedDistilledReasoning()
        traces = engine.get_expert_traces(language=language)
        logger.info(f"Loaded {len(traces)} expert traces from distilled modules ({language})")
        return traces
    except ImportError as e:
        logger.warning(f"Distilled knowledge modules not available: {e}")
        return []
    except Exception as e:
        logger.error(f"Error loading from distilled modules: {e}")
        return []


def load_all_language_traces() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load expert traces for all available languages.
    
    Returns:
        Dictionary mapping language code to list of traces
    """
    languages = ["en", "es", "fr", "de", "ar"]
    all_traces = {}
    
    try:
        from sensei.services.ai.distilled_knowledge import UnifiedDistilledReasoning
        engine = UnifiedDistilledReasoning()
        
        for lang in languages:
            traces = engine.get_expert_traces(language=lang)
            if traces:
                all_traces[lang] = traces
                logger.info(f"Loaded {len(traces)} traces for {lang}")
    except Exception as e:
        logger.error(f"Error loading multilingual traces: {e}")
    
    return all_traces


async def load_seeded_knowledge(
    reasoning_engine = None,
    language: str = "en",
    use_file: bool = False
) -> int:
    """
    Load seeded knowledge into the reasoning engine.
    
    This should be called at application startup to populate the
    SenseiReasoningEngine with expert traces from distilled books.
    
    Args:
        reasoning_engine: Optional SenseiReasoningEngine instance.
                         If None, creates a new one.
        language: Primary language to load (default: en)
        use_file: If True, load from JSON file instead of modules
        
    Returns:
        Number of traces loaded
    """
    # Get or create reasoning engine
    if reasoning_engine is None:
        from sensei.services.ai.reasoning_engine import SenseiReasoningEngine
        reasoning_engine = SenseiReasoningEngine()
    
    # Load traces
    if use_file:
        traces = load_expert_traces_from_file()
    else:
        traces = load_expert_traces_from_modules(language)
    
    if not traces:
        logger.warning("No expert traces available to load")
        return 0
    
    # Load into reasoning engine
    reasoning_engine.load_seeded_knowledge(traces)
    
    logger.info(f"Successfully seeded reasoning engine with {len(traces)} expert traces")
    return len(traces)


def get_knowledge_statistics() -> Dict[str, Any]:
    """
    Get statistics about available seeded knowledge.
    
    Returns:
        Dictionary with knowledge statistics
    """
    stats = {
        "file_based": {
            "available": EXPERT_TRACES_FILE.exists(),
            "path": str(EXPERT_TRACES_FILE),
            "trace_count": 0
        },
        "module_based": {
            "available": False,
            "languages": [],
            "total_principles": 0,
            "by_language": {}
        }
    }
    
    # Check file-based knowledge
    if EXPERT_TRACES_FILE.exists():
        try:
            with open(EXPERT_TRACES_FILE, "r") as f:
                traces = json.load(f)
            stats["file_based"]["trace_count"] = len(traces)
        except:
            pass
    
    # Check module-based knowledge
    try:
        from sensei.services.ai.distilled_knowledge import UnifiedDistilledReasoning
        engine = UnifiedDistilledReasoning()
        module_stats = engine.get_statistics()
        
        stats["module_based"]["available"] = True
        stats["module_based"]["languages"] = module_stats.get("languages_loaded", [])
        stats["module_based"]["total_principles"] = module_stats.get("total_principles", 0)
        stats["module_based"]["by_language"] = module_stats.get("by_language", {})
    except:
        pass
    
    return stats


# CLI for testing
if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    print("=== Knowledge Loader Statistics ===")
    stats = get_knowledge_statistics()
    
    print(f"\nFile-based knowledge:")
    print(f"  Available: {stats['file_based']['available']}")
    print(f"  Path: {stats['file_based']['path']}")
    print(f"  Trace count: {stats['file_based']['trace_count']}")
    
    print(f"\nModule-based knowledge:")
    print(f"  Available: {stats['module_based']['available']}")
    print(f"  Languages: {stats['module_based']['languages']}")
    print(f"  Total principles: {stats['module_based']['total_principles']}")
    print(f"  By language: {stats['module_based']['by_language']}")
    
    print("\n=== Testing Knowledge Loading ===")
    count = asyncio.run(load_seeded_knowledge())
    print(f"Loaded {count} traces into reasoning engine")
