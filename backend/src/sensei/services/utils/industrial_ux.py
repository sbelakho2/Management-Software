"""Industrial UX & Navigation Resiliency (Development Plan 21.11).

Implements:
- High-Glare Theme: contrast validation for outdoor/high-light environments.
- Glove-Friendly Touch Targets: 48px minimum hit target enforcement.
- HID Scanner Feedback: global scan listener with success/failure cues.
- Offline Voice-to-Text: voice note capture using local STT.
- Barcode Navigation: scan station code → open station dashboard.
- Background Sync Resilience: sync survival during battery saving modes.

Backend service layer supporting the frontend UX features.
Pure in-memory Python service following sensei services conventions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Iterable
from uuid import UUID, uuid4


class ThemeMode(str, Enum):
    STANDARD = "standard"
    HIGH_GLARE = "high_glare"
    DARK = "dark"


class ScanResultType(str, Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID_FORMAT = "invalid_format"
    ERROR = "error"


class VoiceNoteStatus(str, Enum):
    PENDING_TRANSCRIPTION = "pending_transcription"
    TRANSCRIBED = "transcribed"
    FAILED = "failed"


class SyncQueueStatus(str, Enum):
    QUEUED = "queued"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ThemeConfig:
    id: UUID
    user_id: UUID
    mode: ThemeMode
    min_contrast_ratio: float  # WCAG AA is 4.5:1, AAA is 7:1.
    touch_target_size_px: int
    created_at: datetime


@dataclass(frozen=True)
class ScanResult:
    id: UUID
    scanned_value: str
    result_type: ScanResultType
    target_entity_type: str | None
    target_entity_id: UUID | None
    navigation_path: str | None
    scanned_at: datetime


@dataclass
class VoiceNote:
    id: UUID
    user_id: UUID
    audio_blob_key: str
    duration_seconds: float
    status: VoiceNoteStatus
    transcription: str | None
    created_at: datetime
    transcribed_at: datetime | None = None


@dataclass
class SyncQueueItem:
    id: UUID
    user_id: UUID
    entity_type: str
    entity_id: UUID
    operation: str  # "create", "update", "delete"
    payload: dict[str, Any]
    status: SyncQueueStatus
    queued_at: datetime
    synced_at: datetime | None = None
    retry_count: int = 0


class IndustrialUXService:
    """In-memory service supporting industrial UX features."""

    def __init__(self) -> None:
        self._theme_configs: dict[UUID, ThemeConfig] = {}
        self._scan_history: list[ScanResult] = []
        self._voice_notes: dict[UUID, VoiceNote] = {}
        self._sync_queue: dict[UUID, SyncQueueItem] = {}

        # Registered barcode patterns for navigation.
        self._barcode_routes: dict[str, tuple[str, str]] = {}  # prefix → (entity_type, nav_path_template)

    # ---- Theme Configuration ----

    def set_user_theme(
        self,
        *,
        user_id: UUID,
        mode: ThemeMode,
        min_contrast_ratio: float = 4.5,
        touch_target_size_px: int = 48,
    ) -> ThemeConfig:
        if touch_target_size_px < 44:
            raise ValueError("Touch target must be at least 44px for accessibility")
        if min_contrast_ratio < 3.0:
            raise ValueError("Contrast ratio must be at least 3.0")

        config = ThemeConfig(
            id=uuid4(),
            user_id=user_id,
            mode=mode,
            min_contrast_ratio=min_contrast_ratio,
            touch_target_size_px=touch_target_size_px,
            created_at=_utcnow(),
        )
        self._theme_configs[user_id] = config
        return config

    def get_user_theme(self, user_id: UUID) -> ThemeConfig | None:
        return self._theme_configs.get(user_id)

    def validate_contrast(self, foreground: str, background: str) -> dict[str, Any]:
        """Validate contrast ratio (simplified RGB luminance calculation)."""
        def parse_hex(color: str) -> tuple[int, int, int]:
            c = color.lstrip("#")
            return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

        def luminance(rgb: tuple[int, int, int]) -> float:
            def adjust(c: int) -> float:
                cs = c / 255
                return cs / 12.92 if cs <= 0.03928 else ((cs + 0.055) / 1.055) ** 2.4

            r, g, b = rgb
            return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

        try:
            fg_lum = luminance(parse_hex(foreground))
            bg_lum = luminance(parse_hex(background))
        except (ValueError, IndexError):
            return {"valid": False, "ratio": 0.0, "error": "Invalid color format"}

        lighter = max(fg_lum, bg_lum)
        darker = min(fg_lum, bg_lum)
        ratio = (lighter + 0.05) / (darker + 0.05)

        return {
            "valid": ratio >= 4.5,
            "ratio": round(ratio, 2),
            "aa_compliant": ratio >= 4.5,
            "aaa_compliant": ratio >= 7.0,
        }

    # ---- HID Scanner Feedback ----

    def register_barcode_route(
        self,
        *,
        prefix: str,
        entity_type: str,
        nav_path_template: str,
    ) -> None:
        """Register a barcode prefix for navigation routing."""
        self._barcode_routes[prefix.upper()] = (entity_type, nav_path_template)

    def process_scan(
        self,
        *,
        scanned_value: str,
        lookup_entity: Callable[..., Any] | None = None,  # Optional function to resolve entity.
    ) -> ScanResult:
        """Process a barcode scan and determine navigation target."""
        scanned = scanned_value.strip().upper()

        if not scanned:
            result = ScanResult(
                id=uuid4(),
                scanned_value=scanned_value,
                result_type=ScanResultType.INVALID_FORMAT,
                target_entity_type=None,
                target_entity_id=None,
                navigation_path=None,
                scanned_at=_utcnow(),
            )
            self._scan_history.append(result)
            return result

        # Find matching prefix.
        matched_prefix = None
        for prefix in self._barcode_routes:
            if scanned.startswith(prefix):
                matched_prefix = prefix
                break

        if not matched_prefix:
            result = ScanResult(
                id=uuid4(),
                scanned_value=scanned_value,
                result_type=ScanResultType.NOT_FOUND,
                target_entity_type=None,
                target_entity_id=None,
                navigation_path=None,
                scanned_at=_utcnow(),
            )
            self._scan_history.append(result)
            return result

        entity_type, nav_template = self._barcode_routes[matched_prefix]
        entity_code = scanned[len(matched_prefix):]

        # Build navigation path.
        nav_path = nav_template.replace("{code}", entity_code)

        result = ScanResult(
            id=uuid4(),
            scanned_value=scanned_value,
            result_type=ScanResultType.SUCCESS,
            target_entity_type=entity_type,
            target_entity_id=None,  # Would be resolved by lookup_entity if provided.
            navigation_path=nav_path,
            scanned_at=_utcnow(),
        )
        self._scan_history.append(result)
        return result

    def get_scan_history(self, *, limit: int = 50) -> list[ScanResult]:
        return sorted(self._scan_history, key=lambda s: s.scanned_at, reverse=True)[:limit]

    # ---- Offline Voice-to-Text ----

    def create_voice_note(
        self,
        *,
        user_id: UUID,
        audio_blob_key: str,
        duration_seconds: float,
    ) -> VoiceNote:
        note = VoiceNote(
            id=uuid4(),
            user_id=user_id,
            audio_blob_key=audio_blob_key,
            duration_seconds=duration_seconds,
            status=VoiceNoteStatus.PENDING_TRANSCRIPTION,
            transcription=None,
            created_at=_utcnow(),
        )
        self._voice_notes[note.id] = note
        return note

    def complete_transcription(
        self,
        note_id: UUID,
        *,
        transcription: str,
    ) -> VoiceNote:
        if note_id not in self._voice_notes:
            raise KeyError("Voice note not found")

        note = self._voice_notes[note_id]
        note.transcription = transcription
        note.status = VoiceNoteStatus.TRANSCRIBED
        note.transcribed_at = _utcnow()
        return note

    def list_voice_notes(
        self,
        user_id: UUID,
        *,
        status: VoiceNoteStatus | None = None,
    ) -> list[VoiceNote]:
        result = [n for n in self._voice_notes.values() if n.user_id == user_id]
        if status:
            result = [n for n in result if n.status == status]
        result.sort(key=lambda n: n.created_at, reverse=True)
        return result

    # ---- Background Sync Resilience ----

    def queue_sync_item(
        self,
        *,
        user_id: UUID,
        entity_type: str,
        entity_id: UUID,
        operation: str,
        payload: dict[str, Any],
    ) -> SyncQueueItem:
        item = SyncQueueItem(
            id=uuid4(),
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload=payload,
            status=SyncQueueStatus.QUEUED,
            queued_at=_utcnow(),
        )
        self._sync_queue[item.id] = item
        return item

    def mark_synced(self, item_id: UUID) -> SyncQueueItem:
        if item_id not in self._sync_queue:
            raise KeyError("Sync queue item not found")

        item = self._sync_queue[item_id]
        item.status = SyncQueueStatus.SYNCED
        item.synced_at = _utcnow()
        return item

    def mark_conflict(self, item_id: UUID) -> SyncQueueItem:
        if item_id not in self._sync_queue:
            raise KeyError("Sync queue item not found")

        item = self._sync_queue[item_id]
        item.status = SyncQueueStatus.CONFLICT
        return item

    def retry_sync(self, item_id: UUID) -> SyncQueueItem:
        if item_id not in self._sync_queue:
            raise KeyError("Sync queue item not found")

        item = self._sync_queue[item_id]
        item.status = SyncQueueStatus.QUEUED
        item.retry_count += 1
        return item

    def get_pending_sync_items(self, user_id: UUID) -> list[SyncQueueItem]:
        result = [
            i for i in self._sync_queue.values()
            if i.user_id == user_id and i.status == SyncQueueStatus.QUEUED
        ]
        result.sort(key=lambda i: i.queued_at)
        return result

    def get_conflict_items(self, user_id: UUID) -> list[SyncQueueItem]:
        result = [
            i for i in self._sync_queue.values()
            if i.user_id == user_id and i.status == SyncQueueStatus.CONFLICT
        ]
        result.sort(key=lambda i: i.queued_at)
        return result
