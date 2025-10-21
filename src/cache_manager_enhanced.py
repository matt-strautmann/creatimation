#!/usr/bin/env python3
"""
Enhanced Cache Manager - Integration with Optimized Folder Structure

Extends the semantic cache manager to work with the optimized local folder structure:
- Campaign-specific asset discovery
- Library asset reuse for cross-campaign optimization
- Path construction for optimized structure
"""
import os
from pathlib import Path
from typing import List, Optional

from cache_manager import CacheManager, SemanticMetadata, AssetType, Season, ProductCategory


class EnhancedCacheManager(CacheManager):
    """Enhanced cache manager with optimized folder structure integration."""

    def __init__(self, cache_dir: str = "cache", output_dir: str = "output"):
        """
        Initialize enhanced cache manager.

        Args:
            cache_dir: Cache directory for asset storage
            output_dir: Output directory with optimized structure
        """
        super().__init__(cache_dir)
        self.output_dir = Path(output_dir)

        # Optimized structure directories
        self.campaigns_dir = self.output_dir / "campaigns"
        self.library_dir = self.output_dir / "library"

        # Ensure directories exist
        self.campaigns_dir.mkdir(parents=True, exist_ok=True)
        self.library_dir.mkdir(parents=True, exist_ok=True)
        (self.library_dir / "products").mkdir(exist_ok=True)
        (self.library_dir / "backgrounds").mkdir(exist_ok=True)

    def construct_optimized_path(
        self,
        semantic_metadata: SemanticMetadata,
        campaign_id: Optional[str] = None,
        region: str = "us",
        filename: str = "asset.jpg"
    ) -> str:
        """
        Construct path using optimized folder structure.

        Args:
            semantic_metadata: Asset semantic metadata
            campaign_id: Optional campaign ID for campaign-specific assets
            region: Target region
            filename: Asset filename

        Returns:
            Optimized folder path
        """
        if campaign_id:
            # Campaign-specific asset
            campaign_slug = self._slugify(campaign_id)

            if semantic_metadata.asset_type == AssetType.PRODUCT_TRANSPARENT:
                product_slug = self._slugify(semantic_metadata.product_name or "product")
                return str(self.campaigns_dir / campaign_slug / "products" / product_slug / "transparent" / filename)

            elif semantic_metadata.asset_type == AssetType.SCENE_BACKGROUND:
                aspect_ratio = semantic_metadata.aspect_ratio or "1x1"
                return str(self.campaigns_dir / campaign_slug / "backgrounds" / region / aspect_ratio / filename)

            elif semantic_metadata.asset_type == AssetType.COMPOSITE:
                aspect_ratio = semantic_metadata.aspect_ratio or "1x1"
                return str(self.campaigns_dir / campaign_slug / "outputs" / region / aspect_ratio / filename)

        else:
            # Library asset for reuse
            if semantic_metadata.asset_type == AssetType.PRODUCT_TRANSPARENT:
                product_slug = self._slugify(semantic_metadata.product_name or "product")
                return str(self.library_dir / "products" / product_slug / "transparent" / filename)

            elif semantic_metadata.asset_type == AssetType.SCENE_BACKGROUND:
                aspect_ratio = semantic_metadata.aspect_ratio or "1x1"

                if semantic_metadata.season and semantic_metadata.season != Season.NONE:
                    # Seasonal background
                    season = semantic_metadata.season.value
                    return str(self.library_dir / "backgrounds" / "seasonal" / season / region / aspect_ratio / filename)

                elif semantic_metadata.product_category:
                    # Category-specific background
                    category = semantic_metadata.product_category.value
                    return str(self.library_dir / "backgrounds" / "category" / category / region / aspect_ratio / filename)

                else:
                    # Neutral background
                    return str(self.library_dir / "backgrounds" / "neutral" / aspect_ratio / filename)

        raise ValueError(f"Cannot construct optimized path for asset type: {semantic_metadata.asset_type}")

    def discover_library_products(self, product_name: Optional[str] = None) -> List[dict]:
        """
        Discover available product assets in library for reuse.

        Args:
            product_name: Optional product name filter

        Returns:
            List of available product assets with metadata
        """
        products_dir = self.library_dir / "products"
        if not products_dir.exists():
            return []

        available_products = []

        for product_dir in products_dir.iterdir():
            if not product_dir.is_dir():
                continue

            # Filter by product name if specified
            if product_name and self._slugify(product_name) != product_dir.name:
                continue

            # Check for transparent assets (most valuable for reuse)
            transparent_dir = product_dir / "transparent"
            if transparent_dir.exists():
                for asset_file in transparent_dir.glob("*.png"):
                    if asset_file.name != 'metadata.json':
                        available_products.append({
                            "product_slug": product_dir.name,
                            "asset_type": "transparent",
                            "path": str(asset_file),
                            "filename": asset_file.name,
                            "size_bytes": asset_file.stat().st_size
                        })

            # Check for source assets
            source_dir = product_dir / "source"
            if source_dir.exists():
                for asset_file in source_dir.glob("*.jpg"):
                    if asset_file.name != 'metadata.json':
                        available_products.append({
                            "product_slug": product_dir.name,
                            "asset_type": "source",
                            "path": str(asset_file),
                            "filename": asset_file.name,
                            "size_bytes": asset_file.stat().st_size
                        })

        return available_products

    def discover_library_backgrounds(
        self,
        product_category: Optional[ProductCategory] = None,
        region: str = "us",
        season: Optional[Season] = None,
        aspect_ratio: str = "1x1"
    ) -> List[dict]:
        """
        Discover available background assets in library for reuse.

        Args:
            product_category: Filter by product category
            region: Target region
            season: Filter by season
            aspect_ratio: Target aspect ratio

        Returns:
            List of available background assets with metadata
        """
        backgrounds_dir = self.library_dir / "backgrounds"
        if not backgrounds_dir.exists():
            return []

        available_backgrounds = []
        search_paths = []

        # 1. Seasonal backgrounds (if season specified)
        if season and season != Season.NONE:
            seasonal_path = backgrounds_dir / "seasonal" / season.value / region / aspect_ratio
            search_paths.append(("seasonal", seasonal_path, season.value))

        # 2. Category-specific backgrounds (if category specified)
        if product_category:
            category_path = backgrounds_dir / "category" / product_category.value / region / aspect_ratio
            search_paths.append(("category", category_path, product_category.value))

        # 3. Neutral backgrounds (always check as fallback)
        neutral_path = backgrounds_dir / "neutral" / aspect_ratio
        search_paths.append(("neutral", neutral_path, None))

        for category_type, path, category_value in search_paths:
            if path.exists():
                for bg_file in path.glob("*.jpg"):
                    if bg_file.name != 'metadata.json':
                        available_backgrounds.append({
                            "category_type": category_type,
                            "category_value": category_value,
                            "region": region,
                            "aspect_ratio": aspect_ratio,
                            "path": str(bg_file),
                            "filename": bg_file.name,
                            "size_bytes": bg_file.stat().st_size
                        })

        return available_backgrounds

    def register_optimized_asset(
        self,
        file_path: str,
        semantic_metadata: SemanticMetadata,
        campaign_id: Optional[str] = None,
        is_library_asset: bool = False
    ) -> str:
        """
        Register asset in both cache and optimized folder structure.

        Args:
            file_path: Path to asset file
            semantic_metadata: Asset semantic metadata
            campaign_id: Campaign ID for campaign-specific assets
            is_library_asset: Whether to store in library for reuse

        Returns:
            Cache key for the registered asset
        """
        # Generate cache key and register in cache system
        cache_key = self._generate_cache_key(file_path)

        # Register in semantic cache
        self.register_semantic_asset(
            cache_key=cache_key,
            file_path=file_path,
            metadata=semantic_metadata,
            campaign_id=campaign_id
        )

        # If it's a library asset, also track for cross-campaign reuse
        if is_library_asset:
            self._add_to_library_index(cache_key, semantic_metadata, file_path)

        return cache_key

    def get_reusable_asset(
        self,
        semantic_metadata: SemanticMetadata,
        campaign_id: Optional[str] = None,
        region: str = "us"
    ) -> Optional[dict]:
        """
        Find reusable asset from library or cache based on semantic matching.

        Args:
            semantic_metadata: Required asset characteristics
            campaign_id: Current campaign ID
            region: Target region

        Returns:
            Reusable asset info or None if not found
        """
        # First, try semantic cache discovery
        matches = self.discover_semantic_assets(
            asset_type=semantic_metadata.asset_type,
            product_category=semantic_metadata.product_category,
            region=region,
            season=semantic_metadata.season,
            visual_style=semantic_metadata.visual_style,
            aspect_ratio=semantic_metadata.aspect_ratio
        )

        if matches:
            # Return best match from cache
            best_match = max(matches, key=lambda x: x.get('similarity_score', 0))
            return {
                "cache_key": best_match['cache_key'],
                "file_path": best_match['file_path'],
                "source": "cache",
                "similarity_score": best_match.get('similarity_score', 0)
            }

        # If no cache match, try library discovery
        if semantic_metadata.asset_type == AssetType.PRODUCT_TRANSPARENT:
            library_products = self.discover_library_products(semantic_metadata.product_name)
            if library_products:
                return {
                    "file_path": library_products[0]['path'],
                    "source": "library",
                    "asset_type": "product_transparent"
                }

        elif semantic_metadata.asset_type == AssetType.SCENE_BACKGROUND:
            library_backgrounds = self.discover_library_backgrounds(
                product_category=semantic_metadata.product_category,
                region=region,
                season=semantic_metadata.season,
                aspect_ratio=semantic_metadata.aspect_ratio
            )
            if library_backgrounds:
                return {
                    "file_path": library_backgrounds[0]['path'],
                    "source": "library",
                    "asset_type": "scene_background"
                }

        return None

    def _add_to_library_index(self, cache_key: str, metadata: SemanticMetadata, file_path: str):
        """Add asset to library index for cross-campaign discovery."""
        if "library_index" not in self.index:
            self.index["library_index"] = {}

        self.index["library_index"][cache_key] = {
            "file_path": file_path,
            "asset_type": metadata.asset_type.value,
            "product_category": metadata.product_category.value if metadata.product_category else None,
            "season": metadata.season.value if metadata.season else None,
            "region": metadata.region,
            "added_at": self._get_timestamp()
        }
        self._save_index()

    def get_library_stats(self) -> dict:
        """
        Get statistics about library assets for reuse optimization.

        Returns:
            Library statistics
        """
        stats = {
            "total_products": 0,
            "total_backgrounds": 0,
            "reuse_potential": 0,
            "disk_usage_mb": 0
        }

        # Count library products
        products_dir = self.library_dir / "products"
        if products_dir.exists():
            for product_dir in products_dir.iterdir():
                if product_dir.is_dir():
                    stats["total_products"] += 1
                    for asset_file in product_dir.rglob("*"):
                        if asset_file.is_file() and asset_file.suffix.lower() in ['.jpg', '.png']:
                            stats["disk_usage_mb"] += asset_file.stat().st_size / (1024 * 1024)

        # Count library backgrounds
        backgrounds_dir = self.library_dir / "backgrounds"
        if backgrounds_dir.exists():
            for bg_file in backgrounds_dir.rglob("*.jpg"):
                stats["total_backgrounds"] += 1
                stats["disk_usage_mb"] += bg_file.stat().st_size / (1024 * 1024)

        # Calculate reuse potential (assets that could be reused)
        if "library_index" in self.index:
            stats["reuse_potential"] = len(self.index["library_index"])

        stats["disk_usage_mb"] = round(stats["disk_usage_mb"], 2)
        return stats

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        if not text:
            return "unknown"

        slug = text.lower()
        slug = slug.replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        while "--" in slug:
            slug = slug.replace("--", "-")

        return slug.strip("-")


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse
    import logging

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Enhanced cache manager with optimized structure")
    parser.add_argument("--discover-products", action="store_true", help="Discover library products")
    parser.add_argument("--discover-backgrounds", action="store_true", help="Discover library backgrounds")
    parser.add_argument("--library-stats", action="store_true", help="Show library statistics")
    parser.add_argument("--product-name", help="Filter products by name")
    parser.add_argument("--region", default="us", help="Target region")
    parser.add_argument("--aspect-ratio", default="1x1", help="Target aspect ratio")
    parser.add_argument("--cache-dir", default="cache", help="Cache directory")
    parser.add_argument("--output-dir", default="output", help="Output directory")

    args = parser.parse_args()

    manager = EnhancedCacheManager(args.cache_dir, args.output_dir)

    if args.discover_products:
        products = manager.discover_library_products(args.product_name)
        print(f"\n📦 Library Products: {len(products)} found")
        for product in products[:10]:  # Show first 10
            print(f"  {product['product_slug']}: {product['asset_type']} ({product['size_bytes']:,} bytes)")

    elif args.discover_backgrounds:
        backgrounds = manager.discover_library_backgrounds(
            region=args.region,
            aspect_ratio=args.aspect_ratio
        )
        print(f"\n🌅 Library Backgrounds: {len(backgrounds)} found")
        for bg in backgrounds[:10]:  # Show first 10
            print(f"  {bg['category_type']}/{bg['category_value']}: {bg['filename']} ({bg['size_bytes']:,} bytes)")

    elif args.library_stats:
        stats = manager.get_library_stats()
        print("\n📊 Library Statistics:")
        print(f"  Products: {stats['total_products']}")
        print(f"  Backgrounds: {stats['total_backgrounds']}")
        print(f"  Reuse potential: {stats['reuse_potential']} assets")
        print(f"  Disk usage: {stats['disk_usage_mb']} MB")

    else:
        print("Use --discover-products, --discover-backgrounds, or --library-stats")