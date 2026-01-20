#!/usr/bin/env python3
"""
Massive Book Catalog & Downloader - 500+ per language guaranteed
================================================================

Uses Open Library + Internet Archive with EXTENSIVE search terms.
Expands searches to ensure 500+ usable books per language.

Strategy:
1. Search with many variants and broader terms
2. Include general business/management that applies
3. Download and validate content quality
"""

import asyncio
import aiohttp
import json
import hashlib
import re
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, asdict, field
from urllib.parse import quote

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('massive_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("downloaded_books")
TXT_DIR = OUTPUT_DIR / "txt"
PROGRESS_FILE = Path("massive_progress.json")

MAX_CONCURRENT = 5
MIN_BOOKS_PER_LANG = 500
MIN_FILE_SIZE = 5000  # 5KB minimum

# MASSIVE search query list - very broad to ensure enough books
QUERIES = {
    "en": [
        # TPS/Lean core
        "toyota production system", "lean manufacturing", "lean management",
        "kaizen", "continuous improvement", "just in time", "kanban",
        "value stream", "six sigma", "lean thinking", "toyota way",
        "taiichi ohno", "shigeo shingo", "total productive maintenance",
        "5S", "gemba", "hoshin kanri", "lean enterprise", "agile manufacturing",
        "standardized work", "visual management", "poka yoke", "jidoka",
        # Quality - many variants
        "quality management", "total quality", "quality control",
        "statistical process control", "quality assurance", "ISO 9001",
        "deming", "juran", "crosby quality", "zero defects", "FMEA",
        "root cause analysis", "quality improvement", "six sigma black belt",
        "control charts", "process capability", "quality circles",
        # Operations - broad
        "operations management", "production management", "manufacturing",
        "plant management", "production planning", "capacity planning",
        "operations research", "industrial management", "factory management",
        "production control", "scheduling", "manufacturing strategy",
        "theory of constraints", "factory physics", "work study",
        # Psychology/HR - many terms
        "organizational behavior", "industrial psychology", "workplace psychology",
        "management psychology", "leadership", "team building",
        "change management", "employee motivation", "performance management",
        "organizational development", "human resources management",
        "human factors", "ergonomics", "decision making", "behavioral economics",
        "organizational culture", "employee engagement", "talent management",
        # Logistics/Supply Chain
        "supply chain management", "logistics", "inventory management",
        "warehouse management", "distribution", "procurement",
        "materials management", "demand forecasting", "transportation",
        "ERP systems", "MRP", "supply chain optimization", "purchasing",
        # Finance/Accounting
        "management accounting", "cost accounting", "financial management",
        "capital budgeting", "cost management", "activity based costing",
        "budgeting", "corporate finance", "financial analysis",
        # Engineering
        "industrial engineering", "manufacturing engineering", "reliability",
        "maintenance management", "predictive maintenance", "automation",
        "process engineering", "production engineering", "machine design",
        "manufacturing processes", "CAD CAM", "robotics manufacturing",
        # General business that's relevant
        "business management", "management principles", "strategic management",
        "project management", "business strategy", "organizational management",
        "management science", "business administration", "executive management",
        "management theory", "business operations", "enterprise management"
    ],
    "es": [
        # Core terms
        "produccion", "manufactura", "calidad", "gestion",
        "administracion", "operaciones", "logistica", "finanzas",
        "contabilidad", "ingenieria", "industrial", "empresa",
        "liderazgo", "recursos humanos", "organizacional",
        # Specific
        "sistema produccion", "mejora continua", "control calidad",
        "gestion calidad", "cadena suministro", "planificacion",
        "direccion empresas", "administracion empresas",
        "psicologia trabajo", "comportamiento organizacional",
        "contabilidad costos", "presupuestos", "finanzas corporativas",
        "mantenimiento industrial", "automatizacion",
        # Broader business
        "negocios", "estrategia empresarial", "gestion proyectos",
        "economia empresa", "comercio", "marketing industrial"
    ],
    "fr": [
        # Core terms  
        "production", "fabrication", "qualite", "gestion",
        "management", "operations", "logistique", "finance",
        "comptabilite", "ingenierie", "industriel", "entreprise",
        "leadership", "ressources humaines", "organisation",
        # Specific
        "systeme production", "amelioration continue", "controle qualite",
        "gestion qualite", "chaine approvisionnement", "planification",
        "direction entreprise", "administration entreprise",
        "psychologie travail", "comportement organisationnel",
        "comptabilite analytique", "budget", "finance entreprise",
        "maintenance industrielle", "automatisation",
        # Broader
        "affaires", "strategie", "gestion projet",
        "economie entreprise", "commerce", "marketing industriel"
    ],
    "de": [
        # Core terms
        "produktion", "fertigung", "qualitat", "management",
        "verwaltung", "betrieb", "logistik", "finanz",
        "buchhaltung", "ingenieur", "industrie", "unternehmen",
        "fuhrung", "personal", "organisation",
        # Specific  
        "produktionssystem", "verbesserung", "qualitatskontrolle",
        "qualitatsmanagement", "lieferkette", "planung",
        "unternehmensfuhrung", "betriebswirtschaft",
        "arbeitspsychologie", "organisationsverhalten",
        "kostenrechnung", "controlling", "unternehmensfinanzierung",
        "instandhaltung", "automatisierung",
        # Broader
        "wirtschaft", "strategie", "projektmanagement",
        "betriebswirtschaftslehre", "handel", "industriemarketing"
    ],
    "ar": [
        # Core Arabic terms - single words work better
        "إنتاج", "تصنيع", "جودة", "إدارة",
        "عمليات", "لوجستيات", "مالية", "محاسبة",
        "هندسة", "صناعة", "شركة", "قيادة",
        "موارد بشرية", "تنظيم", "تخطيط",
        # Business terms
        "أعمال", "استراتيجية", "مشروع", "اقتصاد",
        "تجارة", "تسويق", "استثمار"
    ]
}

LANG_CODES = {
    "en": {"ol": "eng", "ia": "english", "ia2": "eng"},
    "es": {"ol": "spa", "ia": "spanish", "ia2": "spa"},
    "fr": {"ol": "fre", "ia": "french", "ia2": "fre"},
    "de": {"ol": "ger", "ia": "german", "ia2": "ger"},
    "ar": {"ol": "ara", "ia": "arabic", "ia2": "ara"}
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
    ia_id: str
    download_urls: List[str] = field(default_factory=list)
    priority: float = 1.0
    downloaded: bool = False
    file_path: str = ""
    file_size: int = 0


class MassiveDownloader:
    def __init__(self):
        self.books: Dict[str, Book] = {}
        self.downloaded_ia_ids: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {lang: {"found": 0, "downloaded": 0} for lang in QUERIES}
        
        TXT_DIR.mkdir(parents=True, exist_ok=True)
        self._load_progress()
    
    def _load_progress(self):
        if PROGRESS_FILE.exists():
            try:
                with open(PROGRESS_FILE) as f:
                    data = json.load(f)
                    for bd in data.get("books", []):
                        book = Book(**bd)
                        self.books[book.id] = book
                        if book.downloaded:
                            self.downloaded_ia_ids.add(book.ia_id)
                            self.stats[book.language]["downloaded"] += 1
                        self.stats[book.language]["found"] += 1
                logger.info(f"Loaded {len(self.books)} existing books")
            except Exception as e:
                logger.warning(f"Could not load progress: {e}")
    
    def _save_progress(self):
        data = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "books": [asdict(b) for b in self.books.values()]
        }
        with open(PROGRESS_FILE, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _calc_priority(self, year: int, title: str, domain: str) -> float:
        p = 1.0
        if year >= 2020: p += 4.0
        elif year >= 2015: p += 3.0
        elif year >= 2010: p += 2.0
        elif year >= 2000: p += 1.0
        
        tl = title.lower()
        if any(w in tl for w in ["toyota", "lean", "kaizen", "kanban", "tps"]):
            p += 5.0
        if "tps" in domain or "lean" in domain:
            p += 3.0
        return p
    
    def _gen_id(self, title: str, ia_id: str) -> str:
        return hashlib.md5(f"{title}_{ia_id}".encode()).hexdigest()[:16]
    
    def _infer_domain(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["toyota", "lean", "kaizen", "kanban", "jit", "5s", "gemba"]):
            return "tps_lean"
        elif any(w in q for w in ["quality", "qualit", "six sigma", "iso"]):
            return "quality"
        elif any(w in q for w in ["operation", "producci", "produkt", "manufactur", "fabrica"]):
            return "operations"
        elif any(w in q for w in ["psycholog", "leadership", "liderazgo", "fuhrung", "human", "team"]):
            return "psychology"
        elif any(w in q for w in ["supply", "logistic", "inventory", "warehouse"]):
            return "logistics"
        elif any(w in q for w in ["financ", "account", "cost", "budget", "comptab"]):
            return "finance"
        elif any(w in q for w in ["engineer", "mainten", "automat", "ingeni"]):
            return "engineering"
        return "management"
    
    async def _fetch_json(self, url: str, timeout: int = 30) -> Optional[dict]:
        try:
            async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status == 200:
                    return await resp.json()
        except:
            pass
        return None
    
    async def search_open_library(self, query: str, lang: str, domain: str) -> List[Book]:
        books = []
        ol_lang = LANG_CODES[lang]["ol"]
        
        url = f"https://openlibrary.org/search.json?q={quote(query)}&language={ol_lang}&has_fulltext=true&limit=100"
        data = await self._fetch_json(url)
        
        if not data or "docs" not in data:
            return books
        
        for doc in data["docs"]:
            try:
                title = doc.get("title", "")
                ia_ids = doc.get("ia", [])
                if not title or not ia_ids:
                    continue
                
                # Skip fiction
                tl = title.lower()
                if any(w in tl for w in ["novel", "fiction", "poetry", "stories", "romance", "drama"]):
                    continue
                
                ia_id = ia_ids[0]
                if ia_id in self.downloaded_ia_ids:
                    continue
                
                author = doc.get("author_name", ["Unknown"])[0] if doc.get("author_name") else "Unknown"
                year = doc.get("first_publish_year", 2000) or 2000
                
                book = Book(
                    id=self._gen_id(title, ia_id),
                    title=title[:200],
                    author=author[:100],
                    year=year,
                    language=lang,
                    domain=domain,
                    source="open_library",
                    ia_id=ia_id,
                    download_urls=[
                        f"https://archive.org/download/{ia_id}/{ia_id}_djvu.txt",
                        f"https://archive.org/download/{ia_id}/{ia_id}.txt",
                    ],
                    priority=self._calc_priority(year, title, domain)
                )
                books.append(book)
            except:
                continue
        
        return books
    
    async def search_internet_archive(self, query: str, lang: str, domain: str) -> List[Book]:
        books = []
        ia_lang = LANG_CODES[lang]["ia"]
        
        url = f"https://archive.org/advancedsearch.php?q={quote(query)}+AND+language:{ia_lang}+AND+mediatype:texts&fl=identifier,title,creator,date&sort=date+desc&rows=100&output=json"
        data = await self._fetch_json(url)
        
        if not data or "response" not in data:
            return books
        
        for doc in data["response"].get("docs", []):
            try:
                ia_id = doc.get("identifier", "")
                title = doc.get("title", "")
                if not ia_id or not title:
                    continue
                
                if ia_id in self.downloaded_ia_ids:
                    continue
                
                tl = title.lower()
                if any(w in tl for w in ["novel", "fiction", "poetry", "stories", "romance"]):
                    continue
                
                author = doc.get("creator", "Unknown")
                if isinstance(author, list):
                    author = author[0] if author else "Unknown"
                
                date_str = str(doc.get("date", "2000"))
                year_match = re.search(r'(19|20)\d{2}', date_str)
                year = int(year_match.group()) if year_match else 2000
                
                book = Book(
                    id=self._gen_id(title, ia_id),
                    title=title[:200],
                    author=author[:100] if author else "Unknown",
                    year=year,
                    language=lang,
                    domain=domain,
                    source="internet_archive",
                    ia_id=ia_id,
                    download_urls=[
                        f"https://archive.org/download/{ia_id}/{ia_id}_djvu.txt",
                        f"https://archive.org/download/{ia_id}/{ia_id}.txt",
                    ],
                    priority=self._calc_priority(year, title, domain)
                )
                books.append(book)
            except:
                continue
        
        return books
    
    async def search_ia_scrape(self, query: str, lang: str, domain: str) -> List[Book]:
        """Additional IA search with different parameters."""
        books = []
        ia_lang2 = LANG_CODES[lang]["ia2"]
        
        # Try with different search parameters
        url = f"https://archive.org/advancedsearch.php?q=({quote(query)})+AND+languageSorter:{ia_lang2}+AND+mediatype:texts&fl=identifier,title,creator,date&rows=100&output=json"
        data = await self._fetch_json(url)
        
        if not data or "response" not in data:
            return books
        
        for doc in data["response"].get("docs", []):
            try:
                ia_id = doc.get("identifier", "")
                title = doc.get("title", "")
                if not ia_id or not title or ia_id in self.downloaded_ia_ids:
                    continue
                
                tl = title.lower()
                if any(w in tl for w in ["novel", "fiction", "poetry", "stories"]):
                    continue
                
                author = doc.get("creator", "Unknown")
                if isinstance(author, list):
                    author = author[0] if author else "Unknown"
                
                year = 2000
                date_str = str(doc.get("date", ""))
                if date_str:
                    ym = re.search(r'(19|20)\d{2}', date_str)
                    if ym:
                        year = int(ym.group())
                
                book = Book(
                    id=self._gen_id(title, ia_id),
                    title=title[:200],
                    author=author[:100] if author else "Unknown",
                    year=year,
                    language=lang,
                    domain=domain,
                    source="ia_scrape",
                    ia_id=ia_id,
                    download_urls=[
                        f"https://archive.org/download/{ia_id}/{ia_id}_djvu.txt",
                        f"https://archive.org/download/{ia_id}/{ia_id}.txt",
                    ],
                    priority=self._calc_priority(year, title, domain)
                )
                books.append(book)
            except:
                continue
        
        return books
    
    def add_book(self, book: Book):
        if book.id not in self.books and book.ia_id not in self.downloaded_ia_ids:
            self.books[book.id] = book
            self.stats[book.language]["found"] += 1
    
    async def build_catalog(self):
        logger.info("=" * 70)
        logger.info("BUILDING MASSIVE CATALOG")
        logger.info("=" * 70)
        
        self.session = aiohttp.ClientSession()
        
        try:
            for lang, queries in QUERIES.items():
                logger.info(f"\n{'='*50}")
                logger.info(f"SEARCHING {lang.upper()} ({self.stats[lang]['found']} existing)")
                logger.info(f"{'='*50}")
                
                # Keep searching until we have enough
                for query in queries:
                    if self.stats[lang]["found"] >= 1000:  # Get extra for failures
                        break
                    
                    domain = self._infer_domain(query)
                    logger.info(f"  {query[:30]}...")
                    
                    # Search all sources
                    ol = await self.search_open_library(query, lang, domain)
                    for b in ol:
                        self.add_book(b)
                    
                    await asyncio.sleep(0.3)
                    
                    ia = await self.search_internet_archive(query, lang, domain)
                    for b in ia:
                        self.add_book(b)
                    
                    await asyncio.sleep(0.3)
                    
                    ia2 = await self.search_ia_scrape(query, lang, domain)
                    for b in ia2:
                        self.add_book(b)
                    
                    await asyncio.sleep(0.3)
                    
                    logger.info(f"    {lang.upper()}: {self.stats[lang]['found']} books")
                
                logger.info(f"\n{lang.upper()} CATALOG: {self.stats[lang]['found']} books")
        
        finally:
            await self.session.close()
        
        self._save_progress()
        self._print_catalog_stats()
    
    async def download_book(self, book: Book) -> bool:
        if book.downloaded:
            return True
        
        for url in book.download_urls:
            try:
                async with self.session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status != 200:
                        continue
                    
                    content = await resp.read()
                    
                    if len(content) < MIN_FILE_SIZE:
                        continue
                    
                    # Check not HTML
                    sample = content[:500].decode("utf-8", errors="ignore").lower()
                    if "<html" in sample or "<!doctype" in sample:
                        continue
                    
                    # Save
                    clean_title = re.sub(r'[<>:"/\\|?*]', '_', book.title)[:80]
                    filename = f"{book.language}_{book.id}_{clean_title}.txt"
                    filepath = TXT_DIR / filename
                    
                    with open(filepath, "wb") as f:
                        f.write(content)
                    
                    book.downloaded = True
                    book.file_path = str(filepath)
                    book.file_size = len(content)
                    self.downloaded_ia_ids.add(book.ia_id)
                    self.stats[book.language]["downloaded"] += 1
                    
                    logger.info(f"✓ {book.language.upper()}: {book.title[:40]} ({len(content)//1024}KB)")
                    return True
            except:
                continue
        
        return False
    
    async def download_all(self):
        logger.info("\n" + "=" * 70)
        logger.info("DOWNLOADING BOOKS")
        logger.info("=" * 70)
        
        self.session = aiohttp.ClientSession()
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        
        try:
            # Sort by priority
            all_books = sorted(self.books.values(), key=lambda b: -b.priority)
            
            # Download by language to ensure balance
            for lang in QUERIES.keys():
                lang_books = [b for b in all_books if b.language == lang and not b.downloaded]
                logger.info(f"\nDownloading {lang.upper()}: {len(lang_books)} pending")
                
                for i, book in enumerate(lang_books):
                    async with semaphore:
                        await self.download_book(book)
                    
                    if (i + 1) % 20 == 0:
                        logger.info(f"  {lang.upper()} progress: {self.stats[lang]['downloaded']}")
                        self._save_progress()
                    
                    await asyncio.sleep(0.5)
                    
                    # Stop if we have enough
                    if self.stats[lang]["downloaded"] >= MIN_BOOKS_PER_LANG:
                        logger.info(f"  ✓ {lang.upper()} reached {MIN_BOOKS_PER_LANG} books!")
                        break
        
        finally:
            await self.session.close()
            self._save_progress()
        
        self._print_final_stats()
    
    def _print_catalog_stats(self):
        logger.info("\n" + "=" * 70)
        logger.info("CATALOG STATISTICS")
        logger.info("=" * 70)
        for lang, s in self.stats.items():
            status = "✓" if s["found"] >= MIN_BOOKS_PER_LANG else "✗"
            logger.info(f"  {lang.upper()}: {s['found']} found {status}")
    
    def _print_final_stats(self):
        logger.info("\n" + "=" * 70)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 70)
        
        total_dl = sum(s["downloaded"] for s in self.stats.values())
        logger.info(f"Total Downloaded: {total_dl}")
        
        for lang, s in self.stats.items():
            status = "✓" if s["downloaded"] >= MIN_BOOKS_PER_LANG else "✗ NEED MORE"
            logger.info(f"  {lang.upper()}: {s['downloaded']}/{s['found']} {status}")
        
        files = list(TXT_DIR.glob("*.txt"))
        total_size = sum(f.stat().st_size for f in files)
        logger.info(f"\nFiles: {len(files)}, Size: {total_size//(1024*1024)}MB")


async def main():
    dl = MassiveDownloader()
    await dl.build_catalog()
    await dl.download_all()


if __name__ == "__main__":
    asyncio.run(main())
