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
        "1x1": "1:1",      # Square (1080x1080)
        "9x16": "9:16",    # Vertical/Stories (1080x1920)
        "16x9": "16:9",    # Horizontal/Landscape (1920x1080)
        "4x5": "4:5",      # Portrait (864x1080)
        "5x4": "5:4",      # Landscape (1350x1080)
        "3x4": "3:4",      # Vertical (810x1080)
        "4x3": "4:3",      # Horizontal (1440x1080)
        "2x3": "2:3",      # Vertical (720x1080)
        "3x2": "3:2",      # Horizontal (1620x1080)
        "21x9": "21:9",    # Cinematic (2520x1080)
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
            logger.info("GeminiImageGenerator initialized with Nano Banana (Gemini 2.5 Flash Image)")
        else:
            logger.info("GeminiImageGenerator initialized in dry-run mode (client not initialized)")

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
    ) -> Image.Image:
        """
        Generate complete product creative with text in ONE API call.

        This replaces the entire pipeline:
        - Product generation (was DALL-E)
        - Background removal (was rembg)
        - Scene generation (was DALL-E)
        - Compositing (was PIL)
        - Text overlay (now native, was PIL)

        Args:
            product_name: Product name/description
            campaign_message: Text to overlay on image
            scene_description: Scene/background context
            aspect_ratio: Ratio key (1x1, 9x16, 16x9, etc.)
            theme: Optional theme (e.g., "modern", "vintage", "minimalist")
            color_scheme: Optional color scheme (e.g., "warm", "cool", "vibrant")
            region: Regional aesthetic (US, LATAM, APAC, EMEA)
            variant_id: Variant identifier for text positioning variety

        Returns:
            PIL Image object with product, scene, and text overlay
        """
        prompt = self._build_unified_prompt(
            product_name=product_name,
            campaign_message=campaign_message,
            scene_description=scene_description,
            theme=theme,
            color_scheme=color_scheme,
            region=region,
            variant_id=variant_id,
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

    def _build_unified_prompt(
        self,
        product_name: str,
        campaign_message: str,
        scene_description: str,
        theme: str | None = None,
        color_scheme: str | None = None,
        region: str = "US",
        variant_id: str = "variant_1",
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
        # Regional aesthetic mappings
        regional_aesthetics = {
            "US": "clean modern American aesthetic, bright natural lighting, contemporary home setting",
            "LATAM": "warm vibrant family aesthetic, natural sunlight, tropical warmth, colorful accents",
            "APAC": "minimalist clean aesthetic, zen organized environment, soft neutral tones",
            "EMEA": "sophisticated European modern style, premium materials, refined elegance",
        }

        aesthetic = regional_aesthetics.get(region, regional_aesthetics["US"])

        # Text positioning variants for A/B testing
        text_positions = {
            "variant_1": "top center of the image, leaving product clearly visible below",
            "variant_2": "bottom of the image, with product featured prominently above",
            "variant_3": "upper left corner with dynamic diagonal text layout, product right-of-center",
            "variant_4": "centered vertically on the left side, product on right side",
            "variant_5": "top right corner, product featured left and center",
        }

        text_position = text_positions.get(variant_id, text_positions["variant_1"])

        # Build comprehensive unified prompt
        prompt_parts = [
            f"Create a professional advertising creative featuring {product_name}.",
            f"\nScene & Background: {scene_description}",
            f"\nAesthetic Style: {aesthetic}",
        ]

        if theme:
            prompt_parts.append(f"\nTheme: {theme} style with matching visual elements")

        if color_scheme:
            prompt_parts.append(f"\nColor Scheme: {color_scheme} tones and palette")

        # Critical: Text overlay instructions
        prompt_parts.append(f"""
\nText Overlay Requirements:
- Display the text: "{campaign_message}"
- Position: {text_position}
- Typography: Bold, modern sans-serif font, highly readable
- Size: Large and prominent (12-15% of image height)
- Color: Bright white with subtle dark outline/shadow for contrast
- Ensure text is clearly legible against the background
- Text should be perfectly spelled as written above

\nComposition Guidelines:
- Product should be hero-sized (60-70% of frame) and clearly visible
- Professional product photography lighting with natural shadows
- Product centered or positioned to balance with text
- Scene elements should complement but not overpower the product
- Ensure the product packaging and branding are sharp and detailed
- Natural, realistic rendering with photographic quality
- Clean, high-end advertising aesthetic suitable for social media

\nQuality: Ultra high resolution, professional advertising photography, magazine-quality output
""")

        prompt = "".join(prompt_parts).strip()

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Generated prompt:\n{prompt}")

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
