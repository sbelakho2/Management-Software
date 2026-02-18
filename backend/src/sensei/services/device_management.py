"""Device Management (Development Plan 21.8 — MDM-lite).

Implements:
- Kiosk Mode Lockdown: device profiles restricting to approved applications.
- Remote Security Controls: lock, wipe, and locate commands for enrolled devices.

Pure in-memory Python service following sensei services conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable
from uuid import UUID, uuid4

from sensei.services.core.persistent_service_mixin import PersistentServiceMixin
from sensei.services.core.state_codec import decode_dataclass, encode_dataclass


class DeviceStatus(str, Enum):
    ENROLLED = "enrolled"
    PENDING = "pending"
    LOCKED = "locked"
    WIPED = "wiped"
    UNENROLLED = "unenrolled"


class DeviceCommand(str, Enum):
    LOCK = "lock"
    WIPE = "wipe"
    UNLOCK = "unlock"
    LOCATE = "locate"


class CommandStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"


_MDM_ADMIN_ROLES: set[str] = {"admin", "secops", "gm", "it"}
_DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000000")


def _norm_roles(roles: Iterable[str]) -> set[str]:
    return {r.strip().lower() for r in roles if r and r.strip()}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DeviceProfile:
    """Kiosk-mode profile restricting device to allowed apps."""

    id: UUID
    name: str
    description: str
    allowed_apps: list[str]
    kiosk_mode: bool
    enabled: bool
    created_at: datetime
    created_by: UUID


@dataclass
class EnrolledDevice:
    id: UUID
    device_identifier: str  # Serial or hardware ID.
    display_name: str
    assigned_user_id: UUID | None
    profile_id: UUID | None
    status: DeviceStatus
    last_check_in: datetime | None
    enrolled_at: datetime
    enrolled_by: UUID


@dataclass(frozen=True)
class DeviceCommandRecord:
    id: UUID
    device_id: UUID
    command: DeviceCommand
    status: CommandStatus
    issued_at: datetime
    issued_by: UUID
    acknowledged_at: datetime | None = None


class DeviceManagementService(PersistentServiceMixin):
    """In-memory MDM-lite service."""

    SERVICE_NAME = "device_management"

    def __init__(self) -> None:
        self._profiles: dict[UUID, DeviceProfile] = {}
        self._devices: dict[UUID, EnrolledDevice] = {}
        self._commands: dict[UUID, DeviceCommandRecord] = {}
        self._state_loaded = False

    async def load_from_db(self) -> None:
        if self._state_loaded:
            return

        profiles_data = await self.load_state(_DEFAULT_TENANT_ID, "profiles") or {}
        devices_data = await self.load_state(_DEFAULT_TENANT_ID, "devices") or {}
        commands_data = await self.load_state(_DEFAULT_TENANT_ID, "commands") or {}

        self._profiles = {UUID(pid): decode_dataclass(p, DeviceProfile) for pid, p in profiles_data.items()}
        self._devices = {UUID(did): decode_dataclass(d, EnrolledDevice) for did, d in devices_data.items()}
        self._commands = {UUID(cid): decode_dataclass(c, DeviceCommandRecord) for cid, c in commands_data.items()}
        self._state_loaded = True

    async def persist_all(self) -> None:
        profiles_data = {str(pid): encode_dataclass(p) for pid, p in self._profiles.items()}
        devices_data = {str(did): encode_dataclass(d) for did, d in self._devices.items()}
        commands_data = {str(cid): encode_dataclass(c) for cid, c in self._commands.items()}

        await self.save_state(_DEFAULT_TENANT_ID, "profiles", profiles_data)
        await self.save_state(_DEFAULT_TENANT_ID, "devices", devices_data)
        await self.save_state(_DEFAULT_TENANT_ID, "commands", commands_data)

    async def _ensure_loaded(self) -> None:
        if not self._state_loaded:
            await self.load_from_db()

    # ---- RBAC ----

    def can_admin(self, *, actor_roles: Iterable[str]) -> bool:
        return len(_norm_roles(actor_roles).intersection(_MDM_ADMIN_ROLES)) > 0

    # ---- Device Profiles ----

    def create_profile(
        self,
        *,
        name: str,
        description: str,
        allowed_apps: list[str],
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        kiosk_mode: bool = False,
        enabled: bool = True,
    ) -> DeviceProfile:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage device profiles")

        profile = DeviceProfile(
            id=uuid4(),
            name=name.strip(),
            description=description,
            allowed_apps=list(allowed_apps),
            kiosk_mode=kiosk_mode,
            enabled=enabled,
            created_at=_utcnow(),
            created_by=actor_user_id,
        )
        self._profiles[profile.id] = profile
        return profile

    async def create_profile_async(self, **kwargs: Any) -> DeviceProfile:
        await self._ensure_loaded()
        profile = self.create_profile(**kwargs)
        await self.persist_all()
        return profile

    def list_profiles(
        self,
        *,
        actor_roles: Iterable[str],
        only_enabled: bool = False,
    ) -> list[DeviceProfile]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view device profiles")

        result = list(self._profiles.values())
        if only_enabled:
            result = [p for p in result if p.enabled]
        result.sort(key=lambda p: p.name.lower())
        return result

    async def list_profiles_async(self, **kwargs: Any) -> list[DeviceProfile]:
        await self._ensure_loaded()
        return self.list_profiles(**kwargs)

    def toggle_profile(
        self,
        profile_id: UUID,
        *,
        enabled: bool,
        actor_roles: Iterable[str],
    ) -> DeviceProfile:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to manage device profiles")
        if profile_id not in self._profiles:
            raise KeyError("Device profile not found")

        old = self._profiles[profile_id]
        updated = DeviceProfile(
            id=old.id,
            name=old.name,
            description=old.description,
            allowed_apps=old.allowed_apps,
            kiosk_mode=old.kiosk_mode,
            enabled=enabled,
            created_at=old.created_at,
            created_by=old.created_by,
        )
        self._profiles[profile_id] = updated
        return updated

    async def toggle_profile_async(self, **kwargs: Any) -> DeviceProfile:
        await self._ensure_loaded()
        profile = self.toggle_profile(**kwargs)
        await self.persist_all()
        return profile

    # ---- Device Enrollment ----

    def enroll_device(
        self,
        *,
        device_identifier: str,
        display_name: str,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
        assigned_user_id: UUID | None = None,
        profile_id: UUID | None = None,
    ) -> EnrolledDevice:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to enroll devices")

        if profile_id and profile_id not in self._profiles:
            raise KeyError("Device profile not found")

        device = EnrolledDevice(
            id=uuid4(),
            device_identifier=device_identifier.strip(),
            display_name=display_name.strip(),
            assigned_user_id=assigned_user_id,
            profile_id=profile_id,
            status=DeviceStatus.ENROLLED,
            last_check_in=None,
            enrolled_at=_utcnow(),
            enrolled_by=actor_user_id,
        )
        self._devices[device.id] = device
        return device

    async def enroll_device_async(self, **kwargs: Any) -> EnrolledDevice:
        await self._ensure_loaded()
        device = self.enroll_device(**kwargs)
        await self.persist_all()
        return device

    def list_devices(
        self,
        *,
        actor_roles: Iterable[str],
        status_filter: DeviceStatus | None = None,
    ) -> list[EnrolledDevice]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view devices")

        result = list(self._devices.values())
        if status_filter:
            result = [d for d in result if d.status == status_filter]
        result.sort(key=lambda d: d.display_name.lower())
        return result

    async def list_devices_async(self, **kwargs: Any) -> list[EnrolledDevice]:
        await self._ensure_loaded()
        return self.list_devices(**kwargs)

    def unenroll_device(
        self,
        device_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> EnrolledDevice:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to unenroll devices")
        if device_id not in self._devices:
            raise KeyError("Device not found")

        device = self._devices[device_id]
        device.status = DeviceStatus.UNENROLLED
        return device

    async def unenroll_device_async(self, **kwargs: Any) -> EnrolledDevice:
        await self._ensure_loaded()
        device = self.unenroll_device(**kwargs)
        await self.persist_all()
        return device

    def record_check_in(self, device_id: UUID) -> EnrolledDevice:
        """Called by agent when device phones home."""
        if device_id not in self._devices:
            raise KeyError("Device not found")
        device = self._devices[device_id]
        device.last_check_in = _utcnow()
        return device

    async def record_check_in_async(self, device_id: UUID) -> EnrolledDevice:
        await self._ensure_loaded()
        device = self.record_check_in(device_id)
        await self.persist_all()
        return device

    # ---- Remote Commands ----

    def issue_command(
        self,
        device_id: UUID,
        *,
        command: DeviceCommand,
        actor_user_id: UUID,
        actor_roles: Iterable[str],
    ) -> DeviceCommandRecord:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to issue device commands")
        if device_id not in self._devices:
            raise KeyError("Device not found")

        record = DeviceCommandRecord(
            id=uuid4(),
            device_id=device_id,
            command=command,
            status=CommandStatus.PENDING,
            issued_at=_utcnow(),
            issued_by=actor_user_id,
        )
        self._commands[record.id] = record

        # Apply state changes immediately for lock/wipe.
        device = self._devices[device_id]
        if command == DeviceCommand.LOCK:
            device.status = DeviceStatus.LOCKED
        elif command == DeviceCommand.WIPE:
            device.status = DeviceStatus.WIPED
        elif command == DeviceCommand.UNLOCK and device.status == DeviceStatus.LOCKED:
            device.status = DeviceStatus.ENROLLED

        return record

    async def issue_command_async(self, **kwargs: Any) -> DeviceCommandRecord:
        await self._ensure_loaded()
        record = self.issue_command(**kwargs)
        await self.persist_all()
        return record

    def list_commands(
        self,
        device_id: UUID,
        *,
        actor_roles: Iterable[str],
    ) -> list[DeviceCommandRecord]:
        if not self.can_admin(actor_roles=actor_roles):
            raise PermissionError("Not permitted to view device commands")
        if device_id not in self._devices:
            raise KeyError("Device not found")

        result = [c for c in self._commands.values() if c.device_id == device_id]
        result.sort(key=lambda c: c.issued_at)
        return result

    async def list_commands_async(self, **kwargs: Any) -> list[DeviceCommandRecord]:
        await self._ensure_loaded()
        return self.list_commands(**kwargs)

    def acknowledge_command(self, command_id: UUID) -> DeviceCommandRecord:
        """Called by device agent when command is executed."""
        if command_id not in self._commands:
            raise KeyError("Command not found")

        old = self._commands[command_id]
        updated = DeviceCommandRecord(
            id=old.id,
            device_id=old.device_id,
            command=old.command,
            status=CommandStatus.ACKNOWLEDGED,
            issued_at=old.issued_at,
            issued_by=old.issued_by,
            acknowledged_at=_utcnow(),
        )
        self._commands[command_id] = updated
        return updated

    async def acknowledge_command_async(self, command_id: UUID) -> DeviceCommandRecord:
        await self._ensure_loaded()
        record = self.acknowledge_command(command_id)
        await self.persist_all()
        return record
