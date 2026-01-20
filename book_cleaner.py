#!/usr/bin/env python3
"""
Book Cleaner - Validates and cleans downloaded books.

Removes:
- HTML pages (failed downloads)
- Files that are too small
- Files with mostly non-text content
- Duplicate content

Cleans:
- Gutenberg headers/footers
- OCR artifacts
- Excessive whitespace
"""

import os
import re
import hashlib
from pathlib import Path
from typing import Set, Tuple, List
from collections import defaultdict

BOOKS_DIR = Path("downloaded_books/txt")
CLEANED_DIR = Path("downloaded_books/cleaned")
REJECTED_DIR = Path("downloaded_books/rejected")

# Minimum file size (bytes)
MIN_FILE_SIZE = 5000  # 5KB

# Minimum word count
MIN_WORD_COUNT = 500

# Maximum ratio of non-alpha chars
MAX_NOISE_RATIO = 0.5


def is_html(content: str) -> bool:
    """Check if content is HTML."""
    html_patterns = [
        r'<!DOCTYPE',
        r'<html',
        r'<HTML',
        r'<head>',
        r'<body>',
        r'<div ',
        r'<script',
    ]
    first_1000 = content[:1000].lower()
    return any(p.lower() in first_1000 for p in html_patterns)


def is_binary_or_garbage(content: str) -> bool:
    """Check if content is binary or garbage."""
    sample = content[:5000]
    
    # Count printable vs non-printable
    printable = sum(1 for c in sample if c.isprintable() or c in '\n\r\t')
    total = len(sample)
    
    if total == 0:
        return True
    
    return printable / total < 0.8


def calculate_noise_ratio(content: str) -> float:
    """Calculate ratio of non-alphabetic characters."""
    sample = content[:10000]
    alpha_count = sum(1 for c in sample if c.isalpha() or c.isspace())
    return 1 - (alpha_count / max(1, len(sample)))


def clean_gutenberg(content: str) -> str:
    """Remove Gutenberg boilerplate."""
    # Remove header (everything before START marker)
    start_patterns = [
        r'\*\*\*\s*START OF TH(E|IS) PROJECT GUTENBERG.*?\*\*\*',
        r'\*\*\*\s*START OF THE PROJECT.*?\*\*\*',
        r'START OF THIS PROJECT GUTENBERG',
    ]
    
    for pattern in start_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            content = content[match.end():]
            break
    
    # Remove footer (everything after END marker)
    end_patterns = [
        r'\*\*\*\s*END OF TH(E|IS) PROJECT GUTENBERG.*',
        r'\*\*\*\s*END OF THE PROJECT.*',
        r'End of the Project Gutenberg.*',
        r'End of Project Gutenberg.*',
    ]
    
    for pattern in end_patterns:
        match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
        if match:
            content = content[:match.start()]
            break
    
    return content.strip()


def clean_ocr_artifacts(content: str) -> str:
    """Clean common OCR artifacts."""
    # Fix common OCR mistakes
    replacements = [
        (r'\s+', ' '),  # Multiple spaces to single
        (r'\n{3,}', '\n\n'),  # Multiple newlines
        (r'([a-z])-\s*\n\s*([a-z])', r'\1\2'),  # Hyphenated line breaks
        (r'\f', '\n'),  # Form feeds
        (r'[^\x00-\x7F]+', ''),  # Non-ASCII (optional, be careful with languages)
    ]
    
    for pattern, replacement in replacements[:4]:  # Skip non-ASCII removal
        content = re.sub(pattern, replacement, content)
    
    return content


def get_content_hash(content: str) -> str:
    """Get hash of content for deduplication."""
    # Normalize and hash
    normalized = re.sub(r'\s+', ' ', content[:10000].lower())
    return hashlib.md5(normalized.encode()).hexdigest()


def validate_and_clean_file(filepath: Path) -> Tuple[bool, str, str]:
    """
    Validate and clean a single file.
    
    Returns:
        (is_valid, reason, cleaned_content or None)
    """
    try:
        # Check file size
        if filepath.stat().st_size < MIN_FILE_SIZE:
            return False, "File too small", ""
        
        # Read content
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check for HTML
        if is_html(content):
            return False, "HTML content detected", ""
        
        # Check for binary/garbage
        if is_binary_or_garbage(content):
            return False, "Binary or garbage content", ""
        
        # Clean content
        cleaned = clean_gutenberg(content)
        cleaned = clean_ocr_artifacts(cleaned)
        
        # Check word count
        word_count = len(cleaned.split())
        if word_count < MIN_WORD_COUNT:
            return False, f"Too few words ({word_count})", ""
        
        # Check noise ratio
        noise = calculate_noise_ratio(cleaned)
        if noise > MAX_NOISE_RATIO:
            return False, f"Too noisy ({noise:.1%})", ""
        
        return True, "OK", cleaned
        
    except Exception as e:
        return False, f"Error: {e}", ""


def process_all_books():
    """Process all downloaded books."""
    print("=" * 60)
    print("BOOK CLEANER")
    print("=" * 60)
    
    if not BOOKS_DIR.exists():
        print(f"Books directory not found: {BOOKS_DIR}")
        return
    
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    
    book_files = list(BOOKS_DIR.glob("*.txt"))
    print(f"Found {len(book_files)} book files")
    
    stats = {
        "total": len(book_files),
        "valid": 0,
        "rejected": 0,
        "duplicates": 0,
        "reasons": defaultdict(int)
    }
    
    seen_hashes: Set[str] = set()
    
    for i, filepath in enumerate(book_files, 1):
        is_valid, reason, cleaned = validate_and_clean_file(filepath)
        
        if is_valid:
            # Check for duplicates
            content_hash = get_content_hash(cleaned)
            if content_hash in seen_hashes:
                stats["duplicates"] += 1
                stats["reasons"]["Duplicate content"] += 1
                # Move to rejected
                dest = REJECTED_DIR / filepath.name
                os.rename(filepath, dest)
            else:
                seen_hashes.add(content_hash)
                stats["valid"] += 1
                
                # Save cleaned version
                cleaned_path = CLEANED_DIR / filepath.name
                with open(cleaned_path, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
        else:
            stats["rejected"] += 1
            stats["reasons"][reason] += 1
            
            # Move to rejected
            dest = REJECTED_DIR / filepath.name
            try:
                os.rename(filepath, dest)
            except:
                pass
        
        if i % 20 == 0:
            print(f"  Processed {i}/{len(book_files)}...")
    
    # Print summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total files: {stats['total']}")
    print(f"Valid: {stats['valid']} ({100*stats['valid']/max(1,stats['total']):.1f}%)")
    print(f"Rejected: {stats['rejected']}")
    print(f"Duplicates: {stats['duplicates']}")
    print()
    print("Rejection reasons:")
    for reason, count in sorted(stats["reasons"].items(), key=lambda x: -x[1]):
        print(f"  {reason}: {count}")
    
    print()
    print(f"Cleaned books saved to: {CLEANED_DIR}")
    print(f"Rejected books moved to: {REJECTED_DIR}")


def quick_scan():
    """Quick scan without moving files."""
    print("=" * 60)
    print("QUICK BOOK SCAN (no changes)")
    print("=" * 60)
    
    if not BOOKS_DIR.exists():
        print(f"Books directory not found: {BOOKS_DIR}")
        return
    
    book_files = list(BOOKS_DIR.glob("*.txt"))
    print(f"Found {len(book_files)} book files")
    
    issues = {
        "html": [],
        "small": [],
        "noisy": [],
        "short": []
    }
    
    for filepath in book_files:
        try:
            size = filepath.stat().st_size
            if size < MIN_FILE_SIZE:
                issues["small"].append(filepath.name)
                continue
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if is_html(content):
                issues["html"].append(filepath.name)
                continue
            
            word_count = len(content.split())
            if word_count < MIN_WORD_COUNT:
                issues["short"].append(filepath.name)
                continue
            
            noise = calculate_noise_ratio(content)
            if noise > MAX_NOISE_RATIO:
                issues["noisy"].append(filepath.name)
        except:
            pass
    
    total_issues = sum(len(v) for v in issues.values())
    clean_count = len(book_files) - total_issues
    
    print()
    print(f"Clean books: {clean_count} ({100*clean_count/max(1,len(book_files)):.1f}%)")
    print(f"Problematic: {total_issues}")
    print()
    
    if issues["html"]:
        print(f"HTML files ({len(issues['html'])}): {issues['html'][:3]}...")
    if issues["small"]:
        print(f"Too small ({len(issues['small'])}): {issues['small'][:3]}...")
    if issues["short"]:
        print(f"Too short ({len(issues['short'])}): {issues['short'][:3]}...")
    if issues["noisy"]:
        print(f"Too noisy ({len(issues['noisy'])}): {issues['noisy'][:3]}...")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        quick_scan()
    else:
        process_all_books()
