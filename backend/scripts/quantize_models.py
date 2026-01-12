"""
Model Quantization Pipeline.

Provides utilities to export and quantize ONNX models for on-device execution.
Specifically targets INT8 dynamic quantization for CPU efficiency.
"""

import os
import argparse
from pathlib import Path
import logging

try:
    import onnx
    from onnxruntime.quantization import quantize_dynamic, QuantType
except ImportError:
    print("Dependencies missing. Install onnx and onnxruntime.")
    exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def quantize_model(input_path: Path, output_path: Path):
    """Perform INT8 dynamic quantization on an ONNX model."""
    logger.info(f"Quantizing {input_path} -> {output_path}")
    
    if not input_path.exists():
        logger.error(f"Input model not found: {input_path}")
        return

    try:
        quantize_dynamic(
            model_input=str(input_path),
            model_output=str(output_path),
            weight_type=QuantType.QInt8,
            optimize_model=True
        )
        logger.info("Quantization complete.")
    except Exception as e:
        logger.error(f"Quantization failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantize ONNX models to INT8.")
    parser.add_argument("input", type=str, help="Path to input .onnx model")
    parser.add_argument("--output", type=str, help="Path to output .onnx model (optional)")
    
    args = parser.parse_args()
    input_path = Path(args.input)
    
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".int8.onnx")
        
    quantize_model(input_path, output_path)
