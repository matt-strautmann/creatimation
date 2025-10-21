#!/usr/bin/env python3
"""
Text Variant Engine - Professional Ad-Quality Text Generation

Creates dynamic text variants with professional fonts, colors, effects, and
platform-specific optimizations for social media advertising.
"""
import colorsys
import logging
import random
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


class TextVariantEngine:
    """
    Professional text generation engine with variants, effects, and platform optimization

    Features:
    - Multiple text variants and messaging options
    - Professional font library with fallbacks
    - Color harmony and contrast optimization
    - Advanced text effects (gradients, shadows, glows)
    - Platform-specific text positioning and sizing
    - A/B testing support with performance tracking
    """

    def __init__(self, config_dir: str = "cache/text"):
        """Initialize text engine with configuration"""
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load configurations
        self.font_library = self._load_font_library()
        self.color_palettes = self._load_color_palettes()
        self.text_effects = self._load_text_effects()
        self.platform_presets = self._load_platform_presets()
        self.message_variants = self._load_message_variants()

        logger.info("TextVariantEngine initialized with professional ad text capabilities")

    def generate_text_variant(
        self,
        base_message: str,
        target_platform: str,
        background_color: str,
        canvas_size: tuple[int, int],
        text_zone: tuple[float, float, float, float],
        variant_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate a professional text variant with optimized styling

        Args:
            base_message: Base campaign message
            target_platform: Target platform (instagram_square, instagram_story, youtube_thumbnail)
            background_color: Background color for contrast optimization
            canvas_size: Canvas dimensions for sizing calculations
            text_zone: Text positioning zone (x1, y1, x2, y2) as ratios
            variant_id: Optional specific variant to use (for A/B testing)

        Returns:
            Text variant specification with all styling parameters
        """

        # Select message variant
        message = self._select_message_variant(base_message, variant_id)

        # Get platform preset
        platform_preset = self.platform_presets.get(
            target_platform, self.platform_presets["default"]
        )

        # Calculate optimal font and sizing
        font_spec = self._calculate_optimal_font(message, canvas_size, text_zone, platform_preset)

        # Generate color scheme with contrast optimization
        color_scheme = self._generate_color_scheme(background_color, platform_preset)

        # Select text effect based on platform and message
        effect_spec = self._select_text_effect(platform_preset, color_scheme)

        # Calculate positioning with micro-adjustments
        position_spec = self._calculate_positioning(text_zone, canvas_size, platform_preset)

        variant = {
            "message": message,
            "original_message": base_message,
            "variant_id": variant_id or f"auto_{random.randint(1000, 9999)}",
            "platform": target_platform,
            "font": font_spec,
            "colors": color_scheme,
            "effects": effect_spec,
            "positioning": position_spec,
            "canvas_size": canvas_size,
            "metadata": {
                "generated_at": "runtime",
                "contrast_ratio": color_scheme["contrast_ratio"],
                "readability_score": self._calculate_readability_score(message, font_spec),
                "platform_optimized": True,
            },
        }

        logger.info(f"Generated text variant: '{message[:30]}...' for {target_platform}")
        return variant

    def render_text_variant(self, canvas: Image.Image, variant_spec: dict[str, Any]) -> Image.Image:
        """
        Render text variant onto canvas with professional effects

        Args:
            canvas: Target canvas to render text onto
            variant_spec: Text variant specification from generate_text_variant

        Returns:
            Canvas with rendered text
        """

        draw = ImageDraw.Draw(canvas)
        message = variant_spec["message"]
        font_spec = variant_spec["font"]
        colors = variant_spec["colors"]
        effects = variant_spec["effects"]
        positioning = variant_spec["positioning"]

        # Load font with fallback handling
        font = self._load_font_with_fallback(font_spec)

        # Smart text wrapping
        lines = self._wrap_text_intelligently(message, font, positioning["text_width"])

        # Calculate final positioning
        text_positions = self._calculate_line_positions(lines, font, positioning)

        # Apply effects based on specification
        if effects["type"] == "clean_shadow":
            self._render_clean_shadow_text(draw, lines, text_positions, font, colors, effects)
        elif effects["type"] == "soft_shadow":
            self._render_soft_shadow_text(draw, lines, text_positions, font, colors, effects)
        elif effects["type"] == "stroke_text":
            self._render_stroke_text(draw, lines, text_positions, font, colors, effects)
        elif effects["type"] == "high_contrast":
            self._render_high_contrast_text(draw, lines, text_positions, font, colors, effects)
        elif effects["type"] == "premium_subtle":
            self._render_premium_subtle_text(draw, lines, text_positions, font, colors, effects)
        else:
            # Fallback to clean shadow
            self._render_clean_shadow_text(draw, lines, text_positions, font, colors, effects)

        logger.info(f"Rendered {len(lines)} lines with {effects['type']} effect")
        return canvas

    def get_available_variants(self, base_message: str) -> list[dict[str, str]]:
        """Get list of available text variants for A/B testing"""
        variants = []

        # Generate variants from message templates
        for template_name, template_data in self.message_variants.items():
            if template_data.get("active", True):
                for variant in template_data["variations"]:
                    formatted_message = variant.format(base_message=base_message)
                    variants.append(
                        {
                            "id": f"{template_name}_{variant.replace(' ', '_').lower()}",
                            "message": formatted_message,
                            "template": template_name,
                            "performance_tier": template_data.get("performance_tier", "standard"),
                        }
                    )

        return variants

    def _select_message_variant(self, base_message: str, variant_id: str | None = None) -> str:
        """Select message variant based on ID or intelligent selection"""

        if variant_id and variant_id.startswith("auto_"):
            # Auto-selection based on message characteristics
            return self._intelligent_message_selection(base_message)

        if variant_id:
            # Find specific variant
            for template_data in self.message_variants.values():
                for variant in template_data["variations"]:
                    formatted = variant.format(base_message=base_message)
                    test_id = variant.replace(" ", "_").lower()
                    if variant_id.endswith(test_id):
                        return formatted

        # Smart selection based on message content
        return self._intelligent_message_selection(base_message)

    def _intelligent_message_selection(self, base_message: str) -> str:
        """Intelligently select best message variant based on content analysis"""

        # Analyze message characteristics
        word_count = len(base_message.split())
        has_exclamation = "!" in base_message
        has_action_word = any(
            word in base_message.lower() for word in ["clean", "spring", "fresh", "new", "discover"]
        )
        has_price_word = any(
            word in base_message.lower() for word in ["sale", "save", "off", "$", "price", "deal"]
        )

        # Select template based on analysis using new template names
        if has_price_word:
            template_name = "price_promotional"
        elif word_count <= 3 and has_exclamation:
            template_name = "catchphrase_snappy"
        elif has_action_word:
            template_name = "benefit_driven"
        elif "spring" in base_message.lower():
            template_name = "seasonal_fresh"
        elif word_count > 4:
            template_name = "family_focused"
        else:
            template_name = "catchphrase_snappy"

        # Get template and select best variation
        template_data = self.message_variants.get(
            template_name, self.message_variants["catchphrase_snappy"]
        )
        selected_variant = random.choice(template_data["variations"])

        return selected_variant.format(base_message=base_message)

    def _calculate_optimal_font(
        self,
        message: str,
        canvas_size: tuple[int, int],
        text_zone: tuple[float, float, float, float],
        platform_preset: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate optimal font and sizing for message and platform with professional constraints"""

        canvas_width, canvas_height = canvas_size
        zone_width = int((text_zone[2] - text_zone[0]) * canvas_width)
        zone_height = int((text_zone[3] - text_zone[1]) * canvas_height)

        # Platform-specific font selection using system fonts
        font_category = platform_preset.get("preferred_font_category", "system_sans")
        font_options = self.font_library[font_category]

        # Select font based on message characteristics
        word_count = len(message.split())
        if word_count <= 2:
            font_name = font_options.get("extra_bold", font_options["bold"])
        elif word_count <= 4:
            font_name = font_options.get("bold", font_options["regular"])
        else:
            font_name = font_options.get("regular", font_options["bold"])

        # Calculate optimal size with professional constraints
        base_size = platform_preset.get("base_font_size", 110)
        size_factor = min(canvas_width / 1080, canvas_height / 1080)  # Scale relative to 1080p
        optimal_size = int(base_size * size_factor * platform_preset.get("size_multiplier", 1.0))

        # Adjust for text length (shorter text can be larger)
        if word_count > 6:
            optimal_size = int(optimal_size * 0.75)  # Smaller for long text
        elif word_count > 4:
            optimal_size = int(optimal_size * 0.85)
        elif word_count <= 2:
            optimal_size = int(optimal_size * 1.25)  # Larger for short, punchy text

        # Apply professional font size constraints
        min_font_size = platform_preset.get("min_font_size", 16)  # Mobile accessibility minimum
        max_font_size = platform_preset.get("max_font_size", 200)  # Reasonable upper limit

        optimal_size = max(min_font_size, min(optimal_size, max_font_size))

        return {
            "family": font_name,
            "size": optimal_size,
            "weight": "bold" if word_count <= 4 else "regular",
            "category": font_category,
            "fallbacks": font_options.get(
                "fallbacks",
                ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "Arial", "sans-serif"],
            ),
        }

    def _generate_color_scheme(
        self, background_color: str, platform_preset: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate optimized color scheme with high contrast"""

        # Parse background color
        if background_color.startswith("#"):
            bg_rgb = tuple(int(background_color[i : i + 2], 16) for i in (1, 3, 5))
        else:
            bg_rgb = (46, 139, 87)  # Default green

        # Calculate luminance
        bg_luminance = self._calculate_luminance(bg_rgb)

        # Select optimal text color for contrast
        if bg_luminance > 0.5:
            # Light background - use dark text
            primary_color = (25, 25, 25)  # Almost black
            contrast_ratio = self._calculate_contrast_ratio(primary_color, bg_rgb)
        else:
            # Dark background - use light text
            primary_color = (255, 255, 255)  # White
            contrast_ratio = self._calculate_contrast_ratio(primary_color, bg_rgb)

        # Generate accent colors
        accent_color = self._generate_accent_color(bg_rgb, primary_color)
        shadow_color = self._generate_shadow_color(primary_color)

        return {
            "primary": primary_color,
            "accent": accent_color,
            "shadow": shadow_color,
            "background": bg_rgb,
            "contrast_ratio": contrast_ratio,
            "luminance_optimized": True,
        }

    def _select_text_effect(
        self, platform_preset: dict[str, Any], color_scheme: dict[str, Any]
    ) -> dict[str, Any]:
        """Select optimal text effect based on platform and colors"""

        preferred_effects = platform_preset.get("preferred_effects", ["clean_shadow"])
        contrast_ratio = color_scheme["contrast_ratio"]

        # Select effect based on contrast and platform
        if contrast_ratio > 7.0:
            # High contrast - can use minimal effects
            effect_type = "premium_subtle"
        elif contrast_ratio > 4.5:
            # Medium contrast - use clean shadow
            effect_type = "clean_shadow"
        elif contrast_ratio > 3.0:
            # Lower contrast - use soft shadow
            effect_type = "soft_shadow"
        else:
            # Low contrast - use high contrast mode
            effect_type = "high_contrast"

        # Use preferred effects from platform if available
        if preferred_effects and preferred_effects[0] in self.text_effects:
            effect_type = preferred_effects[0]

        # Get effect specification
        effect_spec = self.text_effects.get(effect_type, self.text_effects["clean_shadow"])

        # Customize effect parameters based on platform
        customized_spec = effect_spec.copy()
        if platform_preset.get("name") == "instagram_story":
            customized_spec["intensity"] = min(1.0, customized_spec.get("intensity", 0.6) * 1.1)
        elif platform_preset.get("name") == "youtube_thumbnail":
            customized_spec["intensity"] = min(1.0, customized_spec.get("intensity", 0.6) * 1.2)

        return {"type": effect_type, **customized_spec}

    def _calculate_positioning(
        self,
        text_zone: tuple[float, float, float, float],
        canvas_size: tuple[int, int],
        platform_preset: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate precise text positioning with micro-adjustments"""

        canvas_width, canvas_height = canvas_size

        # Convert zone to pixels
        x1 = int(text_zone[0] * canvas_width)
        y1 = int(text_zone[1] * canvas_height)
        x2 = int(text_zone[2] * canvas_width)
        y2 = int(text_zone[3] * canvas_height)

        text_width = x2 - x1
        text_height = y2 - y1

        # Add platform-specific micro-adjustments
        adjustments = platform_preset.get("position_adjustments", {})

        # Apply micro-adjustments
        if "horizontal_offset" in adjustments:
            offset = int(adjustments["horizontal_offset"] * canvas_width)
            x1 += offset
            x2 += offset

        if "vertical_offset" in adjustments:
            offset = int(adjustments["vertical_offset"] * canvas_height)
            y1 += offset
            y2 += offset

        return {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "text_width": text_width,
            "text_height": text_height,
            "center_x": (x1 + x2) // 2,
            "center_y": (y1 + y2) // 2,
        }

    def _load_font_with_fallback(self, font_spec: dict[str, Any]) -> ImageFont.ImageFont:
        """Load font with intelligent fallback system"""

        font_size = font_spec["size"]

        # Try primary font
        try:
            font_path = f"{font_spec['family']}.ttf"
            return ImageFont.truetype(font_path, font_size)
        except:
            pass

        # Try fallback fonts
        for fallback in font_spec.get("fallbacks", ["Arial", "Helvetica"]):
            try:
                return ImageFont.truetype(f"{fallback}.ttf", font_size)
            except:
                continue

        # Ultimate fallback
        try:
            return ImageFont.truetype("Arial.ttf", font_size)
        except:
            return ImageFont.load_default()

    def _wrap_text_intelligently(
        self, text: str, font: ImageFont.ImageFont, max_width: int
    ) -> list[str]:
        """Wrap text with intelligent line breaking"""

        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            bbox = font.getbbox(test_line)
            line_width = bbox[2] - bbox[0]

            if line_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
                    current_line = []

        if current_line:
            lines.append(" ".join(current_line))

        return lines if lines else [text]

    def _calculate_line_positions(
        self, lines: list[str], font: ImageFont.ImageFont, positioning: dict[str, Any]
    ) -> list[tuple[int, int]]:
        """Calculate precise position for each text line"""

        line_height = int(font.size * 1.2)  # 20% line spacing
        total_height = len(lines) * line_height

        # Vertical centering
        start_y = positioning["center_y"] - total_height // 2

        positions = []
        for i, line in enumerate(lines):
            # Horizontal centering
            bbox = font.getbbox(line)
            line_width = bbox[2] - bbox[0]
            line_x = positioning["center_x"] - line_width // 2
            line_y = start_y + (i * line_height)

            positions.append((line_x, line_y))

        return positions

    def _render_clean_shadow_text(
        self,
        draw: ImageDraw.Draw,
        lines: list[str],
        positions: list[tuple[int, int]],
        font: ImageFont.ImageFont,
        colors: dict[str, Any],
        effects: dict[str, Any],
    ):
        """Render text with clean professional shadow"""

        shadow_offset = effects.get("shadow_offset", 2)
        intensity = effects.get("intensity", 0.6)

        # Calculate shadow color with alpha
        shadow_alpha = int(255 * intensity)
        shadow_color = (*colors["shadow"], shadow_alpha)

        # Draw shadow
        for line, (x, y) in zip(lines, positions):
            draw.text((x + shadow_offset, y + shadow_offset), line, font=font, fill=shadow_color)

        # Draw main text
        for line, (x, y) in zip(lines, positions):
            draw.text((x, y), line, font=font, fill=colors["primary"])

    def _render_shadow_glow_text(
        self,
        draw: ImageDraw.Draw,
        lines: list[str],
        positions: list[tuple[int, int]],
        font: ImageFont.ImageFont,
        colors: dict[str, Any],
        effects: dict[str, Any],
    ):
        """Render text with shadow and glow effects"""

        shadow_offset = effects.get("shadow_offset", 3)
        glow_radius = effects.get("glow_radius", 5)

        # Draw shadow
        for line, (x, y) in zip(lines, positions):
            draw.text(
                (x + shadow_offset, y + shadow_offset), line, font=font, fill=colors["shadow"]
            )

        # Draw glow (simplified)
        for radius in range(glow_radius, 0, -1):
            alpha = int(255 * 0.3 * (glow_radius - radius) / glow_radius)
            glow_color = (*colors["accent"], alpha)

            for line, (x, y) in zip(lines, positions):
                for dx in range(-radius, radius + 1):
                    for dy in range(-radius, radius + 1):
                        if dx**2 + dy**2 <= radius**2:
                            draw.text((x + dx, y + dy), line, font=font, fill=glow_color)

        # Draw main text
        for line, (x, y) in zip(lines, positions):
            draw.text((x, y), line, font=font, fill=colors["primary"])

    def _render_stroke_text(
        self,
        draw: ImageDraw.Draw,
        lines: list[str],
        positions: list[tuple[int, int]],
        font: ImageFont.ImageFont,
        colors: dict[str, Any],
        effects: dict[str, Any],
    ):
        """Render text with clean stroke effect"""

        stroke_width = effects.get("stroke_width", 2)

        # Draw stroke
        for line, (x, y) in zip(lines, positions):
            draw.text(
                (x, y),
                line,
                font=font,
                fill=colors["primary"],
                stroke_width=stroke_width,
                stroke_fill=colors["shadow"],
            )

    def _render_gradient_text(
        self,
        draw: ImageDraw.Draw,
        lines: list[str],
        positions: list[tuple[int, int]],
        font: ImageFont.ImageFont,
        colors: dict[str, Any],
        effects: dict[str, Any],
    ):
        """Render text with gradient effect (simplified version)"""

        # For now, render with accent color - full gradient requires more complex PIL operations
        accent_color = colors.get("accent", colors["primary"])

        # Draw shadow first
        shadow_offset = 2
        for line, (x, y) in zip(lines, positions):
            draw.text(
                (x + shadow_offset, y + shadow_offset), line, font=font, fill=colors["shadow"]
            )

        # Draw main text with accent color
        for line, (x, y) in zip(lines, positions):
            draw.text((x, y), line, font=font, fill=accent_color)

    def _render_soft_shadow_text(
        self,
        draw: ImageDraw.Draw,
        lines: list[str],
        positions: list[tuple[int, int]],
        font: ImageFont.ImageFont,
        colors: dict[str, Any],
        effects: dict[str, Any],
    ):
        """Render text with soft subtle shadow"""

        shadow_offset = effects.get("shadow_offset", 3)
        intensity = effects.get("intensity", 0.4)

        # Draw multiple subtle shadows for softness
        for offset in range(1, shadow_offset + 1):
            alpha = int(255 * intensity * (shadow_offset - offset + 1) / shadow_offset / 2)
            shadow_color = (*colors["shadow"], alpha)

            for line, (x, y) in zip(lines, positions):
                draw.text((x + offset, y + offset), line, font=font, fill=shadow_color)

        # Draw main text
        for line, (x, y) in zip(lines, positions):
            draw.text((x, y), line, font=font, fill=colors["primary"])

    def _render_high_contrast_text(
        self,
        draw: ImageDraw.Draw,
        lines: list[str],
        positions: list[tuple[int, int]],
        font: ImageFont.ImageFont,
        colors: dict[str, Any],
        effects: dict[str, Any],
    ):
        """Render text with high contrast for difficult backgrounds"""

        stroke_width = effects.get("stroke_width", 2)
        shadow_offset = effects.get("shadow_offset", 1)

        # Draw shadow first
        for line, (x, y) in zip(lines, positions):
            draw.text(
                (x + shadow_offset, y + shadow_offset), line, font=font, fill=colors["shadow"]
            )

        # Draw text with stroke
        for line, (x, y) in zip(lines, positions):
            draw.text(
                (x, y),
                line,
                font=font,
                fill=colors["primary"],
                stroke_width=stroke_width,
                stroke_fill=colors["shadow"],
            )

    def _render_premium_subtle_text(
        self,
        draw: ImageDraw.Draw,
        lines: list[str],
        positions: list[tuple[int, int]],
        font: ImageFont.ImageFont,
        colors: dict[str, Any],
        effects: dict[str, Any],
    ):
        """Render text with subtle premium effect"""

        shadow_offset = effects.get("shadow_offset", 1)
        intensity = effects.get("intensity", 0.3)

        # Very subtle shadow
        alpha = int(255 * intensity)
        shadow_color = (*colors["shadow"], alpha)

        for line, (x, y) in zip(lines, positions):
            draw.text((x + shadow_offset, y + shadow_offset), line, font=font, fill=shadow_color)

        # Draw main text
        for line, (x, y) in zip(lines, positions):
            draw.text((x, y), line, font=font, fill=colors["primary"])

    def _calculate_luminance(self, rgb: tuple[int, int, int]) -> float:
        """Calculate relative luminance of RGB color"""
        r, g, b = [x / 255.0 for x in rgb]

        def gamma_correct(x):
            return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4

        r, g, b = map(gamma_correct, [r, g, b])
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _calculate_contrast_ratio(
        self, color1: tuple[int, int, int], color2: tuple[int, int, int]
    ) -> float:
        """Calculate WCAG contrast ratio between two colors"""
        l1 = self._calculate_luminance(color1)
        l2 = self._calculate_luminance(color2)

        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    def _generate_accent_color(
        self, bg_rgb: tuple[int, int, int], primary_rgb: tuple[int, int, int]
    ) -> tuple[int, int, int]:
        """Generate complementary accent color"""
        # Convert to HSV for easier manipulation
        h, s, v = colorsys.rgb_to_hsv(*[x / 255.0 for x in bg_rgb])

        # Generate complementary hue
        accent_h = (h + 0.5) % 1.0
        accent_s = min(1.0, s + 0.2)
        accent_v = max(0.3, min(0.9, v))

        accent_rgb = colorsys.hsv_to_rgb(accent_h, accent_s, accent_v)
        return tuple(int(x * 255) for x in accent_rgb)

    def _generate_shadow_color(self, primary_rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        """Generate appropriate shadow color"""
        if primary_rgb == (255, 255, 255):  # White text
            return (0, 0, 0)  # Black shadow
        else:  # Dark text
            return (255, 255, 255)  # White shadow

    def _calculate_readability_score(self, message: str, font_spec: dict[str, Any]) -> float:
        """Calculate readability score for the text configuration"""
        word_count = len(message.split())
        char_count = len(message)
        font_size = font_spec["size"]

        # Base score
        score = 1.0

        # Adjust for length
        if word_count <= 3:
            score += 0.2  # Short messages are more readable
        elif word_count > 6:
            score -= 0.1  # Long messages are less readable

        # Adjust for font size
        if font_size >= 60:
            score += 0.1  # Larger fonts are more readable
        elif font_size < 40:
            score -= 0.1  # Smaller fonts are less readable

        return min(1.0, max(0.0, score))

    def _load_font_library(self) -> dict[str, dict[str, str]]:
        """Load cross-platform system font library for reliable advertising typography"""
        return {
            "system_sans": {
                "extra_bold": "system-ui",
                "bold": "system-ui",
                "regular": "system-ui",
                "fallbacks": [
                    "-apple-system",
                    "BlinkMacSystemFont",
                    "Segoe UI",
                    "Roboto",
                    "Helvetica Neue",
                    "Arial",
                    "sans-serif",
                ],
            },
            "modern_sans": {
                "extra_bold": "Helvetica Neue",
                "bold": "Helvetica Neue",
                "regular": "Helvetica Neue",
                "fallbacks": ["Helvetica", "Arial", "Liberation Sans", "sans-serif"],
            },
            "clean_geometric": {
                "extra_bold": "Avenir Next",
                "bold": "Avenir Next",
                "regular": "Avenir Next",
                "fallbacks": ["Avenir", "Century Gothic", "Arial", "sans-serif"],
            },
            "premium_serif": {
                "bold": "Georgia",
                "regular": "Georgia",
                "fallbacks": ["Times New Roman", "Times", "Liberation Serif", "serif"],
            },
            "contemporary": {
                "extra_bold": "Segoe UI",
                "bold": "Segoe UI",
                "regular": "Segoe UI",
                "fallbacks": ["San Francisco", "Roboto", "Arial", "sans-serif"],
            },
            "display_impact": {
                "extra_bold": "Impact",
                "bold": "Impact",
                "regular": "Impact",
                "fallbacks": ["Arial Black", "Helvetica", "Arial", "sans-serif"],
            },
            "friendly_rounded": {
                "bold": "Trebuchet MS",
                "regular": "Trebuchet MS",
                "fallbacks": ["Lucida Grande", "Arial", "sans-serif"],
            },
            "editorial": {
                "bold": "Source Sans Pro",
                "regular": "Source Sans Pro",
                "fallbacks": ["Segoe UI", "Arial", "Liberation Sans", "sans-serif"],
            },
        }

    def _load_color_palettes(self) -> dict[str, list[str]]:
        """Load color palettes for different contexts"""
        return {
            "high_contrast": ["#FFFFFF", "#000000"],
            "warm": ["#FF6B35", "#F7931E", "#FFD23F"],
            "cool": ["#1E3A8A", "#3B82F6", "#10B981"],
            "professional": ["#374151", "#6B7280", "#F9FAFB"],
            "vibrant": ["#EF4444", "#F59E0B", "#10B981"],
        }

    def _load_text_effects(self) -> dict[str, dict[str, Any]]:
        """Load professional text effect specifications"""
        return {
            "clean_shadow": {
                "shadow_offset": 2,
                "shadow_blur": 1,
                "intensity": 0.6,
                "description": "Clean professional shadow",
            },
            "soft_shadow": {
                "shadow_offset": 3,
                "shadow_blur": 2,
                "intensity": 0.4,
                "description": "Soft subtle shadow for readability",
            },
            "stroke_text": {
                "stroke_width": 1,
                "intensity": 0.8,
                "description": "Minimal stroke outline",
            },
            "high_contrast": {
                "stroke_width": 2,
                "shadow_offset": 1,
                "intensity": 1.0,
                "description": "High contrast for difficult backgrounds",
            },
            "premium_subtle": {
                "shadow_offset": 1,
                "shadow_blur": 0,
                "intensity": 0.3,
                "description": "Subtle premium effect",
            },
        }

    def _load_platform_presets(self) -> dict[str, dict[str, Any]]:
        """Load platform-specific presets with professional advertising standards"""
        return {
            "instagram_square": {
                "name": "instagram_square",
                "preferred_font_category": "system_sans",
                "base_font_size": 120,
                "min_font_size": 24,  # WCAG large text minimum
                "max_font_size": 180,  # Reasonable max for 1x1 format
                "size_multiplier": 1.0,
                "max_words": 5,  # Instagram best practice: 5 words for headlines
                "preferred_effects": ["clean_shadow", "stroke_text"],
                "position_adjustments": {},
            },
            "instagram_story": {
                "name": "instagram_story",
                "preferred_font_category": "contemporary",
                "base_font_size": 140,
                "min_font_size": 28,  # Larger for mobile story format
                "max_font_size": 220,  # Can be larger for vertical format
                "size_multiplier": 1.3,
                "max_words": 6,  # Allow slightly more for story format
                "preferred_effects": ["soft_shadow", "clean_shadow"],
                "position_adjustments": {"vertical_offset": -0.02},
            },
            "youtube_thumbnail": {
                "name": "youtube_thumbnail",
                "preferred_font_category": "display_impact",
                "base_font_size": 160,
                "min_font_size": 32,  # Large for thumbnail visibility
                "max_font_size": 240,  # Can be very large for thumbnails
                "size_multiplier": 1.5,
                "max_words": 4,  # YouTube: very short for quick comprehension
                "preferred_effects": ["clean_shadow", "stroke_text"],
                "position_adjustments": {"horizontal_offset": 0.02},
            },
            "default": {
                "name": "default",
                "preferred_font_category": "system_sans",
                "base_font_size": 110,
                "min_font_size": 20,  # General web minimum
                "max_font_size": 200,  # General reasonable maximum
                "size_multiplier": 1.0,
                "max_words": 7,  # "7 words or less" rule for outdoor/quick reading
                "preferred_effects": ["clean_shadow"],
                "position_adjustments": {},
            },
        }

    def _load_message_variants(self) -> dict[str, dict[str, Any]]:
        """Load CPG advertising message variant templates with pricing, benefits, and catchphrases"""
        return {
            "price_promotional": {
                "variations": [
                    "SAVE 30% on {base_message}",
                    "{base_message} - Now $4.99",
                    "LIMITED TIME: {base_message} $3.49",
                    "Buy 2 Get 1 FREE - {base_message}",
                    "50% OFF {base_message}",
                    "{base_message} Starting at $2.99",
                    "SALE: {base_message} Just $4.49",
                ],
                "performance_tier": "high",
                "active": True,
            },
            "benefit_driven": {
                "variations": [
                    "{base_message} - 10x Stronger Cleaning",
                    "99.9% Effective {base_message}",
                    "{base_message} Works in 30 Seconds",
                    "Gentle yet Powerful {base_message}",
                    "{base_message} - Cuts Grease Fast",
                    "Advanced Formula {base_message}",
                    "{base_message} - Safe for All Fabrics",
                    "Pro-Strength {base_message}",
                ],
                "performance_tier": "high",
                "active": True,
            },
            "catchphrase_snappy": {
                "variations": [
                    "{base_message} That Actually Works",
                    "The Smart Choice: {base_message}",
                    "{base_message} Made Simple",
                    "Finally, {base_message} That Delivers",
                    "Breakthrough {base_message}",
                    "{base_message} - The Professional Choice",
                    "Next-Level {base_message}",
                    "Revolutionary {base_message}",
                ],
                "performance_tier": "high",
                "active": True,
            },
            "urgency_action": {
                "variations": [
                    "Don't Miss Out - {base_message}",
                    "Last Chance: {base_message}",
                    "Hurry! {base_message} While Supplies Last",
                    "Today Only: {base_message}",
                    "Limited Stock - {base_message}",
                    "Act Fast: {base_message}",
                    "Ending Soon: {base_message}",
                ],
                "performance_tier": "high",
                "active": True,
            },
            "family_focused": {
                "variations": [
                    "{base_message} - Perfect for Families",
                    "Trusted by Moms: {base_message}",
                    "{base_message} Your Family Deserves",
                    "Kid-Safe {base_message}",
                    "{base_message} - Made for Busy Parents",
                    "Family-Sized {base_message}",
                    "Gentle {base_message} for Everyone",
                ],
                "performance_tier": "medium",
                "active": True,
            },
            "seasonal_fresh": {
                "variations": [
                    "Spring Fresh {base_message}",
                    "{base_message} for Spring Cleaning",
                    "New Season, New {base_message}",
                    "Spring into Clean with {base_message}",
                    "Fresh Start with {base_message}",
                    "{base_message} - Spring Special",
                    "Refresh Your Home with {base_message}",
                ],
                "performance_tier": "seasonal",
                "active": True,
            },
            "premium_quality": {
                "variations": [
                    "Premium {base_message}",
                    "Professional-Grade {base_message}",
                    "{base_message} - Salon Quality",
                    "Luxury {base_message} at Home",
                    "Commercial-Strength {base_message}",
                    "{base_message} - Professional Results",
                    "Industrial Power {base_message}",
                ],
                "performance_tier": "high",
                "active": True,
            },
            "comparison_competitive": {
                "variations": [
                    "{base_message} vs. Leading Brand",
                    "Better Than Tide: {base_message}",
                    "{base_message} - 2x More Effective",
                    "Why Choose {base_message}?",
                    "{base_message} Outperforms Competition",
                    "Proven Better: {base_message}",
                    "{base_message} - The Clear Winner",
                ],
                "performance_tier": "medium",
                "active": True,
            },
            "testimonial_social": {
                "variations": [
                    "⭐⭐⭐⭐⭐ Rated {base_message}",
                    "Customers Love {base_message}",
                    "{base_message} - 1M+ Happy Customers",
                    "Recommended: {base_message}",
                    "#1 Choice: {base_message}",
                    "Award-Winning {base_message}",
                    "Top-Rated {base_message}",
                ],
                "performance_tier": "medium",
                "active": True,
            },
            "problem_solution": {
                "variations": [
                    "Tough Stains? Try {base_message}",
                    "{base_message} Solves Stubborn Messes",
                    "Grease Problem? {base_message}",
                    "{base_message} for Impossible Stains",
                    "When Others Fail, {base_message}",
                    "Stuck-On Food? {base_message} Works",
                    "{base_message} Tackles the Toughest Jobs",
                ],
                "performance_tier": "high",
                "active": True,
            },
        }


if __name__ == "__main__":
    """Test the Text Variant Engine"""
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Test Text Variant Engine")
    parser.add_argument("--message", default="Spring Clean Everything!", help="Test message")
    parser.add_argument("--platform", default="instagram_square", help="Target platform")
    parser.add_argument("--background", default="#2E8B57", help="Background color")
    parser.add_argument("--canvas-size", default="1080,1080", help="Canvas size (width,height)")

    args = parser.parse_args()

    canvas_size = tuple(map(int, args.canvas_size.split(",")))
    text_zone = (0.1, 0.05, 0.9, 0.4)  # Standard text zone

    # Initialize engine
    engine = TextVariantEngine()

    # Generate variant
    variant = engine.generate_text_variant(
        args.message, args.platform, args.background, canvas_size, text_zone
    )

    print("\nGenerated Text Variant:")
    print(f"Message: {variant['message']}")
    print(f"Font: {variant['font']['family']} @ {variant['font']['size']}px")
    print(f"Effect: {variant['effects']['type']}")
    print(f"Contrast Ratio: {variant['colors']['contrast_ratio']:.1f}")
    print(f"Readability Score: {variant['metadata']['readability_score']:.2f}")

    # Show available variants
    variants = engine.get_available_variants(args.message)
    print(f"\nAvailable Variants ({len(variants)}):")
    for i, var in enumerate(variants[:5]):  # Show first 5
        print(f"  {i+1}. {var['message']} (ID: {var['id']})")
