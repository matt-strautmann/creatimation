"""
Unified Output Manager for Creative Automation Pipeline.

Consolidates all output management functionality into a single,
well-designed class that handles both basic and enhanced output operations.
"""
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

try:
    from ..core.interfaces import OutputManagerInterface
except ImportError:
    # Fallback for direct execution
    from src.core.interfaces import OutputManagerInterface

logger = logging.getLogger(__name__)


class UnifiedOutputManager(OutputManagerInterface):
    """
    Unified output manager for creative assets.

    Consolidates functionality from:
    - OutputManager (basic file operations)
    - EnhancedOutputManager (semantic structure)
    """

    def __init__(self, output_dir: str = "output", use_semantic_structure: bool = True):
        """Initialize unified output manager."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_semantic_structure = use_semantic_structure

        # Create library structure for asset reuse
        if use_semantic_structure:
            self.library_dir = self.output_dir / "library"
            self.campaigns_dir = self.output_dir / "campaigns"

            self.library_dir.mkdir(exist_ok=True)
            self.campaigns_dir.mkdir(exist_ok=True)
            (self.library_dir / "products").mkdir(exist_ok=True)
            (self.library_dir / "backgrounds").mkdir(exist_ok=True)

    def save_creative(
        self,
        image: Image.Image,
        product_name: str,
        ratio: str,
        metadata: Dict[str, Any],
        template: str,
        region: str,
        variant_id: Optional[str] = None
    ) -> str:
        """Save creative with appropriate structure and metadata."""
        if self.use_semantic_structure:
            return self._save_semantic_creative(
                image, product_name, ratio, metadata, template, region, variant_id
            )
        else:
            return self._save_basic_creative(
                image, product_name, ratio, metadata, template, region, variant_id
            )

    def get_output_path(
        self,
        product_name: str,
        template: str,
        region: str,
        ratio: str
    ) -> Path:
        """Get standardized output path."""
        product_slug = self._slugify(product_name)
        template_slug = self._slugify(template)
        region_slug = region.lower()

        if self.use_semantic_structure:
            # Semantic structure: campaigns/{campaign}/products/{product}/outputs/{region}/{ratio}
            # For now, use product as campaign (can be enhanced with campaign_id)
            return self.campaigns_dir / product_slug / "outputs" / region_slug / ratio
        else:
            # Basic structure: {product}/{template}/{region}/{ratio}
            return self.output_dir / product_slug / template_slug / region_slug / ratio

    # ========================================================================
    # SEMANTIC STRUCTURE OPERATIONS
    # ========================================================================

    def _save_semantic_creative(
        self,
        image: Image.Image,
        product_name: str,
        ratio: str,
        metadata: Dict[str, Any],
        template: str,
        region: str,
        variant_id: Optional[str] = None
    ) -> str:
        """Save creative using semantic folder structure."""
        campaign_id = metadata.get("campaign_id", "default_campaign")
        product_slug = self._slugify(product_name)
        region_slug = region.lower()

        # Create semantic directory structure
        output_path = self.campaigns_dir / campaign_id / "outputs" / region_slug / ratio
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate semantic filename
        if variant_id:
            filename = f"{product_slug}_{template}_{region_slug}_{ratio}_{variant_id}_creative.jpg"
        else:
            filename = f"{product_slug}_{template}_{region_slug}_{ratio}_creative.jpg"

        image_path = output_path / filename

        # Save image with high quality
        image.save(image_path, "JPEG", quality=95, optimize=True)

        # Save variant-specific metadata
        self._save_semantic_metadata(output_path, metadata, filename, variant_id)

        file_size = image_path.stat().st_size
        logger.info(f"💾 Saved semantic creative: {filename} ({file_size:,} bytes) -> {output_path}")

        return str(image_path)

    def _save_semantic_metadata(
        self,
        output_path: Path,
        metadata: Dict[str, Any],
        filename: str,
        variant_id: Optional[str] = None
    ) -> None:
        """Save metadata with semantic naming."""
        # Include variant_id in metadata filename to prevent overwriting
        if variant_id:
            metadata_filename = f"metadata_{variant_id}.json"
        else:
            metadata_filename = "metadata.json"

        metadata_path = output_path / metadata_filename

        # Enhance metadata with output information
        enhanced_metadata = {
            **metadata,
            "output_filename": filename,
            "output_directory": str(output_path),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "output_structure": "semantic"
        }

        # Save metadata
        try:
            with open(metadata_path, 'w') as f:
                json.dump(enhanced_metadata, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save metadata: {e}")

    # ========================================================================
    # BASIC STRUCTURE OPERATIONS
    # ========================================================================

    def _save_basic_creative(
        self,
        image: Image.Image,
        product_name: str,
        ratio: str,
        metadata: Dict[str, Any],
        template: str,
        region: str,
        variant_id: Optional[str] = None
    ) -> str:
        """Save creative using basic folder structure."""
        product_slug = self._slugify(product_name)
        template_slug = self._slugify(template)
        region_slug = region.lower()

        # Create basic directory structure
        creative_dir = self.output_dir / product_slug / template_slug / region_slug / ratio
        creative_dir.mkdir(parents=True, exist_ok=True)

        # Generate basic filename
        if variant_id:
            filename = f"{product_slug}_{template_slug}_{region_slug}_{ratio}_{variant_id}_creative.jpg"
        else:
            filename = f"{product_slug}_{template_slug}_{region_slug}_{ratio}_creative.jpg"

        image_path = creative_dir / filename

        # Save image
        image.save(image_path, "JPEG", quality=95, optimize=True)

        # Enhance metadata with output information
        enhanced_metadata = {
            **metadata,
            "template": template,
            "template_slug": template_slug,
            "region_slug": region_slug,
        }

        # Save basic metadata
        self._save_basic_metadata(creative_dir, enhanced_metadata, filename, variant_id)

        file_size = image_path.stat().st_size
        logger.info(f"💾 Saved basic creative: {filename} ({file_size:,} bytes) -> {creative_dir}")

        return str(image_path)

    def _save_basic_metadata(
        self,
        creative_dir: Path,
        metadata: Dict[str, Any],
        filename: str,
        variant_id: Optional[str] = None
    ) -> None:
        """Save metadata with basic naming."""
        # Include variant_id in metadata filename to prevent overwriting
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
            "output_structure": "basic"
        }

        # Save metadata
        try:
            with open(metadata_path, 'w') as f:
                json.dump(enhanced_metadata, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to save metadata: {e}")

    # ========================================================================
    # LIBRARY MANAGEMENT (Semantic Structure Only)
    # ========================================================================

    def save_library_asset(
        self,
        image: Image.Image,
        asset_type: str,
        product_name: Optional[str] = None,
        category: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save asset to library for cross-campaign reuse."""
        if not self.use_semantic_structure:
            raise NotImplementedError("Library assets require semantic structure")

        if asset_type == "product" and product_name:
            return self._save_library_product(image, product_name, metadata)
        elif asset_type == "background":
            return self._save_library_background(image, category, metadata)
        else:
            raise ValueError(f"Unsupported asset type: {asset_type}")

    def _save_library_product(
        self,
        image: Image.Image,
        product_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save product to library."""
        product_slug = self._slugify(product_name)
        product_dir = self.library_dir / "products" / product_slug / "transparent"
        product_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{product_slug}_transparent.png"
        image_path = product_dir / filename

        # Save as PNG for transparency
        image.save(image_path, "PNG", optimize=True)

        # Save metadata
        if metadata:
            metadata_path = product_dir / "metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        logger.info(f"💾 Saved library product: {filename}")
        return str(image_path)

    def _save_library_background(
        self,
        image: Image.Image,
        category: Optional[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Save background to library."""
        if category:
            bg_dir = self.library_dir / "backgrounds" / "category" / category
        else:
            bg_dir = self.library_dir / "backgrounds" / "neutral"

        bg_dir.mkdir(parents=True, exist_ok=True)

        timestamp = int(time.time())
        filename = f"background_{timestamp}.jpg"
        image_path = bg_dir / filename

        # Save as JPEG
        image.save(image_path, "JPEG", quality=95, optimize=True)

        # Save metadata
        if metadata:
            metadata_path = bg_dir / f"metadata_{timestamp}.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

        logger.info(f"💾 Saved library background: {filename}")
        return str(image_path)

    # ========================================================================
    # STATISTICS AND UTILITIES
    # ========================================================================

    def get_output_stats(self) -> Dict[str, Any]:
        """Get comprehensive output statistics."""
        total_files = 0
        total_size = 0
        file_types = {}

        for file_path in self.output_dir.rglob("*"):
            if file_path.is_file():
                total_files += 1
                total_size += file_path.stat().st_size

                ext = file_path.suffix.lower()
                file_types[ext] = file_types.get(ext, 0) + 1

        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "file_types": file_types,
            "output_directory": str(self.output_dir),
            "semantic_structure": self.use_semantic_structure
        }

    def cleanup_empty_directories(self) -> int:
        """Remove empty directories from output."""
        removed_count = 0

        # Walk bottom-up to remove nested empty directories
        for dir_path in sorted(self.output_dir.rglob("*"), reverse=True):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()
                removed_count += 1

        return removed_count

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


# Legacy compatibility aliases
OutputManager = UnifiedOutputManager
EnhancedOutputManager = UnifiedOutputManager