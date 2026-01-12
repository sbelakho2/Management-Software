"""
Machine Learning: Condition-Based Maintenance Suggestions

Suggests preventive maintenance actions based on:
- Equipment condition monitoring data
- Historical failure patterns
- Operating hours and cycles
- Environmental factors (temperature, vibration, etc.)
- Predictive anomaly detection
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from pathlib import Path

from sensei.core.config import settings

# Type hints for models that may not exist yet
if TYPE_CHECKING:
    from sensei.models.production import Equipment, MaintenanceRecord, ConditionReading

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ConditionBasedMaintenancePredictor:
    """
    ML model for condition-based maintenance predictions.
    
    Combines:
    1. Anomaly detection (Isolation Forest) for sensor data
    2. Failure prediction (Random Forest) based on historical patterns
    3. Rule-based thresholds for critical parameters
    """

    # Critical thresholds for immediate action
    CRITICAL_THRESHOLDS = {
        'temperature': {'max': 80, 'unit': '°C'},       # Equipment temperature
        'vibration': {'max': 10, 'unit': 'mm/s'},       # Vibration amplitude
        'pressure': {'max': 150, 'unit': 'psi'},        # Hydraulic pressure
        'current': {'max': 20, 'unit': 'A'},            # Motor current
        'noise': {'max': 85, 'unit': 'dB'},             # Acoustic noise
    }

    def __init__(self, model_path: Optional[Path] = None):
        default_path = getattr(settings, 'ML_MODEL_PATH', '/tmp/ml_models')
        self.model_path = model_path or Path(default_path) / "cbm_predictor"
        self.failure_classifier: Optional[RandomForestClassifier] = None
        self.anomaly_detector: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        
    def train(
        self,
        equipment_list: List[Any],
        maintenance_records: List[Any],
        condition_readings: List[Any],
    ) -> Dict[str, Any]:
        """
        Train the CBM prediction models synchronously.
        """
        logger.info(f"Training CBM predictor with {len(equipment_list)} equipment")
        
        # Build training dataset
        X_train, y_train = self._build_training_data(
            equipment_list,
            maintenance_records,
            condition_readings,
        )
        
        if len(X_train) < 100:
            logger.warning(f"Insufficient training data: {len(X_train)} samples. Need at least 100.")
            return {'error': 'insufficient_data'}
        
        # Normalize features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X_train)
        
        # Train failure predictor
        self.failure_classifier = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            class_weight='balanced',
            random_state=42,
        )
        self.failure_classifier.fit(X_scaled, y_train)
        
        # Train anomaly detector (unsupervised)
        self.anomaly_detector = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
        )
        self.anomaly_detector.fit(X_scaled)
        
        # Evaluate
        from sklearn.model_selection import cross_val_score
        cv_scores = cross_val_score(
            self.failure_classifier,
            X_scaled,
            y_train,
            cv=5,
            scoring='f1_weighted',
        )
        
        # Save models
        self.model_path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.failure_classifier, self.model_path / "failure_classifier.pkl")
        joblib.dump(self.anomaly_detector, self.model_path / "anomaly_detector.pkl")
        joblib.dump(self.scaler, self.model_path / "scaler.pkl")
        
        metrics = {
            'f1_mean': float(np.mean(cv_scores)),
            'f1_std': float(np.std(cv_scores)),
            'training_samples': len(X_train),
        }
        
        logger.info(f"CBM model trained. F1: {metrics['f1_mean']:.3f} ± {metrics['f1_std']:.3f}")
        return metrics

    def train_async(
        self,
        equipment_list: List[Any],
        maintenance_records: List[Any],
        condition_readings: List[Any],
    ) -> str:
        """
        Offload training to Celery.
        """
        from sensei.tasks.ml_tasks import run_model_training
        
        # We need to serialize data or pass references if Celery can access DB
        # For now, we'll pass the data directly (assuming it's not too large for Redis)
        # In production, we'd pass query parameters or IDs.
        
        task = run_model_training.delay(
            model_name="cbm_predictor",
            model_class_path="sensei.ml.cbm_predictor.ConditionBasedMaintenancePredictor",
            train_data={
                "equipment": equipment_list,
                "records": maintenance_records,
                "readings": condition_readings
            },
            eval_data=None,
            hyperparameters={
                "n_estimators": 200,
                "max_depth": 15
            }
        )
        return task.id
    
    def load(self) -> None:
        """Load trained models from disk."""
        logger.info(f"Loading CBM predictor from {self.model_path}")
        
        self.failure_classifier = joblib.load(self.model_path / "failure_classifier.pkl")
        self.anomaly_detector = joblib.load(self.model_path / "anomaly_detector.pkl")
        self.scaler = joblib.load(self.model_path / "scaler.pkl")
        
        logger.info("CBM predictor loaded successfully")
    
    def predict_maintenance_needs(
        self,
        equipment: Any,
        recent_readings: List[Any],
        maintenance_history: List[Any],
    ) -> Dict[str, Any]:
        """
        Predict maintenance needs for equipment.
        
        Returns:
            {
                'risk_level': 'low' | 'medium' | 'high' | 'critical',
                'failure_probability': float (0-1),
                'is_anomaly': bool,
                'recommendations': List[Dict],
                'reasons': List[str],
                'estimated_time_to_failure': Optional[int],  # days
            }
        """
        if not recent_readings:
            return {
                'risk_level': 'unknown',
                'failure_probability': 0.0,
                'is_anomaly': False,
                'recommendations': [],
                'reasons': ['No condition data available'],
            }
        
        # Extract features
        features = self._extract_features(equipment, recent_readings, maintenance_history)
        
        # Check critical thresholds first
        critical_issues = self._check_critical_thresholds(recent_readings)
        if critical_issues:
            return {
                'risk_level': 'critical',
                'failure_probability': 1.0,
                'is_anomaly': True,
                'recommendations': [
                    {
                        'action': 'immediate_shutdown',
                        'reason': issue['reason'],
                        'parameter': issue['parameter'],
                        'value': issue['value'],
                    }
                    for issue in critical_issues
                ],
                'reasons': [issue['reason'] for issue in critical_issues],
                'estimated_time_to_failure': 0,
            }
        
        # ML predictions
        if self.failure_classifier and self.scaler:
            X = self.scaler.transform([features])
            
            # Failure probability
            failure_prob = self.failure_classifier.predict_proba(X)[0][1]
            
            # Anomaly detection
            is_anomaly = self.anomaly_detector.predict(X)[0] == -1
            
            # Risk level
            if failure_prob >= 0.8 or is_anomaly:
                risk_level = 'high'
            elif failure_prob >= 0.5:
                risk_level = 'medium'
            else:
                risk_level = 'low'
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                equipment,
                recent_readings,
                maintenance_history,
                failure_prob,
                is_anomaly,
            )
            
            # Estimate time to failure
            ttf = self._estimate_time_to_failure(failure_prob, equipment, maintenance_history)
            
            return {
                'risk_level': risk_level,
                'failure_probability': float(failure_prob),
                'is_anomaly': is_anomaly,
                'recommendations': recommendations,
                'reasons': self._explain_prediction(features, recent_readings),
                'estimated_time_to_failure': ttf,
            }
        else:
            # Fallback: rule-based only
            return self._rule_based_assessment(equipment, recent_readings, maintenance_history)
    
    def _build_training_data(
        self,
        equipment_list: List[Any],
        maintenance_records: List[Any],
        condition_readings: List[Any],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Build training dataset from historical data.
        
        Returns (X, y) where:
        - X: feature matrix
        - y: binary labels (0 = no failure, 1 = failure within 7 days)
        """
        X = []
        y = []
        
        # Group data by equipment
        equipment_readings = {}
        equipment_maintenance = {}
        
        for reading in condition_readings:
            if reading.equipment_id not in equipment_readings:
                equipment_readings[reading.equipment_id] = []
            equipment_readings[reading.equipment_id].append(reading)
        
        for record in maintenance_records:
            if record.equipment_id not in equipment_maintenance:
                equipment_maintenance[record.equipment_id] = []
            equipment_maintenance[record.equipment_id].append(record)
        
        # For each equipment, create training samples
        for equipment in equipment_list:
            readings = equipment_readings.get(equipment.id, [])
            maintenance = equipment_maintenance.get(equipment.id, [])
            
            if not readings:
                continue
            
            # Sort by timestamp
            readings.sort(key=lambda r: r.timestamp)
            maintenance.sort(key=lambda r: r.date)
            
            # Create samples: look at readings and label based on future maintenance
            for i in range(len(readings) - 1):
                reading = readings[i]
                
                # Extract features for this time point
                historical_readings = readings[:i+1]
                historical_maintenance = [m for m in maintenance if m.date <= reading.timestamp]
                
                features = self._extract_features(equipment, historical_readings[-10:], historical_maintenance[-5:])
                
                # Label: was there a failure/maintenance within next 7 days?
                future_date = reading.timestamp + timedelta(days=7)
                future_maintenance = [
                    m for m in maintenance
                    if reading.timestamp < m.date <= future_date and m.maintenance_type in ['repair', 'breakdown']
                ]
                
                label = 1 if future_maintenance else 0
                
                X.append(features)
                y.append(label)
        
        return np.array(X), np.array(y)
    
    def _extract_features(
        self,
        equipment: Any,
        recent_readings: List[Any],
        maintenance_history: List[Any],
    ) -> np.ndarray:
        """
        Extract feature vector for ML models.
        
        Features:
        - Latest sensor readings (temperature, vibration, etc.)
        - Statistical features (mean, std, trend over last N readings)
        - Equipment age and operating hours
        - Time since last maintenance
        - Maintenance frequency
        """
        features = []
        
        # 1. Latest sensor readings (6 features)
        latest = recent_readings[-1] if recent_readings else None
        if latest:
            features.extend([
                latest.temperature or 0,
                latest.vibration or 0,
                latest.pressure or 0,
                latest.current or 0,
                latest.noise or 0,
                latest.operating_hours or 0,
            ])
        else:
            features.extend([0] * 6)
        
        # 2. Statistical features over recent readings (12 features)
        if len(recent_readings) >= 2:
            temps = [r.temperature for r in recent_readings if r.temperature]
            vibs = [r.vibration for r in recent_readings if r.vibration]
            
            features.extend([
                np.mean(temps) if temps else 0,
                np.std(temps) if temps else 0,
                np.mean(vibs) if vibs else 0,
                np.std(vibs) if vibs else 0,
            ])
            
            # Trend (slope of linear fit)
            if len(temps) >= 3:
                x = np.arange(len(temps))
                temp_slope = np.polyfit(x, temps, 1)[0]
                features.append(temp_slope)
            else:
                features.append(0)
            
            if len(vibs) >= 3:
                x = np.arange(len(vibs))
                vib_slope = np.polyfit(x, vibs, 1)[0]
                features.append(vib_slope)
            else:
                features.append(0)
        else:
            features.extend([0] * 6)
        
        # 3. Equipment characteristics (3 features)
        now = _utcnow()
        equipment_age_days = (now - equipment.installation_date).days if equipment.installation_date else 0
        features.extend([
            equipment_age_days,
            equipment.total_operating_hours or 0,
            equipment.total_cycles or 0,
        ])
        
        # 4. Maintenance history (3 features)
        if maintenance_history:
            latest_maintenance = maintenance_history[-1]
            days_since_maintenance = (now - latest_maintenance.date).days
            maintenance_count = len(maintenance_history)
            avg_maintenance_interval = equipment_age_days / maintenance_count if maintenance_count > 0 else 0
        else:
            days_since_maintenance = equipment_age_days
            maintenance_count = 0
            avg_maintenance_interval = 0
        
        features.extend([
            days_since_maintenance,
            maintenance_count,
            avg_maintenance_interval,
        ])
        
        return np.array(features)
    
    def _check_critical_thresholds(
        self,
        recent_readings: List[Any],
    ) -> List[Dict]:
        """Check if any readings exceed critical thresholds."""
        critical_issues = []
        
        if not recent_readings:
            return critical_issues
        
        latest = recent_readings[-1]
        
        for param, threshold_info in self.CRITICAL_THRESHOLDS.items():
            value = getattr(latest, param, None)
            if value and value > threshold_info['max']:
                critical_issues.append({
                    'parameter': param,
                    'value': value,
                    'threshold': threshold_info['max'],
                    'unit': threshold_info['unit'],
                    'reason': f"{param.title()} ({value}{threshold_info['unit']}) exceeds critical threshold ({threshold_info['max']}{threshold_info['unit']})",
                })
        
        return critical_issues
    
    def _generate_recommendations(
        self,
        equipment: Any,
        recent_readings: List[Any],
        maintenance_history: List[Any],
        failure_prob: float,
        is_anomaly: bool,
    ) -> List[Dict]:
        """Generate maintenance recommendations based on predictions."""
        recommendations = []
        
        if failure_prob >= 0.8:
            recommendations.append({
                'priority': 'high',
                'action': 'schedule_inspection',
                'reason': 'High probability of failure detected',
                'timeframe': 'within 24 hours',
            })
        elif failure_prob >= 0.5:
            recommendations.append({
                'priority': 'medium',
                'action': 'schedule_inspection',
                'reason': 'Elevated failure risk',
                'timeframe': 'within 3 days',
            })
        
        if is_anomaly:
            recommendations.append({
                'priority': 'medium',
                'action': 'investigate_anomaly',
                'reason': 'Unusual condition readings detected',
                'timeframe': 'within 48 hours',
            })
        
        # Check operating hours
        if equipment.total_operating_hours:
            if equipment.total_operating_hours >= equipment.recommended_maintenance_hours * 0.9:
                recommendations.append({
                    'priority': 'medium',
                    'action': 'schedule_preventive_maintenance',
                    'reason': f'Approaching recommended maintenance interval ({equipment.total_operating_hours}h)',
                    'timeframe': 'within 1 week',
                })
        
        # Check time since last maintenance
        if maintenance_history:
            days_since = (_utcnow() - maintenance_history[-1].date).days
            if days_since >= 90:
                recommendations.append({
                    'priority': 'low',
                    'action': 'schedule_routine_maintenance',
                    'reason': f'No maintenance in {days_since} days',
                    'timeframe': 'within 2 weeks',
                })
        
        return recommendations
    
    def _explain_prediction(
        self,
        features: np.ndarray,
        recent_readings: List[Any],
    ) -> List[str]:
        """Generate human-readable explanations for the prediction."""
        reasons = []
        
        # Feature importance (simplified)
        if features[0] > 60:  # Temperature
            reasons.append(f"Elevated operating temperature: {features[0]:.1f}°C")
        
        if features[1] > 7:  # Vibration
            reasons.append(f"High vibration levels: {features[1]:.1f} mm/s")
        
        if features[4] > 0.5:  # Temperature trend (if increasing)
            reasons.append("Temperature trending upward")
        
        if features[12] > 180:  # Days since maintenance
            reasons.append(f"Extended period since last maintenance: {int(features[12])} days")
        
        if not reasons:
            reasons.append("Normal operating conditions")
        
        return reasons
    
    def _estimate_time_to_failure(
        self,
        failure_prob: float,
        equipment: Any,
        maintenance_history: List[Any],
    ) -> Optional[int]:
        """Estimate days until likely failure."""
        if failure_prob < 0.5:
            return None  # Low risk, no imminent failure
        
        # Simple linear interpolation
        # failure_prob 0.5 -> 30 days
        # failure_prob 1.0 -> 0 days
        days = int((1.0 - failure_prob) * 60)
        return max(0, days)
    
    def _rule_based_assessment(
        self,
        equipment: Any,
        recent_readings: List[Any],
        maintenance_history: List[Any],
    ) -> Dict:
        """Fallback rule-based assessment when ML models not available."""
        # Simple heuristics
        latest = recent_readings[-1]
        
        risk_score = 0.0
        reasons = []
        
        if latest.temperature and latest.temperature > 70:
            risk_score += 0.3
            reasons.append("High temperature")
        
        if latest.vibration and latest.vibration > 8:
            risk_score += 0.3
            reasons.append("High vibration")
        
        if maintenance_history:
            days_since = (_utcnow() - maintenance_history[-1].date).days
            if days_since > 180:
                risk_score += 0.2
                reasons.append("Overdue for maintenance")
        
        if risk_score >= 0.7:
            risk_level = 'high'
        elif risk_score >= 0.4:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'risk_level': risk_level,
            'failure_probability': risk_score,
            'is_anomaly': False,
            'recommendations': [],
            'reasons': reasons or ['Normal conditions'],
            'estimated_time_to_failure': None,
        }
