#!/usr/bin/env python3
"""
Thorough Book Cleaner for Sensei OS
===================================

Comprehensive text cleaning:
1. Fix broken words (OCR artifacts, excessive spacing)
2. Remove irrelevant metadata/headers/footers
3. Clean special characters and symbols
4. Normalize whitespace and line breaks
5. Remove garbage text patterns
6. Validate content quality

Output: Clean, readable text ready for ML training
"""

import re
import os
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from collections import Counter
import unicodedata

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('book_cleaning.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Directories
INPUT_DIR = Path("downloaded_books/txt")
OUTPUT_DIR = Path("cleaned_books")
STATS_FILE = Path("cleaning_stats.json")

# ============================================================================
# CLEANING PATTERNS
# ============================================================================

# Metadata/header patterns to remove completely
REMOVE_PATTERNS = [
    # Government document headers
    r'REPORT\s+DOCUMENTATION\s+PAGE.*?(?=\n\n|\Z)',
    r'Form\s+Approved\s+OMB.*?(?=\n\n|\Z)',
    r'Public\s+reporting\s+burden.*?(?=\n\n|\Z)',
    r'PLEASE\s+DO\s+NOT\s+RETURN.*?(?=\n\n|\Z)',
    r'\d+[a-z]?\.\s+(CONTRACT|GRANT|PROGRAM|PROJECT|TASK|WORK\s+UNIT)\s+NUMBER',
    r'PERFORMING\s+ORG(ANIZATION)?\s+REPORT.*?NUMBER',
    r'SPONSORING\s*/?\s*MONITORING\s+AGENCY.*?(?=\n\n|\Z)',
    r'DISTRIBUTION\s*/?\s*AVAILABILITY\s+STATEMENT.*?(?=\n\n|\Z)',
    r'SUPPLEMENTARY\s+NOTES.*?(?=\n\n|\Z)',
    r'ABSTRACT.*?(?=\n\n[A-Z]|\Z)',
    r'SUBJECT\s+TERMS.*?(?=\n\n|\Z)',
    r'SECURITY\s+CLASSIFICATION.*?(?=\n\n|\Z)',
    r'LIMITATION\s+OF\s+ABSTRACT.*?(?=\n\n|\Z)',
    r'NUMBER\s+OF\s+PAGES.*?(?=\n\n|\Z)',
    r'RESPONSIBLE\s+PERSON.*?(?=\n\n|\Z)',
    
    # Project Gutenberg headers/footers
    r'\*\*\*\s*START\s+OF\s+(THE\s+)?PROJECT\s+GUTENBERG.*?\*\*\*',
    r'\*\*\*\s*END\s+OF\s+(THE\s+)?PROJECT\s+GUTENBERG.*',
    r'This\s+eBook\s+is\s+for\s+the\s+use\s+of\s+anyone.*?(?=\n\n)',
    r'Most\s+people\s+start\s+at\s+our\s+Web\s+site.*',
    r'Updated\s+editions\s+will\s+replace.*',
    r'Section\s+\d+\.\s+General\s+Terms\s+of\s+Use.*',
    r'Produced\s+by.*?(?=\n\n)',
    
    # Internet Archive metadata
    r'Internet\s+Archive.*?(?=\n\n)',
    r'Digitized\s+by.*?(?=\n\n)',
    r'This\s+is\s+a\s+digital\s+copy.*?(?=\n\n)',
    r'Original\s+from.*?(?=\n\n)',
    r'Uploaded\s+by.*?(?=\n\n)',
    
    # NASA/DTIC headers
    r'NASA\s+Technical\s+Reports\s+Server.*?(?=\n\n)',
    r'DTIC\s+[A-Z]+\d+.*?(?=\n\n)',
    r'Approved\s+for\s+public\s+release.*?(?=\n\n)',
    r'Distribution\s+is\s+unlimited.*?(?=\n\n)',
    r'UNCLASSIFIED.*?(?=\n\n)',
    
    # ERIC headers
    r'ERIC\s+[A-Z]+\d+.*?(?=\n\n)',
    r'Document\s+Resume.*?(?=\n\n)',
    r'ED\s+\d+.*?(?=\n\n)',
    
    # Conference/Symposium metadata
    r'(Proceedings|Conference|Symposium|Workshop)\s+of\s+the.*?(?=\n\n)',
    r'Managing\s+Editors?:.*?(?=\n\n)',
    r'Co-?Editors?:.*?(?=\n\n)',
    r'Technical\s+Editors?:.*?(?=\n\n)',
    r'Cover\s+Design:.*?(?=\n\n)',
    r'Executive\s+Secretary.*?(?=\n\n)',
    r'Proposal\s+Reviewers?:.*?(?=\n\n)',
    r'Technology\s+Coordinators?:.*?(?=\n\n)',
    r'Web\s+Page\s+Editors?:.*?(?=\n\n)',
    r'Graphic\s+Designer:.*?(?=\n\n)',
    r'Table\s+of\s+Contents.*?(?=\n\n[A-Z])',
    
    # Standard Form metadata
    r'Standard\s+Form\s+\d+.*?(?=\n\n)',
    r'Prescribed\s+by\s+ANSI\s+Std.*?(?=\n\n)',
    r'OMB\s+No\.\s*\d+.*?(?=\n)',
    
    # Bibliography/References sections at end (often noise)
    r'\n(BIBLIOGRAPHY|REFERENCES|WORKS\s+CITED|INITIAL\s+DISTRIBUTION\s+LIST)\s*\n.*',
    
    # Figure/Image/Table references and captions
    r'^\s*Figure\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Fig\.\s*\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Table\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Chart\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Graph\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Diagram\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Photo\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Photos?\s+\d+[\s\-]+\d*[\.\:\-].*?(?=\n\n)',
    r'^\s*Image\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Exhibit\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Illustration\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Plate\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Map\s+\d+[\.\:\-].*?(?=\n\n)',
    r'^\s*Appendix\s+[A-Z\d]+[\.\:\-].*?(?=\n\n)',
    
    # Source citations for figures
    r'^\s*Source\s*:\s*(Figure|Table|Chart|Graph|Photo|Image).*?(?=\n)',
    r'^\s*Source\s*:\s*(Author|Toyota|Company|adapted|based).*?(?=\n)',
    
    # List of figures/tables/illustrations
    r'\n(LIST\s+OF\s+)?(FIGURES|TABLES|ILLUSTRATIONS|CHARTS|GRAPHS|PHOTOS|IMAGES|EXHIBITS|PLATES|MAPS)\s*\n.*?(?=\n[A-Z]{2,}|\Z)',
    
    # Generic document metadata
    r'DATES?\s+COVERED.*?(?=\n)',
    r'REPORT\s+TYPE.*?(?=\n)',
    r'REPORT\s+DATE.*?(?=\n)',
    r'TITLE\s+AND\s+SUBTITLE.*?(?=\n)',
    r'AUTHOR\(S\).*?(?=\n)',
    r'PERFORMING\s+ORGANIZATION.*?(?=\n)',
    r'ADDRESS\(ES\).*?(?=\n)',
    
    # Page numbers and headers
    r'^\s*-?\s*\d+\s*-?\s*$',
    r'^\s*Page\s+\d+\s*(of\s+\d+)?\s*$',
    r'^\s*\[\s*\d+\s*\]\s*$',
]

# Garbage text patterns (lines to remove)
GARBAGE_LINE_PATTERNS = [
    r'^[_\-=\*~]{5,}$',  # Separator lines
    r'^[\s\d\.\-\/]+$',  # Only numbers/punctuation
    r'^[A-Z\s\d\.\-]{1,10}$',  # Short uppercase codes
    r'^\s*\d+[a-z]?\.\s*$',  # Numbered list items alone
    r'^\s*[ivxlcdm]+\s*$',  # Roman numerals alone
    r'^\s*\[[^\]]*\]\s*$',  # Bracketed references alone
    r'^\s*\([^\)]*\)\s*$',  # Parenthetical alone if short
    r'^(continued|cont\'?d?)\s*$',
    r'^\s*(see|ref|note|ibid|op\.?\s*cit)\.?\s*$',
    # Form fields
    r'^\s*\d+[a-z]?\.\s+(CONTRACT|GRANT|PROGRAM|PROJECT|TASK|REPORT|WORK)\s*(NUMBER|TYPE|DATE)?:?\s*$',
    r'^\s*(NAME|ADDRESS|PHONE|FAX|EMAIL|TITLE|DATE|NUMBER|CODE)\s*[\(\[]?S?\s*[\)\]]?\s*:?\s*$',
    # Copyright/legal
    r'^\s*[©\(C\)]\s*(Copyright)?\s*\d{4}.*$',
    r'^\s*All\s+rights\s+reserved\.?\s*$',
    # Page markers
    r'^\s*-+\s*\d+\s*-+\s*$',
    r'^\s*\|\s*\d+\s*\|\s*$',
    
    # Figure/Image/Table references - remove entirely
    r'^\s*Fig(?:ure)?\.?\s*\d+[\.\:\-\s]',
    r'^\s*Table\s*\d+[\.\:\-\s]',
    r'^\s*Chart\s*\d+[\.\:\-\s]',
    r'^\s*Graph\s*\d+[\.\:\-\s]',
    r'^\s*Diagram\s*\d+[\.\:\-\s]',
    r'^\s*Photo(?:graph)?s?\s*\d+[\.\:\-\s]',
    r'^\s*Image\s*\d+[\.\:\-\s]',
    r'^\s*Exhibit\s*\d+[\.\:\-\s]',
    r'^\s*Illustration\s*\d+[\.\:\-\s]',
    r'^\s*Plate\s*\d+[\.\:\-\s]',
    r'^\s*Map\s*\d+[\.\:\-\s]',
    r'^\s*Appendix\s+[A-Z\d]+[\.\:\-\s]',
    
    # See Figure/Table/etc references
    r'^\s*\(?[Ss]ee\s+(Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Appendix)s?\s*[\d\.\,\s\-]+\)?\.?\s*$',
    r'^\s*\[?[Ss]ee\s+(above|below|following|preceding)\s+(fig(?:ure)?|table|chart|graph|diagram|photo|image|illustration)\]?\.?\s*$',
    
    # Figure/Table captions and sources
    r'^\s*Source\s*:\s*.+',
    r'^\s*Note\s*:\s*(Data|Figures?|Based|Adapted|From).+',
    r'^\s*\(Source\s*:.+\)\s*$',
    r'^\s*Adapted\s+from\s+.+$',
    r'^\s*Based\s+on\s+data\s+from\s+.+$',
    
    # "As shown in Figure X" patterns - keep sentence but mark for later
    r'^\s*\(?\s*(As\s+)?(shown|illustrated|depicted|displayed|presented|seen)\s+in\s+(Fig(?:ure)?|Table|Chart|Graph|Diagram)\s*\d+\s*\)?\.?\s*$',
]

# Repeating header/footer patterns (titles that appear on multiple pages)
REPEATING_CONTENT_PATTERNS = [
    # Conference/symposium headers
    r'^\s*(proceedings|symposium|conference|workshop)\s+(of|on)?\s*',
    r'^\s*\d{1,2}(st|nd|rd|th)?\s+(annual|international|national)\s+',
    # Common page headers
    r'^\s*(chapter|section|part)\s+\d+\s*:?\s*$',
    # Publisher footers
    r'^\s*(printed|published|produced)\s+(by|in|at)\s+',
    # Academic headers
    r'^\s*(university|college|institute)\s+(of|for)\s+',
]

# OCR artifact patterns - will be applied via word dictionary
OCR_FIXES = [
    # Fix common OCR errors
    (r'(\w)- +(\w)', r'\1\2'),  # Hyphenated word breaks: "manu- facturing" -> "manufacturing"
    (r'(\w) {2,}(\w)', r'\1 \2'),  # Multiple spaces: "lean  manufacturing" -> "lean manufacturing"
    (r'vv', 'w'),  # vv -> w
    (r'VV', 'W'),  # VV -> W
]

# Common OCR word corrections (scanned documents often have l/i confusion)
OCR_WORD_FIXES = {
    # l -> i corrections (very common in scanned docs)
    'facuity': 'faculty',
    'abiiity': 'ability',
    'utiiize': 'utilize',
    'utiiized': 'utilized',
    'utiiizing': 'utilizing',
    'simiiar': 'similar',
    'simiiarity': 'similarity',
    'appiication': 'application',
    'appiied': 'applied',
    'appiy': 'apply',
    'appiyng': 'applying',
    'principies': 'principles',
    'principie': 'principle',
    'efficiences': 'efficiencies',
    'efficieny': 'efficiency',
    'abiiities': 'abilities',
    'possibie': 'possible',
    'possibiy': 'possibly',
    'avaiiabie': 'available',
    'reiiabiiity': 'reliability',
    'reiiable': 'reliable',
    'quaiity': 'quality',
    'quaiification': 'qualification',
    'speciai': 'special',
    'speciaiy': 'specially',
    'miiitary': 'military',
    'civiian': 'civilian',
    'expiains': 'explains',
    'expiain': 'explain',
    'exampies': 'examples',
    'exampie': 'example',
    'iiiustrates': 'illustrates',
    'iiiustrate': 'illustrate',
    'inciude': 'include',
    'inciudes': 'includes',
    'inciuding': 'including',
    'coilege': 'college',
    'fuifiilment': 'fulfillment',
    'fulfiilment': 'fulfillment',
    'knoxviile': 'knoxville',
    'okiahoma': 'oklahoma',
    'siil': 'sill',
    'iast': 'last',
    'finaiiy': 'finally',
    'finai': 'final',
    'originai': 'original',
    'criticai': 'critical',
    'traditionai': 'traditional',
    'nationai': 'national',
    'internationai': 'international',
    'industriai': 'industrial',
    'technicai': 'technical',
    'practicai': 'practical',
    'essentiai': 'essential',
    'potentiai': 'potential',
    'materiai': 'material',
    'materiais': 'materials',
    'professionai': 'professional',
    'additionai': 'additional',
    'individuai': 'individual',
    'functionai': 'functional',
    'operationai': 'operational',
    'organizationai': 'organizational',
    'environmentai': 'environmental',
    'experimentai': 'experimental',
    'fundamentai': 'fundamental',
    'governmentai': 'governmental',
    'institutionai': 'institutional',
    'internationai': 'international',
    'developmentai': 'developmental',
    'structurai': 'structural',
    'financiai': 'financial',
    'physicai': 'physical',
    'chemicai': 'chemical',
    'biologicai': 'biological',
    'psychologicai': 'psychological',
    'sociologicai': 'sociological',
    'historicai': 'historical',
    'theoreticai': 'theoretical',
    'analyticai': 'analytical',
    'statisticai': 'statistical',
    'mathematicai': 'mathematical',
    'commerciai': 'commercial',
    'universai': 'universal',
    'generai': 'general',
    'federai': 'federal',
    'iocai': 'local',
    'globai': 'global',
    'totai': 'total',
    'initiai': 'initial',
    'usuai': 'usual',
    'visuai': 'visual',
    'manuai': 'manual',
    'annuai': 'annual',
    'virtuai': 'virtual',
    'mutuai': 'mutual',
    'actuai': 'actual',
    'eventuai': 'eventual',
    'graduai': 'gradual',
    'sexuai': 'sexual',
    'textuai': 'textual',
    'habituai': 'habitual',
    'spirituai': 'spiritual',
    'intellectuai': 'intellectual',
    'conceptuai': 'conceptual',
    'contextuai': 'contextual',
    'contractuai': 'contractual',
    'resuitant': 'resultant',
    'resuit': 'result',
    'resuits': 'results',
    'detaii': 'detail',
    'detaiis': 'details',
    'detaiied': 'detailed',
    'retaii': 'retail',
    'faiiure': 'failure',
    'faiiures': 'failures',
    'vaiue': 'value',
    'vaiues': 'values',
    'vaiuable': 'valuable',
    'evaiuate': 'evaluate',
    'evaiuation': 'evaluation',
    'eiiminate': 'eliminate',
    'eiimination': 'elimination',
    'eiiminated': 'eliminated',
    'simiiar': 'similar',
    'simiiarity': 'similarity',
    'famiiy': 'family',
    'famiiiar': 'familiar',
    'deiiver': 'deliver',
    'deiivery': 'delivery',
    'deiivered': 'delivered',
    'beiieve': 'believe',
    'beiief': 'belief',
    'reiiabiiity': 'reliability',
    'capabiilty': 'capability',
    'capabiilties': 'capabilities',
    'responsibiilty': 'responsibility',
    'responsibiilties': 'responsibilities',
    'visibiiity': 'visibility',
    'flexibiiity': 'flexibility',
    'stabiiity': 'stability',
    'probabiiity': 'probability',
    'avaiiabiiity': 'availability',
    'sustainabiiity': 'sustainability',
    'accountabiiity': 'accountability',
    'traceabiiity': 'traceability',
    'repeatability': 'repeatability',
    'profitabiiity': 'profitability',
    'compatibiilty': 'compatibility',
    'accessibiiity': 'accessibility',
    # Common double-l to ll
    'wiii': 'will',
    'stiii': 'still',
    'skiii': 'skill',
    'skiils': 'skills',
    'biii': 'bill',
    'fiil': 'fill',
    'kiii': 'kill',
    'miii': 'mill',
    'piii': 'pill',
    'tiil': 'till',
    'driil': 'drill',
    'griil': 'grill',
    'chiil': 'chill',
    'spiil': 'spill',
    'thriil': 'thrill',
    'fuifiii': 'fulfill',
    'instaii': 'install',
    'overaii': 'overall',
    'smaii': 'small',
    'caii': 'call',
    'faii': 'fall',
    'taii': 'tall',
    'waii': 'wall',
    'baii': 'ball',
    'haii': 'hall',
    'maii': 'mall',
}

# Unicode normalization and replacement
UNICODE_REPLACEMENTS = {
    '\u2018': "'",  # Left single quote
    '\u2019': "'",  # Right single quote
    '\u201c': '"',  # Left double quote
    '\u201d': '"',  # Right double quote
    '\u2013': '-',  # En dash
    '\u2014': '-',  # Em dash
    '\u2026': '...',  # Ellipsis
    '\u00a0': ' ',  # Non-breaking space
    '\u00ad': '',   # Soft hyphen
    '\ufeff': '',   # BOM
    '\u200b': '',   # Zero-width space
    '\u200c': '',   # Zero-width non-joiner
    '\u200d': '',   # Zero-width joiner
    '\u2028': '\n', # Line separator
    '\u2029': '\n', # Paragraph separator
    '\uf0b7': '*',  # Bullet point
    '\uf0a7': '*',  # Another bullet
    '\u2022': '*',  # Bullet
    '\u2023': '*',  # Triangular bullet
    '\u25cf': '*',  # Black circle
    '\u25e6': '*',  # White bullet
    '\u00b7': '*',  # Middle dot
    '\u00b0': ' degrees ',  # Degree symbol
    '\u00ae': '(R)',  # Registered
    '\u00a9': '(C)',  # Copyright
    '\u2122': '(TM)',  # Trademark
    '\u00bc': '1/4',
    '\u00bd': '1/2',
    '\u00be': '3/4',
}

# ============================================================================
# CLEANER CLASS
# ============================================================================

class ThoroughBookCleaner:
    """Comprehensive book text cleaner."""
    
    def __init__(self):
        self.stats = {
            "total_processed": 0,
            "total_cleaned": 0,
            "total_rejected": 0,
            "bytes_removed": 0,
            "by_language": {},
            "cleaning_details": []
        }
        
        # Compile regex patterns
        self.remove_patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE | re.DOTALL) 
                               for p in REMOVE_PATTERNS]
        self.garbage_patterns = [re.compile(p, re.IGNORECASE) for p in GARBAGE_LINE_PATTERNS]
        self.ocr_fixes = [(re.compile(p), r) for p, r in OCR_FIXES]
    
    def normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters."""
        # Apply replacements
        for old, new in UNICODE_REPLACEMENTS.items():
            text = text.replace(old, new)
        
        # Normalize to NFC form
        text = unicodedata.normalize('NFC', text)
        
        # Remove control characters except newlines and tabs
        text = ''.join(c for c in text if c in '\n\t' or not unicodedata.category(c).startswith('C'))
        
        return text
    
    def remove_metadata(self, text: str) -> str:
        """Remove document metadata and headers."""
        for pattern in self.remove_patterns:
            text = pattern.sub('', text)
        return text
    
    def fix_ocr_artifacts(self, text: str) -> str:
        """Fix common OCR errors."""
        for pattern, replacement in self.ocr_fixes:
            text = pattern.sub(replacement, text)
        return text
    
    def fix_ocr_words(self, text: str) -> str:
        """Fix common OCR word errors using dictionary."""
        # Split into words, fix each, rejoin
        words = text.split()
        fixed_words = []
        
        for word in words:
            # Preserve punctuation
            prefix = ''
            suffix = ''
            
            # Extract leading punctuation
            while word and not word[0].isalnum():
                prefix += word[0]
                word = word[1:]
            
            # Extract trailing punctuation
            while word and not word[-1].isalnum():
                suffix = word[-1] + suffix
                word = word[:-1]
            
            # Check lowercase version in dictionary
            word_lower = word.lower()
            if word_lower in OCR_WORD_FIXES:
                fixed = OCR_WORD_FIXES[word_lower]
                # Preserve original case pattern
                if word.isupper():
                    fixed = fixed.upper()
                elif word[0].isupper() if word else False:
                    fixed = fixed.capitalize()
                word = fixed
            
            fixed_words.append(prefix + word + suffix)
        
        return ' '.join(fixed_words)
    
    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace and line breaks."""
        # Convert tabs to spaces
        text = text.replace('\t', ' ')
        
        # Fix excessive spacing within lines (OCR artifact)
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Collapse multiple spaces to single space
            line = re.sub(r' {2,}', ' ', line)
            # Strip leading/trailing whitespace
            line = line.strip()
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Normalize paragraph breaks (2+ newlines -> 2 newlines)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def remove_garbage_lines(self, text: str) -> str:
        """Remove lines that are garbage/noise."""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Skip empty lines (will be handled later)
            if not line.strip():
                cleaned_lines.append(line)
                continue
            
            # Check against garbage patterns
            is_garbage = False
            for pattern in self.garbage_patterns:
                if pattern.match(line.strip()):
                    is_garbage = True
                    break
            
            # Check if line is too short to be meaningful (unless part of a list)
            if len(line.strip()) < 3 and not re.match(r'^[\d\.\-\*\•]', line.strip()):
                is_garbage = True
            
            # Check for lines that are mostly non-alphanumeric
            alpha_ratio = sum(c.isalnum() for c in line) / max(len(line), 1)
            if alpha_ratio < 0.3 and len(line) > 10:
                is_garbage = True
            
            if not is_garbage:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def fix_broken_words(self, text: str) -> str:
        """Fix words broken across lines (hyphenation)."""
        # Fix end-of-line hyphenation
        text = re.sub(r'(\w)-\n(\w)', r'\1\2', text)
        
        # Fix hyphenation with spaces
        text = re.sub(r'(\w)-\s+\n\s*(\w)', r'\1\2', text)
        
        return text
    
    def merge_short_lines(self, text: str) -> str:
        """Merge short lines that were broken by OCR/formatting, preserving paragraph structure."""
        lines = text.split('\n')
        merged = []
        current_paragraph = []
        
        for line in lines:
            stripped = line.strip()
            
            # Empty line = paragraph break
            if not stripped:
                if current_paragraph:
                    merged.append(' '.join(current_paragraph))
                    current_paragraph = []
                continue
            
            # Check if line is likely a heading (short, possibly caps)
            is_heading = (
                len(stripped) < 80 and
                (stripped.isupper() or 
                 stripped.endswith(':') or
                 re.match(r'^(Chapter|Section|Part|CHAPTER|SECTION|PART)\s+\d+', stripped) or
                 re.match(r'^\d+\.\s+[A-Z]', stripped))
            )
            
            if is_heading:
                if current_paragraph:
                    merged.append(' '.join(current_paragraph))
                    current_paragraph = []
                merged.append(stripped)
            else:
                current_paragraph.append(stripped)
                
                # If line ends with sentence-ending punctuation and is reasonably long,
                # consider it end of paragraph
                if len(stripped) > 100 and stripped[-1] in '.!?':
                    merged.append(' '.join(current_paragraph))
                    current_paragraph = []
        
        # Don't forget last paragraph
        if current_paragraph:
            merged.append(' '.join(current_paragraph))
        
        # Join with double newlines for paragraph separation
        result = '\n\n'.join(p for p in merged if p)
        
        # Ensure we don't have overly long single paragraphs
        # Split any paragraph > 2000 chars on sentence boundaries
        final_paragraphs = []
        for para in result.split('\n\n'):
            if len(para) > 2000:
                # Split on sentence boundaries
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current = []
                current_len = 0
                for sent in sentences:
                    if current_len + len(sent) > 1500 and current:
                        final_paragraphs.append(' '.join(current))
                        current = [sent]
                        current_len = len(sent)
                    else:
                        current.append(sent)
                        current_len += len(sent)
                if current:
                    final_paragraphs.append(' '.join(current))
            else:
                final_paragraphs.append(para)
        
        return '\n\n'.join(final_paragraphs)
    
    def extract_main_content(self, text: str) -> str:
        """Extract main content body, removing front/back matter."""
        lines = text.split('\n')
        
        # Find where actual content starts (after table of contents, preface, etc.)
        content_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip().lower()
            # Skip initial metadata, TOC, preface markers
            if any(marker in stripped for marker in [
                'table of contents', 'contents', 'preface', 'foreword',
                'acknowledgments', 'acknowledgements', 'dedication',
                'list of figures', 'list of tables', 'abstract'
            ]):
                # Content likely starts a bit after this
                content_start = max(content_start, i + 1)
            
            # Look for chapter 1, introduction, or first numbered section
            if re.match(r'^(chapter\s+1|introduction|1\.\s+introduction|1\.\s+\w)', stripped):
                content_start = i
                break
        
        # Find where actual content ends (before bibliography, appendix, index)
        content_end = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            stripped = lines[i].strip().lower()
            if any(marker in stripped for marker in [
                'bibliography', 'references', 'works cited', 'index',
                'appendix', 'initial distribution', 'distribution list'
            ]):
                # Only if this looks like a section header
                if len(stripped) < 50:
                    content_end = i
                    break
        
        # Extract main content
        if content_start < content_end:
            return '\n'.join(lines[content_start:content_end])
        
        return text  # Return original if can't find boundaries
    
    def remove_repeated_content(self, text: str) -> str:
        """Remove content that repeats too often (headers/footers/titles)."""
        lines = text.split('\n')
        line_counts = Counter(line.strip() for line in lines if line.strip())
        
        # Find lines that repeat too often (likely headers/footers)
        total_lines = len([l for l in lines if l.strip()])
        threshold = max(2, total_lines // 50)  # If appears more than ~2% or 2+ times
        
        repeated = set()
        for line, count in line_counts.items():
            # Must appear multiple times and be short enough to be a header
            if count >= threshold and 5 < len(line) < 150:
                # Exclude likely legitimate repeated content
                if not any(word in line.lower() for word in ['the', 'and', 'is', 'are', 'was', 'were']):
                    repeated.add(line)
                elif count >= 4:  # If appears 4+ times, remove anyway
                    repeated.add(line)
        
        # Detect partial repeating patterns (titles with page numbers, dates, etc.)
        partial_repeats = set()
        for line in line_counts:
            if line_counts[line] >= 2 and len(line) > 15:
                # Remove numbers, punctuation to get base pattern
                base = re.sub(r'[\d\.\-\/\:\,]+', '', line).strip()
                if base and len(base) > 10:
                    # Count how many lines match this base pattern
                    base_count = sum(1 for l in lines 
                                    if re.sub(r'[\d\.\-\/\:\,]+', '', l.strip()).strip() == base)
                    if base_count >= 3:
                        partial_repeats.add(base)
        
        # Common header/footer phrases to always remove when repeated
        common_headers = [
            'symposium proceedings', 'conference proceedings', 'proceedings of',
            'all rights reserved', 'copyright', '© ', 'page ', 'table of contents',
        ]
        
        # Remove repeated lines
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            
            # Skip if exact match to repeated
            if stripped in repeated:
                continue
            
            # Skip if matches partial repeat pattern  
            base = re.sub(r'[\d\.\-\/\:\,]+', '', stripped).strip()
            if base in partial_repeats:
                continue
            
            # Skip common repeated headers
            stripped_lower = stripped.lower()
            if any(header in stripped_lower for header in common_headers):
                if line_counts.get(stripped, 0) >= 2:
                    continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def remove_document_metadata(self, text: str) -> str:
        """Remove form-like document metadata sections."""
        lines = text.split('\n')
        cleaned_lines = []
        skip_until_content = False
        form_field_count = 0
        
        # Patterns indicating form fields
        form_patterns = [
            r'^\s*\d+[a-z]?\.\s+[A-Z\s]+:?\s*$',  # "1. REPORT DATE"
            r'^\s*[A-Z][A-Z\s]{2,}:\s*$',  # "TITLE AND SUBTITLE:"
            r'^\s*(N/?A|TBD|None|See\s+above)\s*$',  # Empty field values
            r'^\s*\d+[a-z]?\.\s*$',  # Just numbers
            r'^\s*(Standard\s+Form|SF|DD\s+Form)\s+\d+',  # Form references
        ]
        form_re = [re.compile(p, re.IGNORECASE) for p in form_patterns]
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Check if this looks like a form field
            is_form_field = any(p.match(stripped) for p in form_re)
            
            if is_form_field:
                form_field_count += 1
                # If we've seen many form fields in a row, we're in a form section
                if form_field_count >= 3:
                    skip_until_content = True
                continue
            
            # Reset if we hit real content
            if len(stripped) > 50 and stripped[0].isupper() and '.' in stripped:
                skip_until_content = False
                form_field_count = 0
            
            if not skip_until_content:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def remove_figure_references(self, text: str) -> str:
        """Remove all references to figures, images, tables, graphs, etc."""
        # Patterns to remove entirely (standalone references)
        standalone_patterns = [
            # Full figure captions
            r'^\s*Figure\s+\d+[\.\:\-\s].*$',
            r'^\s*Fig\.\s*\d+[\.\:\-\s].*$',
            r'^\s*TABLE\s+\d+[\.\:\-\s].*$',
            r'^\s*Table\s+\d+[\.\:\-\s].*$',
            r'^\s*Chart\s+\d+[\.\:\-\s].*$',
            r'^\s*CHART\s+\d+[\.\:\-\s].*$',
            r'^\s*Graph\s+\d+[\.\:\-\s].*$',
            r'^\s*GRAPH\s+\d+[\.\:\-\s].*$',
            r'^\s*Diagram\s+\d+[\.\:\-\s].*$',
            r'^\s*Photo\s+\d+[\.\:\-\s].*$',
            r'^\s*Image\s+\d+[\.\:\-\s].*$',
            r'^\s*Exhibit\s+\d+[\.\:\-\s].*$',
            r'^\s*EXHIBIT\s+\d+[\.\:\-\s].*$',
            r'^\s*Illustration\s+\d+[\.\:\-\s].*$',
            r'^\s*Plate\s+\d+[\.\:\-\s].*$',
            r'^\s*Map\s+\d+[\.\:\-\s].*$',
            
            # "See Figure X" style
            r'^\s*\(?\s*[Ss]ee\s+(Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Illustration|Plate|Map|Appendix)[s]?\s*[\d\.\,\-\s]+\s*\)?\.?\s*$',
            
            # Source citations
            r'^\s*Source\s*:\s*.+$',
            r'^\s*Note\s*:\s*(Data|Figures?|Based|Adapted|From).+$',
            r'^\s*\(Source\s*:.+\)\s*$',
            
            # List of figures/tables headers
            r'^\s*LIST\s+OF\s+(FIGURES|TABLES|ILLUSTRATIONS|CHARTS|GRAPHS|EXHIBITS|PLATES|MAPS)\s*$',
            r'^\s*List\s+of\s+(Figures|Tables|Illustrations|Charts|Graphs|Exhibits|Plates|Maps)\s*$',
        ]
        
        # Compile patterns
        compiled_patterns = [re.compile(p, re.MULTILINE | re.IGNORECASE) for p in standalone_patterns]
        
        # Remove standalone lines matching patterns
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            should_remove = False
            for pattern in compiled_patterns:
                if pattern.match(line.strip()):
                    should_remove = True
                    break
            if not should_remove:
                cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Remove inline references within sentences
        inline_patterns = [
            # "(see Figure 1)" or "(Figure 1)" or "(see Fig. 1)"
            r'\s*\([Ss]ee\s+(Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Illustration|Plate|Map|Appendix)[s]?\s*[\d\.\,\-\s\&and]+\)',
            r'\s*\((Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Illustration|Plate|Map|Appendix)[s]?\s*[\d\.\,\-\s\&and]+\)',
            
            # "[see Figure 1]" or "[Figure 1]"
            r'\s*\[[Ss]ee\s+(Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Illustration|Plate|Map|Appendix)[s]?\s*[\d\.\,\-\s\&and]+\]',
            r'\s*\[(Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Illustration|Plate|Map|Appendix)[s]?\s*[\d\.\,\-\s\&and]+\]',
            
            # "as shown in Figure 1" or "see Figure 1"
            r',?\s*as\s+(shown|illustrated|depicted|displayed|presented|seen)\s+in\s+(Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Illustration|Plate|Map|Appendix)[s]?\s*[\d\.\,\-\s\&and]+',
            r',?\s*[Ss]ee\s+(Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Illustration|Plate|Map|Appendix)[s]?\s*[\d\.\,\-\s\&and]+',
            
            # "(above)", "(below)", "(on the following page)", "(opposite)" for figures
            r'\s*\((above|below|on\s+the\s+(following|next|previous|opposite)\s+(page|figure|table|chart))\)',
            r'\s*\[(above|below|on\s+the\s+(following|next|previous|opposite)\s+(page|figure|table|chart))\]',
            
            # "in the figure above/below"
            r',?\s*in\s+the\s+(figure|table|chart|graph|diagram|photo|image|illustration)\s+(above|below|on\s+the\s+(left|right))',
            
            # Trailing figure refs: ", Figure 1" or "; see Table 2"
            r'[,;]\s*(Fig(?:ure)?|Table|Chart|Graph|Diagram|Photo|Image|Exhibit|Illustration|Plate|Map)[s]?\s*[\d\.\,\-\s\&and]+(?=[\.\,\;\)]|$)',
        ]
        
        for pattern in inline_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up any double punctuation or spacing artifacts
        text = re.sub(r'\s*,\s*,', ',', text)
        text = re.sub(r'\s*\.\s*\.', '.', text)
        text = re.sub(r'\s{2,}', ' ', text)
        text = re.sub(r'\(\s*\)', '', text)  # Empty parentheses
        text = re.sub(r'\[\s*\]', '', text)  # Empty brackets
        
        return text
    
    def validate_content(self, text: str) -> Tuple[bool, str]:
        """Validate that cleaned text is useful."""
        # Minimum length
        if len(text) < 1000:
            return False, "Too short (< 1000 chars)"
        
        # Check word count
        words = text.split()
        if len(words) < 200:
            return False, f"Too few words ({len(words)})"
        
        # Check for minimum sentence structure
        sentences = re.split(r'[.!?]+', text)
        valid_sentences = [s for s in sentences if len(s.split()) >= 5]
        if len(valid_sentences) < 10:
            return False, f"Too few valid sentences ({len(valid_sentences)})"
        
        # Check that it's not mostly garbage
        alpha_chars = sum(c.isalpha() for c in text)
        total_chars = len(text)
        if alpha_chars / max(total_chars, 1) < 0.5:
            return False, f"Low alpha ratio ({alpha_chars/total_chars:.2f})"
        
        # Check for reasonable vocabulary
        unique_words = set(w.lower() for w in words if w.isalpha())
        if len(unique_words) < 100:
            return False, f"Low vocabulary ({len(unique_words)} unique words)"
        
        return True, "OK"
    
    def clean_book(self, filepath: Path) -> Optional[Tuple[str, Dict]]:
        """Clean a single book file."""
        try:
            # Read file
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                original_text = f.read()
            
            original_size = len(original_text)
            
            # Apply cleaning pipeline
            text = original_text
            text = self.normalize_unicode(text)
            text = self.remove_metadata(text)
            text = self.remove_document_metadata(text)  # Remove form-like sections
            text = self.fix_broken_words(text)
            text = self.fix_ocr_artifacts(text)
            text = self.fix_ocr_words(text)  # Fix common OCR word errors
            text = self.normalize_whitespace(text)
            text = self.remove_garbage_lines(text)
            text = self.remove_repeated_content(text)  # Remove repeating titles/headers
            text = self.remove_figure_references(text)  # Remove ALL figure/image/table references
            text = self.extract_main_content(text)  # Extract main body content
            text = self.merge_short_lines(text)
            
            # Final whitespace cleanup
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = text.strip()
            
            # Validate
            is_valid, reason = self.validate_content(text)
            
            cleaned_size = len(text)
            reduction = (original_size - cleaned_size) / max(original_size, 1) * 100
            
            details = {
                "file": filepath.name,
                "original_size": original_size,
                "cleaned_size": cleaned_size,
                "reduction_pct": round(reduction, 1),
                "valid": is_valid,
                "reason": reason
            }
            
            if is_valid:
                return text, details
            else:
                return None, details
                
        except Exception as e:
            return None, {"file": filepath.name, "error": str(e)}
    
    def clean_all_books(self):
        """Clean all downloaded books."""
        logger.info("=" * 70)
        logger.info("THOROUGH BOOK CLEANING")
        logger.info("=" * 70)
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        if not INPUT_DIR.exists():
            logger.error(f"Input directory not found: {INPUT_DIR}")
            return
        
        book_files = list(INPUT_DIR.glob("*.txt"))
        logger.info(f"Found {len(book_files)} book files to clean")
        
        for i, filepath in enumerate(book_files, 1):
            self.stats["total_processed"] += 1
            
            # Infer language from filename
            lang = "en"
            if filepath.name.startswith("es_"):
                lang = "es"
            elif filepath.name.startswith("fr_"):
                lang = "fr"
            elif filepath.name.startswith("de_"):
                lang = "de"
            elif filepath.name.startswith("ar_"):
                lang = "ar"
            
            result = self.clean_book(filepath)
            
            if result[0]:  # Valid cleaned text
                text, details = result
                
                # Save cleaned file
                output_path = OUTPUT_DIR / filepath.name
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                self.stats["total_cleaned"] += 1
                self.stats["bytes_removed"] += details["original_size"] - details["cleaned_size"]
                self.stats["by_language"][lang] = self.stats["by_language"].get(lang, 0) + 1
                
                logger.info(f"[{i}/{len(book_files)}] ✓ {filepath.name[:50]}... "
                           f"({details['reduction_pct']:.0f}% reduced)")
            else:
                details = result[1]
                self.stats["total_rejected"] += 1
                self.stats["cleaning_details"].append(details)
                
                reason = details.get("reason", details.get("error", "Unknown"))
                logger.warning(f"[{i}/{len(book_files)}] ✗ {filepath.name[:50]}... "
                              f"REJECTED: {reason}")
        
        self._save_stats()
        self._print_summary()
    
    def _save_stats(self):
        """Save cleaning statistics."""
        with open(STATS_FILE, 'w') as f:
            json.dump(self.stats, f, indent=2)
    
    def _print_summary(self):
        """Print cleaning summary."""
        logger.info("\n" + "=" * 70)
        logger.info("CLEANING SUMMARY")
        logger.info("=" * 70)
        
        logger.info(f"\nTotal processed: {self.stats['total_processed']}")
        logger.info(f"Successfully cleaned: {self.stats['total_cleaned']}")
        logger.info(f"Rejected: {self.stats['total_rejected']}")
        logger.info(f"Bytes removed: {self.stats['bytes_removed']:,}")
        
        logger.info("\nBy Language:")
        for lang, count in sorted(self.stats["by_language"].items(), key=lambda x: -x[1]):
            logger.info(f"  {lang.upper()}: {count}")


def main():
    cleaner = ThoroughBookCleaner()
    cleaner.clean_all_books()


if __name__ == "__main__":
    main()
