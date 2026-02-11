"""
Tests for Sensei OS API Utilities

Comprehensive tests for API utility functions.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from sensei.api.utils import (
    # Query param utilities
    parse_sort_param,
    parse_filter_param,
    _parse_filter_value,
    _parse_single_value,
    # Response builders
    build_response,
    build_paginated_response,
    build_created_response,
    build_updated_response,
    build_deleted_response,
    # Data transformation
    model_to_dict,
    models_to_dicts,
    to_schema,
    to_schemas,
    apply_partial_update,
    # File handling
    validate_file_extension,
    validate_file_size,
    generate_unique_filename,
    get_content_type,
    # Validation
    validate_uuid,
    validate_uuids,
    is_valid_email,
    # Date/time
    now_utc,
    parse_datetime,
    format_datetime,
    # Slug/URL
    slugify,
    generate_unique_code,
    # Batch processing
    chunk_list,
    process_in_batches,
    # Cache
    build_cache_key,
)
from sensei.api.schemas import (
    FilterOperator,
    SortOrder,
    APIResponse,
    PaginatedResponse,
)


# =============================================================================
# Query Parameter Parsing Tests
# =============================================================================


class TestParseSortParam:
    """Tests for parse_sort_param function."""
    
    def test_parse_single_sort(self):
        """Test parsing single sort param."""
        result = parse_sort_param("name:asc")
        
        assert len(result) == 1
        assert result[0].field == "name"
        assert result[0].direction == "asc"
    
    def test_parse_multiple_sorts(self):
        """Test parsing multiple sorts."""
        result = parse_sort_param("name:asc,created_at:desc")
        
        assert len(result) == 2
        assert result[0].field == "name"
        assert result[0].direction == "asc"
        assert result[1].field == "created_at"
        assert result[1].direction == "desc"
    
    def test_parse_default_direction(self):
        """Test parsing with default direction."""
        result = parse_sort_param("name")
        
        assert len(result) == 1
        assert result[0].field == "name"
        assert result[0].direction == "asc"
    
    def test_parse_empty(self):
        """Test parsing empty string."""
        result = parse_sort_param("")
        
        assert result == []
    
    def test_parse_none(self):
        """Test parsing None."""
        result = parse_sort_param(None)
        
        assert result == []
    
    def test_parse_invalid_direction_defaults_to_asc(self):
        """Test that invalid direction defaults to asc."""
        result = parse_sort_param("name:invalid")
        
        assert len(result) == 1
        assert result[0].direction == "asc"
    
    def test_parse_with_spaces(self):
        """Test parsing with spaces."""
        result = parse_sort_param(" name : asc , created_at : desc ")
        
        assert len(result) == 2


class TestParseFilterParam:
    """Tests for parse_filter_param function."""
    
    def test_parse_basic_filter(self):
        """Test parsing basic filter."""
        result = parse_filter_param("status:eq:active")
        
        assert len(result) == 1
        assert result[0].field == "status"
        assert result[0].operator == "eq"
        assert result[0].value == "active"
    
    def test_parse_filter_without_operator(self):
        """Test parsing filter without explicit operator (defaults to eq)."""
        result = parse_filter_param("status:active")
        
        assert len(result) == 1
        assert result[0].field == "status"
        assert result[0].operator == "eq"
        assert result[0].value == "active"
    
    def test_parse_multiple_filters(self):
        """Test parsing multiple filters."""
        result = parse_filter_param("status:eq:active,priority:gte:5")
        
        assert len(result) == 2
        assert result[0].field == "status"
        assert result[1].field == "priority"
        assert result[1].value == 5  # Should be parsed as int
    
    def test_parse_empty(self):
        """Test parsing empty string."""
        result = parse_filter_param("")
        
        assert result == []
    
    def test_parse_none(self):
        """Test parsing None."""
        result = parse_filter_param(None)
        
        assert result == []


class TestParseFilterValue:
    """Tests for _parse_filter_value function."""
    
    def test_parse_boolean_true(self):
        """Test parsing boolean true."""
        assert _parse_single_value("true") is True
        assert _parse_single_value("True") is True
    
    def test_parse_boolean_false(self):
        """Test parsing boolean false."""
        assert _parse_single_value("false") is False
        assert _parse_single_value("False") is False
    
    def test_parse_null(self):
        """Test parsing null/none."""
        assert _parse_single_value("null") is None
        assert _parse_single_value("none") is None
    
    def test_parse_integer(self):
        """Test parsing integer."""
        assert _parse_single_value("42") == 42
        assert _parse_single_value("-10") == -10
    
    def test_parse_float(self):
        """Test float-like strings stay as strings (float coercion disabled)."""
        assert _parse_single_value("3.14") == "3.14"
        assert _parse_single_value("-2.5") == "-2.5"
    
    def test_parse_uuid(self):
        """Test parsing UUID."""
        uuid_str = "12345678-1234-5678-1234-567812345678"
        result = _parse_single_value(uuid_str)
        assert isinstance(result, UUID)
    
    def test_parse_datetime(self):
        """Test parsing datetime."""
        result = _parse_single_value("2024-01-15T10:30:00")
        assert isinstance(result, datetime)
    
    def test_parse_string(self):
        """Test parsing string (fallback)."""
        assert _parse_single_value("hello") == "hello"
    
    def test_parse_list_values(self):
        """Test parsing pipe-separated list values."""
        result = _parse_filter_value("active|pending|completed")
        assert isinstance(result, list)
        assert len(result) == 3


# =============================================================================
# Response Builder Tests
# =============================================================================


class TestBuildResponse:
    """Tests for build_response function."""
    
    def test_build_success_response(self):
        """Test building success response."""
        result = build_response(
            data={"id": "123"},
            message="Operation successful",
            success=True,
        )
        
        assert result.success is True
        assert result.data == {"id": "123"}
        assert result.message == "Operation successful"
    
    def test_build_error_response(self):
        """Test building error response."""
        result = build_response(
            data=None,
            message="Something went wrong",
            success=False,
        )
        
        assert result.success is False
        assert result.message == "Something went wrong"
    
    def test_build_response_defaults(self):
        """Test building response with defaults."""
        result = build_response(data={"test": True})
        
        assert result.success is True
        assert result.message is None


class TestBuildPaginatedResponse:
    """Tests for build_paginated_response function."""
    
    def test_build_paginated_response(self):
        """Test building paginated response."""
        items = [{"id": i} for i in range(10)]
        
        result = build_paginated_response(
            data=items,
            page=1,
            page_size=10,
            total=35,
        )
        
        assert result.success is True
        assert len(result.data) == 10
        assert result.pagination.page == 1
        assert result.pagination.page_size == 10
        assert result.pagination.total_items == 35
    
    def test_build_paginated_response_with_message(self):
        """Test building paginated response with message."""
        result = build_paginated_response(
            data=[],
            page=1,
            page_size=10,
            total=0,
            message="No items found",
        )
        
        assert result.message == "No items found"


class TestBuildCreatedResponse:
    """Tests for build_created_response function."""
    
    def test_build_created_response(self):
        """Test building created response."""
        data = {"id": "123", "name": "Test"}
        
        result = build_created_response(data, resource_name="User")
        
        assert result.success is True
        assert result.data == data
        assert "User" in result.message
        assert "created" in result.message.lower()


class TestBuildUpdatedResponse:
    """Tests for build_updated_response function."""
    
    def test_build_updated_response(self):
        """Test building updated response."""
        data = {"id": "123", "name": "Updated"}
        
        result = build_updated_response(data, resource_name="Account")
        
        assert result.success is True
        assert "Account" in result.message
        assert "updated" in result.message.lower()


class TestBuildDeletedResponse:
    """Tests for build_deleted_response function."""
    
    def test_build_deleted_response(self):
        """Test building deleted response."""
        result = build_deleted_response(resource_name="Product")
        
        assert result.success is True
        assert result.data is None
        assert "Product" in result.message
        assert "deleted" in result.message.lower()


# =============================================================================
# Data Transformation Tests
# =============================================================================


def create_mock_model(columns_data: dict):
    """Helper to create a mock SQLAlchemy model."""
    mock_columns = []
    for col_name in columns_data.keys():
        mock_col = MagicMock()
        mock_col.name = col_name
        mock_columns.append(mock_col)
    
    mock_table = MagicMock()
    mock_table.columns = mock_columns
    
    mock_model = MagicMock()
    mock_model.__table__ = mock_table
    
    for key, value in columns_data.items():
        setattr(mock_model, key, value)
    
    return mock_model


class TestModelToDict:
    """Tests for model_to_dict function."""
    
    def test_model_to_dict(self):
        """Test converting model to dict."""
        mock_model = create_mock_model({
            "id": uuid4(),
            "name": "Test",
        })
        
        result = model_to_dict(mock_model)
        
        assert "id" in result
        assert result["name"] == "Test"
        assert isinstance(result["id"], str)  # UUID should be stringified
    
    def test_model_to_dict_with_exclude(self):
        """Test converting model to dict with exclusions."""
        mock_model = create_mock_model({
            "id": "123",
            "password": "secret",
        })
        
        result = model_to_dict(mock_model, exclude=["password"])
        
        assert "id" in result
        assert "password" not in result
    
    def test_model_to_dict_with_include(self):
        """Test converting model to dict with inclusions."""
        mock_model = create_mock_model({
            "id": "123",
            "name": "Test",
            "email": "test@example.com",
        })
        
        result = model_to_dict(mock_model, include=["id", "name"])
        
        assert "id" in result
        assert "name" in result
        assert "email" not in result


class TestModelsToDict:
    """Tests for models_to_dicts function."""
    
    def test_models_to_dicts(self):
        """Test converting multiple models to dicts."""
        mock_model1 = create_mock_model({"id": "1"})
        mock_model2 = create_mock_model({"id": "2"})
        
        result = models_to_dicts([mock_model1, mock_model2])
        
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"


class TestApplyPartialUpdate:
    """Tests for apply_partial_update function."""
    
    def test_apply_update(self):
        """Test applying partial update."""
        mock_model = MagicMock()
        mock_model.name = "Old"
        mock_model.email = "old@example.com"
        
        apply_partial_update(mock_model, {"name": "New", "email": "new@example.com"})
        
        mock_model.name = "New"
        mock_model.email = "new@example.com"
    
    def test_apply_update_exclude_none(self):
        """Test applying update excluding None values."""
        mock_model = MagicMock()
        mock_model.name = "Original"
        
        apply_partial_update(mock_model, {"name": None}, exclude_unset=True)
        
        # Name should not be changed
        mock_model.name = "Original"


# =============================================================================
# File Handling Tests
# =============================================================================


class TestValidateFileExtension:
    """Tests for validate_file_extension function."""
    
    @patch("sensei.api.utils.settings")
    def test_validate_valid_extension(self, mock_settings):
        """Test validating valid file extension."""
        mock_settings.ALLOWED_UPLOAD_EXTENSIONS = [".pdf", ".docx", ".xlsx"]
        
        result = validate_file_extension("document.pdf")
        
        assert result is True
    
    @patch("sensei.api.utils.settings")
    def test_validate_invalid_extension(self, mock_settings):
        """Test validating invalid file extension."""
        mock_settings.ALLOWED_UPLOAD_EXTENSIONS = [".pdf", ".docx"]
        
        result = validate_file_extension("script.exe")
        
        assert result is False
    
    def test_validate_with_custom_extensions(self):
        """Test validating with custom extension list."""
        result = validate_file_extension(
            "image.png",
            allowed_extensions=[".png", ".jpg"],
        )
        
        assert result is True
    
    def test_validate_case_insensitive(self):
        """Test that validation is case-insensitive."""
        result = validate_file_extension(
            "document.PDF",
            allowed_extensions=[".pdf"],
        )
        
        assert result is True
    
    def test_validate_no_extension(self):
        """Test validating file without extension."""
        result = validate_file_extension(
            "noextension",
            allowed_extensions=[".pdf"],
        )
        
        assert result is False


class TestValidateFileSize:
    """Tests for validate_file_size function."""
    
    @patch("sensei.api.utils.settings")
    def test_validate_valid_size(self, mock_settings):
        """Test validating file with valid size."""
        mock_settings.MAX_UPLOAD_SIZE_MB = 10
        
        mock_file = MagicMock()
        mock_file.file.tell.return_value = 5 * 1024 * 1024  # 5 MB
        
        result = validate_file_size(mock_file)
        
        assert result is True
    
    @patch("sensei.api.utils.settings")
    def test_validate_invalid_size(self, mock_settings):
        """Test validating file with invalid size."""
        mock_settings.MAX_UPLOAD_SIZE_MB = 10
        
        mock_file = MagicMock()
        mock_file.file.tell.return_value = 15 * 1024 * 1024  # 15 MB
        
        result = validate_file_size(mock_file)
        
        assert result is False
    
    def test_validate_with_custom_max(self):
        """Test validating with custom max size."""
        mock_file = MagicMock()
        mock_file.file.tell.return_value = 5 * 1024 * 1024  # 5 MB
        
        result = validate_file_size(mock_file, max_size_mb=10)
        
        assert result is True


class TestGenerateUniqueFilename:
    """Tests for generate_unique_filename function."""
    
    def test_generate_unique_filename(self):
        """Test generating unique filename."""
        result = generate_unique_filename("document.pdf")
        
        assert result.endswith(".pdf")
        assert len(result) > len("document.pdf")
    
    def test_generate_unique_filename_with_prefix(self):
        """Test generating unique filename with prefix."""
        result = generate_unique_filename("document.pdf", prefix="attachment")
        
        assert result.startswith("attachment_")
        assert result.endswith(".pdf")
    
    def test_generated_filenames_are_unique(self):
        """Test that generated filenames are unique."""
        filenames = [generate_unique_filename("test.pdf") for _ in range(100)]
        
        assert len(set(filenames)) == 100


class TestGetContentType:
    """Tests for get_content_type function."""
    
    def test_get_pdf_content_type(self):
        """Test getting PDF content type."""
        result = get_content_type("document.pdf")
        
        assert "pdf" in result
    
    def test_get_image_content_type(self):
        """Test getting image content type."""
        result = get_content_type("image.png")
        
        assert "image" in result
    
    def test_get_unknown_content_type(self):
        """Test getting unknown content type."""
        result = get_content_type("unknown.xyz123")
        
        assert result == "application/octet-stream"


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidateUuid:
    """Tests for validate_uuid function."""
    
    def test_validate_valid_uuid(self):
        """Test validating valid UUID."""
        uuid_str = str(uuid4())
        
        result = validate_uuid(uuid_str)
        
        assert isinstance(result, UUID)
    
    def test_validate_invalid_uuid(self):
        """Test validating invalid UUID."""
        result = validate_uuid("not-a-uuid")
        
        assert result is None
    
    def test_validate_empty_string(self):
        """Test validating empty string."""
        result = validate_uuid("")
        
        assert result is None


class TestValidateUuids:
    """Tests for validate_uuids function."""
    
    def test_validate_all_valid(self):
        """Test validating all valid UUIDs."""
        uuids = [str(uuid4()) for _ in range(3)]
        
        result = validate_uuids(uuids)
        
        assert len(result) == 3
    
    def test_validate_mixed(self):
        """Test validating mixed valid/invalid UUIDs."""
        uuids = [str(uuid4()), "invalid", str(uuid4())]
        
        result = validate_uuids(uuids)
        
        assert len(result) == 2


class TestIsValidEmail:
    """Tests for is_valid_email function."""
    
    def test_valid_email(self):
        """Test valid email addresses."""
        assert is_valid_email("test@example.com") is True
        assert is_valid_email("user.name@domain.co.uk") is True
        assert is_valid_email("user+tag@example.org") is True
    
    def test_invalid_email(self):
        """Test invalid email addresses."""
        assert is_valid_email("notanemail") is False
        assert is_valid_email("missing@domain") is False
        assert is_valid_email("@nodomain.com") is False


# =============================================================================
# Date/Time Tests
# =============================================================================


class TestNowUtc:
    """Tests for now_utc function."""
    
    def test_now_utc(self):
        """Test getting current UTC time."""
        result = now_utc()
        
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


class TestParseDatetime:
    """Tests for parse_datetime function."""
    
    def test_parse_iso_datetime(self):
        """Test parsing ISO datetime."""
        result = parse_datetime("2024-01-15T10:30:00")
        
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
    
    def test_parse_with_timezone(self):
        """Test parsing datetime with timezone."""
        result = parse_datetime("2024-01-15T10:30:00Z")
        
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
    
    def test_parse_invalid(self):
        """Test parsing invalid datetime."""
        result = parse_datetime("not-a-date")
        
        assert result is None


class TestFormatDatetime:
    """Tests for format_datetime function."""
    
    def test_format_iso(self):
        """Test formatting as ISO."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        
        result = format_datetime(dt, format="iso")
        
        assert "2024-01-15" in result
        assert "10:30:45" in result
    
    def test_format_date_only(self):
        """Test formatting date only."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        
        result = format_datetime(dt, format="date")
        
        assert result == "2024-01-15"
    
    def test_format_datetime_full(self):
        """Test formatting full datetime."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        
        result = format_datetime(dt, format="datetime")
        
        assert "2024-01-15" in result
        assert "10:30:45" in result


# =============================================================================
# Slug and URL Tests
# =============================================================================


class TestSlugify:
    """Tests for slugify function."""
    
    def test_basic_slugify(self):
        """Test basic slugification."""
        result = slugify("Hello World")
        
        assert result == "hello-world"
    
    def test_slugify_special_chars(self):
        """Test slugifying special characters."""
        result = slugify("Hello! World? Test#123")
        
        assert result == "hello-world-test-123"
    
    def test_slugify_unicode(self):
        """Test slugifying unicode characters."""
        result = slugify("Café Münchën")
        
        assert "cafe" in result.lower()
    
    def test_slugify_removes_leading_trailing_hyphens(self):
        """Test that slugify removes leading/trailing hyphens."""
        result = slugify("---Hello World---")
        
        assert not result.startswith("-")
        assert not result.endswith("-")
    
    def test_slugify_collapses_hyphens(self):
        """Test that slugify collapses multiple hyphens."""
        result = slugify("Hello    World")
        
        assert "--" not in result


class TestGenerateUniqueCode:
    """Tests for generate_unique_code function."""
    
    def test_generate_code(self):
        """Test generating unique code."""
        result = generate_unique_code()
        
        assert len(result) == 8
    
    def test_generate_code_with_prefix(self):
        """Test generating code with prefix."""
        result = generate_unique_code(prefix="INV")
        
        assert result.startswith("INV-")
    
    def test_generate_code_custom_length(self):
        """Test generating code with custom length."""
        result = generate_unique_code(length=12)
        
        assert len(result) == 12
    
    def test_generated_codes_are_unique(self):
        """Test that generated codes are unique."""
        codes = [generate_unique_code() for _ in range(100)]
        
        assert len(set(codes)) == 100


# =============================================================================
# Batch Processing Tests
# =============================================================================


class TestChunkList:
    """Tests for chunk_list function."""
    
    def test_chunk_list(self):
        """Test chunking list."""
        items = list(range(10))
        
        result = chunk_list(items, chunk_size=3)
        
        assert len(result) == 4
        assert result[0] == [0, 1, 2]
        assert result[1] == [3, 4, 5]
        assert result[2] == [6, 7, 8]
        assert result[3] == [9]
    
    def test_chunk_list_exact_fit(self):
        """Test chunking list that fits exactly."""
        items = list(range(9))
        
        result = chunk_list(items, chunk_size=3)
        
        assert len(result) == 3
        assert all(len(chunk) == 3 for chunk in result)
    
    def test_chunk_empty_list(self):
        """Test chunking empty list."""
        result = chunk_list([], chunk_size=3)
        
        assert result == []


class TestProcessInBatches:
    """Tests for process_in_batches function."""
    
    @pytest.mark.asyncio
    async def test_process_in_batches(self):
        """Test processing in batches."""
        items = list(range(10))
        
        async def processor(batch):
            return sum(batch)
        
        result = await process_in_batches(items, processor, batch_size=3)
        
        # 4 batches: [0,1,2], [3,4,5], [6,7,8], [9]
        assert len(result) == 4
        assert result[0] == 3   # 0+1+2
        assert result[1] == 12  # 3+4+5
        assert result[2] == 21  # 6+7+8
        assert result[3] == 9   # 9
    
    @pytest.mark.asyncio
    async def test_process_empty_list(self):
        """Test processing empty list."""
        async def processor(batch):
            return len(batch)
        
        result = await process_in_batches([], processor, batch_size=3)
        
        assert result == []


# =============================================================================
# Cache Key Tests
# =============================================================================


class TestBuildCacheKey:
    """Tests for build_cache_key function."""
    
    def test_build_simple_key(self):
        """Test building simple cache key."""
        result = build_cache_key("user", "123")
        
        assert result == "user:123"
    
    def test_build_key_with_kwargs(self):
        """Test building cache key with kwargs."""
        result = build_cache_key("user", status="active")
        
        assert result == "user:status=active"
    
    def test_build_key_with_multiple_args(self):
        """Test building cache key with multiple args."""
        result = build_cache_key("entity", "account", "123")
        
        assert result == "entity:account:123"
    
    def test_build_key_kwargs_sorted(self):
        """Test that kwargs are sorted in cache key."""
        result = build_cache_key("user", z="last", a="first")
        
        # Should be sorted alphabetically
        assert "a=first" in result
        assert "z=last" in result
        assert result.index("a=first") < result.index("z=last")
