"""
System Training Script - CLI tool to train all aspects of Sensei OS using online resources.
"""

import asyncio
import logging
import json
import sys
from pathlib import Path

# Add src to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sensei.services.ai.domain_knowledge_seeder import get_knowledge_seeder
from sensei.core.database import async_session_factory
from sensei.services.ai.knowledge_embeddings import EmbeddingService, KnowledgeEmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("SystemTraining")

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sensei OS System Training Script")
    parser.add_argument("--in-memory", action="store_true", help="Run training in-memory only (no DB)")
    args = parser.parse_args()

    logger.info("==================================================")
    logger.info("   SENSEI OS - FULL SYSTEM TRAINING STARTING      ")
    logger.info("==================================================")
    
    # Initialize services
    embed_service = EmbeddingService(provider="local")
    knowledge_embed_service = KnowledgeEmbeddingService(embed_service)
    
    seeder = get_knowledge_seeder()
    seeder.embedding_service = knowledge_embed_service
    
    results = None
    if args.in_memory:
        logger.info("Running in explicit in-memory mode...")
        results = await seeder.seed_all()
    else:
        # Run seeding with session if possible
        try:
            async with async_session_factory() as session:
                results = await seeder.seed_all(session)
        except Exception as e:
            logger.warning(f"Database session not available, falling back to in-memory: {e}")
            results = await seeder.seed_all()
    
    logger.info("==================================================")
    logger.info("   TRAINING COMPLETED                             ")
    logger.info("==================================================")
    logger.info(f"Domains Processed: {results['total_domains']}")
    logger.info(f"URLs Successfully Ingested: {results['processed_urls']}")
    logger.info(f"Total Chunks Generated: {results['ingested_chunks']}")
    logger.info(f"Failed URLs: {results['failed_urls']}")
    
    if results['failed_urls'] > 0:
        logger.warning("Some resources could not be ingested. Check logs for details.")
    
    # Export results to a report file
    report_path = Path("system_training_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Detailed training report saved to {report_path}")

if __name__ == "__main__":
    asyncio.run(main())
