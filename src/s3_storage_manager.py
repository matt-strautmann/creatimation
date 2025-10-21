#!/usr/bin/env python3
"""
S3 Storage Manager - Production-ready S3 integration for Cache Manager

Provides cloud storage capabilities with semantic metadata preservation,
batch upload optimization, and robust error handling.

Features:
- S3 client with automatic retry and exponential backoff
- Semantic folder structure generation in S3
- Metadata tagging using S3 object tags and metadata
- Batch upload with parallel processing and progress tracking
- Asset discovery and retrieval with semantic filtering
- CDN invalidation hooks for CloudFront integration
- S3 lifecycle policy management
- Comprehensive error handling and logging
"""
import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import quote

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:
    raise ImportError(
        "boto3 is required for S3 storage. Install with: pip install boto3"
    )

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================


@dataclass
class S3Config:
    """S3 storage configuration"""

    bucket_name: str
    region: str = "us-east-1"
    prefix: str = "creative-assets"
    cloudfront_distribution_id: Optional[str] = None
    storage_class: str = "STANDARD"
    enable_encryption: bool = True
    enable_versioning: bool = True
    max_parallel_uploads: int = 10
    upload_timeout: int = 300
    retry_attempts: int = 3
    retry_backoff: float = 2.0

    @classmethod
    def from_env(cls, prefix: str = "creative-assets") -> "S3Config":
        """Create configuration from environment variables"""
        bucket_name = os.getenv("S3_BUCKET_NAME")
        if not bucket_name:
            raise ValueError(
                "S3_BUCKET_NAME environment variable is required. "
                "Set it in your .env file."
            )

        return cls(
            bucket_name=bucket_name,
            region=os.getenv("S3_REGION", "us-east-1"),
            prefix=prefix,
            cloudfront_distribution_id=os.getenv("CLOUDFRONT_DISTRIBUTION_ID"),
            storage_class=os.getenv("S3_STORAGE_CLASS", "STANDARD"),
            enable_encryption=os.getenv("S3_ENABLE_ENCRYPTION", "true").lower()
            == "true",
            enable_versioning=os.getenv("S3_ENABLE_VERSIONING", "true").lower()
            == "true",
            max_parallel_uploads=int(os.getenv("S3_MAX_PARALLEL_UPLOADS", "10")),
        )


# ============================================================================
# S3 SEMANTIC FOLDER STRUCTURE
# ============================================================================


class S3FolderStructure:
    """
    Semantic folder structure for S3 organization.

    Structure:
    {prefix}/
      ├── products/
      │   ├── transparent/{category}/{product-slug}/
      │   └── original/{category}/{product-slug}/
      ├── backgrounds/
      │   ├── scene/{region}/{season}/{style}/
      │   ├── gradient/{style}/
      │   └── solid/{color}/
      ├── composites/
      │   └── {campaign-id}/{product-slug}/{aspect-ratio}/
      └── metadata/
          └── index.json
    """

    def __init__(self, prefix: str = "creative-assets"):
        self.prefix = prefix.rstrip("/")

    def get_product_path(
        self,
        product_slug: str,
        category: str = "general",
        asset_type: str = "transparent",
        filename: str = None,
    ) -> str:
        """Generate S3 path for product asset"""
        path = f"{self.prefix}/products/{asset_type}/{category}/{product_slug}"
        if filename:
            path = f"{path}/{filename}"
        return path

    def get_background_path(
        self,
        style: str,
        region: Optional[str] = None,
        season: Optional[str] = None,
        filename: str = None,
    ) -> str:
        """Generate S3 path for background asset"""
        if style == "scene" and region and season:
            path = f"{self.prefix}/backgrounds/scene/{region}/{season}"
        elif style == "gradient":
            path = f"{self.prefix}/backgrounds/gradient"
        elif style == "solid":
            path = f"{self.prefix}/backgrounds/solid"
        else:
            path = f"{self.prefix}/backgrounds/{style}"

        if filename:
            path = f"{path}/{filename}"
        return path

    def get_composite_path(
        self,
        campaign_id: str,
        product_slug: str,
        aspect_ratio: str,
        filename: str = None,
    ) -> str:
        """Generate S3 path for composite creative"""
        path = f"{self.prefix}/composites/{campaign_id}/{product_slug}/{aspect_ratio}"
        if filename:
            path = f"{path}/{filename}"
        return path

    def get_metadata_path(self) -> str:
        """Get path to centralized metadata index in S3"""
        return f"{self.prefix}/metadata/index.json"

    def parse_s3_key(self, s3_key: str) -> Dict[str, str]:
        """Parse S3 key to extract semantic components"""
        if not s3_key.startswith(self.prefix):
            return {}

        parts = s3_key[len(self.prefix) + 1 :].split("/")

        if parts[0] == "products" and len(parts) >= 4:
            return {
                "type": "product",
                "asset_type": parts[1],
                "category": parts[2],
                "product_slug": parts[3],
                "filename": parts[4] if len(parts) > 4 else None,
            }
        elif parts[0] == "backgrounds" and len(parts) >= 2:
            result = {"type": "background", "style": parts[1]}
            if parts[1] == "scene" and len(parts) >= 4:
                result["region"] = parts[2]
                result["season"] = parts[3]
            result["filename"] = parts[-1] if len(parts) > 2 else None
            return result
        elif parts[0] == "composites" and len(parts) >= 4:
            return {
                "type": "composite",
                "campaign_id": parts[1],
                "product_slug": parts[2],
                "aspect_ratio": parts[3],
                "filename": parts[4] if len(parts) > 4 else None,
            }

        return {}


# ============================================================================
# S3 STORAGE MANAGER
# ============================================================================


@dataclass
class UploadResult:
    """Result of an S3 upload operation"""

    s3_key: str
    local_path: str
    success: bool
    error: Optional[str] = None
    size_bytes: int = 0
    duration_seconds: float = 0.0
    etag: Optional[str] = None
    version_id: Optional[str] = None


@dataclass
class UploadProgress:
    """Track batch upload progress"""

    total_files: int
    uploaded: int = 0
    failed: int = 0
    skipped: int = 0
    total_bytes: int = 0
    uploaded_bytes: int = 0
    start_time: float = field(default_factory=time.time)

    @property
    def percent_complete(self) -> float:
        """Calculate completion percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.uploaded + self.failed + self.skipped) / self.total_files * 100

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return time.time() - self.start_time

    @property
    def upload_speed_mbps(self) -> float:
        """Calculate upload speed in MB/s"""
        if self.elapsed_time == 0:
            return 0.0
        return (self.uploaded_bytes / 1024 / 1024) / self.elapsed_time


class S3StorageManager:
    """
    Production-ready S3 storage manager with semantic asset organization.

    Features:
    - Automatic retry with exponential backoff
    - Parallel batch uploads with progress tracking
    - Semantic folder structure preservation
    - Metadata tagging and indexing
    - CloudFront cache invalidation
    - Lifecycle policy management
    """

    def __init__(self, config: S3Config):
        """
        Initialize S3 storage manager.

        Args:
            config: S3 configuration
        """
        self.config = config
        self.folder_structure = S3FolderStructure(config.prefix)

        # Configure boto3 with retry logic
        boto_config = Config(
            region_name=config.region,
            retries={
                "max_attempts": config.retry_attempts,
                "mode": "adaptive",
            },
            connect_timeout=30,
            read_timeout=config.upload_timeout,
        )

        self.s3_client = boto3.client("s3", config=boto_config)
        self.cloudfront_client = (
            boto3.client("cloudfront", config=boto_config)
            if config.cloudfront_distribution_id
            else None
        )

        # Verify bucket access
        self._verify_bucket_access()

        # Setup bucket configuration
        if config.enable_versioning:
            self._enable_versioning()
        if config.enable_encryption:
            self._enable_encryption()

        logger.info(
            f"S3StorageManager initialized for bucket: {config.bucket_name} "
            f"in region: {config.region}"
        )

    def _verify_bucket_access(self) -> None:
        """Verify S3 bucket exists and is accessible"""
        try:
            self.s3_client.head_bucket(Bucket=self.config.bucket_name)
            logger.debug(f"Verified access to bucket: {self.config.bucket_name}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "404":
                raise ValueError(
                    f"S3 bucket '{self.config.bucket_name}' does not exist"
                )
            elif error_code == "403":
                raise PermissionError(
                    f"Access denied to S3 bucket '{self.config.bucket_name}'"
                )
            else:
                raise RuntimeError(f"Failed to access S3 bucket: {e}")

    def _enable_versioning(self) -> None:
        """Enable versioning on S3 bucket"""
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=self.config.bucket_name,
                VersioningConfiguration={"Status": "Enabled"},
            )
            logger.debug("S3 bucket versioning enabled")
        except ClientError as e:
            logger.warning(f"Failed to enable versioning: {e}")

    def _enable_encryption(self) -> None:
        """Enable default encryption on S3 bucket"""
        try:
            self.s3_client.put_bucket_encryption(
                Bucket=self.config.bucket_name,
                ServerSideEncryptionConfiguration={
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": "AES256"
                            },
                            "BucketKeyEnabled": True,
                        }
                    ]
                },
            )
            logger.debug("S3 bucket encryption enabled")
        except ClientError as e:
            logger.warning(f"Failed to enable encryption: {e}")

    # ========================================================================
    # UPLOAD OPERATIONS
    # ========================================================================

    def upload_file(
        self,
        local_path: Path,
        s3_key: str,
        metadata: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
    ) -> UploadResult:
        """
        Upload a single file to S3 with metadata and tags.

        Args:
            local_path: Local file path
            s3_key: Target S3 key
            metadata: S3 object metadata (max 2KB)
            tags: S3 object tags for filtering/lifecycle
            content_type: Content-Type header (auto-detected if None)

        Returns:
            UploadResult with upload details
        """
        start_time = time.time()

        try:
            if not local_path.exists():
                return UploadResult(
                    s3_key=s3_key,
                    local_path=str(local_path),
                    success=False,
                    error=f"File not found: {local_path}",
                )

            file_size = local_path.stat().st_size

            # Auto-detect content type if not provided
            if content_type is None:
                content_type = self._guess_content_type(local_path)

            # Prepare upload arguments
            extra_args = {
                "ContentType": content_type,
                "StorageClass": self.config.storage_class,
            }

            if metadata:
                # S3 metadata keys must be lowercase and alphanumeric
                clean_metadata = {
                    k.lower().replace("-", "").replace("_", ""): str(v)[:1024]
                    for k, v in metadata.items()
                }
                extra_args["Metadata"] = clean_metadata

            if tags:
                # S3 tags as URL-encoded string
                tag_string = "&".join(
                    f"{quote(k)}={quote(str(v))}" for k, v in tags.items()
                )
                extra_args["Tagging"] = tag_string

            # Upload file
            self.s3_client.upload_file(
                str(local_path), self.config.bucket_name, s3_key, ExtraArgs=extra_args
            )

            # Get object metadata for ETag and VersionId
            response = self.s3_client.head_object(
                Bucket=self.config.bucket_name, Key=s3_key
            )

            duration = time.time() - start_time

            logger.debug(
                f"Uploaded {local_path.name} to s3://{self.config.bucket_name}/{s3_key} "
                f"({file_size / 1024:.1f} KB in {duration:.2f}s)"
            )

            return UploadResult(
                s3_key=s3_key,
                local_path=str(local_path),
                success=True,
                size_bytes=file_size,
                duration_seconds=duration,
                etag=response.get("ETag", "").strip('"'),
                version_id=response.get("VersionId"),
            )

        except (ClientError, BotoCoreError) as e:
            duration = time.time() - start_time
            error_msg = f"S3 upload failed: {e}"
            logger.error(error_msg)

            return UploadResult(
                s3_key=s3_key,
                local_path=str(local_path),
                success=False,
                error=error_msg,
                duration_seconds=duration,
            )

    def batch_upload(
        self,
        file_mappings: List[Tuple[Path, str, Optional[Dict[str, str]]]],
        progress_callback: Optional[Callable[[UploadProgress], None]] = None,
    ) -> Tuple[List[UploadResult], UploadProgress]:
        """
        Upload multiple files in parallel with progress tracking.

        Args:
            file_mappings: List of (local_path, s3_key, metadata) tuples
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (results list, final progress)
        """
        progress = UploadProgress(
            total_files=len(file_mappings),
            total_bytes=sum(
                p.stat().st_size for p, _, _ in file_mappings if p.exists()
            ),
        )

        results = []

        logger.info(
            f"Starting batch upload of {progress.total_files} files "
            f"({progress.total_bytes / 1024 / 1024:.1f} MB)"
        )

        # Parallel upload with ThreadPoolExecutor
        with ThreadPoolExecutor(
            max_workers=self.config.max_parallel_uploads
        ) as executor:
            # Submit all upload tasks
            future_to_mapping = {
                executor.submit(
                    self.upload_file,
                    local_path,
                    s3_key,
                    metadata,
                ): (local_path, s3_key)
                for local_path, s3_key, metadata in file_mappings
            }

            # Process completed uploads
            for future in as_completed(future_to_mapping):
                result = future.result()
                results.append(result)

                if result.success:
                    progress.uploaded += 1
                    progress.uploaded_bytes += result.size_bytes
                else:
                    progress.failed += 1

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(progress)

                # Log progress
                if progress.uploaded % 10 == 0 or progress.failed > 0:
                    logger.info(
                        f"Upload progress: {progress.uploaded}/{progress.total_files} files "
                        f"({progress.percent_complete:.1f}%), "
                        f"{progress.failed} failed, "
                        f"{progress.upload_speed_mbps:.2f} MB/s"
                    )

        # Final summary
        logger.info(
            f"Batch upload completed: {progress.uploaded} succeeded, "
            f"{progress.failed} failed, "
            f"{progress.uploaded_bytes / 1024 / 1024:.1f} MB in {progress.elapsed_time:.1f}s "
            f"({progress.upload_speed_mbps:.2f} MB/s)"
        )

        return results, progress

    def _guess_content_type(self, file_path: Path) -> str:
        """Guess content type from file extension"""
        extension_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".svg": "image/svg+xml",
            ".json": "application/json",
            ".txt": "text/plain",
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript",
        }

        ext = file_path.suffix.lower()
        return extension_map.get(ext, "application/octet-stream")

    # ========================================================================
    # DOWNLOAD OPERATIONS
    # ========================================================================

    def download_file(
        self, s3_key: str, local_path: Path, version_id: Optional[str] = None
    ) -> bool:
        """
        Download file from S3 to local path.

        Args:
            s3_key: S3 object key
            local_path: Target local path
            version_id: Optional specific version to download

        Returns:
            True if successful
        """
        try:
            # Ensure parent directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            extra_args = {}
            if version_id:
                extra_args["VersionId"] = version_id

            self.s3_client.download_file(
                self.config.bucket_name, s3_key, str(local_path), ExtraArgs=extra_args
            )

            logger.debug(f"Downloaded {s3_key} to {local_path}")
            return True

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to download {s3_key}: {e}")
            return False

    def get_file_metadata(
        self, s3_key: str, version_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get metadata for S3 object.

        Args:
            s3_key: S3 object key
            version_id: Optional specific version

        Returns:
            Dictionary with metadata or None if not found
        """
        try:
            params = {"Bucket": self.config.bucket_name, "Key": s3_key}
            if version_id:
                params["VersionId"] = version_id

            response = self.s3_client.head_object(**params)

            return {
                "s3_key": s3_key,
                "size_bytes": response["ContentLength"],
                "last_modified": response["LastModified"].isoformat(),
                "etag": response.get("ETag", "").strip('"'),
                "version_id": response.get("VersionId"),
                "content_type": response.get("ContentType"),
                "metadata": response.get("Metadata", {}),
                "storage_class": response.get("StorageClass", "STANDARD"),
            }

        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                logger.debug(f"Object not found: {s3_key}")
                return None
            logger.error(f"Failed to get metadata for {s3_key}: {e}")
            return None

    # ========================================================================
    # DISCOVERY & SEARCH
    # ========================================================================

    def list_objects(
        self,
        prefix: Optional[str] = None,
        max_keys: int = 1000,
        include_metadata: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        List objects in S3 with optional prefix filter.

        Args:
            prefix: Optional S3 key prefix filter
            max_keys: Maximum number of objects to return
            include_metadata: Whether to fetch full metadata for each object

        Returns:
            List of object information dictionaries
        """
        try:
            search_prefix = prefix or self.config.prefix
            objects = []

            paginator = self.s3_client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.config.bucket_name,
                Prefix=search_prefix,
                PaginationConfig={"MaxItems": max_keys},
            )

            for page in pages:
                for obj in page.get("Contents", []):
                    obj_info = {
                        "s3_key": obj["Key"],
                        "size_bytes": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                        "etag": obj.get("ETag", "").strip('"'),
                        "storage_class": obj.get("StorageClass", "STANDARD"),
                    }

                    # Parse semantic components from S3 key
                    obj_info["parsed"] = self.folder_structure.parse_s3_key(
                        obj["Key"]
                    )

                    if include_metadata:
                        metadata = self.get_file_metadata(obj["Key"])
                        if metadata:
                            obj_info.update(metadata)

                    objects.append(obj_info)

            logger.info(f"Listed {len(objects)} objects with prefix: {search_prefix}")
            return objects

        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to list objects: {e}")
            return []

    def find_assets_by_semantic_filter(
        self,
        asset_type: Optional[str] = None,
        category: Optional[str] = None,
        region: Optional[str] = None,
        season: Optional[str] = None,
        campaign_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find assets using semantic filters.

        Args:
            asset_type: Filter by asset type (product, background, composite)
            category: Filter by product category
            region: Filter by region
            season: Filter by season
            campaign_id: Filter by campaign ID

        Returns:
            List of matching assets
        """
        # Build appropriate S3 prefix based on filters
        if asset_type == "product" and category:
            prefix = f"{self.config.prefix}/products/{category}"
        elif asset_type == "background" and region and season:
            prefix = f"{self.config.prefix}/backgrounds/scene/{region}/{season}"
        elif asset_type == "composite" and campaign_id:
            prefix = f"{self.config.prefix}/composites/{campaign_id}"
        else:
            prefix = f"{self.config.prefix}/"

        # List objects with prefix
        objects = self.list_objects(prefix=prefix, include_metadata=True)

        # Additional filtering
        filtered = []
        for obj in objects:
            parsed = obj.get("parsed", {})

            # Apply filters
            if asset_type and parsed.get("type") != asset_type:
                continue
            if category and parsed.get("category") != category:
                continue
            if region and parsed.get("region") != region:
                continue
            if season and parsed.get("season") != season:
                continue
            if campaign_id and parsed.get("campaign_id") != campaign_id:
                continue

            filtered.append(obj)

        logger.info(f"Found {len(filtered)} assets matching filters")
        return filtered

    # ========================================================================
    # LIFECYCLE & MAINTENANCE
    # ========================================================================

    def setup_lifecycle_policy(
        self,
        transition_days: int = 90,
        expiration_days: Optional[int] = None,
        archive_storage_class: str = "GLACIER",
    ) -> bool:
        """
        Configure S3 lifecycle policy for cost optimization.

        Args:
            transition_days: Days until transition to archive storage
            expiration_days: Optional days until object expiration
            archive_storage_class: Archive storage class (GLACIER, DEEP_ARCHIVE)

        Returns:
            True if successful
        """
        try:
            rules = [
                {
                    "Id": "transition-to-archive",
                    "Status": "Enabled",
                    "Filter": {"Prefix": f"{self.config.prefix}/"},
                    "Transitions": [
                        {
                            "Days": transition_days,
                            "StorageClass": archive_storage_class,
                        }
                    ],
                }
            ]

            if expiration_days:
                rules[0]["Expiration"] = {"Days": expiration_days}

            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.config.bucket_name, LifecycleConfiguration={"Rules": rules}
            )

            logger.info(
                f"Lifecycle policy configured: transition to {archive_storage_class} "
                f"after {transition_days} days"
            )
            return True

        except ClientError as e:
            logger.error(f"Failed to setup lifecycle policy: {e}")
            return False

    def invalidate_cloudfront_cache(
        self, paths: List[str], caller_reference: Optional[str] = None
    ) -> Optional[str]:
        """
        Invalidate CloudFront cache for updated assets.

        Args:
            paths: List of CloudFront paths to invalidate
            caller_reference: Unique reference (auto-generated if None)

        Returns:
            Invalidation ID if successful
        """
        if not self.cloudfront_client or not self.config.cloudfront_distribution_id:
            logger.warning("CloudFront not configured, skipping cache invalidation")
            return None

        try:
            if caller_reference is None:
                caller_reference = f"creatimation-{int(time.time())}"

            response = self.cloudfront_client.create_invalidation(
                DistributionId=self.config.cloudfront_distribution_id,
                InvalidationBatch={
                    "Paths": {"Quantity": len(paths), "Items": paths},
                    "CallerReference": caller_reference,
                },
            )

            invalidation_id = response["Invalidation"]["Id"]
            logger.info(
                f"CloudFront invalidation created: {invalidation_id} for {len(paths)} paths"
            )
            return invalidation_id

        except ClientError as e:
            logger.error(f"Failed to invalidate CloudFront cache: {e}")
            return None

    def delete_object(self, s3_key: str, version_id: Optional[str] = None) -> bool:
        """
        Delete object from S3.

        Args:
            s3_key: S3 object key
            version_id: Optional specific version to delete

        Returns:
            True if successful
        """
        try:
            params = {"Bucket": self.config.bucket_name, "Key": s3_key}
            if version_id:
                params["VersionId"] = version_id

            self.s3_client.delete_object(**params)
            logger.info(f"Deleted object: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete {s3_key}: {e}")
            return False

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def get_presigned_url(
        self, s3_key: str, expiration: int = 3600, method: str = "get_object"
    ) -> Optional[str]:
        """
        Generate presigned URL for temporary access.

        Args:
            s3_key: S3 object key
            expiration: URL expiration in seconds (default 1 hour)
            method: S3 operation (get_object, put_object)

        Returns:
            Presigned URL or None if failed
        """
        try:
            url = self.s3_client.generate_presigned_url(
                method,
                Params={"Bucket": self.config.bucket_name, "Key": s3_key},
                ExpiresIn=expiration,
            )
            logger.debug(f"Generated presigned URL for {s3_key} (expires in {expiration}s)")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def get_bucket_size(self) -> Dict[str, Any]:
        """
        Calculate total size of assets in bucket under prefix.

        Returns:
            Dictionary with size statistics
        """
        objects = self.list_objects()

        total_size = sum(obj["size_bytes"] for obj in objects)
        total_count = len(objects)

        # Group by type
        by_type = {}
        for obj in objects:
            obj_type = obj.get("parsed", {}).get("type", "unknown")
            by_type[obj_type] = by_type.get(obj_type, 0) + obj["size_bytes"]

        return {
            "total_objects": total_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "total_size_gb": round(total_size / 1024 / 1024 / 1024, 2),
            "by_type": {
                k: {"size_bytes": v, "size_mb": round(v / 1024 / 1024, 2)}
                for k, v in by_type.items()
            },
        }
