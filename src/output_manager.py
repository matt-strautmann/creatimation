#!/usr/bin/env python3
"""
Output Manager - Semantic file naming and metadata generation

Manages organized output structure with semantic naming conventions
(ecowash-detergent_1x1_creative.jpg) and comprehensive metadata tracking.
"""

import json
import logging
import time
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


class OutputManager:
    """Manages semantic file naming and organized output structure"""

    def __init__(self, output_dir: str = "output"):
        """
        Initialize output manager.

        Args:
            output_dir: Base output directory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        logger.info(f"OutputManager initialized with directory: {self.output_dir}")

    def save_creative(
        self,
        image: Image.Image,
        product_name: str,
        ratio: str,
        metadata: dict,
        template: str = "hero-product",
        region: str = "US",
        variant_id: str = None,
    ) -> str:
        """
        Save creative with regional semantic naming and metadata.

        Args:
            image: PIL Image to save
            product_name: Product name
            ratio: Aspect ratio (1x1, 9x16, 16x9)
            metadata: Metadata dict with generation details
            template: Template type (hero-product, lifestyle, minimal, etc.)
            region: Target region (LATAM, APAC, EMEA, US)
            variant_id: Variant identifier for A/B testing (optional)

        Returns:
            Path to saved creative file
        """
        # Create slugs for directory and filename components
        product_slug = self._slugify(product_name)
        template_slug = self._slugify(template)
        region_slug = region.lower()

        # Regional semantic directory structure: output/{product}/{template}/{region}/{ratio}/
        creative_dir = self.output_dir / product_slug / template_slug / region_slug / ratio
        creative_dir.mkdir(parents=True, exist_ok=True)

        # Regional semantic filename: {product}_{template}_{region}_{ratio}_{variant}_creative.jpg
        if variant_id:
            filename = (
                f"{product_slug}_{template_slug}_{region_slug}_{ratio}_{variant_id}_creative.jpg"
            )
        else:
            filename = f"{product_slug}_{template_slug}_{region_slug}_{ratio}_creative.jpg"
        image_path = creative_dir / filename

        # Save image
        image.save(image_path, "JPEG", quality=95, optimize=True)

        file_size = image_path.stat().st_size
        logger.info(f"💾 Saved creative: {filename} ({file_size:,} bytes) -> {creative_dir}")

        # Save metadata with regional semantic information
        enhanced_metadata = {
            **metadata,
            "template": template,
            "region": region,
            "template_slug": template_slug,
            "region_slug": region_slug,
        }
        self._save_metadata(creative_dir, enhanced_metadata, filename)

        return str(image_path)

    def _save_metadata(self, creative_dir: Path, metadata: dict, filename: str) -> None:
        """
        Save metadata JSON with cache lineage and generation details.

        Args:
            creative_dir: Directory to save metadata in
            metadata: Metadata dict
            filename: Creative filename for reference
        """
        # Include variant_id in metadata filename to prevent overwriting
        variant_id = metadata.get("variant_id")
        if variant_id:
            metadata_filename = f"metadata_{variant_id}.json"
        else:
            metadata_filename = "metadata.json"

        metadata_path = creative_dir / metadata_filename

        # Enhance metadata with output information
        enhanced_metadata = {
            **metadata,
            "output_filename": filename,
            "output_directory": str(creative_dir),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # Make JSON serializable
        serializable_metadata = self._make_json_serializable(enhanced_metadata)

        with open(metadata_path, "w") as f:
            json.dump(serializable_metadata, f, indent=2)

        logger.debug(f"Saved metadata: {metadata_path}")

    def _slugify(self, text: str) -> str:
        """
        Convert text to URL-safe slug.

        Args:
            text: Text to slugify

        Returns:
            Lowercase, hyphenated slug
        """
        # Convert to lowercase and replace spaces/underscores with hyphens
        slug = text.lower()
        slug = slug.replace(" ", "-").replace("_", "-")

        # Remove any non-alphanumeric characters except hyphens
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        # Remove duplicate hyphens
        while "--" in slug:
            slug = slug.replace("--", "-")

        # Strip leading/trailing hyphens
        slug = slug.strip("-")

        return slug

    def _make_json_serializable(self, obj):
        """Recursively convert objects to JSON serializable format"""
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

    def get_output_summary(self) -> dict:
        """
        Get summary of generated outputs.

        Returns:
            Dict with output statistics
        """
        total_files = 0
        total_size = 0
        products = []

        for product_dir in self.output_dir.iterdir():
            if product_dir.is_dir():
                products.append(product_dir.name)
                # Recursively find all .jpg files in the directory tree
                for file in product_dir.rglob("*.jpg"):
                    total_files += 1
                    total_size += file.stat().st_size

        return {
            "total_creatives": total_files,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "products": products,
            "output_dir": str(self.output_dir),
        }


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Output manager utilities")
    parser.add_argument("--summary", action="store_true", help="Show output directory summary")
    parser.add_argument("--output-dir", default="output", help="Output directory to analyze")

    args = parser.parse_args()

    manager = OutputManager(args.output_dir)

    if args.summary:
        summary = manager.get_output_summary()
        print("\n📊 Output Summary:")
        print(f"  Total creatives: {summary['total_creatives']}")
        print(f"  Total size: {summary['total_size_mb']} MB")
        print(f"  Products: {', '.join(summary['products']) if summary['products'] else 'None'}")
        print(f"  Output directory: {summary['output_dir']}")
    else:
        print("Use --summary to see output directory statistics")
