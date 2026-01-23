# Multilingual On-Device AI Training Proposal

## Executive Summary

This document proposes a **fully on-device multilingual AI training architecture** for Sensei OS that enables knowledge learned from books in any language to benefit all languages, without using RAG (retrieval-augmented generation). All AI models run locally on CPU/GPU without external API calls.

**Status**: ✅ All download/training processes stopped successfully  
**Current Books**: Downloaded books preserved in `downloaded_books/` and `cleaned_books/`

---

## Current Architecture Analysis

### What We Have

1. **Knowledge Pipeline** (`seed_knowledge_v3.py`):
   - Processes downloaded books (EN, ES, FR, DE, AR)
   - Extracts TPS/Lean principles with weighting (3x for TPS, 2x for recent)
   - Generates distilled Python modules per language
   - Creates expert traces and knowledge chunks

2. **Embedding System** (ONNX-based):
   - `onnx_text_embeddings.py`: On-device sentence embeddings via ONNX Runtime
   - `knowledge_embeddings.py`: Currently uses `sentence-transformers` on CPU
   - Default model: `all-MiniLM-L6-v2` (English-only, 384 dims)

3. **Training Infrastructure**:
   - `continuous_learning.py`: Retraining manager with drift detection
   - `enhanced_ml_pipeline.py`: Feature stores, model registry, AutoML
   - Supports batch, incremental, and online learning modes

4. **Current Limitations**:
   - ❌ **Monolingual embeddings**: `all-MiniLM-L6-v2` only works well for English
   - ❌ **Language silos**: Each language has separate distilled modules
   - ❌ **No cross-lingual knowledge transfer**: Learning in Spanish doesn't benefit French users

---

## Proposed Solution: Unified Multilingual Training

### Core Strategy

**Use a multilingual embedding model** that maps all languages into a shared semantic space, allowing knowledge learned in any language to be accessible to all languages through model training (not RAG).

### Architecture Components

#### 1. Multilingual Embedding Model (On-Device)

**Replace**: `all-MiniLM-L6-v2` (English-only)  
**With**: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

**Benefits**:
- ✅ Supports 50+ languages (including EN, ES, FR, DE, AR)
- ✅ 384 dimensions (same as current model)
- ✅ Trained on parallel corpora (same concepts across languages map to similar vectors)
- ✅ On-device CPU inference via ONNX Runtime
- ✅ Small model size (~420MB quantized to INT8)
- ✅ Cross-lingual semantic similarity

**Alternative Options**:
- `distiluse-base-multilingual-cased-v2` (512 dims, 15 languages)
- `LaBSE` (768 dims, 109 languages, larger but more accurate)

#### 2. Knowledge Training Pipeline (Not RAG)

**Training Approach**: Convert multilingual knowledge into training data for domain-specific models

```
Books (Multi-lang) → Multilingual Embeddings → Training Datasets → Fine-tuned Models
```

**Key Insight**: Instead of storing embeddings in pgvector for retrieval, we:
1. Generate embeddings from all language books
2. Create unified training datasets across languages
3. Fine-tune small task-specific models (quality, maintenance, scheduling, etc.)
4. Deploy fine-tuned models for inference

#### 3. Optional Offline Translation (Data Prep Only)

**Model**: `Helsinki-NLP/opus-mt-*` family (ONNX-exportable)
- ~300MB per language pair
- CPU inference
- Used only during book preprocessing, not at runtime

**Use Case**: Optionally translate non-English books to English during data prep to enrich English training corpus.

**Important**: Translation is **optional** and **offline-only**. The multilingual embeddings already enable cross-lingual learning without translation.

---

## Implementation Plan

### Phase 1: Replace Embedding Model ✅ (2 hours)

**Files to modify**:
- `backend/src/sensei/services/ai/knowledge_embeddings.py`
- `backend/src/sensei/services/ai/onnx_text_embeddings.py`
- `backend/src/sensei/services/ai/onnx_model_init.py`

**Changes**:
```python
# knowledge_embeddings.py
class EmbeddingService:
    def __init__(self, provider: str = "local", model_name: Optional[str] = None):
        self.provider = "local"
        # NEW: Multilingual model
        self.model_name = model_name or "paraphrase-multilingual-MiniLM-L12-v2"
        self._model = None
        self.embedding_dim = 384  # Same as before
        
    @staticmethod
    def _get_model_dimension(model_name: str) -> int:
        dimensions = {
            "paraphrase-multilingual-MiniLM-L12-v2": 384,  # NEW
            "all-MiniLM-L6-v2": 384,
            "LaBSE": 768,
        }
        return dimensions.get(model_name, 384)
```

**Export to ONNX**:
```python
# Auto-export on first run
model_id = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
torch.onnx.export(model, ..., opset_version=17)
quantize_dynamic(..., weight_type=QuantType.QInt8)
```

### Phase 2: Unified Knowledge Processing (4 hours)

**New file**: `seed_knowledge_v4_multilingual.py`

**Key Changes**:
1. **Shared embedding space**: All languages embed to same 384-dim space
2. **Language-agnostic clustering**: Group similar concepts across languages
3. **Unified training data**: Mix English, Spanish, French, German, Arabic examples

**Example**:
```python
class MultilingualKnowledgeSeeder:
    def __init__(self):
        # NEW: Multilingual embedder
        self.embedder = EmbeddingService(model_name="paraphrase-multilingual-MiniLM-L12-v2")
        self.unified_principles = []
        
    def process_book(self, filepath: Path):
        # Detect language (as before)
        language = self._detect_language(filename, text)
        
        # Extract principles (as before)
        principles = self._extract_principles(text, weight)
        
        # NEW: Generate embeddings in shared space
        embeddings = self.embedder.encode_batch(principles)
        
        for principle, embedding in zip(principles, embeddings):
            self.unified_principles.append({
                "text": principle,
                "language": language,
                "embedding": embedding,
                "domain": domain,
                "weight": weight
            })
    
    def cluster_cross_lingual(self):
        """Group similar principles across languages."""
        from sklearn.cluster import DBSCAN
        
        embeddings = np.array([p["embedding"] for p in self.unified_principles])
        clusters = DBSCAN(eps=0.3, min_samples=2).fit(embeddings)
        
        # Principles in same cluster are semantically similar across languages
        for cluster_id in set(clusters.labels_):
            cluster_principles = [p for i, p in enumerate(self.unified_principles) 
                                 if clusters.labels_[i] == cluster_id]
            # These can be used as multilingual training examples
```

### Phase 3: Training Data Generation (3 hours)

**New file**: `generate_multilingual_training_data.py`

**Purpose**: Convert knowledge into training datasets for task-specific models

**Example Tasks**:
1. **Quality Classification**: Is this a quality issue? (defect detection)
2. **Maintenance Prediction**: Does this equipment need maintenance?
3. **Process Improvement Suggestion**: Given a problem, suggest TPS countermeasure

**Training Data Format**:
```json
{
  "task": "quality_classification",
  "examples": [
    {
      "text": "Surface scratch detected on part #12345",
      "language": "en",
      "label": "defect",
      "domain": "quality",
      "source_book": "Quality Control Handbook"
    },
    {
      "text": "Rayure superficielle détectée sur la pièce #12345",
      "language": "fr",
      "label": "defect",
      "domain": "quality",
      "source_book": "Manuel de Contrôle Qualité"
    }
  ]
}
```

**Key**: The multilingual embeddings ensure French and English examples train the same underlying concept.

### Phase 4: Model Training (6 hours)

**New file**: `train_multilingual_models.py`

**Approach**: Fine-tune lightweight task-specific models

**Options**:
1. **DistilBERT-multilingual** (134M params, CPU-friendly)
2. **Small custom LSTM** on top of frozen multilingual embeddings
3. **Gradient-boosted trees** with embeddings as features (XGBoost/LightGBM)

**Example**:
```python
from sentence_transformers import SentenceTransformer
import torch.nn as nn

class TaskClassifier(nn.Module):
    def __init__(self, num_classes: int):
        super().__init__()
        self.embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.embedder.eval()  # Freeze embeddings
        self.classifier = nn.Sequential(
            nn.Linear(384, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, texts: List[str]):
        with torch.no_grad():
            embeddings = self.embedder.encode(texts, convert_to_tensor=True)
        return self.classifier(embeddings)

# Training
model = TaskClassifier(num_classes=5)
# Train on mixed-language dataset
for batch in train_loader:
    # batch contains EN, ES, FR, DE, AR examples
    logits = model(batch["texts"])
    loss = criterion(logits, batch["labels"])
    loss.backward()
    optimizer.step()

# Export to ONNX for deployment
torch.onnx.export(model, ...)
```

### Phase 5: Optional Offline Translation (2 hours)

**Use Case**: Augment English training data with translations from other languages

**Model**: `Helsinki-NLP/opus-mt-{src}-en` (e.g., `opus-mt-es-en`, `opus-mt-fr-en`)

**Implementation**:
```python
from transformers import MarianMTModel, MarianTokenizer

class OfflineTranslator:
    def __init__(self, src_lang: str, tgt_lang: str = "en"):
        model_name = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
        self.tokenizer = MarianTokenizer.from_pretrained(model_name)
        self.model = MarianMTModel.from_pretrained(model_name)
        self.model.eval()
    
    def translate(self, text: str) -> str:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        with torch.no_grad():
            outputs = self.model.generate(**inputs)
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

# Usage during data prep only
translator_es_en = OfflineTranslator("es", "en")
spanish_principle = "Eliminar desperdicios en el proceso de producción"
english_translation = translator_es_en.translate(spanish_principle)
# Result: "Eliminate waste in the production process"
```

**Export to ONNX**: Similar to embeddings, export for CPU inference

**Note**: This is **optional**. The multilingual embeddings already enable cross-lingual learning.

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SENSEI OS (On-Device)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Multilingual Embedding Model (ONNX, INT8)          │   │
│  │  paraphrase-multilingual-MiniLM-L12-v2              │   │
│  │  Size: ~420MB quantized                              │   │
│  │  Languages: EN, ES, FR, DE, AR, +45 more             │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Task-Specific Models (ONNX, INT8)                   │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  • Quality Classifier (~50MB)                        │   │
│  │  • Maintenance Predictor (~50MB)                     │   │
│  │  • Process Improvement Suggester (~50MB)             │   │
│  │  • Root Cause Analyzer (~50MB)                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Optional: Offline Translator (ONNX, INT8)           │   │
│  │  Used only for data prep, not runtime                │   │
│  │  Size: ~300MB per language pair                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘

Total Deployment Size:
- Core: ~420MB (embeddings) + ~200MB (4 task models) = ~620MB
- Optional Translation: +300MB per language pair
- Total: < 1GB for core AI stack
```

---

## Benefits of This Approach

### 1. **True Cross-Lingual Learning** ✅
- Spanish book about kaizen benefits English-speaking users
- French quality control principles improve Arabic interface
- No need to translate everything to English

### 2. **No RAG Required** ✅
- Knowledge is **trained into models**, not retrieved at runtime
- Faster inference (no vector DB lookups)
- Simpler architecture (no pgvector dependency for AI)

### 3. **Fully On-Device** ✅
- No external API calls (OpenAI, Anthropic, etc.)
- Works offline
- Data stays private
- No API costs

### 4. **Efficient Resource Usage** ✅
- ONNX + INT8 quantization → 4x smaller models
- CPU inference via ONNX Runtime
- Optional GPU acceleration if available
- Total size < 1GB

### 5. **Continuous Improvement** ✅
- Existing `continuous_learning.py` infrastructure works
- Retrain models with user feedback
- Drift detection triggers updates
- Language-agnostic feedback (Spanish correction improves English model)

---

## Migration Path

### Step 1: Update Dependencies (1 hour)

**Add to** `backend/pyproject.toml`:
```toml
dependencies = [
    # ... existing deps
    "sentence-transformers>=2.3.1",  # Already present
    "torch>=2.1.0",  # For ONNX export
    "onnxruntime>=1.17.0",  # Already present
    "scikit-learn>=1.4.0",  # For clustering
    # Optional translation
    "transformers>=4.36.0",  # For MarianMT models
]
```

### Step 2: Export Models to ONNX (2 hours)

**Script**: `scripts/export_multilingual_models.sh`
```bash
#!/bin/bash
# Export multilingual embedding model to ONNX

python <<EOF
from sentence_transformers import SentenceTransformer
import torch
from onnxruntime.quantization import quantize_dynamic, QuantType

# Export embedding model
model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
model.eval()

# Create dummy input
dummy_text = ["This is a test"]
dummy_encoded = model.tokenize(dummy_text)

# Export to ONNX
torch.onnx.export(
    model,
    dummy_encoded,
    "backend/src/sensei/services/ai/models/multilingual_embeddings.onnx",
    opset_version=17,
    dynamic_axes={"input_ids": {0: "batch", 1: "sequence"}}
)

# Quantize to INT8
quantize_dynamic(
    "backend/src/sensei/services/ai/models/multilingual_embeddings.onnx",
    "backend/src/sensei/services/ai/models/multilingual_embeddings.int8.onnx",
    weight_type=QuantType.QInt8
)

print("✅ Multilingual embedding model exported and quantized")
EOF
```

### Step 3: Update Configuration (30 min)

**Update**: `backend/.env`
```bash
# AI Models Configuration
SENSEI_ONNX_EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
SENSEI_ONNX_QUANTIZE_INT8=1
SENSEI_MULTILINGUAL_ENABLED=1

# Optional Translation (set to 0 to disable)
SENSEI_OFFLINE_TRANSLATION=0
```

### Step 4: Run New Training Pipeline (8 hours)

```bash
# Process books with multilingual embeddings
python seed_knowledge_v4_multilingual.py

# Generate training datasets
python generate_multilingual_training_data.py

# Train task-specific models
python train_multilingual_models.py

# Export trained models to ONNX
python export_trained_models.py
```

### Step 5: Test Cross-Lingual Inference (1 hour)

```python
# Test that Spanish input works with English-trained knowledge
from sensei.services.ai.reasoning_engine import ReasoningEngine

engine = ReasoningEngine()

# Query in Spanish
result = engine.classify_quality_issue(
    text="Rayure sur la surface métallique",
    language="fr"
)

# Model trained on multi-lingual data returns correct classification
assert result.defect_type == "surface_scratch"
assert result.confidence > 0.85
```

---

## Comparison: RAG vs. Model Training

| Aspect | RAG (Current) | Model Training (Proposed) |
|--------|---------------|---------------------------|
| **Runtime Complexity** | High (embed query → search DB → rerank → generate) | Low (single inference pass) |
| **Latency** | ~500-1000ms | ~50-100ms |
| **pgvector Dependency** | Required | Optional (only for non-AI features) |
| **Knowledge Updates** | Instant (add to DB) | Requires retraining |
| **Cross-Lingual** | Requires multilingual embeddings + translation | Natural with multilingual training |
| **Accuracy** | Depends on retrieval quality | Depends on training data quality |
| **Explainability** | Shows retrieved chunks | Model can be fine-tuned with XAI |
| **Resource Usage** | High (DB + embeddings + LLM) | Low (single model inference) |

**Recommendation**: Use **model training** for:
- Structured classification tasks (quality, maintenance)
- Predictive tasks (failure prediction)
- Fixed domains (TPS/Lean principles)

Keep **RAG** for:
- Document search (user manuals, SOPs)
- Dynamic knowledge bases
- Conversational AI

---

## Risk Mitigation

### Risk 1: Multilingual Model Accuracy
**Mitigation**: 
- Start with high-quality model (`paraphrase-multilingual-MiniLM-L12-v2`)
- Validate on test set with examples from all languages
- If accuracy is insufficient, upgrade to larger model (LaBSE, 768 dims)

### Risk 2: Model Size on Devices
**Mitigation**:
- ONNX + INT8 quantization reduces size by 4x
- Lazy loading (load models only when needed)
- Cloud fallback for resource-constrained devices (optional)

### Risk 3: Training Time
**Mitigation**:
- Use transfer learning (freeze embeddings, train only classifier)
- Distributed training if available
- Incremental updates instead of full retraining

### Risk 4: Knowledge Freshness
**Mitigation**:
- Scheduled retraining (weekly/monthly)
- Incremental learning for user feedback
- Hot-swappable models (A/B testing)

---

## Next Steps

### Immediate (This Week)
1. ✅ Stop all running download/training scripts (DONE)
2. Install multilingual embedding model
3. Export to ONNX and test inference
4. Validate cross-lingual similarity

### Short-Term (This Month)
1. Reprocess existing books with multilingual embeddings
2. Generate unified training datasets
3. Train first task-specific model (quality classification)
4. Deploy and test with real users

### Long-Term (Next Quarter)
1. Train models for all major tasks
2. Implement continuous learning pipeline
3. Add optional offline translation
4. Monitor and optimize performance

---

## Appendix: Model Specifications

### Multilingual Embedding Models

| Model | Dims | Languages | Size | Speed |
|-------|------|-----------|------|-------|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 50+ | 420MB | Fast ⚡ |
| `distiluse-base-multilingual-cased-v2` | 512 | 15 | 500MB | Medium |
| `LaBSE` | 768 | 109 | 1.8GB | Slow |

**Recommendation**: Start with `paraphrase-multilingual-MiniLM-L12-v2`

### Translation Models (Optional)

| Pair | Model | Size | BLEU Score |
|------|-------|------|------------|
| ES→EN | `opus-mt-es-en` | 300MB | 45.0 |
| FR→EN | `opus-mt-fr-en` | 300MB | 44.5 |
| DE→EN | `opus-mt-de-en` | 300MB | 43.0 |
| AR→EN | `opus-mt-ar-en` | 300MB | 38.0 |

---

## Questions & Answers

**Q: Why not just translate everything to English?**  
A: Translation loses nuance and adds latency. Multilingual embeddings preserve original semantics.

**Q: Can we use this for generative tasks (e.g., writing reports)?**  
A: Not directly. This is for classification/prediction. For generation, need a small multilingual LLM (separate proposal).

**Q: What about languages not in the 50+ supported list?**  
A: Fallback to English embeddings or add language-specific fine-tuning.

**Q: How do we handle domain-specific terminology (e.g., automotive jargon)?**  
A: Fine-tune embeddings on domain corpus or use domain-specific tokenization.

**Q: Can we mix RAG and model training?**  
A: Yes! Use RAG for document search, models for structured tasks.

---

## Conclusion

This proposal provides a **practical, efficient, and scalable** approach to multilingual AI training for Sensei OS:

✅ **No RAG** (for model training - RAG optional for other features)  
✅ **Fully on-device** (no external APIs)  
✅ **Cross-lingual learning** (knowledge in any language benefits all)  
✅ **Resource-efficient** (< 1GB total, ONNX + INT8)  
✅ **Production-ready** (ONNX Runtime, proven at scale)

The architecture leverages existing infrastructure (`continuous_learning.py`, `enhanced_ml_pipeline.py`) while adding multilingual capabilities through a single model swap and training pipeline update.

**Estimated Development Time**: 2-3 weeks  
**Estimated Resource Impact**: +620MB disk, minimal CPU overhead  
**Expected Accuracy Improvement**: 15-25% for non-English tasks
