"""Socratic pedagogy RAG utilities."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Iterable

from sensei.core.config import settings
from sensei.services.ai.reasoning_engine import A3Phase


@dataclass
class RankedLearningUnit:
    unit: object
    score: float


@dataclass
class SocraticPrompt:
    phase: A3Phase
    prompt: str


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t}


def score_learning_unit(query: str, unit: object) -> float:
    """Deterministic lexical similarity score in (0, 1)."""
    fields = [
        str(getattr(unit, "title", "")),
        str(getattr(unit, "description", "")),
        str(getattr(unit, "content", "")),
    ]
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0.0
    unit_tokens = _tokenize(" ".join(fields))
    overlap = len(q_tokens & unit_tokens)
    score = overlap / max(1, len(q_tokens))
    return max(0.0, min(1.0, score))


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns a value in [-1, 1].  Returns 0.0 when either vector has
    zero magnitude (avoids division-by-zero).
    """
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def rank_learning_units(
    units: Iterable[object],
    *,
    query: str,
    max_sources: int = 5,
    embedder: object | None = None,
) -> list[RankedLearningUnit]:
    retrieval_mode = settings.SOCRATIC_RAG_RETRIEVAL_MODE.lower()
    units_list = list(units)

    if retrieval_mode == "onnx" and embedder is not None:
        query_vec = embedder.embed_text(query)
        unit_texts = [
            f"{getattr(u, 'title', '')} {getattr(u, 'description', '')} {getattr(u, 'content', '')}".strip()
            for u in units_list
        ]
        unit_vecs = embedder.embed_texts(unit_texts)
        ranked = [
            RankedLearningUnit(unit=u, score=_cosine_similarity(query_vec, vec))
            for u, vec in zip(units_list, unit_vecs)
        ]
        ranked.sort(key=lambda r: r.score, reverse=True)
        return ranked[:max_sources]

    scored = [RankedLearningUnit(unit=u, score=score_learning_unit(query, u)) for u in units_list]
    scored = [r for r in scored if r.score > 0.1]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored[:max_sources]


class SocraticPedagogyRAG:
    """Generates Socratic coaching prompts based on learning units."""

    def coach(
        self,
        *,
        query: str,
        units: Iterable[object],
        phase: A3Phase,
        max_sources: int = 3,
        max_prompts: int = 3,
    ) -> tuple[list[RankedLearningUnit], list[SocraticPrompt]]:
        retrieved = rank_learning_units(units, query=query, max_sources=max_sources)
        prompts: list[SocraticPrompt] = []
        for ranked in retrieved:
            if len(prompts) >= max_prompts:
                break
            title = getattr(ranked.unit, "title", "this topic")
            prompts.append(
                SocraticPrompt(
                    phase=phase,
                    prompt=f"In {phase.value}, how does {title} apply to your situation?",
                )
            )
        while len(prompts) < max_prompts and retrieved:
            prompts.append(
                SocraticPrompt(
                    phase=phase,
                    prompt=f"What evidence supports your current thinking in {phase.value}?",
                )
            )
        return retrieved, prompts
