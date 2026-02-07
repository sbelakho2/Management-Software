"""
Machine Learning: Lesson Recommendation Model

Recommends relevant training lessons to users based on:
- Current role and responsibilities
- Skills gap analysis
- Recent quality issues in their area
- Peer learning patterns
- Mandatory compliance requirements
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import joblib
import logging
from pathlib import Path

if TYPE_CHECKING:
    from sensei.models.training import Lesson, LessonCompletion
    from sensei.models.user import User

from sensei.core.config import settings

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LessonRecommender:
    """
    Hybrid recommendation system combining:
    1. Content-based filtering (skill/topic matching)
    2. Collaborative filtering (similar user patterns)
    3. Context-aware rules (role, compliance, recency)
    """

    def __init__(self, model_path: Optional[Path] = None):
        default_path = getattr(settings, 'ML_MODEL_PATH', '/tmp/ml_models')
        self.model_path = model_path or Path(default_path) / "lesson_recommender"
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.scaler: Optional[StandardScaler] = None
        self.lesson_embeddings: Optional[np.ndarray] = None
        self.lesson_ids: List[str] = []
        self._lesson_id_to_idx: Dict[str, int] = {}  # O(1) lookup index
        
    def train(
        self,
        lessons: List[Any],
        completions: List[Any],
        users: List[Any],
    ) -> Dict[str, float]:
        """
        Train the recommendation model.
        
        Returns metrics: precision@5, recall@5, coverage
        """
        logger.info(f"Training lesson recommender with {len(lessons)} lessons, {len(completions)} completions")
        
        # Handle empty data gracefully
        if not lessons:
            logger.warning("No lessons provided for training. Model will be empty.")
            self.tfidf_vectorizer = None
            self.lesson_embeddings = np.array([])
            self.lesson_ids = []
            return {
                'precision@5': 0.0,
                'recall@5': 0.0,
                'coverage': 0.0,
            }
        
        # Build lesson content embeddings (TF-IDF)
        lesson_texts = [
            f"{lesson.title} {lesson.description} {' '.join(lesson.tags or [])}"
            for lesson in lessons
        ]
        
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.lesson_embeddings = self.tfidf_vectorizer.fit_transform(lesson_texts).toarray()
        self.lesson_ids = [lesson.id for lesson in lessons]
        self._lesson_id_to_idx = {lid: idx for idx, lid in enumerate(self.lesson_ids)}
        
        # Build user-lesson interaction matrix for collaborative filtering
        user_lesson_matrix = self._build_interaction_matrix(completions, users, lessons)
        
        # Train collaborative filter (user similarity)
        if user_lesson_matrix.size > 0:
            user_similarity = cosine_similarity(user_lesson_matrix)
        else:
            user_similarity = np.array([])
        
        # Save model artifacts
        self.model_path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.tfidf_vectorizer, self.model_path / "tfidf_vectorizer.pkl")
        joblib.dump(self.lesson_embeddings, self.model_path / "lesson_embeddings.pkl")
        joblib.dump(self.lesson_ids, self.model_path / "lesson_ids.pkl")
        joblib.dump(user_similarity, self.model_path / "user_similarity.pkl")
        
        # Evaluate model
        metrics = self._evaluate(completions, users, lessons)
        
        logger.info(f"Model trained. Metrics: {metrics}")
        return metrics
    
    def load(self) -> None:
        """Load trained model from disk."""
        logger.info(f"Loading lesson recommender from {self.model_path}")
        
        self.tfidf_vectorizer = joblib.load(self.model_path / "tfidf_vectorizer.pkl")
        self.lesson_embeddings = joblib.load(self.model_path / "lesson_embeddings.pkl")
        self.lesson_ids = joblib.load(self.model_path / "lesson_ids.pkl")
        self._lesson_id_to_idx = {lid: idx for idx, lid in enumerate(self.lesson_ids)}
        
        logger.info("Lesson recommender loaded successfully")
    
    def recommend(
        self,
        user: Any,
        user_completions: List[Any],
        all_lessons: List[Any],
        top_k: int = 10,
        exclude_completed: bool = True,
    ) -> List[Tuple[str, float, Dict[str, str]]]:
        """
        Generate lesson recommendations for a user.
        
        Returns:
            List of (lesson_id, score, explanation) tuples
        """
        if self.tfidf_vectorizer is None:
            raise RuntimeError("Model not loaded. Call load() first.")
        
        # Get completed lesson IDs
        completed_ids = {c.lesson_id for c in user_completions}
        
        # Filter available lessons
        available_lessons = [
            l for l in all_lessons
            if not exclude_completed or l.id not in completed_ids
        ]
        
        if not available_lessons:
            return []
        
        # Score lessons using hybrid approach
        scores = []
        for lesson in available_lessons:
            score, explanation = self._score_lesson(user, lesson, user_completions, all_lessons)
            scores.append((lesson.id, score, explanation))
        
        # Sort by score and return top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def _score_lesson(
        self,
        user: Any,
        lesson: Any,
        user_completions: List[Any],
        all_lessons: List[Any],
    ) -> Tuple[float, Dict[str, str]]:
        """
        Score a single lesson for a user using hybrid approach.
        
        Returns (score, explanation)
        """
        explanation = {}
        score = 0.0
        
        # 1. Role match (30% weight)
        role_match = self._check_role_match(user, lesson)
        if role_match:
            score += 0.3
            explanation['role'] = f"Matches {user.role} role requirements"
        
        # 2. Skills gap (25% weight)
        skills_gap = self._calculate_skills_gap(user, lesson)
        score += skills_gap * 0.25
        if skills_gap > 0.5:
            explanation['skills'] = "Addresses critical skills gap"
        
        # 3. Content similarity to completed lessons (20% weight)
        if user_completions:
            content_sim = self._calculate_content_similarity(lesson, user_completions, all_lessons)
            score += content_sim * 0.20
            if content_sim > 0.6:
                explanation['similar'] = "Similar to lessons you've completed"
        
        # 4. Compliance/mandatory (25% weight)
        if lesson.is_mandatory or lesson.compliance_required:
            score += 0.25
            explanation['mandatory'] = "Compliance training required"
        
        # Boost for recently added lessons
        if lesson.created_at and (_utcnow() - lesson.created_at) < timedelta(days=30):
            score += 0.05
            explanation['new'] = "Recently added content"
        
        # Boost for high-rated lessons
        if lesson.average_rating and lesson.average_rating >= 4.5:
            score += 0.05
            explanation['popular'] = f"Highly rated ({lesson.average_rating:.1f}★)"
        
        return score, explanation
    
    def _check_role_match(self, user: Any, lesson: Any) -> bool:
        """Check if lesson target roles match user role."""
        if not lesson.target_roles:
            return True  # Available to all
        return user.role in lesson.target_roles
    
    def _calculate_skills_gap(self, user: Any, lesson: Any) -> float:
        """
        Calculate how well lesson addresses user's skills gap.
        
        Returns value between 0 and 1.
        """
        # Get user's current skills
        user_skills = set(user.skills or [])
        
        # Get skills taught in lesson
        lesson_skills = set(lesson.skills_taught or [])
        
        if not lesson_skills:
            return 0.5  # Neutral if no skills specified
        
        # Calculate gap (skills in lesson but not in user profile)
        gap_skills = lesson_skills - user_skills
        
        if not gap_skills:
            return 0.2  # Already have these skills
        
        # More gap = more relevant
        gap_ratio = len(gap_skills) / len(lesson_skills)
        return min(gap_ratio, 1.0)
    
    def _calculate_content_similarity(
        self,
        lesson: Any,
        user_completions: List[Any],
        all_lessons: List[Any],
    ) -> float:
        """
        Calculate content similarity between lesson and user's completed lessons.
        
        Uses TF-IDF cosine similarity.
        """
        if self.lesson_embeddings is None:
            return 0.0
        
        lesson_idx = self._lesson_id_to_idx.get(lesson.id)
        if lesson_idx is None:
            return 0.0
        
        lesson_vec = self.lesson_embeddings[lesson_idx]
        
        # Get completed lesson vectors
        completed_indices = [
            self._lesson_id_to_idx[c.lesson_id]
            for c in user_completions
            if c.lesson_id in self._lesson_id_to_idx
        ]
        
        if not completed_indices:
            return 0.0
        
        completed_vecs = self.lesson_embeddings[completed_indices]
        
        # Calculate average similarity to completed lessons
        similarities = cosine_similarity([lesson_vec], completed_vecs)[0]
        return float(np.mean(similarities))
    
    def _build_interaction_matrix(
        self,
        completions: List[Any],
        users: List[Any],
        lessons: List[Any],
    ) -> np.ndarray:
        """Build user-lesson interaction matrix for collaborative filtering."""
        user_ids = [u.id for u in users]
        lesson_ids = [l.id for l in lessons]
        
        # Build O(1) lookup maps
        user_id_to_idx = {uid: idx for idx, uid in enumerate(user_ids)}
        lesson_id_to_idx = {lid: idx for idx, lid in enumerate(lesson_ids)}
        
        matrix = np.zeros((len(user_ids), len(lesson_ids)))
        
        for completion in completions:
            user_idx = user_id_to_idx.get(completion.user_id)
            lesson_idx = lesson_id_to_idx.get(completion.lesson_id)
            if user_idx is None or lesson_idx is None:
                continue
            
            # Score based on completion and rating
            score = 1.0
            if completion.completed:
                score += 0.5
            if completion.rating:
                score += (completion.rating - 3) * 0.2  # Normalize rating
            
            matrix[user_idx, lesson_idx] = score
        
        return matrix
    
    def _evaluate(
        self,
        completions: List[Any],
        users: List[Any],
        lessons: List[Any],
    ) -> Dict[str, float]:
        """
        Evaluate model using precision@k and recall@k.
        
        Uses leave-one-out cross-validation.
        """
        # Group completions by user
        user_completions: dict[int, list[Any]] = {}
        for c in completions:
            if c.user_id not in user_completions:
                user_completions[c.user_id] = []
            user_completions[c.user_id].append(c)
        
        precisions = []
        recalls = []
        
        # Evaluate on users with at least 5 completions
        for user in users:
            if user.id not in user_completions:
                continue
            
            user_comps = user_completions[user.id]
            if len(user_comps) < 5:
                continue
            
            # Leave one out for testing
            test_lesson_id = user_comps[-1].lesson_id
            train_comps = user_comps[:-1]
            
            # Get recommendations
            try:
                recommendations = self.recommend(
                    user,
                    train_comps,
                    lessons,
                    top_k=5,
                    exclude_completed=True,
                )
                
                recommended_ids = [r[0] for r in recommendations]
                
                # Calculate metrics
                if test_lesson_id in recommended_ids:
                    precisions.append(1.0)
                    recalls.append(1.0)
                else:
                    precisions.append(0.0)
                    recalls.append(0.0)
            except Exception as e:
                logger.warning(f"Error evaluating user {user.id}: {e}")
                continue
        
        # Calculate coverage (% of lessons that can be recommended)
        coverage = len(self.lesson_ids) / len(lessons) if lessons else 0
        
        return {
            'precision@5': float(np.mean(precisions)) if precisions else 0.0,
            'recall@5': float(np.mean(recalls)) if recalls else 0.0,
            'coverage': coverage,
        }


# Batch recommendation pipeline
def generate_recommendations_for_all_users(
    recommender: LessonRecommender,
    users: List[Any],
    completions: List[Any],
    lessons: List[Any],
    top_k: int = 10,
) -> Dict[str, List[Tuple[str, float, Dict[str, str]]]]:
    """
    Generate recommendations for all users in batch.
    
    Returns dict mapping user_id -> recommendations
    """
    logger.info(f"Generating recommendations for {len(users)} users")
    
    # Group completions by user
    user_completions: dict[int, list[Any]] = {}
    for c in completions:
        if c.user_id not in user_completions:
            user_completions[c.user_id] = []
        user_completions[c.user_id].append(c)
    
    # Generate recommendations
    all_recommendations = {}
    for user in users:
        user_comps = user_completions.get(user.id, [])
        recommendations = recommender.recommend(
            user,
            user_comps,
            lessons,
            top_k=top_k,
        )
        all_recommendations[user.id] = recommendations
    
    logger.info(f"Generated {sum(len(r) for r in all_recommendations.values())} total recommendations")
    return all_recommendations
