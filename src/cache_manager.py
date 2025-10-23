#!/usr/bin/env python3
"""
Cache Manager - Intelligent Semantic Asset Reuse System

Maintains cache/index.json with hash→file mapping and tracks cache lineage
in metadata for full transparency of which cached assets contributed to each output.

Enhanced Features:
- Semantic asset tagging and metadata system
- Intelligent asset matching algorithms with similarity scoring
- Cross-campaign asset discovery mechanisms
- Asset versioning and variant tracking
- Background adaptation and seasonal updating logic
- Learning system for asset reuse pattern tracking
- Clean API for seamless CLI integration
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# SEMANTIC METADATA SCHEMA
# ============================================================================


class AssetType(Enum):
    """Asset type classifications"""

    PRODUCT_TRANSPARENT = "product_transparent"  # Background-removed product
    PRODUCT_ORIGINAL = "product_original"  # Original product with background
    SCENE_BACKGROUND = "scene_background"  # Lifestyle/contextual backgrounds
    CONTEXTUAL_BACKGROUND = "contextual_background"  # Product-specific contexts
    GRADIENT_BACKGROUND = "gradient_background"  # Gradient backgrounds
    SOLID_BACKGROUND = "solid_background"  # Solid color backgrounds
    COMPOSITE = "composite"  # Final composed creative


class Season(Enum):
    """Seasonal classifications for adaptive backgrounds"""

    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    HOLIDAY = "holiday"
    BACK_TO_SCHOOL = "back_to_school"
    NONE = "none"  # Season-neutral assets


class VisualStyle(Enum):
    """Visual style classifications"""

    MINIMAL = "minimal"
    VIBRANT = "vibrant"
    ELEGANT = "elegant"
    WARM = "warm"
    COOL = "cool"
    PROFESSIONAL = "professional"
    CASUAL = "casual"


class ProductCategory(Enum):
    """Product category classifications"""

    LAUNDRY_DETERGENT = "laundry_detergent"
    DISH_SOAP = "dish_soap"
    HAIR_CARE = "hair_care"
    ORAL_CARE = "oral_care"
    PERSONAL_CARE = "personal_care"
    GENERAL_CPG = "general_cpg"


class SemanticMetadata:
    """
    Semantic metadata for intelligent asset reuse.

    This rich metadata enables cross-campaign asset discovery,
    intelligent matching, and adaptive background selection.
    """

    def __init__(
        self,
        asset_type: AssetType,
        product_category: ProductCategory | None = None,
        region: str | None = None,
        visual_style: VisualStyle | None = None,
        season: Season = Season.NONE,
        color_palette: list[str] | None = None,
        tags: list[str] | None = None,
        dimensions: tuple[int, int] | None = None,
        aspect_ratio: str | None = None,
    ):
        self.asset_type = asset_type
        self.product_category = product_category
        self.region = region
        self.visual_style = visual_style
        self.season = season
        self.color_palette = color_palette or []
        self.tags = tags or []
        self.dimensions = dimensions
        self.aspect_ratio = aspect_ratio

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "asset_type": self.asset_type.value,
            "product_category": self.product_category.value if self.product_category else None,
            "region": self.region,
            "visual_style": self.visual_style.value if self.visual_style else None,
            "season": self.season.value,
            "color_palette": self.color_palette,
            "tags": self.tags,
            "dimensions": self.dimensions,
            "aspect_ratio": self.aspect_ratio,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticMetadata":
        """Create from dictionary"""
        return cls(
            asset_type=AssetType(data["asset_type"]),
            product_category=(
                ProductCategory(data["product_category"]) if data.get("product_category") else None
            ),
            region=data.get("region"),
            visual_style=VisualStyle(data["visual_style"]) if data.get("visual_style") else None,
            season=Season(data.get("season", "none")),
            color_palette=data.get("color_palette", []),
            tags=data.get("tags", []),
            dimensions=tuple(data["dimensions"]) if data.get("dimensions") else None,
            aspect_ratio=data.get("aspect_ratio"),
        )


# ============================================================================
# ASSET MATCHING & DISCOVERY
# ============================================================================


class AssetMatcher:
    """
    Intelligent asset matching for cross-campaign reuse.

    Uses weighted scoring across multiple dimensions:
    - Visual style similarity
    - Seasonal appropriateness
    - Product category compatibility
    - Regional aesthetic match
    - Color palette harmony
    """

    # Matching weights for similarity scoring
    WEIGHTS = {
        "visual_style": 0.25,
        "season": 0.20,
        "product_category": 0.20,
        "region": 0.15,
        "color_palette": 0.10,
        "tags": 0.10,
    }

    @staticmethod
    def calculate_similarity(
        target_metadata: SemanticMetadata,
        candidate_metadata: SemanticMetadata,
    ) -> float:
        """
        Calculate similarity score between target and candidate assets.

        Args:
            target_metadata: Target asset metadata
            candidate_metadata: Candidate asset metadata

        Returns:
            Similarity score (0.0 to 1.0, higher is better match)
        """
        score = 0.0

        # Visual style match
        if target_metadata.visual_style and candidate_metadata.visual_style:
            if target_metadata.visual_style == candidate_metadata.visual_style:
                score += AssetMatcher.WEIGHTS["visual_style"]

        # Seasonal appropriateness
        if AssetMatcher._is_season_compatible(target_metadata.season, candidate_metadata.season):
            score += AssetMatcher.WEIGHTS["season"]

        # Product category match
        if target_metadata.product_category and candidate_metadata.product_category:
            if target_metadata.product_category == candidate_metadata.product_category:
                score += AssetMatcher.WEIGHTS["product_category"]

        # Regional aesthetic match
        if target_metadata.region and candidate_metadata.region:
            if target_metadata.region == candidate_metadata.region:
                score += AssetMatcher.WEIGHTS["region"]

        # Color palette harmony
        color_similarity = AssetMatcher._calculate_color_similarity(
            target_metadata.color_palette,
            candidate_metadata.color_palette,
        )
        score += color_similarity * AssetMatcher.WEIGHTS["color_palette"]

        # Tag overlap
        tag_similarity = AssetMatcher._calculate_tag_similarity(
            target_metadata.tags,
            candidate_metadata.tags,
        )
        score += tag_similarity * AssetMatcher.WEIGHTS["tags"]

        return min(score, 1.0)

    @staticmethod
    def _is_season_compatible(target_season: Season, candidate_season: Season) -> bool:
        """Check if seasons are compatible"""
        # Season-neutral assets work with anything
        if target_season == Season.NONE or candidate_season == Season.NONE:
            return True

        # Exact match is best
        if target_season == candidate_season:
            return True

        # Some seasons are compatible (e.g., spring/summer, fall/winter)
        compatible_pairs = [
            {Season.SPRING, Season.SUMMER},
            {Season.FALL, Season.WINTER},
        ]

        for pair in compatible_pairs:
            if target_season in pair and candidate_season in pair:
                return True

        return False

    @staticmethod
    def _calculate_color_similarity(colors1: list[str], colors2: list[str]) -> float:
        """Calculate color palette similarity (basic overlap metric)"""
        if not colors1 or not colors2:
            return 0.0

        set1 = set(colors1)
        set2 = set(colors2)

        overlap = len(set1 & set2)
        total = len(set1 | set2)

        return overlap / total if total > 0 else 0.0

    @staticmethod
    def _calculate_tag_similarity(tags1: list[str], tags2: list[str]) -> float:
        """Calculate tag similarity (Jaccard index)"""
        if not tags1 or not tags2:
            return 0.0

        set1 = set(tags1)
        set2 = set(tags2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        return intersection / union if union > 0 else 0.0


# ============================================================================
# ASSET VERSIONING & VARIANTS
# ============================================================================


class AssetVersion:
    """
    Asset versioning for tracking updates and variants.

    Enables seasonal refreshes, A/B testing, and variant management.
    """

    def __init__(
        self,
        version: str,
        cache_key: str,
        file_path: str,
        created_at: str,
        variant_type: str | None = None,
        parent_version: str | None = None,
        change_notes: str | None = None,
    ):
        self.version = version
        self.cache_key = cache_key
        self.file_path = file_path
        self.created_at = created_at
        self.variant_type = variant_type
        self.parent_version = parent_version
        self.change_notes = change_notes

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "cache_key": self.cache_key,
            "file_path": self.file_path,
            "created_at": self.created_at,
            "variant_type": self.variant_type,
            "parent_version": self.parent_version,
            "change_notes": self.change_notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AssetVersion":
        """Create from dictionary"""
        return cls(
            version=data["version"],
            cache_key=data["cache_key"],
            file_path=data["file_path"],
            created_at=data["created_at"],
            variant_type=data.get("variant_type"),
            parent_version=data.get("parent_version"),
            change_notes=data.get("change_notes"),
        )


# ============================================================================
# LEARNING SYSTEM FOR REUSE PATTERNS
# ============================================================================


class ReusePattern:
    """
    Tracks successful asset reuse patterns to learn over time.

    This enables the system to get smarter about asset selection
    based on what has worked well in the past.
    """

    def __init__(
        self,
        source_asset: str,
        target_campaign: str,
        reuse_count: int = 0,
        success_rate: float = 0.0,
        contexts: list[str] | None = None,
    ):
        self.source_asset = source_asset
        self.target_campaign = target_campaign
        self.reuse_count = reuse_count
        self.success_rate = success_rate
        self.contexts = contexts or []

    def record_reuse(self, success: bool, context: str | None = None):
        """Record a reuse instance"""
        self.reuse_count += 1

        # Update success rate (weighted average)
        if success:
            self.success_rate = (
                self.success_rate * (self.reuse_count - 1) + 1.0
            ) / self.reuse_count
        else:
            self.success_rate = (self.success_rate * (self.reuse_count - 1)) / self.reuse_count

        if context and context not in self.contexts:
            self.contexts.append(context)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "source_asset": self.source_asset,
            "target_campaign": self.target_campaign,
            "reuse_count": self.reuse_count,
            "success_rate": self.success_rate,
            "contexts": self.contexts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReusePattern":
        """Create from dictionary"""
        return cls(
            source_asset=data["source_asset"],
            target_campaign=data["target_campaign"],
            reuse_count=data.get("reuse_count", 0),
            success_rate=data.get("success_rate", 0.0),
            contexts=data.get("contexts", []),
        )


class CacheManager:
    """
    Manages cache index, lineage tracking, and intelligent semantic asset reuse.

    Enhanced with semantic tagging, cross-campaign discovery, versioning,
    adaptive backgrounds, and learning-based asset recommendations.
    """

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

        # Ensure all required sections exist
        if "products" not in self.index:
            self.index["products"] = {}
        if "cache_entries" not in self.index:
            self.index["cache_entries"] = {}
        if "semantic_assets" not in self.index:
            self.index["semantic_assets"] = {}
        if "asset_versions" not in self.index:
            self.index["asset_versions"] = {}
        if "reuse_patterns" not in self.index:
            self.index["reuse_patterns"] = {}
        if "background_library" not in self.index:
            self.index["background_library"] = {}

        # Save the initialized index structure
        self._save_index()

        # Initialize matcher
        self.matcher = AssetMatcher()

        logger.info(f"CacheManager initialized with directory: {self.cache_dir}")
        logger.info("Intelligent semantic asset reuse enabled")

    def _load_index(self) -> dict[Any, Any]:
        """Load cache index from disk"""
        if self.index_path.exists():
            try:
                with open(self.index_path) as f:
                    loaded: dict[Any, Any] = json.load(f)
                    return loaded
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

        for _cache_key, entry in self.index.items():
            metadata = entry.get("metadata", {})
            if all(metadata.get(k) == v for k, v in kwargs.items()):
                matches.append(entry)

        return matches

    def query_cache(self, **kwargs) -> list[dict]:
        """
        Query cache entries by metadata (alias for find_by_metadata).

        Args:
            **kwargs: Metadata key-value pairs to match

        Returns:
            List of matching cache entries
        """
        return self.find_by_metadata(**kwargs)

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
        by_type: dict[str, int] = {}
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
        file_path: str,
        campaign_id: str,
        tags: list[str] | None = None,
        cache_filename: str | None = None,
        product_cache_filename: str | None = None,
    ) -> str:
        """
        Register a product in the product registry.

        Args:
            product_name: Full product name
            file_path: Path to the product file
            campaign_id: Campaign that created this product
            tags: Optional tags for categorization
            cache_filename: Background-removed cache filename (optional, for backwards compatibility)
            product_cache_filename: Original product cache filename (optional, for backwards compatibility)

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
            "file_path": file_path,
            "cache_filename": cache_filename or file_path,  # For backwards compatibility
            "product_cache_filename": product_cache_filename
            or file_path,  # For backwards compatibility
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
        result = self.index["products"].get(product_slug)
        return dict(result) if result else None

    def get_product_by_slug(self, product_slug: str) -> dict | None:
        """
        Get product info by slug.

        Args:
            product_slug: Product slug

        Returns:
            Product entry dict or None if not found
        """
        result = self.index["products"].get(product_slug)
        return dict(result) if result else None

    def list_all_products(self) -> dict[str, dict[Any, Any]]:
        """
        Get all registered products.

        Returns:
            Dict of {product_slug: product_info}
        """
        return dict(self.index["products"])

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

    # ========================================================================
    # SEMANTIC ASSET REGISTRATION & TAGGING
    # ========================================================================

    def register_semantic_asset(
        self,
        cache_key: str,
        file_path: str,
        metadata: SemanticMetadata,
        campaign_id: str | None = None,
    ) -> None:
        """
        Register asset with semantic metadata for intelligent reuse.

        Args:
            cache_key: Unique cache key
            file_path: Path to asset file
            metadata: Semantic metadata for the asset
            campaign_id: Campaign that created this asset
        """
        asset_entry = {
            "cache_key": cache_key,
            "file_path": str(file_path),
            "semantic_metadata": metadata.to_dict(),
            "campaign_id": campaign_id,
            "created_at": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "usage_count": 0,
            "campaigns_used": [campaign_id] if campaign_id else [],
        }

        self.index["semantic_assets"][cache_key] = asset_entry
        self._save_index()

        logger.info(f"Registered semantic asset: {cache_key} ({metadata.asset_type.value})")

    def update_semantic_metadata(
        self,
        cache_key: str,
        metadata_updates: dict[str, Any],
    ) -> bool:
        """
        Update semantic metadata for an existing asset.

        Args:
            cache_key: Asset cache key
            metadata_updates: Dictionary of metadata fields to update

        Returns:
            True if successful, False if asset not found
        """
        if cache_key not in self.index["semantic_assets"]:
            logger.warning(f"Asset not found: {cache_key}")
            return False

        asset_entry = self.index["semantic_assets"][cache_key]
        current_metadata = asset_entry.get("semantic_metadata", {})

        # Merge updates
        current_metadata.update(metadata_updates)
        asset_entry["semantic_metadata"] = current_metadata

        self._save_index()
        logger.info(f"Updated semantic metadata for: {cache_key}")
        return True

    def tag_asset(self, cache_key: str, tags: list[str]) -> bool:
        """
        Add tags to an asset for better discovery.

        Args:
            cache_key: Asset cache key
            tags: List of tags to add

        Returns:
            True if successful, False if asset not found
        """
        if cache_key not in self.index["semantic_assets"]:
            logger.warning(f"Asset not found: {cache_key}")
            return False

        asset_entry = self.index["semantic_assets"][cache_key]
        metadata = asset_entry.get("semantic_metadata", {})

        existing_tags = set(metadata.get("tags", []))
        existing_tags.update(tags)
        metadata["tags"] = list(existing_tags)

        asset_entry["semantic_metadata"] = metadata
        self._save_index()

        logger.info(f"Tagged asset {cache_key} with: {', '.join(tags)}")
        return True

    # ========================================================================
    # INTELLIGENT ASSET DISCOVERY & MATCHING
    # ========================================================================

    def find_similar_assets(
        self,
        target_metadata: SemanticMetadata,
        asset_type: AssetType | None = None,
        min_similarity: float = 0.5,
        max_results: int = 10,
        exclude_campaigns: list[str] | None = None,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """
        Find similar assets using intelligent matching.

        Args:
            target_metadata: Target asset metadata to match against
            asset_type: Optional filter by asset type
            min_similarity: Minimum similarity threshold (0.0 to 1.0)
            max_results: Maximum number of results to return
            exclude_campaigns: Optional list of campaign IDs to exclude

        Returns:
            List of (cache_key, similarity_score, asset_entry) tuples,
            sorted by similarity (highest first)
        """
        candidates = []

        for cache_key, asset_entry in self.index["semantic_assets"].items():
            # Filter by asset type if specified
            if asset_type:
                entry_type = asset_entry.get("semantic_metadata", {}).get("asset_type")
                if entry_type != asset_type.value:
                    continue

            # Exclude specific campaigns if requested
            if exclude_campaigns:
                campaign_id = asset_entry.get("campaign_id")
                if campaign_id in exclude_campaigns:
                    continue

            # Calculate similarity
            try:
                candidate_metadata = SemanticMetadata.from_dict(asset_entry["semantic_metadata"])
                similarity = self.matcher.calculate_similarity(target_metadata, candidate_metadata)

                if similarity >= min_similarity:
                    candidates.append((cache_key, similarity, asset_entry))

            except Exception as e:
                logger.warning(f"Error calculating similarity for {cache_key}: {e}")
                continue

        # Sort by similarity (highest first) and limit results
        candidates.sort(key=lambda x: x[1], reverse=True)
        results = candidates[:max_results]

        logger.info(
            f"Found {len(results)} similar assets (threshold: {min_similarity}, "
            f"best match: {results[0][1]:.2f})"
            if results
            else "No similar assets found"
        )

        return results

    def find_backgrounds_for_product(
        self,
        product_category: ProductCategory,
        region: str,
        season: Season = Season.NONE,
        visual_style: VisualStyle | None = None,
        aspect_ratio: str | None = None,
        min_similarity: float = 0.4,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """
        Find suitable background assets for a product.

        Args:
            product_category: Product category
            region: Target region
            season: Seasonal preference
            visual_style: Visual style preference
            aspect_ratio: Optional aspect ratio filter
            min_similarity: Minimum similarity threshold

        Returns:
            List of (cache_key, similarity_score, asset_entry) tuples
        """
        # Build target metadata for background search
        target_metadata = SemanticMetadata(
            asset_type=AssetType.SCENE_BACKGROUND,
            product_category=product_category,
            region=region,
            season=season,
            visual_style=visual_style,
            aspect_ratio=aspect_ratio,
        )

        # Search for matching backgrounds
        candidates = self.find_similar_assets(
            target_metadata=target_metadata,
            asset_type=AssetType.SCENE_BACKGROUND,
            min_similarity=min_similarity,
            max_results=20,
        )

        # Filter by aspect ratio if specified
        if aspect_ratio:
            candidates = [
                (key, score, entry)
                for key, score, entry in candidates
                if entry.get("semantic_metadata", {}).get("aspect_ratio") == aspect_ratio
            ]

        logger.info(
            f"Found {len(candidates)} suitable backgrounds for {product_category.value} "
            f"in {region} (season: {season.value})"
        )

        return candidates

    def discover_cross_campaign_assets(
        self,
        campaign_id: str,
        asset_types: list[AssetType] | None = None,
    ) -> dict[str, list[tuple[str, dict[str, Any]]]]:
        """
        Discover reusable assets from other campaigns.

        Args:
            campaign_id: Current campaign ID
            asset_types: Optional filter by asset types

        Returns:
            Dictionary mapping asset type to list of (cache_key, asset_entry) tuples
        """
        discovered = defaultdict(list)

        for cache_key, asset_entry in self.index["semantic_assets"].items():
            # Skip assets from current campaign
            if asset_entry.get("campaign_id") == campaign_id:
                continue

            # Check file still exists
            file_path = Path(asset_entry.get("file_path", ""))
            if not file_path.exists():
                continue

            # Filter by asset type if specified
            asset_type_str = asset_entry.get("semantic_metadata", {}).get("asset_type")
            if asset_types:
                if not any(at.value == asset_type_str for at in asset_types):
                    continue

            discovered[asset_type_str].append((cache_key, asset_entry))

        # Log discoveries
        total = sum(len(v) for v in discovered.values())
        logger.info(f"Discovered {total} cross-campaign assets across {len(discovered)} types")

        return dict(discovered)

    # ========================================================================
    # ASSET VERSIONING & VARIANTS
    # ========================================================================

    def register_asset_version(
        self,
        asset_id: str,
        version: AssetVersion,
    ) -> None:
        """
        Register a new version of an asset.

        Args:
            asset_id: Base asset identifier
            version: AssetVersion object
        """
        if asset_id not in self.index["asset_versions"]:
            self.index["asset_versions"][asset_id] = []

        self.index["asset_versions"][asset_id].append(version.to_dict())
        self._save_index()

        logger.info(f"Registered version {version.version} for asset {asset_id}")

    def get_latest_version(self, asset_id: str) -> AssetVersion | None:
        """
        Get the latest version of an asset.

        Args:
            asset_id: Base asset identifier

        Returns:
            Latest AssetVersion or None if not found
        """
        if asset_id not in self.index["asset_versions"]:
            return None

        versions = self.index["asset_versions"][asset_id]
        if not versions:
            return None

        # Get most recent version
        latest = max(versions, key=lambda v: v.get("created_at", ""))
        return AssetVersion.from_dict(latest)

    def get_version_history(self, asset_id: str) -> list[AssetVersion]:
        """
        Get complete version history for an asset.

        Args:
            asset_id: Base asset identifier

        Returns:
            List of AssetVersion objects, sorted by creation date
        """
        if asset_id not in self.index["asset_versions"]:
            return []

        versions = [AssetVersion.from_dict(v) for v in self.index["asset_versions"][asset_id]]

        # Sort by creation date (newest first)
        versions.sort(key=lambda v: v.created_at, reverse=True)

        return versions

    def create_seasonal_variant(
        self,
        source_cache_key: str,
        new_cache_key: str,
        new_file_path: str,
        target_season: Season,
        change_notes: str | None = None,
    ) -> bool:
        """
        Create a seasonal variant of an existing asset.

        Args:
            source_cache_key: Source asset cache key
            new_cache_key: New cache key for variant
            new_file_path: Path to new seasonal variant
            target_season: Target season for variant
            change_notes: Optional notes about changes

        Returns:
            True if successful
        """
        # Get source asset
        if source_cache_key not in self.index["semantic_assets"]:
            logger.warning(f"Source asset not found: {source_cache_key}")
            return False

        source_asset = self.index["semantic_assets"][source_cache_key]
        source_metadata = SemanticMetadata.from_dict(source_asset["semantic_metadata"])

        # Create new metadata with updated season
        new_metadata = SemanticMetadata(
            asset_type=source_metadata.asset_type,
            product_category=source_metadata.product_category,
            region=source_metadata.region,
            visual_style=source_metadata.visual_style,
            season=target_season,
            color_palette=source_metadata.color_palette,
            tags=source_metadata.tags + [f"seasonal_{target_season.value}"],
            dimensions=source_metadata.dimensions,
            aspect_ratio=source_metadata.aspect_ratio,
        )

        # Register new semantic asset
        self.register_semantic_asset(
            cache_key=new_cache_key,
            file_path=new_file_path,
            metadata=new_metadata,
            campaign_id=source_asset.get("campaign_id"),
        )

        # Register version
        version = AssetVersion(
            version=f"{target_season.value}_variant",
            cache_key=new_cache_key,
            file_path=new_file_path,
            created_at=datetime.now().isoformat(),
            variant_type="seasonal",
            parent_version=source_cache_key,
            change_notes=change_notes or f"Seasonal variant for {target_season.value}",
        )

        self.register_asset_version(source_cache_key, version)

        logger.info(f"Created seasonal variant for {source_cache_key}: {target_season.value}")

        return True

    # ========================================================================
    # ADAPTIVE BACKGROUND SELECTION
    # ========================================================================

    def get_seasonal_background(
        self,
        product_category: ProductCategory,
        region: str,
        current_date: datetime | None = None,
        visual_style: VisualStyle | None = None,
    ) -> tuple[str, dict[str, Any]] | None:
        """
        Get season-appropriate background based on current date.

        Args:
            product_category: Product category
            region: Target region
            current_date: Date to determine season (defaults to now)
            visual_style: Optional visual style preference

        Returns:
            Tuple of (cache_key, asset_entry) or None if not found
        """
        if current_date is None:
            current_date = datetime.now()

        # Determine current season
        season = self._determine_season(current_date)

        # Find matching backgrounds
        backgrounds = self.find_backgrounds_for_product(
            product_category=product_category,
            region=region,
            season=season,
            visual_style=visual_style,
            min_similarity=0.4,
        )

        if backgrounds:
            # Return best match
            cache_key, similarity, asset_entry = backgrounds[0]
            logger.info(
                f"Selected seasonal background for {season.value}: "
                f"{cache_key} (similarity: {similarity:.2f})"
            )
            return (cache_key, asset_entry)

        # Fallback to season-neutral backgrounds
        logger.info(f"No {season.value} backgrounds found, using season-neutral")
        neutral_backgrounds = self.find_backgrounds_for_product(
            product_category=product_category,
            region=region,
            season=Season.NONE,
            visual_style=visual_style,
            min_similarity=0.3,
        )

        if neutral_backgrounds:
            cache_key, similarity, asset_entry = neutral_backgrounds[0]
            return (cache_key, asset_entry)

        return None

    @staticmethod
    def _determine_season(date: datetime) -> Season:
        """Determine season based on date (Northern Hemisphere)"""
        month = date.month

        # Holiday season (November-December)
        if month in [11, 12]:
            return Season.HOLIDAY

        # Winter (January-February)
        elif month in [1, 2]:
            return Season.WINTER

        # Spring (March-May)
        elif month in [3, 4, 5]:
            return Season.SPRING

        # Summer (June-August)
        elif month in [6, 7, 8]:
            return Season.SUMMER

        # Back to school (August-September)
        elif month == 9:
            return Season.BACK_TO_SCHOOL

        # Fall (October)
        elif month == 10:
            return Season.FALL

        return Season.NONE

    # ========================================================================
    # LEARNING SYSTEM FOR REUSE PATTERNS
    # ========================================================================

    def record_asset_reuse(
        self,
        source_cache_key: str,
        target_campaign: str,
        success: bool = True,
        context: str | None = None,
    ) -> None:
        """
        Record asset reuse for learning patterns.

        Args:
            source_cache_key: Asset that was reused
            target_campaign: Campaign where it was reused
            success: Whether the reuse was successful
            context: Optional context (product category, region, etc.)
        """
        pattern_key = f"{source_cache_key}_{target_campaign}"

        if pattern_key not in self.index["reuse_patterns"]:
            pattern = ReusePattern(
                source_asset=source_cache_key,
                target_campaign=target_campaign,
            )
            self.index["reuse_patterns"][pattern_key] = pattern.to_dict()
        else:
            pattern = ReusePattern.from_dict(self.index["reuse_patterns"][pattern_key])

        pattern.record_reuse(success, context)
        self.index["reuse_patterns"][pattern_key] = pattern.to_dict()

        # Update usage count on semantic asset
        if source_cache_key in self.index["semantic_assets"]:
            asset_entry = self.index["semantic_assets"][source_cache_key]
            asset_entry["usage_count"] = asset_entry.get("usage_count", 0) + 1
            asset_entry["last_used"] = datetime.now().isoformat()

            campaigns_used = asset_entry.get("campaigns_used", [])
            if target_campaign not in campaigns_used:
                campaigns_used.append(target_campaign)
            asset_entry["campaigns_used"] = campaigns_used

        self._save_index()

        logger.info(f"Recorded reuse: {source_cache_key} in {target_campaign} (success: {success})")

    def get_recommended_assets(
        self,
        target_metadata: SemanticMetadata,
        campaign_id: str,
        max_results: int = 5,
    ) -> list[tuple[str, float, dict[str, Any]]]:
        """
        Get recommended assets based on similarity and reuse patterns.

        Combines similarity scoring with historical reuse success rates
        to provide intelligent recommendations.

        Args:
            target_metadata: Target asset metadata
            campaign_id: Current campaign ID
            max_results: Maximum number of recommendations

        Returns:
            List of (cache_key, combined_score, asset_entry) tuples
        """
        # Get similar assets
        similar_assets = self.find_similar_assets(
            target_metadata=target_metadata,
            min_similarity=0.3,
            max_results=20,
            exclude_campaigns=[campaign_id],
        )

        # Enhance scores with reuse patterns
        recommendations = []

        for cache_key, similarity, asset_entry in similar_assets:
            # Check reuse patterns
            pattern_key = f"{cache_key}_{campaign_id}"
            reuse_boost = 0.0

            if pattern_key in self.index["reuse_patterns"]:
                pattern = ReusePattern.from_dict(self.index["reuse_patterns"][pattern_key])
                reuse_boost = pattern.success_rate * 0.2  # Up to 20% boost

            # Check overall usage count
            usage_count = asset_entry.get("usage_count", 0)
            usage_boost = min(usage_count * 0.02, 0.1)  # Up to 10% boost

            # Combined score
            combined_score = similarity + reuse_boost + usage_boost
            recommendations.append((cache_key, combined_score, asset_entry))

        # Sort by combined score
        recommendations.sort(key=lambda x: x[1], reverse=True)

        results = recommendations[:max_results]

        logger.info(
            f"Generated {len(results)} recommendations (best score: {results[0][1]:.2f})"
            if results
            else "No recommendations available"
        )

        return results

    def get_reuse_analytics(self, campaign_id: str | None = None) -> dict[str, Any]:
        """
        Get analytics on asset reuse patterns.

        Args:
            campaign_id: Optional filter by campaign

        Returns:
            Dictionary with reuse analytics
        """
        patterns = self.index["reuse_patterns"]

        if campaign_id:
            # Filter patterns for specific campaign
            patterns = {
                k: v for k, v in patterns.items() if v.get("target_campaign") == campaign_id
            }

        total_reuses = sum(p.get("reuse_count", 0) for p in patterns.values())
        avg_success_rate = (
            sum(p.get("success_rate", 0) for p in patterns.values()) / len(patterns)
            if patterns
            else 0.0
        )

        # Find most reused assets
        asset_usage: defaultdict[str, int] = defaultdict(int)
        for pattern in patterns.values():
            asset_usage[pattern["source_asset"]] += pattern.get("reuse_count", 0)

        most_reused = sorted(asset_usage.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_patterns": len(patterns),
            "total_reuses": total_reuses,
            "average_success_rate": round(avg_success_rate, 3),
            "most_reused_assets": [
                {"cache_key": key, "reuse_count": count} for key, count in most_reused
            ],
            "campaign_filter": campaign_id,
        }


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(
        description="Cache Manager - Intelligent Semantic Asset Reuse System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic cache operations
  python src/cache_manager.py --stats
  python src/cache_manager.py --validate

  # Semantic asset discovery
  python src/cache_manager.py --discover --campaign spring_2025
  python src/cache_manager.py --find-backgrounds --category laundry_detergent --region US

  # Asset reuse analytics
  python src/cache_manager.py --analytics
  python src/cache_manager.py --analytics --campaign spring_2025

  # Asset recommendations
  python src/cache_manager.py --recommend --category dish_soap --region LATAM --season summer
        """,
    )

    # Basic operations
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--validate", action="store_true", help="Validate cache integrity")
    parser.add_argument("--clear", action="store_true", help="Clear all cache entries")
    parser.add_argument("--cache-dir", default="cache", help="Cache directory")

    # Semantic asset operations
    parser.add_argument("--discover", action="store_true", help="Discover cross-campaign assets")
    parser.add_argument(
        "--find-backgrounds", action="store_true", help="Find suitable backgrounds for a product"
    )
    parser.add_argument(
        "--recommend", action="store_true", help="Get intelligent asset recommendations"
    )
    parser.add_argument("--analytics", action="store_true", help="Show asset reuse analytics")

    # Filters and parameters
    parser.add_argument("--campaign", help="Campaign ID filter")
    parser.add_argument(
        "--category",
        choices=[
            "laundry_detergent",
            "dish_soap",
            "hair_care",
            "oral_care",
            "personal_care",
            "general_cpg",
        ],
        help="Product category",
    )
    parser.add_argument("--region", help="Target region (US, LATAM, APAC, EMEA)")
    parser.add_argument(
        "--season",
        choices=["spring", "summer", "fall", "winter", "holiday", "back_to_school", "none"],
        help="Seasonal preference",
    )
    parser.add_argument(
        "--style",
        choices=["minimal", "vibrant", "elegant", "warm", "cool", "professional", "casual"],
        help="Visual style",
    )
    parser.add_argument("--aspect-ratio", choices=["1x1", "9x16", "16x9"], help="Aspect ratio")

    args = parser.parse_args()

    manager = CacheManager(args.cache_dir)

    if args.stats:
        stats = manager.get_cache_stats()
        print("\n" + "=" * 60)
        print("CACHE STATISTICS")
        print("=" * 60)
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print("\n  By type:")
        for cache_type, count in stats["by_type"].items():
            print(f"    - {cache_type}: {count}")
        print(f"\n  Index path: {stats['index_path']}")

        # Show semantic assets stats
        semantic_count = len(manager.index.get("semantic_assets", {}))
        version_count = len(manager.index.get("asset_versions", {}))
        pattern_count = len(manager.index.get("reuse_patterns", {}))

        print("\n  Intelligent Asset Reuse:")
        print(f"    - Semantic assets: {semantic_count}")
        print(f"    - Versioned assets: {version_count}")
        print(f"    - Reuse patterns: {pattern_count}")
        print()

    elif args.validate:
        results = manager.validate_cache()
        print("\n" + "=" * 60)
        print("CACHE VALIDATION")
        print("=" * 60)
        print(f"  Total entries: {results['total_entries']}")
        print(f"  Valid entries: {results['valid_entries']}")
        print(f"  Missing entries: {results['missing_entries']}")
        if results["missing_keys"]:
            print("\n  Missing keys:")
            for key in results["missing_keys"][:5]:
                print(f"    - {key}")
            if len(results["missing_keys"]) > 5:
                print(f"    ... and {len(results['missing_keys']) - 5} more")
        print()

    elif args.discover:
        if not args.campaign:
            print("Error: --campaign required for discovery")
            sys.exit(1)

        print(f"\nDiscovering cross-campaign assets for: {args.campaign}")
        print("=" * 60)

        discovered = manager.discover_cross_campaign_assets(args.campaign)

        if not discovered:
            print("  No cross-campaign assets found")
        else:
            for asset_type, assets in discovered.items():
                print(f"\n  {asset_type}:")
                for cache_key, asset_entry in assets[:5]:  # Show first 5
                    campaign_id = asset_entry.get("campaign_id", "unknown")
                    print(f"    - {cache_key} (from {campaign_id})")
                if len(assets) > 5:
                    print(f"    ... and {len(assets) - 5} more")
        print()

    elif args.find_backgrounds:
        if not args.category or not args.region:
            print("Error: --category and --region required for background search")
            sys.exit(1)

        category = ProductCategory(args.category)
        season = Season(args.season) if args.season else Season.NONE
        style = VisualStyle(args.style) if args.style else None

        print(f"\nFinding backgrounds for {category.value} in {args.region}")
        print("=" * 60)

        backgrounds = manager.find_backgrounds_for_product(
            product_category=category,
            region=args.region,
            season=season,
            visual_style=style,
            aspect_ratio=args.aspect_ratio,
        )

        if not backgrounds:
            print("  No matching backgrounds found")
        else:
            print(f"\n  Found {len(backgrounds)} matching backgrounds:\n")
            for cache_key, similarity, asset_entry in backgrounds[:10]:
                metadata = asset_entry.get("semantic_metadata", {})
                print(f"    {similarity:.2f} - {cache_key}")
                print(f"         Season: {metadata.get('season', 'none')}")
                print(f"         Style: {metadata.get('visual_style', 'unknown')}")
                print(f"         File: {asset_entry.get('file_path', 'unknown')}")
                print()

    elif args.recommend:
        if not args.category or not args.region:
            print("Error: --category and --region required for recommendations")
            sys.exit(1)
        if not args.campaign:
            print("Error: --campaign required for recommendations")
            sys.exit(1)

        category = ProductCategory(args.category)
        season = Season(args.season) if args.season else Season.NONE
        style = VisualStyle(args.style) if args.style else None

        # Build target metadata
        target_metadata = SemanticMetadata(
            asset_type=AssetType.SCENE_BACKGROUND,
            product_category=category,
            region=args.region,
            season=season,
            visual_style=style,
            aspect_ratio=args.aspect_ratio,
        )

        print(f"\nGetting recommendations for {category.value} in {args.region}")
        print("=" * 60)

        recommendations = manager.get_recommended_assets(
            target_metadata=target_metadata,
            campaign_id=args.campaign,
            max_results=5,
        )

        if not recommendations:
            print("  No recommendations available")
        else:
            print(f"\n  Top {len(recommendations)} recommendations:\n")
            for i, (cache_key, score, asset_entry) in enumerate(recommendations, 1):
                metadata = asset_entry.get("semantic_metadata", {})
                usage_count = asset_entry.get("usage_count", 0)
                print(f"  {i}. Score: {score:.2f} - {cache_key}")
                print(f"     Used {usage_count} times across campaigns")
                print(f"     Season: {metadata.get('season', 'none')}")
                print(f"     Style: {metadata.get('visual_style', 'unknown')}")
                print()

    elif args.analytics:
        print("\n" + "=" * 60)
        print("ASSET REUSE ANALYTICS")
        print("=" * 60)

        analytics = manager.get_reuse_analytics(campaign_id=args.campaign)

        if args.campaign:
            print(f"\nCampaign: {args.campaign}")
        else:
            print("\nAll campaigns")

        print(f"\n  Total patterns: {analytics['total_patterns']}")
        print(f"  Total reuses: {analytics['total_reuses']}")
        print(f"  Average success rate: {analytics['average_success_rate']:.1%}")

        if analytics["most_reused_assets"]:
            print("\n  Most reused assets:")
            for asset_info in analytics["most_reused_assets"][:5]:
                print(f"    - {asset_info['cache_key']}: {asset_info['reuse_count']} reuses")
        print()

    elif args.clear:
        response = input("Clear all cache entries? This cannot be undone. (yes/no): ")
        if response.lower() == "yes":
            cleared = manager.clear_cache()
            print(f"\nCleared {cleared} cache entries\n")
        else:
            print("\nCancelled\n")
            sys.exit(0)

    else:
        parser.print_help()
