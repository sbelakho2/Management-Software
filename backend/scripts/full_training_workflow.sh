#!/bin/bash
#
# Full Training Workflow: Preprocessing → Training → ONNX Export
# Usage: ./full_training_workflow.sh
#

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  On-Device AI Training Workflow${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 1: Check if preprocessing is complete
echo -e "${YELLOW}[1/4] Checking preprocessing status...${NC}"
INPUT_PDF_COUNT=$(find downloaded_books/pdf -name "*.pdf" 2>/dev/null | wc -l)
PROCESSED_TEXT_COUNT=$(find preprocessed_corpus/text -name "*.txt" 2>/dev/null | wc -l)

echo "  PDF files in downloaded_books/pdf: $INPUT_PDF_COUNT"
echo "  Processed text files: $PROCESSED_TEXT_COUNT"

if [ "$PROCESSED_TEXT_COUNT" -lt "$INPUT_PDF_COUNT" ]; then
    echo -e "${YELLOW}  Preprocessing not complete. Running preprocess_corpus.py...${NC}"
    "$VENV_PYTHON" backend/scripts/preprocess_corpus.py \
        --input-dir downloaded_books/pdf \
        --output-dir preprocessed_corpus \
        --workers 6 \
        --min-sentence-length 60 \
        --max-sentence-length 800
    echo -e "${GREEN}  ✓ Preprocessing complete!${NC}"
else
    echo -e "${GREEN}  ✓ Preprocessing already complete ($PROCESSED_TEXT_COUNT/$INPUT_PDF_COUNT files)${NC}"
fi
echo ""

# Step 2: Train domain embeddings
echo -e "${YELLOW}[2/4] Training domain-adapted embeddings...${NC}"
"$VENV_PYTHON" backend/scripts/train_domain_adapter.py \
    --corpus-dir preprocessed_corpus/text \
    --output-dir backend/models/sensei-mfg-adapter \
    --base-model sentence-transformers/all-MiniLM-L6-v2 \
    --epochs 1 \
    --batch-size 8 \
    --max-sentences 100000

echo -e "${GREEN}  ✓ Training complete!${NC}"
echo ""

# Step 3: Export to ONNX
echo -e "${YELLOW}[3/4] Exporting to ONNX with INT8 quantization...${NC}"
if [ -f "backend/scripts/export_onnx_models.py" ]; then
    "$VENV_PYTHON" backend/scripts/export_onnx_models.py \
        --input-model backend/models/sensei-mfg-adapter/final \
        --output-dir backend/models/sensei-mfg-onnx \
        --quantize int8
    echo -e "${GREEN}  ✓ ONNX export complete!${NC}"
else
    echo -e "${YELLOW}  ⚠ export_onnx_models.py not found, skipping ONNX export${NC}"
fi
echo ""

# Step 4: Validate models
echo -e "${YELLOW}[4/4] Validating models...${NC}"
echo "  Model artifacts:"
if [ -d "backend/models/sensei-mfg-adapter/final" ]; then
    echo -e "  ${GREEN}✓${NC} PyTorch model: backend/models/sensei-mfg-adapter/final"
fi
if [ -d "backend/models/sensei-mfg-onnx" ]; then
    echo -e "  ${GREEN}✓${NC} ONNX model: backend/models/sensei-mfg-onnx"
    ls -lh backend/models/sensei-mfg-onnx/*.onnx 2>/dev/null || echo "    (model files)"
fi

# Calculate corpus statistics
TOTAL_TEXT_SIZE=$(du -sh preprocessed_corpus/text 2>/dev/null | awk '{print $1}')
TOTAL_IMAGE_SIZE=$(du -sh preprocessed_corpus/images 2>/dev/null | awk '{print $1}')
echo ""
echo "  Corpus statistics:"
echo "    Text files: $PROCESSED_TEXT_COUNT ($TOTAL_TEXT_SIZE)"
echo "    Images extracted: $(find preprocessed_corpus/images -name "*.png" 2>/dev/null | wc -l) ($TOTAL_IMAGE_SIZE)"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ Training workflow complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Run tests: pytest backend/tests/ml/test_onnx_comprehensive.py -v"
echo "  2. Benchmark performance: pytest backend/tests/ml/test_onnx_comprehensive.py::TestONNXPerformance -v -s"
echo "  3. Deploy models to production"
