"""
Tests for Sensei Core Storage Module

Comprehensive tests for S3-compatible storage operations with edge cases.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

from sensei.core.storage import (
    generate_file_key,
    compute_file_hash,
    upload_file,
    download_file,
    delete_file,
    generate_presigned_url,
    list_files,
    check_storage_connection,
)


class TestGenerateFileKey:
    """Tests for file key generation."""
    
    def test_basic_key_generation(self):
        """Test basic file key generation."""
        key = generate_file_key("rfq", "123", "document.pdf")
        assert key.startswith("rfq/123/")
        assert "document.pdf" in key
    
    def test_key_with_version(self):
        """Test file key with version number."""
        key = generate_file_key("quote", "456", "specs.pdf", version=2)
        assert "_v2_" in key
        assert key.startswith("quote/456/")
    
    def test_key_sanitizes_filename(self):
        """Test that filenames are sanitized."""
        key = generate_file_key("attachment", "789", "file with spaces!@#.pdf")
        # Should remove special characters except . _ -
        assert "!" not in key
        assert "@" not in key
        assert "#" not in key
    
    def test_key_preserves_extension(self):
        """Test that file extension is preserved."""
        key = generate_file_key("doc", "1", "report.xlsx")
        assert key.endswith(".xlsx")
    
    def test_key_with_empty_filename(self):
        """Test key generation with empty filename."""
        key = generate_file_key("test", "1", "")
        assert key.startswith("test/1/")
    
    def test_key_with_unicode_filename(self):
        """Test key generation with unicode characters."""
        key = generate_file_key("test", "1", "fichier_été.pdf")
        # Unicode letters should be kept as alphanumeric
        assert "fichier" in key


class TestComputeFileHash:
    """Tests for file hash computation."""
    
    def test_hash_basic_content(self):
        """Test hashing basic content."""
        content = b"Hello, World!"
        hash_result = compute_file_hash(content)
        assert len(hash_result) == 64  # SHA-256 hex length
        assert hash_result.isalnum()
    
    def test_hash_empty_content(self):
        """Test hashing empty content."""
        content = b""
        hash_result = compute_file_hash(content)
        # SHA-256 of empty string
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert hash_result == expected
    
    def test_hash_consistency(self):
        """Test that same content produces same hash."""
        content = b"Test content"
        hash1 = compute_file_hash(content)
        hash2 = compute_file_hash(content)
        assert hash1 == hash2
    
    def test_hash_different_content(self):
        """Test that different content produces different hashes."""
        hash1 = compute_file_hash(b"Content A")
        hash2 = compute_file_hash(b"Content B")
        assert hash1 != hash2
    
    def test_hash_large_content(self):
        """Test hashing large content."""
        content = b"x" * 10_000_000  # 10MB
        hash_result = compute_file_hash(content)
        assert len(hash_result) == 64


class TestUploadFile:
    """Tests for file upload functionality."""
    
    @patch("sensei.core.storage.storage_client")
    def test_upload_success(self, mock_client):
        """Test successful file upload."""
        mock_client.put_object.return_value = {}
        
        result = upload_file(
            file_content=b"Test content",
            key="test/file.txt",
            content_type="text/plain",
        )
        
        assert result["key"] == "test/file.txt"
        assert result["size"] == 12
        assert result["content_type"] == "text/plain"
        assert "hash" in result
        mock_client.put_object.assert_called_once()
    
    @patch("sensei.core.storage.storage_client")
    def test_upload_with_metadata(self, mock_client):
        """Test upload with custom metadata."""
        mock_client.put_object.return_value = {}
        
        result = upload_file(
            file_content=b"Data",
            key="test/data.bin",
            metadata={"author": "test_user", "version": "1"},
        )
        
        call_args = mock_client.put_object.call_args
        assert "author" in call_args.kwargs["Metadata"]
        assert "version" in call_args.kwargs["Metadata"]
    
    @patch("sensei.core.storage.storage_client")
    def test_upload_empty_file(self, mock_client):
        """Test uploading empty file."""
        mock_client.put_object.return_value = {}
        
        result = upload_file(
            file_content=b"",
            key="test/empty.txt",
        )
        
        assert result["size"] == 0


class TestDownloadFile:
    """Tests for file download functionality."""
    
    @patch("sensei.core.storage.storage_client")
    def test_download_success(self, mock_client):
        """Test successful file download."""
        mock_response = {"Body": MagicMock()}
        mock_response["Body"].read.return_value = b"File content"
        mock_client.get_object.return_value = mock_response
        
        result = download_file("test/file.txt")
        
        assert result == b"File content"
        mock_client.get_object.assert_called_once()
    
    @patch("sensei.core.storage.storage_client")
    def test_download_not_found(self, mock_client):
        """Test download of non-existent file."""
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}},
            "GetObject"
        )
        
        result = download_file("nonexistent/file.txt")
        
        assert result is None
    
    @patch("sensei.core.storage.storage_client")
    def test_download_access_denied(self, mock_client):
        """Test download with access denied."""
        mock_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}},
            "GetObject"
        )
        
        result = download_file("restricted/file.txt")
        
        assert result is None


class TestDeleteFile:
    """Tests for file deletion functionality."""
    
    @patch("sensei.core.storage.storage_client")
    def test_delete_success(self, mock_client):
        """Test successful file deletion."""
        mock_client.delete_object.return_value = {}
        
        result = delete_file("test/file.txt")
        
        assert result is True
        mock_client.delete_object.assert_called_once()
    
    @patch("sensei.core.storage.storage_client")
    def test_delete_failure(self, mock_client):
        """Test failed file deletion."""
        mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "InternalError"}},
            "DeleteObject"
        )
        
        result = delete_file("test/file.txt")
        
        assert result is False


class TestGeneratePresignedUrl:
    """Tests for presigned URL generation."""
    
    @patch("sensei.core.storage.storage_client")
    def test_presigned_url_success(self, mock_client):
        """Test successful presigned URL generation."""
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/file?signature=abc"
        
        result = generate_presigned_url("test/file.pdf")
        
        assert result is not None
        assert result.startswith("https://")
    
    @patch("sensei.core.storage.storage_client")
    def test_presigned_url_with_content_type(self, mock_client):
        """Test presigned URL with custom content type."""
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/file"
        
        result = generate_presigned_url(
            "test/file.pdf",
            response_content_type="application/pdf"
        )
        
        call_args = mock_client.generate_presigned_url.call_args
        assert call_args.kwargs["Params"]["ResponseContentType"] == "application/pdf"
    
    @patch("sensei.core.storage.storage_client")
    def test_presigned_url_custom_expiration(self, mock_client):
        """Test presigned URL with custom expiration."""
        mock_client.generate_presigned_url.return_value = "https://s3.example.com/file"
        
        result = generate_presigned_url("test/file.pdf", expiration_seconds=600)
        
        call_args = mock_client.generate_presigned_url.call_args
        assert call_args.kwargs["ExpiresIn"] == 600
    
    @patch("sensei.core.storage.storage_client")
    def test_presigned_url_failure(self, mock_client):
        """Test presigned URL generation failure."""
        mock_client.generate_presigned_url.side_effect = ClientError(
            {"Error": {"Code": "InternalError"}},
            "GeneratePresignedUrl"
        )
        
        result = generate_presigned_url("test/file.pdf")
        
        assert result is None


class TestListFiles:
    """Tests for file listing functionality."""
    
    @patch("sensei.core.storage.storage_client")
    def test_list_files_success(self, mock_client):
        """Test successful file listing."""
        mock_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "test/file1.txt"},
                {"Key": "test/file2.txt"},
            ]
        }
        
        result = list_files("test/")
        
        assert len(result) == 2
        assert result[0]["Key"] == "test/file1.txt"
    
    @patch("sensei.core.storage.storage_client")
    def test_list_files_empty(self, mock_client):
        """Test listing with no files."""
        mock_client.list_objects_v2.return_value = {}
        
        result = list_files("empty/")
        
        assert result == []
    
    @patch("sensei.core.storage.storage_client")
    def test_list_files_with_max_keys(self, mock_client):
        """Test listing with max keys limit."""
        mock_client.list_objects_v2.return_value = {"Contents": []}
        
        list_files("test/", max_keys=50)
        
        call_args = mock_client.list_objects_v2.call_args
        assert call_args.kwargs["MaxKeys"] == 50


class TestCheckStorageConnection:
    """Tests for storage connection checking."""
    
    @pytest.mark.asyncio
    @patch("sensei.core.storage.settings")
    async def test_connection_healthy(self, mock_settings):
        """Test healthy storage connection."""
        mock_settings.S3_BUCKET = "test-bucket"
        mock_client = Mock()
        mock_client.head_bucket.return_value = {}
        
        result = await check_storage_connection(mock_client)
        
        assert result is True
    
    @pytest.mark.asyncio
    @patch("sensei.core.storage.settings")
    async def test_connection_bucket_not_found_creates(self, mock_settings):
        """Test bucket creation when not found."""
        mock_settings.S3_BUCKET = "test-bucket"
        mock_client = Mock()
        mock_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404"}},
            "HeadBucket"
        )
        mock_client.create_bucket.return_value = {}
        
        result = await check_storage_connection(mock_client)
        
        assert result is True
        mock_client.create_bucket.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("sensei.core.storage.settings")
    async def test_connection_failure(self, mock_settings):
        """Test storage connection failure."""
        mock_settings.S3_BUCKET = "test-bucket"
        mock_client = Mock()
        mock_client.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "500"}},
            "HeadBucket"
        )
        
        result = await check_storage_connection(mock_client)
        
        assert result is False
