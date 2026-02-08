"""
Integration test framework for DB-backed services (#411, #412, #481, #482).

Provides reusable fixtures and assertion helpers for testing repository
CRUD operations, transaction rollback, and concurrent access patterns.

Usage::

    @pytest.mark.asyncio
    async def test_inspection_crud(db_session):
        repo = InspectionRepository(db_session)
        await assert_crud_lifecycle(repo, create_data={...})
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Sequence, Type
from uuid import UUID, uuid4

import pytest

logger = logging.getLogger(__name__)


# =====================================================================
# Helpers
# =====================================================================


def make_uuid() -> str:
    return str(uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =====================================================================
# Generic CRUD lifecycle assertion (#481)
# =====================================================================


async def assert_crud_lifecycle(
    repo: Any,
    create_data: Dict[str, Any],
    update_data: Dict[str, Any] | None = None,
    id_field: str = "id",
) -> None:
    """Run a full CREATE → READ → UPDATE → SOFT-DELETE cycle against *repo*.

    Raises ``AssertionError`` if any step fails.
    """
    # CREATE
    created = await repo.create(create_data)
    assert created is not None, "create() returned None"
    entity_id = getattr(created, id_field)
    assert entity_id is not None, f"{id_field} is None after create"

    # READ
    fetched = await repo.get(entity_id)
    assert fetched is not None, "get() returned None for existing entity"

    # LIST
    items = await repo.list(limit=10)
    assert len(items) >= 1, "list() returned empty after create"

    # COUNT
    count = await repo.count()
    assert count >= 1, "count() is 0 after create"

    # UPDATE
    if update_data:
        updated = await repo.update(entity_id, update_data)
        assert updated is not None, "update() returned None for existing entity"
        for key, value in update_data.items():
            actual = getattr(updated, key, None)
            assert actual == value, f"update: {key} expected {value}, got {actual}"

    # SOFT DELETE
    deleted = await repo.soft_delete(entity_id)
    assert deleted is True, "soft_delete() returned False"

    # Verify soft-deleted entity is excluded from default queries
    after_delete = await repo.get(entity_id)
    assert after_delete is None, "get() still returns soft-deleted entity"


# =====================================================================
# Transaction rollback test (#482)
# =====================================================================


async def assert_transaction_rollback(
    session_factory: Any,
    repo_class: Type,
    create_data: Dict[str, Any],
) -> None:
    """Verify that a failed transaction rolls back cleanly.

    Creates an entity, raises an exception before commit,
    and asserts the entity does not persist.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    async with session_factory() as session:
        repo = repo_class(session)

        try:
            created = await repo.create(create_data)
            entity_id = created.id
            # Simulate failure
            raise RuntimeError("Simulated failure for rollback test")
        except RuntimeError:
            await session.rollback()

    # In a new session, verify entity was not persisted
    async with session_factory() as session:
        repo = repo_class(session)
        result = await repo.get(entity_id)
        assert result is None, "Entity persisted despite rollback"


# =====================================================================
# Concurrent access test (#483)
# =====================================================================


async def assert_concurrent_safety(
    session_factory: Any,
    repo_class: Type,
    create_data: Dict[str, Any],
    n_concurrent: int = 10,
) -> Dict[str, Any]:
    """Run N concurrent create operations and report results.

    Returns a summary dict with success/failure counts.
    Useful for documenting race conditions in in-memory services.
    """
    results = {"success": 0, "errors": 0, "error_types": []}

    async def _create_one(i: int) -> None:
        try:
            async with session_factory() as session:
                repo = repo_class(session)
                data = {**create_data, "id": uuid4()}
                await repo.create(data)
                await session.commit()
                results["success"] += 1
        except Exception as exc:
            results["errors"] += 1
            results["error_types"].append(type(exc).__name__)

    await asyncio.gather(*[_create_one(i) for i in range(n_concurrent)])

    return results


# =====================================================================
# Error handling / try-except coverage test (#411)
# =====================================================================


async def assert_error_handling(
    repo: Any,
    method_name: str = "get",
    bad_args: tuple = (),
    bad_kwargs: dict | None = None,
) -> None:
    """Verify that the repo method handles errors gracefully.

    Calls the method with known-bad arguments and asserts it either
    returns None/empty or raises a well-typed exception (not bare Exception).
    """
    method = getattr(repo, method_name, None)
    if method is None:
        pytest.skip(f"Repository has no method '{method_name}'")

    try:
        result = await method(*(bad_args or ()), **(bad_kwargs or {}))
        # Acceptable: returns None or empty list
        assert result is None or result == [] or result == 0, \
            f"{method_name} returned unexpected result for bad input: {result}"
    except (ValueError, TypeError, KeyError, AttributeError):
        pass  # Well-typed exceptions are acceptable
    except Exception as exc:
        pytest.fail(
            f"{method_name} raised bare Exception instead of specific type: "
            f"{type(exc).__name__}: {exc}"
        )


# =====================================================================
# AI model quality benchmark scaffold (#413, #484)
# =====================================================================


class ModelQualityBenchmark:
    """Scaffold for benchmarking AI model output quality.

    Collects predictions vs ground-truth labels and computes
    precision, recall, F1, and accuracy.
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.predictions: list[Any] = []
        self.ground_truth: list[Any] = []

    def add(self, prediction: Any, truth: Any) -> None:
        self.predictions.append(prediction)
        self.ground_truth.append(truth)

    @property
    def accuracy(self) -> float:
        if not self.predictions:
            return 0.0
        correct = sum(
            1 for p, t in zip(self.predictions, self.ground_truth) if p == t
        )
        return correct / len(self.predictions)

    def compute_metrics(self) -> Dict[str, float]:
        """Compute classification metrics (binary: positive = first unique label)."""
        if not self.predictions:
            return {"accuracy": 0.0, "precision": 0.0, "recall": 0.0, "f1": 0.0}

        labels = sorted(set(self.ground_truth))
        if len(labels) < 2:
            return {"accuracy": self.accuracy, "precision": 0.0, "recall": 0.0, "f1": 0.0}

        positive = labels[0]
        tp = sum(1 for p, t in zip(self.predictions, self.ground_truth) if p == positive and t == positive)
        fp = sum(1 for p, t in zip(self.predictions, self.ground_truth) if p == positive and t != positive)
        fn = sum(1 for p, t in zip(self.predictions, self.ground_truth) if p != positive and t == positive)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "accuracy": self.accuracy,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    def assert_minimum_quality(
        self,
        min_accuracy: float = 0.7,
        min_precision: float = 0.5,
        min_recall: float = 0.5,
    ) -> None:
        """Raise AssertionError if model quality falls below thresholds."""
        metrics = self.compute_metrics()
        assert metrics["accuracy"] >= min_accuracy, \
            f"{self.model_name} accuracy {metrics['accuracy']:.2%} < {min_accuracy:.2%}"
        assert metrics["precision"] >= min_precision, \
            f"{self.model_name} precision {metrics['precision']:.2%} < {min_precision:.2%}"
        assert metrics["recall"] >= min_recall, \
            f"{self.model_name} recall {metrics['recall']:.2%} < {min_recall:.2%}"


# =====================================================================
# Frontend component test helpers (#486)
# =====================================================================


def generate_component_test_template(component_name: str, import_path: str) -> str:
    """Generate a React Testing Library test template for a component.

    Returns the test file content as a string.
    """
    return f"""import {{ render, screen, fireEvent, waitFor }} from '@testing-library/react';
import {{ {component_name} }} from '{import_path}';

describe('{component_name}', () => {{
  it('renders without crashing', () => {{
    render(<{component_name} />);
  }});

  it('displays expected content', () => {{
    render(<{component_name} />);
    // Add assertions based on component's expected output
  }});

  it('handles user interaction', async () => {{
    render(<{component_name} />);
    // Add interaction tests
  }});

  it('handles loading state', () => {{
    render(<{component_name} isLoading={{true}} />);
    // Verify loading indicator is shown
  }});

  it('handles error state', () => {{
    render(<{component_name} error="Test error" />);
    // Verify error message is shown
  }});

  it('is accessible', async () => {{
    const {{ container }} = render(<{component_name} />);
    // Add axe accessibility checks
  }});
}});
"""
