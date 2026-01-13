"""
Domain Knowledge Seeder - Trains all system aspects using curated online resources.

This service implements the 'full training' requirement by ingesting authoritative
manufacturing and Lean/TPS knowledge into the Sensei OS knowledge base.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sensei.services.ai.knowledge_ingestion import KnowledgePackIngestionService
from sensei.services.ai.knowledge_embeddings import KnowledgeEmbeddingService
from sensei.models.knowledge_pack import TaxonomyTag, LicenseType

logger = logging.getLogger(__name__)

class DomainKnowledgeSeeder:
    """
    Seeds the system with comprehensive domain knowledge from curated online resources.
    """
    
    # Curated high-value open-license or public domain resources
    DOMAINS: Dict[str, List[Dict[str, Any]]] = {
        "TPS_CORE": [
            {
                "url": "https://en.wikipedia.org/wiki/Toyota_Production_System",
                "title": "Toyota Production System - Foundation",
                "tags": [TaxonomyTag.TPS.value, TaxonomyTag.LEAN_PRINCIPLES.value],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# Toyota Production System (TPS)
The Toyota Production System (TPS) is an integrated socio-technical system, developed by Toyota, that comprises its management philosophy and practices. The TPS organizes manufacturing and logistics for the automobile manufacturer, including interaction with suppliers and customers. The system is a major precursor of the more generic "lean manufacturing". Taiichi Ohno and Eiji Toyoda, Japanese industrial engineers, developed the system between 1948 and 1975.

Originally called "just-in-time production," it builds on the approach created by the founder of Toyota, Sakichi Toyoda, his son Kiichiro Toyoda, and the engineer Taiichi Ohno. The principles underlying the TPS are embodied in The Toyota Way.

## Main Objectives
The main objectives of the TPS are to design out overburden (muri) and inconsistency (mura), and to eliminate waste (muda). The most significant effects on business process delivery are achieved by designing a process capable of delivering the required results smoothly; by designing out "mura" (inconsistency), which in turn exposes "muda" (waste). 

## Two Pillars
1. Just-in-time: "Making only what is needed, only when it is needed, and only in the amount that is needed."
2. Jidoka: (Autonomation) "Automation with a human touch."
"""
            },
            {
                "url": "https://en.wikipedia.org/wiki/Just-in-time_manufacturing",
                "title": "Just-In-Time (JIT) Manufacturing",
                "tags": [TaxonomyTag.TPS.value, "JIT"],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# Just-in-Time (JIT) Manufacturing
Just-in-time (JIT) manufacturing, also known as just-in-time production or the Toyota Production System (TPS), is a methodology aimed primarily at reducing times within the production system as well as response times from suppliers and to customers.

## Elements of JIT
- Continuous improvement: Attacking fundamental problems—anything that does not add value to the product.
- Eliminating waste: Waste results from any activity that adds cost without adding value, such as moving and storing.
- Good housekeeping: Workplace cleanliness and organization.
- Set-up time reduction: Increases flexibility and allows smaller batches.
- Levelled production: Smooth flow of products through the factory.
"""
            },
            {
                "url": "https://en.wikipedia.org/wiki/Autonomation",
                "title": "Jidoka - Autonomation with a Human Touch",
                "tags": [TaxonomyTag.TPS.value, "Jidoka"],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# Jidoka (Autonomation)
Jidoka is a Japanese word used in the Toyota Production System (TPS) which can be translated as "automation with a human touch". It means that when a problem occurs, the equipment stops immediately, preventing defective products from being produced.

## The Principle of Jidoka
Jidoka highlights the causes of problems because work stops immediately when a problem is first identified. This leads to improvements in the processes by eliminating root causes. 

## Steps of Jidoka
1. Discover an abnormality.
2. STOP.
3. Fix the immediate condition.
4. Investigate the root cause and install a countermeasure.
"""
            }
        ],
        "PROBLEM_SOLVING": [
            {
                "url": "https://en.wikipedia.org/wiki/PDCA",
                "title": "PDCA (Plan-Do-Check-Act) Cycle",
                "tags": [TaxonomyTag.PDCA.value, TaxonomyTag.CONTINUOUS_IMPROVEMENT.value],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# PDCA (Plan-Do-Check-Act)
PDCA (plan–do–check–act or plan–do–check–adjust) is an iterative four-step management method used in business for the control and continuous improvement of processes and products. It is also known as the Deming circle/cycle/wheel, the Shewhart cycle, the control circle/cycle, or plan–do–study–act (PDSA).

## Phases
- PLAN: Establish objectives and processes required to deliver results in accordance with the expected output.
- DO: Implement the plan, execute the process, make the product. Collect data for charting and analysis in the following "CHECK" and "ACT" steps.
- CHECK: Study the actual results (measured and collected in "DO" above) and compare against the expected results.
- ACT: If the check shows that the plan that was implemented in 'DO' is an improvement to the prior standard, then that becomes the new standard.
"""
            },
            {
                "url": "https://en.wikipedia.org/wiki/Eight_disciplines_problem_solving",
                "title": "8D Problem Solving Methodology",
                "tags": [TaxonomyTag.PROBLEM_SOLVING.value, "8D"],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# 8D Problem Solving
The Eight Disciplines (8D) Problem Solving Process is a method developed at Ford Motor Company used to approach and to resolve problems, typically employed by quality engineers or other professionals.

## The Eight Disciplines
- D0: Preparation and Emergency Response Actions.
- D1: Use a Team.
- D2: Describe the Problem.
- D3: Develop Interim Containment Plan.
- D4: Determine, Identify, and Verify Root Causes and Escape Points.
- D5: Choose and Verify Permanent Corrections (PCs) for Root Cause and Escape Point.
- D6: Implement and Validate Permanent Corrections.
- D7: Prevent Recurrence.
- D8: Recognize Team and Individual Contributions.
"""
            },
            {
                "url": "https://en.wikipedia.org/wiki/A3_problem_solving",
                "title": "A3 Thinking and Reporting",
                "tags": [TaxonomyTag.A3_THINKING.value, TaxonomyTag.PROBLEM_SOLVING.value],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# A3 Problem Solving
A3 problem solving is a structured problem-solving and continuous-improvement approach, first employed at Toyota and typically used by lean manufacturing practitioners. It provides a simple and strict procedure that guides workers through problem solving.

## Structure of an A3 Report
The A3 report is typically a single sheet of ISO A3-size paper. It usually follows these sections:
1. Title
2. Context / Background
3. Current Condition
4. Goal / Target State
5. Root Cause Analysis
6. Countermeasures
7. Implementation Plan
8. Follow-up / Confirmation of Results
"""
            },
            {
                "url": "https://en.wikipedia.org/wiki/Five_whys",
                "title": "5 Whys Root Cause Analysis",
                "tags": [TaxonomyTag.PROBLEM_SOLVING.value, "Root Cause"],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# 5 Whys
The 5 Whys is an iterative interrogative technique used to explore the cause-and-effect relationships underlying a particular problem. The primary goal of the technique is to determine the root cause of a defect or problem by repeating the question "Why?". Each answer forms the basis of the next question.

## Example
Problem: The vehicle will not start.
1. Why? - The battery is dead.
2. Why? - The alternator is not functioning.
3. Why? - The alternator belt has broken.
4. Why? - The alternator belt was well beyond its useful service life and not replaced.
5. Why? - The vehicle was not maintained according to the recommended service schedule. (Root cause)
"""
            }
        ],
        "QUALITY_MANAGEMENT": [
            {
                "url": "https://en.wikipedia.org/wiki/Statistical_process_control",
                "title": "Statistical Process Control (SPC)",
                "tags": [TaxonomyTag.RISK_MANAGEMENT.value, "SPC"],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# Statistical Process Control (SPC)
Statistical process control (SPC) is a method of quality control which employs statistical methods to monitor and control a process. This helps to ensure that the process operates efficiently, producing more specification-conforming product with less waste.

## Key Tools
- Control charts: Graphs used to study how a process changes over time.
- Mean (X-bar) chart: Tracks the central tendency of the process.
- Range (R) chart: Tracks the dispersion or variability of the process.
- Upper and Lower Control Limits (UCL/LCL): Calculated from data, usually +/- 3 standard deviations from the mean.
"""
            },
            {
                "url": "https://en.wikipedia.org/wiki/Total_quality_management",
                "title": "Total Quality Management (TQM)",
                "tags": [TaxonomyTag.QUALITY_GATES.value, "TQM"],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# Total Quality Management (TQM)
Total Quality Management (TQM) consists of organization-wide efforts to "install and make permanent a climate where employees continuously improve their ability to provide on demand products and services that customers will find of particular value."

## Core Principles
- Customer-focused
- Total employee involvement
- Process-centered
- Integrated system
- Strategic and systematic approach
- Continual improvement
- Fact-based decision making
- Communications
"""
            }
        ],
        "LEAN_WASTE": [
            {
                "url": "https://en.wikipedia.org/wiki/Muda_(Japanese_term)",
                "title": "Muda, Mura, Muri - The Three Types of Waste",
                "tags": [TaxonomyTag.LEAN_PRINCIPLES.value, "Waste Detection"],
                "license": LicenseType.CC_BY_SA,
                "fallback_content": """
# The 3Ms of Lean: Muda, Mura, Muri
In Lean manufacturing, three types of waste are identified:

1. Muda (Waste): Any activity that does not add value. The 7+1 wastes are: Transportation, Inventory, Motion, Waiting, Overproduction, Overprocessing, Defects, and Underutilized Talent.
2. Mura (Unevenness): Inconsistency in the process, such as fluctuating production volumes or uneven work pace.
3. Muri (Overburden): Overburdening equipment or operators by requiring them to run at a higher pace than they can sustain.
"""
            }
        ]
    }

    def __init__(
        self, 
        ingestion_service: Optional[KnowledgePackIngestionService] = None,
        embedding_service: Optional[KnowledgeEmbeddingService] = None
    ):
        self.ingestion_service = ingestion_service or KnowledgePackIngestionService()
        self.embedding_service = embedding_service
        self.results: Dict[str, Any] = {
            "total_domains": len(self.DOMAINS),
            "processed_urls": 0,
            "failed_urls": 0,
            "ingested_chunks": 0,
            "details": []
        }

    async def seed_all(self, session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """
        Run the full training process across all domains.
        """
        logger.info("Starting full system training via domain knowledge seeding...")
        
        for domain_name, resources in self.DOMAINS.items():
            logger.info(f"Training aspect: {domain_name}")
            for resource in resources:
                await self._seed_resource(domain_name, resource, session)
        
        self.results["status"] = "completed"
        self.results["timestamp"] = datetime.now().isoformat()
        return self.results

    async def _seed_resource(self, domain: str, resource: Dict[str, Any], session: Optional[AsyncSession] = None):
        """
        Seed a single resource.
        """
        url = resource["url"]
        title = resource["title"]
        tags = resource.get("tags", [])
        fallback = resource.get("fallback_content")
        
        logger.info(f"Ingesting resource: {title} ({url})")
        
        try:
            doc, msg = self.ingestion_service.ingest_url(
                url=url,
                title=title,
                tags=tags,
                license_text="Ingested under CC-BY-SA license for manufacturing training."
            )
            
            # If doc failed but fallback is available, use fallback
            if not doc and fallback:
                from sensei.models.knowledge_pack import KnowledgeDocument, ContentFormat
                import hashlib
                
                logger.info(f"Using high-fidelity fallback training data for {title}")
                doc = KnowledgeDocument(
                    id=uuid4(),
                    title=title,
                    source_url=url,
                    retrieval_date=datetime.now(),
                    license_type=resource.get("license", LicenseType.CC_BY_SA),
                    attribution_text=f"Synthesized Domain Knowledge for {title}",
                    original_format=ContentFormat.MARKDOWN,
                    raw_content=fallback,
                    normalized_content=fallback,
                    word_count=len(fallback.split()),
                    content_hash=hashlib.sha256(fallback.encode()).hexdigest(),
                    tags=tags,
                    is_processed=False,
                    is_indexed=False
                )
                msg = "Using local fallback knowledge."

            if doc:
                if session:
                    session.add(doc)
                    await session.flush()

                chunks = self.ingestion_service.process_document(doc)
                
                if session:
                    for chunk in chunks:
                        session.add(chunk)
                    await session.flush()
                    
                    # Generate embeddings if service provided
                    if self.embedding_service:
                        for chunk in chunks:
                            await self.embedding_service.embed_chunk(chunk, session)
                    
                    await session.commit()

                self.results["processed_urls"] += 1
                self.results["ingested_chunks"] += len(chunks)
                self.results["details"].append({
                    "domain": domain,
                    "title": title,
                    "status": "success",
                    "chunks": len(chunks),
                    "source": "online" if "fallback" not in msg.lower() else "fallback",
                    "indexed": self.embedding_service is not None
                })
            else:
                logger.warning(f"Failed to ingest {title}: {msg}")
                self.results["failed_urls"] += 1
                self.results["details"].append({
                    "domain": domain,
                    "title": title,
                    "status": "failed",
                    "error": msg
                })
        except Exception as e:
            logger.error(f"Error during seeding of {title}: {str(e)}")
            if session:
                await session.rollback()
            self.results["failed_urls"] += 1
            self.results["details"].append({
                "domain": domain,
                "title": title,
                "status": "error",
                "error": str(e)
            })

def get_knowledge_seeder() -> DomainKnowledgeSeeder:
    return DomainKnowledgeSeeder()
