"""Tests for Socratic Pedagogy RAG service."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

from sensei.models.learning import LearningUnit
from sensei.services.ai.reasoning_engine import A3Phase
from sensei.services.ai.socratic_pedagogy_rag import (
    SocraticPedagogyRAG,
    rank_learning_units,
    score_learning_unit,
)


class TestSocraticPedagogyRAG:
    def test_score_learning_unit_is_deterministic(self):
        unit = MagicMock(spec=LearningUnit)
        unit.title = "SMED Basics"
        unit.description = "Changeover reduction"
        unit.content = "SMED reduces setup/changeover time."

        q = "SMED changeover"
        s1 = score_learning_unit(q, unit)
        s2 = score_learning_unit(q, unit)
        assert s1 == s2
        assert 0.0 < s1 < 1.0

    def test_rank_learning_units_orders_by_relevance(self):
        unit_1 = MagicMock(spec=LearningUnit)
        unit_1.id = uuid4()
        unit_1.title = "SMED Basics"
        unit_1.description = "Changeover reduction"
        unit_1.content = "SMED reduces setup time"

        unit_2 = MagicMock(spec=LearningUnit)
        unit_2.id = uuid4()
        unit_2.title = "Kanban Sizing"
        unit_2.description = "Pull systems"
        unit_2.content = "WIP limits"

        ranked = rank_learning_units([unit_2, unit_1], query="smed changeover", max_sources=5)
        assert len(ranked) == 1
        assert ranked[0].unit.title == "SMED Basics"

    def test_rank_learning_units_embedding_mode_orders_by_similarity(self, monkeypatch):
        class FakeEmbedder:
            def embed_text(self, text: str):
                # Query vector points strongly along x.
                return [1.0, 0.0]

            def embed_texts(self, texts):
                # First unit is weakly aligned, second is strongly aligned.
                # (vectors assumed already normalized by embedder contract)
                return [[0.3, 0.0], [0.9, 0.0]]

        unit_1 = MagicMock(spec=LearningUnit)
        unit_1.id = uuid4()
        unit_1.title = "Less relevant"
        unit_1.description = ""
        unit_1.content = ""

        unit_2 = MagicMock(spec=LearningUnit)
        unit_2.id = uuid4()
        unit_2.title = "More relevant"
        unit_2.description = ""
        unit_2.content = ""

        # Ensure the embedding code path is selected.
        monkeypatch.setenv("SENSEI_SOCRATIC_RAG_RETRIEVAL", "onnx")

        ranked = rank_learning_units(
            [unit_1, unit_2],
            query="any query",
            max_sources=5,
            embedder=FakeEmbedder(),
        )

        assert len(ranked) == 2
        assert ranked[0].unit.title == "More relevant"

    def test_coach_generates_prompts(self):
        unit = MagicMock(spec=LearningUnit)
        unit.id = uuid4()
        unit.code = "TPS-SMED"
        unit.title = "SMED Basics"
        unit.description = "Changeover reduction"
        unit.content = "SMED reduces setup time"
        unit.category = "tps"
        unit.difficulty = "beginner"

        rag = SocraticPedagogyRAG()
        retrieved, prompts = rag.coach(
            query="How do we reduce changeover?",
            units=[unit],
            phase=A3Phase.CURRENT_STATE,
            max_sources=3,
            max_prompts=3,
        )

        assert len(retrieved) == 1
        assert retrieved[0].unit.code == "TPS-SMED"
        assert 1 <= len(prompts) <= 3
        assert all(p.phase == A3Phase.CURRENT_STATE for p in prompts)
