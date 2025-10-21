#!/usr/bin/env python3
"""
Background Remover - AI-powered background removal with SHA-256 caching

Converts images with solid backgrounds to transparent PNGs using rembg AI segmentation.
Implements hash-based caching for performance and cost optimization.
"""
import hashlib
import json
import logging
import time
from pathlib import Path

from PIL import Image

try:
    from rembg import remove

    REMBG_AVAILABLE = True
except ImportError:
    REMBG_AVAILABLE = False

logger = logging.getLogger(__name__)


class BackgroundRemover:
    """AI-powered background removal with intelligent SHA-256 caching"""

    def __init__(self, cache_dir: str = "cache/products"):
        """
        Initialize background remover with caching.

        Args:
            cache_dir: Directory for caching product PNG assets
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not REMBG_AVAILABLE:
            logger.warning("rembg not available - background removal disabled")

        logger.info(f"BackgroundRemover initialized with cache: {self.cache_dir}")

    def remove_background(
        self,
        image: Image.Image,
        product_slug: str,
        force: bool = False,
        semantic_filename: str = None,
    ) -> tuple[Image.Image, bool, float, str]:
        """
        Remove background from image using AI segmentation.

        Args:
            image: PIL Image with solid background
            product_slug: Product identifier slug for caching
            force: Force regeneration even if cached
            semantic_filename: Optional semantic filename (e.g., 'product_transparent.png')

        Returns:
            Tuple of (product_png_image, was_cached, processing_time, cache_filename)
        """
        if not REMBG_AVAILABLE:
            logger.warning("rembg not available - returning original image")
            return image, False, 0.0, ""

        # Use semantic filename and subfolder structure if provided
        if semantic_filename:
            # Create semantic subfolder structure: cache/products/product-slug/
            product_cache_dir = self.cache_dir / product_slug
            product_cache_dir.mkdir(exist_ok=True)
            cache_filename = semantic_filename
            cached_path = product_cache_dir / cache_filename
            cache_key = "semantic"  # Use semantic key for metadata
        else:
            # Use hash-based naming in root cache directory
            cache_key = self._generate_cache_key(image, product_slug)
            cache_filename = f"{product_slug}_{cache_key}.png"
            cached_path = self.cache_dir / cache_filename

        # Check cache first
        if not force and cached_path.exists():
            logger.info(f"✓ Cache HIT: {cache_filename}")
            cached_image = Image.open(cached_path)
            return cached_image, True, 0.0, cache_filename

        logger.info(f"✗ Cache MISS: Removing background for {product_slug}")

        # Remove background
        start_time = time.time()

        try:
            # AI-powered background removal
            transparent_image = remove(image)

            # Ensure RGBA mode
            if transparent_image.mode != "RGBA":
                transparent_image = transparent_image.convert("RGBA")

            processing_time = time.time() - start_time

            # Cache result
            cache_key_for_metadata = cache_key if not semantic_filename else "semantic"
            self._cache_image(transparent_image, cached_path, product_slug, cache_key_for_metadata)

            # Return relative path for semantic files to include subfolder
            return_cache_filename = cache_filename
            if semantic_filename:
                return_cache_filename = f"{product_slug}/{cache_filename}"

            logger.info(f"✓ Background removed in {processing_time:.1f}s: {product_slug}")
            return transparent_image, False, processing_time, return_cache_filename

        except Exception as e:
            logger.error(f"Background removal failed for {product_slug}: {e}")
            # Return original image in RGBA mode as fallback
            if image.mode != "RGBA":
                image = image.convert("RGBA")
            return image, False, 0.0, ""

    def _generate_cache_key(self, image: Image.Image, product_slug: str) -> str:
        """
        Generate SHA-256 cache key from image content and product slug.

        Uses image bytes hash to ensure cache validity across different source images.
        """
        # Convert image to bytes for hashing
        img_bytes = image.tobytes()

        # Create hash from image content + product slug
        hash_input = img_bytes + product_slug.encode("utf-8")
        cache_key = hashlib.sha256(hash_input).hexdigest()[:16]

        return cache_key

    def _cache_image(
        self,
        image: Image.Image,
        cache_path: Path,
        product_slug: str,
        cache_key: str,
    ) -> None:
        """Cache product image to disk with metadata"""
        # Save as PNG with alpha channel
        image.save(cache_path, "PNG", optimize=True)

        file_size = cache_path.stat().st_size
        logger.info(f"💾 Cached: {cache_path.name} ({file_size:,} bytes)")

        # Save metadata for debugging and cache tracking
        metadata_path = cache_path.with_suffix(".json")
        metadata = {
            "product_slug": product_slug,
            "cache_key": cache_key,
            "image_size": list(image.size),
            "image_mode": image.mode,
            "file_size": file_size,
            "cached_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        png_files = list(self.cache_dir.glob("*.png"))

        total_size = sum(f.stat().st_size for f in png_files)

        return {
            "cached_assets": len(png_files),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir),
        }

    def clear_cache(self) -> int:
        """
        Clear all cached product assets.

        Returns:
            Number of files cleared
        """
        png_files = list(self.cache_dir.glob("*.png"))
        json_files = list(self.cache_dir.glob("*.json"))

        for f in png_files + json_files:
            f.unlink()

        cleared_count = len(png_files)
        logger.info(f"Cleared {cleared_count} cached product assets")
        return cleared_count


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Remove image backgrounds with caching")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("--product", "-p", required=True, help="Product slug")
    parser.add_argument("--output", "-o", help="Output path (default: test_output/transparent.png)")
    parser.add_argument("--force", "-f", action="store_true", help="Force regeneration")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")

    args = parser.parse_args()

    # Initialize remover
    remover = BackgroundRemover()

    if args.stats:
        stats = remover.get_cache_stats()
        print("\n📊 Cache Statistics:")
        print(f"  Cached assets: {stats['cached_assets']}")
        print(f"  Total size: {stats['total_size_mb']} MB")
        print(f"  Cache directory: {stats['cache_dir']}")
        import sys

        sys.exit(0)

    # Load input image
    input_image = Image.open(args.input)
    print(f"Loaded: {args.input}")
    print(f"Size: {input_image.size}, Mode: {input_image.mode}")

    # Remove background
    transparent_image, was_cached, proc_time, cache_filename = remover.remove_background(
        input_image, args.product, force=args.force
    )

    # Save output
    output_path = args.output or "test_output/transparent.png"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    transparent_image.save(output_path, "PNG")

    print(f"\n✓ Saved: {output_path}")
    print(f"  Cached: {was_cached}")
    print(f"  Processing time: {proc_time:.2f}s")
    if cache_filename:
        print(f"  Cache file: {cache_filename}")
