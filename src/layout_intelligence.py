#!/usr/bin/env python3
"""
Layout Intelligence - Smart Aspect Ratio Transformations

Implements Canva-style Magic Resize functionality for intelligent layout adaptation
across different aspect ratios with platform-specific optimizations.
"""
import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Social media platform types with specific layout requirements"""

    INSTAGRAM_SQUARE = "instagram_square"  # 1:1
    INSTAGRAM_STORY = "instagram_story"  # 9:16
    YOUTUBE_THUMBNAIL = "youtube_thumb"  # 16:9
    FACEBOOK_POST = "facebook_post"  # 16:9
    TIKTOK_VIDEO = "tiktok_video"  # 9:16


@dataclass
class LayoutElement:
    """Represents a design element with position and properties"""

    element_type: str  # 'product', 'text', 'background', 'badge', 'decoration'
    position: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    content: str = ""
    priority: int = 1  # 1=highest, 5=lowest
    scalable: bool = True
    anchor_point: str = "center"  # center, top, bottom, left, right


@dataclass
class LayoutRule:
    """Defines transformation rules for specific aspect ratios"""

    target_ratio: str
    platform: Platform
    product_zone: tuple[float, float, float, float]  # Relative coordinates (0-1)
    text_zone: tuple[float, float, float, float]
    decoration_zones: list[tuple[float, float, float, float]]
    text_size_factor: float = 1.0
    product_size_factor: float = 1.0


class LayoutIntelligence:
    """
    Smart layout transformation engine for aspect ratio adaptations

    Implements Canva-style Magic Resize with intelligent element repositioning,
    platform-specific optimizations, and layout rule application.
    """

    def __init__(self):
        """Initialize layout intelligence with predefined rules"""
        self.layout_rules = self._load_layout_rules()
        logger.info("LayoutIntelligence initialized with smart transformation rules")

    def transform_design(
        self,
        master_image: Image.Image,
        target_ratio: str,
        campaign_message: str,
        product_name: str,
        elements: list[LayoutElement] | None = None,
    ) -> Image.Image:
        """
        Transform master design to target aspect ratio with intelligent layout adaptation

        Args:
            master_image: Source design (typically 1:1)
            target_ratio: Target aspect ratio (1x1, 9x16, 16x9)
            campaign_message: Text to position intelligently
            product_name: Product for context-aware positioning
            elements: Optional detected elements for advanced positioning

        Returns:
            Transformed image with intelligent layout
        """
        logger.info(f"🎨 Transforming layout: 1:1 → {target_ratio}")
        start_time = time.time()

        # Get layout rule for target ratio
        rule = self.layout_rules.get(target_ratio)
        if not rule:
            logger.warning(f"No layout rule for {target_ratio}, using default resize")
            return self._simple_resize(master_image, target_ratio)

        # Calculate target dimensions
        target_size = self._get_target_dimensions(target_ratio)

        # For solid color backgrounds, use proper layout transformation
        # Extract product and reposition according to layout rules
        transformed = self._apply_layout_transformation(
            master_image, target_size, rule, campaign_message, product_name
        )

        transform_time = time.time() - start_time
        logger.info(f"✓ Layout transformed in {transform_time:.1f}s: {target_ratio}")

        return transformed

    def transform_design_with_assets(
        self,
        transparent_product: Image.Image,
        background: Image.Image,
        target_ratio: str,
        campaign_message: str,
        product_name: str,
        target_size: tuple[int, int],
        variant_id: str | None = None,
    ) -> Image.Image:
        """
        Transform design by properly rebuilding with transparent product and background

        This approach properly scales and positions the product according to layout rules
        instead of trying to extract and reposition from a composite image.
        """
        logger.info(f"🎨 Rebuilding layout: transparent product + background → {target_ratio}")
        start_time = time.time()

        # Get layout rule for target ratio
        rule = self.layout_rules.get(target_ratio)
        if not rule:
            logger.warning(f"No layout rule for {target_ratio}, using fallback")
            return self._fallback_rebuild(
                transparent_product, background, target_size, campaign_message
            )

        # Create canvas with target size
        canvas = Image.new("RGB", target_size, (255, 255, 255))

        # Adapt background to target size
        adapted_background = self._adapt_background_to_size(background, target_size)
        canvas.paste(adapted_background, (0, 0))

        # Position and scale product according to layout rules
        positioned_product = self._position_product_in_zone(
            transparent_product, target_size, rule.product_zone, rule.product_size_factor
        )

        # Composite product onto canvas
        self._composite_product_on_canvas(
            canvas, positioned_product, rule.product_zone, target_size
        )

        # Add intelligent text overlay
        self._add_intelligent_text(canvas, campaign_message, rule, target_size, variant_id)

        transform_time = time.time() - start_time
        logger.info(f"✓ Layout rebuilt in {transform_time:.1f}s: {target_ratio}")

        return canvas

    def analyze_layout_elements(self, image: Image.Image) -> list[LayoutElement]:
        """
        Analyze image to detect layout elements for intelligent positioning

        Args:
            image: Image to analyze

        Returns:
            List of detected layout elements
        """
        # Simplified element detection - in production would use computer vision
        elements = []
        width, height = image.size

        # Assume standard ad layout with product in center, text areas
        elements.append(
            LayoutElement(
                element_type="product",
                position=(width // 4, height // 4, 3 * width // 4, 3 * height // 4),
                priority=1,
                anchor_point="center",
            )
        )

        elements.append(
            LayoutElement(
                element_type="text_primary",
                position=(0, 0, width, height // 6),
                priority=2,
                anchor_point="top",
            )
        )

        elements.append(
            LayoutElement(
                element_type="text_secondary",
                position=(0, 5 * height // 6, width, height),
                priority=3,
                anchor_point="bottom",
            )
        )

        return elements

    def _apply_layout_transformation(
        self,
        source: Image.Image,
        target_size: tuple[int, int],
        rule: LayoutRule,
        campaign_message: str,
        product_name: str,
    ) -> Image.Image:
        """Apply intelligent layout transformation based on rules"""

        target_width, target_height = target_size

        # Create new canvas with target dimensions
        transformed = Image.new("RGB", target_size, (255, 255, 255))

        # Smart background adaptation
        background = self._adapt_background(source, target_size, rule)
        transformed.paste(background, (0, 0))

        # Intelligent product positioning
        product_region = self._extract_product_region(source)
        if product_region:
            positioned_product = self._position_element(
                product_region, target_size, rule.product_zone, rule.product_size_factor
            )
            self._composite_element(transformed, positioned_product, rule.product_zone)

        # Smart text overlay with platform optimization
        self._add_intelligent_text(transformed, campaign_message, rule, target_size)

        # Platform-specific enhancements
        transformed = self._apply_platform_optimizations(transformed, rule.platform)

        return transformed

    def _adapt_background(
        self, source: Image.Image, target_size: tuple[int, int], rule: LayoutRule
    ) -> Image.Image:
        """Intelligently adapt background for new aspect ratio"""

        target_width, target_height = target_size
        source_width, source_height = source.size

        # Smart crop/extend based on target ratio
        if target_height > target_width:  # Portrait (9:16)
            # Extend vertically, intelligent crop horizontally
            scale_factor = target_width / source_width
            scaled_height = int(source_height * scale_factor)

            background = source.resize((target_width, scaled_height), Image.Resampling.LANCZOS)

            if scaled_height < target_height:
                # Need to extend - create gradient fill
                extended = self._extend_background_intelligently(background, target_size)
                return extended
            else:
                # Crop intelligently (center-weighted)
                crop_y = (scaled_height - target_height) // 2
                return background.crop((0, crop_y, target_width, crop_y + target_height))

        elif target_width > target_height:  # Landscape (16:9)
            # Extend horizontally, intelligent crop vertically
            scale_factor = target_height / source_height
            scaled_width = int(source_width * scale_factor)

            background = source.resize((scaled_width, target_height), Image.Resampling.LANCZOS)

            if scaled_width < target_width:
                # Need to extend horizontally
                extended = self._extend_background_intelligently(background, target_size)
                return extended
            else:
                # Crop intelligently
                crop_x = (scaled_width - target_width) // 2
                return background.crop((crop_x, 0, crop_x + target_width, target_height))

        else:  # Square (1:1)
            return source.resize(target_size, Image.Resampling.LANCZOS)

    def _extend_background_intelligently(
        self, base: Image.Image, target_size: tuple[int, int]
    ) -> Image.Image:
        """Extend background using intelligent edge continuation"""

        target_width, target_height = target_size
        base_width, base_height = base.size

        # Create target canvas
        extended = Image.new("RGB", target_size, (255, 255, 255))

        # Position base image centered
        paste_x = (target_width - base_width) // 2
        paste_y = (target_height - base_height) // 2
        extended.paste(base, (paste_x, paste_y))

        # Fill remaining areas with gradient/edge extension
        if paste_y > 0:  # Top area
            top_fill = self._create_gradient_fill(base, "top", paste_y, base_width)
            extended.paste(top_fill, (paste_x, 0))

        if paste_y + base_height < target_height:  # Bottom area
            bottom_fill = self._create_gradient_fill(
                base, "bottom", target_height - (paste_y + base_height), base_width
            )
            extended.paste(bottom_fill, (paste_x, paste_y + base_height))

        return extended

    def _create_gradient_fill(
        self, source: Image.Image, direction: str, height: int, width: int
    ) -> Image.Image:
        """Create gradient fill for background extension"""

        if direction == "top":
            # Sample top edge colors
            edge_colors = []
            for x in range(0, width, max(1, width // 10)):
                pixel = source.getpixel((x, 0))
                edge_colors.append(pixel)
        else:  # bottom
            # Sample bottom edge colors
            edge_colors = []
            for x in range(0, width, max(1, width // 10)):
                pixel = source.getpixel((x, source.height - 1))
                edge_colors.append(pixel)

        # Create simple gradient
        fill = Image.new("RGB", (width, height), edge_colors[0] if edge_colors else (240, 240, 240))
        return fill

    def _extract_product_region(self, source: Image.Image) -> Image.Image | None:
        """Extract product region from source image (simplified detection)"""
        # Simplified - assume product is in center region
        width, height = source.size

        # Extract center 60% as product region
        margin_x = int(width * 0.2)
        margin_y = int(height * 0.2)

        product_region = source.crop((margin_x, margin_y, width - margin_x, height - margin_y))
        return product_region

    def _position_element(
        self,
        element: Image.Image,
        canvas_size: tuple[int, int],
        zone: tuple[float, float, float, float],
        size_factor: float,
    ) -> Image.Image:
        """Position element within specified zone with size adjustment"""

        canvas_width, canvas_height = canvas_size
        zone_x1, zone_y1, zone_x2, zone_y2 = zone

        # Calculate zone dimensions
        zone_width = int((zone_x2 - zone_x1) * canvas_width)
        zone_height = int((zone_y2 - zone_y1) * canvas_height)

        # Resize element to fit zone with size factor
        element_width = int(zone_width * size_factor)
        element_height = int(zone_height * size_factor)

        # Maintain aspect ratio
        element_ratio = element.width / element.height
        target_ratio = element_width / element_height

        if element_ratio > target_ratio:
            # Fit to width
            element_height = int(element_width / element_ratio)
        else:
            # Fit to height
            element_width = int(element_height * element_ratio)

        positioned = element.resize((element_width, element_height), Image.Resampling.LANCZOS)
        return positioned

    def _composite_element(
        self, canvas: Image.Image, element: Image.Image, zone: tuple[float, float, float, float]
    ):
        """Composite element onto canvas within zone"""

        canvas_width, canvas_height = canvas.size
        zone_x1, zone_y1, zone_x2, zone_y2 = zone

        # Calculate zone center
        zone_center_x = int((zone_x1 + zone_x2) / 2 * canvas_width)
        zone_center_y = int((zone_y1 + zone_y2) / 2 * canvas_height)

        # Position element at zone center
        paste_x = zone_center_x - element.width // 2
        paste_y = zone_center_y - element.height // 2

        # Composite with alpha support
        if element.mode == "RGBA":
            canvas.paste(element, (paste_x, paste_y), element)
        else:
            canvas.paste(element, (paste_x, paste_y))

    def _add_intelligent_text(
        self,
        canvas: Image.Image,
        message: str,
        rule: LayoutRule,
        canvas_size: tuple[int, int],
        variant_id: str | None = None,
    ):
        """Add professional text with variants, fonts, colors, and effects"""

        # Import text variant engine
        try:
            from text_variant_engine import TextVariantEngine

            text_engine = TextVariantEngine()
        except ImportError:
            try:
                import os
                import sys

                sys.path.append(os.path.dirname(__file__))
                from text_variant_engine import TextVariantEngine

                text_engine = TextVariantEngine()
            except ImportError:
                logger.warning("TextVariantEngine not available, falling back to basic text")
                self._add_basic_text_fallback(canvas, message, rule, canvas_size)
                return

        # Determine platform from rule
        platform_map = {
            "instagram_square": "instagram_square",
            "instagram_story": "instagram_story",
            "youtube_thumbnail": "youtube_thumbnail",
            "facebook_post": "youtube_thumbnail",  # Similar to YouTube
            "tiktok_video": "instagram_story",  # Similar to Instagram Story
        }

        platform = platform_map.get(
            rule.platform.value if hasattr(rule.platform, "value") else str(rule.platform),
            "default",
        )

        # Sample background color from canvas
        background_color = self._sample_background_color(canvas)

        # Generate text variant
        try:
            text_variant = text_engine.generate_text_variant(
                base_message=message,
                target_platform=platform,
                background_color=background_color,
                canvas_size=canvas_size,
                text_zone=rule.text_zone,
                variant_id=variant_id,
            )

            # Render the variant onto canvas
            text_engine.render_text_variant(canvas, text_variant)

            logger.info(
                f"✓ Rendered advanced text: '{text_variant['message'][:30]}...' with {text_variant['effects']['type']} effect"
            )

        except Exception as e:
            logger.warning(f"Text variant engine failed: {e}, falling back to basic text")
            self._add_basic_text_fallback(canvas, message, rule, canvas_size)

    def _add_basic_text_fallback(
        self, canvas: Image.Image, message: str, rule: LayoutRule, canvas_size: tuple[int, int]
    ):
        """Fallback to basic text rendering if advanced engine fails"""

        draw = ImageDraw.Draw(canvas)
        canvas_width, canvas_height = canvas_size

        # Calculate text zone
        text_x1, text_y1, text_x2, text_y2 = rule.text_zone
        text_width = int((text_x2 - text_x1) * canvas_width)
        text_height = int((text_y2 - text_y1) * canvas_height)

        # Much larger dynamic font sizing
        base_font_size = max(30, min(80, int(canvas_height * 0.08)))
        font_size = int(base_font_size * rule.text_size_factor)

        try:
            # Try to load system font with bigger size
            font = ImageFont.truetype("Arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # Smart multiline text wrapping
        lines = self._wrap_text_intelligently(message, font, text_width)

        # Calculate total text height for vertical centering
        line_height = font_size + int(font_size * 0.2)  # 20% line spacing
        total_text_height = len(lines) * line_height

        # Vertical centering within text zone
        start_y = int(text_y1 * canvas_height + (text_height - total_text_height) / 2)

        # Draw each line with outline for visibility (no grey background)
        outline_width = max(2, font_size // 15)

        for i, line in enumerate(lines):
            # Calculate horizontal centering for each line
            line_bbox = draw.textbbox((0, 0), line, font=font)
            line_width = line_bbox[2] - line_bbox[0]
            line_x = int(text_x1 * canvas_width + (text_width - line_width) / 2)
            line_y = start_y + (i * line_height)

            # Draw text outline (black) - no grey background
            for dx in range(-outline_width, outline_width + 1):
                for dy in range(-outline_width, outline_width + 1):
                    if dx != 0 or dy != 0:
                        draw.text((line_x + dx, line_y + dy), line, font=font, fill="black")

            # Draw main text (white)
            draw.text((line_x, line_y), line, font=font, fill="white")

    def _sample_background_color(self, canvas: Image.Image) -> str:
        """Sample background color from canvas for contrast optimization"""

        # Sample color from multiple points to find dominant background color
        width, height = canvas.size
        sample_points = [
            (width // 4, height // 4),
            (3 * width // 4, height // 4),
            (width // 2, height // 2),
            (width // 4, 3 * height // 4),
            (3 * width // 4, 3 * height // 4),
        ]

        colors = []
        for x, y in sample_points:
            try:
                color = canvas.getpixel((x, y))
                if isinstance(color, (list, tuple)) and len(color) >= 3:
                    colors.append(color[:3])  # Take RGB only
            except:
                continue

        if colors:
            # Average the sampled colors
            avg_r = sum(c[0] for c in colors) // len(colors)
            avg_g = sum(c[1] for c in colors) // len(colors)
            avg_b = sum(c[2] for c in colors) // len(colors)
            return f"#{avg_r:02x}{avg_g:02x}{avg_b:02x}"
        else:
            return "#2E8B57"  # Fallback green

    def _wrap_text_intelligently(
        self, text: str, font: ImageFont.ImageFont, max_width: int
    ) -> list[str]:
        """Wrap text intelligently based on width constraints"""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            # Test if adding this word exceeds width
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                current_line.append(word)
            else:
                # Start new line if current line has words
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Single word too long, force it anyway
                    lines.append(word)
                    current_line = []

        # Add remaining words
        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [text]

    def _apply_platform_optimizations(self, image: Image.Image, platform: Platform) -> Image.Image:
        """Apply platform-specific optimizations"""

        if platform == Platform.INSTAGRAM_STORY:
            # Add story-specific optimizations (safe zones, etc.)
            pass
        elif platform == Platform.YOUTUBE_THUMBNAIL:
            # Enhance contrast and text visibility for thumbnails
            pass
        elif platform == Platform.TIKTOK_VIDEO:
            # TikTok-specific optimizations
            pass

        return image

    def _get_target_dimensions(self, ratio: str) -> tuple[int, int]:
        """Get optimal dimensions for target ratio from external config or fallback"""
        aspect_ratios_path = Path("cache/layouts/aspect_ratios.json")

        if aspect_ratios_path.exists():
            try:
                import json

                with open(aspect_ratios_path) as f:
                    config = json.load(f)

                aspect_ratios = config.get("aspect_ratios", {})
                if ratio in aspect_ratios:
                    return tuple(aspect_ratios[ratio]["dimensions"])

            except Exception as e:
                logger.warning(f"Failed to load aspect ratios config: {e}")

        # Fallback dimensions
        dimensions = {
            "1x1": (1080, 1080),  # Instagram Square
            "9x16": (1080, 1920),  # Instagram Stories, TikTok
            "16x9": (1920, 1080),  # YouTube, Facebook
        }
        return dimensions.get(ratio, (1080, 1080))

    def _smart_resize_with_text(
        self,
        source: Image.Image,
        target_size: tuple[int, int],
        rule: LayoutRule,
        campaign_message: str,
    ) -> Image.Image:
        """
        Smart resize for solid color backgrounds with intelligent text placement

        This approach avoids product duplication by treating the source as a complete
        composition and just resizing it intelligently while adding proper text overlay.
        """
        target_width, target_height = target_size
        source_width, source_height = source.size

        # Calculate the best fit approach for the target ratio
        if target_height > target_width:  # Portrait (9x16)
            # Scale to fit width, then crop/extend height as needed
            scale_factor = target_width / source_width
            scaled_height = int(source_height * scale_factor)

            resized = source.resize((target_width, scaled_height), Image.Resampling.LANCZOS)

            if scaled_height >= target_height:
                # Crop intelligently (center crop)
                crop_y = (scaled_height - target_height) // 2
                transformed = resized.crop((0, crop_y, target_width, crop_y + target_height))
            else:
                # Extend with solid color (sample from edges)
                transformed = self._extend_with_solid_color(resized, target_size)

        elif target_width > target_height:  # Landscape (16x9)
            # Scale to fit height, then crop/extend width as needed
            scale_factor = target_height / source_height
            scaled_width = int(source_width * scale_factor)

            resized = source.resize((scaled_width, target_height), Image.Resampling.LANCZOS)

            if scaled_width >= target_width:
                # Crop intelligently (center crop)
                crop_x = (scaled_width - target_width) // 2
                transformed = resized.crop((crop_x, 0, crop_x + target_width, target_height))
            else:
                # Extend with solid color
                transformed = self._extend_with_solid_color(resized, target_size)

        else:  # Square (1x1)
            # Simple resize
            transformed = source.resize(target_size, Image.Resampling.LANCZOS)

        # Add intelligent text overlay
        self._add_intelligent_text(transformed, campaign_message, rule, target_size)

        return transformed

    def _extend_with_solid_color(
        self, resized: Image.Image, target_size: tuple[int, int]
    ) -> Image.Image:
        """Extend image with solid color sampled from edges"""
        target_width, target_height = target_size
        resized_width, resized_height = resized.size

        # Sample background color from corners (should be solid color)
        corner_colors = [
            resized.getpixel((0, 0)),
            resized.getpixel((resized_width - 1, 0)),
            resized.getpixel((0, resized_height - 1)),
            resized.getpixel((resized_width - 1, resized_height - 1)),
        ]

        # Use the most common color (should be our solid background)
        bg_color = corner_colors[0]  # For solid backgrounds, all corners should be same

        # Create target canvas with background color
        extended = Image.new("RGB", target_size, bg_color)

        # Center the resized image
        paste_x = (target_width - resized_width) // 2
        paste_y = (target_height - resized_height) // 2
        extended.paste(resized, (paste_x, paste_y))

        return extended

    def _simple_resize(self, image: Image.Image, ratio: str) -> Image.Image:
        """Fallback simple resize when no intelligent rule available"""
        target_size = self._get_target_dimensions(ratio)
        return image.resize(target_size, Image.Resampling.LANCZOS)

    def _load_layout_rules(self) -> dict[str, LayoutRule]:
        """Load layout transformation rules from external config or fallback to hardcoded"""
        layout_rules_path = Path("cache/layouts/layout_rules.json")

        if layout_rules_path.exists():
            try:
                import json

                with open(layout_rules_path) as f:
                    config = json.load(f)

                rules = {}
                platform_map = {
                    "instagram_square": Platform.INSTAGRAM_SQUARE,
                    "instagram_story": Platform.INSTAGRAM_STORY,
                    "youtube_thumbnail": Platform.YOUTUBE_THUMBNAIL,
                    "facebook_post": Platform.FACEBOOK_POST,
                    "tiktok_video": Platform.TIKTOK_VIDEO,
                }

                for ratio, rule_config in config.get("layout_rules", {}).items():
                    platform = platform_map.get(
                        rule_config.get("platform", "instagram_square"), Platform.INSTAGRAM_SQUARE
                    )

                    rules[ratio] = LayoutRule(
                        target_ratio=rule_config.get("target_ratio", ratio),
                        platform=platform,
                        product_zone=tuple(rule_config.get("product_zone", [0.2, 0.2, 0.8, 0.8])),
                        text_zone=tuple(rule_config.get("text_zone", [0.1, 0.05, 0.9, 0.15])),
                        decoration_zones=[
                            tuple(zone)
                            for zone in rule_config.get("decoration_zones", [[0.0, 0.85, 1.0, 1.0]])
                        ],
                        text_size_factor=rule_config.get("text_size_factor", 1.0),
                        product_size_factor=rule_config.get("product_size_factor", 0.6),
                    )

                logger.info(f"✓ Loaded layout rules from external config: {len(rules)} rules")
                return rules

            except Exception as e:
                logger.warning(
                    f"Failed to load external layout rules: {e}, using hardcoded fallback"
                )

        # Fallback to hardcoded rules
        logger.info("Using hardcoded layout rules as fallback")
        rules = {
            # 1x1: Product centered, 60% size
            "1x1": LayoutRule(
                target_ratio="1x1",
                platform=Platform.INSTAGRAM_SQUARE,
                product_zone=(0.2, 0.2, 0.8, 0.8),  # Centered, 60% of canvas
                text_zone=(0.1, 0.05, 0.9, 0.15),  # Top text
                decoration_zones=[(0.0, 0.85, 1.0, 1.0)],  # Bottom decorations
                text_size_factor=1.0,
                product_size_factor=0.6,  # 60% size as requested
            ),
            # 9x16: Product 60% of bottom half (positioned in lower portion)
            "9x16": LayoutRule(
                target_ratio="9x16",
                platform=Platform.INSTAGRAM_STORY,
                product_zone=(0.2, 0.5, 0.8, 0.9),  # Bottom half, 60% width
                text_zone=(0.1, 0.1, 0.9, 0.45),  # Top half text zone
                decoration_zones=[(0.0, 0.9, 1.0, 1.0)],  # Bottom decorations
                text_size_factor=1.2,  # Larger text for stories
                product_size_factor=0.6,  # 60% size in bottom half
            ),
            # 16x9: Product 60% of height, positioned right of center
            "16x9": LayoutRule(
                target_ratio="16x9",
                platform=Platform.YOUTUBE_THUMBNAIL,
                product_zone=(0.55, 0.2, 0.9, 0.8),  # Right of center, 60% height
                text_zone=(0.05, 0.3, 0.5, 0.7),  # Left-side text
                decoration_zones=[(0.0, 0.05, 0.4, 0.25)],  # Top-left decorations
                text_size_factor=1.4,  # Large text for thumbnails
                product_size_factor=0.6,  # 60% of vertical space
            ),
        }

        return rules

    def _adapt_background_to_size(
        self, background: Image.Image, target_size: tuple[int, int]
    ) -> Image.Image:
        """Adapt background image to target size with proper aspect ratio preservation"""

        target_width, target_height = target_size
        bg_width, bg_height = background.size

        # Calculate scale factors for both dimensions
        scale_x = target_width / bg_width
        scale_y = target_height / bg_height

        # Use the larger scale factor to ensure background covers entire target area
        scale_factor = max(scale_x, scale_y)

        # Scale background to cover target area
        scaled_width = int(bg_width * scale_factor)
        scaled_height = int(bg_height * scale_factor)

        scaled_background = background.resize(
            (scaled_width, scaled_height), Image.Resampling.LANCZOS
        )

        # If scaled background is larger than target, crop it centered
        if scaled_width > target_width or scaled_height > target_height:
            # Center crop
            crop_x = (scaled_width - target_width) // 2
            crop_y = (scaled_height - target_height) // 2

            cropped_background = scaled_background.crop(
                (crop_x, crop_y, crop_x + target_width, crop_y + target_height)
            )

            return cropped_background
        else:
            # This shouldn't happen with max scale factor, but as fallback
            return scaled_background

    def _position_product_in_zone(
        self,
        product: Image.Image,
        canvas_size: tuple[int, int],
        product_zone: tuple[float, float, float, float],
        size_factor: float,
    ) -> Image.Image:
        """Position and scale product within the specified zone"""
        canvas_width, canvas_height = canvas_size
        zone_x1, zone_y1, zone_x2, zone_y2 = product_zone

        # Calculate zone dimensions
        zone_width = int((zone_x2 - zone_x1) * canvas_width)
        zone_height = int((zone_y2 - zone_y1) * canvas_height)

        # Calculate target product size with size factor
        target_width = int(zone_width * size_factor)
        target_height = int(zone_height * size_factor)

        # Maintain aspect ratio
        product_ratio = product.width / product.height
        target_ratio = target_width / target_height

        if product_ratio > target_ratio:
            # Fit to width
            final_width = target_width
            final_height = int(target_width / product_ratio)
        else:
            # Fit to height
            final_height = target_height
            final_width = int(target_height * product_ratio)

        # Resize product
        positioned_product = product.resize((final_width, final_height), Image.Resampling.LANCZOS)
        return positioned_product

    def _composite_product_on_canvas(
        self,
        canvas: Image.Image,
        product: Image.Image,
        product_zone: tuple[float, float, float, float],
        canvas_size: tuple[int, int],
    ):
        """Composite product onto canvas within the specified zone"""
        canvas_width, canvas_height = canvas_size
        zone_x1, zone_y1, zone_x2, zone_y2 = product_zone

        # Calculate zone center
        zone_center_x = int((zone_x1 + zone_x2) / 2 * canvas_width)
        zone_center_y = int((zone_y1 + zone_y2) / 2 * canvas_height)

        # Position product at zone center
        paste_x = zone_center_x - product.width // 2
        paste_y = zone_center_y - product.height // 2

        # Composite with alpha support for transparent products
        if product.mode == "RGBA":
            canvas.paste(product, (paste_x, paste_y), product)
        else:
            canvas.paste(product, (paste_x, paste_y))

    def _fallback_rebuild(
        self,
        product: Image.Image,
        background: Image.Image,
        target_size: tuple[int, int],
        message: str,
    ) -> Image.Image:
        """Fallback rebuild when no layout rules available"""
        canvas = Image.new("RGB", target_size, (255, 255, 255))

        # Simple background resize
        bg_resized = background.resize(target_size, Image.Resampling.LANCZOS)
        canvas.paste(bg_resized, (0, 0))

        # Center product at 60% size
        canvas_width, canvas_height = target_size
        product_size = int(min(canvas_width, canvas_height) * 0.6)

        # Maintain aspect ratio
        product_ratio = product.width / product.height
        if product_ratio > 1:
            new_width = product_size
            new_height = int(product_size / product_ratio)
        else:
            new_height = product_size
            new_width = int(product_size * product_ratio)

        resized_product = product.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Center position
        paste_x = (canvas_width - new_width) // 2
        paste_y = (canvas_height - new_height) // 2

        if resized_product.mode == "RGBA":
            canvas.paste(resized_product, (paste_x, paste_y), resized_product)
        else:
            canvas.paste(resized_product, (paste_x, paste_y))

        return canvas


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Test layout intelligence transformations")
    parser.add_argument("input_image", help="Input image path")
    parser.add_argument("target_ratio", choices=["1x1", "9x16", "16x9"], help="Target aspect ratio")
    parser.add_argument(
        "--message", default="Complete home care solutions", help="Campaign message"
    )
    parser.add_argument("--product", default="CleanHome Detergent", help="Product name")
    parser.add_argument("--output", "-o", default="layout_test_output", help="Output directory")

    args = parser.parse_args()

    # Initialize layout intelligence
    layout_ai = LayoutIntelligence()

    # Load input image
    input_image = Image.open(args.input_image)
    print(f"Loaded input: {input_image.size}")

    # Transform layout
    transformed = layout_ai.transform_design(
        input_image, args.target_ratio, args.message, args.product
    )

    # Save output
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / f"transformed_{args.target_ratio}.jpg"
    transformed.save(output_path, "JPEG", quality=95)

    print(f"\n✓ Transformed {input_image.size} → {transformed.size}")
    print(f"✓ Saved: {output_path}")
