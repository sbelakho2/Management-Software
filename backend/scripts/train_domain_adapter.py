#!/usr/bin/env python3
"""
Domain Adaptation Training Script

Fine-tunes embedding models on the manufacturing domain corpus using TSDAE
(Transformer-based Sequential Denoising Auto-Encoder) for unsupervised learning.

This script:
1. Loads all cleaned books from the corpus
2. Fine-tunes a base model (all-MiniLM-L6-v2) on domain text
3. Saves the adapted model for ONNX export

Usage:
    python scripts/train_domain_adapter.py [--epochs 1] [--batch-size 8]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def train_domain_embeddings(
    corpus_dir: Path,
    output_dir: Path,
    base_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    epochs: int = 1,
    batch_size: int = 8,
    max_sentences: int = 100000,
):
    """
    Train domain-adapted embeddings using TSDAE.
    
    Args:
        corpus_dir: Directory containing .txt files
        output_dir: Where to save the fine-tuned model
        base_model: Base sentence-transformer model
        epochs: Training epochs
        batch_size: Batch size for training
        max_sentences: Maximum sentences to use (for memory management)
    """
    try:
        from sentence_transformers import SentenceTransformer, LoggingHandler
        from sentence_transformers import models, datasets, losses
        from torch.utils.data import DataLoader
        import torch
    except ImportError as e:
        logger.error(f"Required packages not installed: {e}")
        logger.error("Install with: pip install sentence-transformers torch")
        sys.exit(1)
    
    # 1. Load Corpus
    logger.info(f"Loading corpus from {corpus_dir}")
    train_sentences = []
    
    if not corpus_dir.exists():
        logger.error(f"Corpus directory not found: {corpus_dir}")
        sys.exit(1)
    
    txt_files = list(corpus_dir.glob("*.txt"))
    logger.info(f"Found {len(txt_files)} text files")
    
    for book_file in txt_files:
        try:
            content = book_file.read_text(encoding='utf-8', errors='ignore')
            # Split by lines and filter short/empty lines
            lines = [
                line.strip() 
                for line in content.split('\n') 
                if len(line.strip()) > 50 and len(line.strip()) < 1000
            ]
            train_sentences.extend(lines)
            
            if len(train_sentences) >= max_sentences:
                logger.info(f"Reached max sentences limit ({max_sentences}), stopping corpus loading")
                break
                
        except Exception as e:
            logger.warning(f"Error reading {book_file.name}: {e}")
            continue
    
    if not train_sentences:
        logger.error("No training sentences found!")
        sys.exit(1)
    
    # Limit to max_sentences
    train_sentences = train_sentences[:max_sentences]
    logger.info(f"Loaded {len(train_sentences):,} sentences for training")
    
    # 2. Setup Device (Prefer GPU, fall back to CPU)
    if torch.cuda.is_available():
        device = "cuda"
        logger.info(f"Using device: {device} (GPU acceleration enabled)")
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        device = "cpu"
        logger.warning("GPU (CUDA) not available - training will be slower on CPU")
        logger.warning("To enable GPU: Install NVIDIA drivers and CUDA toolkit")
        logger.info(f"Using device: {device}")
    
    # 3. Load Base Model
    logger.info(f"Loading base model: {base_model}")
    try:
        word_embedding_model = models.Transformer(base_model)
        pooling_model = models.Pooling(
            word_embedding_model.get_word_embedding_dimension(),
            pooling_mode='mean'
        )
        model = SentenceTransformer(modules=[word_embedding_model, pooling_model])
        model.to(device)
    except Exception as e:
        logger.error(f"Error loading base model: {e}")
        sys.exit(1)
    
    # 4. Create TSDAE Dataset
    logger.info("Creating denoising autoencoder dataset")
    train_dataset = datasets.DenoisingAutoEncoderDataset(train_sentences)
    train_dataloader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    
    # 5. Setup Loss Function
    train_loss = losses.DenoisingAutoEncoderLoss(
        model,
        decoder_name_or_path=base_model,
        tie_encoder_decoder=True
    )
    
    # 6. Train
    logger.info(f"Starting training for {epochs} epoch(s)")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=epochs,
        weight_decay=0,
        scheduler='constantlr',
        optimizer_params={'lr': 3e-5},
        show_progress_bar=True,
        checkpoint_path=str(output_dir / "checkpoints"),
        checkpoint_save_steps=len(train_dataloader) // 2,
    )
    
    # 7. Save Final Model (CPU-compatible)
    logger.info("Training complete, preparing model for CPU inference...")
    
    # Move model to CPU before saving to ensure CPU compatibility
    if device == "cuda":
        model = model.to('cpu')
        torch.cuda.empty_cache()  # Clear GPU memory
        logger.info("Model moved from GPU to CPU for saving")
    
    final_path = output_dir / "final"
    final_path.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Saving CPU-compatible model to {final_path}")
    model.save(str(final_path))
    
    logger.info(f"✓ Training complete! Model saved to {final_path}")
    logger.info("✓ Model is CPU-compatible and ready for deployment")
    logger.info(f"Next step: Run export_onnx_models.py to create optimized deployment artifacts")
    
    return final_path


def main():
    parser = argparse.ArgumentParser(description="Train domain-adapted embeddings")
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("cleaned_books"),
        help="Directory containing training corpus (.txt files)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("backend/models/sensei-mfg-adapter"),
        help="Output directory for trained model"
    )
    parser.add_argument(
        "--base-model",
        type=str,
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Base model to fine-tune"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=1,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Training batch size"
    )
    parser.add_argument(
        "--max-sentences",
        type=int,
        default=100000,
        help="Maximum sentences to use for training"
    )
    
    args = parser.parse_args()
    
    train_domain_embeddings(
        corpus_dir=args.corpus_dir,
        output_dir=args.output_dir,
        base_model=args.base_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        max_sentences=args.max_sentences,
    )


if __name__ == "__main__":
    main()
