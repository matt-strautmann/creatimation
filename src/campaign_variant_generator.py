#!/usr/bin/env python3
"""
Campaign Variant Generator - Expand Simple Briefs into Full Campaign Specifications

Takes simple campaign briefs and intelligently expands them into comprehensive
campaign variant specifications with backgrounds, text variants, layouts,
regional adaptations, and cached asset references.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CampaignVariantGenerator:
    """
    Intelligent campaign brief expansion engine

    Transforms simple briefs into comprehensive campaign variant specifications
    with context-rich generation parameters, cached asset references, and
    multi-variant optimization strategies.
    """

    def __init__(self, cache_dir: str = "cache"):
        """Initialize with cache directory for asset management"""
        self.cache_dir = Path(cache_dir)
        self.regional_aesthetics = self._load_regional_aesthetics()
        self.product_contexts = self._load_product_contexts()
        logger.info("CampaignVariantGenerator initialized with asset cache")

    def generate_campaign_variants(
        self, simple_brief: dict[str, Any], cached_assets: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """
        Generate comprehensive campaign variant specification from simple brief

        Args:
            simple_brief: Simple campaign brief (products, region, message, etc.)
            cached_assets: Optional dict of cached asset paths by product

        Returns:
            Full campaign variant specification with all generation parameters
        """
        logger.info(f"🎨 Generating campaign variants for: {simple_brief.get('campaign_id')}")

        # Detect cached assets if not provided
        if not cached_assets:
            cached_assets = self._detect_cached_assets(simple_brief.get("products", []))

        # Build comprehensive campaign spec
        campaign_variants = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": f"Generated Campaign Variants - {simple_brief.get('campaign_id', 'Unknown')}",
            "description": "AI-generated comprehensive campaign specification from simple brief",
            "generated_at": datetime.now().isoformat(),
            "source_brief": simple_brief,
            # Enhanced brand meta
            "brand_meta": self._generate_brand_meta(simple_brief),
            # Campaign metadata with variants
            "campaign_meta": self._generate_campaign_meta(simple_brief),
            # Regional context and aesthetics
            "regional_context": self._generate_regional_context(simple_brief),
            # Visual concept with backgrounds and layouts
            "visual_concept": self._generate_visual_concept(simple_brief),
            # Text elements with variants
            "text_elements": self._generate_text_elements(simple_brief),
            # Campaign text with social variants
            "campaign_text": self._generate_campaign_text(simple_brief),
            # Product specifications with cached assets
            "products": simple_brief.get("products", []),
            "cached_assets": cached_assets,
            # Context mapping for generation
            "context_mapping": self._generate_context_mapping(simple_brief),
            # Comprehensive variant options
            "variant_options": self._generate_variant_options(simple_brief),
            # Background and scene specifications
            "background_specifications": self._generate_background_specs(simple_brief),
            # Layout specifications for intelligent adaptation
            "layout_specifications": self._generate_layout_specs(simple_brief),
            # Generation parameters
            "generation_parameters": self._generate_generation_params(simple_brief, cached_assets),
        }

        logger.info(
            f"✓ Generated {len(campaign_variants.get('variant_options', {}).get('headline_variants', []))} headline variants"
        )
        logger.info(
            f"✓ Generated {len(campaign_variants.get('variant_options', {}).get('background_variants', []))} background variants"
        )
        logger.info(
            f"✓ Generated {len(campaign_variants.get('layout_specifications', {}))} layout specifications"
        )

        return campaign_variants

    def save_campaign_variants(
        self, campaign_variants: dict[str, Any], output_path: str | None = None
    ) -> str:
        """Save campaign variants to JSON file"""

        if not output_path:
            campaign_id = campaign_variants.get("source_brief", {}).get("campaign_id", "unknown")
            timestamp = int(time.time())
            output_path = self.cache_dir / "variants" / f"{campaign_id}_variants_{timestamp}.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(campaign_variants, f, indent=2)

        logger.info(f"💾 Saved campaign variants: {output_path}")
        return str(output_path)

    def _detect_cached_assets(self, products: list[str]) -> dict[str, str]:
        """Detect cached product assets for products"""
        cached_assets = {}
        products_cache = self.cache_dir / "products"

        if not products_cache.exists():
            logger.warning("No products cache directory found")
            return cached_assets

        for product in products:
            product_slug = self._slugify(product)

            # Find matching cached asset
            for asset_file in products_cache.glob(f"{product_slug}_transparent_*.png"):
                cached_assets[product] = str(asset_file)
                logger.info(f"   ✓ Found cached asset: {product} → {asset_file.name}")
                break

        return cached_assets

    def _generate_brand_meta(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate enhanced brand metadata"""
        products = brief.get("products", [])
        primary_product = products[0] if products else "Unknown Product"

        # Extract product name - handle both string and dict formats
        if isinstance(primary_product, dict):
            product_name = primary_product.get("name", "Unknown Product")
        else:
            product_name = primary_product if primary_product else "Unknown Product"

        # Extract brand name from first product
        brand_name = product_name.split()[0] if product_name else "Brand"

        return {
            "brand_name": brand_name,
            "brand_tone": "confident",
            "brand_colors": ["#2E8B57", "#FFFFFF", "#FFD700"],  # Default CPG colors
            "primary_product_category": self._infer_product_category(product_name),
            "brand_promise": "Quality products for modern families",
            "brand_values": ["quality", "effectiveness", "family-safe"],
        }

    def _generate_campaign_meta(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate campaign metadata with platform specifications"""
        campaign_id = brief.get("campaign_id", "generated_campaign")

        return {
            "campaign_name": campaign_id.replace("_", " ").title(),
            "concept_type": "ProductRange",
            "objective": brief.get(
                "target_audience", "Engage target audience with compelling product messaging"
            ),
            "platforms": ["Instagram", "TikTok", "Meta Ads", "YouTube"],
            "aspect_ratios": ["1:1", "9:16", "16:9"],
            "campaign_duration": "30 days",
            "performance_targets": {
                "reach": "1M+",
                "engagement_rate": "3.5%+",
                "conversion_rate": "2.1%+",
            },
        }

    def _generate_regional_context(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate regional context and localization rules"""
        region = brief.get("target_region", "US")

        regional_data = self.regional_aesthetics.get(region, self.regional_aesthetics["US"])

        return {
            "region_code": region,
            "language": "en-US",  # Default to English
            "localized_copy_rules": f"Use clear, confident language appropriate for {region} market",
            "regional_colors": regional_data.get("colors", ["#2E8B57", "#FFFFFF", "#FFD700"]),
            "cultural_considerations": regional_data.get("cultural_notes", []),
            "legal_requirements": regional_data.get("legal_requirements", []),
        }

    def _generate_visual_concept(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate visual concept with solid color backgrounds and simple product placement"""
        brief.get("products", [])
        region = brief.get("target_region", "US")

        # Get regional colors for backgrounds
        regional_colors = self.regional_aesthetics.get(region, {}).get(
            "colors", ["#FFFFFF", "#F5F5F5"]
        )

        return {
            "layout_style": "hero_product",
            "background_style": "solid_color",
            "composition_description": "Clean solid color background with single product prominently featured",
            "visual_prompt_template": "Social media advertisement featuring [product_name]. Clean solid [background_color] background. Single product prominently centered and displayed. Text '[headline_text]' in bold, clear typography. [aspect_ratio] format. Professional product photography style, clean and minimal.",
            "scene_specifications": {
                "background_type": "solid_color",
                "background_colors": regional_colors,
                "product_presentation": "clean and centered",
                "text_style": "bold typography with high contrast",
                "overall_style": "minimal and professional",
            },
        }

    def _generate_text_elements(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate text elements with hierarchy and styling"""
        campaign_message = brief.get("campaign_message", "Quality Products")

        return {
            "headline_text": campaign_message,
            "subhead_text": f"Everything you need for {brief.get('target_audience', 'modern families')}",
            "cta_text": "Shop Now",
            "font_style": "Clean sans-serif, bold",
            "text_color": "#FFFFFF",
            "text_hierarchy": {
                "primary": campaign_message,
                "secondary": "Trusted quality",
                "tertiary": "Shop Now",
            },
            "text_styling": {
                "headline_size": "large",
                "headline_weight": "bold",
                "contrast_requirement": "4.5:1 minimum",
            },
        }

    def _generate_campaign_text(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate campaign text with social media variants"""
        campaign_message = brief.get("campaign_message", "Quality Products")
        products = brief.get("products", [])

        return {
            "caption_text": f"{campaign_message} Perfect for {brief.get('target_audience', 'busy families')}! ✨",
            "hashtags": [
                f"#{brief.get('campaign_id', 'campaign').replace('_', '')}",
                "#QualityProducts",
                "#Home",
                (
                    "#Cleaning"
                    if any("soap" in p.lower() or "detergent" in p.lower() for p in products)
                    else "#Products"
                ),
            ],
            "cta_url": f"https://brand.com/{brief.get('campaign_id', 'products')}",
            "tone_descriptor": "confident and trustworthy",
            "social_variants": {
                "instagram": f"{campaign_message} ✨",
                "tiktok": f"POV: {campaign_message.lower()} 🙌",
                "facebook": f"Introducing {campaign_message} - perfect for families!",
            },
        }

    def _generate_context_mapping(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate simplified context mapping for solid color background AI generation"""
        products = brief.get("products", [])
        region = brief.get("target_region", "US")

        primary_product = products[0] if products else "Unknown"
        # Extract product name - handle both string and dict formats
        if isinstance(primary_product, dict):
            product_name = primary_product.get("name", "Unknown")
        else:
            product_name = primary_product if primary_product else "Unknown"

        product_category = self._infer_product_category(product_name)
        context = self.product_contexts.get(product_category, {})
        regional_colors = self.regional_aesthetics.get(region, {}).get("colors", ["#FFFFFF"])

        return {
            "background_type": "solid_color",
            "background_colors": regional_colors,
            "placement": context.get("placement", "Single product prominently centered"),
            "demonstration": context.get("demonstration", "Simple product showcase"),
            "text_focus": context.get("text_focus", "Key product benefit"),
            "functional_elements": context.get("functional_elements", "Clean, minimal styling"),
            "regional_aesthetic": f"{region} - solid color with regional brand colors",
            "placement_rules": "Single product centered and prominently displayed, no floating elements",
            "composition_rules": {
                "product_prominence": "70% visibility in frame",
                "background_simplicity": "100% solid color",
                "text_contrast": "High contrast text overlay for readability",
            },
        }

    def _generate_variant_options(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate comprehensive variant options for A/B testing"""
        campaign_message = brief.get("campaign_message", "Quality Products")
        region = brief.get("target_region", "US")

        # Generate headline variants
        campaign_message.split()
        headline_variants = [
            campaign_message,  # Original
            f"Discover {campaign_message}",  # Discovery variant
            f"{campaign_message} - Trusted Quality",  # Trust variant
            f"Experience {campaign_message}",  # Experience variant
        ]

        return {
            "headline_variants": headline_variants,
            "color_variants": [
                "#2E8B57",  # Primary green
                "#1E40AF",  # Professional blue
                "#DC2626",  # Attention red
                "#059669",  # Fresh green
            ],
            "layout_variants": ["hero_product", "split_visual", "minimal_text"],
            "background_variants": [
                "solid_color",
                "gradient_simple",
                "clean_minimal",
                "brand_color",
            ],
            "regional_variants": {
                region: {
                    "aesthetic": self.regional_aesthetics.get(region, {}).get(
                        "description", "Modern"
                    ),
                    "colors": self.regional_aesthetics.get(region, {}).get("colors", ["#FFFFFF"]),
                    "cultural_elements": self.regional_aesthetics.get(region, {}).get(
                        "cultural_notes", []
                    ),
                }
            },
            "size_variants": {
                "1x1": {"focus": "centered_product", "text_position": "bottom"},
                "9x16": {"focus": "vertical_stack", "text_position": "top"},
                "16x9": {"focus": "side_by_side", "text_position": "left"},
            },
        }

    def _generate_background_specs(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate simplified background specifications for solid color generation"""
        products = brief.get("products", [])
        region = brief.get("target_region", "US")

        primary_product = products[0] if products else "Unknown"
        # Extract product name - handle both string and dict formats
        if isinstance(primary_product, dict):
            product_name = primary_product.get("name", "Unknown")
        else:
            product_name = primary_product if primary_product else "Unknown"

        product_category = self._infer_product_category(product_name)
        context = self.product_contexts.get(product_category, {})
        regional_colors = self.regional_aesthetics.get(region, {}).get("colors", ["#FFFFFF"])

        return {
            "background_types": {
                "primary": {
                    "type": "solid_color",
                    "colors": regional_colors,
                    "description": "Clean solid color background",
                    "style": "minimal and professional",
                },
                "alternative": {
                    "type": "gradient_simple",
                    "colors": regional_colors[:2],
                    "description": "Simple two-color gradient",
                    "style": "subtle gradient transition",
                },
            },
            "product_demonstration": {
                "focus": context.get("demonstration", "Simple product showcase"),
                "functional_elements": context.get("functional_elements", "Clean, minimal styling"),
                "text_focus": context.get("text_focus", "Key product benefit"),
            },
            "regional_adaptations": {
                region: {
                    "primary_colors": regional_colors,
                    "aesthetic": "solid color with regional brand colors",
                    "style_notes": self.regional_aesthetics.get(region, {}).get(
                        "cultural_notes", []
                    ),
                }
            },
            "cache_strategy": {
                "background_cache_key": f"{product_category}_{region}_solid",
                "color_variations": regional_colors,
                "reuse_policy": "cache_for_24h",
            },
        }

    def _generate_layout_specs(self, brief: dict[str, Any]) -> dict[str, Any]:
        """Generate layout specifications for intelligent adaptation from external config"""
        # Load layout rules from external file
        layout_rules_path = self.cache_dir / "layouts" / "layout_rules.json"

        if layout_rules_path.exists():
            with open(layout_rules_path) as f:
                layout_config = json.load(f)

            # Convert external format to internal format
            layout_specs = {}
            for ratio, rule in layout_config.get("layout_rules", {}).items():
                layout_specs[ratio] = {
                    "product_zone": rule.get("product_zone", [0.2, 0.2, 0.8, 0.8]),
                    "text_zone": rule.get("text_zone", [0.1, 0.05, 0.9, 0.15]),
                    "product_scale": rule.get("product_size_factor", 0.6),
                    "text_scale": rule.get("text_size_factor", 1.0),
                    "platform_optimization": rule.get("platform", "instagram_feed"),
                }

            logger.info(f"✓ Loaded layout specs from external config: {len(layout_specs)} ratios")
            return layout_specs
        else:
            # Fallback to hardcoded specs if external file doesn't exist
            logger.warning("Layout rules file not found, using fallback hardcoded specs")
            return {
                "1x1": {
                    "product_zone": [0.2, 0.2, 0.8, 0.8],
                    "text_zone": [0.1, 0.05, 0.9, 0.15],
                    "product_scale": 0.6,
                    "text_scale": 1.0,
                    "platform_optimization": "instagram_feed",
                },
                "9x16": {
                    "product_zone": [0.2, 0.5, 0.8, 0.9],
                    "text_zone": [0.1, 0.1, 0.9, 0.45],
                    "product_scale": 0.6,
                    "text_scale": 1.2,
                    "platform_optimization": "instagram_stories",
                },
                "16x9": {
                    "product_zone": [0.55, 0.2, 0.9, 0.8],
                    "text_zone": [0.05, 0.3, 0.5, 0.7],
                    "product_scale": 0.6,
                    "text_scale": 1.4,
                    "platform_optimization": "youtube_thumbnail",
                },
            }

    def _generate_generation_params(
        self, brief: dict[str, Any], cached_assets: dict[str, str]
    ) -> dict[str, Any]:
        """Generate AI generation parameters and cache strategy"""
        return {
            "asset_strategy": {
                "use_cached_products": True,
                "cached_assets": cached_assets,
                "generate_backgrounds": True,
                "cache_new_assets": True,
            },
            "generation_quality": {
                "image_quality": "high",
                "resolution": "1024x1024_minimum",
                "aspect_ratio_handling": "intelligent_adaptation",
                "text_rendering": "high_contrast",
            },
            "performance_targets": {
                "generation_time": "under_60s_per_variant",
                "cache_hit_rate": "70%+",
                "file_size": "300-500kb_per_creative",
            },
            "validation_rules": {
                "brand_compliance": "check_colors_and_contrast",
                "text_readability": "minimum_4.5_contrast_ratio",
                "product_visibility": "minimum_60%_of_frame",
            },
        }

    def _infer_product_category(self, product_name: str) -> str:
        """Infer product category from name"""
        product_lower = product_name.lower()

        if any(word in product_lower for word in ["detergent", "laundry", "wash"]):
            return "Laundry Detergent"
        elif any(word in product_lower for word in ["dish", "soap", "kitchen"]):
            return "Dish Soap"
        elif any(word in product_lower for word in ["shampoo", "conditioner", "hair"]):
            return "Hair Care"
        else:
            return "General CPG"

    def _slugify(self, text: str) -> str:
        """Convert text to URL-friendly slug"""
        return text.lower().replace(" ", "-").replace("&", "and")

    def _load_product_contexts(self) -> dict[str, dict[str, str]]:
        """Load simplified product context mappings for solid color backgrounds"""
        return {
            "Laundry Detergent": {
                "background": "Clean solid color background",
                "placement": "Single product bottle prominently centered",
                "demonstration": "Before/after clothes comparison - dirty vs clean white fabrics",
                "text_focus": "Cleaning power and effectiveness",
                "functional_elements": "Clean white clothes, stain removal results",
            },
            "Dish Soap": {
                "background": "Clean solid color background",
                "placement": "Single product bottle prominently centered",
                "demonstration": "Clean sparkling dishes or grease-cutting action",
                "text_focus": "Grease-cutting power and dish cleanliness",
                "functional_elements": "Sparkling clean dishes, soap bubbles",
            },
            "General CPG": {
                "background": "Clean solid color background",
                "placement": "Single product prominently centered",
                "demonstration": "Product benefit visualization",
                "text_focus": "Key product benefit",
                "functional_elements": "Clean, minimal styling",
            },
        }

    def _load_regional_aesthetics(self) -> dict[str, dict[str, Any]]:
        """Load regional aesthetic mappings"""
        return {
            "US": {
                "description": "Clean modern aesthetic with natural lighting and contemporary design",
                "colors": ["#2E8B57", "#FFFFFF", "#FFD700"],
                "cultural_notes": ["family-oriented", "efficiency-focused", "clean and simple"],
                "legal_requirements": ["EPA Safer Choice", "Child-safe packaging"],
            },
            "LATAM": {
                "description": "Warm vibrant colors, natural sunlight, tropical plants, family-oriented spaces",
                "colors": ["#FF6B35", "#F7931E", "#FFD23F"],
                "cultural_notes": [
                    "family-centered",
                    "warm and welcoming",
                    "vibrant and energetic",
                ],
                "legal_requirements": ["Local safety standards", "Multi-language labeling"],
            },
            "APAC": {
                "description": "Clean whites, soft pastels, natural wood tones, organized spaces, quality appliances",
                "colors": ["#1E3A8A", "#F8FAFC", "#10B981"],
                "cultural_notes": [
                    "quality-focused",
                    "efficiency and precision",
                    "minimal and organized",
                ],
                "legal_requirements": ["Quality certifications", "Dermatologically tested"],
            },
            "EMEA": {
                "description": "Sophisticated greys, deep blues, premium whites, contemporary design",
                "colors": ["#374151", "#1E40AF", "#F9FAFB"],
                "cultural_notes": [
                    "premium and sophisticated",
                    "environmental consciousness",
                    "design-forward",
                ],
                "legal_requirements": ["EU regulations", "Eco-label compliance"],
            },
        }


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="Generate campaign variants from simple brief")
    parser.add_argument("brief_path", help="Path to simple campaign brief JSON")
    parser.add_argument("--output", "-o", help="Output path for campaign variants JSON")
    parser.add_argument("--cache-dir", default="cache", help="Cache directory path")

    args = parser.parse_args()

    # Load simple brief
    with open(args.brief_path) as f:
        simple_brief = json.load(f)

    # Generate campaign variants
    generator = CampaignVariantGenerator(cache_dir=args.cache_dir)
    campaign_variants = generator.generate_campaign_variants(simple_brief)

    # Save campaign variants
    output_path = generator.save_campaign_variants(campaign_variants, args.output)

    print(f"\n✓ Generated campaign variants: {output_path}")
    print(
        f"✓ Headline variants: {len(campaign_variants.get('variant_options', {}).get('headline_variants', []))}"
    )
    print(
        f"✓ Background variants: {len(campaign_variants.get('variant_options', {}).get('background_variants', []))}"
    )
    print(f"✓ Layout specifications: {len(campaign_variants.get('layout_specifications', {}))}")
