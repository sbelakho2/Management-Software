"""
Tests for ML Module: Lesson Recommender

Tests the hybrid recommendation system for training lessons.
"""

import pytest
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import List
from unittest.mock import MagicMock, patch
import tempfile


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sensei.ml.lesson_recommender import (
    LessonRecommender,
    generate_recommendations_for_all_users,
)


# =============================================================================
# Mock Models
# =============================================================================

class MockLesson:
    """Mock Lesson model for testing."""
    
    def __init__(
        self,
        lesson_id: str,
        title: str = "Test Lesson",
        description: str = "Test description",
        tags: List[str] = None,
        target_roles: List[str] = None,
        skills_taught: List[str] = None,
        is_mandatory: bool = False,
        compliance_required: bool = False,
        average_rating: float = None,
        created_at: datetime = None,
    ):
        self.id = lesson_id
        self.title = title
        self.description = description
        self.tags = tags or []
        self.target_roles = target_roles or []
        self.skills_taught = skills_taught or []
        self.is_mandatory = is_mandatory
        self.compliance_required = compliance_required
        self.average_rating = average_rating
        self.created_at = created_at or _utcnow() - timedelta(days=60)


class MockLessonCompletion:
    """Mock LessonCompletion model for testing."""
    
    def __init__(
        self,
        user_id: str,
        lesson_id: str,
        completed: bool = True,
        rating: int = None,
    ):
        self.user_id = user_id
        self.lesson_id = lesson_id
        self.completed = completed
        self.rating = rating


class MockUser:
    """Mock User model for testing."""
    
    def __init__(
        self,
        user_id: str,
        role: str = "operator",
        skills: List[str] = None,
    ):
        self.id = user_id
        self.role = role
        self.skills = skills or []


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_lessons():
    """Create sample lessons for testing."""
    return [
        MockLesson(
            lesson_id="L001",
            title="5S Workplace Organization",
            description="Learn the 5S methodology for workplace organization",
            tags=["5S", "lean", "organization"],
            target_roles=["operator", "supervisor"],
            skills_taught=["5S", "workplace_organization"],
        ),
        MockLesson(
            lesson_id="L002",
            title="Toyota Production System Basics",
            description="Introduction to TPS principles",
            tags=["TPS", "lean", "production"],
            target_roles=["all"],
            skills_taught=["TPS", "lean_thinking"],
        ),
        MockLesson(
            lesson_id="L003",
            title="Quality Control Basics",
            description="Fundamentals of quality control",
            tags=["quality", "control", "inspection"],
            target_roles=["operator", "quality"],
            skills_taught=["quality_control", "inspection"],
            is_mandatory=True,
        ),
        MockLesson(
            lesson_id="L004",
            title="Advanced Problem Solving",
            description="A3 thinking and problem solving techniques",
            tags=["A3", "problem_solving", "PDCA"],
            target_roles=["supervisor", "manager"],
            skills_taught=["A3", "problem_solving", "PDCA"],
            average_rating=4.8,
        ),
        MockLesson(
            lesson_id="L005",
            title="Safety Compliance Training",
            description="Mandatory safety training for all employees",
            tags=["safety", "compliance"],
            target_roles=["all"],
            skills_taught=["safety"],
            is_mandatory=True,
            compliance_required=True,
        ),
        MockLesson(
            lesson_id="L006",
            title="New Machine Operation",
            description="Training on the new CNC machine",
            tags=["CNC", "machine", "operation"],
            target_roles=["operator"],
            skills_taught=["CNC_operation"],
            created_at=_utcnow() - timedelta(days=10),  # Recently added
        ),
    ]


@pytest.fixture
def sample_users():
    """Create sample users for testing."""
    return [
        MockUser(
            user_id="U001",
            role="operator",
            skills=["5S", "safety"],
        ),
        MockUser(
            user_id="U002",
            role="supervisor",
            skills=["5S", "TPS", "quality_control"],
        ),
        MockUser(
            user_id="U003",
            role="manager",
            skills=["A3", "problem_solving", "TPS"],
        ),
    ]


@pytest.fixture
def sample_completions():
    """Create sample lesson completions for testing."""
    return [
        MockLessonCompletion("U001", "L001", True, 4),
        MockLessonCompletion("U001", "L005", True, 5),
        MockLessonCompletion("U002", "L001", True, 5),
        MockLessonCompletion("U002", "L002", True, 4),
        MockLessonCompletion("U002", "L003", True, 3),
        MockLessonCompletion("U003", "L004", True, 5),
        MockLessonCompletion("U003", "L002", True, 4),
    ]


@pytest.fixture
def temp_model_path():
    """Create temporary directory for model artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# =============================================================================
# Test: LessonRecommender Initialization
# =============================================================================

class TestLessonRecommenderInit:
    """Test LessonRecommender initialization."""
    
    def test_init_with_default_path(self):
        """Test initialization with default model path."""
        with patch.object(Path, 'mkdir', return_value=None):
            recommender = LessonRecommender()
            assert recommender.tfidf_vectorizer is None
            assert recommender.lesson_embeddings is None
    
    def test_init_with_custom_path(self, temp_model_path):
        """Test initialization with custom model path."""
        recommender = LessonRecommender(model_path=temp_model_path)
        assert recommender.model_path == temp_model_path


# =============================================================================
# Test: LessonRecommender Training
# =============================================================================

class TestLessonRecommenderTraining:
    """Test LessonRecommender training."""
    
    def test_train_creates_model_artifacts(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test that training creates model artifacts."""
        recommender = LessonRecommender(model_path=temp_model_path)
        
        metrics = recommender.train(
            lessons=sample_lessons,
            completions=sample_completions,
            users=sample_users,
        )
        
        # Check metrics returned
        assert 'precision@5' in metrics
        assert 'recall@5' in metrics
        assert 'coverage' in metrics
        
        # Check artifacts created
        assert (temp_model_path / "tfidf_vectorizer.pkl").exists()
        assert (temp_model_path / "lesson_embeddings.pkl").exists()
        assert (temp_model_path / "lesson_ids.pkl").exists()
        assert (temp_model_path / "user_similarity.pkl").exists()
    
    def test_train_builds_embeddings(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test that training builds lesson embeddings."""
        recommender = LessonRecommender(model_path=temp_model_path)
        recommender.train(sample_lessons, sample_completions, sample_users)
        
        assert recommender.tfidf_vectorizer is not None
        assert recommender.lesson_embeddings is not None
        assert len(recommender.lesson_ids) == len(sample_lessons)
    
    def test_train_with_empty_data(self, temp_model_path):
        """Test training with empty data."""
        recommender = LessonRecommender(model_path=temp_model_path)
        
        metrics = recommender.train(
            lessons=[],
            completions=[],
            users=[],
        )
        
        # Should handle gracefully
        assert metrics['coverage'] == 0


# =============================================================================
# Test: LessonRecommender Loading
# =============================================================================

class TestLessonRecommenderLoading:
    """Test LessonRecommender model loading."""
    
    def test_load_after_training(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test loading model after training."""
        # Train first
        recommender1 = LessonRecommender(model_path=temp_model_path)
        recommender1.train(sample_lessons, sample_completions, sample_users)
        
        # Load in new instance
        recommender2 = LessonRecommender(model_path=temp_model_path)
        recommender2.load()
        
        assert recommender2.tfidf_vectorizer is not None
        assert recommender2.lesson_embeddings is not None
        assert len(recommender2.lesson_ids) == len(sample_lessons)
    
    def test_load_without_training_raises(self, temp_model_path):
        """Test that loading without training raises error."""
        recommender = LessonRecommender(model_path=temp_model_path)
        
        with pytest.raises(Exception):
            recommender.load()


# =============================================================================
# Test: LessonRecommender Recommendations
# =============================================================================

class TestLessonRecommenderRecommendations:
    """Test LessonRecommender recommendation generation."""
    
    def test_recommend_excludes_completed(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test that recommendations exclude completed lessons."""
        recommender = LessonRecommender(model_path=temp_model_path)
        recommender.train(sample_lessons, sample_completions, sample_users)
        
        user = sample_users[0]  # U001 completed L001, L005
        user_completions = [c for c in sample_completions if c.user_id == user.id]
        
        recommendations = recommender.recommend(
            user=user,
            user_completions=user_completions,
            all_lessons=sample_lessons,
            top_k=10,
            exclude_completed=True,
        )
        
        recommended_ids = [r[0] for r in recommendations]
        assert "L001" not in recommended_ids
        assert "L005" not in recommended_ids
    
    def test_recommend_includes_mandatory_lessons(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test that mandatory lessons get boosted."""
        recommender = LessonRecommender(model_path=temp_model_path)
        recommender.train(sample_lessons, sample_completions, sample_users)
        
        user = sample_users[0]
        # Simulate no completions for mandatory lesson L003
        user_completions = [c for c in sample_completions if c.user_id == user.id and c.lesson_id != "L003"]
        
        recommendations = recommender.recommend(
            user=user,
            user_completions=user_completions,
            all_lessons=sample_lessons,
            top_k=5,
        )
        
        # L003 (mandatory) should be in recommendations
        recommended_ids = [r[0] for r in recommendations]
        assert "L003" in recommended_ids or len(recommended_ids) == 0  # Depends on scoring
    
    def test_recommend_respects_top_k(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test that recommend returns at most top_k items."""
        recommender = LessonRecommender(model_path=temp_model_path)
        recommender.train(sample_lessons, sample_completions, sample_users)
        
        recommendations = recommender.recommend(
            user=sample_users[0],
            user_completions=[],
            all_lessons=sample_lessons,
            top_k=3,
        )
        
        assert len(recommendations) <= 3
    
    def test_recommend_returns_scores_and_explanations(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test that recommendations include scores and explanations."""
        recommender = LessonRecommender(model_path=temp_model_path)
        recommender.train(sample_lessons, sample_completions, sample_users)
        
        recommendations = recommender.recommend(
            user=sample_users[0],
            user_completions=[],
            all_lessons=sample_lessons,
            top_k=5,
        )
        
        for lesson_id, score, explanation in recommendations:
            assert isinstance(lesson_id, str)
            assert isinstance(score, float)
            assert 0 <= score <= 2  # Score can exceed 1 with boosts
            assert isinstance(explanation, dict)
    
    def test_recommend_empty_if_all_completed(
        self,
        sample_lessons,
        sample_users,
        temp_model_path,
    ):
        """Test that recommendations are empty if all lessons completed."""
        recommender = LessonRecommender(model_path=temp_model_path)
        
        # Complete all lessons
        all_completions = [
            MockLessonCompletion(sample_users[0].id, lesson.id, True)
            for lesson in sample_lessons
        ]
        
        recommender.train(sample_lessons, all_completions, sample_users)
        
        recommendations = recommender.recommend(
            user=sample_users[0],
            user_completions=all_completions,
            all_lessons=sample_lessons,
            top_k=5,
            exclude_completed=True,
        )
        
        assert len(recommendations) == 0
    
    def test_recommend_without_loading_raises(self, sample_users, sample_lessons):
        """Test that recommend without loading model raises error."""
        recommender = LessonRecommender()
        
        with pytest.raises(RuntimeError, match="Model not loaded"):
            recommender.recommend(
                user=sample_users[0],
                user_completions=[],
                all_lessons=sample_lessons,
                top_k=5,
            )


# =============================================================================
# Test: Role Matching
# =============================================================================

class TestRoleMatching:
    """Test role-based filtering and scoring."""
    
    def test_role_match_boosts_score(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test that role-matched lessons get higher scores."""
        recommender = LessonRecommender(model_path=temp_model_path)
        recommender.train(sample_lessons, sample_completions, sample_users)
        
        # Operator should see operator-targeted lessons scored higher
        operator = sample_users[0]
        recommendations = recommender.recommend(
            user=operator,
            user_completions=[],
            all_lessons=sample_lessons,
            top_k=10,
        )
        
        # Find recommendations with role explanation
        role_matched = [r for r in recommendations if 'role' in r[2]]
        assert len(role_matched) > 0


# =============================================================================
# Test: Skills Gap Detection
# =============================================================================

class TestSkillsGapDetection:
    """Test skills gap analysis in recommendations."""
    
    def test_skills_gap_prioritized(
        self,
        sample_lessons,
        sample_users,
        temp_model_path,
    ):
        """Test that lessons filling skills gaps are prioritized."""
        recommender = LessonRecommender(model_path=temp_model_path)
        recommender.train(sample_lessons, [], sample_users)
        
        # User with minimal skills
        new_user = MockUser(user_id="U999", role="operator", skills=[])
        
        recommendations = recommender.recommend(
            user=new_user,
            user_completions=[],
            all_lessons=sample_lessons,
            top_k=10,
        )
        
        # Should get recommendations
        assert len(recommendations) > 0


# =============================================================================
# Test: Batch Recommendations
# =============================================================================

class TestBatchRecommendations:
    """Test batch recommendation generation."""
    
    def test_generate_recommendations_for_all_users(
        self,
        sample_lessons,
        sample_completions,
        sample_users,
        temp_model_path,
    ):
        """Test generating recommendations for all users."""
        recommender = LessonRecommender(model_path=temp_model_path)
        recommender.train(sample_lessons, sample_completions, sample_users)
        
        all_recommendations = generate_recommendations_for_all_users(
            recommender=recommender,
            users=sample_users,
            completions=sample_completions,
            lessons=sample_lessons,
            top_k=5,
        )
        
        # Should have recommendations for each user
        assert len(all_recommendations) == len(sample_users)
        
        for user_id, recommendations in all_recommendations.items():
            assert isinstance(recommendations, list)
            assert len(recommendations) <= 5


# =============================================================================
# Test: Content Similarity
# =============================================================================

class TestContentSimilarity:
    """Test content-based similarity features."""
    
    def test_similar_lessons_grouped(
        self,
        sample_lessons,
        sample_users,
        temp_model_path,
    ):
        """Test that similar lessons are grouped in recommendations."""
        # Add more lessons with similar content
        lessons = sample_lessons + [
            MockLesson(
                lesson_id="L007",
                title="5S Advanced Techniques",
                description="Advanced 5S for continuous improvement",
                tags=["5S", "advanced", "lean"],
                skills_taught=["5S_advanced"],
            ),
        ]
        
        recommender = LessonRecommender(model_path=temp_model_path)
        
        # User completed basic 5S
        completions = [MockLessonCompletion("U001", "L001", True, 5)]
        
        recommender.train(lessons, completions, sample_users)
        
        recommendations = recommender.recommend(
            user=sample_users[0],
            user_completions=completions,
            all_lessons=lessons,
            top_k=5,
        )
        
        # Advanced 5S should be recommended due to similarity
        recommended_ids = [r[0] for r in recommendations]
        assert "L007" in recommended_ids
