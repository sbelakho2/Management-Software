"""
Pipeline Forecast Aggregation for CRM.

Aggregates deal pipeline data into weighted forecasts by:
- Stage probability weighting
- Time-period bucketing (weekly/monthly/quarterly)
- Rep/team rollups
- Scenario analysis (best/worst/expected)

Checklist items: #378, #477
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ForecastPeriod(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ForecastScenario(str, Enum):
    BEST_CASE = "best_case"
    EXPECTED = "expected"
    WORST_CASE = "worst_case"
    COMMITTED = "committed"


@dataclass
class DealSnapshot:
    """Snapshot of a deal for forecast calculation."""

    deal_id: str
    name: str
    stage: str
    amount: float
    probability: float  # 0.0–1.0
    expected_close: date
    owner_id: str = ""
    team: str = ""
    is_committed: bool = False
    last_activity: datetime | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class ForecastBucket:
    """Aggregated forecast for a time period."""

    period_label: str  # e.g. "2024-Q1", "2024-W05", "2024-03"
    period_start: date
    period_end: date
    total_pipeline: float = 0.0  # sum of all deal amounts
    weighted_pipeline: float = 0.0  # sum of amount × probability
    committed: float = 0.0  # sum of committed deals
    best_case: float = 0.0
    expected: float = 0.0
    worst_case: float = 0.0
    deal_count: int = 0
    avg_probability: float = 0.0
    deals: list[DealSnapshot] = field(default_factory=list)


@dataclass
class TeamForecast:
    """Forecast rollup for a team or rep."""

    owner_id: str
    team: str
    total_pipeline: float = 0.0
    weighted_pipeline: float = 0.0
    committed: float = 0.0
    deal_count: int = 0


@dataclass
class ForecastReport:
    """Complete forecast report."""

    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    period_type: ForecastPeriod = ForecastPeriod.MONTHLY
    buckets: list[ForecastBucket] = field(default_factory=list)
    by_team: list[TeamForecast] = field(default_factory=list)
    by_owner: list[TeamForecast] = field(default_factory=list)
    total_pipeline: float = 0.0
    total_weighted: float = 0.0
    total_committed: float = 0.0
    total_deals: int = 0


# Default stage probabilities
DEFAULT_STAGE_PROBABILITIES: dict[str, float] = {
    "lead": 0.10,
    "qualified": 0.25,
    "proposal": 0.50,
    "negotiation": 0.75,
    "closed_won": 1.00,
    "closed_lost": 0.00,
}

# Scenario multipliers
SCENARIO_MULTIPLIERS: dict[ForecastScenario, float] = {
    ForecastScenario.BEST_CASE: 1.2,
    ForecastScenario.EXPECTED: 1.0,
    ForecastScenario.WORST_CASE: 0.7,
    ForecastScenario.COMMITTED: 1.0,
}


class PipelineForecastService:
    """Aggregates pipeline data into forecasts.

    Usage::

        svc = PipelineForecastService()

        deals = [
            DealSnapshot(
                deal_id="d1", name="Acme Corp",
                stage="proposal", amount=50000,
                probability=0.5, expected_close=date(2024, 3, 15),
                owner_id="rep-1", team="enterprise",
            ),
            ...
        ]

        report = svc.generate_forecast(deals, period=ForecastPeriod.MONTHLY)
    """

    def __init__(
        self,
        stage_probabilities: dict[str, float] | None = None,
    ) -> None:
        self.stage_probabilities = (
            stage_probabilities or DEFAULT_STAGE_PROBABILITIES
        )

    def generate_forecast(
        self,
        deals: list[DealSnapshot],
        *,
        period: ForecastPeriod = ForecastPeriod.MONTHLY,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> ForecastReport:
        """Generate a complete forecast report."""
        if not deals:
            return ForecastReport(period_type=period)

        # Filter by date range
        filtered = deals
        if start_date:
            filtered = [
                d for d in filtered if d.expected_close >= start_date
            ]
        if end_date:
            filtered = [
                d for d in filtered if d.expected_close <= end_date
            ]

        # Build time buckets
        buckets = self._build_buckets(filtered, period)

        # Build team/owner rollups
        by_team = self._rollup_by_field(filtered, "team")
        by_owner = self._rollup_by_field(filtered, "owner_id")

        return ForecastReport(
            period_type=period,
            buckets=buckets,
            by_team=by_team,
            by_owner=by_owner,
            total_pipeline=sum(d.amount for d in filtered),
            total_weighted=sum(
                d.amount * d.probability for d in filtered
            ),
            total_committed=sum(
                d.amount for d in filtered if d.is_committed
            ),
            total_deals=len(filtered),
        )

    def _build_buckets(
        self,
        deals: list[DealSnapshot],
        period: ForecastPeriod,
    ) -> list[ForecastBucket]:
        """Group deals into time-period buckets."""
        grouped: dict[str, list[DealSnapshot]] = defaultdict(list)

        for deal in deals:
            key = self._period_key(deal.expected_close, period)
            grouped[key].append(deal)

        buckets: list[ForecastBucket] = []
        for key in sorted(grouped.keys()):
            bucket_deals = grouped[key]
            period_start, period_end = self._period_range(
                key, period
            )

            total = sum(d.amount for d in bucket_deals)
            weighted = sum(
                d.amount * d.probability for d in bucket_deals
            )
            committed = sum(
                d.amount for d in bucket_deals if d.is_committed
            )
            avg_prob = (
                sum(d.probability for d in bucket_deals)
                / len(bucket_deals)
                if bucket_deals
                else 0.0
            )

            bucket = ForecastBucket(
                period_label=key,
                period_start=period_start,
                period_end=period_end,
                total_pipeline=total,
                weighted_pipeline=weighted,
                committed=committed,
                best_case=weighted * SCENARIO_MULTIPLIERS[ForecastScenario.BEST_CASE],
                expected=weighted,
                worst_case=weighted * SCENARIO_MULTIPLIERS[ForecastScenario.WORST_CASE],
                deal_count=len(bucket_deals),
                avg_probability=avg_prob,
                deals=bucket_deals,
            )
            buckets.append(bucket)

        return buckets

    def _rollup_by_field(
        self,
        deals: list[DealSnapshot],
        field_name: str,
    ) -> list[TeamForecast]:
        """Roll up deals by a grouping field (team or owner)."""
        grouped: dict[str, list[DealSnapshot]] = defaultdict(list)
        for deal in deals:
            key = getattr(deal, field_name, "") or "unassigned"
            grouped[key].append(deal)

        result: list[TeamForecast] = []
        for key, group in sorted(grouped.items()):
            tf = TeamForecast(
                owner_id=key if field_name == "owner_id" else "",
                team=key if field_name == "team" else "",
                total_pipeline=sum(d.amount for d in group),
                weighted_pipeline=sum(
                    d.amount * d.probability for d in group
                ),
                committed=sum(
                    d.amount for d in group if d.is_committed
                ),
                deal_count=len(group),
            )
            result.append(tf)

        return result

    @staticmethod
    def _period_key(d: date, period: ForecastPeriod) -> str:
        if period == ForecastPeriod.WEEKLY:
            iso = d.isocalendar()
            return f"{iso[0]}-W{iso[1]:02d}"
        elif period == ForecastPeriod.MONTHLY:
            return f"{d.year}-{d.month:02d}"
        else:  # quarterly
            q = (d.month - 1) // 3 + 1
            return f"{d.year}-Q{q}"

    @staticmethod
    def _period_range(
        key: str, period: ForecastPeriod
    ) -> tuple[date, date]:
        """Parse a period key back to start/end dates."""
        if period == ForecastPeriod.WEEKLY:
            year, week = key.split("-W")
            start = date.fromisocalendar(int(year), int(week), 1)
            end = start + timedelta(days=6)
        elif period == ForecastPeriod.MONTHLY:
            year, month = key.split("-")
            start = date(int(year), int(month), 1)
            if int(month) == 12:
                end = date(int(year) + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(int(year), int(month) + 1, 1) - timedelta(
                    days=1
                )
        else:  # quarterly
            year, q_str = key.split("-Q")
            q = int(q_str)
            start_month = (q - 1) * 3 + 1
            start = date(int(year), start_month, 1)
            end_month = start_month + 2
            if end_month == 12:
                end = date(int(year), 12, 31)
            else:
                end = date(int(year), end_month + 1, 1) - timedelta(
                    days=1
                )
        return start, end

    # ------------------------------------------------------------------
    # Pipeline velocity analytics
    # ------------------------------------------------------------------

    def calculate_velocity(
        self, deals: list[DealSnapshot]
    ) -> dict[str, Any]:
        """Calculate pipeline velocity metrics.

        Velocity = (# deals × win rate × avg deal size) / avg sales cycle
        """
        won = [d for d in deals if d.stage == "closed_won"]
        lost = [d for d in deals if d.stage == "closed_lost"]
        total_closed = len(won) + len(lost)
        win_rate = len(won) / total_closed if total_closed else 0.0
        avg_deal = sum(d.amount for d in won) / len(won) if won else 0.0

        return {
            "total_deals": len(deals),
            "won_deals": len(won),
            "lost_deals": len(lost),
            "win_rate": round(win_rate, 3),
            "avg_deal_size": round(avg_deal, 2),
            "total_pipeline_value": sum(d.amount for d in deals),
            "weighted_pipeline_value": sum(
                d.amount * d.probability for d in deals
            ),
        }
