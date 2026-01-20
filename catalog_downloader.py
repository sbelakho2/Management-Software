#!/usr/bin/env python3
"""
Comprehensive Book Catalog & Downloader
=======================================

Uses Open Library + Internet Archive (with proper text download).
Ensures 500+ books per language with ACTUAL downloadable content.

Focus: TPS/Lean, Operations, Quality, Psychology, Logistics, Finance, Engineering
Skew: Newer books + heavy TPS emphasis
"""

import asyncio
import aiohttp
import json
import hashlib
import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
from urllib.parse import quote
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('catalog_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

OUTPUT_DIR = Path("downloaded_books")
TXT_DIR = OUTPUT_DIR / "txt"
PROGRESS_FILE = Path("download_progress.json")
CATALOG_FILE = Path("book_catalog.json")

# Concurrency
MAX_CONCURRENT = 5
RATE_LIMIT = 1.0  # seconds between requests

# Minimum requirements
MIN_BOOKS_PER_LANG = 500
MIN_FILE_SIZE = 10000  # 10KB minimum for valid book

# ============================================================================
# SEARCH QUERIES - Heavy on TPS/Business, NO literature
# ============================================================================

SEARCH_QUERIES = {
    "en": {
        "tps_lean": [
            "toyota production system", "lean manufacturing", "lean management",
            "kaizen improvement", "continuous improvement manufacturing",
            "just in time production", "kanban system", "value stream mapping",
            "lean six sigma", "toyota way", "taiichi ohno", "shigeo shingo",
            "lean thinking", "total productive maintenance", "TPM manufacturing",
            "5S workplace", "gemba kaizen", "hoshin kanri", "lean enterprise",
            "lean transformation", "pull system", "one piece flow",
            "standardized work", "visual management factory", "poka yoke",
            "jidoka automation", "heijunka leveling", "muda waste elimination",
            "lean operations", "agile manufacturing", "world class manufacturing"
        ],
        "quality": [
            "total quality management", "six sigma methodology",
            "statistical process control", "quality control manufacturing",
            "ISO 9001 implementation", "quality improvement process",
            "deming management", "juran quality handbook", "zero defects",
            "quality assurance manufacturing", "process capability",
            "root cause analysis", "FMEA failure mode", "quality circles",
            "quality function deployment", "control charts SPC"
        ],
        "operations": [
            "operations management textbook", "production management",
            "manufacturing management", "plant management",
            "production planning control", "capacity planning",
            "master production scheduling", "operations research",
            "industrial management", "factory physics",
            "theory of constraints", "manufacturing strategy"
        ],
        "psychology": [
            "organizational behavior", "industrial organizational psychology",
            "workplace psychology", "management psychology",
            "leadership development", "team effectiveness",
            "change management organization", "employee motivation",
            "performance management systems", "organizational development",
            "human factors engineering", "workplace ergonomics",
            "decision making psychology", "behavioral economics business"
        ],
        "logistics": [
            "supply chain management", "logistics management textbook",
            "inventory management control", "warehouse management systems",
            "distribution management", "procurement management",
            "materials management", "demand forecasting",
            "transportation logistics", "ERP enterprise resource planning",
            "MRP materials requirements planning", "supply chain optimization"
        ],
        "finance": [
            "management accounting", "cost accounting manufacturing",
            "financial management business", "capital budgeting",
            "cost management strategies", "activity based costing",
            "throughput accounting", "lean accounting",
            "manufacturing cost analysis", "budgeting planning"
        ],
        "engineering": [
            "manufacturing engineering", "industrial engineering handbook",
            "reliability engineering", "maintenance management",
            "predictive maintenance", "equipment reliability",
            "manufacturing processes", "automation manufacturing",
            "process engineering", "production engineering",
            "machine design", "CAD CAM manufacturing"
        ]
    },
    "es": {
        "tps_lean": [
            "sistema produccion toyota", "manufactura esbelta",
            "lean manufacturing español", "mejora continua kaizen",
            "gestion lean", "produccion justo a tiempo"
        ],
        "quality": [
            "gestion calidad total", "control calidad",
            "six sigma español", "aseguramiento calidad"
        ],
        "operations": [
            "administracion operaciones", "gestion produccion",
            "planificacion produccion", "direccion operaciones"
        ],
        "psychology": [
            "psicologia organizacional", "comportamiento organizacional",
            "liderazgo empresarial", "recursos humanos gestion"
        ],
        "logistics": [
            "logistica empresarial", "cadena suministro",
            "gestion inventarios", "administracion almacenes"
        ],
        "finance": [
            "contabilidad costos", "contabilidad gerencial",
            "finanzas empresariales", "presupuestos"
        ],
        "engineering": [
            "ingenieria industrial", "ingenieria manufactura",
            "mantenimiento industrial", "automatizacion"
        ]
    },
    "fr": {
        "tps_lean": [
            "systeme production toyota", "lean management français",
            "amelioration continue", "production au plus juste"
        ],
        "quality": [
            "management qualite totale", "controle qualite",
            "six sigma français", "assurance qualite"
        ],
        "operations": [
            "gestion production", "gestion operations",
            "planification production", "management industriel"
        ],
        "psychology": [
            "psychologie travail organisations", "comportement organisationnel",
            "leadership management", "gestion ressources humaines"
        ],
        "logistics": [
            "logistique entreprise", "chaine approvisionnement",
            "gestion stocks", "management supply chain"
        ],
        "finance": [
            "comptabilite gestion", "controle gestion",
            "finance entreprise", "comptabilite analytique"
        ],
        "engineering": [
            "genie industriel", "maintenance industrielle",
            "ingenierie production", "automatisation"
        ]
    },
    "de": {
        "tps_lean": [
            "toyota produktionssystem", "lean management deutsch",
            "schlanke produktion", "kontinuierliche verbesserung"
        ],
        "quality": [
            "qualitatsmanagement", "qualitätssicherung",
            "six sigma deutsch", "qualitätskontrolle"
        ],
        "operations": [
            "produktionsmanagement", "betriebsmanagement",
            "fertigungsplanung", "operations management deutsch"
        ],
        "psychology": [
            "arbeitspsychologie", "organisationspsychologie",
            "führung management", "personalmanagement"
        ],
        "logistics": [
            "logistik management", "supply chain management deutsch",
            "lagerverwaltung", "bestandsmanagement"
        ],
        "finance": [
            "kostenrechnung", "controlling",
            "betriebswirtschaft", "finanzmanagement"
        ],
        "engineering": [
            "fertigungstechnik", "produktionstechnik",
            "instandhaltung", "automatisierungstechnik"
        ]
    },
    "ar": {
        "tps_lean": [
            "نظام إنتاج تويوتا", "الإنتاج الرشيق",
            "التحسين المستمر", "كايزن"
        ],
        "quality": [
            "إدارة الجودة الشاملة", "ضبط الجودة",
            "تحسين الجودة"
        ],
        "operations": [
            "إدارة العمليات", "إدارة الإنتاج",
            "تخطيط الإنتاج"
        ],
        "psychology": [
            "علم النفس التنظيمي", "السلوك التنظيمي",
            "إدارة الموارد البشرية"
        ],
        "logistics": [
            "إدارة سلسلة التوريد", "إدارة المخزون",
            "اللوجستيات"
        ],
        "finance": [
            "محاسبة التكاليف", "المحاسبة الإدارية"
        ],
        "engineering": [
            "الهندسة الصناعية", "هندسة التصنيع"
        ]
    }
}

# Language codes for APIs
LANG_CODES = {
    "en": {"ol": "eng", "ia": "english"},
    "es": {"ol": "spa", "ia": "spanish"},
    "fr": {"ol": "fre", "ia": "french"},
    "de": {"ol": "ger", "ia": "german"},
    "ar": {"ol": "ara", "ia": "arabic"}
}

@dataclass
class Book:
    id: str
    title: str
    author: str
    year: int
    language: str
    domain: str
    source: str
    ia_id: str  # Internet Archive identifier
    download_urls: List[str] = field(default_factory=list)
    priority: float = 1.0
    downloaded: bool = False
    file_path: str = ""
    file_size: int = 0


class CatalogDownloader:
    """Build catalog and download books."""
    
    def __init__(self):
        self.books: Dict[str, Book] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self.stats = {
            "by_language": {lang: {"found": 0, "downloaded": 0} for lang in SEARCH_QUERIES},
            "by_domain": {},
            "by_source": {}
        }
        
        # Create directories
        TXT_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing progress
        self._load_progress()
    
    def _load_progress(self):
        """Load existing progress."""
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE) as f:
                    data = json.load(f)
                    for book_data in data.get("books", []):
                        book = Book(**book_data)
                        self.books[book.id] = book
                logger.info(f"Loaded {len(self.books)} books from progress")
            except Exception as e:
                logger.warning(f"Could not load progress: {e}")
    
    def _save_progress(self):
        """Save progress to file."""
        data = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "books": [asdict(b) for b in self.books.values()]
        }
        with open(PROGRESS_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _calculate_priority(self, year: int, domain: str, title: str) -> float:
        """Calculate priority - TPS and newer = higher."""
        p = 1.0
        
        # Year bonus (newer is better)
        if year >= 2020: p += 4.0
        elif year >= 2015: p += 3.5
        elif year >= 2010: p += 3.0
        elif year >= 2005: p += 2.5
        elif year >= 2000: p += 2.0
        elif year >= 1990: p += 1.0
        
        # TPS keywords in title
        title_lower = title.lower()
        tps_keywords = ["toyota", "lean", "kaizen", "kanban", "jit", "tps", "ohno", "shingo"]
        if any(kw in title_lower for kw in tps_keywords):
            p += 6.0
        
        # Domain bonus
        if domain == "tps_lean":
            p += 4.0
        elif domain in ["quality", "operations"]:
            p += 2.0
        elif domain in ["psychology", "logistics"]:
            p += 1.5
        
        return p
    
    def _generate_id(self, title: str, author: str) -> str:
        """Generate unique book ID."""
        content = f"{title}_{author}".lower()
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    async def _fetch_json(self, url: str, timeout: int = 30) -> Optional[dict]:
        """Fetch JSON from URL."""
        try:
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": "SenseiOS-KnowledgeBot/1.0"}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.debug(f"Fetch error: {e}")
        return None
    
    async def search_open_library(self, query: str, language: str, domain: str) -> List[Book]:
        """Search Open Library for books with Internet Archive text."""
        books = []
        ol_lang = LANG_CODES.get(language, {}).get("ol", "eng")
        
        # Search for books with full text available
        url = f"https://openlibrary.org/search.json?q={quote(query)}&language={ol_lang}&has_fulltext=true&limit=100"
        
        data = await self._fetch_json(url)
        if not data or "docs" not in data:
            return books
        
        for doc in data["docs"]:
            try:
                title = doc.get("title", "")
                author = doc.get("author_name", ["Unknown"])[0] if doc.get("author_name") else "Unknown"
                year = doc.get("first_publish_year", 2000) or 2000
                ia_ids = doc.get("ia", [])
                
                if not title or not ia_ids:
                    continue
                
                # Skip fiction/literature
                title_lower = title.lower()
                subjects = " ".join(doc.get("subject", [])[:20]).lower()
                skip_words = ["novel", "fiction", "poetry", "stories", "tales", "romance", "drama", "plays"]
                if any(w in title_lower for w in skip_words) or any(w in subjects for w in skip_words):
                    continue
                
                ia_id = ia_ids[0]
                book_id = self._generate_id(title, author)
                
                # Build download URLs (try multiple formats)
                download_urls = [
                    f"https://archive.org/download/{ia_id}/{ia_id}_djvu.txt",
                    f"https://archive.org/download/{ia_id}/{ia_id}.txt",
                    f"https://archive.org/download/{ia_id}/{ia_id}_text.txt",
                ]
                
                book = Book(
                    id=book_id,
                    title=title[:200],
                    author=author[:100],
                    year=year,
                    language=language,
                    domain=domain,
                    source="open_library",
                    ia_id=ia_id,
                    download_urls=download_urls,
                    priority=self._calculate_priority(year, domain, title)
                )
                books.append(book)
                
            except Exception as e:
                continue
        
        return books
    
    async def search_internet_archive(self, query: str, language: str, domain: str) -> List[Book]:
        """Search Internet Archive directly for texts."""
        books = []
        ia_lang = LANG_CODES.get(language, {}).get("ia", "english")
        
        # Search for texts, sorted by date (newest first)
        url = f"https://archive.org/advancedsearch.php?q={quote(query)}+AND+language:{ia_lang}+AND+mediatype:texts&fl=identifier,title,creator,date,language&sort=date+desc&rows=100&output=json"
        
        data = await self._fetch_json(url)
        if not data or "response" not in data:
            return books
        
        for doc in data["response"].get("docs", []):
            try:
                ia_id = doc.get("identifier", "")
                title = doc.get("title", "")
                author = doc.get("creator", "Unknown")
                if isinstance(author, list):
                    author = author[0] if author else "Unknown"
                date_str = str(doc.get("date", "2000"))
                
                if not ia_id or not title:
                    continue
                
                # Skip fiction
                title_lower = title.lower()
                if any(w in title_lower for w in ["novel", "fiction", "poetry", "stories", "romance"]):
                    continue
                
                # Extract year
                year_match = re.search(r'(19|20)\d{2}', date_str)
                year = int(year_match.group()) if year_match else 2000
                
                book_id = self._generate_id(title, author)
                
                download_urls = [
                    f"https://archive.org/download/{ia_id}/{ia_id}_djvu.txt",
                    f"https://archive.org/download/{ia_id}/{ia_id}.txt",
                    f"https://archive.org/download/{ia_id}/{ia_id}_text.txt",
                ]
                
                book = Book(
                    id=book_id,
                    title=title[:200],
                    author=author[:100] if author else "Unknown",
                    year=year,
                    language=language,
                    domain=domain,
                    source="internet_archive",
                    ia_id=ia_id,
                    download_urls=download_urls,
                    priority=self._calculate_priority(year, domain, title)
                )
                books.append(book)
                
            except Exception as e:
                continue
        
        return books
    
    def add_book(self, book: Book):
        """Add book to catalog if not duplicate."""
        if book.id not in self.books:
            self.books[book.id] = book
            self.stats["by_language"][book.language]["found"] += 1
            self.stats["by_domain"][book.domain] = self.stats["by_domain"].get(book.domain, 0) + 1
            self.stats["by_source"][book.source] = self.stats["by_source"].get(book.source, 0) + 1
    
    async def build_catalog(self):
        """Build catalog from Open Library and Internet Archive."""
        logger.info("=" * 70)
        logger.info("BUILDING BOOK CATALOG")
        logger.info("=" * 70)
        
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
        self.session = aiohttp.ClientSession(connector=connector)
        
        try:
            for language, domains in SEARCH_QUERIES.items():
                logger.info(f"\n{'='*50}")
                logger.info(f"SEARCHING {language.upper()} BOOKS")
                logger.info(f"{'='*50}")
                
                # Double TPS queries for emphasis
                priority_domains = ["tps_lean", "quality", "operations"]
                
                for domain, queries in domains.items():
                    # More searches for priority domains
                    if domain in priority_domains:
                        search_queries = queries * 2
                    else:
                        search_queries = queries
                    
                    for query in search_queries:
                        logger.info(f"  Searching: {query[:40]}...")
                        
                        # Search both sources
                        ol_books = await self.search_open_library(query, language, domain)
                        for book in ol_books:
                            self.add_book(book)
                        
                        await asyncio.sleep(0.5)
                        
                        ia_books = await self.search_internet_archive(query, language, domain)
                        for book in ia_books:
                            self.add_book(book)
                        
                        await asyncio.sleep(0.5)
                        
                        found = self.stats["by_language"][language]["found"]
                        logger.info(f"    {language.upper()}: {found} books found")
                        
                        # If we have plenty, move on
                        if found >= 800:
                            break
                    
                    if self.stats["by_language"][language]["found"] >= 800:
                        break
                
                logger.info(f"\n{language.upper()} TOTAL: {self.stats['by_language'][language]['found']} books")
        
        finally:
            await self.session.close()
        
        self._save_progress()
        self._print_catalog_stats()
    
    async def download_book(self, book: Book) -> bool:
        """Download a single book."""
        if book.downloaded:
            return True
        
        async with self.semaphore:
            for url in book.download_urls:
                try:
                    async with self.session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=120),
                        headers={"User-Agent": "SenseiOS-KnowledgeBot/1.0"}
                    ) as resp:
                        if resp.status != 200:
                            continue
                        
                        content = await resp.read()
                        
                        # Validate content
                        if len(content) < MIN_FILE_SIZE:
                            continue
                        
                        # Check it's actual text, not HTML error
                        text_sample = content[:1000].decode("utf-8", errors="ignore").lower()
                        if "<html" in text_sample or "<!doctype" in text_sample:
                            continue
                        
                        # Save file
                        clean_title = re.sub(r'[<>:"/\\|?*]', '_', book.title)[:100]
                        filename = f"{book.id}_{clean_title}_{book.year}.txt"
                        filepath = TXT_DIR / filename
                        
                        with open(filepath, "wb") as f:
                            f.write(content)
                        
                        book.downloaded = True
                        book.file_path = str(filepath)
                        book.file_size = len(content)
                        
                        self.stats["by_language"][book.language]["downloaded"] += 1
                        
                        logger.info(f"✓ Downloaded: {book.title[:50]} ({book.language}, {len(content)//1024}KB)")
                        return True
                        
                except Exception as e:
                    continue
            
            return False
    
    async def download_all(self):
        """Download all books in catalog."""
        logger.info("\n" + "=" * 70)
        logger.info("DOWNLOADING BOOKS")
        logger.info("=" * 70)
        
        connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT)
        self.session = aiohttp.ClientSession(connector=connector)
        
        try:
            # Sort by priority (TPS + newer first)
            sorted_books = sorted(
                self.books.values(),
                key=lambda b: -b.priority
            )
            
            # Download with progress tracking
            for i, book in enumerate(sorted_books):
                if book.downloaded:
                    continue
                
                await self.download_book(book)
                
                # Progress report every 50 books
                if (i + 1) % 50 == 0:
                    self._print_download_progress()
                    self._save_progress()
                
                await asyncio.sleep(RATE_LIMIT)
        
        finally:
            await self.session.close()
            self._save_progress()
        
        self._print_final_stats()
    
    def _print_catalog_stats(self):
        """Print catalog statistics."""
        logger.info("\n" + "=" * 70)
        logger.info("CATALOG STATISTICS")
        logger.info("=" * 70)
        
        total = sum(s["found"] for s in self.stats["by_language"].values())
        logger.info(f"\nTotal Books Found: {total}")
        
        logger.info("\nBy Language:")
        for lang, stats in sorted(self.stats["by_language"].items()):
            status = "✓" if stats["found"] >= MIN_BOOKS_PER_LANG else "✗ NEED MORE"
            logger.info(f"  {lang.upper()}: {stats['found']} {status}")
        
        logger.info("\nBy Domain:")
        for domain, count in sorted(self.stats["by_domain"].items(), key=lambda x: -x[1]):
            logger.info(f"  {domain}: {count}")
    
    def _print_download_progress(self):
        """Print download progress."""
        logger.info("\n--- Download Progress ---")
        for lang, stats in self.stats["by_language"].items():
            logger.info(f"  {lang.upper()}: {stats['downloaded']}/{stats['found']}")
    
    def _print_final_stats(self):
        """Print final statistics."""
        logger.info("\n" + "=" * 70)
        logger.info("FINAL DOWNLOAD STATISTICS")
        logger.info("=" * 70)
        
        total_found = sum(s["found"] for s in self.stats["by_language"].values())
        total_downloaded = sum(s["downloaded"] for s in self.stats["by_language"].values())
        
        logger.info(f"\nTotal Found: {total_found}")
        logger.info(f"Total Downloaded: {total_downloaded}")
        logger.info(f"Success Rate: {100*total_downloaded/max(1,total_found):.1f}%")
        
        logger.info("\nBy Language:")
        for lang, stats in sorted(self.stats["by_language"].items()):
            status = "✓" if stats["downloaded"] >= MIN_BOOKS_PER_LANG else "✗ NEED MORE"
            logger.info(f"  {lang.upper()}: {stats['downloaded']}/{stats['found']} {status}")
        
        # Check files
        files = list(TXT_DIR.glob("*.txt"))
        total_size = sum(f.stat().st_size for f in files)
        logger.info(f"\nFiles on disk: {len(files)}")
        logger.info(f"Total size: {total_size // (1024*1024)}MB")


async def main():
    downloader = CatalogDownloader()
    
    # Build catalog first
    await downloader.build_catalog()
    
    # Then download
    await downloader.download_all()


if __name__ == "__main__":
    asyncio.run(main())
