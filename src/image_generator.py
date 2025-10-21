#!/usr/bin/env python3
"""
Image Generator - DALL-E 3 Integration for Product and Scene Generation

Generates product images on white backgrounds and regional scene backgrounds
for component-based creative composition.
"""
import logging
import os
import time
from io import BytesIO
from pathlib import Path

import requests
from openai import OpenAI
from PIL import Image

logger = logging.getLogger(__name__)


class ImageGenerator:
    """DALL-E 3 image generation for products and scenes"""

    def __init__(self, api_key: str | None = None):
        """
        Initialize image generator with OpenAI API key.

        Args:
            api_key: OpenAI API key (uses OPENAI_API_KEY env var if not provided)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")

        self.client = OpenAI(api_key=self.api_key)
        logger.info("ImageGenerator initialized with DALL-E 3")

    def generate_product_on_white(self, product_name: str, size: str = "1024x1024") -> Image.Image:
        """
        Generate product image on pure white background.

        Creates clean product photography suitable for background removal
        and component-based composition.

        Args:
            product_name: Product name/description
            size: Image size (1024x1024, 1024x1792, 1792x1024)

        Returns:
            PIL Image object
        """
        prompt = self._build_product_prompt(product_name)

        logger.info(f"Generating product on white: {product_name}")
        start_time = time.time()

        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url
            image_data = self._download_image(image_url)

            generation_time = time.time() - start_time
            logger.info(f"✓ Generated product in {generation_time:.1f}s: {product_name}")

            return image_data

        except Exception as e:
            logger.error(f"Failed to generate product {product_name}: {e}")
            raise

    def generate_scene_background(
        self, region: str, scene_type: str = "lifestyle", size: str = "1024x1024"
    ) -> Image.Image:
        """
        Generate regional scene background WITHOUT product.

        Creates lifestyle/home interior scenes with regional aesthetics
        for product composition.

        Args:
            region: Target region (LATAM, APAC, EMEA, NA)
            scene_type: Scene category (lifestyle, kitchen, home)
            size: Image size

        Returns:
            PIL Image object
        """
        prompt = self._build_scene_prompt(region, scene_type)

        logger.info(f"Generating scene background: {region} {scene_type}")
        start_time = time.time()

        try:
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url
            image_data = self._download_image(image_url)

            generation_time = time.time() - start_time
            logger.info(f"✓ Generated scene in {generation_time:.1f}s: {region} {scene_type}")

            return image_data

        except Exception as e:
            logger.error(f"Failed to generate scene {region}/{scene_type}: {e}")
            raise

    def generate_contextual_background(
        self,
        product_category: str,
        product_name: str,
        region: str = "US",
        size: str = "1024x1024",
        style: str = "scene",
    ) -> Image.Image:
        """
        Generate contextual background based on product category with variety options.

        Creates contextually relevant backgrounds that enhance product messaging:
        - scene: Full lifestyle/home contexts (default)
        - gradient: Smooth color gradients matching brand/category
        - split_screen: Before/after, dirty/clean comparisons
        - objects_only: Contextual elements only (bubbles, clothes, dishes)
        - solid: Solid color backgrounds

        Args:
            product_category: Product category (Laundry Detergent, Dish Soap, etc.)
            product_name: Specific product name for context
            region: Regional aesthetic preferences
            size: Image size
            style: Background style (scene, gradient, split_screen, objects_only, solid)

        Returns:
            PIL Image object with contextual background
        """
        logger.info(f"Generating {style} background: {product_category} for {product_name}")
        start_time = time.time()

        try:
            # Handle different background styles
            if style == "solid":
                # Use category-appropriate solid colors
                color = self._get_category_color(product_category)
                return self.generate_solid_color_background(color, size)

            elif style == "gradient":
                return self._generate_gradient_background(product_category, size)

            elif style == "split_screen":
                prompt = self._build_split_screen_prompt(product_category, product_name, region)

            elif style == "objects_only":
                prompt = self._build_objects_only_prompt(product_category, product_name, region)

            else:  # Default to "scene"
                prompt = self._build_contextual_prompt(product_category, product_name, region)

            # Generate image with DALL-E for non-solid styles
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality="standard",
                n=1,
            )

            image_url = response.data[0].url
            image_data = self._download_image(image_url)

            generation_time = time.time() - start_time
            logger.info(
                f"✓ Generated {style} background in {generation_time:.1f}s: {product_category}"
            )

            return image_data

        except Exception as e:
            logger.error(f"Failed to generate {style} background for {product_category}: {e}")
            # Fallback to solid color
            logger.info("Falling back to solid color background")
            color = self._get_category_color(product_category)
            return self.generate_solid_color_background(color, size)

    def generate_solid_color_background(
        self, color: str = "#2E8B57", size: str = "1024x1024"
    ) -> Image.Image:
        """
        Generate solid color background using PIL.

        Creates clean solid color backgrounds perfect for social media ads
        that can be easily resized and maintain quality.

        Args:
            color: Hex color code (e.g., "#2E8B57")
            size: Image size (1024x1024, 1024x1792, 1792x1024)

        Returns:
            PIL Image object with solid color background
        """
        # Parse size
        if size == "1024x1024":
            width, height = 1024, 1024
        elif size == "1024x1792":
            width, height = 1024, 1792
        elif size == "1792x1024":
            width, height = 1792, 1024
        else:
            width, height = 1024, 1024  # Default

        logger.info(f"Generating solid color background: {color}")
        start_time = time.time()

        try:
            # Create solid color image
            image = Image.new("RGB", (width, height), color)

            generation_time = time.time() - start_time
            logger.info(f"✓ Generated solid background in {generation_time:.3f}s: {color}")

            return image

        except Exception as e:
            logger.error(f"Failed to generate solid color {color}: {e}")
            raise

    def _build_product_prompt(self, product_name: str) -> str:
        """Build optimized prompt for product on white background"""
        prompt = f"""Professional product photography of {product_name} centered on pure white background.
Studio lighting with soft shadows. Product bottle/container prominently displayed, sharp focus,
high detail, clear branding and labeling. Product name "{product_name}" clearly visible and
correctly spelled on packaging. Clean centered composition perfect for cutout and background
removal. No additional props, no scene context, just the product on solid white background.
Ultra high resolution commercial product shot."""

        return prompt

    def _build_scene_prompt(self, region: str, scene_type: str) -> str:
        """Build optimized prompt for regional scene background"""
        regional_aesthetics = {
            "LATAM": "warm vibrant colors, family-friendly home interior, natural sunlight streaming through windows, tropical plants, wooden textures, welcoming atmosphere",
            "APAC": "minimalist modern interior, clean zen aesthetic, soft natural light, bamboo elements, neutral tones, serene peaceful atmosphere",
            "EMEA": "elegant sophisticated interior, premium materials, cool professional tones, contemporary European design, refined minimalist style",
            "NA": "modern comfortable home interior, bright natural lighting, clean contemporary design, warm inviting atmosphere",
        }

        aesthetic = regional_aesthetics.get(region, "modern clean interior design")

        prompt = f"""Beautiful {region} home interior scene, {aesthetic}.
{scene_type.title()} setting with empty countertop or surface in foreground,
perfect for product placement. Professional architectural photography style,
high-end home magazine quality. NO products visible, clean empty surface ready
for composition. Photorealistic lighting and textures. Ultra high resolution
interior design photography."""

        return prompt

    def _build_contextual_prompt(
        self, product_category: str, product_name: str, region: str
    ) -> str:
        """Build contextual background prompt based on product category"""

        # Regional aesthetic modifiers
        regional_aesthetics = {
            "US": "clean modern American home aesthetic, bright natural lighting",
            "LATAM": "warm vibrant family home, natural sunlight, tropical warmth",
            "APAC": "minimalist clean aesthetic, organized serene environment",
            "EMEA": "sophisticated European modern style, premium materials",
        }

        aesthetic = regional_aesthetics.get(region, "clean modern home aesthetic")

        # Category-specific contextual elements
        contextual_prompts = {
            "Laundry Detergent": f"""Beautiful laundry room or bedroom scene with {aesthetic}.
                Soft pile of freshly washed white cotton clothes, gentle soap bubbles floating in air,
                sparkling clean white towels and shirts, subtle steam rising suggesting freshness and cleanliness.
                Bright clean surfaces, organized laundry basket with white linens.
                Professional lifestyle photography showing the results of effective laundry care.
                No product visible, clean empty space in center for product placement.
                Emphasizes cleanliness, freshness, and fabric care.""",
            "Dish Soap": f"""Beautiful modern kitchen scene with {aesthetic}.
                Sparkling clean white dishes, glasses, and silverware stacked neatly,
                iridescent soap bubbles catching light, crystal clear water droplets on clean surfaces,
                pristine white plates and bowls showing grease-free cleanliness.
                Clean granite or marble countertop with subtle shine, organized dish drying area.
                Professional lifestyle photography showing the results of effective dish cleaning.
                No product visible, clean empty space in center for product placement.
                Emphasizes grease-cutting power and dish cleanliness.""",
            "Hair Care": f"""Beautiful modern bathroom scene with {aesthetic}.
                Soft fluffy white towels, gentle flowing water, steam suggesting warmth and comfort,
                clean bathroom surfaces with marble or granite textures, natural sunlight through frosted windows.
                Subtle hair care elements like clean combs, but no products visible.
                Professional lifestyle photography emphasizing cleanliness and personal care.
                Clean empty space in center for product placement.
                Emphasizes hair health and beauty care.""",
            "General CPG": f"""Beautiful modern home interior with {aesthetic}.
                Clean organized living space, bright natural lighting, pristine surfaces,
                subtle elements suggesting home care and family life.
                Professional lifestyle photography with premium home magazine quality.
                No products visible, clean empty space in center for product placement.
                Emphasizes quality, cleanliness, and modern family living.""",
        }

        # Get contextual prompt or fallback to general
        context_prompt = contextual_prompts.get(product_category, contextual_prompts["General CPG"])

        # Build complete prompt
        prompt = f"""{context_prompt}

        Ultra high resolution lifestyle photography, professional lighting, photorealistic textures.
        Clean composition perfect for product overlay. NO text, NO branding, NO products in scene.
        Focus on creating the perfect contextual environment that enhances the story of {product_name}."""

        return prompt.strip()

    def _get_category_color(self, product_category: str) -> str:
        """Get category-appropriate solid color"""
        category_colors = {
            "Laundry Detergent": "#4A90E2",  # Clean blue
            "Dish Soap": "#50C878",  # Fresh green
            "Hair Care": "#9B59B6",  # Elegant purple
            "Oral Care": "#3498DB",  # Fresh blue
            "Personal Care": "#E67E22",  # Warm orange
            "General CPG": "#2E8B57",  # Sea green (default)
        }
        return category_colors.get(product_category, "#2E8B57")

    def _generate_gradient_background(self, product_category: str, size: str) -> Image.Image:
        """Generate gradient background using PIL"""
        # Parse size
        if size == "1024x1024":
            width, height = 1024, 1024
        elif size == "1024x1792":
            width, height = 1024, 1792
        elif size == "1792x1024":
            width, height = 1792, 1024
        else:
            width, height = 1024, 1024  # Default

        # Get category-specific gradient colors
        gradient_colors = {
            "Laundry Detergent": ("#E3F2FD", "#1976D2"),  # Light blue to blue
            "Dish Soap": ("#E8F5E8", "#2E7D32"),  # Light green to green
            "Hair Care": ("#F3E5F5", "#7B1FA2"),  # Light purple to purple
            "Oral Care": ("#E1F5FE", "#0277BD"),  # Light cyan to blue
            "Personal Care": ("#FFF3E0", "#F57C00"),  # Light orange to orange
            "General CPG": ("#F1F8E9", "#388E3C"),  # Light green to green (default)
        }

        start_color, end_color = gradient_colors.get(
            product_category, gradient_colors["General CPG"]
        )

        logger.info(f"Generating gradient background: {start_color} to {end_color}")

        # Create gradient
        image = Image.new("RGB", (width, height))
        pixels = image.load()

        # Convert hex to RGB
        start_rgb = tuple(int(start_color[i : i + 2], 16) for i in (1, 3, 5))
        end_rgb = tuple(int(end_color[i : i + 2], 16) for i in (1, 3, 5))

        # Create vertical gradient
        for y in range(height):
            # Calculate gradient position (0 to 1)
            ratio = y / height

            # Interpolate colors
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)

            # Fill entire row with this color
            for x in range(width):
                pixels[x, y] = (r, g, b)

        return image

    def _build_split_screen_prompt(
        self, product_category: str, product_name: str, region: str
    ) -> str:
        """Build split-screen before/after prompt"""

        regional_aesthetic = {
            "US": "clean modern American aesthetic",
            "LATAM": "warm vibrant family aesthetic",
            "APAC": "minimalist organized aesthetic",
            "EMEA": "sophisticated European aesthetic",
        }.get(region, "clean modern aesthetic")

        split_screen_prompts = {
            "Laundry Detergent": f"""Split-screen comparison image with {regional_aesthetic}.
                LEFT SIDE: Pile of dirty, stained white clothes and towels with visible dirt marks and wrinkles.
                RIGHT SIDE: Same clothes now perfectly clean, bright white, neatly folded and organized.
                Center dividing line clearly separating before and after. Professional laundry commercial photography style.
                No products visible, clean empty space in center foreground for product placement.
                Emphasizes dramatic cleaning transformation and effectiveness.""",
            "Dish Soap": f"""Split-screen comparison image with {regional_aesthetic}.
                LEFT SIDE: Stack of dirty dishes with grease stains, food residue, and soap scum on plates and glasses.
                RIGHT SIDE: Same dishes now sparkling clean, crystal clear glasses, spotless white plates gleaming.
                Center dividing line clearly separating before and after. Professional kitchen commercial photography.
                No products visible, clean empty space in center foreground for product placement.
                Emphasizes grease-cutting power and dish cleaning effectiveness.""",
            "Hair Care": f"""Split-screen comparison image with {regional_aesthetic}.
                LEFT SIDE: Dull, tangled, dry hair strands showing damage and lack of shine.
                RIGHT SIDE: Silky, shiny, healthy hair with perfect texture and lustrous appearance.
                Center dividing line clearly separating before and after. Professional beauty commercial photography.
                No products visible, clean empty space in center foreground for product placement.
                Emphasizes hair transformation and care benefits.""",
            "General CPG": f"""Split-screen comparison image with {regional_aesthetic}.
                LEFT SIDE: Messy, disorganized home environment with clutter and dullness.
                RIGHT SIDE: Clean, organized, bright home space showing improvement and care.
                Center dividing line clearly separating before and after. Professional lifestyle photography.
                No products visible, clean empty space in center foreground for product placement.
                Emphasizes improvement and transformation benefits.""",
        }

        prompt = split_screen_prompts.get(product_category, split_screen_prompts["General CPG"])

        return f"""{prompt}

        Ultra high resolution commercial photography, professional lighting, dramatic before/after contrast.
        Clean composition perfect for product overlay. NO text, NO branding, NO products in scene.
        Focus on creating compelling visual proof of {product_name} effectiveness.""".strip()

    def _build_objects_only_prompt(
        self, product_category: str, product_name: str, region: str
    ) -> str:
        """Build objects-only background prompt"""

        objects_prompts = {
            "Laundry Detergent": """Floating collection of clean laundry elements on clean white background.
                Soft white cotton clothes gently floating, iridescent soap bubbles of various sizes,
                sparkling water droplets catching light, fresh white towels and shirts,
                subtle steam wisps suggesting cleanliness and freshness. Clean organized composition
                with plenty of white space in center for product placement. Professional commercial photography
                emphasizing cleanliness, freshness, and fabric care through floating elements only.""",
            "Dish Soap": """Floating collection of clean kitchen elements on clean white background.
                Sparkling clean white plates, crystal clear glasses, soap bubbles with rainbow reflections,
                pristine silverware gleaming, water droplets on surfaces, subtle light reflections.
                Clean organized composition with plenty of white space in center for product placement.
                Professional commercial photography emphasizing grease-cutting and dish cleanliness
                through floating clean elements only.""",
            "Hair Care": """Floating collection of hair care elements on clean white background.
                Silky hair strands with natural shine, gentle water droplets, soft white towels,
                natural botanical elements like aloe or herbs, subtle steam suggesting warmth.
                Clean organized composition with plenty of white space in center for product placement.
                Professional beauty photography emphasizing hair health and natural care
                through floating elements only.""",
            "Oral Care": """Floating collection of oral care elements on clean white background.
                Sparkling white teeth illustrations, fresh mint leaves, clean water droplets,
                bright white foam bubbles, subtle fresh breath visualizations.
                Clean organized composition with plenty of white space in center for product placement.
                Professional dental commercial photography emphasizing oral health and freshness
                through floating elements only.""",
            "General CPG": """Floating collection of clean home elements on clean white background.
                Pristine white surfaces, gentle light reflections, sparkling clean textures,
                subtle fresh air visualizations, organized home care elements.
                Clean organized composition with plenty of white space in center for product placement.
                Professional lifestyle photography emphasizing cleanliness and home care
                through floating elements only.""",
        }

        prompt = objects_prompts.get(product_category, objects_prompts["General CPG"])

        return f"""{prompt}

        Ultra high resolution commercial photography, professional studio lighting, crisp white background.
        Elements appear to float naturally without surfaces. Clean composition perfect for product overlay.
        NO text, NO branding, NO products in scene. Focus on creating contextual floating elements
        that enhance the story of {product_name} effectiveness.""".strip()

    def _download_image(self, image_url: str) -> Image.Image:
        """Download and convert image from URL to PIL Image"""
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()

            image = Image.open(BytesIO(response.content))

            # Ensure RGB mode
            if image.mode != "RGB":
                image = image.convert("RGB")

            return image

        except Exception as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
            raise


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Generate product or scene images")
    parser.add_argument("type", choices=["product", "scene"], help="Generation type")
    parser.add_argument("name", help="Product name or region")
    parser.add_argument(
        "--scene-type", default="lifestyle", help="Scene type (for scene generation)"
    )
    parser.add_argument("--output", "-o", default="test_output", help="Output directory")

    args = parser.parse_args()

    # Initialize generator
    generator = ImageGenerator()

    # Generate based on type
    if args.type == "product":
        print(f"Generating product: {args.name}")
        image = generator.generate_product_on_white(args.name)
        output_path = Path(args.output) / f"{args.name.replace(' ', '_').lower()}_white_bg.jpg"
    else:
        print(f"Generating scene: {args.name} {args.scene_type}")
        image = generator.generate_scene_background(args.name, args.scene_type)
        output_path = Path(args.output) / f"{args.name.lower()}_{args.scene_type}_scene.jpg"

    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, "JPEG", quality=95)

    print(f"\nSaved: {output_path}")
    print(f"Size: {image.size}")
