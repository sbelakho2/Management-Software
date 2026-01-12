"""Socratic Pedagogy RAG (Retrieval-Augmented Guidance).

This module implements the "Socratic" layer on top of content retrieval.

Design goals:
- Retrieval-augmented (use existing learning content as grounding)
- Pedagogical (ask questions instead of directly answering)
- Deterministic ranking (stable results for tests)

NOTE: This is intentionally model-agnostic. It reuses the existing
`SocraticMentor` logic from `sensei.services.ai.reasoning_engineNone`.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from sensei.models.learning import LearningUnit
from sensei.services.ai.reasoning_engine import (
    A3Phase,
    ChallengingPrompt,
    MentorPersona,
    SocraticMentor,
)


_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokenize(query: str) -> list[str]:
    tokens = [t.lower() for t in _TOKEN_RE.findall(query or "")]
    # Keep short tokens out to reduce noise (e.g., 'a', 'of')
    return [t for t in tokens if len(t) >= 3]


def _count_term_hits(text: str, terms: Sequence[str]) -> int:
    if not text:
        return 0
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def score_learning_unit(query: str, unit: LearningUnit) -> float:
    """Score a learning unit for relevance to a query.

    This is a lightweight deterministic scorer intended to work on both
    SQLite and Postgres without requiring full-text indexes.
    """

    terms = _tokenize(query)
    if not terms:
        return 0.0

    title_hits = _count_term_hits(getattr(unit, "title", "") or "", terms)
    desc_hits = _count_term_hits(getattr(unit, "description", "") or "", terms)
    content_hits = _count_term_hits(getattr(unit, "content", "") or "", terms)

    # Weighted sum; title is most important.
    raw = (title_hits * 3) + (desc_hits * 2) + (content_hits * 1)

    # Convert to a bounded score in [0, 1) for stable API output.
    return raw / (raw + 10.0) if raw > 0 else 0.0


@dataclass(frozen=True)
class RetrievedUnit:
    unit: LearningUnit
    relevance_score: float


def rank_learning_units(
    units: Iterable[LearningUnit],
    *,
    query: str,
    max_sources: int = 5,
    retrieval_mode: str | None = None,
    embedder: object | None = None,
) -> list[RetrievedUnit]:
    scored: list[RetrievedUnit] = []

    mode = (retrieval_mode or os.getenv("SENSEI_SOCRATIC_RAG_RETRIEVAL", "keyword")).strip().lower()
    if mode == "onnx":
        try:
            scored = _rank_learning_units_by_embeddings(
                list(units),
                query=query,
                max_sources=max_sources,
                embedder=embedder,
            )
            return scored
        except Exception:
            # Fall back to deterministic keyword retrieval.
            scored = []

    for unit in units:
        score = score_learning_unit(query, unit)
        if score > 0:
            scored.append(RetrievedUnit(unit=unit, relevance_score=score))

    scored.sort(
        key=lambda x: (
            x.relevance_score,
            (getattr(x.unit, "title", "") or "").lower(),
        ),
        reverse=True,
    )

    return scored[:max_sources]


def _rank_learning_units_by_embeddings(
    units: Sequence[LearningUnit],
    *,
    query: str,
    max_sources: int,
    embedder: object | None,
) -> list[RetrievedUnit]:
    # Import lazily to keep base path cheap.
    from sensei.services.ai.onnx_text_embeddings import ONNXTextEmbedder

    embed = embedder
    if embed is None:
        embed = ONNXTextEmbedder(ONNXTextEmbedder.default_config())

    if not hasattr(embed, "embed_text") or not hasattr(embed, "embed_texts"):
        raise TypeError("embedder must expose embed_text() and embed_texts()")

    unit_texts: list[str] = []
    for u in units:
        parts = [u.title or "", u.description or "", u.content or ""]
        unit_texts.append("\n".join(p for p in parts if p.strip()))

    q_vec = np.asarray(embed.embed_text(query), dtype=np.float32)
    u_vecs = np.asarray(embed.embed_texts(unit_texts), dtype=np.float32)

    if u_vecs.ndim != 2 or q_vec.ndim != 1:
        raise ValueError("Invalid embedding shapes")

    # Cosine similarity for L2-normalized embeddings; clamp to [0, 1] for stable scoring.
    sims = (u_vecs @ q_vec).astype(np.float32)
    sims = np.clip(sims, 0.0, 1.0)

    scored: list[RetrievedUnit] = []
    for unit, sim in zip(units, sims.tolist(), strict=False):
        if sim > 0:
            scored.append(RetrievedUnit(unit=unit, relevance_score=float(sim)))

    scored.sort(
        key=lambda x: (
            x.relevance_score,
            (getattr(x.unit, "title", "") or "").lower(),
        ),
        reverse=True,
    )

    return scored[:max_sources]


def build_pedagogical_context(query: str, retrieved: Sequence[RetrievedUnit]) -> str:
    """Build a compact grounding context to feed into the Socratic mentor."""

    lines: list[str] = [f"User question: {query.strip()}"]

    if retrieved:
        lines.append("\nRelevant learning references:")
        for i, item in enumerate(retrieved, start=1):
            unit = item.unit
            title = (getattr(unit, "title", "") or "").strip()
            summary = (getattr(unit, "description", "") or "").strip()
            if summary:
                summary = summary[:220]
                lines.append(f"{i}. {title} — {summary}")
            else:
                lines.append(f"{i}. {title}")

    # Keep the context reasonably bounded.
    return "\n".join(lines)[:4000]


class SocraticPedagogyRAG:
    """Orchestrates retrieval + Socratic mentoring."""

    def __init__(
        self,
        mentor: SocraticMentor | None = None,
    ) -> None:
        self.mentor = mentor or SocraticMentor()

    def coach(
        self,
        *,
        query: str,
        units: Sequence[LearningUnit],
        phase: A3Phase = A3Phase.CURRENT_STATE,
        persona: MentorPersona | None = None,
        max_sources: int = 5,
        max_prompts: int = 3,
    ) -> tuple[list[RetrievedUnit], list[ChallengingPrompt]]:
        retrieved = rank_learning_units(units, query=query, max_sources=max_sources)
        content = build_pedagogical_context(query, retrieved)
        prompts = self.mentor.generate_prompts(
            content=content,
            phase=phase,
            persona=persona,
            max_prompts=max_prompts,
        )
        return retrieved, prompts
