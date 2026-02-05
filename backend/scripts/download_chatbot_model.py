#!/usr/bin/env python3
"""
Download and Setup Script for Sensei OS Chatbot LLM Model.

This script downloads a VPS-optimized GGUF model for the chatbot.
Recommended models for VPS (2-4 CPU cores, 4-8GB RAM):
- Qwen2.5-3B-Instruct (Q4_K_M) - Best balance of quality/speed
- Phi-3.5-mini-instruct (Q4_K_M) - Very fast, good quality
- TinyLlama-1.1B-Chat - Fastest, suitable for very low resources

Usage:
    python download_chatbot_model.py [--model MODEL_NAME]

Models:
    qwen3b (default) - Qwen2.5-3B-Instruct Q4_K_M (~2GB)
    phi3.5           - Phi-3.5-mini-instruct Q4_K_M (~2.4GB)
    tinyllama        - TinyLlama-1.1B-Chat Q4_K_M (~600MB)
"""

import argparse
import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.request import urlretrieve
from urllib.error import URLError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Model configurations
MODELS = {
    "qwen3b": {
        "name": "Qwen2.5-3B-Instruct",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "size_mb": 2048,
        "description": "Best quality for VPS - 3B params, Q4_K_M quantization",
    },
    "phi3.5": {
        "name": "Phi-3.5-mini-instruct",
        "url": "https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf",
        "filename": "phi-3.5-mini-instruct-q4_k_m.gguf",
        "size_mb": 2400,
        "description": "Fast inference, good quality - Microsoft Phi-3.5",
    },
    "tinyllama": {
        "name": "TinyLlama-1.1B-Chat",
        "url": "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "filename": "tinyllama-1.1b-chat-v1.0-q4_k_m.gguf",
        "size_mb": 670,
        "description": "Fastest - For very low resource VPS",
    },
    "qwen1.5b": {
        "name": "Qwen2.5-1.5B-Instruct",
        "url": "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "filename": "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        "size_mb": 1024,
        "description": "Compact Qwen - Good quality/size ratio",
    },
}

# Default model directory
MODEL_DIR = Path(__file__).parent.parent / "models" / "llm"


def download_with_progress(url: str, destination: Path) -> bool:
    """Download a file with progress indication."""
    def report_progress(block_num: int, block_size: int, total_size: int) -> None:
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            sys.stdout.write(f"\rDownloading: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)")
            sys.stdout.flush()
    
    try:
        logger.info(f"Downloading from: {url}")
        logger.info(f"Destination: {destination}")
        
        urlretrieve(url, destination, reporthook=report_progress)
        print()  # New line after progress
        logger.info("Download complete!")
        return True
        
    except URLError as e:
        logger.error(f"Download failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False


def verify_model(model_path: Path) -> bool:
    """Verify the downloaded model is valid."""
    if not model_path.exists():
        return False
    
    # Check file size (should be at least 100MB for any real model)
    size_mb = model_path.stat().st_size / (1024 * 1024)
    if size_mb < 100:
        logger.warning(f"Model file seems too small ({size_mb:.1f} MB)")
        return False
    
    # Check GGUF magic number
    try:
        with open(model_path, 'rb') as f:
            magic = f.read(4)
            if magic != b'GGUF':
                logger.warning("File does not appear to be a valid GGUF model")
                return False
    except Exception as e:
        logger.error(f"Error verifying model: {e}")
        return False
    
    logger.info(f"Model verified successfully ({size_mb:.1f} MB)")
    return True


def update_config(model_path: Path, model_key: str) -> None:
    """Print config updates for the model."""
    model_info = MODELS[model_key]
    
    print("\n" + "="*60)
    print("Configuration Update Required")
    print("="*60)
    print("\nAdd these to your .env file or environment variables:\n")
    print(f"CHATBOT_MODEL_PATH={model_path}")
    print(f"CHATBOT_MODEL_URL={model_info['url']}")
    print("\nRecommended VPS settings:")
    print("CHATBOT_CONTEXT_LENGTH=2048")
    print("CHATBOT_MAX_TOKENS=256")
    print("CHATBOT_N_GPU_LAYERS=0")
    print("CHATBOT_N_THREADS=2")
    print("CHATBOT_BATCH_SIZE=256")
    print("="*60 + "\n")


def list_models() -> None:
    """List available models."""
    print("\nAvailable Models for VPS Deployment:")
    print("="*60)
    for key, info in MODELS.items():
        print(f"\n{key}:")
        print(f"  Name: {info['name']}")
        print(f"  Size: ~{info['size_mb']} MB")
        print(f"  Description: {info['description']}")
    print("\n" + "="*60)


def download_model(
    model_key: str = "qwen3b",
    output_dir: Optional[Path] = None,
    force: bool = False,
) -> Optional[Path]:
    """
    Download the specified model.
    
    Args:
        model_key: Key of model to download (qwen3b, phi3.5, tinyllama, qwen1.5b)
        output_dir: Directory to save model (default: backend/models/llm)
        force: Force re-download even if model exists
        
    Returns:
        Path to downloaded model or None if failed
    """
    if model_key not in MODELS:
        logger.error(f"Unknown model: {model_key}")
        logger.info(f"Available models: {', '.join(MODELS.keys())}")
        return None
    
    model_info = MODELS[model_key]
    model_dir = output_dir or MODEL_DIR
    model_path = model_dir / model_info["filename"]
    
    # Create directory if needed
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if model already exists
    if model_path.exists() and not force:
        if verify_model(model_path):
            logger.info(f"Model already exists: {model_path}")
            return model_path
        else:
            logger.warning("Existing model file is invalid, re-downloading...")
    
    print(f"\n{'='*60}")
    print(f"Downloading: {model_info['name']}")
    print(f"Description: {model_info['description']}")
    print(f"Expected size: ~{model_info['size_mb']} MB")
    print(f"{'='*60}\n")
    
    # Download
    if download_with_progress(model_info["url"], model_path):
        if verify_model(model_path):
            update_config(model_path, model_key)
            return model_path
        else:
            logger.error("Downloaded model verification failed")
            model_path.unlink(missing_ok=True)
            return None
    
    return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download LLM model for Sensei OS Chatbot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--model", "-m",
        choices=list(MODELS.keys()),
        default="qwen3b",
        help="Model to download (default: qwen3b)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=None,
        help=f"Output directory (default: {MODEL_DIR})",
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force re-download even if model exists",
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available models",
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_models()
        return 0
    
    logger.info(f"Sensei OS Chatbot Model Downloader")
    logger.info(f"Selected model: {args.model}")
    
    model_path = download_model(
        model_key=args.model,
        output_dir=args.output_dir,
        force=args.force,
    )
    
    if model_path:
        logger.info(f"Success! Model ready at: {model_path}")
        return 0
    else:
        logger.error("Model download failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
