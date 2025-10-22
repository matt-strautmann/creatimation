#!/usr/bin/env python3
"""
Gemini Image Generator - Nano Banana (Gemini 2.5 Flash Image) Integration

Unified image generation with native text overlay, multi-image composition,
and theme/color variations in a single API call.

Replaces: ImageGenerator (DALL-E), BackgroundRemover (rembg), CreativeCompositor (PIL)
"""

import logging
import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

logger = logging.getLogger(__name__)


class GeminiImageGenerator:
    """
    Unified image generation using Gemini 2.5 Flash Image (Nano Banana).

    Combines product generation, scene composition, and text overlay into
    single API calls. Eliminates need for background removal and manual compositing.
    """

    # Gemini 2.5 Flash Image supports 10 aspect ratios
    ASPECT_RATIOS = {
        "1x1": "1:1",  # Square (1080x1080)
        "9x16": "9:16",  # Vertical/Stories (1080x1920)
        "16x9": "16:9",  # Horizontal/Landscape (1920x1080)
        "4x5": "4:5",  # Portrait (864x1080)
        "5x4": "5:4",  # Landscape (1350x1080)
        "3x4": "3:4",  # Vertical (810x1080)
        "4x3": "4:3",  # Horizontal (1440x1080)
        "2x3": "2:3",  # Vertical (720x1080)
        "3x2": "3:2",  # Horizontal (1620x1080)
        "21x9": "21:9",  # Cinematic (2520x1080)
    }

    def __init__(self, api_key: str | None = None, skip_init: bool = False):
        """
        Initialize Gemini image generator.

        Args:
            api_key: Google API key (uses GOOGLE_API_KEY env var if not provided)
            skip_init: Skip client initialization (for dry-run/testing)
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.client = None

        if not skip_init:
            if not self.api_key:
                raise ValueError("GOOGLE_API_KEY not found in environment")

            self.client = genai.Client(api_key=self.api_key)
            logger.info(
                "GeminiImageGenerator initialized with Nano Banana (Gemini 2.5 Flash Image)"
            )
        else:
            logger.info("GeminiImageGenerator initialized in dry-run mode (client not initialized)")

    def generate_product_only(
        self,
        product_name: str,
        aspect_ratio: str = "1x1",
    ) -> Image.Image:
        """
        Generate product-only image for caching and reuse.

        Creates clean product photography on neutral background for later
        composition with scenes using multi-image fusion.

        Args:
            product_name: Product name/description
            aspect_ratio: Ratio key (1x1, 9x16, 16x9, etc.)

        Returns:
            PIL Image object with product on neutral background
        """
        prompt = self._build_product_only_prompt(product_name)
        gemini_ratio = self.ASPECT_RATIOS.get(aspect_ratio, "1:1")

        logger.info(f"Generating product-only image: {product_name} ({aspect_ratio})")
        start_time = time.time()

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=gemini_ratio,
                    ),
                ),
            )

            # Extract image from response
            for part in response.parts:
                if part.inline_data is not None:
                    from io import BytesIO

                    image_data = part.inline_data.data
                    image = Image.open(BytesIO(image_data))

                    generation_time = time.time() - start_time
                    logger.info(f"✓ Generated product image in {generation_time:.1f}s")
                    logger.info(f"   Size: {image.size}")

                    return image

            raise ValueError("No image in response")

        except Exception as e:
            logger.error(f"Failed to generate product image for {product_name}: {e}")
            raise

    def generate_product_creative(
        self,
        product_name: str,
        campaign_message: str,
        scene_description: str,
        aspect_ratio: str = "1x1",
        theme: str | None = None,
        color_scheme: str | None = None,
        region: str = "US",
        variant_id: str = "variant_1",
        product_image: Image.Image | None = None,
        brand_guide: dict | None = None,
    ) -> Image.Image:
        """
        Generate complete product creative with text.

        If product_image is provided, uses multi-image fusion to compose product
        into scene. Otherwise generates unified image in one call.

        This method supports two workflows:
        1. Two-step (recommended): product_image provided → fusion with scene
        2. One-step (legacy): product_image=None → unified generation

        Args:
            product_name: Product name/description
            campaign_message: Text to overlay on image
            scene_description: Scene/background context
            aspect_ratio: Ratio key (1x1, 9x16, 16x9, etc.)
            theme: Optional theme (e.g., "modern", "vintage", "minimalist")
            color_scheme: Optional color scheme (e.g., "warm", "cool", "vibrant")
            region: Regional aesthetic (US, LATAM, APAC, EMEA)
            variant_id: Variant identifier for text positioning variety
            product_image: Pre-generated product image for fusion (optional)
            brand_guide: Brand guide dict for typography/colors (optional)

        Returns:
            PIL Image object with product, scene, and text overlay
        """
        # Use fusion workflow if product image provided
        if product_image is not None:
            return self._generate_with_fusion(
                product_image=product_image,
                campaign_message=campaign_message,
                scene_description=scene_description,
                aspect_ratio=aspect_ratio,
                theme=theme,
                color_scheme=color_scheme,
                region=region,
                variant_id=variant_id,
                brand_guide=brand_guide,
            )

        # Otherwise use legacy unified generation
        prompt = self._build_unified_prompt(
            product_name=product_name,
            campaign_message=campaign_message,
            scene_description=scene_description,
            theme=theme,
            color_scheme=color_scheme,
            region=region,
            variant_id=variant_id,
            brand_guide=brand_guide,
        )

        gemini_ratio = self.ASPECT_RATIOS.get(aspect_ratio, "1:1")

        logger.info(f"Generating {aspect_ratio} creative with Nano Banana: {product_name}")
        logger.info(f"   Message: {campaign_message}")
        logger.info(f"   Variant: {variant_id}")
        start_time = time.time()

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=gemini_ratio,
                    ),
                ),
            )

            # Extract image from response
            for part in response.parts:
                if part.inline_data is not None:
                    # Convert to PIL Image
                    from io import BytesIO

                    image_data = part.inline_data.data
                    image = Image.open(BytesIO(image_data))

                    generation_time = time.time() - start_time
                    logger.info(f"✓ Generated complete creative in {generation_time:.1f}s")
                    logger.info(f"   Size: {image.size}")

                    return image

            raise ValueError("No image in response")

        except Exception as e:
            logger.error(f"Failed to generate creative for {product_name}: {e}")
            raise

    def generate_multi_image_composition(
        self,
        images: list[Image.Image],
        composition_prompt: str,
        aspect_ratio: str = "1x1",
    ) -> Image.Image:
        """
        Compose multiple images together (up to 3 images).

        Nano Banana's native multi-image fusion capability.

        Args:
            images: List of PIL Images to compose (max 3)
            composition_prompt: How to blend/compose the images
            aspect_ratio: Output aspect ratio

        Returns:
            Composed PIL Image
        """
        if len(images) > 3:
            raise ValueError("Nano Banana supports max 3 images for composition")

        gemini_ratio = self.ASPECT_RATIOS.get(aspect_ratio, "1:1")

        logger.info(f"Composing {len(images)} images with Nano Banana")
        start_time = time.time()

        try:
            # Build contents with multiple images + prompt
            contents = [composition_prompt] + images

            response = self.client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=gemini_ratio,
                    ),
                ),
            )

            for part in response.parts:
                if part.inline_data is not None:
                    # Convert to PIL Image
                    from io import BytesIO

                    image_data = part.inline_data.data
                    image = Image.open(BytesIO(image_data))
                    generation_time = time.time() - start_time
                    logger.info(f"✓ Composed images in {generation_time:.1f}s")
                    return image

            raise ValueError("No image in response")

        except Exception as e:
            logger.error(f"Failed to compose images: {e}")
            raise

    def _generate_with_fusion(
        self,
        product_image: Image.Image,
        campaign_message: str,
        scene_description: str,
        aspect_ratio: str = "1x1",
        theme: str | None = None,
        color_scheme: str | None = None,
        region: str = "US",
        variant_id: str = "variant_1",
        brand_guide: dict | None = None,
    ) -> Image.Image:
        """
        Generate creative using multi-image fusion.

        Composes pre-generated product image into scene with text overlay.

        Args:
            product_image: Pre-generated product image
            campaign_message: Text to overlay
            scene_description: Scene context
            aspect_ratio: Output aspect ratio
            theme: Optional theme
            color_scheme: Optional color scheme
            region: Regional aesthetic
            variant_id: Variant identifier
            brand_guide: Brand guide dict

        Returns:
            Composed PIL Image
        """
        prompt = self._build_fusion_prompt(
            campaign_message=campaign_message,
            scene_description=scene_description,
            theme=theme,
            color_scheme=color_scheme,
            region=region,
            variant_id=variant_id,
            brand_guide=brand_guide,
        )

        gemini_ratio = self.ASPECT_RATIOS.get(aspect_ratio, "1:1")

        logger.info(f"Composing {aspect_ratio} creative via fusion")
        logger.info(f"   Message: {campaign_message}")
        logger.info(f"   Variant: {variant_id}")
        start_time = time.time()

        try:
            # Multi-image fusion: product + prompt
            contents = [product_image, prompt]

            response = self.client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=gemini_ratio,
                    ),
                ),
            )

            # Extract image from response
            for part in response.parts:
                if part.inline_data is not None:
                    from io import BytesIO

                    image_data = part.inline_data.data
                    image = Image.open(BytesIO(image_data))

                    generation_time = time.time() - start_time
                    logger.info(f"✓ Composed creative via fusion in {generation_time:.1f}s")
                    logger.info(f"   Size: {image.size}")

                    return image

            raise ValueError("No image in response")

        except Exception as e:
            logger.error(f"Failed to compose creative via fusion: {e}")
            raise

    def _build_unified_prompt(
        self,
        product_name: str,
        campaign_message: str,
        scene_description: str,
        theme: str | None = None,
        color_scheme: str | None = None,
        region: str = "US",
        variant_id: str = "variant_1",
        brand_guide: dict | None = None,
    ) -> str:
        """
        Build comprehensive prompt for unified generation.

        This prompt handles:
        - Product rendering
        - Scene/background context
        - Text overlay positioning
        - Theme and color variations
        - Regional aesthetics
        """
        # AI-first approach: Let Gemini infer appropriate aesthetic unless brand guide specifies
        aesthetic_style = None
        if brand_guide and "regional_guidelines" in brand_guide:
            regional_guide = brand_guide["regional_guidelines"].get(region, {})
            if "visual_preference" in regional_guide:
                aesthetic_style = regional_guide["visual_preference"]

        # AI-first approach: Let Gemini determine optimal text positioning unless brand guide specifies
        text_position = None
        if brand_guide and "variants" in brand_guide and variant_id in brand_guide["variants"]:
            variant_spec = brand_guide["variants"][variant_id]
            text_position = variant_spec.get("text_positioning") or variant_spec.get(
                "text_treatment"
            )

        # Build AI-first prompt: minimal base + explicit brand guide specifications
        prompt_parts = [f"Create a professional advertising creative featuring {product_name}."]

        # Add scene description if provided
        if scene_description:
            prompt_parts.append(f"\nScene & Background: {scene_description}")

        # Add aesthetic style only if explicitly specified in brand guide
        if aesthetic_style:
            prompt_parts.append(f"\nAesthetic Style: {aesthetic_style}")

        # Add theme if provided
        if theme:
            prompt_parts.append(f"\nTheme: {theme} style with matching visual elements")

        # Add color scheme if provided
        if color_scheme:
            prompt_parts.append(f"\nColor Scheme: {color_scheme} tones and palette")

        # Get typography from brand guide if available
        typography_style = "bold modern sans-serif font"
        if brand_guide and "typography" in brand_guide:
            font_family = brand_guide["typography"].get("font_family", "")
            if font_family:  # Only split if font_family is not empty
                font_family = font_family.split(",")[0]
                font_weight = brand_guide["typography"].get("font_weight", "700")
                weight_desc = "bold" if font_weight in ["700", "bold"] else "regular"
                typography_style = f"{weight_desc} {font_family} font style"

        # Build text overlay instructions - AI-first approach
        text_overlay_parts = [
            f'- Display the text: "{campaign_message}"',
            f"- Typography: {typography_style}, clean and professional",
            "- Size: Large and prominent (12-15% of image height)",
            "- Style: Clean, modern advertising typography with crisp edges",
            "- Color: High contrast against background (white on dark, dark on light)",
            "- NO heavy outlines, NO thick shadows - use subtle drop shadow only if needed for legibility",
            "- Professional advertising quality text rendering",
            "- Text should be perfectly spelled as written above",
        ]

        # Only specify position if explicitly defined in brand guide
        if text_position:
            text_overlay_parts.insert(1, f"- Position: {text_position}")

        prompt_parts.append("\nText Overlay Requirements:\n" + "\n".join(text_overlay_parts))

        prompt_parts.append(
            """
\nComposition Guidelines:
- Product should be hero-sized (60-70% of frame) and clearly visible
- Professional product photography lighting with natural shadows
- Product centered or positioned to balance with text
- Scene elements should complement but not overpower the product
- Ensure the product packaging and branding are sharp and detailed
- Natural, realistic rendering with photographic quality
- Clean, high-end advertising aesthetic suitable for social media

\nQuality: Ultra high resolution, professional advertising photography, magazine-quality output
"""
        )

        prompt = "".join(prompt_parts).strip()

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Generated prompt:\n{prompt}")

        return prompt

    def _build_fusion_prompt(
        self,
        campaign_message: str,
        scene_description: str,
        theme: str | None = None,
        color_scheme: str | None = None,
        region: str = "US",
        variant_id: str = "variant_1",
        brand_guide: dict | None = None,
    ) -> str:
        """
        Build prompt for multi-image fusion.

        This prompt guides fusion of product image with scene and text overlay.

        Args:
            campaign_message: Text to overlay
            scene_description: Scene context
            theme: Optional theme
            color_scheme: Optional color scheme
            region: Regional aesthetic
            variant_id: Variant identifier
            brand_guide: Brand guide dict

        Returns:
            Fusion prompt string
        """
        # Regional aesthetic mappings
        regional_aesthetics = {
            "US": "clean modern American aesthetic, bright natural lighting, contemporary home setting",
            "LATAM": "warm vibrant family aesthetic, natural sunlight, tropical warmth, colorful accents",
            "APAC": "minimalist clean aesthetic, zen organized environment, soft neutral tones",
            "EMEA": "sophisticated European modern style, premium materials, refined elegance",
        }

        aesthetic = regional_aesthetics.get(region, regional_aesthetics["US"])

        # Get text positioning from brand guide or variant
        text_position = "bottom of the image, with product prominently featured above"
        if brand_guide and "visual" in brand_guide:
            position = brand_guide["visual"].get("text_positioning", "bottom")
            position_map = {
                "top": "top of the image, with product featured below",
                "bottom": "bottom of the image, with product prominently featured above",
                "center": "centered, with product balanced around it",
                "left": "left side, with product on the right",
                "right": "right side, with product on the left",
            }
            text_position = position_map.get(position, text_position)

        # Get typography from brand guide
        typography_style = "bold modern sans-serif font"
        if brand_guide and "typography" in brand_guide:
            font_family = brand_guide["typography"].get("font_family", "")
            if font_family:  # Only split if font_family is not empty
                font_family = font_family.split(",")[0]
                font_weight = brand_guide["typography"].get("font_weight", "700")
                weight_desc = "bold" if font_weight in ["700", "bold"] else "regular"
                typography_style = f"{weight_desc} {font_family} font style"

        # Get brand colors
        color_scheme_text = color_scheme or ""
        if brand_guide and "colors" in brand_guide:
            primary = brand_guide["colors"].get("primary", "")
            accent = brand_guide["colors"].get("accent", "")
            if primary and accent:
                color_scheme_text = f"Primary brand color {primary}, accent {accent} for highlights"

        # Build fusion prompt
        prompt_parts = [
            "Compose this product into a professional advertising creative.",
            f"\nScene & Background: {scene_description}",
            f"\nAesthetic Style: {aesthetic}",
        ]

        if theme:
            prompt_parts.append(f"\nTheme: {theme} style with matching visual elements")

        if color_scheme_text:
            prompt_parts.append(f"\nColor Scheme: {color_scheme_text}")

        # Get variant-specific composition from brand guide
        composition_instructions = "Place the product as the hero element (60-70% of frame)"
        layout_instructions = "Professional product photography lighting"

        # Debug logging for brand guide variant application
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"DEBUG: variant_id = {variant_id}")
            logger.debug(f"DEBUG: brand_guide type = {type(brand_guide)}")
            if brand_guide:
                logger.debug(f"DEBUG: brand_guide keys = {list(brand_guide.keys())}")
                if "variants" in brand_guide:
                    logger.debug(
                        f"DEBUG: variants available = {list(brand_guide['variants'].keys())}"
                    )

        if brand_guide and "variants" in brand_guide and variant_id in brand_guide["variants"]:
            variant_spec = brand_guide["variants"][variant_id]
            variant_composition = variant_spec.get("composition", "")
            variant_layout = variant_spec.get("layout_style", "")

            logger.info(f"🎯 Applying variant composition: {variant_composition}")
            logger.info(f"🎯 Applying variant layout: {variant_layout}")

            if variant_composition:
                # Use brand guide composition directly with generic enhancement
                composition_instructions = variant_composition
                # Add universal instruction to avoid literal text labels in before/after compositions
                if any(
                    word in variant_composition.lower()
                    for word in ["left", "right", "before", "after"]
                ):
                    composition_instructions += "\nIMPORTANT: Show transformation visually without text labels like 'BEFORE', 'AFTER', or directional words"
            if variant_layout:
                layout_instructions = f"{variant_layout} with {layout_instructions}"
        else:
            logger.warning(f"⚠️ No variant composition found for {variant_id} in brand guide")

        # Text overlay instructions
        prompt_parts.append(
            f"""
\nText Overlay:
- Display the text: "{campaign_message}"
- Position: {text_position}
- Typography: {typography_style}, clean and professional
- Size: Large and prominent (12-15% of image height)
- Style: Clean, modern advertising typography with crisp edges
- Color: High contrast against background
- NO heavy outlines, NO thick shadows - subtle drop shadow only if needed
- Professional advertising quality text rendering

\nComposition:
- {composition_instructions}
- {layout_instructions}
- Scene elements complement but don't overpower product
- Natural, realistic rendering with photographic quality
- Clean, high-end advertising aesthetic for social media

\nQuality: Ultra high resolution, professional advertising photography"""
        )

        prompt = "".join(prompt_parts).strip()

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Generated fusion prompt:\n{prompt}")

        return prompt

    def _build_product_only_prompt(self, product_name: str) -> str:
        """Build prompt for product-only generation (if needed for caching)"""
        prompt = f"""Professional product photography of {product_name}.

Studio lighting with soft shadows. Product bottle/container prominently displayed,
sharp focus, high detail, clear branding and labeling. Product name clearly visible
and correctly spelled on packaging.

Clean centered composition on neutral background. Ultra high resolution commercial
product photography suitable for advertising."""

        return prompt


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Generate images with Gemini Nano Banana")
    parser.add_argument("product", help="Product name/description")
    parser.add_argument("message", help="Campaign message text")
    parser.add_argument(
        "--scene",
        default="modern home interior with clean countertop",
        help="Scene description",
    )
    parser.add_argument(
        "--ratio",
        "-r",
        default="1x1",
        choices=list(GeminiImageGenerator.ASPECT_RATIOS.keys()),
        help="Aspect ratio",
    )
    parser.add_argument("--theme", help="Theme style (e.g., modern, vintage)")
    parser.add_argument("--color", help="Color scheme (e.g., warm, cool, vibrant)")
    parser.add_argument("--region", default="US", help="Regional aesthetic")
    parser.add_argument("--variant", default="variant_1", help="Text variant ID")
    parser.add_argument("--output", "-o", default="test_output", help="Output directory")

    args = parser.parse_args()

    # Initialize generator
    generator = GeminiImageGenerator()

    # Generate creative
    print(f"\nGenerating creative for: {args.product}")
    print(f"Message: {args.message}")
    print(f"Ratio: {args.ratio}")

    image = generator.generate_product_creative(
        product_name=args.product,
        campaign_message=args.message,
        scene_description=args.scene,
        aspect_ratio=args.ratio,
        theme=args.theme,
        color_scheme=args.color,
        region=args.region,
        variant_id=args.variant,
    )

    # Save output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    product_slug = args.product.lower().replace(" ", "_")
    output_path = output_dir / f"{product_slug}_{args.ratio}_{args.variant}.jpg"

    image.save(output_path, "JPEG", quality=95)

    print(f"\n✓ Saved: {output_path}")
    print(f"  Size: {image.size}")
