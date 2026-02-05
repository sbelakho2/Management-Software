#!/bin/bash
#
# Resume GPU-accelerated TSDAE training
#
# This script will:
# 1. Check if GPU is available
# 2. Kill any existing training processes
# 3. Start training with GPU acceleration
# 4. Model will be saved as CPU-compatible for deployment
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

echo "==========================================="
echo "GPU-Accelerated Training Launcher"
echo "==========================================="
echo ""

# Check if GPU is available
echo "Checking GPU availability..."
if command -v nvidia-smi &> /dev/null; then
    echo "✓ nvidia-smi found"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo ""
else
    echo "⚠ WARNING: nvidia-smi not found. GPU may not be available."
    echo "Training will fall back to CPU (slow)."
    echo ""
fi

# Check CUDA in PyTorch
echo "Checking PyTorch CUDA support..."
CUDA_AVAILABLE=$(backend/.venv/bin/python -c "import torch; print('yes' if torch.cuda.is_available() else 'no')")
if [ "$CUDA_AVAILABLE" = "yes" ]; then
    echo "✓ PyTorch can see CUDA - GPU training enabled"
    GPU_NAME=$(backend/.venv/bin/python -c "import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')")
    echo "  GPU: $GPU_NAME"
else
    echo "⚠ WARNING: PyTorch cannot see CUDA"
    echo "  Training will use CPU (6+ hours estimated)"
    echo "  To fix: Reboot after installing NVIDIA drivers"
fi
echo ""

# Kill existing training processes
echo "Checking for existing training processes..."
if pgrep -f "train_domain_adapter.py" > /dev/null; then
    echo "Found existing training process. Stopping..."
    pkill -f "train_domain_adapter.py" || true
    sleep 2
    echo "✓ Process stopped"
else
    echo "✓ No existing training process"
fi
echo ""

# Start training
echo "==========================================="
echo "Starting TSDAE Training"
echo "==========================================="
echo ""
echo "Configuration:"
echo "  Corpus: preprocessed_corpus/text (434 files, 222 MB)"
echo "  Base model: sentence-transformers/all-MiniLM-L6-v2"
echo "  Training sentences: 100,000"
echo "  Epochs: 1"
echo "  Batch size: 8"
echo "  Output: backend/models/sensei-mfg-adapter"
echo ""

if [ "$CUDA_AVAILABLE" = "yes" ]; then
    echo "⚡ GPU acceleration: ENABLED"
    echo "  Estimated time: 30-60 minutes"
else
    echo "🐌 GPU acceleration: DISABLED (CPU mode)"
    echo "  Estimated time: 6+ hours"
fi
echo ""
echo "Model will be saved as CPU-compatible for deployment"
echo ""
echo "Press Ctrl+C to stop training"
echo "==========================================="
echo ""

# Run training
backend/.venv/bin/python backend/scripts/train_domain_adapter.py \
    --corpus-dir preprocessed_corpus/text \
    --output-dir backend/models/sensei-mfg-adapter \
    --base-model sentence-transformers/all-MiniLM-L6-v2 \
    --epochs 1 \
    --batch-size 8 \
    --max-sentences 100000

echo ""
echo "==========================================="
echo "Training Complete!"
echo "==========================================="
echo ""
echo "Model saved to: backend/models/sensei-mfg-adapter/final"
echo ""
echo "Next steps:"
echo "  1. Export to ONNX: backend/scripts/export_onnx_models.py"
echo "  2. Run tests: pytest backend/tests/ml/"
echo "  3. Benchmark performance"
echo ""
