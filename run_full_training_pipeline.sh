#!/bin/bash
# Master pipeline for book processing and model training
# 
# Sequence:
# 1. Wait for downloads to complete
# 2. Thoroughly clean all books
# 3. Train all AI models (including ONNX)
#
# IMPORTANT: Training does NOT start until downloads are complete

set -e

cd /home/aaron/IdeaProjects/Management-Software
source .venv/bin/activate

echo "=============================================================="
echo "SENSEI OS - BOOK PROCESSING & MODEL TRAINING PIPELINE"
echo "=============================================================="
echo "Started at: $(date)"
echo ""

# Step 1: Wait for downloads
echo "Step 1: Checking download status..."
while pgrep -f "download" > /dev/null 2>&1; do
    BOOK_COUNT=$(ls -1 downloaded_books/txt/*.txt 2>/dev/null | wc -l)
    echo "  Downloads in progress... ($BOOK_COUNT books so far)"
    sleep 60
done
echo "  Downloads complete!"
echo ""

# Check we have books
BOOK_COUNT=$(ls -1 downloaded_books/txt/*.txt 2>/dev/null | wc -l)
if [ "$BOOK_COUNT" -lt 10 ]; then
    echo "ERROR: Only $BOOK_COUNT books downloaded. Need more books."
    exit 1
fi
echo "  Found $BOOK_COUNT downloaded books"
echo ""

# Step 2: Thoroughly clean books
echo "=============================================================="
echo "Step 2: Thoroughly cleaning books..."
echo "=============================================================="
python thorough_book_cleaner.py

CLEAN_COUNT=$(ls -1 cleaned_books/*.txt 2>/dev/null | wc -l)
if [ "$CLEAN_COUNT" -lt 10 ]; then
    echo "ERROR: Only $CLEAN_COUNT books passed cleaning. Check quality."
    exit 1
fi
echo "  $CLEAN_COUNT books cleaned successfully"
echo ""

# Step 3: Train all models
echo "=============================================================="
echo "Step 3: Training all AI models (including ONNX)..."
echo "=============================================================="
python train_all_models.py

echo ""
echo "=============================================================="
echo "PIPELINE COMPLETE"
echo "=============================================================="
echo "Finished at: $(date)"
echo ""
echo "Results:"
echo "  - Cleaned books: cleaned_books/"
echo "  - Expert traces: seeded_knowledge/expert_traces.json"
echo "  - Knowledge chunks: seeded_knowledge/knowledge_chunks.json"
echo "  - Distilled modules: backend/src/sensei/services/ai/distilled_knowledge/"
echo "  - ONNX models: backend/src/sensei/services/ai/models/"
