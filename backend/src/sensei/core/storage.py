"""
Sensei OS Storage Module

S3-compatible object storage for file attachments and exports.
"""

from io import BytesIO
from typing import Optional, BinaryIO
from datetime import datetime, timedelta, timezone
import hashlib

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import structlog

from sensei.core.config import settings

logger = structlog.get_logger(__name__)


def create_storage_client():
    """Create and configure the S3 client."""
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
        ),
    )


storage_client = create_storage_client()


async def check_storage_connection(client) -> bool:
    """Check if the storage connection is healthy."""
    try:
        def _do_check():
            client.head_bucket(Bucket=settings.S3_BUCKET)
        
        await anyio.to_thread.run_sync(_do_check)
        return True
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            # Bucket doesn't exist, try to create it
            try:
                def _do_create():
                    client.create_bucket(Bucket=settings.S3_BUCKET)
                
                await anyio.to_thread.run_sync(_do_create)
                logger.info("Created storage bucket", bucket=settings.S3_BUCKET)
                return True
            except Exception as create_error:
                logger.error("Failed to create bucket", error=str(create_error))
                return False
        logger.error("Storage connection error", error=str(e))
        return False
    except Exception as e:
        logger.error("Storage connection error", error=str(e))
        return False


def generate_file_key(
    entity_type: str,
    entity_id: str,
    filename: str,
    version: Optional[int] = None
) -> str:
    """Generate a unique storage key for a file."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    version_suffix = f"_v{version}" if version else ""
    safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-")
    return f"{entity_type}/{entity_id}/{timestamp}{version_suffix}_{safe_filename}"


def compute_file_hash(file_content: bytes) -> str:
    """Compute SHA-256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


async def upload_file(
    file_content: bytes,
    key: str,
    content_type: str = "application/octet-stream",
    metadata: Optional[dict] = None
) -> dict:
    """
    Upload a file to S3 storage.
    
    Returns:
        Dictionary with key, size, hash, and url.
    """
    file_hash = compute_file_hash(file_content)
    file_size = len(file_content)
    
    upload_metadata = {
        "sha256": file_hash,
        "uploaded_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    }
    if metadata:
        upload_metadata.update(metadata)
    
    def _do_upload():
        storage_client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=BytesIO(file_content),
            ContentType=content_type,
            Metadata=upload_metadata,
        )
    
    await anyio.to_thread.run_sync(_do_upload)
    
    logger.info(
        "File uploaded",
        key=key,
        size=file_size,
        content_type=content_type,
    )
    
    return {
        "key": key,
        "size": file_size,
        "hash": file_hash,
        "content_type": content_type,
    }


async def download_file(key: str) -> Optional[bytes]:
    """Download a file from S3 storage."""
    try:
        def _do_download():
            response = storage_client.get_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
            )
            return response["Body"].read()
        
        return await anyio.to_thread.run_sync(_do_download)
    except ClientError as e:
        logger.error("File download failed", key=key, error=str(e))
        return None


async def delete_file(key: str) -> bool:
    """Delete a file from S3 storage."""
    try:
        def _do_delete():
            storage_client.delete_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
            )
        
        await anyio.to_thread.run_sync(_do_delete)
        logger.info("File deleted", key=key)
        return True
    except ClientError as e:
        logger.error("File deletion failed", key=key, error=str(e))
        return False


def generate_presigned_url(
    key: str,
    expiration_seconds: int = 3600,
    response_content_type: Optional[str] = None
) -> Optional[str]:
    """Generate a presigned URL for temporary file access."""
    try:
        params = {
            "Bucket": settings.S3_BUCKET,
            "Key": key,
        }
        if response_content_type:
            params["ResponseContentType"] = response_content_type
        
        url = storage_client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expiration_seconds,
        )
        return url
    except ClientError as e:
        logger.error("Presigned URL generation failed", key=key, error=str(e))
        return None


async def list_files(prefix: str, max_keys: int = 1000) -> list:
    """List files with a given prefix."""
    try:
        def _do_list():
            response = storage_client.list_objects_v2(
                Bucket=settings.S3_BUCKET,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            return response.get("Contents", [])
        
        return await anyio.to_thread.run_sync(_do_list)
    except ClientError as e:
        logger.error("File listing failed", prefix=prefix, error=str(e))
        return []
