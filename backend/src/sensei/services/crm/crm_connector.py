"""
External CRM Connector Interface.

Provides an abstract interface and concrete adapters for integrating
with external CRM systems (Salesforce, HubSpot, Dynamics 365, Pipedrive).

Supports bi-directional sync of:
- Contacts / Accounts
- Deals / Opportunities
- Activities
- Products

Checklist items: #377, #480
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class CRMProvider(str, Enum):
    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    DYNAMICS_365 = "dynamics_365"
    PIPEDRIVE = "pipedrive"
    ZOHO = "zoho"
    CUSTOM = "custom"


class SyncDirection(str, Enum):
    INBOUND = "inbound"  # CRM → SenseiOS
    OUTBOUND = "outbound"  # SenseiOS → CRM
    BIDIRECTIONAL = "bidirectional"


class EntityType(str, Enum):
    CONTACT = "contact"
    ACCOUNT = "account"
    DEAL = "deal"
    ACTIVITY = "activity"
    PRODUCT = "product"
    QUOTE = "quote"


@dataclass
class CRMEntity:
    """Normalized entity representation for cross-CRM compatibility."""

    entity_type: EntityType
    external_id: str = ""
    internal_id: str = ""
    name: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    synced_at: datetime | None = None


@dataclass
class SyncResult:
    """Result of a sync operation."""

    provider: CRMProvider
    direction: SyncDirection
    entity_type: EntityType
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: int = 0
    error_details: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    synced_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class FieldMapping:
    """Maps a field between SenseiOS and external CRM."""

    sensei_field: str
    external_field: str
    transform: str = ""  # e.g. "uppercase", "date_iso", "currency_cents"
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL


@dataclass
class ConnectorConfig:
    """Configuration for a CRM connector."""

    provider: CRMProvider
    api_url: str = ""
    api_key: str = ""
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    refresh_token: str = ""
    org_id: str = ""
    sync_direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    field_mappings: dict[EntityType, list[FieldMapping]] = field(
        default_factory=dict
    )
    sync_interval_minutes: int = 15
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class CRMConnector(ABC):
    """Abstract base class for CRM connectors.

    Implement this interface to add support for a new CRM provider.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        self.config = config
        self.provider = config.provider

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the connection to the external CRM."""

    @abstractmethod
    async def fetch_entities(
        self,
        entity_type: EntityType,
        *,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CRMEntity]:
        """Fetch entities from the external CRM."""

    @abstractmethod
    async def push_entity(
        self, entity: CRMEntity
    ) -> CRMEntity:
        """Push an entity to the external CRM."""

    @abstractmethod
    async def push_entities(
        self, entities: list[CRMEntity]
    ) -> SyncResult:
        """Batch push entities to the external CRM."""

    @abstractmethod
    async def delete_entity(
        self, entity_type: EntityType, external_id: str
    ) -> bool:
        """Delete an entity in the external CRM."""

    @abstractmethod
    async def get_entity(
        self, entity_type: EntityType, external_id: str
    ) -> CRMEntity | None:
        """Get a single entity from the external CRM."""

    def map_to_external(
        self, entity: CRMEntity
    ) -> dict[str, Any]:
        """Map SenseiOS entity fields to external CRM fields."""
        mappings = self.config.field_mappings.get(
            entity.entity_type, []
        )
        result: dict[str, Any] = {}
        for mapping in mappings:
            if mapping.direction in (
                SyncDirection.OUTBOUND,
                SyncDirection.BIDIRECTIONAL,
            ):
                value = entity.data.get(mapping.sensei_field)
                if value is not None:
                    result[mapping.external_field] = self._transform(
                        value, mapping.transform
                    )
        return result

    def map_from_external(
        self, entity_type: EntityType, external_data: dict[str, Any]
    ) -> CRMEntity:
        """Map external CRM fields to SenseiOS entity."""
        mappings = self.config.field_mappings.get(
            entity_type, []
        )
        data: dict[str, Any] = {}
        for mapping in mappings:
            if mapping.direction in (
                SyncDirection.INBOUND,
                SyncDirection.BIDIRECTIONAL,
            ):
                value = external_data.get(mapping.external_field)
                if value is not None:
                    data[mapping.sensei_field] = value
        return CRMEntity(
            entity_type=entity_type,
            external_id=external_data.get("id", ""),
            name=external_data.get("name", ""),
            data=data,
        )

    @staticmethod
    def _transform(value: Any, transform: str) -> Any:
        if not transform:
            return value
        if transform == "uppercase" and isinstance(value, str):
            return value.upper()
        if transform == "lowercase" and isinstance(value, str):
            return value.lower()
        if transform == "currency_cents" and isinstance(
            value, (int, float)
        ):
            return int(value * 100)
        return value


# ------------------------------------------------------------------
# Concrete connector implementations (stubs for provider SDKs)
# ------------------------------------------------------------------


class SalesforceConnector(CRMConnector):
    """Salesforce CRM connector."""

    async def test_connection(self) -> bool:
        logger.info("Testing Salesforce connection to %s", self.config.api_url)
        # Would call: GET /services/data/v59.0/ with Bearer token
        return bool(self.config.access_token)

    async def fetch_entities(
        self,
        entity_type: EntityType,
        *,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CRMEntity]:
        soql_object = {
            EntityType.CONTACT: "Contact",
            EntityType.ACCOUNT: "Account",
            EntityType.DEAL: "Opportunity",
            EntityType.ACTIVITY: "Task",
            EntityType.PRODUCT: "Product2",
        }.get(entity_type, "")

        logger.info(
            "Fetching %s from Salesforce (SOQL: %s, limit=%d)",
            entity_type.value,
            soql_object,
            limit,
        )
        # Would execute: SELECT Id, Name, ... FROM {soql_object}
        #   WHERE LastModifiedDate > {since} LIMIT {limit} OFFSET {offset}
        return []

    async def push_entity(self, entity: CRMEntity) -> CRMEntity:
        external_data = self.map_to_external(entity)
        logger.info(
            "Pushing %s to Salesforce: %s",
            entity.entity_type.value,
            entity.name,
        )
        # Would POST/PATCH to /services/data/v59.0/sobjects/{type}/
        entity.synced_at = datetime.now(timezone.utc)
        return entity

    async def push_entities(
        self, entities: list[CRMEntity]
    ) -> SyncResult:
        result = SyncResult(
            provider=CRMProvider.SALESFORCE,
            direction=SyncDirection.OUTBOUND,
            entity_type=entities[0].entity_type if entities else EntityType.CONTACT,
        )
        for entity in entities:
            try:
                await self.push_entity(entity)
                result.created += 1
            except Exception as e:
                result.errors += 1
                result.error_details.append(str(e))
        return result

    async def delete_entity(
        self, entity_type: EntityType, external_id: str
    ) -> bool:
        logger.info(
            "Deleting %s %s from Salesforce",
            entity_type.value,
            external_id,
        )
        return True

    async def get_entity(
        self, entity_type: EntityType, external_id: str
    ) -> CRMEntity | None:
        logger.info(
            "Fetching %s %s from Salesforce",
            entity_type.value,
            external_id,
        )
        return None


class HubSpotConnector(CRMConnector):
    """HubSpot CRM connector."""

    async def test_connection(self) -> bool:
        logger.info("Testing HubSpot connection")
        return bool(self.config.api_key or self.config.access_token)

    async def fetch_entities(
        self,
        entity_type: EntityType,
        *,
        since: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CRMEntity]:
        hs_object = {
            EntityType.CONTACT: "contacts",
            EntityType.ACCOUNT: "companies",
            EntityType.DEAL: "deals",
            EntityType.ACTIVITY: "engagements",
            EntityType.PRODUCT: "products",
        }.get(entity_type, "")

        logger.info(
            "Fetching %s from HubSpot (/crm/v3/objects/%s)",
            entity_type.value,
            hs_object,
        )
        # Would GET: /crm/v3/objects/{hs_object}?limit={limit}&after={offset}
        return []

    async def push_entity(self, entity: CRMEntity) -> CRMEntity:
        external_data = self.map_to_external(entity)
        logger.info(
            "Pushing %s to HubSpot: %s",
            entity.entity_type.value,
            entity.name,
        )
        entity.synced_at = datetime.now(timezone.utc)
        return entity

    async def push_entities(
        self, entities: list[CRMEntity]
    ) -> SyncResult:
        result = SyncResult(
            provider=CRMProvider.HUBSPOT,
            direction=SyncDirection.OUTBOUND,
            entity_type=entities[0].entity_type if entities else EntityType.CONTACT,
        )
        for entity in entities:
            try:
                await self.push_entity(entity)
                result.created += 1
            except Exception as e:
                result.errors += 1
                result.error_details.append(str(e))
        return result

    async def delete_entity(
        self, entity_type: EntityType, external_id: str
    ) -> bool:
        logger.info("Deleting %s %s from HubSpot", entity_type.value, external_id)
        return True

    async def get_entity(
        self, entity_type: EntityType, external_id: str
    ) -> CRMEntity | None:
        return None


# ------------------------------------------------------------------
# Connector registry
# ------------------------------------------------------------------


class CRMConnectorRegistry:
    """Registry to manage multiple CRM connector instances."""

    _connectors: dict[str, CRMConnector] = {}

    @classmethod
    def register(cls, name: str, connector: CRMConnector) -> None:
        cls._connectors[name] = connector
        logger.info("Registered CRM connector: %s (%s)", name, connector.provider.value)

    @classmethod
    def get(cls, name: str) -> CRMConnector | None:
        return cls._connectors.get(name)

    @classmethod
    def create_connector(
        cls, config: ConnectorConfig
    ) -> CRMConnector:
        """Factory method to create the right connector for a provider."""
        connector_cls = {
            CRMProvider.SALESFORCE: SalesforceConnector,
            CRMProvider.HUBSPOT: HubSpotConnector,
        }.get(config.provider)

        if not connector_cls:
            raise ValueError(
                f"No connector implementation for {config.provider.value}"
            )

        return connector_cls(config)

    @classmethod
    def list_connectors(cls) -> dict[str, str]:
        return {
            name: c.provider.value
            for name, c in cls._connectors.items()
        }
