"""
Refactored Creative Pipeline with Dependency Injection.

This module contains the main pipeline orchestrator that follows SOLID principles
and uses dependency injection for better testability and maintainability.
"""

import logging
import time
from pathlib import Path
from typing import Any

from PIL import Image

try:
    from ..core.interfaces import (
        BrandGuideLoaderInterface,
        BriefLoaderInterface,
        CacheManagerInterface,
        ImageGeneratorInterface,
        OutputManagerInterface,
        StateTrackerInterface,
    )
    from ..core.models import CampaignBrief, CreativeSpec, GenerationResult, PipelineState
except ImportError:
    # Fallback for direct execution
    from src.core.interfaces import (
        BrandGuideLoaderInterface,
        BriefLoaderInterface,
        CacheManagerInterface,
        ImageGeneratorInterface,
        OutputManagerInterface,
        StateTrackerInterface,
    )
    from src.core.models import CampaignBrief, CreativeSpec, GenerationResult, PipelineState

logger = logging.getLogger(__name__)


class CreativePipeline:
    """
    Main pipeline orchestrator with dependency injection.

    This class coordinates the entire creative generation process
    while maintaining loose coupling with its dependencies.
    """

    def __init__(
        self,
        cache_manager: CacheManagerInterface,
        output_manager: OutputManagerInterface,
        image_generator: ImageGeneratorInterface,
        brief_loader: BriefLoaderInterface,
        brand_guide_loader: BrandGuideLoaderInterface,
        state_tracker: StateTrackerInterface,
        no_cache: bool = False,
        dry_run: bool = False,
    ):
        """Initialize pipeline with injected dependencies."""
        self.cache_manager = cache_manager
        self.output_manager = output_manager
        self.image_generator = image_generator
        self.brief_loader = brief_loader
        self.brand_guide_loader = brand_guide_loader
        self.state_tracker = state_tracker

        self.no_cache = no_cache
        self.dry_run = dry_run

        # Default aspect ratios (PRD requirement)
        self.default_aspect_ratios = ["1x1", "9x16", "16x9"]

        logger.info("🚀 CreativePipeline initialized with dependency injection")

    def process_campaign(
        self, brief_path: str, brand_guide_path: str | None = None, resume: bool = False
    ) -> dict[str, Any]:
        """
        Process a complete campaign brief.

        Args:
            brief_path: Path to campaign brief JSON file
            brand_guide_path: Optional path to brand guide YAML file
            resume: Whether to resume from previous state

        Returns:
            Campaign processing results
        """
        # Load and validate brief
        brief_data = self.brief_loader.load_brief(brief_path)
        campaign_brief = CampaignBrief.from_dict(brief_data)

        # Store brief directory for asset path resolution and campaign context
        self._brief_dir = Path(brief_path).parent
        self._current_campaign_id = campaign_brief.campaign_id

        # Load brand guide if provided
        brand_guide = None
        if brand_guide_path:
            brand_guide = self.brand_guide_loader.load_brand_guide(brand_guide_path)

        # Initialize pipeline state
        pipeline_state = self._initialize_pipeline_state(campaign_brief)

        if self.dry_run:
            return self._dry_run_preview(campaign_brief, pipeline_state)

        logger.info(f"\n{'=' * 60}")
        logger.info(f"CAMPAIGN: {campaign_brief.campaign_id}")
        logger.info(f"{'=' * 60}")

        # Process campaign
        try:
            results = self._process_campaign_products(
                campaign_brief, brand_guide, pipeline_state, resume
            )

            # Mark pipeline complete
            pipeline_state.end_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.state_tracker.update_product_state("_pipeline", pipeline_state.__dict__)

            return results

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            pipeline_state.errors.append(str(e))
            raise

    def _process_campaign_products(
        self,
        campaign_brief: CampaignBrief,
        brand_guide: dict[str, Any] | None,
        pipeline_state: PipelineState,
        resume: bool,
    ) -> dict[str, Any]:
        """Process all products in the campaign."""
        results = {
            "campaign_id": campaign_brief.campaign_id,
            "target_regions": campaign_brief.target_regions,
            "products_processed": [],
            "total_creatives": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "processing_time": 0,
        }

        start_time = time.time()
        products = campaign_brief.products
        total_products = len(products)

        for idx, product in enumerate(products, 1):
            product_name = self._extract_product_name(product)
            self._slugify(product_name)

            logger.info(f"\n[{idx}/{total_products}] 🎨 Processing: {product_name}")
            logger.info("-" * 60)

            try:
                product_results = self._process_single_product(
                    product, campaign_brief, brand_guide, pipeline_state
                )

                results["total_creatives"] += product_results["creatives_generated"]
                results["cache_hits"] += product_results["cache_hits"]
                results["cache_misses"] += product_results["cache_misses"]
                results["products_processed"].append(product_name)

                # Update pipeline state
                pipeline_state.processed_products += 1
                pipeline_state.generated_creatives += product_results["creatives_generated"]

            except Exception as e:
                logger.error(f"❌ Failed to process {product_name}: {e}")
                pipeline_state.errors.append(f"{product_name}: {str(e)}")

        results["processing_time"] = time.time() - start_time
        return results

    def _process_single_product(
        self,
        product: Any,
        campaign_brief: CampaignBrief,
        brand_guide: dict[str, Any] | None,
        pipeline_state: PipelineState,
    ) -> dict[str, Any]:
        """Process a single product across all regions and variants."""
        product_name = self._extract_product_name(product)
        product_slug = self._slugify(product_name)

        # Step 1: Get or generate product image (cache for reuse across ALL regions)
        # ✨ KEY INNOVATION: Generate product ONCE → fuse into 72 regional scenes
        product_image = self._get_or_generate_product_image(product, product_slug)

        # Extract creative requirements
        creative_reqs = campaign_brief.creative_requirements
        aspect_ratios = creative_reqs.get("aspect_ratios", self.default_aspect_ratios)
        variant_types = creative_reqs.get("variant_types", [])
        variant_themes = creative_reqs.get("variant_themes", {})
        variant_color_rules = creative_reqs.get("variant_color_rules", {})

        # Build scene description and color scheme
        scene_description = self._build_scene_description(campaign_brief)
        base_color_scheme = self._get_color_scheme(campaign_brief)

        product_results = {
            "creatives_generated": 0,
            "cache_hits": (
                1 if self._is_cache_hit(product_name) or self._has_provided_image(product) else 0
            ),
            "cache_misses": (
                0 if self._is_cache_hit(product_name) or self._has_provided_image(product) else 1
            ),
        }

        # Step 2: Generate variants for all regions
        for region in campaign_brief.target_regions:
            logger.info(f"   🌍 Region: {region}")

            # Get regional adaptations
            region_config = campaign_brief.regional_adaptations.get(region, None)
            if region_config:
                region_cta = region_config.call_to_action
            else:
                region_cta = campaign_brief.enhanced_context.get("call_to_action", "Learn More")

            for ratio in aspect_ratios:
                logger.info(f"      🎨 Generating {ratio} creatives...")

                for variant_type in variant_types:
                    logger.info(f"         📐 {variant_type}...")

                    # Create creative specification
                    creative_spec = CreativeSpec(
                        product_name=product_name,
                        campaign_message=region_cta,
                        aspect_ratio=ratio,
                        region=region,
                        variant_type=variant_type,
                        template=campaign_brief.enhanced_context.get(
                            "layout_style", "hero-product"
                        ),
                        theme=variant_themes.get(variant_type),
                        color_scheme=self._apply_color_rules(
                            base_color_scheme, variant_type, variant_color_rules, brand_guide
                        ),
                        scene_description=scene_description,
                    )

                    # Generate creative
                    result = self._generate_single_creative(
                        creative_spec, product_image, campaign_brief, brand_guide
                    )

                    if result.success:
                        product_results["creatives_generated"] += 1
                        logger.info(f"            ✓ Saved: {Path(result.output_path).name}")
                    else:
                        logger.error(f"            ❌ Failed: {result.error_message}")

        return product_results

    def _generate_single_creative(
        self,
        spec: CreativeSpec,
        product_image: Image.Image,
        campaign_brief: CampaignBrief,
        brand_guide: dict[str, Any] | None,
    ) -> GenerationResult:
        """Generate a single creative asset."""
        try:
            start_time = time.time()

            # Generate creative using image generator
            final_image = self.image_generator.generate_product_creative(
                product_name=spec.product_name,
                campaign_message=spec.campaign_message,
                scene_description=spec.scene_description,
                aspect_ratio=spec.aspect_ratio,
                theme=spec.theme,
                color_scheme=spec.color_scheme,
                region=spec.region,
                variant_id=spec.variant_type,
                product_image=product_image,
                brand_guide=brand_guide,
            )

            # Build metadata
            metadata = {
                "campaign_id": campaign_brief.campaign_id,
                "product": spec.product_name,
                "product_slug": self._slugify(spec.product_name),
                "ratio": spec.aspect_ratio,
                "variant_id": spec.variant_type,
                "campaign_message": spec.campaign_message,
                "generation_method": "gemini_fusion",
                "theme": spec.theme,
                "color_scheme": spec.color_scheme,
                "region": spec.region,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Save output
            output_path = self.output_manager.save_creative(
                final_image,
                spec.product_name,
                spec.aspect_ratio,
                metadata,
                spec.template,
                spec.region,
                variant_id=spec.variant_type,
            )

            # Cache the output creative for potential reuse
            if not self.no_cache:
                cache_key = f"creative:{self._slugify(spec.product_name)}:{spec.region}:{spec.aspect_ratio}:{spec.variant_type}"
                self.cache_manager.register_cache_entry(
                    cache_key=cache_key,
                    file_path=output_path,
                    metadata={
                        "type": "creative_output",
                        "product_name": spec.product_name,
                        "campaign_id": campaign_brief.campaign_id,
                        "region": spec.region,
                        "aspect_ratio": spec.aspect_ratio,
                        "variant_type": spec.variant_type,
                        "template": spec.template,
                        "generated_at": metadata["generated_at"],
                    }
                )

            processing_time = time.time() - start_time

            return GenerationResult(
                success=True,
                output_path=output_path,
                metadata=metadata,
                processing_time=processing_time,
            )

        except Exception as e:
            return GenerationResult(success=False, error_message=str(e))

    def _get_or_generate_product_image(self, product: Any, product_slug: str) -> Image.Image:
        """
        Get product image from pre-provided source, cache, or generate new one.

        🚀 KEY INNOVATION: Intelligent image sourcing with perfect consistency
        Priority: Brief Image → Cache → Generation
        """
        product_name = self._extract_product_name(product)

        # 🎯 STEP 1: Check if brief provides product image (HIGHEST PRIORITY)
        if isinstance(product, dict):
            # Support multiple field names for maximum compatibility
            product_image_path = (
                product.get("image")
                or product.get("image_path")
                or product.get("asset_path")
                or product.get("product_image")
                or product.get("asset_url")
            )
            if product_image_path:
                try:
                    image_path = Path(product_image_path)

                    # Try multiple path resolution strategies
                    search_paths = []

                    if image_path.is_absolute():
                        search_paths.append(image_path)
                    else:
                        # Strategy 1: Relative to brief directory
                        brief_dir = getattr(self, '_brief_dir', Path.cwd())
                        search_paths.append(brief_dir / image_path)

                        # Strategy 2: Relative to project root (cwd)
                        search_paths.append(Path.cwd() / image_path)

                        # Strategy 3: As-is (for edge cases)
                        search_paths.append(image_path)

                    # Try each path until we find the file
                    found_path = None
                    for candidate_path in search_paths:
                        if candidate_path.exists():
                            found_path = candidate_path
                            break

                    if found_path:
                        logger.info(f"   🎨 Using provided product image: {product_name}")
                        logger.info(f"       Source: {found_path}")
                        product_image = Image.open(found_path)

                        # Cache the provided image for future efficiency
                        if not self.no_cache:
                            self._cache_product_image(product_name, product_slug, product_image)

                        return product_image
                    else:
                        logger.warning(f"   ⚠ Provided image not found: {product_image_path}")
                        logger.warning(f"       Searched locations:")
                        for i, path in enumerate(search_paths, 1):
                            logger.warning(f"         {i}. {path}")
                except Exception as e:
                    logger.warning(f"   ⚠ Failed to load provided image '{product_image_path}': {e}")

        # 🎯 STEP 2: Check cache for existing product image
        if not self.no_cache:
            product_entry = self._lookup_cached_product(product_name)
            if product_entry:
                cache_path = Path(product_entry["file_path"])
                if cache_path.exists():
                    logger.info(f"   ✓ Loaded product from cache: {product_name}")
                    return Image.open(cache_path)

        # 🎯 STEP 3: Generate new product image (FALLBACK)
        logger.info(f"   🎨 Generating product image: {product_name}")
        product_image = self.image_generator.generate_product_only(
            product_name=product_name,
            aspect_ratio="1x1",  # Standard square for products
        )

        # Save to cache for future efficiency
        if not self.no_cache:
            self._cache_product_image(product_name, product_slug, product_image)

        return product_image

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def _initialize_pipeline_state(self, campaign_brief: CampaignBrief) -> PipelineState:
        """Initialize pipeline state tracking."""
        total_creatives = self._calculate_total_creatives(campaign_brief)

        return PipelineState(
            campaign_id=campaign_brief.campaign_id,
            total_products=len(campaign_brief.products),
            processed_products=0,
            total_creatives=total_creatives,
            generated_creatives=0,
            cache_hits=0,
            cache_misses=0,
            errors=[],
            start_time=time.strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _calculate_total_creatives(self, campaign_brief: CampaignBrief) -> int:
        """Calculate expected total number of creatives."""
        creative_reqs = campaign_brief.creative_requirements
        num_products = len(campaign_brief.products)
        num_regions = len(campaign_brief.target_regions)
        num_ratios = len(creative_reqs.get("aspect_ratios", self.default_aspect_ratios))
        num_variants = len(creative_reqs.get("variant_types", []))

        return num_products * num_regions * num_ratios * num_variants

    def _extract_product_name(self, product: Any) -> str:
        """Extract product name from brief product entry."""
        if isinstance(product, str):
            return product
        elif isinstance(product, dict):
            return product.get("name", str(product))
        else:
            return str(product)

    def _build_scene_description(self, campaign_brief: CampaignBrief) -> str:
        """Build scene description from campaign brief."""
        enhanced_context = campaign_brief.enhanced_context or {}

        setting = enhanced_context.get("setting", "modern clean environment")
        mood = enhanced_context.get("mood", "professional and appealing")
        lifestyle_elements = enhanced_context.get("lifestyle_elements", [])

        if lifestyle_elements:
            elements = ", ".join(lifestyle_elements[:3])  # Limit to first 3 elements
            return f"{setting}, {elements}, {mood}"

        return f"{setting}, {mood}"

    def _get_color_scheme(self, campaign_brief: CampaignBrief) -> str | None:
        """Extract color scheme from campaign brief."""
        brand_meta = campaign_brief.enhanced_context or {}
        brand_colors = brand_meta.get("brand_colors", {})

        if not brand_colors:
            return None

        primary_color = brand_colors.get("primary")
        if primary_color and primary_color.startswith("#"):
            return "vibrant and modern"

        return None

    def _apply_color_rules(
        self,
        base_color_scheme: str | None,
        variant_type: str,
        color_rules: dict[str, str],
        brand_guide: dict[str, Any] | None,
    ) -> str | None:
        """Apply variant-specific color rules."""
        color_rule = color_rules.get(variant_type, "use_primary")

        if color_rule == "use_accent" and brand_guide:
            accent = brand_guide.get("colors", {}).get("accent")
            if accent:
                return f"Accent color {accent} palette with complementary tones"

        return base_color_scheme

    def _lookup_cached_product(self, product_name: str) -> dict[str, Any] | None:
        """Look up cached product entry."""
        return self.cache_manager.lookup_product(product_name)

    def _cache_product_image(
        self, product_name: str, product_slug: str, image: Image.Image
    ) -> None:
        """Cache product image for reuse."""
        # Save product image to cache directory
        cache_path = self.cache_manager.products_dir / f"{product_slug}.png"
        image.save(cache_path, "PNG", optimize=True)

        # Register in cache manager (campaign_id will be tracked)
        campaign_id = getattr(self, '_current_campaign_id', 'unknown')
        self.cache_manager.register_product(
            product_name=product_name,
            file_path=str(cache_path),
            campaign_id=campaign_id,
            tags=[],
            metadata={"cached_at": time.strftime("%Y-%m-%d %H:%M:%S")}
        )

    def _is_cache_hit(self, product_name: str) -> bool:
        """Check if product was loaded from cache."""
        return self._lookup_cached_product(product_name) is not None

    def _has_provided_image(self, product: Any) -> bool:
        """Check if product has a pre-provided image."""
        if isinstance(product, dict):
            return bool(
                product.get("image") or product.get("image_path") or product.get("product_image")
            )
        return False

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

    def _dry_run_preview(
        self, campaign_brief: CampaignBrief, pipeline_state: PipelineState
    ) -> dict[str, Any]:
        """Preview pipeline execution without generation."""
        total_creatives = self._calculate_total_creatives(campaign_brief)

        return {
            "campaign_id": campaign_brief.campaign_id,
            "dry_run": True,
            "total_products": len(campaign_brief.products),
            "total_regions": len(campaign_brief.target_regions),
            "total_creatives_planned": total_creatives,
            "products": [self._extract_product_name(p) for p in campaign_brief.products],
            "regions": campaign_brief.target_regions,
        }
