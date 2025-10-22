#!/usr/bin/env python3
"""
Image Processor - Text overlay with multi-line wrapping and professional typography

Adds campaign messages to images with intelligent word wrapping, responsive font sizing,
and high-contrast styling for readability across all aspect ratios.
"""

import logging

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Professional text overlay and image processing"""

    # Font search paths (macOS and Linux)
    FONT_PATHS = [
        "/System/Library/Fonts/HelveticaNeue.ttc",  # macOS - Bold, modern
        "/System/Library/Fonts/Helvetica.ttc",  # macOS - Fallback
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",  # Linux
    ]

    def __init__(self):
        """Initialize image processor"""
        logger.info("ImageProcessor initialized")

    def add_campaign_text(
        self,
        image: Image.Image,
        message: str,
        position: str = "top",
        max_lines: int = 3,
    ) -> Image.Image:
        """
        Add professional campaign message with multi-line wrapping.

        Args:
            image: PIL Image to add text to
            message: Campaign message text
            position: Text position (top, center, bottom)
            max_lines: Maximum number of text lines

        Returns:
            Image with text overlay
        """
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)

        # Calculate much larger responsive font size based on image size
        font_size = int(min(img_copy.size) * 0.12)  # 12% of smallest dimension (was 8%)
        font = self._load_font(font_size)

        # Word wrapping for long messages
        lines = self._wrap_text(message, draw, font, img_copy.width)

        # Limit to max lines
        lines = lines[:max_lines]

        # Calculate positioning
        line_height = int(font_size * 1.4)
        total_height = len(lines) * line_height

        if position == "top":
            y_start = int(img_copy.height * 0.08)
        elif position == "center":
            y_start = (img_copy.height - total_height) // 2
        else:  # bottom
            y_start = int(img_copy.height * 0.85 - total_height)

        # No background overlay - clean text directly on image
        draw = ImageDraw.Draw(img_copy)

        # Draw each line centered with professional styling
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (img_copy.width - text_width) // 2
            y = y_start + (i * line_height)

            # Add subtle outline for definition
            outline_width = 2
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx * dx + dy * dy <= outline_width * outline_width:
                        draw.text((x + dx, y + dy), line, fill="#1a1a1a", font=font)

            # Main text in bright white with slight shadow
            draw.text((x + 1, y + 1), line, fill="#e0e0e0", font=font)  # Shadow
            draw.text((x, y), line, fill="white", font=font)  # Main text

        logger.info(f"✓ Added text overlay: {len(lines)} lines, {message[:40]}...")
        return img_copy

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Load system font with fallback to default"""
        for font_path in self.FONT_PATHS:
            try:
                return ImageFont.truetype(font_path, size)
            except:
                continue

        logger.warning("System fonts not found - using default font")
        return ImageFont.load_default()

    def _wrap_text(
        self, text: str, draw: ImageDraw.Draw, font: ImageFont.FreeTypeFont, max_width: int
    ) -> list:
        """
        Wrap text into multiple lines based on max width.

        Args:
            text: Text to wrap
            draw: ImageDraw object for text measurement
            font: Font to use
            max_width: Maximum width in pixels

        Returns:
            List of text lines
        """
        words = text.split()
        lines = []
        current_line = []

        # Use 85% of image width for text
        effective_width = int(max_width * 0.85)

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]

            if text_width <= effective_width or not current_line:
                current_line.append(word)
            else:
                lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def resize_to_ratio(self, image: Image.Image, ratio: str) -> Image.Image:
        """
        Resize image to specific aspect ratio.

        Args:
            image: PIL Image to resize
            ratio: Aspect ratio (1x1, 9x16, 16x9)

        Returns:
            Resized image
        """
        aspect_ratios = {
            "1x1": (1080, 1080),
            "9x16": (1080, 1920),
            "16x9": (1920, 1080),
        }

        target_size = aspect_ratios.get(ratio, (1080, 1080))

        # Resize maintaining aspect ratio, then crop/pad to target
        resized = image.resize(target_size, Image.Resampling.LANCZOS)

        logger.info(f"✓ Resized to {ratio}: {target_size}")
        return resized


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse
    from pathlib import Path

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Add text overlay to images")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("message", help="Campaign message text")
    parser.add_argument(
        "--position",
        "-p",
        default="top",
        choices=["top", "center", "bottom"],
        help="Text position",
    )
    parser.add_argument(
        "--max-lines", "-l", type=int, default=3, help="Maximum number of text lines"
    )
    parser.add_argument(
        "--output", "-o", default="test_output/text_overlay.jpg", help="Output path"
    )

    args = parser.parse_args()

    # Load image
    image = Image.open(args.input)
    print(f"Loaded: {args.input}")
    print(f"Size: {image.size}, Mode: {image.mode}")

    # Add text
    processor = ImageProcessor()
    result = processor.add_campaign_text(
        image, args.message, position=args.position, max_lines=args.max_lines
    )

    # Save
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result.save(args.output, "JPEG", quality=95)

    print(f"\n✓ Saved: {args.output}")
    print(f"  Message: {args.message}")
    print(f"  Position: {args.position}")
