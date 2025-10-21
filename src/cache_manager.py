#!/usr/bin/env python3
"""
Cache Manager - Index tracking and cache lineage

Maintains cache/index.json with hash→file mapping and tracks cache lineage
in metadata for full transparency of which cached assets contributed to each output.
"""
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages cache index and lineage tracking"""

    def __init__(self, cache_dir: str = "cache"):
        """
        Initialize cache manager.

        Args:
            cache_dir: Base cache directory
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.index_path = self.cache_dir / "index.json"
        self.index = self._load_index()

        # Ensure product registry section exists
        if "products" not in self.index:
            self.index["products"] = {}
        if "cache_entries" not in self.index:
            self.index["cache_entries"] = {}

        logger.info(f"CacheManager initialized with directory: {self.cache_dir}")

    def _load_index(self) -> dict:
        """Load cache index from disk"""
        if self.index_path.exists():
            try:
                with open(self.index_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                return {}
        return {}

    def _save_index(self) -> None:
        """Save cache index to disk"""
        try:
            with open(self.index_path, "w") as f:
                json.dump(self.index, f, indent=2)
            logger.debug("Cache index saved")
        except Exception as e:
            logger.error(f"Failed to save cache index: {e}")

    def register_cache_entry(self, cache_key: str, file_path: str, metadata: dict) -> None:
        """
        Register a cache entry in the index.

        Args:
            cache_key: Cache hash key
            file_path: Path to cached file
            metadata: Additional metadata (product_slug, type, etc.)
        """
        entry = {
            "file_path": str(file_path),
            "cache_key": cache_key,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata,
        }

        self.index[cache_key] = entry
        self._save_index()

        logger.debug(f"Registered cache entry: {cache_key} -> {file_path}")

    def get_cache_entry(self, cache_key: str) -> dict | None:
        """
        Get cache entry by key.

        Args:
            cache_key: Cache hash key

        Returns:
            Cache entry dict or None if not found
        """
        return self.index.get(cache_key)

    def find_by_metadata(self, **kwargs) -> list[dict]:
        """
        Find cache entries matching metadata criteria.

        Args:
            **kwargs: Metadata key-value pairs to match

        Returns:
            List of matching cache entries
        """
        matches = []

        for cache_key, entry in self.index.items():
            metadata = entry.get("metadata", {})
            if all(metadata.get(k) == v for k, v in kwargs.items()):
                matches.append(entry)

        return matches

    def build_lineage_metadata(self, cache_hits: dict) -> dict:
        """
        Build cache lineage metadata for output.

        Args:
            cache_hits: Dict of {cache_type: cache_filename}

        Returns:
            Lineage metadata dict
        """
        lineage = {
            "cache_hits": cache_hits,
            "cache_count": len(cache_hits),
            "fully_cached": all(v for v in cache_hits.values()),
        }

        # Add cache entry details
        for cache_type, cache_filename in cache_hits.items():
            if cache_filename:
                # Try to find entry in index
                for cache_key, entry in self.index.items():
                    if cache_filename in entry.get("file_path", ""):
                        lineage[f"{cache_type}_cache_key"] = cache_key
                        lineage[f"{cache_type}_created_at"] = entry.get("created_at")
                        break

        return lineage

    def get_cache_stats(self) -> dict:
        """
        Get comprehensive cache statistics.

        Returns:
            Dict with cache statistics
        """
        total_entries = len(self.index)
        total_size = 0

        # Calculate total size of cached files
        for entry in self.index.values():
            file_path = Path(entry.get("file_path", ""))
            if file_path.exists():
                total_size += file_path.stat().st_size

        # Group by type
        by_type = {}
        for entry in self.index.values():
            cache_type = entry.get("metadata", {}).get("type", "unknown")
            by_type[cache_type] = by_type.get(cache_type, 0) + 1

        return {
            "total_entries": total_entries,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": by_type,
            "index_path": str(self.index_path),
        }

    def clear_cache(self, cache_type: str | None = None) -> int:
        """
        Clear cache entries and files.

        Args:
            cache_type: Optional cache type filter (transparent, scene, etc.)

        Returns:
            Number of entries cleared
        """
        entries_to_remove = []

        # Ensure cache_entries section exists
        if "cache_entries" not in self.index:
            self.index["cache_entries"] = {}

        # Only iterate over cache_entries, not the special sections like "products"
        for cache_key, entry in self.index.get("cache_entries", {}).items():
            if cache_type is None or entry.get("metadata", {}).get("type") == cache_type:
                # Delete file
                file_path = Path(entry.get("file_path", ""))
                if file_path.exists():
                    try:
                        file_path.unlink()
                        logger.debug(f"Deleted cache file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete {file_path}: {e}")

                entries_to_remove.append(cache_key)

        # Remove from cache_entries section
        for cache_key in entries_to_remove:
            del self.index["cache_entries"][cache_key]

        self._save_index()

        cleared_count = len(entries_to_remove)
        logger.info(f"Cleared {cleared_count} cache entries")
        return cleared_count

    # ========================================================================
    # PRODUCT REGISTRY METHODS
    # ========================================================================

    def register_product(
        self,
        product_name: str,
        cache_filename: str = None,
        product_cache_filename: str = None,
        campaign_id: str = None,
        tags: list[str] = None,
    ) -> str:
        """
        Register a product in the product registry.

        Args:
            product_name: Full product name
            cache_filename: Background-removed cache filename
            product_cache_filename: Original product cache filename
            campaign_id: Campaign that created this product
            tags: Optional tags for categorization

        Returns:
            Product slug
        """
        product_slug = self._slugify_product_name(product_name)

        # Check if product already exists
        existing = self.index["products"].get(product_slug)
        if existing:
            # Update campaigns_used list
            if campaign_id and campaign_id not in existing.get("campaigns_used", []):
                existing["campaigns_used"].append(campaign_id)
                self._save_index()
            logger.info(f"Product already registered: {product_slug}")
            return product_slug

        # Register new product
        product_entry = {
            "name": product_name,
            "slug": product_slug,
            "cache_filename": cache_filename,
            "product_cache_filename": product_cache_filename,
            "created_at": datetime.now().isoformat(),
            "campaigns_used": [campaign_id] if campaign_id else [],
            "status": "ready",
            "tags": tags or [],
        }

        self.index["products"][product_slug] = product_entry
        self._save_index()

        logger.info(f"Registered product: {product_name} -> {product_slug}")
        return product_slug

    def lookup_product(self, product_name: str) -> dict | None:
        """
        Look up product by name in the registry.

        Args:
            product_name: Full product name to search for

        Returns:
            Product entry dict or None if not found
        """
        product_slug = self._slugify_product_name(product_name)
        return self.index["products"].get(product_slug)

    def get_product_by_slug(self, product_slug: str) -> dict | None:
        """
        Get product info by slug.

        Args:
            product_slug: Product slug

        Returns:
            Product entry dict or None if not found
        """
        return self.index["products"].get(product_slug)

    def list_all_products(self) -> dict[str, dict]:
        """
        Get all registered products.

        Returns:
            Dict of {product_slug: product_info}
        """
        return self.index["products"]

    def _slugify_product_name(self, product_name: str) -> str:
        """
        Convert product name to slug format.

        Args:
            product_name: Full product name

        Returns:
            Slugified product name
        """
        import re

        # Convert to lowercase and replace spaces/special chars with hyphens
        slug = re.sub(r"[^\w\s-]", "", product_name.lower())
        slug = re.sub(r"[\s_-]+", "-", slug)
        return slug.strip("-")

    def validate_cache(self) -> dict:
        """
        Validate cache integrity (check for missing files).

        Returns:
            Dict with validation results
        """
        total = len(self.index)
        valid = 0
        missing = []

        for cache_key, entry in self.index.items():
            file_path = Path(entry.get("file_path", ""))
            if file_path.exists():
                valid += 1
            else:
                missing.append(cache_key)

        return {
            "total_entries": total,
            "valid_entries": valid,
            "missing_entries": len(missing),
            "missing_keys": missing,
        }


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Cache manager utilities")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--validate", action="store_true", help="Validate cache integrity")
    parser.add_argument("--clear", action="store_true", help="Clear all cache entries")
    parser.add_argument("--cache-dir", default="cache", help="Cache directory")

    args = parser.parse_args()

    manager = CacheManager(args.cache_dir)

    if args.stats:
        stats = manager.get_cache_stats()
        print("\n📊 Cache Statistics:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print("  By type:")
        for cache_type, count in stats["by_type"].items():
            print(f"    - {cache_type}: {count}")
        print(f"  Index path: {stats['index_path']}")

    elif args.validate:
        results = manager.validate_cache()
        print("\n✓ Cache Validation:")
        print(f"  Total entries: {results['total_entries']}")
        print(f"  Valid entries: {results['valid_entries']}")
        print(f"  Missing entries: {results['missing_entries']}")
        if results["missing_keys"]:
            print("  Missing keys:")
            for key in results["missing_keys"][:5]:
                print(f"    - {key}")
            if len(results["missing_keys"]) > 5:
                print(f"    ... and {len(results['missing_keys']) - 5} more")

    elif args.clear:
        import sys

        response = input("Clear all cache entries? This cannot be undone. (yes/no): ")
        if response.lower() == "yes":
            cleared = manager.clear_cache()
            print(f"✓ Cleared {cleared} cache entries")
        else:
            print("Cancelled")
            sys.exit(0)

    else:
        print("Use --stats, --validate, or --clear")
