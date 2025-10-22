"""
Unified Cache Manager for Creative Automation Pipeline.

Consolidates all cache functionality into a single, well-designed class
that supports both local and S3 storage with semantic asset matching.
"""
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from ..core.interfaces import CacheManagerInterface
    from ..core.models import AssetType, CacheEntry, Season, ProductCategory
except ImportError:
    # Fallback for direct execution
    from src.core.interfaces import CacheManagerInterface
    from src.core.models import AssetType, CacheEntry, Season, ProductCategory

logger = logging.getLogger(__name__)


class UnifiedCacheManager(CacheManagerInterface):
    """
    Unified cache manager with local and S3 support.

    Consolidates functionality from:
    - CacheManager (basic caching)
    - EnhancedCacheManager (semantic matching)
    - S3CacheManager (cloud storage)
    """

    def __init__(
        self,
        cache_dir: str = "cache",
        enable_s3: bool = False,
        s3_bucket: Optional[str] = None
    ):
        """Initialize unified cache manager."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Cache structure
        self.products_dir = self.cache_dir / "products"
        self.scenes_dir = self.cache_dir / "scenes"
        self.index_file = self.cache_dir / "index.json"

        # Initialize directories
        self.products_dir.mkdir(exist_ok=True)
        self.scenes_dir.mkdir(exist_ok=True)

        # Load or create index
        self.index = self._load_index()

        # S3 configuration (optional)
        self.enable_s3 = enable_s3
        self.s3_bucket = s3_bucket
        self._s3_client = None

        if enable_s3:
            self._initialize_s3()

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache."""
        if key in self.index:
            entry = self.index[key]
            file_path = Path(entry["file_path"])

            if file_path.exists():
                # Update access time
                entry["accessed_at"] = self._get_timestamp()
                self._save_index()
                return str(file_path)
            else:
                # Remove stale entry
                del self.index[key]
                self._save_index()

        return None

    def set(self, key: str, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store item in cache."""
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        entry = CacheEntry(
            key=key,
            file_path=str(file_path_obj),
            metadata=metadata or {},
            created_at=self._get_timestamp(),
            accessed_at=self._get_timestamp(),
            size_bytes=file_path_obj.stat().st_size
        )

        self.index[key] = entry.__dict__
        self._save_index()

        # Sync to S3 if enabled
        if self.enable_s3:
            self._sync_to_s3(key, file_path)

    def exists(self, key: str) -> bool:
        """Check if item exists in cache."""
        return key in self.index and Path(self.index[key]["file_path"]).exists()

    def clear(self) -> None:
        """Clear all cache entries."""
        self.index.clear()
        self._save_index()

        # Clear local files
        for cache_file in self.cache_dir.rglob("*"):
            if cache_file.is_file() and cache_file.name != "index.json":
                cache_file.unlink()

    # ========================================================================
    # PRODUCT MANAGEMENT
    # ========================================================================

    def register_product(
        self,
        product_name: str,
        product_slug: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a product in the cache."""
        cache_key = f"product:{product_slug}"

        enhanced_metadata = {
            "type": "product",
            "product_name": product_name,
            "product_slug": product_slug,
            **(metadata or {})
        }

        self.set(cache_key, file_path, enhanced_metadata)
        return cache_key

    def lookup_product(self, product_name: str) -> Optional[Dict[str, Any]]:
        """Look up product by name."""
        for key, entry in self.index.items():
            if (entry.get("metadata", {}).get("product_name") == product_name and
                entry.get("metadata", {}).get("type") == "product"):
                return {
                    "cache_key": key,
                    "file_path": entry["file_path"],
                    "metadata": entry["metadata"],
                    "product_cache_filename": entry["file_path"]
                }
        return None

    # ========================================================================
    # SEMANTIC ASSET MATCHING
    # ========================================================================

    def register_semantic_asset(
        self,
        cache_key: str,
        file_path: str,
        asset_type: AssetType,
        product_category: Optional[ProductCategory] = None,
        region: str = "US",
        season: Optional[Season] = None,
        aspect_ratio: Optional[str] = None,
        **kwargs
    ) -> None:
        """Register asset with semantic metadata for intelligent matching."""
        semantic_metadata = {
            "type": "semantic_asset",
            "asset_type": asset_type.value,
            "product_category": product_category.value if product_category else None,
            "region": region,
            "season": season.value if season else None,
            "aspect_ratio": aspect_ratio,
            **kwargs
        }

        self.set(cache_key, file_path, semantic_metadata)

    def discover_semantic_assets(
        self,
        asset_type: AssetType,
        product_category: Optional[ProductCategory] = None,
        region: str = "US",
        season: Optional[Season] = None,
        aspect_ratio: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Discover assets using semantic matching."""
        matches = []

        for key, entry in self.index.items():
            metadata = entry.get("metadata", {})

            if metadata.get("type") != "semantic_asset":
                continue

            if metadata.get("asset_type") != asset_type.value:
                continue

            # Calculate similarity score
            score = self._calculate_similarity_score(
                metadata, asset_type, product_category, region, season, aspect_ratio
            )

            if score > 0.3:  # Minimum similarity threshold
                matches.append({
                    "cache_key": key,
                    "file_path": entry["file_path"],
                    "metadata": metadata,
                    "similarity_score": score
                })

        # Sort by similarity and return top matches
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches[:limit]

    # ========================================================================
    # STATISTICS AND MAINTENANCE
    # ========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_entries = len(self.index)
        total_size = sum(entry.get("size_bytes", 0) for entry in self.index.values())

        # Count by type
        type_counts = {}
        for entry in self.index.values():
            asset_type = entry.get("metadata", {}).get("type", "unknown")
            type_counts[asset_type] = type_counts.get(asset_type, 0) + 1

        return {
            "total_entries": total_entries,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "type_breakdown": type_counts,
            "cache_directory": str(self.cache_dir),
            "s3_enabled": self.enable_s3
        }

    def cleanup_stale_entries(self, max_age_days: int = 30) -> int:
        """Remove stale cache entries."""
        current_time = time.time()
        cutoff_time = current_time - (max_age_days * 24 * 3600)

        stale_keys = []
        for key, entry in self.index.items():
            # Parse timestamp (assuming ISO format)
            accessed_at = entry.get("accessed_at", "")
            if accessed_at:
                try:
                    accessed_timestamp = time.mktime(
                        time.strptime(accessed_at, "%Y-%m-%d %H:%M:%S")
                    )
                    if accessed_timestamp < cutoff_time:
                        stale_keys.append(key)
                except ValueError:
                    # Invalid timestamp format, consider stale
                    stale_keys.append(key)

        # Remove stale entries
        for key in stale_keys:
            entry = self.index[key]
            file_path = Path(entry["file_path"])
            if file_path.exists():
                file_path.unlink()
            del self.index[key]

        if stale_keys:
            self._save_index()

        return len(stale_keys)

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _load_index(self) -> Dict[str, Any]:
        """Load cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache index: {e}")
        return {}

    def _save_index(self) -> None:
        """Save cache index to disk."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save cache index: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp in standard format."""
        return time.strftime("%Y-%m-%d %H:%M:%S")

    def _generate_cache_key(self, content: str) -> str:
        """Generate cache key from content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _calculate_similarity_score(
        self,
        metadata: Dict[str, Any],
        asset_type: AssetType,
        product_category: Optional[ProductCategory],
        region: str,
        season: Optional[Season],
        aspect_ratio: Optional[str]
    ) -> float:
        """Calculate similarity score for semantic matching."""
        score = 0.0

        # Exact matches get higher scores
        if metadata.get("asset_type") == asset_type.value:
            score += 0.4

        if product_category and metadata.get("product_category") == product_category.value:
            score += 0.3

        if metadata.get("region") == region:
            score += 0.2

        if season and metadata.get("season") == season.value:
            score += 0.2

        if aspect_ratio and metadata.get("aspect_ratio") == aspect_ratio:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    def _initialize_s3(self) -> None:
        """Initialize S3 client if enabled."""
        if not self.s3_bucket:
            logger.warning("S3 enabled but no bucket specified")
            return

        try:
            import boto3
            self._s3_client = boto3.client('s3')
            logger.info(f"S3 cache enabled with bucket: {self.s3_bucket}")
        except ImportError:
            logger.error("boto3 not installed, S3 cache disabled")
            self.enable_s3 = False

    def _sync_to_s3(self, key: str, file_path: str) -> None:
        """Sync cache entry to S3."""
        if not self._s3_client or not self.s3_bucket:
            return

        try:
            s3_key = f"cache/{key}"
            self._s3_client.upload_file(file_path, self.s3_bucket, s3_key)
            logger.debug(f"Synced to S3: {s3_key}")
        except Exception as e:
            logger.warning(f"Failed to sync to S3: {e}")


# Legacy compatibility aliases
CacheManager = UnifiedCacheManager
EnhancedCacheManager = UnifiedCacheManager
S3CacheManager = UnifiedCacheManager