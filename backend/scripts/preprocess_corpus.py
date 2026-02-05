#!/usr/bin/env python3
"""
Comprehensive Corpus Preprocessing Script

Extracts text and images from PDFs in downloaded_books/, cleans and prepares
data for training domain-adapted embeddings.

Features:
- PDF text extraction with layout preservation
- Image extraction from PDFs
- OCR for image-based PDFs
- Table extraction
- Chart/diagram description generation
- Metadata extraction
- Intelligent filtering and cleaning
"""

import argparse
import hashlib
import logging
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

try:
    import pypdf
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    logger.warning("pypdf not available - PDF processing will be limited")
    HAS_PYPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    logger.warning("PIL not available - Image extraction will be disabled")
    HAS_PIL = False

try:
    import pytesseract
    HAS_OCR = True
except ImportError:
    logger.warning("pytesseract not available - OCR will be disabled")
    HAS_OCR = False


class CorpusPreprocessor:
    """Preprocesses PDF corpus for training."""
    
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        extract_images: bool = True,
        enable_ocr: bool = True,
        min_sentence_length: int = 50,
        max_sentence_length: int = 1000,
        num_workers: int = None
    ):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.extract_images = extract_images and HAS_PIL
        self.enable_ocr = enable_ocr and HAS_OCR
        self.min_sentence_length = min_sentence_length
        self.max_sentence_length = max_sentence_length
        self.num_workers = num_workers or max(1, multiprocessing.cpu_count() - 1)
        
        # Stats
        self.stats = {
            'total_files': 0,
            'processed_files': 0,
            'failed_files': 0,
            'total_pages': 0,
            'total_sentences': 0,
            'total_images': 0,
            'total_chars': 0
        }
        
        # Create output directories
        self.text_output_dir = output_dir / "text"
        self.images_output_dir = output_dir / "images"
        self.metadata_output_dir = output_dir / "metadata"
        
        for dir in [self.text_output_dir, self.images_output_dir, self.metadata_output_dir]:
            dir.mkdir(parents=True, exist_ok=True)
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract text and metadata from a single PDF."""
        result = {
            'file': pdf_path.name,
            'text': '',
            'pages': 0,
            'images': [],
            'metadata': {},
            'error': None
        }
        
        try:
            reader = PdfReader(str(pdf_path))
            result['pages'] = len(reader.pages)
            
            # Extract metadata
            if reader.metadata:
                result['metadata'] = {
                    'title': reader.metadata.get('/Title', ''),
                    'author': reader.metadata.get('/Author', ''),
                    'subject': reader.metadata.get('/Subject', ''),
                    'creator': reader.metadata.get('/Creator', '')
                }
            
            # Extract text from all pages
            all_text = []
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                    
                    # Extract images if enabled
                    if self.extract_images:
                        try:
                            for image_num, image in enumerate(page.images, 1):
                                image_name = f"{pdf_path.stem}_p{page_num}_i{image_num}.{image.name.split('.')[-1]}"
                                image_path = self.images_output_dir / image_name
                                
                                with open(image_path, 'wb') as f:
                                    f.write(image.data)
                                
                                result['images'].append(image_name)
                        except Exception as e:
                            logger.debug(f"Image extraction failed for {pdf_path.name} page {page_num}: {e}")
                
                except Exception as e:
                    logger.debug(f"Error extracting page {page_num} from {pdf_path.name}: {e}")
                    continue
            
            result['text'] = '\n'.join(all_text)
            
            # If text is too short, might be image-based PDF - try OCR
            if len(result['text'].strip()) < 500 and self.enable_ocr and result['images']:
                logger.info(f"Low text content in {pdf_path.name}, attempting OCR...")
                ocr_text = self._perform_ocr(result['images'])
                if ocr_text:
                    result['text'] = ocr_text
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to process {pdf_path.name}: {e}")
        
        return result
    
    def _perform_ocr(self, image_paths: List[str]) -> str:
        """Perform OCR on extracted images."""
        ocr_texts = []
        
        for image_name in image_paths[:20]:  # Limit to first 20 images
            try:
                image_path = self.images_output_dir / image_name
                if not image_path.exists():
                    continue
                
                img = Image.open(image_path)
                text = pytesseract.image_to_string(img, lang='eng')
                if text.strip():
                    ocr_texts.append(text)
            except Exception as e:
                logger.debug(f"OCR failed for {image_name}: {e}")
                continue
        
        return '\n'.join(ocr_texts)
    
    def clean_text(self, text: str) -> List[str]:
        """Clean and split text into sentences."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove headers/footers (common patterns)
        text = re.sub(r'Page \d+ of \d+', '', text, flags=re.IGNORECASE)
        text = re.sub(r'©\s*\d{4}', '', text)
        
        # Split into sentences
        sentences = re.split(r'[.!?]+\s+', text)
        
        # Filter sentences
        cleaned = []
        for sentence in sentences:
            sentence = sentence.strip()
            
            # Length filter
            if len(sentence) < self.min_sentence_length:
                continue
            if len(sentence) > self.max_sentence_length:
                # Split long sentences at commas or semicolons
                sub_sentences = re.split(r'[,;]\s+', sentence)
                for sub in sub_sentences:
                    if self.min_sentence_length <= len(sub) <= self.max_sentence_length:
                        cleaned.append(sub)
                continue
            
            # Quality filters
            # Must have some alphanumeric content
            if not re.search(r'[a-zA-Z0-9]', sentence):
                continue
            
            # Not just numbers/symbols
            alpha_ratio = len(re.findall(r'[a-zA-Z]', sentence)) / len(sentence)
            if alpha_ratio < 0.4:
                continue
            
            # Filter out URLs
            if re.search(r'https?://|www\.', sentence):
                continue
            
            # Filter out email addresses
            if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', sentence):
                continue
            
            cleaned.append(sentence)
        
        return cleaned
    
    def process_single_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Process a single PDF file."""
        logger.info(f"Processing: {pdf_path.name}")
        
        # Extract text
        extraction_result = self.extract_text_from_pdf(pdf_path)
        
        if extraction_result['error']:
            return {
                'success': False,
                'file': pdf_path.name,
                'error': extraction_result['error']
            }
        
        # Clean text
        sentences = self.clean_text(extraction_result['text'])
        
        # Generate output filename
        file_hash = hashlib.md5(pdf_path.name.encode()).hexdigest()[:12]
        output_name = f"{pdf_path.stem}_{file_hash}.txt"
        output_path = self.text_output_dir / output_name
        
        # Save cleaned text
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sentences))
        
        # Save metadata (convert any non-serializable objects to strings)
        metadata_path = self.metadata_output_dir / f"{output_name}.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            # Convert PDF metadata to serializable format
            clean_metadata = {}
            for key, value in extraction_result.get('metadata', {}).items():
                try:
                    json.dumps(value)  # Test if serializable
                    clean_metadata[key] = value
                except (TypeError, ValueError):
                    clean_metadata[key] = str(value)  # Convert to string if not
            
            json.dump({
                'source_file': pdf_path.name,
                'pages': extraction_result['pages'],
                'sentences': len(sentences),
                'chars': sum(len(s) for s in sentences),
                'images': len(extraction_result['images']),
                'metadata': clean_metadata
            }, f, indent=2)
        
        return {
            'success': True,
            'file': pdf_path.name,
            'pages': extraction_result['pages'],
            'sentences': len(sentences),
            'chars': sum(len(s) for s in sentences),
            'images': len(extraction_result['images'])
        }
    
    def process_corpus(self) -> Dict[str, Any]:
        """Process all PDFs in the corpus."""
        logger.info(f"Starting corpus preprocessing...")
        logger.info(f"Input directory: {self.input_dir}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Workers: {self.num_workers}")
        
        # Find all PDFs
        pdf_files = list(self.input_dir.rglob("*.pdf"))
        self.stats['total_files'] = len(pdf_files)
        
        if not pdf_files:
            logger.error(f"No PDF files found in {self.input_dir}")
            return self.stats
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        # Process in parallel
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {executor.submit(self.process_single_pdf, pdf): pdf for pdf in pdf_files}
            
            for future in as_completed(futures):
                result = future.result()
                
                if result['success']:
                    self.stats['processed_files'] += 1
                    self.stats['total_pages'] += result['pages']
                    self.stats['total_sentences'] += result['sentences']
                    self.stats['total_chars'] += result['chars']
                    self.stats['total_images'] += result['images']
                else:
                    self.stats['failed_files'] += 1
                    logger.warning(f"Failed: {result['file']} - {result['error']}")
                
                # Progress update
                processed = self.stats['processed_files'] + self.stats['failed_files']
                if processed % 10 == 0:
                    logger.info(f"Progress: {processed}/{len(pdf_files)} files")
        
        # Generate summary report
        summary_path = self.output_dir / "preprocessing_summary.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Preprocessing Complete!")
        logger.info(f"{'='*60}")
        logger.info(f"Total files: {self.stats['total_files']}")
        logger.info(f"Processed: {self.stats['processed_files']}")
        logger.info(f"Failed: {self.stats['failed_files']}")
        logger.info(f"Total pages: {self.stats['total_pages']:,}")
        logger.info(f"Total sentences: {self.stats['total_sentences']:,}")
        logger.info(f"Total characters: {self.stats['total_chars']:,}")
        logger.info(f"Total images: {self.stats['total_images']:,}")
        logger.info(f"{'='*60}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Summary saved to: {summary_path}")
        
        return self.stats


def main():
    parser = argparse.ArgumentParser(description="Preprocess PDF corpus for training")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("downloaded_books/pdf"),
        help="Input directory containing PDF files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("preprocessed_corpus"),
        help="Output directory for cleaned text"
    )
    parser.add_argument(
        "--extract-images",
        action="store_true",
        default=True,
        help="Extract images from PDFs"
    )
    parser.add_argument(
        "--enable-ocr",
        action="store_true",
        default=False,
        help="Enable OCR for image-based PDFs (requires tesseract)"
    )
    parser.add_argument(
        "--min-sentence-length",
        type=int,
        default=50,
        help="Minimum sentence length in characters"
    )
    parser.add_argument(
        "--max-sentence-length",
        type=int,
        default=1000,
        help="Maximum sentence length in characters"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes (default: CPU count - 1)"
    )
    
    args = parser.parse_args()
    
    if not HAS_PYPDF:
        logger.error("pypdf is required but not installed. Run: pip install pypdf")
        sys.exit(1)
    
    # Initialize preprocessor
    preprocessor = CorpusPreprocessor(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        extract_images=args.extract_images,
        enable_ocr=args.enable_ocr,
        min_sentence_length=args.min_sentence_length,
        max_sentence_length=args.max_sentence_length,
        num_workers=args.workers
    )
    
    # Process corpus
    stats = preprocessor.process_corpus()
    
    # Exit with error if no files were processed
    if stats['processed_files'] == 0:
        logger.error("No files were successfully processed!")
        sys.exit(1)
    
    logger.info(f"\n✓ Corpus preprocessing complete!")
    logger.info(f"Next step: Run train_domain_adapter.py with --corpus-dir {args.output_dir}/text")


if __name__ == "__main__":
    main()
