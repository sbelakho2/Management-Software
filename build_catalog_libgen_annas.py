#!/usr/bin/env python3
"""
Book Catalog Builder - LibGen.vg + Anna's Archive Focus
========================================================

Uses ONLY:
1. LibGen.vg (libgen.is mirror) 
2. Anna's Archive (annas-archive.org)

Target: 500+ books per language (EN, ES, FR, DE, AR)
Focus: TPS/Lean, Operations, Quality, Psychology, Logistics, Finance, Engineering
Skew: Newer books (2000+), heavy TPS emphasis
"""

import requests
import json
import hashlib
import re
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from urllib.parse import quote
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('catalog_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Headers for requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Search queries by language - business/manufacturing focus
QUERIES = {
    "en": [
        # TPS/Lean (highest priority)
        "toyota production system", "lean manufacturing", "lean management",
        "kaizen", "continuous improvement", "just in time JIT",
        "kanban", "value stream mapping", "lean six sigma",
        "toyota way", "taiichi ohno", "shigeo shingo", "lean thinking",
        "total productive maintenance TPM", "5S methodology",
        "gemba kaizen", "hoshin kanri", "A3 problem solving",
        "lean enterprise", "lean transformation", "pull system",
        # Quality
        "total quality management TQM", "six sigma", "statistical process control",
        "quality management", "ISO 9001", "deming quality", "FMEA",
        "root cause analysis", "quality improvement",
        # Operations
        "operations management", "production management", "manufacturing management",
        "production planning", "capacity planning", "operations research",
        # Psychology/HR
        "organizational behavior", "industrial psychology", "organizational psychology",
        "leadership management", "change management", "employee engagement",
        "performance management", "team building",
        # Logistics
        "supply chain management", "logistics management", "inventory management",
        "warehouse management", "procurement", "ERP systems",
        # Finance
        "management accounting", "cost accounting", "lean accounting",
        "financial management", "activity based costing",
        # Engineering
        "industrial engineering", "manufacturing engineering", "reliability engineering",
        "maintenance management", "predictive maintenance", "automation"
    ],
    "es": [
        "sistema produccion toyota", "manufactura esbelta", "lean manufacturing",
        "mejora continua", "kaizen", "gestion calidad", "six sigma",
        "administracion operaciones", "gestion produccion",
        "psicologia organizacional", "liderazgo", "recursos humanos",
        "logistica", "cadena suministro", "gestion inventarios",
        "contabilidad costos", "finanzas", "ingenieria industrial"
    ],
    "fr": [
        "systeme production toyota", "lean management", "amelioration continue",
        "kaizen", "gestion qualite", "six sigma",
        "gestion production", "gestion operations",
        "psychologie travail", "management equipe", "ressources humaines",
        "logistique", "chaine approvisionnement",
        "comptabilite gestion", "genie industriel"
    ],
    "de": [
        "toyota produktionssystem", "lean management", "kontinuierliche verbesserung",
        "kaizen", "qualitatsmanagement", "six sigma",
        "produktionsmanagement", "betriebsmanagement",
        "arbeitspsychologie", "fuhrung", "personalmanagement",
        "logistik", "supply chain",
        "kostenrechnung", "controlling", "fertigungstechnik"
    ],
    "ar": [
        "نظام إنتاج تويوتا", "الإنتاج الرشيق", "التحسين المستمر",
        "إدارة الجودة", "إدارة العمليات", "إدارة الإنتاج",
        "علم النفس التنظيمي", "الموارد البشرية", "القيادة",
        "إدارة سلسلة التوريد", "اللوجستيات",
        "محاسبة التكاليف", "الهندسة الصناعية"
    ]
}

LANG_LIBGEN = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "ar": "Arabic"}

@dataclass
class Book:
    id: str
    title: str
    author: str
    year: int
    language: str
    domain: str
    source: str
    download_url: str
    md5: str = ""
    size_mb: float = 0
    format: str = "pdf"
    priority: float = 1.0

def calculate_priority(year: int, domain: str, title: str) -> float:
    """Calculate priority - newer and TPS = higher."""
    p = 1.0
    
    # Year bonus
    if year >= 2020: p += 4.0
    elif year >= 2015: p += 3.0
    elif year >= 2010: p += 2.0
    elif year >= 2000: p += 1.0
    
    # TPS bonus
    title_lower = title.lower()
    if any(w in title_lower for w in ["toyota", "lean", "kaizen", "kanban", "tps"]):
        p += 5.0
    
    # Domain bonus
    if "tps" in domain or "lean" in domain:
        p += 3.0
    elif domain in ["quality", "operations"]:
        p += 1.5
    
    return p

def infer_domain(query: str) -> str:
    """Infer domain from search query."""
    q = query.lower()
    if any(w in q for w in ["toyota", "lean", "kaizen", "kanban", "jit", "tpm", "5s", "gemba"]):
        return "tps_lean"
    elif any(w in q for w in ["quality", "six sigma", "tqm", "iso", "fmea"]):
        return "quality"
    elif any(w in q for w in ["operation", "production", "manufacturing", "capacity"]):
        return "operations"
    elif any(w in q for w in ["psycholog", "behavior", "leadership", "team", "hr", "human"]):
        return "psychology"
    elif any(w in q for w in ["supply chain", "logistic", "inventory", "warehouse"]):
        return "logistics"
    elif any(w in q for w in ["account", "financ", "cost", "budget"]):
        return "finance"
    elif any(w in q for w in ["engineer", "maintenance", "reliabil", "automat"]):
        return "engineering"
    return "general"


def search_libgen(query: str, language: str, session: requests.Session) -> List[Book]:
    """Search LibGen.is/LibGen.vg for books."""
    books = []
    lang_filter = LANG_LIBGEN.get(language, "English")
    domain = infer_domain(query)
    
    try:
        # LibGen search
        search_url = f"https://libgen.is/search.php?req={quote(query)}&lg_topic=libgen&open=0&view=simple&res=100&phrase=1&column=def"
        
        resp = session.get(search_url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return books
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find the results table
        tables = soup.find_all('table')
        if len(tables) < 3:
            return books
        
        results_table = tables[2]  # Usually the 3rd table has results
        rows = results_table.find_all('tr')[1:]  # Skip header
        
        for row in rows[:50]:
            try:
                cols = row.find_all('td')
                if len(cols) < 10:
                    continue
                
                # Extract data
                author = cols[1].get_text(strip=True)[:100]
                title_cell = cols[2]
                title_link = title_cell.find('a')
                title = title_link.get_text(strip=True) if title_link else cols[2].get_text(strip=True)
                title = title[:200]
                
                publisher = cols[3].get_text(strip=True)
                year_str = cols[4].get_text(strip=True)
                lang_found = cols[6].get_text(strip=True).lower()
                size = cols[7].get_text(strip=True)
                ext = cols[8].get_text(strip=True).lower()
                
                # Get MD5 from mirror links
                mirror_links = cols[9].find_all('a') if len(cols) > 9 else []
                md5 = ""
                for link in mirror_links:
                    href = link.get('href', '')
                    md5_match = re.search(r'md5=([a-fA-F0-9]{32})', href)
                    if md5_match:
                        md5 = md5_match.group(1)
                        break
                    md5_match = re.search(r'/([a-fA-F0-9]{32})', href)
                    if md5_match:
                        md5 = md5_match.group(1)
                        break
                
                if not md5:
                    continue
                
                # Filter by language
                if language == "en" and "english" not in lang_found:
                    continue
                elif language == "es" and "spanish" not in lang_found:
                    continue
                elif language == "fr" and "french" not in lang_found:
                    continue
                elif language == "de" and "german" not in lang_found:
                    continue
                elif language == "ar" and "arabic" not in lang_found:
                    continue
                
                # Skip fiction/literature
                title_lower = title.lower()
                if any(w in title_lower for w in ["novel", "fiction", "poetry", "stories", "tales", "romance"]):
                    continue
                
                # Parse year
                year = 2000
                if year_str and year_str.isdigit():
                    year = int(year_str)
                
                # Parse size
                size_mb = 0
                size_match = re.search(r'([\d.]+)\s*(mb|kb|gb)', size.lower())
                if size_match:
                    val = float(size_match.group(1))
                    unit = size_match.group(2)
                    if unit == 'kb': size_mb = val / 1024
                    elif unit == 'gb': size_mb = val * 1024
                    else: size_mb = val
                
                book = Book(
                    id=f"lg_{md5[:12]}",
                    title=title,
                    author=author if author else "Unknown",
                    year=year,
                    language=language,
                    domain=domain,
                    source="libgen",
                    download_url=f"https://libgen.vg/get.php?md5={md5}",
                    md5=md5,
                    size_mb=size_mb,
                    format=ext if ext else "pdf",
                    priority=calculate_priority(year, domain, title)
                )
                books.append(book)
                
            except Exception as e:
                continue
        
    except Exception as e:
        logger.debug(f"LibGen error for '{query}': {e}")
    
    return books


def search_annas_archive(query: str, language: str, session: requests.Session) -> List[Book]:
    """Search Anna's Archive for books."""
    books = []
    domain = infer_domain(query)
    
    lang_codes = {"en": "en", "es": "es", "fr": "fr", "de": "de", "ar": "ar"}
    lang_code = lang_codes.get(language, "en")
    
    try:
        # Anna's Archive search - sort by newest
        search_url = f"https://annas-archive.org/search?q={quote(query)}&lang={lang_code}&content=book_nonfiction&sort=newest"
        
        resp = session.get(search_url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return books
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find book entries - Anna's Archive uses specific class patterns
        # Look for links to /md5/ pages
        md5_links = soup.find_all('a', href=re.compile(r'/md5/[a-fA-F0-9]{32}'))
        
        seen_md5 = set()
        for link in md5_links[:50]:
            try:
                href = link.get('href', '')
                md5_match = re.search(r'/md5/([a-fA-F0-9]{32})', href)
                if not md5_match:
                    continue
                
                md5 = md5_match.group(1)
                if md5 in seen_md5:
                    continue
                seen_md5.add(md5)
                
                # Try to get title from link text or parent
                title = link.get_text(strip=True)
                if not title or len(title) < 5:
                    parent = link.find_parent('div')
                    if parent:
                        title = parent.get_text(strip=True)[:200]
                
                if not title or len(title) < 5:
                    title = f"Book {md5[:8]}"
                
                # Skip fiction
                title_lower = title.lower()
                if any(w in title_lower for w in ["novel", "fiction", "poetry", "stories", "romance"]):
                    continue
                
                # Anna's Archive sorted by newest, assume recent
                year = 2020
                
                book = Book(
                    id=f"aa_{md5[:12]}",
                    title=title[:200],
                    author="Unknown",
                    year=year,
                    language=language,
                    domain=domain,
                    source="annas_archive",
                    download_url=f"https://annas-archive.org/md5/{md5}",
                    md5=md5,
                    priority=calculate_priority(year, domain, title)
                )
                books.append(book)
                
            except Exception as e:
                continue
        
    except Exception as e:
        logger.debug(f"Anna's Archive error for '{query}': {e}")
    
    return books


def deduplicate_books(books: List[Book]) -> List[Book]:
    """Remove duplicate books by MD5 and similar titles."""
    seen_md5 = set()
    seen_titles = set()
    unique = []
    
    for book in books:
        # Check MD5
        if book.md5 and book.md5 in seen_md5:
            continue
        
        # Check title similarity
        title_key = re.sub(r'[^a-z0-9]', '', book.title.lower())[:50]
        if title_key in seen_titles:
            continue
        
        if book.md5:
            seen_md5.add(book.md5)
        seen_titles.add(title_key)
        unique.append(book)
    
    return unique


def main():
    logger.info("=" * 70)
    logger.info("BUILDING CATALOG FROM LIBGEN.VG + ANNA'S ARCHIVE")
    logger.info("=" * 70)
    
    session = requests.Session()
    all_books: Dict[str, List[Book]] = {lang: [] for lang in QUERIES.keys()}
    
    for language, queries in QUERIES.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"SEARCHING {language.upper()} BOOKS")
        logger.info(f"{'='*50}")
        
        for query in queries:
            logger.info(f"  Query: {query[:40]}...")
            
            # Search LibGen
            libgen_books = search_libgen(query, language, session)
            all_books[language].extend(libgen_books)
            logger.info(f"    LibGen: {len(libgen_books)} books")
            
            time.sleep(1)  # Rate limit
            
            # Search Anna's Archive
            annas_books = search_annas_archive(query, language, session)
            all_books[language].extend(annas_books)
            logger.info(f"    Anna's: {len(annas_books)} books")
            
            time.sleep(1)  # Rate limit
            
            # Progress
            total = len(all_books[language])
            logger.info(f"    {language.upper()} total: {total}")
            
            # If we have enough, move on
            if total >= 600:
                logger.info(f"  Reached 600+ for {language.upper()}, stopping early")
                break
    
    # Deduplicate and sort
    logger.info("\n" + "=" * 70)
    logger.info("DEDUPLICATING AND SORTING")
    logger.info("=" * 70)
    
    final_catalog = []
    stats = {"by_language": {}, "by_domain": {}, "by_source": {}}
    
    for language, books in all_books.items():
        unique = deduplicate_books(books)
        # Sort by priority (TPS + newer first)
        unique.sort(key=lambda b: -b.priority)
        
        logger.info(f"  {language.upper()}: {len(books)} raw -> {len(unique)} unique")
        
        stats["by_language"][language] = len(unique)
        final_catalog.extend(unique)
        
        for book in unique:
            stats["by_domain"][book.domain] = stats["by_domain"].get(book.domain, 0) + 1
            stats["by_source"][book.source] = stats["by_source"].get(book.source, 0) + 1
    
    # Final sort by priority
    final_catalog.sort(key=lambda b: -b.priority)
    
    # Save catalog
    catalog_data = {
        "generated": datetime.now().isoformat(),
        "total": len(final_catalog),
        "stats": stats,
        "books": [asdict(b) for b in final_catalog]
    }
    
    output_file = Path("book_catalog.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    logger.info("\n" + "=" * 70)
    logger.info("CATALOG COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total books: {len(final_catalog)}")
    
    logger.info("\nBy Language:")
    for lang, count in sorted(stats["by_language"].items(), key=lambda x: -x[1]):
        status = "✓" if count >= 500 else "✗ NEED MORE"
        logger.info(f"  {lang.upper()}: {count} {status}")
    
    logger.info("\nBy Domain:")
    for domain, count in sorted(stats["by_domain"].items(), key=lambda x: -x[1]):
        logger.info(f"  {domain}: {count}")
    
    logger.info("\nBy Source:")
    for source, count in sorted(stats["by_source"].items(), key=lambda x: -x[1]):
        logger.info(f"  {source}: {count}")
    
    logger.info(f"\nSaved to: {output_file}")


if __name__ == "__main__":
    main()
