#!/usr/bin/env python3
"""
Enhanced Output Manager - Optimized Semantic Folder Structure

Supports both campaign-specific outputs and cross-campaign asset library
for intelligent semantic reuse based on PRD requirements.

Current Structure:  output/{product}/{template}/{region}/{ratio}/
Optimized Structure: output/campaigns/{campaign_id}/outputs/{region}/{ratio}/
                    output/library/products/{product_slug}/transparent/
                    output/library/backgrounds/seasonal/{season}/{region}/{ratio}/
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


class EnhancedOutputManager:
    """Enhanced output manager with semantic folder organization for asset reuse"""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize enhanced output manager.

        Args:
            output_dir: Base output directory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Create main structure directories
        self.campaigns_dir = self.output_dir / "campaigns"
        self.library_dir = self.output_dir / "library"
        self.cache_dir = self.output_dir / "cache"
        self.temp_dir = self.output_dir / "temp"

        # Create subdirectories
        self.campaigns_dir.mkdir(exist_ok=True)
        self.library_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)

        # Library subdirectories
        (self.library_dir / "products").mkdir(exist_ok=True)
        (self.library_dir / "backgrounds").mkdir(exist_ok=True)
        (self.library_dir / "brand-elements").mkdir(exist_ok=True)

        logger.info(f"EnhancedOutputManager initialized with directory: {self.output_dir}")

    def save_campaign_creative(
        self,
        image: Image.Image,
        campaign_id: str,
        product_name: str,
        ratio: str,
        metadata: dict,
        template: str = "hero-product",
        region: str = "us",
        variant_id: str = None,
    ) -> str:
        """
        Save campaign-specific creative with optimized folder structure.

        Args:
            image: PIL Image to save
            campaign_id: Campaign identifier (e.g., cleanwave-spring-2025)
            product_name: Product name
            ratio: Aspect ratio (1x1, 9x16, 16x9)
            metadata: Metadata dict with generation details
            template: Template type (hero-product, lifestyle, minimal)
            region: Target region (us, latam, apac, emea)
            variant_id: Variant identifier for A/B testing

        Returns:
            Path to saved creative file
        """
        # Create slugs
        campaign_slug = self._slugify(campaign_id)
        product_slug = self._slugify(product_name)
        region_slug = region.lower()

        # Campaign structure: output/campaigns/{campaign_id}/outputs/{region}/{ratio}/
        creative_dir = self.campaigns_dir / campaign_slug / "outputs" / region_slug / ratio
        creative_dir.mkdir(parents=True, exist_ok=True)

        # Filename: {product_slug}_variant_{variant_id}.jpg or {product_slug}_base.jpg
        if variant_id:
            filename = f"{product_slug}_variant_{variant_id}.jpg"
        else:
            filename = f"{product_slug}_base.jpg"

        image_path = creative_dir / filename

        # Save image
        image.save(image_path, "JPEG", quality=95, optimize=True)

        file_size = image_path.stat().st_size
        logger.info(f"💾 Saved campaign creative: {filename} ({file_size:,} bytes) -> {creative_dir}")

        # Save metadata
        enhanced_metadata = {
            **metadata,
            "campaign_id": campaign_id,
            "product_name": product_name,
            "template": template,
            "region": region,
            "variant_id": variant_id,
            "asset_type": "campaign_creative"
        }
        self._save_metadata(creative_dir, enhanced_metadata, filename)

        return str(image_path)

    def save_library_product(
        self,
        image: Image.Image,
        product_name: str,
        asset_type: str,  # "transparent", "source", "variant"
        metadata: dict,
        variant_name: Optional[str] = None
    ) -> str:
        """
        Save product asset to library for cross-campaign reuse.

        Args:
            image: PIL Image to save
            product_name: Product name
            asset_type: Type of asset (transparent, source, variant)
            metadata: Metadata dict
            variant_name: Optional variant name for different angles/lighting

        Returns:
            Path to saved library asset
        """
        product_slug = self._slugify(product_name)

        # Library structure: output/library/products/{product_slug}/{asset_type}/
        if variant_name:
            asset_dir = self.library_dir / "products" / product_slug / "variants" / variant_name
            filename = f"{product_slug}_{variant_name}.png" if asset_type == "transparent" else f"{product_slug}_{variant_name}.jpg"
        else:
            asset_dir = self.library_dir / "products" / product_slug / asset_type
            filename = f"{product_slug}_{asset_type}.png" if asset_type == "transparent" else f"{product_slug}_{asset_type}.jpg"

        asset_dir.mkdir(parents=True, exist_ok=True)
        image_path = asset_dir / filename

        # Save with appropriate format
        if asset_type == "transparent":
            image.save(image_path, "PNG", optimize=True)
        else:
            image.save(image_path, "JPEG", quality=95, optimize=True)

        file_size = image_path.stat().st_size
        logger.info(f"📚 Saved library product: {filename} ({file_size:,} bytes) -> {asset_dir}")

        # Save metadata
        enhanced_metadata = {
            **metadata,
            "product_name": product_name,
            "asset_type": f"product_{asset_type}",
            "variant_name": variant_name,
            "library_asset": True
        }
        self._save_metadata(asset_dir, enhanced_metadata, filename)

        return str(image_path)

    def save_library_background(
        self,
        image: Image.Image,
        category_type: str,  # "seasonal", "category", "neutral"
        category_value: str,  # "spring", "laundry-detergent", "minimal"
        region: str,
        ratio: str,
        metadata: dict,
        bg_name: Optional[str] = None
    ) -> str:
        """
        Save background asset to library for cross-campaign reuse.

        Args:
            image: PIL Image to save
            category_type: Type of categorization (seasonal, category, neutral)
            category_value: Specific category (spring, laundry-detergent, minimal)
            region: Target region (us, latam, apac, emea)
            ratio: Aspect ratio (1x1, 9x16, 16x9)
            metadata: Metadata dict
            bg_name: Optional background name

        Returns:
            Path to saved library background
        """
        region_slug = region.lower()
        category_slug = self._slugify(category_value)

        # Library background structure: output/library/backgrounds/{category_type}/{category_value}/{region}/{ratio}/
        if category_type == "neutral":
            # Neutral backgrounds don't need region subdivision
            bg_dir = self.library_dir / "backgrounds" / category_type / ratio
        else:
            bg_dir = self.library_dir / "backgrounds" / category_type / category_slug / region_slug / ratio

        bg_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        if bg_name:
            filename = f"{self._slugify(bg_name)}.jpg"
        else:
            # Auto-generate name based on content
            timestamp = int(time.time())
            filename = f"{category_slug}_{region_slug}_{timestamp}.jpg"

        image_path = bg_dir / filename

        # Save image
        image.save(image_path, "JPEG", quality=95, optimize=True)

        file_size = image_path.stat().st_size
        logger.info(f"🌅 Saved library background: {filename} ({file_size:,} bytes) -> {bg_dir}")

        # Save metadata
        enhanced_metadata = {
            **metadata,
            "category_type": category_type,
            "category_value": category_value,
            "region": region,
            "ratio": ratio,
            "asset_type": "library_background",
            "bg_name": bg_name
        }
        self._save_metadata(bg_dir, enhanced_metadata, filename)

        return str(image_path)

    def discover_library_products(self, product_name: Optional[str] = None) -> list:
        """
        Discover available product assets in library.

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

            product_info = {
                "product_slug": product_dir.name,
                "available_assets": {}
            }

            # Check each asset type
            for asset_type_dir in product_dir.iterdir():
                if not asset_type_dir.is_dir():
                    continue

                asset_files = []
                for asset_file in asset_type_dir.glob("*"):
                    if asset_file.suffix.lower() in ['.jpg', '.png'] and asset_file.name != 'metadata.json':
                        # Try to load metadata
                        metadata_path = asset_type_dir / "metadata.json"
                        file_metadata = {}
                        if metadata_path.exists():
                            try:
                                with open(metadata_path) as f:
                                    file_metadata = json.load(f)
                            except Exception as e:
                                logger.warning(f"Failed to load metadata for {asset_file}: {e}")

                        asset_files.append({
                            "filename": asset_file.name,
                            "path": str(asset_file),
                            "size_bytes": asset_file.stat().st_size,
                            "metadata": file_metadata
                        })

                if asset_files:
                    product_info["available_assets"][asset_type_dir.name] = asset_files

            if product_info["available_assets"]:
                available_products.append(product_info)

        return available_products

    def discover_library_backgrounds(
        self,
        category_type: Optional[str] = None,
        category_value: Optional[str] = None,
        region: Optional[str] = None,
        ratio: Optional[str] = None
    ) -> list:
        """
        Discover available background assets in library.

        Args:
            category_type: Filter by category type (seasonal, category, neutral)
            category_value: Filter by category value (spring, laundry-detergent)
            region: Filter by region (us, latam, apac, emea)
            ratio: Filter by aspect ratio (1x1, 9x16, 16x9)

        Returns:
            List of available background assets with metadata
        """
        backgrounds_dir = self.library_dir / "backgrounds"
        if not backgrounds_dir.exists():
            return []

        available_backgrounds = []

        for cat_type_dir in backgrounds_dir.iterdir():
            if not cat_type_dir.is_dir():
                continue

            # Filter by category type if specified
            if category_type and cat_type_dir.name != category_type:
                continue

            if cat_type_dir.name == "neutral":
                # Neutral structure: neutral/{ratio}/
                for ratio_dir in cat_type_dir.iterdir():
                    if not ratio_dir.is_dir():
                        continue

                    # Filter by ratio if specified
                    if ratio and ratio_dir.name != ratio:
                        continue

                    for bg_file in ratio_dir.glob("*.jpg"):
                        bg_info = self._get_background_info(bg_file, "neutral", None, None, ratio_dir.name)
                        available_backgrounds.append(bg_info)

            else:
                # Category structure: {category_type}/{category_value}/{region}/{ratio}/
                for cat_value_dir in cat_type_dir.iterdir():
                    if not cat_value_dir.is_dir():
                        continue

                    # Filter by category value if specified
                    if category_value and cat_value_dir.name != self._slugify(category_value):
                        continue

                    for region_dir in cat_value_dir.iterdir():
                        if not region_dir.is_dir():
                            continue

                        # Filter by region if specified
                        if region and region_dir.name != region.lower():
                            continue

                        for ratio_dir in region_dir.iterdir():
                            if not ratio_dir.is_dir():
                                continue

                            # Filter by ratio if specified
                            if ratio and ratio_dir.name != ratio:
                                continue

                            for bg_file in ratio_dir.glob("*.jpg"):
                                bg_info = self._get_background_info(
                                    bg_file, cat_type_dir.name, cat_value_dir.name, region_dir.name, ratio_dir.name
                                )
                                available_backgrounds.append(bg_info)

        return available_backgrounds

    def _get_background_info(self, bg_file: Path, category_type: str, category_value: Optional[str], region: Optional[str], ratio: str) -> dict:
        """Extract background asset information."""
        # Try to load metadata
        metadata_path = bg_file.parent / "metadata.json"
        file_metadata = {}
        if metadata_path.exists():
            try:
                with open(metadata_path) as f:
                    file_metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load metadata for {bg_file}: {e}")

        return {
            "filename": bg_file.name,
            "path": str(bg_file),
            "category_type": category_type,
            "category_value": category_value,
            "region": region,
            "ratio": ratio,
            "size_bytes": bg_file.stat().st_size,
            "metadata": file_metadata
        }

    def save_campaign_brief(self, campaign_id: str, brief_data: dict) -> str:
        """
        Save campaign brief to campaign directory.

        Args:
            campaign_id: Campaign identifier
            brief_data: Campaign brief dictionary

        Returns:
            Path to saved brief file
        """
        campaign_slug = self._slugify(campaign_id)
        campaign_dir = self.campaigns_dir / campaign_slug
        campaign_dir.mkdir(parents=True, exist_ok=True)

        brief_path = campaign_dir / "brief.json"
        with open(brief_path, "w") as f:
            json.dump(brief_data, f, indent=2)

        logger.info(f"📄 Saved campaign brief: {brief_path}")
        return str(brief_path)

    def get_campaign_summary(self, campaign_id: Optional[str] = None) -> dict:
        """
        Get summary of campaign outputs.

        Args:
            campaign_id: Optional campaign ID filter

        Returns:
            Dict with campaign statistics
        """
        if campaign_id:
            campaign_slug = self._slugify(campaign_id)
            campaign_dirs = [self.campaigns_dir / campaign_slug] if (self.campaigns_dir / campaign_slug).exists() else []
        else:
            campaign_dirs = [d for d in self.campaigns_dir.iterdir() if d.is_dir()]

        summary = {
            "campaigns": [],
            "total_creatives": 0,
            "total_size_bytes": 0
        }

        for campaign_dir in campaign_dirs:
            campaign_info = {
                "campaign_id": campaign_dir.name,
                "creatives": 0,
                "size_bytes": 0,
                "regions": [],
                "ratios": [],
                "brief_exists": (campaign_dir / "brief.json").exists()
            }

            outputs_dir = campaign_dir / "outputs"
            if outputs_dir.exists():
                for region_dir in outputs_dir.iterdir():
                    if not region_dir.is_dir():
                        continue

                    campaign_info["regions"].append(region_dir.name)

                    for ratio_dir in region_dir.iterdir():
                        if not ratio_dir.is_dir():
                            continue

                        if ratio_dir.name not in campaign_info["ratios"]:
                            campaign_info["ratios"].append(ratio_dir.name)

                        for creative_file in ratio_dir.glob("*.jpg"):
                            campaign_info["creatives"] += 1
                            campaign_info["size_bytes"] += creative_file.stat().st_size

            summary["campaigns"].append(campaign_info)
            summary["total_creatives"] += campaign_info["creatives"]
            summary["total_size_bytes"] += campaign_info["size_bytes"]

        summary["total_size_mb"] = round(summary["total_size_bytes"] / (1024 * 1024), 2)
        return summary

    def get_library_summary(self) -> dict:
        """
        Get summary of library assets.

        Returns:
            Dict with library statistics
        """
        summary = {
            "products": {"count": 0, "asset_types": [], "total_size_bytes": 0},
            "backgrounds": {"count": 0, "categories": [], "total_size_bytes": 0},
            "total_size_bytes": 0
        }

        # Products summary
        products_dir = self.library_dir / "products"
        if products_dir.exists():
            for product_dir in products_dir.iterdir():
                if not product_dir.is_dir():
                    continue

                summary["products"]["count"] += 1

                for asset_type_dir in product_dir.iterdir():
                    if not asset_type_dir.is_dir():
                        continue

                    if asset_type_dir.name not in summary["products"]["asset_types"]:
                        summary["products"]["asset_types"].append(asset_type_dir.name)

                    for asset_file in asset_type_dir.glob("*"):
                        if asset_file.suffix.lower() in ['.jpg', '.png']:
                            summary["products"]["total_size_bytes"] += asset_file.stat().st_size

        # Backgrounds summary
        backgrounds_dir = self.library_dir / "backgrounds"
        if backgrounds_dir.exists():
            for cat_type_dir in backgrounds_dir.iterdir():
                if not cat_type_dir.is_dir():
                    continue

                if cat_type_dir.name not in summary["backgrounds"]["categories"]:
                    summary["backgrounds"]["categories"].append(cat_type_dir.name)

                for file_path in cat_type_dir.rglob("*.jpg"):
                    summary["backgrounds"]["count"] += 1
                    summary["backgrounds"]["total_size_bytes"] += file_path.stat().st_size

        summary["total_size_bytes"] = summary["products"]["total_size_bytes"] + summary["backgrounds"]["total_size_bytes"]
        summary["total_size_mb"] = round(summary["total_size_bytes"] / (1024 * 1024), 2)

        return summary

    def _save_metadata(self, asset_dir: Path, metadata: dict, filename: str) -> None:
        """Save metadata JSON file."""
        metadata_path = asset_dir / "metadata.json"

        enhanced_metadata = {
            **metadata,
            "filename": filename,
            "directory": str(asset_dir),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Make JSON serializable
        serializable_metadata = self._make_json_serializable(enhanced_metadata)

        with open(metadata_path, "w") as f:
            json.dump(serializable_metadata, f, indent=2)

        logger.debug(f"Saved metadata: {metadata_path}")

    def _slugify(self, text: str) -> str:
        """Convert text to URL-safe slug."""
        slug = text.lower()
        slug = slug.replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        while "--" in slug:
            slug = slug.replace("--", "-")

        return slug.strip("-")

    def _make_json_serializable(self, obj):
        """Recursively convert objects to JSON serializable format."""
        if isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, (bool, int, float, str, type(None))):
            return obj
        elif hasattr(obj, "__dict__"):
            return str(obj)
        else:
            return str(obj)


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Enhanced output manager utilities")
    parser.add_argument("--campaign-summary", metavar="CAMPAIGN_ID", help="Show campaign summary")
    parser.add_argument("--library-summary", action="store_true", help="Show library summary")
    parser.add_argument("--discover-products", metavar="PRODUCT_NAME", nargs="?", const="", help="Discover library products")
    parser.add_argument("--discover-backgrounds", action="store_true", help="Discover library backgrounds")
    parser.add_argument("--output-dir", default="output", help="Output directory to analyze")

    args = parser.parse_args()

    manager = EnhancedOutputManager(args.output_dir)

    if args.campaign_summary:
        summary = manager.get_campaign_summary(args.campaign_summary if args.campaign_summary != "" else None)
        print("\n📊 Campaign Summary:")
        for campaign in summary["campaigns"]:
            print(f"  Campaign: {campaign['campaign_id']}")
            print(f"    Creatives: {campaign['creatives']}")
            print(f"    Regions: {', '.join(campaign['regions'])}")
            print(f"    Ratios: {', '.join(campaign['ratios'])}")
            print(f"    Brief: {'✓' if campaign['brief_exists'] else '✗'}")
        print(f"  Total: {summary['total_creatives']} creatives, {summary['total_size_mb']} MB")

    elif args.library_summary:
        summary = manager.get_library_summary()
        print("\n📚 Library Summary:")
        print(f"  Products: {summary['products']['count']} ({', '.join(summary['products']['asset_types'])})")
        print(f"  Backgrounds: {summary['backgrounds']['count']} ({', '.join(summary['backgrounds']['categories'])})")
        print(f"  Total: {summary['total_size_mb']} MB")

    elif args.discover_products is not None:
        products = manager.discover_library_products(args.discover_products or None)
        print(f"\n🔍 Library Products:")
        for product in products:
            print(f"  Product: {product['product_slug']}")
            for asset_type, assets in product['available_assets'].items():
                print(f"    {asset_type}: {len(assets)} assets")

    elif args.discover_backgrounds:
        backgrounds = manager.discover_library_backgrounds()
        print(f"\n🌅 Library Backgrounds: {len(backgrounds)} total")
        by_category = {}
        for bg in backgrounds:
            key = f"{bg['category_type']}/{bg['category_value'] or 'neutral'}"
            if key not in by_category:
                by_category[key] = 0
            by_category[key] += 1

        for category, count in by_category.items():
            print(f"  {category}: {count} backgrounds")

    else:
        print("Use --campaign-summary, --library-summary, --discover-products, or --discover-backgrounds")