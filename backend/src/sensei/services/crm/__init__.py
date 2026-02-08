"""CRM services — pipeline automation, forecasting, and external connectors."""

from sensei.services.crm.pipeline_automation import (
    PipelineAutomationService,
    PipelineStage,
    ActivityType,
    DealScore,
    StageTransition,
    FollowUpReminder,
    ScoringConfig,
)
from sensei.services.crm.pipeline_forecast import (
    PipelineForecastService,
)
from sensei.services.crm.crm_connector import (
    CRMConnector,
)

__all__ = [
    "PipelineAutomationService",
    "PipelineStage",
    "ActivityType",
    "DealScore",
    "StageTransition",
    "FollowUpReminder",
    "ScoringConfig",
    "PipelineForecastService",
    "CRMConnector",
]
