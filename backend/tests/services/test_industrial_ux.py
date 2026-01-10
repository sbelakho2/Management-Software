"""Tests for Industrial UX & Navigation Resiliency service."""

from __future__ import annotations

from uuid import uuid4

import pytest

from sensei.services.industrial_ux import (
    IndustrialUXService,
    ScanResultType,
    SyncQueueStatus,
    ThemeConfig,
    ThemeMode,
    VoiceNote,
    VoiceNoteStatus,
)


@pytest.fixture
def svc() -> IndustrialUXService:
    return IndustrialUXService()


class TestThemeConfiguration:
    def test_set_user_theme(self, svc: IndustrialUXService) -> None:
        user_id = uuid4()
        config = svc.set_user_theme(
            user_id=user_id,
            mode=ThemeMode.HIGH_GLARE,
            min_contrast_ratio=7.0,
            touch_target_size_px=56,
        )

        assert isinstance(config, ThemeConfig)
        assert config.mode == ThemeMode.HIGH_GLARE
        assert config.touch_target_size_px == 56

        retrieved = svc.get_user_theme(user_id)
        assert retrieved == config

    def test_touch_target_minimum_enforced(self, svc: IndustrialUXService) -> None:
        with pytest.raises(ValueError, match="44px"):
            svc.set_user_theme(
                user_id=uuid4(),
                mode=ThemeMode.STANDARD,
                touch_target_size_px=40,
            )

    def test_contrast_ratio_minimum(self, svc: IndustrialUXService) -> None:
        with pytest.raises(ValueError, match="3.0"):
            svc.set_user_theme(
                user_id=uuid4(),
                mode=ThemeMode.DARK,
                min_contrast_ratio=2.0,
            )

    def test_validate_contrast(self, svc: IndustrialUXService) -> None:
        # White on black should have high contrast.
        result = svc.validate_contrast("#FFFFFF", "#000000")
        assert result["valid"] is True
        assert result["aaa_compliant"] is True
        assert result["ratio"] >= 21.0

        # Similar grays should fail.
        result2 = svc.validate_contrast("#808080", "#909090")
        assert result2["valid"] is False


class TestHIDScannerFeedback:
    def test_register_and_process_scan(self, svc: IndustrialUXService) -> None:
        svc.register_barcode_route(
            prefix="STN-",
            entity_type="station",
            nav_path_template="/stations/{code}",
        )

        result = svc.process_scan(scanned_value="STN-001")
        assert result.result_type == ScanResultType.SUCCESS
        assert result.target_entity_type == "station"
        assert result.navigation_path == "/stations/001"

    def test_scan_not_found(self, svc: IndustrialUXService) -> None:
        result = svc.process_scan(scanned_value="UNKNOWN-123")
        assert result.result_type == ScanResultType.NOT_FOUND

    def test_scan_empty_invalid(self, svc: IndustrialUXService) -> None:
        result = svc.process_scan(scanned_value="   ")
        assert result.result_type == ScanResultType.INVALID_FORMAT

    def test_scan_history(self, svc: IndustrialUXService) -> None:
        svc.register_barcode_route(prefix="WO-", entity_type="work_order", nav_path_template="/wo/{code}")
        svc.process_scan(scanned_value="WO-100")
        svc.process_scan(scanned_value="WO-101")

        history = svc.get_scan_history(limit=10)
        assert len(history) == 2


class TestVoiceNotes:
    def test_create_and_transcribe(self, svc: IndustrialUXService) -> None:
        user_id = uuid4()
        note = svc.create_voice_note(
            user_id=user_id,
            audio_blob_key="blob-123",
            duration_seconds=5.5,
        )

        assert isinstance(note, VoiceNote)
        assert note.status == VoiceNoteStatus.PENDING_TRANSCRIPTION

        completed = svc.complete_transcription(note.id, transcription="Check station 5")
        assert completed.status == VoiceNoteStatus.TRANSCRIBED
        assert completed.transcription == "Check station 5"

    def test_list_voice_notes_by_status(self, svc: IndustrialUXService) -> None:
        user_id = uuid4()
        n1 = svc.create_voice_note(user_id=user_id, audio_blob_key="b1", duration_seconds=3.0)
        n2 = svc.create_voice_note(user_id=user_id, audio_blob_key="b2", duration_seconds=4.0)
        svc.complete_transcription(n1.id, transcription="Test")

        pending = svc.list_voice_notes(user_id, status=VoiceNoteStatus.PENDING_TRANSCRIPTION)
        assert len(pending) == 1
        assert pending[0].id == n2.id


class TestBackgroundSyncResilience:
    def test_queue_and_sync_item(self, svc: IndustrialUXService) -> None:
        user_id = uuid4()
        entity_id = uuid4()

        item = svc.queue_sync_item(
            user_id=user_id,
            entity_type="work_order",
            entity_id=entity_id,
            operation="create",
            payload={"wo_number": "WO-001"},
        )

        assert item.status == SyncQueueStatus.QUEUED

        pending = svc.get_pending_sync_items(user_id)
        assert len(pending) == 1

        synced = svc.mark_synced(item.id)
        assert synced.status == SyncQueueStatus.SYNCED

        pending2 = svc.get_pending_sync_items(user_id)
        assert len(pending2) == 0

    def test_conflict_handling(self, svc: IndustrialUXService) -> None:
        user_id = uuid4()
        item = svc.queue_sync_item(
            user_id=user_id,
            entity_type="quality_event",
            entity_id=uuid4(),
            operation="update",
            payload={"status": "closed"},
        )

        conflict = svc.mark_conflict(item.id)
        assert conflict.status == SyncQueueStatus.CONFLICT

        conflicts = svc.get_conflict_items(user_id)
        assert len(conflicts) == 1

    def test_retry_sync(self, svc: IndustrialUXService) -> None:
        user_id = uuid4()
        item = svc.queue_sync_item(
            user_id=user_id,
            entity_type="andon_event",
            entity_id=uuid4(),
            operation="create",
            payload={},
        )

        svc.mark_conflict(item.id)
        retried = svc.retry_sync(item.id)

        assert retried.status == SyncQueueStatus.QUEUED
        assert retried.retry_count == 1
