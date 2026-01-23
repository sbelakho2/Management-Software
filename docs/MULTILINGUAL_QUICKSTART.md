# Quick Start: Multilingual On-Device AI

## Current Status

✅ **All download/training scripts stopped**  
✅ **Downloaded books preserved** (`downloaded_books/`, `cleaned_books/`)  
✅ **Proposal document created** ([MULTILINGUAL_TRAINING_PROPOSAL.md](./MULTILINGUAL_TRAINING_PROPOSAL.md))

---

## Architecture Summary

**Current Problem**: Books in different languages are siloed - learning from Spanish books doesn't help French users.

**Solution**: Use multilingual embeddings to map all languages into a shared semantic space, then train models on this unified representation.

**Key Insight**: Instead of RAG (retrieve + generate), we **train knowledge into models** that work across all languages.

---

## Quick Commands

### Stop All Download/Training Scripts

```bash
./stop_all_scripts.sh
```

This will safely stop any running download or training processes without affecting the backend server.

### Check What's Running

```bash
# Check for download/training processes
pgrep -af 'python.*(download|train|seed_knowledge)'

# Check for book download processes
pgrep -af 'wget|curl.*libgen'
```

### Count Downloaded Books

```bash
# Total downloaded books
ls -1 downloaded_books/txt/*.txt 2>/dev/null | wc -l

# Total cleaned books  
ls -1 cleaned_books/*.txt 2>/dev/null | wc -l

# By language
ls -1 cleaned_books/en_*.txt 2>/dev/null | wc -l  # English
ls -1 cleaned_books/es_*.txt 2>/dev/null | wc -l  # Spanish
ls -1 cleaned_books/fr_*.txt 2>/dev/null | wc -l  # French
```

---

## Implementation Steps (High-Level)

### Phase 1: Install Multilingual Embedding Model ⏭️

**Estimated Time**: 2 hours

**What**: Replace English-only `all-MiniLM-L6-v2` with multilingual `paraphrase-multilingual-MiniLM-L12-v2`

**Files to modify**:
- `backend/src/sensei/services/ai/knowledge_embeddings.py`
- `backend/src/sensei/services/ai/onnx_text_embeddings.py`
- `backend/src/sensei/services/ai/onnx_model_init.py`

**Command**:
```bash
cd backend
# Update default model in .env
echo "SENSEI_ONNX_EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2" >> .env

# Test download (will cache model locally)
python <<EOF
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
print("✅ Model downloaded successfully")
print(f"Model size: {model.get_sentence_embedding_dimension()} dimensions")
EOF
```

### Phase 2: Create Unified Training Pipeline ⏭️

**Estimated Time**: 4 hours

**What**: Process books from all languages into a unified training dataset

**New file**: `seed_knowledge_v4_multilingual.py`

**Key changes**:
- Use multilingual embeddings for all languages
- Cluster similar concepts across languages
- Generate mixed-language training data

**Command**:
```bash
# Copy and modify existing seeder
cp seed_knowledge_v3.py seed_knowledge_v4_multilingual.py

# Update to use multilingual embeddings
# (See MULTILINGUAL_TRAINING_PROPOSAL.md Phase 2 for code changes)

# Run new pipeline
python seed_knowledge_v4_multilingual.py
```

### Phase 3: Train Cross-Lingual Models ⏭️

**Estimated Time**: 6 hours

**What**: Train task-specific models that work across all languages

**New file**: `train_multilingual_models.py`

**Tasks to train**:
1. Quality classification (defect detection)
2. Maintenance prediction
3. Process improvement suggestions
4. Root cause analysis

**Command**:
```bash
python train_multilingual_models.py \
    --task quality_classification \
    --epochs 10 \
    --batch-size 32 \
    --export-onnx
```

### Phase 4: Deploy & Test ⏭️

**Estimated Time**: 2 hours

**What**: Export models to ONNX, integrate with backend, test cross-lingual inference

**Command**:
```bash
# Export trained models to ONNX
python export_trained_models.py

# Test cross-lingual inference
python <<EOF
from sensei.services.ai.reasoning_engine import ReasoningEngine

engine = ReasoningEngine()

# Test French input (trained on multilingual data)
result = engine.classify_quality_issue(
    text="Rayure sur la surface métallique",
    language="fr"
)
print(f"Classification: {result.defect_type}")
print(f"Confidence: {result.confidence:.2%}")
EOF
```

---

## Key Benefits

### 1. Cross-Lingual Knowledge Transfer ✨

**Before**: Books are language-siloed
```
Spanish book about kaizen → Spanish users only
French quality guide → French users only
```

**After**: All languages benefit from all books
```
Spanish book about kaizen → Embeddings → Shared training → All languages
French quality guide → Embeddings → Shared training → All languages
```

### 2. No RAG Required for Training ✨

**RAG Approach** (retrieve at runtime):
```
User query → Embed → Search pgvector → Retrieve chunks → Generate response
Latency: ~500-1000ms
```

**Model Training Approach**:
```
Training: Books → Embeddings → Train model → Deploy
Inference: User query → Model → Response
Latency: ~50-100ms (10x faster)
```

**Note**: RAG is still useful for document search and conversational AI. This proposal focuses on structured tasks (classification, prediction).

### 3. Fully On-Device ✨

```
┌─────────────────────────────────────┐
│      SENSEI OS (Your Device)        │
├─────────────────────────────────────┤
│ ✅ Multilingual embeddings (420MB)  │
│ ✅ Task models (50MB each)          │
│ ✅ ONNX Runtime (CPU)               │
│ ✅ Optional: Translation (300MB)    │
├─────────────────────────────────────┤
│ ❌ No external API calls            │
│ ❌ No internet required (inference) │
│ ❌ No data sent to cloud            │
└─────────────────────────────────────┘
```

### 4. Optional Offline Translation ✨

**Use case**: Augment English training data with translations

**Model**: `Helsinki-NLP/opus-mt-{src}-en`

**Important**: 
- Translation is **optional** (multilingual embeddings already enable cross-lingual learning)
- Used only during **data preparation**, not at runtime
- Fully offline (no API calls)

**Example**:
```python
from transformers import MarianMTModel, MarianTokenizer

# Load offline translator
translator = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-es-en")
tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-es-en")

# Translate Spanish principle to English
spanish = "Eliminar desperdicios en el proceso"
inputs = tokenizer(spanish, return_tensors="pt")
outputs = translator.generate(**inputs)
english = tokenizer.decode(outputs[0], skip_special_tokens=True)
# Result: "Eliminate waste in the process"
```

---

## Resource Requirements

### Disk Space

| Component | Size | Required |
|-----------|------|----------|
| Multilingual embeddings (ONNX INT8) | 420MB | ✅ Yes |
| Task models (4 models × 50MB) | 200MB | ✅ Yes |
| ONNX Runtime | 50MB | ✅ Yes |
| Offline translator (per language pair) | 300MB | Optional |
| **Total (core)** | **~670MB** | **✅ Yes** |
| **Total (with translation)** | **~1.3GB** | Optional |

### RAM Usage

| Operation | RAM | Notes |
|-----------|-----|-------|
| Embedding generation | ~500MB | During training only |
| Model inference | ~100MB | Per model |
| Total at runtime | ~600MB | Embeddings + 1 task model |

### CPU Usage

| Operation | CPU | Notes |
|-----------|-----|-------|
| Embedding generation | ~1 core | ONNX Runtime optimized |
| Model inference | ~0.5 core | Fast inference |
| Training | 4-8 cores | Multi-threaded |

**GPU**: Optional (will use if available, not required)

---

## Testing Cross-Lingual Learning

### Example 1: Quality Classification

**Training data** (mixed languages):
```
EN: "Surface scratch on metal part" → label: surface_defect
ES: "Rayadura en la superficie metálica" → label: surface_defect
FR: "Rayure sur la surface métallique" → label: surface_defect
```

**Inference** (works in any language):
```python
# German input (not in training data!)
classify("Kratzer auf der Metalloberfläche")
# → Predicts: surface_defect (because multilingual embeddings map similar concepts)
```

### Example 2: Maintenance Prediction

**Training data**:
```
EN: "Unusual vibration detected" → label: bearing_failure_risk
FR: "Vibration inhabituelle détectée" → label: bearing_failure_risk
```

**Inference**:
```python
# Spanish input
predict("Vibración inusual detectada")
# → Predicts: bearing_failure_risk
```

---

## Comparison: Current vs. Proposed

| Aspect | Current | Proposed |
|--------|---------|----------|
| **Embedding model** | `all-MiniLM-L6-v2` (EN only) | `paraphrase-multilingual-MiniLM-L12-v2` (50+ langs) |
| **Cross-lingual** | ❌ No | ✅ Yes |
| **Knowledge sharing** | Language silos | Unified semantic space |
| **Inference speed** | N/A (no training yet) | ~50-100ms |
| **Model size** | N/A | ~670MB (ONNX INT8) |
| **External APIs** | None | None |
| **Offline capable** | ✅ Yes | ✅ Yes |

---

## Troubleshooting

### Issue: Model download fails

**Solution**: Check internet connection, retry download
```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"
```

### Issue: Out of memory during training

**Solution**: Reduce batch size or use gradient accumulation
```bash
python train_multilingual_models.py --batch-size 16  # Instead of 32
```

### Issue: Inference too slow

**Solution**: Verify ONNX quantization is enabled
```bash
# Check if INT8 quantized models are being used
ls -lh backend/src/sensei/services/ai/models/*.int8.onnx
```

### Issue: Cross-lingual accuracy low

**Solution**: 
1. Check if multilingual model is actually being used (not English-only model)
2. Increase training data for underrepresented languages
3. Consider using larger model (LaBSE, 768 dims)

---

## Next Steps

1. **Review** the full proposal: [MULTILINGUAL_TRAINING_PROPOSAL.md](./MULTILINGUAL_TRAINING_PROPOSAL.md)

2. **Stop scripts** if still running:
   ```bash
   ./stop_all_scripts.sh
   ```

3. **Phase 1**: Install multilingual embedding model (2 hours)

4. **Phase 2**: Create unified training pipeline (4 hours)

5. **Phase 3**: Train cross-lingual models (6 hours)

6. **Phase 4**: Deploy and test (2 hours)

**Total estimated time**: 14 hours (~2 days)

---

## Questions?

- **Q: Is this production-ready?**  
  A: Yes, ONNX Runtime is production-grade, used by Microsoft/AWS/Google.

- **Q: Will this replace RAG entirely?**  
  A: No, RAG is still useful for document search. This is for structured tasks.

- **Q: Can we add more languages later?**  
  A: Yes, the multilingual model supports 50+ languages out of the box.

- **Q: What about languages not in the 50+ list?**  
  A: Fallback to English or fine-tune on language-specific data.

- **Q: How do we update models with new books?**  
  A: Run retraining pipeline (existing `continuous_learning.py` infrastructure).

---

**Created**: 2026-01-23  
**Status**: Ready for implementation  
**See also**: [MULTILINGUAL_TRAINING_PROPOSAL.md](./MULTILINGUAL_TRAINING_PROPOSAL.md)
