#!/usr/bin/env python3
"""
S3-Enhanced Cache Manager - Hybrid local/cloud cache management

Extends the semantic cache manager with transparent S3 integration,
providing automatic fallback between local and cloud storage.

Features:
- Transparent local/S3 hybrid storage
- Automatic cache tier management (hot local, cold S3)
- Lazy download with local caching
- S3 metadata synchronization
- Fallback strategies for offline operation
- Smart prefetching based on usage patterns
"""

import logging
import os
from pathlib import Path
from typing import Any

from cache_manager import (
    AssetType,
    CacheManager,
    Season,
    SemanticMetadata,
)
from s3_storage_manager import S3Config, S3StorageManager

logger = logging.getLogger(__name__)


# ============================================================================
# S3-ENHANCED CACHE MANAGER
# ============================================================================


class S3CacheManager(CacheManager):
    """
    Enhanced cache manager with transparent S3 integration.

    Provides hybrid local/cloud storage with intelligent tier management:
    - Hot tier: Frequently used assets stored locally
    - Cold tier: Infrequently used assets in S3, downloaded on demand
    - Automatic tier promotion/demotion based on usage patterns
    """

    def __init__(
        self,
        cache_dir: str = "cache",
        s3_config: S3Config | None = None,
        enable_s3: bool = None,
        local_cache_size_limit_gb: float = 10.0,
    ):
        """
        Initialize S3-enhanced cache manager.

        Args:
            cache_dir: Local cache directory
            s3_config: S3 configuration (auto-loaded from env if None)
            enable_s3: Explicitly enable/disable S3 (auto-detect if None)
            local_cache_size_limit_gb: Maximum local cache size before promotion to S3
        """
        # Initialize base cache manager
        super().__init__(cache_dir=cache_dir)

        # S3 configuration
        self.local_cache_size_limit_bytes = int(local_cache_size_limit_gb * 1024 * 1024 * 1024)

        # Determine if S3 should be enabled
        if enable_s3 is None:
            # Auto-detect based on environment
            enable_s3 = bool(os.getenv("S3_BUCKET_NAME"))

        self.s3_enabled = enable_s3
        self.s3_manager: S3StorageManager | None = None

        if self.s3_enabled:
            try:
                if s3_config is None:
                    s3_config = S3Config.from_env()

                self.s3_manager = S3StorageManager(config=s3_config)
                logger.info("S3 integration enabled")

                # Track S3 operations
                if "s3_operations" not in self.index:
                    self.index["s3_operations"] = {
                        "uploads": 0,
                        "downloads": 0,
                        "cache_hits": 0,
                        "cache_misses": 0,
                    }
                    self._save_index()

            except Exception as e:
                logger.warning(f"Failed to initialize S3: {e}. Operating in local-only mode.")
                self.s3_enabled = False
                self.s3_manager = None
        else:
            logger.info("S3 integration disabled - operating in local-only mode")

    # ========================================================================
    # HYBRID STORAGE OPERATIONS
    # ========================================================================

    def get_asset_path(
        self,
        cache_key: str,
        auto_download: bool = True,
    ) -> Path | None:
        """
        Get local path to asset, downloading from S3 if necessary.

        Args:
            cache_key: Asset cache key
            auto_download: Automatically download from S3 if not local

        Returns:
            Local path to asset or None if not available
        """
        # Check semantic assets
        if cache_key in self.index.get("semantic_assets", {}):
            asset_entry = self.index["semantic_assets"][cache_key]
            local_path = Path(asset_entry.get("file_path", ""))

            # Check if exists locally
            if local_path.exists():
                self._record_access(cache_key, "local")
                return local_path

            # Try S3 download if enabled
            if self.s3_enabled and self.s3_manager and auto_download:
                s3_key = asset_entry.get("s3_key")
                if s3_key:
                    logger.info(f"Downloading {cache_key} from S3...")
                    if self._download_from_s3(s3_key, local_path):
                        self._record_access(cache_key, "s3_download")
                        return local_path

        # Check cache entries
        if cache_key in self.index.get("cache_entries", {}):
            entry = self.index["cache_entries"][cache_key]
            local_path = Path(entry.get("file_path", ""))

            if local_path.exists():
                self._record_access(cache_key, "local")
                return local_path

            # Try S3 download
            if self.s3_enabled and self.s3_manager and auto_download:
                s3_key = entry.get("s3_key")
                if s3_key:
                    if self._download_from_s3(s3_key, local_path):
                        self._record_access(cache_key, "s3_download")
                        return local_path

        logger.warning(f"Asset not found: {cache_key}")
        return None

    def register_semantic_asset(
        self,
        cache_key: str,
        file_path: str,
        metadata: SemanticMetadata,
        campaign_id: str | None = None,
        upload_to_s3: bool = True,
    ) -> None:
        """
        Register semantic asset with optional S3 upload.

        Args:
            cache_key: Unique cache key
            file_path: Path to asset file
            metadata: Semantic metadata
            campaign_id: Campaign that created this asset
            upload_to_s3: Whether to upload to S3 immediately
        """
        # Register locally
        super().register_semantic_asset(cache_key, file_path, metadata, campaign_id)

        # Upload to S3 if enabled
        if self.s3_enabled and self.s3_manager and upload_to_s3:
            self._upload_asset_to_s3(cache_key, file_path, metadata, campaign_id)

    def _upload_asset_to_s3(
        self,
        cache_key: str,
        file_path: str,
        metadata: SemanticMetadata,
        campaign_id: str | None = None,
    ) -> bool:
        """Upload asset to S3 with semantic metadata"""
        try:
            local_path = Path(file_path)
            if not local_path.exists():
                logger.warning(f"Cannot upload {cache_key}: file not found")
                return False

            # Generate S3 key based on metadata
            s3_key = self._generate_s3_key(cache_key, metadata, campaign_id)

            # Build S3 metadata
            s3_metadata = {
                "cache-key": cache_key,
                "asset-type": metadata.asset_type.value,
                "campaign-id": campaign_id or "",
            }

            if metadata.product_category:
                s3_metadata["product-category"] = metadata.product_category.value
            if metadata.region:
                s3_metadata["region"] = metadata.region
            if metadata.season:
                s3_metadata["season"] = metadata.season.value
            if metadata.visual_style:
                s3_metadata["visual-style"] = metadata.visual_style.value

            # Upload to S3
            result = self.s3_manager.upload_file(
                local_path=local_path,
                s3_key=s3_key,
                metadata=s3_metadata,
                tags={"cache-key": cache_key, "type": "semantic-asset"},
            )

            if result.success:
                # Update index with S3 key
                if cache_key in self.index["semantic_assets"]:
                    self.index["semantic_assets"][cache_key]["s3_key"] = s3_key
                    self.index["semantic_assets"][cache_key]["s3_uploaded"] = True
                    self._save_index()

                # Track upload
                self.index["s3_operations"]["uploads"] += 1
                self._save_index()

                logger.info(f"Uploaded {cache_key} to S3: {s3_key}")
                return True
            else:
                logger.error(f"Failed to upload {cache_key}: {result.error}")
                return False

        except Exception as e:
            logger.error(f"Error uploading {cache_key} to S3: {e}")
            return False

    def _download_from_s3(self, s3_key: str, local_path: Path) -> bool:
        """Download asset from S3 to local cache"""
        if not self.s3_manager:
            return False

        try:
            # Ensure directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Download
            success = self.s3_manager.download_file(s3_key, local_path)

            if success:
                # Track download
                self.index["s3_operations"]["downloads"] += 1
                self._save_index()

                logger.info(f"Downloaded from S3: {s3_key} -> {local_path}")
                return True
            else:
                logger.error(f"Failed to download from S3: {s3_key}")
                return False

        except Exception as e:
            logger.error(f"Error downloading from S3: {e}")
            return False

    def _generate_s3_key(
        self,
        cache_key: str,
        metadata: SemanticMetadata,
        campaign_id: str | None = None,
    ) -> str:
        """Generate S3 key based on semantic metadata"""
        if not self.s3_manager:
            return f"assets/{cache_key}"

        folder_structure = self.s3_manager.folder_structure

        # Product assets
        if metadata.asset_type in [
            AssetType.PRODUCT_TRANSPARENT,
            AssetType.PRODUCT_ORIGINAL,
        ]:
            category = metadata.product_category.value if metadata.product_category else "general"
            asset_type = (
                "transparent"
                if metadata.asset_type == AssetType.PRODUCT_TRANSPARENT
                else "original"
            )
            return folder_structure.get_product_path(
                product_slug=cache_key,
                category=category,
                asset_type=asset_type,
                filename=f"{cache_key}.png",
            )

        # Background assets
        elif metadata.asset_type in [
            AssetType.SCENE_BACKGROUND,
            AssetType.CONTEXTUAL_BACKGROUND,
            AssetType.GRADIENT_BACKGROUND,
            AssetType.SOLID_BACKGROUND,
        ]:
            style = metadata.visual_style.value if metadata.visual_style else "scene"
            return folder_structure.get_background_path(
                style=style,
                region=metadata.region,
                season=metadata.season.value if metadata.season != Season.NONE else None,
                filename=f"{cache_key}.jpg",
            )

        # Composite assets
        elif metadata.asset_type == AssetType.COMPOSITE:
            return folder_structure.get_composite_path(
                campaign_id=campaign_id or "unknown",
                product_slug=cache_key,
                aspect_ratio=metadata.aspect_ratio or "1x1",
                filename=f"{cache_key}.jpg",
            )

        # Default
        return f"{self.s3_manager.config.prefix}/assets/{cache_key}"

    def _record_access(self, cache_key: str, access_type: str) -> None:
        """Record asset access for tier management"""
        if cache_key in self.index.get("semantic_assets", {}):
            asset_entry = self.index["semantic_assets"][cache_key]
            asset_entry["last_accessed"] = self._get_timestamp()
            asset_entry["access_count"] = asset_entry.get("access_count", 0) + 1

            if access_type == "s3_download":
                self.index["s3_operations"]["cache_misses"] += 1
            elif access_type == "local":
                self.index["s3_operations"]["cache_hits"] += 1

            self._save_index()

    @staticmethod
    def _get_timestamp() -> str:
        """Get current timestamp"""
        from datetime import datetime

        return datetime.now().isoformat()

    # ========================================================================
    # S3 DISCOVERY INTEGRATION
    # ========================================================================

    def discover_s3_assets(
        self,
        asset_type: AssetType | None = None,
        sync_to_local: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Discover assets available in S3.

        Args:
            asset_type: Optional filter by asset type
            sync_to_local: Whether to sync discovered assets to local index

        Returns:
            List of discovered S3 assets
        """
        if not self.s3_enabled or not self.s3_manager:
            logger.warning("S3 not enabled")
            return []

        logger.info("Discovering assets in S3...")

        # List all objects
        objects = self.s3_manager.list_objects(include_metadata=True)

        discovered = []

        for obj in objects:
            parsed = obj.get("parsed", {})
            obj_type = parsed.get("type")

            # Filter by asset type if specified
            if asset_type and obj_type != asset_type.value.split("_")[0]:
                continue

            discovered.append(
                {
                    "s3_key": obj["s3_key"],
                    "size_bytes": obj["size_bytes"],
                    "last_modified": obj["last_modified"],
                    "parsed": parsed,
                    "metadata": obj.get("metadata", {}),
                }
            )

        logger.info(f"Discovered {len(discovered)} assets in S3")

        # Optionally sync to local index
        if sync_to_local:
            self._sync_s3_assets_to_index(discovered)

        return discovered

    def _sync_s3_assets_to_index(self, s3_assets: list[dict[str, Any]]) -> int:
        """Sync S3 assets to local index without downloading files"""
        synced = 0

        for asset in s3_assets:
            s3_key = asset["s3_key"]
            parsed = asset.get("parsed", {})
            metadata = asset.get("metadata", {})

            cache_key = metadata.get("cache-key") or s3_key.split("/")[-1]

            # Check if already in index
            if cache_key in self.index.get("semantic_assets", {}):
                continue

            # Create index entry without local file
            asset_entry = {
                "cache_key": cache_key,
                "file_path": str(self.cache_dir / f"s3_cache/{cache_key}"),
                "s3_key": s3_key,
                "s3_only": True,
                "semantic_metadata": {
                    "asset_type": metadata.get("asset-type", "unknown"),
                    "product_category": metadata.get("product-category"),
                    "region": metadata.get("region"),
                    "season": metadata.get("season"),
                    "visual_style": metadata.get("visual-style"),
                },
                "created_at": asset.get("last_modified"),
                "usage_count": 0,
                "campaigns_used": [metadata.get("campaign-id")]
                if metadata.get("campaign-id")
                else [],
            }

            self.index["semantic_assets"][cache_key] = asset_entry
            synced += 1

        if synced > 0:
            self._save_index()
            logger.info(f"Synced {synced} S3 assets to local index")

        return synced

    # ========================================================================
    # TIER MANAGEMENT
    # ========================================================================

    def manage_cache_tiers(
        self,
        promote_hot_assets: bool = True,
        demote_cold_assets: bool = True,
        cold_threshold_days: int = 30,
    ) -> dict[str, int]:
        """
        Manage cache tiers based on usage patterns.

        Args:
            promote_hot_assets: Download frequently used S3 assets locally
            demote_cold_assets: Remove infrequently used local assets
            cold_threshold_days: Days since last access to consider asset cold

        Returns:
            Dictionary with promotion/demotion counts
        """
        if not self.s3_enabled:
            return {"promoted": 0, "demoted": 0, "skipped": 0}

        from datetime import datetime, timedelta

        now = datetime.now()
        cold_cutoff = now - timedelta(days=cold_threshold_days)

        promoted = 0
        demoted = 0
        skipped = 0

        # Check local cache size
        current_size = self._calculate_local_cache_size()

        logger.info(
            f"Managing cache tiers (current size: {current_size / 1024 / 1024:.1f} MB, "
            f"limit: {self.local_cache_size_limit_bytes / 1024 / 1024:.1f} MB)"
        )

        # Demote cold assets if over limit
        if demote_cold_assets and current_size > self.local_cache_size_limit_bytes:
            for cache_key, asset_entry in self.index.get("semantic_assets", {}).items():
                local_path = Path(asset_entry.get("file_path", ""))

                # Skip if not local or already in S3
                if not local_path.exists() or not asset_entry.get("s3_uploaded"):
                    continue

                # Check last access
                last_accessed_str = asset_entry.get("last_accessed")
                if last_accessed_str:
                    last_accessed = datetime.fromisoformat(last_accessed_str)
                    if last_accessed < cold_cutoff:
                        # Remove local file
                        try:
                            local_path.unlink()
                            demoted += 1
                            logger.debug(f"Demoted cold asset: {cache_key}")
                        except Exception as e:
                            logger.warning(f"Failed to demote {cache_key}: {e}")

        # Promote hot S3-only assets
        if promote_hot_assets:
            for cache_key, asset_entry in self.index.get("semantic_assets", {}).items():
                if not asset_entry.get("s3_only"):
                    continue

                access_count = asset_entry.get("access_count", 0)
                if access_count >= 3:  # Accessed 3+ times
                    s3_key = asset_entry.get("s3_key")
                    local_path = Path(asset_entry.get("file_path", ""))

                    if s3_key and not local_path.exists():
                        if self._download_from_s3(s3_key, local_path):
                            asset_entry["s3_only"] = False
                            promoted += 1
                            logger.debug(f"Promoted hot asset: {cache_key}")

        self._save_index()

        logger.info(f"Tier management complete: {promoted} promoted, {demoted} demoted")

        return {"promoted": promoted, "demoted": demoted, "skipped": skipped}

    def _calculate_local_cache_size(self) -> int:
        """Calculate total size of local cache"""
        total_size = 0

        for cache_key, asset_entry in self.index.get("semantic_assets", {}).items():
            local_path = Path(asset_entry.get("file_path", ""))
            if local_path.exists():
                total_size += local_path.stat().st_size

        return total_size

    # ========================================================================
    # S3 STATISTICS
    # ========================================================================

    def get_s3_stats(self) -> dict[str, Any]:
        """Get S3 usage statistics"""
        if not self.s3_enabled:
            return {"s3_enabled": False}

        s3_ops = self.index.get("s3_operations", {})

        # Count S3-backed assets
        s3_assets = sum(
            1
            for asset in self.index.get("semantic_assets", {}).values()
            if asset.get("s3_uploaded") or asset.get("s3_only")
        )

        # Calculate cache hit rate
        total_accesses = s3_ops.get("cache_hits", 0) + s3_ops.get("cache_misses", 0)
        cache_hit_rate = (
            (s3_ops.get("cache_hits", 0) / total_accesses * 100) if total_accesses > 0 else 0
        )

        stats = {
            "s3_enabled": True,
            "bucket_name": self.s3_manager.config.bucket_name if self.s3_manager else None,
            "s3_assets": s3_assets,
            "uploads": s3_ops.get("uploads", 0),
            "downloads": s3_ops.get("downloads", 0),
            "cache_hits": s3_ops.get("cache_hits", 0),
            "cache_misses": s3_ops.get("cache_misses", 0),
            "cache_hit_rate": round(cache_hit_rate, 1),
            "local_cache_size_mb": round(self._calculate_local_cache_size() / 1024 / 1024, 2),
        }

        # Get S3 bucket size if available
        if self.s3_manager:
            try:
                bucket_size = self.s3_manager.get_bucket_size()
                stats["s3_total_size_mb"] = bucket_size.get("total_size_mb", 0)
                stats["s3_total_objects"] = bucket_size.get("total_objects", 0)
            except Exception as e:
                logger.debug(f"Could not get bucket size: {e}")

        return stats
