#!/bin/bash
# Stop All Download and Training Scripts
# Usage: ./stop_all_scripts.sh

set -e

echo "=============================================================="
echo "STOPPING ALL SENSEI OS DOWNLOAD/TRAINING SCRIPTS"
echo "=============================================================="
echo ""

# Function to safely kill process
safe_kill() {
    local pid=$1
    local name=$2
    if ps -p $pid > /dev/null 2>&1; then
        echo "  ⏹️  Stopping $name (PID $pid)..."
        kill -TERM $pid 2>/dev/null || kill -9 $pid 2>/dev/null || true
        sleep 0.5
        if ps -p $pid > /dev/null 2>&1; then
            echo "     ⚠️  Process still running, forcing..."
            kill -9 $pid 2>/dev/null || true
        else
            echo "     ✅ Stopped"
        fi
    fi
}

# Find and stop Python download/training scripts
echo "Checking for Python download/training scripts..."
PIDS=$(pgrep -f 'python.*(download|train|seed_knowledge|book_cleaner|massive_downloader|multilingual_downloader|enhanced_downloader|robust_downloader|targeted_downloader|broad_downloader|catalog|libgen)' 2>/dev/null || true)

if [ -n "$PIDS" ]; then
    echo "Found Python scripts:"
    ps -p $PIDS -o pid,cmd 2>/dev/null || true
    echo ""
    for pid in $PIDS; do
        cmd=$(ps -p $pid -o cmd= 2>/dev/null || echo "unknown")
        safe_kill $pid "$cmd"
    done
else
    echo "  ✅ No Python download/training scripts running"
fi
echo ""

# Find and stop bash download/training scripts
echo "Checking for bash download/training scripts..."
BASH_PIDS=$(pgrep -f 'bash.*(download|train|pipeline|watchdog)' 2>/dev/null || true)

if [ -n "$BASH_PIDS" ]; then
    echo "Found bash scripts:"
    ps -p $BASH_PIDS -o pid,cmd 2>/dev/null || true
    echo ""
    for pid in $BASH_PIDS; do
        cmd=$(ps -p $pid -o cmd= 2>/dev/null || echo "unknown")
        safe_kill $pid "$cmd"
    done
else
    echo "  ✅ No bash download/training scripts running"
fi
echo ""

# Check for wget/curl downloading from libgen/annas
echo "Checking for wget/curl download processes..."
DOWNLOAD_PIDS=$(pgrep -f '(wget|curl).*(libgen|annas|archive\.org|z-lib)' 2>/dev/null || true)

if [ -n "$DOWNLOAD_PIDS" ]; then
    echo "Found download processes:"
    ps -p $DOWNLOAD_PIDS -o pid,cmd 2>/dev/null || true
    echo ""
    for pid in $DOWNLOAD_PIDS; do
        cmd=$(ps -p $pid -o cmd= 2>/dev/null || echo "unknown")
        safe_kill $pid "$cmd"
    done
else
    echo "  ✅ No wget/curl download processes running"
fi
echo ""

# Summary
echo "=============================================================="
echo "SUMMARY"
echo "=============================================================="

REMAINING=$(pgrep -f '(python|bash).*(download|train|seed_knowledge|book_cleaner|pipeline)' 2>/dev/null | wc -l)

if [ "$REMAINING" -eq 0 ]; then
    echo "✅ All download/training scripts stopped successfully"
    echo ""
    echo "Downloaded books preserved in:"
    echo "  - downloaded_books/"
    echo "  - cleaned_books/"
    echo ""
echo "Next steps:"
echo "  1. Review docs/maintenance/ML_SYSTEMS.md"
echo "  2. Install multilingual embedding model"
echo "  3. Reprocess books with new pipeline"
else
    echo "⚠️  Warning: $REMAINING processes may still be running"
    echo ""
    echo "Remaining processes:"
    pgrep -af '(python|bash).*(download|train|seed_knowledge|book_cleaner|pipeline)' 2>/dev/null || true
    echo ""
    echo "You may need to manually stop these with:"
    echo "  sudo kill -9 <PID>"
fi

echo ""
echo "=============================================================="
