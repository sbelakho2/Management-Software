"""
Machine Learning: Missing Evidence Detection

Detects when A3 problem-solving reports are missing critical evidence:
- Root cause analysis without data
- Countermeasures without validation
- 5-Why analysis with insufficient depth
- Missing before/after comparisons
- Incomplete documentation of actions taken
"""

import re
from typing import List, Dict, Optional, Tuple, Any, TYPE_CHECKING
from datetime import datetime
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
import joblib
import logging
from pathlib import Path

if TYPE_CHECKING:
    from sensei.models.a3 import A3, A3Section

from sensei.core.config import settings

logger = logging.getLogger(__name__)


class MissingEvidenceDetector:
    """
    ML model to detect missing or insufficient evidence in A3 reports.
    
    Uses rule-based + ML hybrid approach:
    - Rule-based: Check for required sections, data, images
    - ML: Classify text quality and completeness
    """

    # Required evidence patterns
    EVIDENCE_PATTERNS = {
        'numerical_data': r'\d+\.?\d*\s*(%|ppm|units|pieces|hours|days)',
        'before_after': r'(before|after|baseline|current|improved)',
        'root_cause_keyword': r'(root cause|5 why|fishbone|ishikawa|pareto)',
        'validation': r'(validate|verify|confirm|test|measure)',
        'action_verb': r'(implement|install|train|modify|replace|update)',
    }

    # Section completeness thresholds
    MIN_SECTION_LENGTH = {
        'background': 100,      # chars
        'current_condition': 150,
        'goal': 50,
        'root_cause_analysis': 200,
        'countermeasures': 150,
        'implementation_plan': 100,
        'followup': 80,
    }

    def __init__(self, model_path: Optional[Path] = None):
        default_path = getattr(settings, 'ML_MODEL_PATH', '/tmp/ml_models')
        self.model_path = model_path or Path(default_path) / "evidence_detector"
        self.text_classifier: Optional[RandomForestClassifier] = None
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        
    def train(
        self,
        labeled_reports: List[Tuple[Any, Dict[str, bool]]],
    ) -> Dict[str, float]:
        """
        Train the missing evidence detector.
        
        Args:
            labeled_reports: List of (A3, evidence_labels) where
                evidence_labels = {
                    'has_numerical_data': bool,
                    'has_root_cause_evidence': bool,
                    'has_validation': bool,
                    ...
                }
        
        Returns:
            Training metrics: accuracy, precision, recall, f1
        """
        logger.info(f"Training evidence detector with {len(labeled_reports)} reports")
        
        # Extract features and labels
        X_texts = []
        y_labels = []
        
        for report, labels in labeled_reports:
            # Combine all text sections
            text = self._extract_text_from_report(report)
            X_texts.append(text)
            
            # Create binary label (0 = missing evidence, 1 = complete)
            is_complete = all(labels.values())
            y_labels.append(1 if is_complete else 0)
        
        # Train TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=300,
            ngram_range=(1, 3),
            stop_words='english',
        )
        X_features = self.tfidf_vectorizer.fit_transform(X_texts).toarray()
        
        # Add rule-based features
        X_rule_features = np.array([
            self._extract_rule_features(text) for text in X_texts
        ])
        
        # Combine features
        X_combined = np.hstack([X_features, X_rule_features])
        
        # Train classifier
        self.text_classifier = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
        )
        self.text_classifier.fit(X_combined, y_labels)
        
        # Evaluate
        from sklearn.model_selection import cross_val_score
        cv_scores = cross_val_score(
            self.text_classifier,
            X_combined,
            y_labels,
            cv=5,
            scoring='f1',
        )
        
        # Save model
        self.model_path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.text_classifier, self.model_path / "classifier.pkl")
        joblib.dump(self.tfidf_vectorizer, self.model_path / "tfidf.pkl")
        
        metrics = {
            'f1_mean': float(np.mean(cv_scores)),
            'f1_std': float(np.std(cv_scores)),
        }
        
        logger.info(f"Model trained. F1 score: {metrics['f1_mean']:.3f} ± {metrics['f1_std']:.3f}")
        return metrics
    
    def load(self) -> None:
        """Load trained model from disk."""
        logger.info(f"Loading evidence detector from {self.model_path}")
        
        self.text_classifier = joblib.load(self.model_path / "classifier.pkl")
        self.tfidf_vectorizer = joblib.load(self.model_path / "tfidf.pkl")
        
        logger.info("Evidence detector loaded successfully")
    
    def detect_missing_evidence(
        self,
        report: Any,
    ) -> Dict[str, Any]:
        """
        Detect missing evidence in an A3 report.
        
        Returns:
            {
                'overall_score': float (0-1, higher = more complete),
                'is_complete': bool,
                'missing_items': List[Dict],
                'warnings': List[str],
                'suggestions': List[str],
            }
        """
        results = {
            'overall_score': 0.0,
            'is_complete': True,
            'missing_items': [],
            'warnings': [],
            'suggestions': [],
        }
        
        # 1. Check section completeness
        section_scores = self._check_section_completeness(report)
        for section, score in section_scores.items():
            if score < 0.5:
                results['missing_items'].append({
                    'type': 'incomplete_section',
                    'section': section,
                    'score': score,
                    'message': f"Section '{section}' is incomplete or too brief",
                })
                results['is_complete'] = False
        
        # 2. Check for numerical evidence
        has_numerical = self._check_numerical_evidence(report)
        if not has_numerical:
            results['missing_items'].append({
                'type': 'missing_data',
                'message': 'No numerical data found (measurements, metrics, percentages)',
            })
            results['warnings'].append('Add quantitative data to support your analysis')
        
        # 3. Check for root cause evidence
        has_root_cause = self._check_root_cause_evidence(report)
        if not has_root_cause:
            results['missing_items'].append({
                'type': 'missing_root_cause',
                'message': 'Root cause analysis lacks evidence or methodology',
            })
            results['suggestions'].append('Include 5-Why analysis or fishbone diagram')
        
        # 4. Check for validation/verification
        has_validation = self._check_validation_evidence(report)
        if not has_validation:
            results['missing_items'].append({
                'type': 'missing_validation',
                'message': 'Countermeasures not validated with data',
            })
            results['suggestions'].append('Add before/after metrics to validate effectiveness')
        
        # 5. Check for attachments (images, charts)
        if not report.attachments or len(report.attachments) == 0:
            results['warnings'].append('No attachments found. Consider adding photos, charts, or diagrams')
        
        # 6. Use ML classifier for overall assessment
        if self.text_classifier and self.tfidf_vectorizer:
            ml_score = self._ml_predict(report)
            results['overall_score'] = ml_score
            
            if ml_score < 0.6:
                results['is_complete'] = False
                results['warnings'].append(
                    f'Overall evidence score: {ml_score:.1%}. Consider adding more detail and data.'
                )
        else:
            # Fallback: simple rule-based score
            results['overall_score'] = self._calculate_rule_based_score(section_scores, has_numerical, has_root_cause, has_validation)
        
        return results
    
    def _extract_text_from_report(self, report: Any) -> str:
        """Extract all text content from report."""
        texts = [
            report.title or '',
            report.background or '',
            report.current_condition or '',
            report.goal or '',
            report.root_cause_analysis or '',
            report.countermeasures or '',
            report.implementation_plan or '',
            report.followup or '',
        ]
        return ' '.join(texts)
    
    def _extract_rule_features(self, text: str) -> np.ndarray:
        """Extract rule-based features as numeric vector."""
        features = []
        
        # Count pattern matches
        for pattern_name, pattern in self.EVIDENCE_PATTERNS.items():
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            features.append(matches)
        
        # Text length
        features.append(len(text))
        
        # Word count
        features.append(len(text.split()))
        
        return np.array(features)
    
    def _check_section_completeness(self, report: Any) -> Dict[str, float]:
        """
        Check completeness of each A3 section.
        
        Returns dict mapping section_name -> score (0-1)
        """
        scores = {}
        
        for section, min_length in self.MIN_SECTION_LENGTH.items():
            text = getattr(report, section, '') or ''
            length = len(text)
            
            # Score based on length relative to minimum
            if length >= min_length:
                scores[section] = 1.0
            else:
                scores[section] = length / min_length
        
        return scores
    
    def _check_numerical_evidence(self, report: Any) -> bool:
        """Check if report contains numerical data/metrics."""
        text = self._extract_text_from_report(report)
        pattern = self.EVIDENCE_PATTERNS['numerical_data']
        matches = re.findall(pattern, text, re.IGNORECASE)
        return len(matches) >= 3  # At least 3 numeric data points
    
    def _check_root_cause_evidence(self, report: Any) -> bool:
        """Check if report contains root cause analysis evidence."""
        text = report.root_cause_analysis or ''
        
        # Check for methodology keywords
        pattern = self.EVIDENCE_PATTERNS['root_cause_keyword']
        has_methodology = bool(re.search(pattern, text, re.IGNORECASE))
        
        # Check for sufficient detail (at least 150 chars)
        has_detail = len(text) >= 150
        
        return has_methodology and has_detail
    
    def _check_validation_evidence(self, report: Any) -> bool:
        """Check if countermeasures have validation evidence."""
        text = f"{report.countermeasures or ''} {report.followup or ''}"
        
        # Check for validation keywords
        validation_pattern = self.EVIDENCE_PATTERNS['validation']
        has_validation = bool(re.search(validation_pattern, text, re.IGNORECASE))
        
        # Check for before/after comparison
        before_after_pattern = self.EVIDENCE_PATTERNS['before_after']
        has_comparison = bool(re.search(before_after_pattern, text, re.IGNORECASE))
        
        return has_validation or has_comparison
    
    def _ml_predict(self, report: Any) -> float:
        """Use ML model to predict evidence completeness score."""
        text = self._extract_text_from_report(report)
        
        # Extract features
        text_features = self.tfidf_vectorizer.transform([text]).toarray()
        rule_features = self._extract_rule_features(text).reshape(1, -1)
        combined_features = np.hstack([text_features, rule_features])
        
        # Predict probability of being complete
        proba = self.text_classifier.predict_proba(combined_features)[0]
        return float(proba[1])  # Probability of class 1 (complete)
    
    def _calculate_rule_based_score(
        self,
        section_scores: Dict[str, float],
        has_numerical: bool,
        has_root_cause: bool,
        has_validation: bool,
    ) -> float:
        """Calculate overall score using rule-based approach."""
        # Section completeness (50%)
        avg_section_score = np.mean(list(section_scores.values()))
        
        # Evidence presence (50%)
        evidence_score = (
            (1.0 if has_numerical else 0.0) +
            (1.0 if has_root_cause else 0.0) +
            (1.0 if has_validation else 0.0)
        ) / 3.0
        
        return (avg_section_score * 0.5) + (evidence_score * 0.5)


# Batch analysis pipeline
def analyze_all_reports(
    detector: MissingEvidenceDetector,
    reports: List[Any],
) -> Dict[str, Dict]:
    """
    Analyze all A3 reports for missing evidence.
    
    Returns dict mapping report_id -> analysis results
    """
    logger.info(f"Analyzing {len(reports)} A3 reports for missing evidence")
    
    results = {}
    for report in reports:
        try:
            analysis = detector.detect_missing_evidence(report)
            results[report.id] = analysis
        except Exception as e:
            logger.error(f"Error analyzing report {report.id}: {e}")
            results[report.id] = {
                'error': str(e),
                'overall_score': 0.0,
                'is_complete': False,
            }
    
    # Summary statistics
    complete_count = sum(1 for r in results.values() if r.get('is_complete', False))
    avg_score = np.mean([r.get('overall_score', 0) for r in results.values()])
    
    logger.info(f"Analysis complete. {complete_count}/{len(reports)} reports are complete. Avg score: {avg_score:.2f}")
    
    return results
