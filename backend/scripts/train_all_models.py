#!/usr/bin/env python3
"""
Comprehensive Model Training Pipeline

Downloads public datasets and trains ALL AI/ML models for Sensei OS with:
- Statistical validation (cross-validation, confidence intervals)
- Hyperparameter optimization
- Large-scale real dataset testing

Usage:
    python scripts/train_all_models.py --all
    python scripts/train_all_models.py --model cbm
    python scripts/train_all_models.py --model embeddings
"""

import argparse
import logging
import sys
import os
import json
import time
import zipfile
import hashlib
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import urllib.request
import urllib.error

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# Dataset Configuration
# =============================================================================

@dataclass
class DatasetConfig:
    """Configuration for a public dataset."""
    name: str
    url: str
    description: str
    format: str  # csv, json, zip, tar.gz
    size_mb: float
    target_model: str
    preprocessing_fn: str = ""  # Function name for preprocessing
    

# Publicly available datasets for each model type
DATASETS = {
    # CBM Predictor - Predictive Maintenance
    "ai4i_2020": DatasetConfig(
        name="AI4I 2020 Predictive Maintenance",
        url="https://archive.ics.uci.edu/ml/machine-learning-databases/00601/ai4i2020.csv",
        description="UCI ML Dataset - Synthetic predictive maintenance data (10,000 samples)",
        format="csv",
        size_mb=0.5,
        target_model="cbm_predictor",
    ),
    "pump_sensor": DatasetConfig(
        name="Pump Sensor Data for Predictive Maintenance",
        url="https://raw.githubusercontent.com/nphantawee/pump-sensor-data/main/sensor.csv",
        description="Real sensor data from industrial pumps (220,320 samples)",
        format="csv",
        size_mb=40,
        target_model="cbm_predictor",
    ),
    "nasa_turbofan": DatasetConfig(
        name="NASA C-MAPSS Turbofan Engine Degradation",
        url="https://raw.githubusercontent.com/kpeters/exploring-nasas-turbofan-dataset/main/CMAPSSData/train_FD001.txt",
        description="NASA jet engine run-to-failure simulation",
        format="txt",
        size_mb=3,
        target_model="cbm_predictor",
    ),
    
    # Evidence Detector - Problem Report Classification  
    "twenty_newsgroups": DatasetConfig(
        name="20 Newsgroups Text Classification",
        url="http://qwone.com/~jason/20Newsgroups/20news-bydate.tar.gz",
        description="Classic text classification dataset (18,846 documents)",
        format="tar.gz",
        size_mb=17,
        target_model="evidence_detector",
    ),
    
    # Intent Classifier - Intent Recognition
    "banking77": DatasetConfig(
        name="Banking77 Intent Classification",
        url="https://raw.githubusercontent.com/PolyAI-LDN/task-specific-datasets/master/banking_data/train.csv",
        description="77 banking intents (10,003 training samples)",
        format="csv",
        size_mb=1,
        target_model="intent_classifier",
    ),
    "snips": DatasetConfig(
        name="SNIPS Intent Dataset", 
        url="https://raw.githubusercontent.com/sonos/nlu-benchmark/master/2017-06-custom-intent-engines/train_dataset.json",
        description="7 intents - personal assistant commands",
        format="json",
        size_mb=0.2,
        target_model="intent_classifier",
    ),
    
    # Visual Quality - Defect Detection
    "neu_surface_defects": DatasetConfig(
        name="NEU Surface Defect Dataset",
        url="http://faculty.neu.edu.cn/yunhyan/NEU_surface_defect_database.html",  # Manual download
        description="6 types of steel surface defects (1,800 images)",
        format="manual",
        size_mb=60,
        target_model="visual_quality",
    ),
    
    # Domain Embeddings - Manufacturing Text
    "lean_manufacturing_corpus": DatasetConfig(
        name="Lean Manufacturing Corpus (Local)",
        url="local://cleaned_books",
        description="Pre-processed Lean/TPS domain corpus",
        format="local",
        size_mb=50,
        target_model="domain_embeddings",
    ),
}


# =============================================================================
# Dataset Downloaders
# =============================================================================

class DatasetDownloader:
    """Downloads and caches public datasets."""
    
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def download(self, config: DatasetConfig, force: bool = False) -> Path:
        """Download dataset if not cached."""
        cache_path = self.cache_dir / config.name.replace(" ", "_").lower()
        
        if cache_path.exists() and not force:
            logger.info(f"Using cached dataset: {config.name}")
            return cache_path
            
        cache_path.mkdir(parents=True, exist_ok=True)
        
        if config.url.startswith("local://"):
            # Local dataset
            local_path = Path(config.url.replace("local://", ""))
            if not local_path.is_absolute():
                local_path = Path(__file__).parent.parent.parent / local_path
            return local_path
            
        if config.format == "manual":
            logger.warning(f"Dataset {config.name} requires manual download from: {config.url}")
            return cache_path
            
        logger.info(f"Downloading {config.name} ({config.size_mb:.1f} MB)...")
        
        try:
            file_ext = config.url.split('.')[-1]
            if config.format in ("tar.gz",):
                file_ext = "tar.gz"
            download_path = cache_path / f"data.{file_ext}"
            
            # Download with progress
            self._download_with_progress(config.url, download_path)
            
            # Extract if needed
            if config.format == "zip":
                self._extract_zip(download_path, cache_path)
            elif config.format == "tar.gz":
                self._extract_tar_gz(download_path, cache_path)
                
            return cache_path
            
        except Exception as e:
            logger.error(f"Failed to download {config.name}: {e}")
            raise
            
    def _download_with_progress(self, url: str, dest: Path):
        """Download file with progress indicator."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=300) as response:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(dest, 'wb') as f:
                    while True:
                        chunk = response.read(block_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = (downloaded / total_size) * 100
                            print(f"\r  Progress: {pct:.1f}%", end='', flush=True)
                            
            print()  # New line after progress
            logger.info(f"Downloaded: {dest}")
            
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e}")
            raise
            
    def _extract_zip(self, zip_path: Path, dest: Path):
        """Extract zip file."""
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(dest)
        logger.info(f"Extracted zip to: {dest}")
        
    def _extract_tar_gz(self, tar_path: Path, dest: Path):
        """Extract tar.gz file."""
        import tarfile
        with tarfile.open(tar_path, 'r:gz') as t:
            t.extractall(dest)
        logger.info(f"Extracted tar.gz to: {dest}")


# =============================================================================
# Model Trainers
# =============================================================================

@dataclass
class TrainingResult:
    """Results from model training."""
    model_name: str
    success: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    training_time_seconds: float = 0.0
    dataset_size: int = 0
    error: str = ""
    cross_val_scores: List[float] = field(default_factory=list)
    confidence_interval_95: Tuple[float, float] = (0.0, 0.0)
    hyperparameters: Dict[str, Any] = field(default_factory=dict)


class BaseTrainer:
    """Base class for model trainers."""
    
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
    def train(self, data_path: Path, **kwargs) -> TrainingResult:
        raise NotImplementedError
        
    def _calculate_confidence_interval(
        self, 
        scores: List[float], 
        confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval for cross-validation scores."""
        import scipy.stats as stats
        n = len(scores)
        mean = np.mean(scores)
        se = stats.sem(scores)
        h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
        return (mean - h, mean + h)


class CBMPredictor_Trainer(BaseTrainer):
    """Trainer for Condition-Based Maintenance Predictor."""
    
    def train(self, data_path: Path, **kwargs) -> TrainingResult:
        """Train CBM models on predictive maintenance data."""
        from sklearn.ensemble import RandomForestClassifier, IsolationForest, GradientBoostingClassifier
        from sklearn.preprocessing import StandardScaler, LabelEncoder
        from sklearn.model_selection import cross_val_score, GridSearchCV, StratifiedKFold
        from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
        import joblib
        import pandas as pd
        
        start_time = time.time()
        logger.info("Training CBM Predictor on AI4I 2020 dataset...")
        
        try:
            # Load AI4I 2020 dataset (UCI Predictive Maintenance)
            csv_files = list(data_path.glob("**/*.csv")) + list(data_path.glob("**/*.txt"))
            if not csv_files:
                return TrainingResult(
                    model_name="cbm_predictor",
                    success=False,
                    error="No CSV/TXT files found in dataset"
                )
            
            # Try to load AI4I 2020 format
            df = None
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                    if 'Machine failure' in df.columns or 'Target' in df.columns:
                        break
                    if 'UDI' in df.columns:  # AI4I 2020 format
                        break
                except Exception:
                    continue
                    
            if df is None or df.empty:
                return TrainingResult(
                    model_name="cbm_predictor",
                    success=False,
                    error="Could not load valid dataset"
                )
            
            logger.info(f"Loaded dataset: {len(df)} samples, {len(df.columns)} features")
            
            # Preprocess AI4I 2020 dataset
            # Expected columns: UDI, Product ID, Type, Air temperature, Process temperature, 
            # Rotational speed, Torque, Tool wear, Machine failure, TWF, HDF, PWF, OSF, RNF
            
            if 'Machine failure' in df.columns:
                target_col = 'Machine failure'
            elif 'Target' in df.columns:
                target_col = 'Target'
            else:
                target_col = df.columns[-1]  # Assume last column
                
            y = df[target_col].values
            
            # Select numeric features
            feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            feature_cols = [c for c in feature_cols if c != target_col and c not in ['UDI', 'TWF', 'HDF', 'PWF', 'OSF', 'RNF']]
            
            X = df[feature_cols].values
            
            # Handle categorical 'Type' column if present
            if 'Type' in df.columns:
                le = LabelEncoder()
                type_encoded = le.fit_transform(df['Type'].fillna('M'))
                X = np.column_stack([X, type_encoded])
            
            # Remove NaN rows
            mask = ~np.isnan(X).any(axis=1) & ~np.isnan(y)
            X = X[mask]
            y = y[mask].astype(int)
            
            logger.info(f"Training data: {X.shape[0]} samples, {X.shape[1]} features")
            logger.info(f"Class distribution: {np.bincount(y)}")
            
            # Normalize features
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)
            
            # ================================================================
            # HYPERPARAMETER OPTIMIZATION with GridSearchCV
            # ================================================================
            logger.info("Performing hyperparameter optimization...")
            
            param_grid = {
                'n_estimators': [100, 200, 300],
                'max_depth': [10, 15, 20, None],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'class_weight': ['balanced', 'balanced_subsample'],
            }
            
            # Use stratified k-fold for class imbalance
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            
            # Grid search (reduce search space for speed)
            rf = RandomForestClassifier(random_state=42, n_jobs=-1)
            
            # Reduced grid for faster training
            param_grid_reduced = {
                'n_estimators': [200, 300],
                'max_depth': [15, 20],
                'min_samples_split': [5, 10],
                'class_weight': ['balanced'],
            }
            
            grid_search = GridSearchCV(
                rf, param_grid_reduced, 
                cv=cv, 
                scoring='f1_weighted',
                n_jobs=-1,
                verbose=1
            )
            grid_search.fit(X_scaled, y)
            
            best_params = grid_search.best_params_
            logger.info(f"Best hyperparameters: {best_params}")
            
            # Train final model with best params
            failure_classifier = RandomForestClassifier(**best_params, random_state=42, n_jobs=-1)
            
            # Cross-validation for robust metrics
            cv_f1 = cross_val_score(failure_classifier, X_scaled, y, cv=cv, scoring='f1_weighted')
            cv_precision = cross_val_score(failure_classifier, X_scaled, y, cv=cv, scoring='precision_weighted')
            cv_recall = cross_val_score(failure_classifier, X_scaled, y, cv=cv, scoring='recall_weighted')
            
            # Fit on full data
            failure_classifier.fit(X_scaled, y)
            
            # Train anomaly detector (Isolation Forest)
            anomaly_detector = IsolationForest(
                contamination=0.1,
                n_estimators=200,
                max_samples='auto',
                random_state=42,
                n_jobs=-1
            )
            anomaly_detector.fit(X_scaled)
            
            # Calculate metrics and confidence intervals
            f1_mean = np.mean(cv_f1)
            f1_ci = self._calculate_confidence_interval(cv_f1.tolist())
            
            # Save models
            output_dir = self.model_dir / "cbm_predictor"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            joblib.dump(failure_classifier, output_dir / "failure_classifier.pkl")
            joblib.dump(anomaly_detector, output_dir / "anomaly_detector.pkl")
            joblib.dump(scaler, output_dir / "scaler.pkl")
            
            # Save metadata
            metadata = {
                "trained_at": datetime.now().isoformat(),
                "dataset": "AI4I 2020 Predictive Maintenance",
                "samples": int(X.shape[0]),
                "features": int(X.shape[1]),
                "hyperparameters": best_params,
                "metrics": {
                    "f1_weighted": float(f1_mean),
                    "f1_ci_95": [float(f1_ci[0]), float(f1_ci[1])],
                    "precision_weighted": float(np.mean(cv_precision)),
                    "recall_weighted": float(np.mean(cv_recall)),
                },
                "cross_validation_folds": 5,
            }
            with open(output_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            elapsed = time.time() - start_time
            
            return TrainingResult(
                model_name="cbm_predictor",
                success=True,
                metrics={
                    'f1_weighted': f1_mean,
                    'precision_weighted': float(np.mean(cv_precision)),
                    'recall_weighted': float(np.mean(cv_recall)),
                },
                training_time_seconds=elapsed,
                dataset_size=X.shape[0],
                cross_val_scores=cv_f1.tolist(),
                confidence_interval_95=f1_ci,
                hyperparameters=best_params,
            )
            
        except Exception as e:
            logger.exception(f"CBM training failed: {e}")
            return TrainingResult(
                model_name="cbm_predictor",
                success=False,
                error=str(e),
                training_time_seconds=time.time() - start_time
            )


class EvidenceDetector_Trainer(BaseTrainer):
    """Trainer for Missing Evidence Detector."""
    
    def train(self, data_path: Path, **kwargs) -> TrainingResult:
        """Train evidence detector on text classification data."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
        from sklearn.model_selection import cross_val_score, GridSearchCV, StratifiedKFold
        from sklearn.pipeline import Pipeline
        import joblib
        
        start_time = time.time()
        logger.info("Training Evidence Detector...")
        
        try:
            # Generate synthetic A3-style training data since no public A3 dataset exists
            # This simulates the structure of A3 problem-solving reports
            
            logger.info("Generating synthetic A3 training data...")
            
            # Templates for complete/incomplete evidence
            complete_templates = [
                "Root cause analysis shows 35% defect rate reduction after implementing countermeasures. "
                "Data collected over 30 days baseline vs 30 days post-implementation. "
                "Before: 150 ppm defects. After: 98 ppm defects. Validation confirmed by QC team.",
                
                "5-Why analysis identified bearing wear as root cause. Vibration data: 8.2mm/s before, "
                "2.1mm/s after replacement. Statistical significance p<0.05. N=45 samples.",
                
                "Pareto chart shows 78% of delays from material shortages. Implemented Kanban system. "
                "Lead time reduced from 5.2 days to 2.1 days. Validated over 90 production cycles.",
                
                "Fishbone diagram identified 4 contributing factors. Temperature variation was primary. "
                "Before: ±15°C variation. After SPC implementation: ±3°C. Cp improved from 0.67 to 1.45.",
                
                "Measurement system analysis shows Gage R&R = 12.5%. Process capability Cpk = 1.67. "
                "Control charts demonstrate stable process. 500 samples validated over 4 weeks.",
            ]
            
            incomplete_templates = [
                "We fixed the problem. The issue was with the machine. It works better now.",
                
                "Root cause is unclear but we changed the process and it seems to help.",
                
                "Production improved after changes. Will monitor going forward.",
                
                "The team discussed options and implemented a solution. Results pending.",
                
                "Problem identified and corrected. Training provided to operators.",
            ]
            
            # Expand templates with variations
            import random
            random.seed(42)
            
            complete_reports = []
            incomplete_reports = []
            
            # Generate 2000 complete samples
            metrics_words = ['ppm', 'defects', 'hours', 'days', '%', 'sigma', 'Cpk', 'samples']
            action_words = ['implemented', 'reduced', 'improved', 'validated', 'measured', 'analyzed']
            
            for i in range(2000):
                base = random.choice(complete_templates)
                # Add random numeric data
                num1 = random.randint(10, 500)
                num2 = random.randint(1, 100)
                metric = random.choice(metrics_words)
                action = random.choice(action_words)
                variation = f" Additional data: {num1} {metric}, {action} successfully. N={num2} samples verified."
                complete_reports.append(base + variation)
            
            # Generate 2000 incomplete samples
            vague_phrases = [
                "We will investigate further.",
                "More data needed.",
                "Results look promising.",
                "Team is working on it.",
                "Situation improved somewhat.",
            ]
            
            for i in range(2000):
                base = random.choice(incomplete_templates)
                variation = random.choice(vague_phrases)
                incomplete_reports.append(base + " " + variation)
            
            # Combine data
            texts = complete_reports + incomplete_reports
            labels = [1] * len(complete_reports) + [0] * len(incomplete_reports)
            
            # Shuffle
            combined = list(zip(texts, labels))
            random.shuffle(combined)
            texts, labels = zip(*combined)
            texts = list(texts)
            labels = list(labels)
            
            logger.info(f"Training data: {len(texts)} samples (balanced)")
            
            # Build pipeline with TF-IDF + Classifier
            pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=1000,
                    ngram_range=(1, 3),
                    stop_words='english',
                    min_df=2,
                    max_df=0.95
                )),
                ('clf', RandomForestClassifier(random_state=42, n_jobs=-1))
            ])
            
            # Hyperparameter optimization
            param_grid = {
                'tfidf__max_features': [500, 1000],
                'tfidf__ngram_range': [(1, 2), (1, 3)],
                'clf__n_estimators': [100, 200],
                'clf__max_depth': [10, 20],
            }
            
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            
            grid_search = GridSearchCV(
                pipeline, param_grid,
                cv=cv,
                scoring='f1',
                n_jobs=-1,
                verbose=1
            )
            grid_search.fit(texts, labels)
            
            best_params = grid_search.best_params_
            logger.info(f"Best hyperparameters: {best_params}")
            
            # Final cross-validation
            best_pipeline = grid_search.best_estimator_
            cv_f1 = cross_val_score(best_pipeline, texts, labels, cv=cv, scoring='f1')
            cv_precision = cross_val_score(best_pipeline, texts, labels, cv=cv, scoring='precision')
            cv_recall = cross_val_score(best_pipeline, texts, labels, cv=cv, scoring='recall')
            
            f1_mean = np.mean(cv_f1)
            f1_ci = self._calculate_confidence_interval(cv_f1.tolist())
            
            # Save model
            output_dir = self.model_dir / "evidence_detector"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            joblib.dump(best_pipeline, output_dir / "pipeline.pkl")
            
            # Also save components separately for compatibility
            joblib.dump(best_pipeline.named_steps['tfidf'], output_dir / "tfidf.pkl")
            joblib.dump(best_pipeline.named_steps['clf'], output_dir / "classifier.pkl")
            
            # Save metadata
            metadata = {
                "trained_at": datetime.now().isoformat(),
                "dataset": "Synthetic A3 Report Data",
                "samples": len(texts),
                "hyperparameters": best_params,
                "metrics": {
                    "f1": float(f1_mean),
                    "f1_ci_95": [float(f1_ci[0]), float(f1_ci[1])],
                    "precision": float(np.mean(cv_precision)),
                    "recall": float(np.mean(cv_recall)),
                },
                "cross_validation_folds": 5,
            }
            with open(output_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            elapsed = time.time() - start_time
            
            return TrainingResult(
                model_name="evidence_detector",
                success=True,
                metrics={
                    'f1': f1_mean,
                    'precision': float(np.mean(cv_precision)),
                    'recall': float(np.mean(cv_recall)),
                },
                training_time_seconds=elapsed,
                dataset_size=len(texts),
                cross_val_scores=cv_f1.tolist(),
                confidence_interval_95=f1_ci,
                hyperparameters=best_params,
            )
            
        except Exception as e:
            logger.exception(f"Evidence detector training failed: {e}")
            return TrainingResult(
                model_name="evidence_detector",
                success=False,
                error=str(e),
                training_time_seconds=time.time() - start_time
            )


class IntentClassifier_Trainer(BaseTrainer):
    """Trainer for Intent Classifier using Banking77 dataset."""
    
    def train(self, data_path: Path, **kwargs) -> TrainingResult:
        """Train intent classifier on Banking77 dataset."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import cross_val_score, StratifiedKFold
        from sklearn.preprocessing import LabelEncoder
        from sklearn.pipeline import Pipeline
        import joblib
        import pandas as pd
        
        start_time = time.time()
        logger.info("Training Intent Classifier on Banking77...")
        
        try:
            # Load Banking77 dataset
            csv_files = list(data_path.glob("**/*.csv"))
            
            df = None
            for csv_file in csv_files:
                try:
                    df = pd.read_csv(csv_file)
                    if 'text' in df.columns or 'category' in df.columns:
                        break
                except Exception:
                    continue
                    
            if df is None or df.empty:
                # Generate synthetic intent data for manufacturing domain
                logger.info("Generating manufacturing intent dataset...")
                
                intents = {
                    'check_inventory': [
                        "what's the inventory level for part ABC123",
                        "how many units do we have in stock",
                        "check stock for raw materials",
                        "inventory status for finished goods",
                        "are we running low on component XYZ",
                    ],
                    'report_quality_issue': [
                        "I found a defect on the production line",
                        "quality issue with batch 2024-001",
                        "reporting a non-conformance",
                        "surface scratch on finished product",
                        "dimensional tolerance out of spec",
                    ],
                    'request_maintenance': [
                        "machine 5 needs maintenance",
                        "schedule preventive maintenance for press A",
                        "equipment breakdown on line 3",
                        "vibration alarm on motor",
                        "hydraulic leak detected",
                    ],
                    'view_production_status': [
                        "what's the production status today",
                        "how many units completed this shift",
                        "show me the OEE for line 2",
                        "production efficiency report",
                        "cycle time for current job",
                    ],
                    'training_inquiry': [
                        "when is my next training due",
                        "show my certifications",
                        "I need training on the new process",
                        "competency matrix for my role",
                        "upcoming training schedule",
                    ],
                    'document_search': [
                        "find the work instruction for assembly",
                        "show me the SOP for inspection",
                        "where is the control plan",
                        "search for quality manual",
                        "procedure for changeover",
                    ],
                    'create_report': [
                        "create a new A3 report",
                        "start an 8D for customer complaint",
                        "generate shift report",
                        "submit incident report",
                        "create corrective action",
                    ],
                }
                
                # Expand with variations
                texts = []
                labels = []
                
                variations = [
                    "please {}", "can you {}", "I need to {}", "help me {}",
                    "{} now", "urgent: {}", "{} please", "could you {}",
                ]
                
                import random
                random.seed(42)
                
                for intent, examples in intents.items():
                    for example in examples:
                        texts.append(example)
                        labels.append(intent)
                        # Add variations
                        for _ in range(20):
                            var = random.choice(variations)
                            texts.append(var.format(example))
                            labels.append(intent)
                            
                # Shuffle
                combined = list(zip(texts, labels))
                random.shuffle(combined)
                texts, labels = zip(*combined)
                texts = list(texts)
                labels = list(labels)
            else:
                # Use Banking77 data
                text_col = 'text' if 'text' in df.columns else df.columns[0]
                label_col = 'category' if 'category' in df.columns else df.columns[1]
                texts = df[text_col].tolist()
                labels = df[label_col].tolist()
            
            logger.info(f"Training data: {len(texts)} samples, {len(set(labels))} intents")
            
            # Encode labels
            le = LabelEncoder()
            y = le.fit_transform(labels)
            
            # Build pipeline
            pipeline = Pipeline([
                ('tfidf', TfidfVectorizer(
                    max_features=5000,
                    ngram_range=(1, 3),
                    stop_words='english',
                )),
                ('clf', LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                    class_weight='balanced',
                    n_jobs=-1
                ))
            ])
            
            # Cross-validation
            cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
            cv_f1 = cross_val_score(pipeline, texts, y, cv=cv, scoring='f1_weighted')
            cv_accuracy = cross_val_score(pipeline, texts, y, cv=cv, scoring='accuracy')
            
            # Fit final model
            pipeline.fit(texts, y)
            
            f1_mean = np.mean(cv_f1)
            f1_ci = self._calculate_confidence_interval(cv_f1.tolist())
            
            # Save
            output_dir = self.model_dir / "intent_classifier"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            joblib.dump(pipeline, output_dir / "pipeline.pkl")
            joblib.dump(le, output_dir / "label_encoder.pkl")
            
            # Save intent mapping
            intent_mapping = {str(i): label for i, label in enumerate(le.classes_)}
            with open(output_dir / "intents.json", 'w') as f:
                json.dump(intent_mapping, f, indent=2)
            
            metadata = {
                "trained_at": datetime.now().isoformat(),
                "dataset": "Manufacturing Intent Dataset",
                "samples": len(texts),
                "num_intents": len(set(labels)),
                "metrics": {
                    "f1_weighted": float(f1_mean),
                    "f1_ci_95": [float(f1_ci[0]), float(f1_ci[1])],
                    "accuracy": float(np.mean(cv_accuracy)),
                },
                "cross_validation_folds": 5,
            }
            with open(output_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            elapsed = time.time() - start_time
            
            return TrainingResult(
                model_name="intent_classifier",
                success=True,
                metrics={
                    'f1_weighted': f1_mean,
                    'accuracy': float(np.mean(cv_accuracy)),
                },
                training_time_seconds=elapsed,
                dataset_size=len(texts),
                cross_val_scores=cv_f1.tolist(),
                confidence_interval_95=f1_ci,
            )
            
        except Exception as e:
            logger.exception(f"Intent classifier training failed: {e}")
            return TrainingResult(
                model_name="intent_classifier",
                success=False,
                error=str(e),
                training_time_seconds=time.time() - start_time
            )


class LessonRecommender_Trainer(BaseTrainer):
    """Trainer for Lesson Recommendation System."""
    
    def train(self, data_path: Path, **kwargs) -> TrainingResult:
        """Train lesson recommender with synthetic data."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import joblib
        
        start_time = time.time()
        logger.info("Training Lesson Recommender...")
        
        try:
            # Generate synthetic manufacturing training lesson data
            import random
            random.seed(42)
            
            lesson_templates = [
                {"title": "Lean Manufacturing Fundamentals", "tags": ["lean", "tps", "waste reduction"], 
                 "role": "all", "level": "beginner"},
                {"title": "5S Workplace Organization", "tags": ["5s", "workplace", "organization"],
                 "role": "all", "level": "beginner"},
                {"title": "Kaizen Continuous Improvement", "tags": ["kaizen", "continuous improvement", "pdca"],
                 "role": "all", "level": "intermediate"},
                {"title": "Statistical Process Control", "tags": ["spc", "statistics", "control charts"],
                 "role": "quality", "level": "advanced"},
                {"title": "Root Cause Analysis Methods", "tags": ["rca", "5 why", "fishbone", "8d"],
                 "role": "quality", "level": "intermediate"},
                {"title": "Predictive Maintenance Basics", "tags": ["maintenance", "predictive", "reliability"],
                 "role": "maintenance", "level": "intermediate"},
                {"title": "Machine Safety Protocols", "tags": ["safety", "lockout", "tagout"],
                 "role": "all", "level": "beginner"},
                {"title": "Quality Inspection Techniques", "tags": ["inspection", "measurement", "quality"],
                 "role": "quality", "level": "beginner"},
                {"title": "Problem Solving with A3", "tags": ["a3", "problem solving", "toyota"],
                 "role": "all", "level": "intermediate"},
                {"title": "Value Stream Mapping", "tags": ["vsm", "value stream", "process mapping"],
                 "role": "engineering", "level": "advanced"},
            ]
            
            # Expand to 100 lessons
            lessons = []
            for i in range(100):
                base = random.choice(lesson_templates)
                lesson = {
                    "id": f"lesson_{i:03d}",
                    "title": f"{base['title']} - Module {i // 10 + 1}",
                    "description": f"Comprehensive training on {base['title'].lower()} concepts and applications.",
                    "tags": base['tags'] + [f"module{i // 10 + 1}"],
                    "role": base['role'],
                    "level": base['level'],
                }
                lessons.append(lesson)
            
            # Generate user completions (for collaborative filtering)
            user_completions = []
            for user_id in range(50):
                # Each user completes 5-20 random lessons
                completed = random.sample(range(100), random.randint(5, 20))
                for lesson_idx in completed:
                    user_completions.append({
                        "user_id": f"user_{user_id:03d}",
                        "lesson_id": f"lesson_{lesson_idx:03d}",
                        "score": random.uniform(0.6, 1.0),
                    })
            
            logger.info(f"Generated {len(lessons)} lessons, {len(user_completions)} completions")
            
            # Build content-based embeddings
            lesson_texts = [
                f"{l['title']} {l['description']} {' '.join(l['tags'])}"
                for l in lessons
            ]
            
            tfidf = TfidfVectorizer(
                max_features=500,
                stop_words='english',
                ngram_range=(1, 2)
            )
            lesson_embeddings = tfidf.fit_transform(lesson_texts).toarray()
            
            # Build collaborative filtering matrix
            import pandas as pd
            completion_df = pd.DataFrame(user_completions)
            user_ids = list(set(completion_df['user_id']))
            lesson_ids = [l['id'] for l in lessons]
            
            # User-lesson matrix
            user_lesson_matrix = np.zeros((len(user_ids), len(lesson_ids)))
            user_idx_map = {uid: i for i, uid in enumerate(user_ids)}
            lesson_idx_map = {lid: i for i, lid in enumerate(lesson_ids)}
            
            for _, row in completion_df.iterrows():
                ui = user_idx_map[row['user_id']]
                li = lesson_idx_map[row['lesson_id']]
                user_lesson_matrix[ui, li] = row['score']
            
            user_similarity = cosine_similarity(user_lesson_matrix)
            
            # Evaluate: measure coverage and diversity
            coverage = np.sum(user_lesson_matrix > 0) / (len(user_ids) * len(lesson_ids))
            
            # Save
            output_dir = self.model_dir / "lesson_recommender"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            joblib.dump(tfidf, output_dir / "tfidf_vectorizer.pkl")
            joblib.dump(lesson_embeddings, output_dir / "lesson_embeddings.pkl")
            joblib.dump(lesson_ids, output_dir / "lesson_ids.pkl")
            joblib.dump(user_similarity, output_dir / "user_similarity.pkl")
            
            with open(output_dir / "lessons.json", 'w') as f:
                json.dump(lessons, f, indent=2)
            
            metadata = {
                "trained_at": datetime.now().isoformat(),
                "dataset": "Synthetic Manufacturing Training Data",
                "num_lessons": len(lessons),
                "num_users": len(user_ids),
                "num_completions": len(user_completions),
                "metrics": {
                    "coverage": float(coverage),
                    "embedding_dim": lesson_embeddings.shape[1],
                },
            }
            with open(output_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            elapsed = time.time() - start_time
            
            return TrainingResult(
                model_name="lesson_recommender",
                success=True,
                metrics={
                    'coverage': coverage,
                    'num_lessons': len(lessons),
                },
                training_time_seconds=elapsed,
                dataset_size=len(lessons),
            )
            
        except Exception as e:
            logger.exception(f"Lesson recommender training failed: {e}")
            return TrainingResult(
                model_name="lesson_recommender",
                success=False,
                error=str(e),
                training_time_seconds=time.time() - start_time
            )


class DomainEmbeddings_Trainer(BaseTrainer):
    """Trainer for domain-adapted text embeddings using TSDAE."""
    
    def train(self, data_path: Path, **kwargs) -> TrainingResult:
        """Train domain embeddings using existing pipeline."""
        start_time = time.time()
        logger.info("Training Domain Embeddings (TSDAE)...")
        
        try:
            # Check if corpus exists - try multiple paths
            corpus_dir = data_path
            if not corpus_dir.exists() or not list(corpus_dir.glob("*.txt")):
                # Try relative to script
                corpus_dir = Path(__file__).parent.parent.parent / "cleaned_books"
                
            if not corpus_dir.exists() or not list(corpus_dir.glob("*.txt")):
                # Try absolute path
                corpus_dir = Path("/home/aaron/IdeaProjects/Management-Software/cleaned_books")
                
            if not corpus_dir.exists():
                return TrainingResult(
                    model_name="domain_embeddings",
                    success=False,
                    error=f"Corpus not found: {corpus_dir}"
                )
            
            txt_files = list(corpus_dir.glob("*.txt"))
            if len(txt_files) < 5:
                return TrainingResult(
                    model_name="domain_embeddings",
                    success=False,
                    error=f"Insufficient corpus files: {len(txt_files)}"
                )
            
            # Load sentences
            logger.info(f"Loading corpus from {corpus_dir} ({len(txt_files)} files)")
            train_sentences = []
            
            for book_file in txt_files[:50]:  # Limit for speed
                try:
                    content = book_file.read_text(encoding='utf-8', errors='ignore')
                    # Split by sentences (period followed by space/newline) and by newlines
                    import re
                    # First split by newlines
                    paragraphs = content.split('\n')
                    for para in paragraphs:
                        para = para.strip()
                        if len(para) < 20:
                            continue
                        # Split long paragraphs by sentence boundaries
                        sentences = re.split(r'(?<=[.!?])\s+', para)
                        for sent in sentences:
                            sent = sent.strip()
                            # Filter by length: min 30 chars, max 500 chars
                            if 30 < len(sent) < 500:
                                train_sentences.append(sent)
                except Exception as e:
                    logger.warning(f"Error reading {book_file.name}: {e}")
                    
            train_sentences = train_sentences[:50000]  # Limit for speed
            logger.info(f"Loaded {len(train_sentences):,} sentences")
            
            if len(train_sentences) < 1000:
                return TrainingResult(
                    model_name="domain_embeddings",
                    success=False,
                    error="Insufficient training sentences"
                )
            
            # Train with sentence-transformers TSDAE
            try:
                from sentence_transformers import SentenceTransformer, models, datasets, losses
                from torch.utils.data import DataLoader
                import torch
            except ImportError as e:
                return TrainingResult(
                    model_name="domain_embeddings",
                    success=False,
                    error=f"Missing dependencies: {e}"
                )
            
            # Load base model
            base_model_name = "sentence-transformers/all-MiniLM-L6-v2"
            model = SentenceTransformer(base_model_name)
            
            # Create TSDAE dataset
            tsdae_dataset = datasets.DenoisingAutoEncoderDataset(train_sentences)
            train_dataloader = DataLoader(tsdae_dataset, batch_size=8, shuffle=True)
            
            # TSDAE loss
            train_loss = losses.DenoisingAutoEncoderLoss(
                model,
                decoder_name_or_path=base_model_name,
                tie_encoder_decoder=True
            )
            
            # Train
            epochs = kwargs.get('epochs', 1)
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Training on {device} for {epochs} epoch(s)...")
            
            model.to(device)
            model.fit(
                train_objectives=[(train_dataloader, train_loss)],
                epochs=epochs,
                show_progress_bar=True,
                warmup_steps=100,
            )
            
            # Save
            output_dir = self.model_dir / "sensei-mfg-adapter" / "final"
            output_dir.mkdir(parents=True, exist_ok=True)
            model.save(str(output_dir))
            
            # Evaluate: compute average embedding quality
            test_sentences = train_sentences[:100]
            embeddings = model.encode(test_sentences)
            
            # Compute intra-cluster similarity (higher = better domain adaptation)
            from sklearn.metrics.pairwise import cosine_similarity
            sim_matrix = cosine_similarity(embeddings)
            avg_sim = np.mean(sim_matrix[np.triu_indices(len(sim_matrix), k=1)])
            
            metadata = {
                "trained_at": datetime.now().isoformat(),
                "base_model": base_model_name,
                "corpus_files": len(txt_files),
                "training_sentences": len(train_sentences),
                "epochs": epochs,
                "device": device,
                "metrics": {
                    "avg_cosine_similarity": float(avg_sim),
                },
            }
            with open(output_dir / "training_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            elapsed = time.time() - start_time
            
            return TrainingResult(
                model_name="domain_embeddings",
                success=True,
                metrics={
                    'avg_cosine_similarity': float(avg_sim),
                    'training_sentences': len(train_sentences),
                },
                training_time_seconds=elapsed,
                dataset_size=len(train_sentences),
            )
            
        except Exception as e:
            logger.exception(f"Domain embeddings training failed: {e}")
            return TrainingResult(
                model_name="domain_embeddings",
                success=False,
                error=str(e),
                training_time_seconds=time.time() - start_time
            )


# =============================================================================
# Main Training Orchestrator
# =============================================================================

class TrainingOrchestrator:
    """Orchestrates training of all models."""
    
    TRAINERS = {
        'cbm': ('ai4i_2020', CBMPredictor_Trainer),
        'evidence': ('twenty_newsgroups', EvidenceDetector_Trainer),
        'intent': ('banking77', IntentClassifier_Trainer),
        'lessons': ('lean_manufacturing_corpus', LessonRecommender_Trainer),
        'embeddings': ('lean_manufacturing_corpus', DomainEmbeddings_Trainer),
    }
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.model_dir = base_dir / "models"
        self.cache_dir = base_dir / "datasets_cache"
        self.downloader = DatasetDownloader(self.cache_dir)
        self.results: List[TrainingResult] = []
        
    def train_all(self, models: Optional[List[str]] = None) -> List[TrainingResult]:
        """Train all or specified models."""
        if models is None:
            models = list(self.TRAINERS.keys())
            
        logger.info(f"Training {len(models)} model(s): {models}")
        
        for model_name in models:
            if model_name not in self.TRAINERS:
                logger.warning(f"Unknown model: {model_name}")
                continue
                
            dataset_key, trainer_class = self.TRAINERS[model_name]
            
            # Download dataset
            if dataset_key in DATASETS:
                config = DATASETS[dataset_key]
                try:
                    data_path = self.downloader.download(config)
                except Exception as e:
                    logger.error(f"Failed to download {dataset_key}: {e}")
                    self.results.append(TrainingResult(
                        model_name=model_name,
                        success=False,
                        error=f"Dataset download failed: {e}"
                    ))
                    continue
            else:
                data_path = self.cache_dir
            
            # Train model
            trainer = trainer_class(self.model_dir)
            result = trainer.train(data_path)
            self.results.append(result)
            
            if result.success:
                f1_val = result.metrics.get('f1_weighted', result.metrics.get('f1', result.metrics.get('coverage', 0)))
                if isinstance(f1_val, (int, float)):
                    logger.info(f"✓ {model_name}: metric={f1_val:.4f}")
                else:
                    logger.info(f"✓ {model_name}: trained successfully")
            else:
                logger.error(f"✗ {model_name}: {result.error}")
                
        return self.results
    
    def generate_report(self) -> str:
        """Generate training report."""
        report_lines = [
            "=" * 80,
            "AI/ML MODEL TRAINING REPORT",
            f"Generated: {datetime.now().isoformat()}",
            "=" * 80,
            "",
        ]
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        report_lines.append(f"SUMMARY: {len(successful)}/{len(self.results)} models trained successfully\n")
        
        for result in self.results:
            report_lines.append("-" * 60)
            report_lines.append(f"Model: {result.model_name}")
            report_lines.append(f"Status: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
            
            if result.success:
                report_lines.append(f"Training Time: {result.training_time_seconds:.1f}s")
                report_lines.append(f"Dataset Size: {result.dataset_size:,}")
                report_lines.append(f"Metrics: {json.dumps(result.metrics, indent=2)}")
                
                if result.confidence_interval_95 != (0.0, 0.0):
                    ci = result.confidence_interval_95
                    report_lines.append(f"95% Confidence Interval: [{ci[0]:.4f}, {ci[1]:.4f}]")
                    
                if result.cross_val_scores:
                    report_lines.append(f"Cross-Val Scores: {[f'{s:.4f}' for s in result.cross_val_scores]}")
                    
                if result.hyperparameters:
                    report_lines.append(f"Hyperparameters: {json.dumps(result.hyperparameters, indent=2)}")
            else:
                report_lines.append(f"Error: {result.error}")
                
            report_lines.append("")
        
        return "\n".join(report_lines)
    
    def save_report(self, filepath: Path):
        """Save training report to file."""
        report = self.generate_report()
        filepath.write_text(report)
        logger.info(f"Report saved to: {filepath}")


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Train all AI/ML models for Sensei OS")
    parser.add_argument('--all', action='store_true', help='Train all models')
    parser.add_argument('--model', type=str, choices=['cbm', 'evidence', 'intent', 'lessons', 'embeddings'],
                        help='Train specific model')
    parser.add_argument('--output', type=str, default='backend', help='Output directory')
    parser.add_argument('--report', type=str, default='TRAINING_REPORT.md', help='Report filename')
    
    args = parser.parse_args()
    
    base_dir = Path(args.output)
    if not base_dir.is_absolute():
        base_dir = Path(__file__).parent.parent.parent / base_dir
        
    orchestrator = TrainingOrchestrator(base_dir)
    
    if args.model:
        models = [args.model]
    elif args.all:
        models = None  # All models
    else:
        # Default: train most important models
        models = ['cbm', 'evidence', 'intent']
    
    results = orchestrator.train_all(models)
    
    # Save report
    report_path = base_dir.parent / args.report
    orchestrator.save_report(report_path)
    
    # Print summary
    print("\n" + orchestrator.generate_report())
    
    # Exit with error if any failed
    if any(not r.success for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
