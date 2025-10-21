#!/usr/bin/env python3
"""
Creative Automation Pipeline - Main CLI Orchestrator

Production-ready POC with 7-component modular architecture for Adobe FDE take-home assignment.

Usage:
    python src/main.py --brief briefs/campaign.json
    python src/main.py --brief briefs/campaign.json --verbose
    python src/main.py --brief briefs/campaign.json --resume
    python src/main.py --brief briefs/campaign.json --dry-run
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import pipeline components
from .background_remover import BackgroundRemover
from .cache_manager import CacheManager
from .compositor import CreativeCompositor
from .enhanced_brief_loader import EnhancedBriefLoader
from .image_generator import ImageGenerator
from .image_processor import ImageProcessor
from .layout_intelligence import LayoutIntelligence
from .output_manager import OutputManager
from .state_tracker import StateTracker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class CreativePipeline:
    """Main pipeline orchestrator"""

    def __init__(self, no_cache: bool = False):
        """
        Initialize pipeline with all components.

        Args:
            no_cache: Disable caching (regenerate everything)
        """
        self.no_cache = no_cache

        # Initialize components
        self.image_generator = ImageGenerator()
        self.background_remover = BackgroundRemover()
        self.compositor = CreativeCompositor()
        self.image_processor = ImageProcessor()
        self.output_manager = OutputManager()
        self.cache_manager = CacheManager()
        self.brief_loader = EnhancedBriefLoader()
        self.layout_intelligence = LayoutIntelligence()

        # Load aspect ratios from external config
        self.aspect_ratios = self._load_aspect_ratios()

        logger.info("🚀 CreativePipeline initialized with 8 components + Layout Intelligence")

    def _load_aspect_ratios(self) -> dict:
        """Load aspect ratios from external config file"""
        aspect_ratios_path = Path("cache/layouts/aspect_ratios.json")

        if aspect_ratios_path.exists():
            with open(aspect_ratios_path) as f:
                config = json.load(f)

            # Convert to the expected format
            aspect_ratios = {}
            for ratio, info in config.get("aspect_ratios", {}).items():
                aspect_ratios[ratio] = tuple(info["dimensions"])

            logger.info(f"✓ Loaded aspect ratios from external config: {len(aspect_ratios)} ratios")
            return aspect_ratios
        else:
            # Fallback to hardcoded ratios
            logger.warning("Aspect ratios file not found, using fallback hardcoded ratios")
            return {
                "1x1": (1080, 1080),
                "9x16": (1080, 1920),
                "16x9": (1920, 1080),
            }

    def process_campaign(
        self, brief_path: str, dry_run: bool = False, resume: bool = False
    ) -> dict:
        """
        Process campaign brief and generate all creatives.

        Args:
            brief_path: Path to campaign brief JSON
            dry_run: Preview without execution
            resume: Resume from saved state

        Returns:
            Dict with processing results
        """
        # Load and enhance brief using CPG schema processing
        brief = self.brief_loader.load_and_enhance_brief(brief_path)

        campaign_id = brief.get("campaign_id", Path(brief_path).stem)
        logger.info(f"\n{'='*60}")
        logger.info(f"CAMPAIGN: {campaign_id}")
        logger.info(f"{'='*60}")

        # Initialize state tracker
        state_tracker = StateTracker(campaign_id)

        if resume and state_tracker.can_resume():
            logger.info("📋 Resuming from saved state...")
            summary = state_tracker.get_summary()
            logger.info(f"   Progress: {summary['progress']} ({summary['progress_percentage']}%)")
            logger.info(f"   Next step: {summary['next_step']}")
        else:
            logger.info("📋 Starting new pipeline execution...")

        if dry_run:
            logger.info("🔍 DRY RUN MODE - Preview only")
            return self._dry_run_preview(brief, state_tracker)

        # Track results
        results = {
            "campaign_id": campaign_id,
            "target_region": brief.get("target_region", "US"),
            "products_processed": [],
            "total_creatives": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "processing_time": 0,
        }

        start_time = time.time()

        # Process each product
        products = brief.get("products", [])
        total_products = len(products)

        for idx, product in enumerate(products, 1):
            product_name = (
                product if isinstance(product, str) else product.get("name", str(product))
            )
            product_slug = self.output_manager._slugify(product_name)

            logger.info(f"\n[{idx}/{total_products}] 🎨 Processing: {product_name}")
            logger.info("-" * 60)

            try:
                # Step 1: Generate/retrieve product asset
                product_image, product_cache_hit = self._get_or_generate_product(
                    product_name, product_slug, state_tracker, brief
                )

                # Step 2: Remove background
                transparent_product, bg_removed_cache_hit, bg_cache_filename = (
                    self._remove_background(product_image, product_slug, state_tracker)
                )

                # Step 3: Generate master composition (1x1 square as base) WITHOUT text
                master_ratio = "1x1"  # Use square as master for optimal transformation
                logger.info(f"   🎨 Generating master composition ({master_ratio})...")

                # Get/generate scene background for master
                scene_bg, scene_cache_hit = self._get_or_generate_scene(
                    brief, master_ratio, state_tracker
                )

                # Composite product + scene for master (NO TEXT YET)
                master_composited = self.compositor.composite(
                    transparent_product,
                    scene_bg,
                    ratio=master_ratio,
                    target_size=self.aspect_ratios[master_ratio],
                )

                campaign_message = brief.get("campaign_message", "Discover Quality")
                logger.info("      ✓ Master composition created (product + background)")

                # Step 4-6: Use Layout Intelligence to transform to all ratios with multiple variants
                for ratio in self.aspect_ratios.keys():
                    logger.info(f"   📐 Intelligent layout adaptation to {ratio}...")

                    # Generate multiple text variants per ratio for A/B testing
                    num_variants = 3  # Generate 3 variants per ratio for proper A/B testing

                    for variant_num in range(1, num_variants + 1):
                        logger.info(f"      🎨 Variant {variant_num}/{num_variants}...")

                        # Always use Layout Intelligence for proper layout positioning
                        # This ensures consistent text-product separation across all ratios
                        final_image = self.layout_intelligence.transform_design_with_assets(
                            transparent_product,  # Pass transparent product
                            scene_bg,  # Pass scene background
                            ratio,
                            campaign_message,
                            product_name,
                            self.aspect_ratios[ratio],
                            variant_id=f"variant_{variant_num}",  # Pass variant ID for different text variations
                        )
                        logger.info("         ✓ Transformed with Layout Intelligence")

                        # Build metadata with cache lineage
                        cache_lineage = self.cache_manager.build_lineage_metadata(
                            {
                                "product": "cached" if product_cache_hit else "generated",
                                "transparent": (
                                    bg_cache_filename if bg_removed_cache_hit else "generated"
                                ),
                                "scene": "cached" if scene_cache_hit else "generated",
                                "layout_transform": "layout_intelligence",
                                "text_variant": f"variant_{variant_num}",
                            }
                        )

                        metadata = {
                            "campaign_id": campaign_id,
                            "product": product_name,
                            "product_slug": product_slug,
                            "ratio": ratio,
                            "variant_id": f"variant_{variant_num}",
                            "campaign_message": campaign_message,
                            "cache_lineage": cache_lineage,
                            "master_ratio": master_ratio,
                            "transformation_method": "layout_intelligence",
                            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }

                        # Extract template and region for regional semantic naming
                        enhanced_context = brief.get("enhanced_context", {})
                        template = enhanced_context.get("layout_style", "hero-product")
                        region = brief.get("target_region", "US")

                        # Save output with regional semantic naming including variant
                        output_path = self.output_manager.save_creative(
                            final_image,
                            product_name,
                            ratio,
                            metadata,
                            template,
                            region,
                            variant_id=f"variant_{variant_num}",
                        )

                        logger.info(f"         ✓ Saved: {Path(output_path).name}")

                        # Update results
                        results["total_creatives"] += 1
                        if ratio == master_ratio and variant_num == 1:
                            # Only count cache hits once for master generation
                            if product_cache_hit:
                                results["cache_hits"] += 1
                            if bg_removed_cache_hit:
                                results["cache_hits"] += 1
                            if scene_cache_hit:
                                results["cache_hits"] += 1

                # Update state
                # Register product in cache registry for cross-campaign reuse
                if bg_cache_filename:
                    product_cache_filename = state_tracker.get_product_state(product_slug).get(
                        "product_cache_filename"
                    )
                    product_category = self.brief_loader._infer_product_category(
                        product_name
                    ).lower()
                    self.cache_manager.register_product(
                        product_name,
                        cache_filename=bg_cache_filename,
                        product_cache_filename=product_cache_filename,
                        campaign_id=campaign_id,
                        tags=[product_category],
                    )

                state_tracker.update_product_state(
                    product_slug,
                    {
                        "product_name": product_name,
                        "processed": True,
                        "ratios_generated": list(self.aspect_ratios.keys()),
                    },
                )

                results["products_processed"].append(product_name)

            except Exception as e:
                logger.error(f"❌ Failed to process {product_name}: {e}")
                state_tracker.log_error(str(e), {"product": product_name})

        # Mark pipeline complete
        state_tracker.mark_step_complete("output_saved")

        # Calculate final metrics
        results["processing_time"] = round(time.time() - start_time, 2)
        results["cache_hit_rate"] = (
            round(
                results["cache_hits"] / (results["cache_hits"] + results["cache_misses"]) * 100,
                1,
            )
            if (results["cache_hits"] + results["cache_misses"]) > 0
            else 0
        )

        # Display summary
        self._display_summary(results)

        return results

    def _get_or_generate_product(
        self, product_name: str, product_slug: str, state_tracker: StateTracker, brief: dict = None
    ) -> tuple:
        """Generate product on white background or retrieve from cache"""
        logger.info("   🖼️  Product asset...")

        if not self.no_cache:
            # First check cache registry from brief loader (cross-campaign cache)
            cache_lookup = brief.get("cache_lookup", {}) if brief else {}
            cache_info = cache_lookup.get("cache_info", {})

            if product_name in cache_info:
                cached_product_info = cache_info[product_name]
                cache_filename = cached_product_info.get("cache_filename")

                if cache_filename:
                    # Handle both semantic and hash-based cache paths
                    if "/" in cache_filename:
                        # Semantic path already includes subfolder: cache/products/subfolder/file.png
                        cache_path = Path("cache/products") / cache_filename
                    else:
                        # Hash-based path: cache/products/product_hash.png
                        cache_path = Path("cache/products") / cache_filename

                    if cache_path.exists():
                        logger.info(
                            f"      ✓ Cache HIT: Using cross-campaign cached product from {cache_path.relative_to('cache/products')}"
                        )
                        from PIL import Image

                        # Load the transparent product from cache and create a white background version
                        cached_transparent = Image.open(cache_path)
                        # Create white background version for this step
                        white_bg = Image.new("RGB", cached_transparent.size, "white")
                        if cached_transparent.mode == "RGBA":
                            white_bg.paste(cached_transparent, mask=cached_transparent.split()[-1])
                        else:
                            white_bg.paste(cached_transparent)

                        # Update state tracker with cross-campaign cached info
                        state_tracker.update_product_state(
                            product_slug,
                            {
                                "product_generated": True,
                                "cache_filename": str(cache_path.relative_to("cache/products")),
                                "cross_campaign_cache": True,
                            },
                        )

                        return white_bg, True

            # Fall back to checking current campaign state
            product_state = state_tracker.get_product_state(product_slug)
            if product_state and product_state.get("product_generated"):
                # Try to load from background remover cache since that's where processed products are stored
                cache_filename = product_state.get("cache_filename")
                if cache_filename:
                    cache_path = Path("cache/products") / cache_filename
                    if cache_path.exists():
                        logger.info(
                            f"      ✓ Cache HIT: Using existing product asset from {cache_filename}"
                        )
                        from PIL import Image

                        # Load the transparent product from cache and create a white background version
                        cached_transparent = Image.open(cache_path)
                        # Create white background version for this step
                        white_bg = Image.new("RGB", cached_transparent.size, "white")
                        if cached_transparent.mode == "RGBA":
                            white_bg.paste(cached_transparent, mask=cached_transparent.split()[-1])
                        else:
                            white_bg.paste(cached_transparent)
                        return white_bg, True

        # Generate product with enhanced context if available
        enhanced_context = brief.get("enhanced_context", {}) if brief else {}
        brand_colors = enhanced_context.get("brand_colors", [])
        brand_tone = enhanced_context.get("brand_tone", "confident")

        logger.info("      🔄 Generating with DALL-E 3...")
        if enhanced_context:
            logger.info(f"         Using enhanced context: {brand_tone} tone")

        product_image = self.image_generator.generate_product_on_white(product_name)

        state_tracker.update_product_state(product_slug, {"product_generated": True})
        return product_image, False

    def _remove_background(
        self, product_image, product_slug: str, state_tracker: StateTracker
    ) -> tuple:
        """Remove background with caching"""
        logger.info("   ✂️  Background removal...")

        if not self.no_cache:
            # Check state tracker for existing background-removed product
            product_state = state_tracker.get_product_state(product_slug)
            if product_state and product_state.get("background_removed"):
                cache_filename = product_state.get("cache_filename")
                if cache_filename:
                    # Handle both semantic and hash-based cache paths
                    if "/" in cache_filename:
                        cache_path = Path("cache/products") / cache_filename
                    else:
                        cache_path = Path("cache/products") / cache_filename

                    if cache_path.exists():
                        cache_source = (
                            "cross-campaign"
                            if product_state.get("cross_campaign_cache")
                            else "current campaign"
                        )
                        logger.info(
                            f"      ✓ Cache HIT: Using existing background-removed product from {cache_filename} ({cache_source})"
                        )
                        from PIL import Image

                        cached_transparent = Image.open(cache_path)
                        return cached_transparent, True, cache_filename
            elif product_state and product_state.get("cross_campaign_cache"):
                # Product was loaded from cross-campaign cache, which is already background-removed
                cache_filename = product_state.get("cache_filename")
                if cache_filename:
                    # Handle both semantic and hash-based cache paths
                    if "/" in cache_filename:
                        cache_path = Path("cache/products") / cache_filename
                    else:
                        cache_path = Path("cache/products") / cache_filename

                    if cache_path.exists():
                        logger.info(
                            f"      ✓ Cache HIT: Cross-campaign product already background-removed: {cache_filename}"
                        )
                        from PIL import Image

                        cached_transparent = Image.open(cache_path)
                        # Mark as background removed in state
                        state_tracker.update_product_state(
                            product_slug, {"background_removed": True}
                        )
                        return cached_transparent, True, cache_filename

        # Generate new background removal using semantic naming (no _transparent suffix)
        semantic_filename = f"{product_slug}.png"

        transparent_product, was_cached, proc_time, cache_filename = (
            self.background_remover.remove_background(
                product_image,
                product_slug,
                force=self.no_cache,
                semantic_filename=semantic_filename,
            )
        )

        if was_cached:
            logger.info(f"      ✓ Cache HIT: {cache_filename}")
        else:
            logger.info(f"      ✓ Processed in {proc_time:.1f}s")

        state_tracker.update_product_state(
            product_slug, {"background_removed": True, "cache_filename": cache_filename}
        )

        return transparent_product, was_cached, cache_filename

    def _get_or_generate_scene(self, brief: dict, ratio: str, state_tracker: StateTracker) -> tuple:
        """Generate contextual background or retrieve from cache"""
        region = brief.get("target_region", "US")
        enhanced_context = brief.get("enhanced_context", {})
        products = brief.get("products", [])

        logger.info(f"      🎨 Contextual background ({region})...")

        # Use CPG context if available
        if enhanced_context:
            setting = enhanced_context.get("setting", "Modern setting")
            aesthetic = enhanced_context.get(
                "aesthetic", "Contextual background for product showcase"
            )
            logger.info(f"         Context: {setting}")
            logger.info(f"         Aesthetic: {aesthetic}")

        # Determine product category for contextual background
        if products:
            primary_product = (
                products[0]
                if isinstance(products[0], str)
                else products[0].get("name", str(products[0]))
            )
            product_category = self.brief_loader._infer_product_category(primary_product)

            logger.info(f"         Product Category: {product_category}")

            # Generate contextual background based on product category
            try:
                scene_bg = self.image_generator.generate_contextual_background(
                    product_category=product_category,
                    product_name=primary_product,
                    region=region,
                    size="1024x1024",
                )
                return scene_bg, False
            except Exception as e:
                logger.warning(
                    f"Contextual background generation failed: {e}, falling back to solid color"
                )
                # Fallback to solid color
                brand_colors = ["#2E8B57", "#FFFFFF", "#FFD700"]  # Sea green, white, gold
                primary_color = brand_colors[0]
                scene_bg = self.image_generator.generate_solid_color_background(
                    primary_color, "1024x1024"
                )
                return scene_bg, False
        else:
            # No products specified, use solid color fallback
            brand_colors = ["#2E8B57", "#FFFFFF", "#FFD700"]
            primary_color = brand_colors[0]
            scene_bg = self.image_generator.generate_solid_color_background(
                primary_color, "1024x1024"
            )
            return scene_bg, False

    def _dry_run_preview(self, brief: dict, state_tracker: StateTracker) -> dict:
        """Preview pipeline execution without actually running"""
        products = brief.get("products", [])
        campaign_message = brief.get("campaign_message", "")

        print("\n📋 DRY RUN PREVIEW")
        print("=" * 60)
        print(f"Campaign ID: {brief.get('campaign_id', 'N/A')}")
        print(f"Target Region: {brief.get('target_region', 'N/A')}")
        print(f"Target Audience: {brief.get('target_audience', 'N/A')}")
        print(f"Campaign Message: {campaign_message}")
        print(f"\nProducts ({len(products)}):")
        for idx, product in enumerate(products, 1):
            product_name = (
                product if isinstance(product, str) else product.get("name", str(product))
            )
            print(f"  {idx}. {product_name}")

        print(f"\nAspect Ratios: {', '.join(self.aspect_ratios.keys())}")
        print(f"\nTotal Creatives: {len(products) * len(self.aspect_ratios)} variants")

        print("\n📊 Pipeline Steps:")
        print("  1. Generate product on white background (DALL-E 3)")
        print("  2. Remove background (rembg AI)")
        print("  3. Generate master design (1x1 square)")
        print("  4. Use Layout Intelligence for adaptive layout transformations")
        print("  5. Transform to all aspect ratios (9x16, 16x9)")
        print("  6. Save with semantic naming + metadata")

        return {"dry_run": True, "products": len(products)}

    def _display_summary(self, results: dict):
        """Display final processing summary"""
        print("\n" + "=" * 60)
        print("✅ PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Campaign ID: {results['campaign_id']}")
        print(f"Products Processed: {len(results['products_processed'])}")
        print(f"Total Creatives: {results['total_creatives']}")
        print(f"Processing Time: {results['processing_time']}s")
        print(f"Cache Hit Rate: {results.get('cache_hit_rate', 0)}%")

        print("\n📁 Regional Semantic Output Structure:")
        for product in results["products_processed"]:
            product_slug = self.output_manager._slugify(product)
            print(f"  output/{product_slug}/")
            print("    hero-product/")
            print(f"      {results.get('target_region', 'us').lower()}/")
            for ratio in self.aspect_ratios.keys():
                template_slug = "hero-product"
                region_slug = results.get("target_region", "US").lower()
                print(
                    f"        {ratio}/ → {product_slug}_{template_slug}_{region_slug}_{ratio}_creative.jpg"
                )


# ============================================================================
# CLI ENTRY POINT
# ============================================================================


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Creative Automation Pipeline - Adobe FDE POC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python src/main.py --brief briefs/campaign_001.json

  # Verbose logging
  python src/main.py --brief briefs/campaign_001.json --verbose

  # Dry run (preview)
  python src/main.py --brief briefs/campaign_001.json --dry-run

  # Resume after error
  python src/main.py --brief briefs/campaign_001.json --resume

  # Clear cache and regenerate
  python src/main.py --brief briefs/campaign_001.json --no-cache --clean
        """,
    )

    parser.add_argument("--brief", "-b", required=True, help="Path to campaign brief JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--dry-run", action="store_true", help="Preview without execution")
    parser.add_argument("--resume", action="store_true", help="Resume from saved state")
    parser.add_argument("--clean", action="store_true", help="Clear cache before running")
    parser.add_argument("--no-cache", action="store_true", help="Skip cache, regenerate everything")
    parser.add_argument("--report", action="store_true", help="Generate cost/performance report")

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate brief file exists
    if not Path(args.brief).exists():
        logger.error(f"❌ Brief file not found: {args.brief}")
        sys.exit(1)

    try:
        # Clean cache if requested
        if args.clean:
            logger.info("🧹 Clearing cache...")
            cache_mgr = CacheManager()
            cleared = cache_mgr.clear_cache()
            logger.info(f"   Cleared {cleared} cache entries")

            bg_remover = BackgroundRemover()
            cleared_bg = bg_remover.clear_cache()
            logger.info(f"   Cleared {cleared_bg} background removal cache entries")

        # Initialize and run pipeline
        pipeline = CreativePipeline(no_cache=args.no_cache)
        results = pipeline.process_campaign(args.brief, dry_run=args.dry_run, resume=args.resume)

        # Generate report if requested
        if args.report and not args.dry_run:
            logger.info("\n📊 Generating performance report...")
            # Report generation implementation
            print("\nPerformance Report:")
            print(f"  Total Creatives: {results['total_creatives']}")
            print(f"  Processing Time: {results['processing_time']}s")
            print(
                f"  Time per Creative: {results['processing_time'] / results['total_creatives']:.1f}s"
            )
            print(f"  Cache Hit Rate: {results.get('cache_hit_rate', 0)}%")

        sys.exit(0)

    except KeyboardInterrupt:
        logger.info("\n⚠️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Pipeline failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
