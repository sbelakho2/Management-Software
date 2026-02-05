#!/bin/bash
#
# Monitor Preprocessing Progress
# Usage: ./monitor_preprocessing.sh
#

TOTAL_PDFS=$(find downloaded_books/pdf -name "*.pdf" 2>/dev/null | wc -l)

echo "Monitoring preprocessing progress..."
echo "Total PDFs to process: $TOTAL_PDFS"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
    PROCESSED=$(find preprocessed_corpus/text -name "*.txt" 2>/dev/null | wc -l)
    PERCENT=$((PROCESSED * 100 / TOTAL_PDFS))
    TEXT_SIZE=$(du -sh preprocessed_corpus/text 2>/dev/null | awk '{print $1}')
    
    # Progress bar
    FILLED=$((PERCENT / 2))
    BAR=$(printf '█%.0s' $(seq 1 $FILLED))
    EMPTY=$(printf '░%.0s' $(seq 1 $((50 - FILLED))))
    
    echo -ne "\r[${BAR}${EMPTY}] ${PROCESSED}/${TOTAL_PDFS} (${PERCENT}%) | Text: ${TEXT_SIZE}   "
    
    if [ "$PROCESSED" -ge "$TOTAL_PDFS" ]; then
        echo ""
        echo ""
        echo "✓ Preprocessing complete!"
        echo "  Processed files: $PROCESSED"
        echo "  Total text size: $TEXT_SIZE"
        echo ""
        echo "Ready to train. Run: backend/scripts/full_training_workflow.sh"
        break
    fi
    
    sleep 5
done
