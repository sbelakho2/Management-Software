#!/usr/bin/env python3
"""
ONNX Model Export and Quantization Script

Converts fine-tuned PyTorch models to optimized ONNX format with INT8 quantization
for fast CPU inference in production environments.

This script:
1. Loads the fine-tuned adapter model
2. Exports to ONNX format
3. Applies dynamic INT8 quantization for CPU optimization
4. Validates the quantized model
5. Creates deployment-ready artifacts

Usage:
    python scripts/export_onnx_models.py --source backend/models/sensei-mfg-adapter/final
"""

import argparse
import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def export_and_quantize(
    source_path: Path,
    export_path: Path,
    quantize: bool = True,
    validate: bool = True,
):
    """
    Export model to ONNX and optionally quantize.
    
    Args:
        source_path: Path to fine-tuned PyTorch model
        export_path: Path for ONNX export
        quantize: Whether to apply INT8 quantization
        validate: Whether to validate the exported model
    """
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel
        import onnx
        import onnxruntime as ort
        from onnxruntime.quantization import quantize_dynamic, QuantType
    except ImportError as e:
        logger.error(f"Required packages not installed: {e}")
        logger.error("Install with: pip install torch transformers onnx onnxruntime")
        sys.exit(1)
    
    if not source_path.exists():
        logger.error(f"Source model not found: {source_path}")
        sys.exit(1)
    
    export_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Load Model and Tokenizer
    logger.info(f"Loading model from {source_path}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(str(source_path))
        model = AutoModel.from_pretrained(str(source_path))
        model.eval()
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        sys.exit(1)
    
    # 2. Export to ONNX
    onnx_path = export_path / "model.onnx"
    logger.info(f"Exporting to ONNX format: {onnx_path}")
    
    # Prepare dummy input
    dummy_input = tokenizer(
        "This is a sample sentence for export.",
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=256
    )
    
    # Export
    try:
        with torch.no_grad():
            torch.onnx.export(
                model,
                (dummy_input['input_ids'], dummy_input['attention_mask']),
                str(onnx_path),
                input_names=['input_ids', 'attention_mask'],
                output_names=['last_hidden_state'],
                dynamic_axes={
                    'input_ids': {0: 'batch', 1: 'sequence'},
                    'attention_mask': {0: 'batch', 1: 'sequence'},
                    'last_hidden_state': {0: 'batch', 1: 'sequence'}
                },
                opset_version=17,
                do_constant_folding=True,
            )
        logger.info("✓ ONNX export successful")
    except Exception as e:
        logger.error(f"Error during ONNX export: {e}")
        sys.exit(1)
    
    # 3. Quantize to INT8
    if quantize:
        quantized_path = export_path / "model.quant.onnx"
        logger.info(f"Quantizing to INT8: {quantized_path}")
        
        try:
            quantize_dynamic(
                model_input=str(onnx_path),
                model_output=str(quantized_path),
                weight_type=QuantType.QInt8,
                optimize_model=True,
            )
            logger.info("✓ Quantization successful")
            
            # Report size reduction
            original_size = onnx_path.stat().st_size / (1024 * 1024)
            quantized_size = quantized_path.stat().st_size / (1024 * 1024)
            reduction = ((original_size - quantized_size) / original_size) * 100
            
            logger.info(f"  Original size: {original_size:.2f} MB")
            logger.info(f"  Quantized size: {quantized_size:.2f} MB")
            logger.info(f"  Size reduction: {reduction:.1f}%")
            
        except Exception as e:
            logger.error(f"Error during quantization: {e}")
            sys.exit(1)
    
    # 4. Save Tokenizer
    tokenizer_path = export_path / "tokenizer"
    logger.info(f"Saving tokenizer: {tokenizer_path}")
    tokenizer.save_pretrained(str(tokenizer_path))
    
    # 5. Validate
    if validate:
        logger.info("Validating exported models...")
        
        # Validate ONNX model
        try:
            onnx_model = onnx.load(str(onnx_path))
            onnx.checker.check_model(onnx_model)
            logger.info("✓ ONNX model validation passed")
        except Exception as e:
            logger.error(f"ONNX validation failed: {e}")
            sys.exit(1)
        
        # Validate quantized model if it exists
        if quantize:
            try:
                quantized_onnx = onnx.load(str(quantized_path))
                onnx.checker.check_model(quantized_onnx)
                logger.info("✓ Quantized model validation passed")
            except Exception as e:
                logger.error(f"Quantized model validation failed: {e}")
                sys.exit(1)
        
        # Inference test
        logger.info("Running inference test...")
        test_model = str(quantized_path) if quantize else str(onnx_path)
        
        try:
            session = ort.InferenceSession(test_model)
            test_input = tokenizer(
                "Lean manufacturing reduces waste.",
                return_tensors="np",
                padding=True,
                truncation=True,
                max_length=256
            )
            
            start_time = time.time()
            outputs = session.run(
                None,
                {
                    'input_ids': test_input['input_ids'],
                    'attention_mask': test_input['attention_mask']
                }
            )
            inference_time = (time.time() - start_time) * 1000
            
            logger.info(f"✓ Inference test passed ({inference_time:.2f}ms)")
            logger.info(f"  Output shape: {outputs[0].shape}")
            
        except Exception as e:
            logger.error(f"Inference test failed: {e}")
            sys.exit(1)
    
    # 6. Create metadata file
    metadata = {
        "source_model": str(source_path),
        "export_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "quantized": quantize,
        "opset_version": 17,
        "embedding_dim": 384,  # all-MiniLM-L6-v2 dimension
    }
    
    import json
    metadata_path = export_path / "metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info("✓ Export complete!")
    logger.info(f"{'='*60}")
    logger.info(f"Deployment artifacts:")
    logger.info(f"  - Model: {quantized_path if quantize else onnx_path}")
    logger.info(f"  - Tokenizer: {tokenizer_path}")
    logger.info(f"  - Metadata: {metadata_path}")
    logger.info(f"\nTo use in production, update config:")
    logger.info(f"  SENSEI_ONNX_MODEL_PATH={export_path}")
    
    return export_path


def main():
    parser = argparse.ArgumentParser(description="Export and quantize models to ONNX")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("backend/models/sensei-mfg-adapter/final"),
        help="Path to fine-tuned model"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/models/sensei-mfg-onnx"),
        help="Output path for ONNX models"
    )
    parser.add_argument(
        "--no-quantize",
        action="store_true",
        help="Skip INT8 quantization"
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation"
    )
    
    args = parser.parse_args()
    
    export_and_quantize(
        source_path=args.source,
        export_path=args.output,
        quantize=not args.no_quantize,
        validate=not args.no_validate,
    )


if __name__ == "__main__":
    main()
