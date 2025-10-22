#!/usr/bin/env python3
"""
Creative Compositor - Aspect-ratio-aware product+scene composition

Combines transparent product PNGs with scene backgrounds using smart positioning,
hero-sized scaling (70-80%), and realistic drop shadows.
"""

import logging

from PIL import Image, ImageFilter

logger = logging.getLogger(__name__)


class CreativeCompositor:
    """Intelligently composite product assets onto scene backgrounds"""

    # Composition presets for different aspect ratios
    COMPOSITION_RULES = {
        "1x1": {
            "product_scale": 0.70,  # Product takes 70% of frame (hero-sized)
            "position": (0.5, 0.5),  # Centered (x, y as percentage)
            "anchor": "center",
        },
        "9x16": {
            "product_scale": 0.60,  # Smaller for vertical (text space below)
            "position": (0.5, 0.35),  # Upper-center for text space below
            "anchor": "center",
        },
        "16x9": {
            "product_scale": 0.55,  # Smaller for horizontal
            "position": (0.35, 0.5),  # Left-of-center for balance
            "anchor": "center",
        },
    }

    def __init__(self):
        """Initialize compositor"""
        logger.info("CreativeCompositor initialized")

    def composite(
        self,
        product_png: Image.Image,
        scene_background: Image.Image,
        ratio: str = "1x1",
        target_size: tuple[int, int] | None = None,
    ) -> Image.Image:
        """
        Composite transparent product onto scene background.

        Args:
            product_png: Transparent product PNG (RGBA)
            scene_background: Scene background image (RGB)
            ratio: Aspect ratio for composition rules (1x1, 9x16, 16x9)
            target_size: Optional final output size (width, height)

        Returns:
            Composited creative image (RGB)
        """
        # Get composition rules for ratio
        rules = self.COMPOSITION_RULES.get(ratio, self.COMPOSITION_RULES["1x1"])

        # Ensure product has alpha channel
        if product_png.mode != "RGBA":
            product_png = product_png.convert("RGBA")

        # Ensure background is RGB
        if scene_background.mode != "RGB":
            scene_background = scene_background.convert("RGB")

        # Resize background to target size if specified
        if target_size:
            scene_background = scene_background.resize(target_size, Image.Resampling.LANCZOS)

        # Calculate product size based on composition rules (hero-sized: 70-80%)
        bg_width, bg_height = scene_background.size
        product_width = int(bg_width * rules["product_scale"])

        # Maintain product aspect ratio
        product_aspect = product_png.width / product_png.height
        product_height = int(product_width / product_aspect)

        # Resize product
        resized_product = product_png.resize(
            (product_width, product_height), Image.Resampling.LANCZOS
        )

        # Calculate position (centered or offset based on rules)
        position_x = int(bg_width * rules["position"][0] - product_width / 2)
        position_y = int(bg_height * rules["position"][1] - product_height / 2)

        # Create shadow layer for realism
        shadow = self._create_shadow(resized_product, offset=(8, 8), blur_radius=15)

        # Composite: background + shadow + product
        result = scene_background.copy()
        result = Image.alpha_composite(
            result.convert("RGBA"), Image.new("RGBA", result.size, (0, 0, 0, 0))
        )

        # Paste shadow (offset slightly from product)
        shadow_x = position_x + 8
        shadow_y = position_y + 8
        result.paste(shadow, (shadow_x, shadow_y), shadow)

        # Paste product
        result.paste(resized_product, (position_x, position_y), resized_product)

        # Convert back to RGB
        final_result = result.convert("RGB")

        logger.info(
            f"✓ Composited {ratio} creative: product at ({position_x}, {position_y}), "
            f"size {product_width}x{product_height} ({int(rules['product_scale'] * 100)}% scale)"
        )

        return final_result

    def _create_shadow(
        self,
        product_png: Image.Image,
        offset: tuple[int, int] = (8, 8),
        blur_radius: int = 15,
        opacity: float = 0.35,
    ) -> Image.Image:
        """
        Create realistic drop shadow for product.

        Args:
            product_png: Transparent product PNG
            offset: Shadow offset (x, y) in pixels
            blur_radius: Gaussian blur radius for shadow softness
            opacity: Shadow opacity (0-1)

        Returns:
            Shadow layer as RGBA image
        """
        # Create shadow base from alpha channel
        shadow = Image.new("RGBA", product_png.size, (0, 0, 0, 0))

        # Extract alpha channel
        alpha = product_png.split()[3]

        # Create black shadow with product shape
        shadow_data = []
        for pixel in alpha.getdata():
            # Black with alpha-based opacity
            shadow_opacity = int(pixel * opacity)
            shadow_data.append((0, 0, 0, shadow_opacity))

        shadow.putdata(shadow_data)

        # Blur shadow for softness and realism
        shadow = shadow.filter(ImageFilter.GaussianBlur(radius=blur_radius))

        return shadow


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Composite product onto scene background")
    parser.add_argument("product", help="Transparent product PNG path")
    parser.add_argument("background", help="Scene background image path")
    parser.add_argument(
        "--ratio",
        "-r",
        default="1x1",
        choices=["1x1", "9x16", "16x9"],
        help="Aspect ratio for composition",
    )
    parser.add_argument("--output", "-o", default="test_output/composite.jpg", help="Output path")
    parser.add_argument(
        "--size",
        "-s",
        help="Target size as WIDTHxHEIGHT (e.g., 1080x1080)",
    )

    args = parser.parse_args()

    # Load images
    product = Image.open(args.product)
    background = Image.open(args.background)

    print(f"Product: {args.product} ({product.size}, {product.mode})")
    print(f"Background: {args.background} ({background.size}, {background.mode})")

    # Parse target size if provided
    target_size = None
    if args.size:
        width, height = map(int, args.size.split("x"))
        target_size = (width, height)

    # Composite
    compositor = CreativeCompositor()
    result = compositor.composite(product, background, ratio=args.ratio, target_size=target_size)

    # Save
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, "JPEG", quality=95)

    print(f"\n✓ Saved: {args.output}")
    print(f"  Size: {result.size}")
    print(f"  Ratio: {args.ratio}")
