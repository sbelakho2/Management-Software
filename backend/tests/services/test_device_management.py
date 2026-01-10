"""Tests for Device Management (MDM-lite) service."""

from __future__ import annotations

from uuid import uuid4

import pytest

from sensei.services.device_management import (
    CommandStatus,
    DeviceCommand,
    DeviceManagementService,
    DeviceProfile,
    DeviceStatus,
    EnrolledDevice,
)


@pytest.fixture
def svc() -> DeviceManagementService:
    return DeviceManagementService()


ADMIN_ROLES = ("admin",)
IT_ROLES = ("it",)
VIEWER_ROLES = ("viewer",)


class TestDeviceProfiles:
    def test_create_profile_requires_admin(self, svc: DeviceManagementService) -> None:
        with pytest.raises(PermissionError):
            svc.create_profile(
                name="Production Kiosk",
                description="Floor terminal",
                allowed_apps=["sensei-app"],
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )

        profile = svc.create_profile(
            name="Production Kiosk",
            description="Floor terminal",
            allowed_apps=["sensei-app", "browser"],
            actor_user_id=uuid4(),
            actor_roles=IT_ROLES,
            kiosk_mode=True,
        )

        assert isinstance(profile, DeviceProfile)
        assert profile.kiosk_mode is True
        assert len(profile.allowed_apps) == 2

    def test_toggle_profile(self, svc: DeviceManagementService) -> None:
        profile = svc.create_profile(
            name="Test",
            description="desc",
            allowed_apps=[],
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        assert profile.enabled is True

        disabled = svc.toggle_profile(profile.id, enabled=False, actor_roles=ADMIN_ROLES)
        assert disabled.enabled is False


class TestDeviceEnrollment:
    def test_enroll_and_list_devices(self, svc: DeviceManagementService) -> None:
        device = svc.enroll_device(
            device_identifier="SN-1234-ABCD",
            display_name="Floor Kiosk A",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        assert isinstance(device, EnrolledDevice)
        assert device.status == DeviceStatus.ENROLLED

        devices = svc.list_devices(actor_roles=ADMIN_ROLES)
        assert len(devices) == 1

    def test_unenroll_device(self, svc: DeviceManagementService) -> None:
        device = svc.enroll_device(
            device_identifier="SN-5678",
            display_name="Old Terminal",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        unenrolled = svc.unenroll_device(device.id, actor_roles=ADMIN_ROLES)
        assert unenrolled.status == DeviceStatus.UNENROLLED


class TestRemoteCommands:
    def test_lock_wipe_unlock_flow(self, svc: DeviceManagementService) -> None:
        device = svc.enroll_device(
            device_identifier="SN-9999",
            display_name="Warehouse Scanner",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        # Lock the device.
        lock_cmd = svc.issue_command(
            device.id,
            command=DeviceCommand.LOCK,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        assert lock_cmd.status == CommandStatus.PENDING
        assert svc._devices[device.id].status == DeviceStatus.LOCKED

        # Unlock the device.
        svc.issue_command(
            device.id,
            command=DeviceCommand.UNLOCK,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        assert svc._devices[device.id].status == DeviceStatus.ENROLLED

        # Wipe the device.
        wipe_cmd = svc.issue_command(
            device.id,
            command=DeviceCommand.WIPE,
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )
        assert svc._devices[device.id].status == DeviceStatus.WIPED

        # Acknowledge the command.
        ack = svc.acknowledge_command(wipe_cmd.id)
        assert ack.status == CommandStatus.ACKNOWLEDGED
        assert ack.acknowledged_at is not None

    def test_commands_require_admin(self, svc: DeviceManagementService) -> None:
        device = svc.enroll_device(
            device_identifier="SN-0000",
            display_name="Terminal B",
            actor_user_id=uuid4(),
            actor_roles=ADMIN_ROLES,
        )

        with pytest.raises(PermissionError):
            svc.issue_command(
                device.id,
                command=DeviceCommand.LOCATE,
                actor_user_id=uuid4(),
                actor_roles=VIEWER_ROLES,
            )
