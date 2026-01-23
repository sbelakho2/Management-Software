"""
Comprehensive TPS & Lean Knowledge Sources.

This module provides an extensive collection of authoritative TPS (Toyota Production System),
Lean Manufacturing, and Operational Excellence knowledge sources from around the world.

Sources include:
- Toyota official resources
- Academic institutions (MIT, Stanford, University of Michigan, Cambridge)
- Government resources (NIST, EPA, DOE)
- Professional organizations (LEI, AME, Shingo Institute)
- Classic texts and historical documents
- Industry case studies
- International resources (Japan, Germany, UK)

All sources are categorized by:
- License type (public domain, CC, proprietary for reference only)
- Content format (HTML, PDF, video, course materials)
- Topic taxonomy (JIT, Jidoka, Kaizen, etc.)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


# =============================================================================
# Enums
# =============================================================================


class SourceCategory(str, Enum):
    """High-level source categories."""
    TOYOTA_OFFICIAL = "toyota_official"
    ACADEMIC = "academic"
    GOVERNMENT = "government"
    PROFESSIONAL_ORG = "professional_org"
    CLASSIC_TEXT = "classic_text"
    INDUSTRY_CASE = "industry_case"
    VIDEO_COURSE = "video_course"
    TOOL_TEMPLATE = "tool_template"
    RESEARCH_PAPER = "research_paper"
    BLOG_ARTICLE = "blog_article"


class LicenseType(str, Enum):
    """License types for knowledge sources."""
    PUBLIC_DOMAIN = "public_domain"
    CC_BY = "cc_by"
    CC_BY_SA = "cc_by_sa"
    CC_BY_NC = "cc_by_nc"
    CC_BY_NC_SA = "cc_by_nc_sa"
    US_GOVERNMENT = "us_government"
    OPEN_ACCESS = "open_access"
    FAIR_USE = "fair_use"
    PROPRIETARY_REFERENCE = "proprietary_reference"


class TopicArea(str, Enum):
    """TPS/Lean topic areas."""
    # Core TPS Pillars
    JUST_IN_TIME = "just_in_time"
    JIDOKA = "jidoka"
    
    # Foundational Concepts
    MUDA_MURA_MURI = "muda_mura_muri"
    CONTINUOUS_FLOW = "continuous_flow"
    PULL_SYSTEMS = "pull_systems"
    HEIJUNKA = "heijunka"
    STANDARDIZED_WORK = "standardized_work"
    
    # Improvement Methods
    KAIZEN = "kaizen"
    PDCA = "pdca"
    A3_THINKING = "a3_thinking"
    FIVE_WHYS = "five_whys"
    DMAIC = "dmaic"
    
    # Tools & Techniques
    KANBAN = "kanban"
    ANDON = "andon"
    POKA_YOKE = "poka_yoke"
    FIVE_S = "five_s"
    SMED = "smed"
    TPM = "tpm"
    VSM = "value_stream_mapping"
    
    # Management & Strategy
    HOSHIN_KANRI = "hoshin_kanri"
    GEMBA = "gemba"
    RESPECT_FOR_PEOPLE = "respect_for_people"
    LEADERSHIP = "leadership"
    
    # Quality
    QUALITY_AT_SOURCE = "quality_at_source"
    SPC = "statistical_process_control"
    SIX_SIGMA = "six_sigma"
    
    # Broader Applications
    LEAN_OFFICE = "lean_office"
    LEAN_HEALTHCARE = "lean_healthcare"
    LEAN_CONSTRUCTION = "lean_construction"
    LEAN_SOFTWARE = "lean_software"
    AGILE = "agile"
    
    # History & Philosophy
    HISTORY = "history"
    PHILOSOPHY = "philosophy"
    CULTURE = "culture"


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class KnowledgeSource:
    """A TPS/Lean knowledge source."""
    id: str
    name: str
    description: str
    url: str
    category: SourceCategory
    license_type: LicenseType
    topics: list[TopicArea]
    tags: list[str]
    format: str  # html, pdf, video, course
    language: str = "en"
    author: str | None = None
    organization: str | None = None
    year_published: int | None = None
    last_verified: datetime | None = None
    quality_score: float = 0.8  # 0-1 scale
    notes: str | None = None


# =============================================================================
# COMPREHENSIVE TPS/LEAN KNOWLEDGE SOURCES
# =============================================================================


COMPREHENSIVE_TPS_SOURCES: list[KnowledgeSource] = [
    # =========================================================================
    # TOYOTA OFFICIAL SOURCES
    # =========================================================================
    KnowledgeSource(
        id="toyota_global_tps",
        name="Toyota Global - Toyota Production System",
        description="Official Toyota explanation of TPS pillars: Just-in-Time and Jidoka. Primary authoritative source.",
        url="https://www.toyota-global.com/company/vision_philosophy/toyota_production_system/",
        category=SourceCategory.TOYOTA_OFFICIAL,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.JUST_IN_TIME, TopicArea.JIDOKA, TopicArea.PHILOSOPHY],
        tags=["toyota", "tps", "official", "jit", "jidoka"],
        format="html",
        organization="Toyota Motor Corporation",
        quality_score=1.0,
    ),
    KnowledgeSource(
        id="toyota_global_kaizen",
        name="Toyota Global - Kaizen Philosophy",
        description="Toyota's official explanation of continuous improvement philosophy.",
        url="https://www.toyota-global.com/company/vision_philosophy/toyota_production_system/kaizen.html",
        category=SourceCategory.TOYOTA_OFFICIAL,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.KAIZEN, TopicArea.PHILOSOPHY],
        tags=["toyota", "kaizen", "continuous-improvement"],
        format="html",
        organization="Toyota Motor Corporation",
        quality_score=1.0,
    ),
    KnowledgeSource(
        id="toyota_global_jidoka",
        name="Toyota Global - Jidoka",
        description="Official Toyota explanation of Jidoka (automation with human intelligence).",
        url="https://www.toyota-global.com/company/vision_philosophy/toyota_production_system/jidoka.html",
        category=SourceCategory.TOYOTA_OFFICIAL,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.JIDOKA, TopicArea.QUALITY_AT_SOURCE],
        tags=["toyota", "jidoka", "quality", "automation"],
        format="html",
        organization="Toyota Motor Corporation",
        quality_score=1.0,
    ),
    KnowledgeSource(
        id="toyota_north_america_tps",
        name="Toyota North America - TPS Explained",
        description="Toyota North America's explanation of TPS for American audiences.",
        url="https://www.toyota.com/usa/operations/production-system/",
        category=SourceCategory.TOYOTA_OFFICIAL,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.JUST_IN_TIME, TopicArea.JIDOKA, TopicArea.STANDARDIZED_WORK],
        tags=["toyota", "north-america", "tps"],
        format="html",
        organization="Toyota North America",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="toyota_way_2001",
        name="The Toyota Way 2001 (Internal Document)",
        description="Toyota's internal document defining the Toyota Way principles. Referenced in academic literature.",
        url="https://www.toyota-global.com/company/history_of_toyota/75years/data/conditions/philosophy/toyotaway2001.html",
        category=SourceCategory.TOYOTA_OFFICIAL,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PHILOSOPHY, TopicArea.RESPECT_FOR_PEOPLE, TopicArea.KAIZEN],
        tags=["toyota-way", "philosophy", "culture", "respect"],
        format="html",
        organization="Toyota Motor Corporation",
        year_published=2001,
        quality_score=1.0,
    ),
    
    # =========================================================================
    # ACADEMIC SOURCES - MIT
    # =========================================================================
    KnowledgeSource(
        id="mit_ocw_lean_enterprise",
        name="MIT OCW - Integrating the Lean Enterprise",
        description="Complete MIT course on Lean Enterprise with lectures, readings, and assignments.",
        url="https://ocw.mit.edu/courses/16-852j-integrating-the-lean-enterprise-fall-2005/",
        category=SourceCategory.ACADEMIC,
        license_type=LicenseType.CC_BY_NC_SA,
        topics=[TopicArea.VSM, TopicArea.CONTINUOUS_FLOW, TopicArea.LEADERSHIP],
        tags=["mit", "course", "lean-enterprise", "education"],
        format="course",
        organization="MIT OpenCourseWare",
        year_published=2005,
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="mit_ocw_manufacturing_systems",
        name="MIT OCW - Manufacturing Systems Analysis",
        description="MIT course covering manufacturing systems including lean manufacturing concepts.",
        url="https://ocw.mit.edu/courses/2-852-manufacturing-systems-analysis-spring-2010/",
        category=SourceCategory.ACADEMIC,
        license_type=LicenseType.CC_BY_NC_SA,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.PULL_SYSTEMS, TopicArea.HEIJUNKA],
        tags=["mit", "manufacturing", "systems-analysis"],
        format="course",
        organization="MIT OpenCourseWare",
        year_published=2010,
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="mit_sloan_lean_dynamics",
        name="MIT Sloan - System Dynamics and Lean",
        description="MIT Sloan research on system dynamics applied to lean manufacturing.",
        url="https://ocw.mit.edu/courses/15-988-system-dynamics-self-study-fall-1998-spring-1999/",
        category=SourceCategory.ACADEMIC,
        license_type=LicenseType.CC_BY_NC_SA,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.VSM],
        tags=["mit", "sloan", "system-dynamics"],
        format="course",
        organization="MIT Sloan School of Management",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # ACADEMIC SOURCES - OTHER UNIVERSITIES
    # =========================================================================
    KnowledgeSource(
        id="umich_lean_manufacturing",
        name="University of Michigan - Lean Manufacturing Resources",
        description="University of Michigan's Lean manufacturing research and resources.",
        url="https://leanlab.engin.umich.edu/",
        category=SourceCategory.ACADEMIC,
        license_type=LicenseType.OPEN_ACCESS,
        topics=[TopicArea.VSM, TopicArea.SMED, TopicArea.TPM],
        tags=["university-of-michigan", "lean", "research"],
        format="html",
        organization="University of Michigan",
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="stanford_lean_startup",
        name="Stanford - Lean Startup Methodology",
        description="Stanford's resources on applying Lean principles to startups and innovation.",
        url="https://www.gsb.stanford.edu/faculty-research/case-studies/lean-startup",
        category=SourceCategory.ACADEMIC,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PDCA, TopicArea.KAIZEN, TopicArea.LEAN_SOFTWARE],
        tags=["stanford", "lean-startup", "innovation"],
        format="html",
        organization="Stanford Graduate School of Business",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="cardiff_lean_enterprise",
        name="Cardiff University - Lean Enterprise Research Centre",
        description="UK academic research center focused on Lean enterprise and operations.",
        url="https://www.cardiff.ac.uk/research/explore/research-units/lean-enterprise-research-centre",
        category=SourceCategory.ACADEMIC,
        license_type=LicenseType.OPEN_ACCESS,
        topics=[TopicArea.VSM, TopicArea.LEADERSHIP, TopicArea.CULTURE],
        tags=["cardiff", "uk", "research", "lean-enterprise"],
        format="html",
        organization="Cardiff University",
        language="en",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="cambridge_ifm_lean",
        name="Cambridge IfM - Lean Manufacturing Resources",
        description="Cambridge Institute for Manufacturing resources on Lean operations.",
        url="https://www.ifm.eng.cam.ac.uk/research/industrial-sustainability/lean-management/",
        category=SourceCategory.ACADEMIC,
        license_type=LicenseType.OPEN_ACCESS,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.STANDARDIZED_WORK],
        tags=["cambridge", "uk", "manufacturing"],
        format="html",
        organization="University of Cambridge",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # GOVERNMENT SOURCES - US
    # =========================================================================
    KnowledgeSource(
        id="nist_mep_lean_guide",
        name="NIST MEP - Lean Manufacturing Guide",
        description="Official US Government guide to Lean manufacturing from NIST MEP.",
        url="https://www.nist.gov/system/files/documents/mep/Lean-Manufacturing-Guide.pdf",
        category=SourceCategory.GOVERNMENT,
        license_type=LicenseType.US_GOVERNMENT,
        topics=[TopicArea.FIVE_S, TopicArea.VSM, TopicArea.KANBAN, TopicArea.SMED],
        tags=["nist", "mep", "government", "guide"],
        format="pdf",
        organization="National Institute of Standards and Technology",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="epa_lean_environment",
        name="EPA - Lean and Environment Toolkit",
        description="EPA toolkit for integrating Lean manufacturing with environmental sustainability.",
        url="https://www.epa.gov/lean/lean-environment-toolkit",
        category=SourceCategory.GOVERNMENT,
        license_type=LicenseType.US_GOVERNMENT,
        topics=[TopicArea.MUDA_MURA_MURI, TopicArea.VSM],
        tags=["epa", "environment", "sustainability", "green-lean"],
        format="html",
        organization="Environmental Protection Agency",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="doe_lean_energy",
        name="DOE - Lean Manufacturing for Energy Efficiency",
        description="Department of Energy resources on Lean for energy reduction.",
        url="https://www.energy.gov/eere/amo/lean-manufacturing",
        category=SourceCategory.GOVERNMENT,
        license_type=LicenseType.US_GOVERNMENT,
        topics=[TopicArea.MUDA_MURA_MURI, TopicArea.TPM],
        tags=["doe", "energy", "efficiency"],
        format="html",
        organization="Department of Energy",
        quality_score=0.8,
    ),
    KnowledgeSource(
        id="va_lean_healthcare",
        name="VA - Lean Healthcare in Veterans Affairs",
        description="Veterans Affairs implementation of Lean in healthcare settings.",
        url="https://www.va.gov/QUALITYOFCARE/initiatives/lean/",
        category=SourceCategory.GOVERNMENT,
        license_type=LicenseType.US_GOVERNMENT,
        topics=[TopicArea.LEAN_HEALTHCARE, TopicArea.A3_THINKING, TopicArea.VSM],
        tags=["va", "healthcare", "lean-healthcare"],
        format="html",
        organization="Department of Veterans Affairs",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # PROFESSIONAL ORGANIZATIONS
    # =========================================================================
    KnowledgeSource(
        id="lei_lean_org",
        name="Lean Enterprise Institute - Knowledge Center",
        description="Primary Lean knowledge source from LEI, founded by Jim Womack.",
        url="https://www.lean.org/explore-lean/what-is-lean/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.VSM, TopicArea.PULL_SYSTEMS, TopicArea.HEIJUNKA, TopicArea.LEADERSHIP],
        tags=["lei", "womack", "lean-thinking"],
        format="html",
        author="James P. Womack",
        organization="Lean Enterprise Institute",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="lei_a3_thinking",
        name="LEI - Understanding A3 Thinking",
        description="LEI's comprehensive guide to A3 problem-solving methodology.",
        url="https://www.lean.org/explore-lean/a3-thinking/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.A3_THINKING, TopicArea.PDCA, TopicArea.FIVE_WHYS],
        tags=["lei", "a3", "problem-solving"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="shingo_institute",
        name="Shingo Institute - The Shingo Model",
        description="Shingo Institute's operational excellence model and principles.",
        url="https://shingo.org/shingo-model/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PHILOSOPHY, TopicArea.CULTURE, TopicArea.LEADERSHIP],
        tags=["shingo", "excellence", "principles"],
        format="html",
        organization="Jon M. Huntsman School of Business",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="ame_resources",
        name="AME - Association for Manufacturing Excellence",
        description="AME's library of Lean and operational excellence resources.",
        url="https://www.ame.org/target/lean-sensei",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.GEMBA, TopicArea.KAIZEN, TopicArea.LEADERSHIP],
        tags=["ame", "manufacturing", "excellence"],
        format="html",
        organization="Association for Manufacturing Excellence",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="asq_lean_six_sigma",
        name="ASQ - Lean Six Sigma Resources",
        description="American Society for Quality resources on Lean Six Sigma integration.",
        url="https://asq.org/quality-resources/lean",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.SIX_SIGMA, TopicArea.DMAIC, TopicArea.SPC],
        tags=["asq", "six-sigma", "quality"],
        format="html",
        organization="American Society for Quality",
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="iise_lean",
        name="IISE - Industrial Engineering Lean Resources",
        description="Institute of Industrial and Systems Engineers Lean resources.",
        url="https://www.iise.org/details.aspx?id=43494",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.STANDARDIZED_WORK],
        tags=["iise", "industrial-engineering"],
        format="html",
        organization="Institute of Industrial and Systems Engineers",
        quality_score=0.8,
    ),
    
    # =========================================================================
    # CLASSIC TEXTS & HISTORICAL SOURCES
    # =========================================================================
    KnowledgeSource(
        id="taylor_scientific_mgmt",
        name="Frederick Taylor - Principles of Scientific Management (1911)",
        description="Classic text on scientific management - historical foundation of modern manufacturing.",
        url="https://www.gutenberg.org/files/6435/6435-h/6435-h.htm",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.PUBLIC_DOMAIN,
        topics=[TopicArea.HISTORY, TopicArea.STANDARDIZED_WORK],
        tags=["taylor", "scientific-management", "history", "gutenberg"],
        format="html",
        author="Frederick Winslow Taylor",
        year_published=1911,
        quality_score=0.9,
        notes="Historical context - foundation that TPS evolved from and improved upon",
    ),
    KnowledgeSource(
        id="ford_moving_assembly",
        name="Ford - Today and Tomorrow (1926)",
        description="Henry Ford's principles that influenced Taiichi Ohno's development of TPS.",
        url="https://archive.org/details/todaytomorrow00telerich",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.PUBLIC_DOMAIN,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.HISTORY],
        tags=["ford", "mass-production", "history"],
        format="html",
        author="Henry Ford",
        year_published=1926,
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="deming_out_of_crisis",
        name="Deming - Out of the Crisis (Summary)",
        description="Summary of Deming's 14 points and their influence on Japanese manufacturing.",
        url="https://deming.org/explore/fourteen-points/",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PDCA, TopicArea.QUALITY_AT_SOURCE, TopicArea.PHILOSOPHY],
        tags=["deming", "quality", "14-points", "pdca"],
        format="html",
        author="W. Edwards Deming",
        organization="The Deming Institute",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="juran_quality_handbook",
        name="Juran's Quality Contributions",
        description="Joseph Juran's contributions to quality management and their influence on TPS.",
        url="https://www.juran.com/blog/the-history-of-quality/",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.QUALITY_AT_SOURCE, TopicArea.HISTORY],
        tags=["juran", "quality", "history"],
        format="html",
        author="Joseph M. Juran",
        organization="Juran Institute",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="shewhart_statistical_method",
        name="Shewhart - Statistical Method and Quality Control",
        description="Walter Shewhart's PDCA cycle and statistical process control foundations.",
        url="https://asq.org/quality-resources/shewhart-cycle",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PDCA, TopicArea.SPC, TopicArea.HISTORY],
        tags=["shewhart", "pdca", "spc", "history"],
        format="html",
        author="Walter A. Shewhart",
        organization="ASQ",
        quality_score=0.9,
    ),
    
    # =========================================================================
    # WIKIPEDIA KNOWLEDGE BASE
    # =========================================================================
    KnowledgeSource(
        id="wiki_lean_manufacturing",
        name="Wikipedia - Lean Manufacturing",
        description="Comprehensive Wikipedia article on Lean manufacturing history and principles.",
        url="https://en.wikipedia.org/wiki/Lean_manufacturing",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.HISTORY, TopicArea.MUDA_MURA_MURI, TopicArea.CONTINUOUS_FLOW],
        tags=["wikipedia", "lean", "overview"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_toyota_production_system",
        name="Wikipedia - Toyota Production System",
        description="Wikipedia's TPS article with history, pillars, and implementation details.",
        url="https://en.wikipedia.org/wiki/Toyota_Production_System",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.JUST_IN_TIME, TopicArea.JIDOKA, TopicArea.HISTORY],
        tags=["wikipedia", "tps", "toyota"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_kaizen",
        name="Wikipedia - Kaizen",
        description="Wikipedia article on Kaizen philosophy and practices.",
        url="https://en.wikipedia.org/wiki/Kaizen",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.KAIZEN, TopicArea.PDCA],
        tags=["wikipedia", "kaizen", "continuous-improvement"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_kanban",
        name="Wikipedia - Kanban",
        description="Wikipedia article on Kanban systems in manufacturing and software.",
        url="https://en.wikipedia.org/wiki/Kanban",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.KANBAN, TopicArea.PULL_SYSTEMS],
        tags=["wikipedia", "kanban", "pull-system"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_five_s",
        name="Wikipedia - 5S Methodology",
        description="Wikipedia article on 5S workplace organization methodology.",
        url="https://en.wikipedia.org/wiki/5S_(methodology)",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.FIVE_S, TopicArea.STANDARDIZED_WORK],
        tags=["wikipedia", "5s", "workplace-organization"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_six_sigma",
        name="Wikipedia - Six Sigma",
        description="Wikipedia article on Six Sigma quality methodology.",
        url="https://en.wikipedia.org/wiki/Six_Sigma",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.SIX_SIGMA, TopicArea.DMAIC, TopicArea.SPC],
        tags=["wikipedia", "six-sigma", "quality"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_tqm",
        name="Wikipedia - Total Quality Management",
        description="Wikipedia article on TQM principles and history.",
        url="https://en.wikipedia.org/wiki/Total_quality_management",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.QUALITY_AT_SOURCE, TopicArea.PHILOSOPHY],
        tags=["wikipedia", "tqm", "quality"],
        format="html",
        quality_score=0.8,
    ),
    KnowledgeSource(
        id="wiki_poka_yoke",
        name="Wikipedia - Poka-yoke (Mistake-Proofing)",
        description="Wikipedia article on mistake-proofing techniques.",
        url="https://en.wikipedia.org/wiki/Poka-yoke",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.POKA_YOKE, TopicArea.JIDOKA],
        tags=["wikipedia", "poka-yoke", "mistake-proofing"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_andon",
        name="Wikipedia - Andon",
        description="Wikipedia article on Andon visual management systems.",
        url="https://en.wikipedia.org/wiki/Andon_(manufacturing)",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.ANDON, TopicArea.JIDOKA],
        tags=["wikipedia", "andon", "visual-management"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_value_stream_mapping",
        name="Wikipedia - Value Stream Mapping",
        description="Wikipedia article on VSM methodology and symbols.",
        url="https://en.wikipedia.org/wiki/Value-stream_mapping",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.VSM, TopicArea.CONTINUOUS_FLOW],
        tags=["wikipedia", "vsm", "value-stream"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_gemba",
        name="Wikipedia - Gemba",
        description="Wikipedia article on Gemba (the real place) concept.",
        url="https://en.wikipedia.org/wiki/Gemba",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.GEMBA, TopicArea.LEADERSHIP],
        tags=["wikipedia", "gemba", "go-and-see"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_smed",
        name="Wikipedia - SMED (Single-Minute Exchange of Die)",
        description="Wikipedia article on quick changeover methodology.",
        url="https://en.wikipedia.org/wiki/Single-minute_exchange_of_die",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.SMED, TopicArea.CONTINUOUS_FLOW],
        tags=["wikipedia", "smed", "quick-changeover"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_tpm",
        name="Wikipedia - Total Productive Maintenance",
        description="Wikipedia article on TPM methodology.",
        url="https://en.wikipedia.org/wiki/Total_productive_maintenance",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.TPM],
        tags=["wikipedia", "tpm", "maintenance"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_heijunka",
        name="Wikipedia - Heijunka (Production Leveling)",
        description="Wikipedia article on production leveling methodology.",
        url="https://en.wikipedia.org/wiki/Heijunka",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.HEIJUNKA, TopicArea.JUST_IN_TIME],
        tags=["wikipedia", "heijunka", "leveling"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_hoshin_kanri",
        name="Wikipedia - Hoshin Kanri",
        description="Wikipedia article on policy deployment methodology.",
        url="https://en.wikipedia.org/wiki/Hoshin_Kanri",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.HOSHIN_KANRI, TopicArea.LEADERSHIP],
        tags=["wikipedia", "hoshin-kanri", "strategy-deployment"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_a3_report",
        name="Wikipedia - A3 Problem Solving",
        description="Wikipedia article on A3 structured problem-solving.",
        url="https://en.wikipedia.org/wiki/A3_problem_solving",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.A3_THINKING, TopicArea.PDCA],
        tags=["wikipedia", "a3", "problem-solving"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_five_whys",
        name="Wikipedia - Five Whys",
        description="Wikipedia article on 5 Whys root cause analysis.",
        url="https://en.wikipedia.org/wiki/Five_whys",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.FIVE_WHYS, TopicArea.A3_THINKING],
        tags=["wikipedia", "five-whys", "root-cause"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_taiichi_ohno",
        name="Wikipedia - Taiichi Ohno",
        description="Biography of Taiichi Ohno, father of the Toyota Production System.",
        url="https://en.wikipedia.org/wiki/Taiichi_Ohno",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.HISTORY, TopicArea.PHILOSOPHY],
        tags=["wikipedia", "taiichi-ohno", "biography", "history"],
        format="html",
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="wiki_shigeo_shingo",
        name="Wikipedia - Shigeo Shingo",
        description="Biography of Shigeo Shingo, developer of SMED and Poka-Yoke.",
        url="https://en.wikipedia.org/wiki/Shigeo_Shingo",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.SMED, TopicArea.POKA_YOKE, TopicArea.HISTORY],
        tags=["wikipedia", "shigeo-shingo", "biography", "history"],
        format="html",
        quality_score=0.9,
    ),
    
    # =========================================================================
    # LEAN SOFTWARE & AGILE
    # =========================================================================
    KnowledgeSource(
        id="agile_manifesto",
        name="Agile Manifesto",
        description="The original Agile Manifesto and its Lean manufacturing roots.",
        url="https://agilemanifesto.org/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.CC_BY,
        topics=[TopicArea.AGILE, TopicArea.LEAN_SOFTWARE],
        tags=["agile", "manifesto", "software"],
        format="html",
        year_published=2001,
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="wiki_lean_software",
        name="Wikipedia - Lean Software Development",
        description="Wikipedia article on applying Lean principles to software development.",
        url="https://en.wikipedia.org/wiki/Lean_software_development",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.LEAN_SOFTWARE, TopicArea.AGILE],
        tags=["wikipedia", "lean-software", "agile"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="kanban_software",
        name="Kanban for Software Development",
        description="David Anderson's Kanban method for knowledge work.",
        url="https://www.agilealliance.org/glossary/kanban/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.KANBAN, TopicArea.LEAN_SOFTWARE, TopicArea.AGILE],
        tags=["kanban", "software", "agile"],
        format="html",
        organization="Agile Alliance",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # LEAN HEALTHCARE
    # =========================================================================
    KnowledgeSource(
        id="ihi_lean_healthcare",
        name="IHI - Lean in Healthcare",
        description="Institute for Healthcare Improvement resources on Lean healthcare.",
        url="https://www.ihi.org/Topics/LeanHealthCare/Pages/default.aspx",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.LEAN_HEALTHCARE, TopicArea.VSM, TopicArea.A3_THINKING],
        tags=["ihi", "healthcare", "lean-healthcare"],
        format="html",
        organization="Institute for Healthcare Improvement",
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="catalysis_healthcare",
        name="Catalysis - Healthcare Value Network",
        description="Network for Lean healthcare transformation resources.",
        url="https://createvalue.org/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.LEAN_HEALTHCARE, TopicArea.LEADERSHIP],
        tags=["catalysis", "healthcare", "transformation"],
        format="html",
        organization="Catalysis",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # LEAN CONSTRUCTION
    # =========================================================================
    KnowledgeSource(
        id="lci_lean_construction",
        name="Lean Construction Institute",
        description="Resources on applying Lean principles to construction industry.",
        url="https://www.leanconstruction.org/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.LEAN_CONSTRUCTION, TopicArea.VSM],
        tags=["lci", "construction", "lean-construction"],
        format="html",
        organization="Lean Construction Institute",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_lean_construction",
        name="Wikipedia - Lean Construction",
        description="Wikipedia article on Lean construction methodology.",
        url="https://en.wikipedia.org/wiki/Lean_construction",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.LEAN_CONSTRUCTION],
        tags=["wikipedia", "lean-construction"],
        format="html",
        quality_score=0.8,
    ),
    
    # =========================================================================
    # INTERNATIONAL SOURCES
    # =========================================================================
    KnowledgeSource(
        id="jma_japan",
        name="Japan Management Association",
        description="JMA's resources on Japanese management and production systems.",
        url="https://www.jma.or.jp/en/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.KAIZEN, TopicArea.TPM, TopicArea.CULTURE],
        tags=["jma", "japan", "management"],
        format="html",
        organization="Japan Management Association",
        language="en",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="jipm_tpm",
        name="JIPM - Japan Institute of Plant Maintenance",
        description="Originator of TPM methodology and resources.",
        url="https://www.jipm.or.jp/en/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.TPM],
        tags=["jipm", "japan", "tpm", "maintenance"],
        format="html",
        organization="Japan Institute of Plant Maintenance",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="fraunhofer_lean",
        name="Fraunhofer Institute - Lean Production Systems",
        description="German research institute's Lean manufacturing research.",
        url="https://www.ipa.fraunhofer.de/en/expertise/production-and-logistics-systems/lean-production-systems.html",
        category=SourceCategory.ACADEMIC,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.STANDARDIZED_WORK],
        tags=["fraunhofer", "germany", "research"],
        format="html",
        organization="Fraunhofer IPA",
        language="en",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # TOOLS & TEMPLATES
    # =========================================================================
    KnowledgeSource(
        id="lei_a3_template",
        name="LEI - A3 Report Template",
        description="Standard A3 report template from Lean Enterprise Institute.",
        url="https://www.lean.org/explore-lean/a3-template/",
        category=SourceCategory.TOOL_TEMPLATE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.A3_THINKING, TopicArea.PDCA],
        tags=["template", "a3", "problem-solving"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="vsm_symbols",
        name="Value Stream Mapping Symbols Guide",
        description="Standard VSM symbols and their meanings.",
        url="https://www.lean.org/lexicon-terms/value-stream-mapping/",
        category=SourceCategory.TOOL_TEMPLATE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.VSM],
        tags=["vsm", "symbols", "mapping"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.9,
    ),
    
    # =========================================================================
    # RESEARCH PAPERS (Open Access)
    # =========================================================================
    KnowledgeSource(
        id="arxiv_lean_ml",
        name="arXiv - Machine Learning in Lean Manufacturing",
        description="Academic papers on ML/AI applications in Lean manufacturing.",
        url="https://arxiv.org/search/?query=lean+manufacturing&searchtype=all",
        category=SourceCategory.RESEARCH_PAPER,
        license_type=LicenseType.OPEN_ACCESS,
        topics=[TopicArea.KAIZEN],
        tags=["arxiv", "research", "machine-learning"],
        format="html",
        quality_score=0.8,
    ),
    
    # =========================================================================
    # ADDITIONAL CLASSIC AUTHORS & TEXTS
    # =========================================================================
    KnowledgeSource(
        id="ohno_tps_book",
        name="Taiichi Ohno - Toyota Production System Overview",
        description="Summary of Ohno's foundational book on TPS philosophy and methods.",
        url="https://www.lean.org/lexicon-terms/toyota-production-system/",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.JUST_IN_TIME, TopicArea.JIDOKA, TopicArea.MUDA_MURA_MURI, TopicArea.PHILOSOPHY],
        tags=["ohno", "tps", "classic", "philosophy"],
        format="html",
        author="Taiichi Ohno",
        organization="Lean Enterprise Institute",
        year_published=1988,
        quality_score=0.98,
    ),
    KnowledgeSource(
        id="shingo_study_tps",
        name="Shigeo Shingo - Study of Toyota Production System",
        description="Overview of Shingo's industrial engineering contributions to TPS.",
        url="https://en.wikipedia.org/wiki/Shigeo_Shingo",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.SMED, TopicArea.POKA_YOKE, TopicArea.QUALITY_AT_SOURCE],
        tags=["shingo", "smed", "poka-yoke", "classic"],
        format="html",
        author="Shigeo Shingo",
        year_published=1981,
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="liker_toyota_way",
        name="Jeffrey Liker - The Toyota Way Principles",
        description="Summary of the 14 management principles from The Toyota Way.",
        url="https://www.lean.org/lexicon-terms/the-toyota-way/",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PHILOSOPHY, TopicArea.LEADERSHIP, TopicArea.CULTURE, TopicArea.RESPECT_FOR_PEOPLE],
        tags=["liker", "toyota-way", "14-principles", "management"],
        format="html",
        author="Jeffrey K. Liker",
        year_published=2004,
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="womack_jones_lean_thinking",
        name="Womack & Jones - Lean Thinking Principles",
        description="The 5 Lean thinking principles from the seminal Lean Thinking book.",
        url="https://www.lean.org/explore-lean/lean-thinking/",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.VSM, TopicArea.PULL_SYSTEMS, TopicArea.CONTINUOUS_FLOW, TopicArea.PHILOSOPHY],
        tags=["womack", "jones", "lean-thinking", "5-principles"],
        format="html",
        author="James P. Womack and Daniel T. Jones",
        organization="Lean Enterprise Institute",
        year_published=1996,
        quality_score=0.98,
    ),
    KnowledgeSource(
        id="machine_changed_world",
        name="The Machine That Changed the World (Summary)",
        description="Overview of the book that introduced 'lean production' to the West.",
        url="https://en.wikipedia.org/wiki/The_Machine_That_Changed_the_World_(book)",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.HISTORY, TopicArea.PHILOSOPHY],
        tags=["womack", "jones", "roos", "imvp", "history"],
        format="html",
        author="James P. Womack, Daniel T. Jones, and Daniel Roos",
        year_published=1990,
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="crosby_quality_free",
        name="Philip Crosby - Quality is Free Concepts",
        description="Overview of Crosby's zero defects and quality management principles.",
        url="https://en.wikipedia.org/wiki/Philip_B._Crosby",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.QUALITY_AT_SOURCE, TopicArea.HISTORY],
        tags=["crosby", "quality", "zero-defects"],
        format="html",
        author="Philip B. Crosby",
        year_published=1979,
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="ishikawa_quality_circles",
        name="Kaoru Ishikawa - Quality Circles and Tools",
        description="Ishikawa's contributions: fishbone diagrams, quality circles, 7 QC tools.",
        url="https://en.wikipedia.org/wiki/Kaoru_Ishikawa",
        category=SourceCategory.CLASSIC_TEXT,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.QUALITY_AT_SOURCE, TopicArea.A3_THINKING, TopicArea.HISTORY],
        tags=["ishikawa", "fishbone", "quality-circles", "7-qc-tools"],
        format="html",
        author="Kaoru Ishikawa",
        quality_score=0.9,
    ),
    
    # =========================================================================
    # ADDITIONAL INDUSTRY ASSOCIATIONS
    # =========================================================================
    KnowledgeSource(
        id="sme_lean",
        name="SME - Society of Manufacturing Engineers Lean Resources",
        description="SME's resources on Lean manufacturing and operational excellence.",
        url="https://www.sme.org/technologies/lean-six-sigma/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.SIX_SIGMA],
        tags=["sme", "manufacturing", "lean"],
        format="html",
        organization="Society of Manufacturing Engineers",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="apics_lean",
        name="APICS/ASCM - Lean Supply Chain Resources",
        description="ASCM resources on Lean supply chain management.",
        url="https://www.ascm.org/learning-development/certifications-credentials/cpim/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PULL_SYSTEMS, TopicArea.JUST_IN_TIME],
        tags=["apics", "ascm", "supply-chain"],
        format="html",
        organization="Association for Supply Chain Management",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="aiag_lean_automotive",
        name="AIAG - Automotive Industry Lean Standards",
        description="Automotive Industry Action Group resources on Lean in automotive.",
        url="https://www.aiag.org/quality/quality-tools",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.STANDARDIZED_WORK, TopicArea.QUALITY_AT_SOURCE],
        tags=["aiag", "automotive", "quality"],
        format="html",
        organization="Automotive Industry Action Group",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="efqm_excellence",
        name="EFQM - European Foundation for Quality Management",
        description="European excellence model with Lean integration.",
        url="https://efqm.org/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.LEADERSHIP, TopicArea.PHILOSOPHY],
        tags=["efqm", "europe", "excellence"],
        format="html",
        organization="European Foundation for Quality Management",
        language="en",
        quality_score=0.8,
    ),
    
    # =========================================================================
    # ADDITIONAL WIKIPEDIA SOURCES
    # =========================================================================
    KnowledgeSource(
        id="wiki_mura",
        name="Wikipedia - Mura (Unevenness)",
        description="Wikipedia article on Mura - unevenness in production.",
        url="https://en.wikipedia.org/wiki/Mura_(Japanese_term)",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.MUDA_MURA_MURI, TopicArea.HEIJUNKA],
        tags=["wikipedia", "mura", "unevenness"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_muri",
        name="Wikipedia - Muri (Overburden)",
        description="Wikipedia article on Muri - overburden on workers or equipment.",
        url="https://en.wikipedia.org/wiki/Muri_(Japanese_term)",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.MUDA_MURA_MURI, TopicArea.RESPECT_FOR_PEOPLE],
        tags=["wikipedia", "muri", "overburden"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_oee",
        name="Wikipedia - Overall Equipment Effectiveness",
        description="Wikipedia article on OEE metric used in TPM.",
        url="https://en.wikipedia.org/wiki/Overall_equipment_effectiveness",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.TPM],
        tags=["wikipedia", "oee", "equipment", "effectiveness"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_takt_time",
        name="Wikipedia - Takt Time",
        description="Wikipedia article on Takt time concept in Lean.",
        url="https://en.wikipedia.org/wiki/Takt_time",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.JUST_IN_TIME, TopicArea.CONTINUOUS_FLOW],
        tags=["wikipedia", "takt-time", "pacing"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_autonomation",
        name="Wikipedia - Autonomation",
        description="Wikipedia article on autonomation (Jidoka) with human touch.",
        url="https://en.wikipedia.org/wiki/Autonomation",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.JIDOKA],
        tags=["wikipedia", "autonomation", "jidoka"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_supermarket",
        name="Wikipedia - Supermarket (Lean)",
        description="Wikipedia article on supermarket inventory system in Lean.",
        url="https://en.wikipedia.org/wiki/Supermarket_(manufacturing)",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.PULL_SYSTEMS, TopicArea.KANBAN],
        tags=["wikipedia", "supermarket", "inventory"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_bottleneck",
        name="Wikipedia - Theory of Constraints",
        description="Wikipedia article on TOC and bottleneck management.",
        url="https://en.wikipedia.org/wiki/Theory_of_constraints",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.CONTINUOUS_FLOW],
        tags=["wikipedia", "toc", "constraints", "bottleneck"],
        format="html",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="wiki_kata",
        name="Wikipedia - Toyota Kata",
        description="Wikipedia article on Improvement Kata and Coaching Kata.",
        url="https://en.wikipedia.org/wiki/Toyota_Kata",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.KAIZEN, TopicArea.PDCA, TopicArea.LEADERSHIP],
        tags=["wikipedia", "kata", "improvement", "coaching"],
        format="html",
        author="Mike Rother",
        quality_score=0.9,
    ),
    
    # =========================================================================
    # ADDITIONAL VIDEO & COURSE RESOURCES
    # =========================================================================
    KnowledgeSource(
        id="coursera_lean_six_sigma",
        name="Coursera - Lean Six Sigma Specialization",
        description="University of Amsterdam's Lean Six Sigma certification course.",
        url="https://www.coursera.org/specializations/lean-six-sigma",
        category=SourceCategory.VIDEO_COURSE,
        license_type=LicenseType.PROPRIETARY_REFERENCE,
        topics=[TopicArea.SIX_SIGMA, TopicArea.DMAIC, TopicArea.VSM],
        tags=["coursera", "course", "six-sigma", "certification"],
        format="course",
        organization="University of Amsterdam",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="edx_lean_production",
        name="edX - Lean Production",
        description="TU Delft's Lean production fundamentals course.",
        url="https://www.edx.org/learn/lean-management",
        category=SourceCategory.VIDEO_COURSE,
        license_type=LicenseType.PROPRIETARY_REFERENCE,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.STANDARDIZED_WORK],
        tags=["edx", "course", "tu-delft", "lean"],
        format="course",
        organization="TU Delft",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="youtube_gemba_academy",
        name="Gemba Academy - Free Lean Videos",
        description="Comprehensive free Lean training videos from Gemba Academy.",
        url="https://www.gembaacademy.com/free-lean-resources",
        category=SourceCategory.VIDEO_COURSE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.GEMBA, TopicArea.FIVE_S, TopicArea.VSM],
        tags=["gemba-academy", "video", "training"],
        format="video",
        organization="Gemba Academy",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # ADDITIONAL CASE STUDIES
    # =========================================================================
    KnowledgeSource(
        id="boeing_lean",
        name="Boeing Lean Manufacturing Case Study",
        description="Boeing's implementation of Lean manufacturing principles.",
        url="https://www.boeing.com/company/about-bca/", 
        category=SourceCategory.INDUSTRY_CASE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.STANDARDIZED_WORK],
        tags=["boeing", "aerospace", "case-study"],
        format="html",
        organization="Boeing",
        quality_score=0.8,
    ),
    KnowledgeSource(
        id="john_deere_lean",
        name="John Deere Manufacturing Excellence",
        description="John Deere's Lean manufacturing and operational excellence programs.",
        url="https://www.deere.com/en/our-company/",
        category=SourceCategory.INDUSTRY_CASE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.TPM, TopicArea.STANDARDIZED_WORK],
        tags=["john-deere", "agriculture", "case-study"],
        format="html",
        organization="John Deere",
        quality_score=0.8,
    ),
    KnowledgeSource(
        id="virginia_mason_lean",
        name="Virginia Mason - Lean Healthcare Pioneer",
        description="Virginia Mason's pioneering implementation of TPS in healthcare.",
        url="https://www.virginiamason.org/virginia-mason-production-system",
        category=SourceCategory.INDUSTRY_CASE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.LEAN_HEALTHCARE, TopicArea.GEMBA, TopicArea.A3_THINKING],
        tags=["virginia-mason", "healthcare", "case-study"],
        format="html",
        organization="Virginia Mason Medical Center",
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="danaher_dbs",
        name="Danaher Business System",
        description="Danaher's renowned business system based on Lean principles.",
        url="https://www.danaher.com/about-danaher/danaher-business-system",
        category=SourceCategory.INDUSTRY_CASE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.KAIZEN, TopicArea.LEADERSHIP, TopicArea.CULTURE],
        tags=["danaher", "dbs", "case-study", "business-system"],
        format="html",
        organization="Danaher Corporation",
        quality_score=0.9,
    ),
    
    # =========================================================================
    # ADDITIONAL TOOLS & TEMPLATES
    # =========================================================================
    KnowledgeSource(
        id="lei_kata_patterns",
        name="LEI - Improvement Kata Patterns",
        description="Starter kata patterns for coaching and improvement.",
        url="https://www.lean.org/explore-lean/improvement-kata/",
        category=SourceCategory.TOOL_TEMPLATE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.KAIZEN, TopicArea.PDCA, TopicArea.LEADERSHIP],
        tags=["template", "kata", "coaching", "improvement"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="five_s_checklist",
        name="5S Audit Checklist Template",
        description="Standard 5S audit checklist for workplace organization.",
        url="https://www.lean.org/lexicon-terms/5s/",
        category=SourceCategory.TOOL_TEMPLATE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.FIVE_S],
        tags=["template", "5s", "audit", "checklist"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="standard_work_template",
        name="Standard Work Combination Sheet",
        description="Template for documenting standard work sequences.",
        url="https://www.lean.org/lexicon-terms/standardized-work/",
        category=SourceCategory.TOOL_TEMPLATE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.STANDARDIZED_WORK],
        tags=["template", "standard-work", "combination-sheet"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.9,
    ),
    KnowledgeSource(
        id="smed_worksheet",
        name="SMED Analysis Worksheet",
        description="Template for analyzing and reducing changeover times.",
        url="https://www.lean.org/lexicon-terms/smed/",
        category=SourceCategory.TOOL_TEMPLATE,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.SMED],
        tags=["template", "smed", "changeover", "quick-changeover"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # ADDITIONAL RESEARCH & ACADEMIC
    # =========================================================================
    KnowledgeSource(
        id="research_gate_lean",
        name="ResearchGate - Lean Manufacturing Research",
        description="Academic research papers on Lean manufacturing.",
        url="https://www.researchgate.net/topic/Lean-Manufacturing/publications",
        category=SourceCategory.RESEARCH_PAPER,
        license_type=LicenseType.OPEN_ACCESS,
        topics=[TopicArea.KAIZEN, TopicArea.CONTINUOUS_FLOW],
        tags=["researchgate", "research", "academic"],
        format="html",
        quality_score=0.8,
    ),
    KnowledgeSource(
        id="scholar_lean",
        name="Google Scholar - Lean Production Research",
        description="Academic search for Lean production research papers.",
        url="https://scholar.google.com/scholar?q=lean+production+manufacturing",
        category=SourceCategory.RESEARCH_PAPER,
        license_type=LicenseType.OPEN_ACCESS,
        topics=[TopicArea.PHILOSOPHY, TopicArea.HISTORY],
        tags=["google-scholar", "research", "academic"],
        format="html",
        quality_score=0.8,
    ),
    KnowledgeSource(
        id="jstor_lean_mgmt",
        name="JSTOR - Lean Management Research",
        description="Academic journal articles on Lean management.",
        url="https://www.jstor.org/action/doBasicSearch?Query=lean+management",
        category=SourceCategory.RESEARCH_PAPER,
        license_type=LicenseType.OPEN_ACCESS,
        topics=[TopicArea.LEADERSHIP, TopicArea.PHILOSOPHY],
        tags=["jstor", "research", "academic", "management"],
        format="html",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # ADDITIONAL INTERNATIONAL SOURCES
    # =========================================================================
    KnowledgeSource(
        id="wef_manufacturing",
        name="World Economic Forum - Future of Manufacturing",
        description="WEF resources on advanced manufacturing and Lean principles.",
        url="https://www.weforum.org/topics/manufacturing-and-value-chains/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.CONTINUOUS_FLOW, TopicArea.PHILOSOPHY],
        tags=["wef", "future", "manufacturing"],
        format="html",
        organization="World Economic Forum",
        quality_score=0.8,
    ),
    KnowledgeSource(
        id="unido_lean",
        name="UNIDO - Lean Manufacturing Resources",
        description="United Nations Industrial Development Organization Lean resources.",
        url="https://www.unido.org/our-focus-safeguarding-environment-resource-efficient-and-low-carbon-industrial-production",
        category=SourceCategory.GOVERNMENT,
        license_type=LicenseType.OPEN_ACCESS,
        topics=[TopicArea.MUDA_MURA_MURI],
        tags=["unido", "un", "international", "development"],
        format="html",
        organization="United Nations Industrial Development Organization",
        quality_score=0.8,
    ),
    KnowledgeSource(
        id="kaizen_institute",
        name="Kaizen Institute - Global Lean Resources",
        description="Global Kaizen consulting organization's resources.",
        url="https://www.kaizen.com/what-is-kaizen/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.KAIZEN, TopicArea.GEMBA, TopicArea.LEADERSHIP],
        tags=["kaizen-institute", "consulting", "global"],
        format="html",
        organization="Kaizen Institute",
        quality_score=0.85,
    ),
    KnowledgeSource(
        id="monozukuri_japan",
        name="Monozukuri - Japanese Manufacturing Philosophy",
        description="Japanese philosophy of 'making things' that underlies TPS.",
        url="https://en.wikipedia.org/wiki/Monozukuri",
        category=SourceCategory.BLOG_ARTICLE,
        license_type=LicenseType.CC_BY_SA,
        topics=[TopicArea.PHILOSOPHY, TopicArea.CULTURE, TopicArea.RESPECT_FOR_PEOPLE],
        tags=["monozukuri", "japan", "philosophy", "craftsmanship"],
        format="html",
        language="en",
        quality_score=0.85,
    ),
    
    # =========================================================================
    # SPECIFIC CONCEPTS DEEP DIVES
    # =========================================================================
    KnowledgeSource(
        id="lei_waste_types",
        name="LEI - Eight Types of Waste (Muda)",
        description="Comprehensive guide to the 8 types of manufacturing waste.",
        url="https://www.lean.org/lexicon-terms/muda-mura-muri/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.MUDA_MURA_MURI],
        tags=["lei", "waste", "muda", "8-wastes"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="lei_pull_systems",
        name="LEI - Pull Production Systems",
        description="Deep dive into pull production vs. push systems.",
        url="https://www.lean.org/lexicon-terms/pull-production/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PULL_SYSTEMS, TopicArea.KANBAN],
        tags=["lei", "pull", "production", "kanban"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="lei_continuous_flow",
        name="LEI - Continuous Flow Production",
        description="Principles and implementation of continuous flow.",
        url="https://www.lean.org/lexicon-terms/continuous-flow/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.CONTINUOUS_FLOW],
        tags=["lei", "flow", "one-piece-flow"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="lei_respect_people",
        name="LEI - Respect for People Principle",
        description="Deep dive into the often-overlooked respect for people pillar.",
        url="https://www.lean.org/explore-lean/respect-for-people/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.RESPECT_FOR_PEOPLE, TopicArea.CULTURE, TopicArea.LEADERSHIP],
        tags=["lei", "respect", "people", "culture"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="lei_pdca",
        name="LEI - PDCA Problem Solving",
        description="Plan-Do-Check-Act cycle for systematic problem solving.",
        url="https://www.lean.org/lexicon-terms/pdca/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.PDCA, TopicArea.A3_THINKING],
        tags=["lei", "pdca", "problem-solving", "deming"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.95,
    ),
    KnowledgeSource(
        id="lei_gemba_walk",
        name="LEI - Gemba Walk Guide",
        description="How to conduct effective Gemba walks.",
        url="https://www.lean.org/lexicon-terms/gemba/",
        category=SourceCategory.PROFESSIONAL_ORG,
        license_type=LicenseType.FAIR_USE,
        topics=[TopicArea.GEMBA, TopicArea.LEADERSHIP],
        tags=["lei", "gemba", "walk", "go-see"],
        format="html",
        organization="Lean Enterprise Institute",
        quality_score=0.95,
    ),
]


# =============================================================================
# Service Functions
# =============================================================================


def get_all_sources() -> list[KnowledgeSource]:
    """Get all TPS/Lean knowledge sources."""
    return COMPREHENSIVE_TPS_SOURCES


def get_sources_by_category(category: SourceCategory) -> list[KnowledgeSource]:
    """Get sources filtered by category."""
    return [s for s in COMPREHENSIVE_TPS_SOURCES if s.category == category]


def get_sources_by_topic(topic: TopicArea) -> list[KnowledgeSource]:
    """Get sources filtered by topic area."""
    return [s for s in COMPREHENSIVE_TPS_SOURCES if topic in s.topics]


def get_sources_by_license(license_type: LicenseType) -> list[KnowledgeSource]:
    """Get sources filtered by license type."""
    return [s for s in COMPREHENSIVE_TPS_SOURCES if s.license_type == license_type]


def get_high_quality_sources(min_score: float = 0.9) -> list[KnowledgeSource]:
    """Get sources with quality score above threshold."""
    return [s for s in COMPREHENSIVE_TPS_SOURCES if s.quality_score >= min_score]


def get_sources_by_tags(tags: list[str]) -> list[KnowledgeSource]:
    """Get sources that have any of the specified tags."""
    tag_set = set(tags)
    return [s for s in COMPREHENSIVE_TPS_SOURCES if tag_set & set(s.tags)]


def get_source_statistics() -> dict[str, Any]:
    """Get statistics about the knowledge sources."""
    sources = COMPREHENSIVE_TPS_SOURCES
    
    by_category: dict[str, int] = {}
    for s in sources:
        by_category[s.category.value] = by_category.get(s.category.value, 0) + 1
    
    by_license: dict[str, int] = {}
    for s in sources:
        by_license[s.license_type.value] = by_license.get(s.license_type.value, 0) + 1
    
    topic_counts: dict[str, int] = {}
    for s in sources:
        for t in s.topics:
            topic_counts[t.value] = topic_counts.get(t.value, 0) + 1
    
    return {
        "total_sources": len(sources),
        "by_category": by_category,
        "by_license": by_license,
        "topic_coverage": topic_counts,
        "average_quality_score": sum(s.quality_score for s in sources) / len(sources),
        "high_quality_count": len([s for s in sources if s.quality_score >= 0.9]),
    }


def generate_cli_commands() -> list[dict[str, str]]:
    """Generate CLI commands for acquiring all sources."""
    commands = []
    for source in COMPREHENSIVE_TPS_SOURCES:
        if source.format in ("html", "pdf"):
            if source.format == "pdf":
                cmd = f'curl -L -o "{source.id}.pdf" "{source.url}"'
            else:
                cmd = f'curl -s "{source.url}" > "{source.id}.html"'
            
            commands.append({
                "source_id": source.id,
                "source_name": source.name,
                "command": cmd,
                "license": source.license_type.value,
            })
    
    return commands
