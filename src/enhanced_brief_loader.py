"""
Enhanced Brief Loader - CPG Schema Processing

Transforms CPG schema briefs into format compatible with existing pipeline
while supporting both old simple format and new sophisticated schema.
Includes automatic product cache lookup for cross-campaign reuse.
"""

import json
import logging
from pathlib import Path
from typing import Any

# Support both relative imports (when run as module) and direct imports (when run in tests)
try:
    from cache_manager import CacheManager  # Direct import for tests
except ImportError:
    from .cache_manager import CacheManager  # Relative import for module execution

logger = logging.getLogger(__name__)


class EnhancedBriefLoader:
    """
    Brief loader that handles both simple and CPG schema formats.

    Transforms sophisticated CPG schema into pipeline-compatible format
    while preserving all enhanced metadata for context-rich generation.
    """

    def __init__(self, cache_manager=None, cache_dir=None):
        self.product_contexts = self._load_product_contexts()
        self.regional_aesthetics = self._load_regional_aesthetics()

        if cache_manager is not None:
            self.cache_manager = cache_manager
        elif cache_dir is not None:
            self.cache_manager = CacheManager(cache_dir=cache_dir)
        else:
            self.cache_manager = CacheManager()

        self.brand_guidelines = self._load_brand_guidelines_index()

    def load_brief(self, brief_path: str) -> dict[str, Any]:
        """Load brief - interface method that delegates to enhanced version."""
        return self.load_and_enhance_brief(brief_path)

    def validate_brief(self, brief: dict[str, Any]) -> bool:
        """Validate brief structure and content."""
        # Basic validation - check for required fields
        required_fields = ["products", "campaign_id"]
        return all(field in brief for field in required_fields)

    def load_and_enhance_brief(self, brief_path: str) -> dict[str, Any]:
        """
        Load brief file and enhance with CPG schema processing.

        Args:
            brief_path: Path to brief JSON file

        Returns:
            Enhanced brief compatible with pipeline + CPG metadata
        """
        with open(brief_path) as f:
            raw_brief = json.load(f)

        # Add brief path for campaign ID extraction
        raw_brief["_brief_path"] = brief_path

        # Detect format type
        if self._is_cpg_schema(raw_brief):
            logger.info("📋 Detected CPG schema format - transforming...")
            return self._transform_cpg_to_pipeline(raw_brief)
        elif self._is_simple_format(raw_brief):
            logger.info("📋 Detected simple format - enhancing with CPG processing...")
            return self._enhance_simple_brief(raw_brief)
        else:
            logger.warning("📋 Unknown brief format - attempting basic processing...")
            return self._handle_unknown_format(raw_brief)

    def _is_cpg_schema(self, brief: dict) -> bool:
        """Check if brief uses CPG schema format"""
        required_keys = ["brand_meta", "campaign_meta", "visual_concept", "text_elements"]
        return all(key in brief for key in required_keys)

    def _is_simple_format(self, brief: dict) -> bool:
        """Check if brief uses simple format"""
        return "products" in brief and isinstance(brief["products"], list)

    def _transform_cpg_to_pipeline(self, cpg_brief: dict) -> dict[str, Any]:
        """Transform CPG schema brief to pipeline-compatible format with enhanced features"""

        # Extract core information
        brand_meta = cpg_brief.get("brand_meta", {})
        campaign_meta = cpg_brief.get("campaign_meta", {})
        regional_context = cpg_brief.get("regional_context", {})
        visual_concept = cpg_brief.get("visual_concept", {})
        text_elements = cpg_brief.get("text_elements", {})
        context_mapping = cpg_brief.get("context_mapping", {})

        # Enhanced features
        creative_specifications = cpg_brief.get("creative_specifications", {})
        performance_tracking = cpg_brief.get("performance_tracking", {})

        # Load brand guidelines if specified
        brand_guidelines = None
        brand_guidelines_id = brand_meta.get("brand_guidelines_id")
        if brand_guidelines_id:
            brand_guidelines = self._load_brand_guidelines(brand_guidelines_id)

        # Create product list (pipeline expects this)
        # Handle both simple and enhanced product formats
        if "products" in cpg_brief and isinstance(cpg_brief["products"], list):
            # Check if products are objects (enhanced format) or strings (simple format)
            if cpg_brief["products"] and isinstance(cpg_brief["products"][0], dict):
                # Enhanced format with product objects
                products = [product["name"] for product in cpg_brief["products"]]
                product_details = {product["name"]: product for product in cpg_brief["products"]}
            else:
                # Simple format with product names
                products = cpg_brief["products"]
                product_details = {}
            logger.info(f"✓ Using explicit products array: {len(products)} products")
        else:
            # Fallback to brand_meta for single product
            product_name = f"{brand_meta.get('brand_name', 'Brand')} {brand_meta.get('product_name', 'Product')}"
            products = [product_name]
            product_details = {}
            logger.info(f"✓ Generated product from brand_meta: {product_name}")

        # Transform to pipeline format
        enhanced_brief = {
            # Pipeline-compatible fields
            "products": products,
            "target_region": regional_context.get("region_code", "US"),
            "campaign_message": text_elements.get("headline_text", "Quality Product"),
            "target_audience": campaign_meta.get("objective", "General audience"),
            "campaign_id": campaign_meta.get("campaign_name", "cpg_campaign")
            .lower()
            .replace(" ", "_"),
            # Enhanced CPG metadata
            "cpg_schema": {
                "brand_meta": brand_meta,
                "campaign_meta": campaign_meta,
                "regional_context": regional_context,
                "visual_concept": visual_concept,
                "text_elements": text_elements,
                "context_mapping": context_mapping,
                "creative_specifications": creative_specifications,
                "performance_tracking": performance_tracking,
            },
            # Context-rich generation data with enhanced features
            "enhanced_context": {
                "scene_description": context_mapping.get("scene", "Modern setting"),
                "product_placement": context_mapping.get("placement", "Naturally positioned"),
                "placement_rules": context_mapping.get(
                    "placement_rules", "Product positioned naturally"
                ),
                "regional_aesthetic": context_mapping.get("regional_aesthetic", "Clean and modern"),
                "visual_prompt_template": visual_concept.get("visual_prompt_template", ""),
                "layout_style": visual_concept.get("layout_style", "hero_product"),
                "brand_tone": brand_meta.get("brand_tone", "confident"),
                "brand_colors": brand_meta.get("brand_colors", ["#000000", "#FFFFFF"]),
                # Enhanced features
                "background_style": visual_concept.get("background_style", "contextual"),
                "background_options": visual_concept.get("background_options", {}),
                "text_style": text_elements.get("text_style", {}),
                "composition_rules": visual_concept.get("composition_rules", {}),
                "creative_specs": creative_specifications,
                "product_details": product_details,
                "brand_guidelines": brand_guidelines,
                "generated_from": "enhanced_cpg_schema",
            },
        }

        logger.info(f"✓ Transformed CPG schema for: {', '.join(products)}")
        logger.info(f"   Region: {enhanced_brief['target_region']}")
        logger.info(f"   Message: {enhanced_brief['campaign_message']}")
        logger.info(f"   Context: {context_mapping.get('scene', 'N/A')}")

        return enhanced_brief

    def _enhance_simple_brief(self, simple_brief: dict) -> dict[str, Any]:
        """Enhance simple brief with CPG-style processing and cache lookup"""

        products = simple_brief.get("products", [])
        region = simple_brief.get("target_region", "US")
        simple_brief.get("campaign_message", "Quality Product")
        campaign_id = simple_brief.get(
            "campaign_id", Path(simple_brief.get("_brief_path", "unknown")).stem
        )

        enhanced_brief = simple_brief.copy()

        # Process products with automatic cache lookup
        cache_results = self._process_products_with_cache_lookup(products, campaign_id)

        # Add enhanced context for each product
        enhanced_contexts = []
        for product in products:
            # Handle both string and dict products
            product_name = (
                product if isinstance(product, str) else product.get("name", str(product))
            )
            product_category = self._infer_product_category(product_name)
            context = self._generate_product_context(product_category, region)
            enhanced_contexts.append(context)

        enhanced_brief["enhanced_context"] = {
            "product_contexts": enhanced_contexts,
            "regional_aesthetic": self._get_regional_aesthetic(region),
            "generated_from": "simple_brief_enhancement",
        }

        # Add cache information
        enhanced_brief["cache_lookup"] = cache_results

        logger.info(f"✓ Enhanced simple brief with {len(products)} products")
        logger.info(
            f"   Cache hit rate: {cache_results['cache_hit_rate']:.1f}% ({len(cache_results['cached_products'])}/{len(products)})"
        )

        return enhanced_brief

    def _handle_unknown_format(self, brief: dict) -> dict[str, Any]:
        """Handle unknown brief formats with basic fallbacks"""

        # Try to extract any recognizable fields
        products = brief.get("products", brief.get("product", ["Unknown Product"]))
        if isinstance(products, str):
            products = [products]

        enhanced_brief = {
            "products": products,
            "target_region": brief.get("target_region", brief.get("region", "US")),
            "campaign_message": brief.get(
                "campaign_message", brief.get("message", "Quality Product")
            ),
            "campaign_id": brief.get("campaign_id", "unknown_campaign"),
            "enhanced_context": {"generated_from": "unknown_format_fallback"},
        }

        logger.warning("⚠️ Used fallback processing for unknown format")
        return enhanced_brief

    def _process_products_with_cache_lookup(
        self, products: list[str], campaign_id: str = None
    ) -> dict[str, Any]:
        """
        Process product list with automatic cache lookup.

        Args:
            products: List of product names
            campaign_id: Current campaign ID for tracking

        Returns:
            Dict with categorized products: cached and new
        """
        cached_products = []
        new_products = []
        cache_info = {}

        logger.info(f"🔍 Checking cache for {len(products)} products...")

        for product in products:
            # Handle both string and dict products
            product_name = (
                product if isinstance(product, str) else product.get("name", str(product))
            )

            # Look up product in cache registry
            cached_product = self.cache_manager.lookup_product(product_name)

            if cached_product:
                # Generate slug for logging (since we simplified cache structure)
                product_slug = product_name.lower().replace(" ", "-").replace("&", "-").strip("-")
                logger.info(f"   ✓ Cache HIT: {product_name} -> {product_slug}")
                cached_products.append(product)
                cache_info[product_name] = cached_product

                # Update campaign usage tracking
                if campaign_id:
                    self.cache_manager.register_product(
                        product_name,
                        cached_product.get("file_path"),
                        cached_product.get("product_cache_filename"),
                        campaign_id,
                    )
            else:
                # Check if product has asset path in brief (support multiple field names)
                logger.debug(f"   DEBUG: product type: {type(product)}, content: {product}")
                if isinstance(product, dict):
                    # Support multiple field names for maximum compatibility
                    asset_path = (
                        product.get("image")
                        or product.get("image_path")
                        or product.get("asset_path")
                        or product.get("product_image")
                        or product.get("asset_url")
                    )

                    if asset_path:
                        logger.info(
                            f"   📁 Registering asset from brief: {product_name} -> {asset_path}"
                        )

                        # Register the asset in cache
                        self.cache_manager.register_product(
                            product_name=product_name,
                            file_path=asset_path,
                            campaign_id=campaign_id,
                        )
                        # Treat as cached since we now have it registered
                        cached_products.append(product)
                        cache_info[product_name] = {
                            "cache_filename": asset_path,
                            "product_cache_filename": asset_path,
                        }
                else:
                    logger.info(f"   ✗ Cache MISS: {product_name} (will generate)")
                    new_products.append(product)

        return {
            "products": products,  # Keep original product list for pipeline
            "cached_products": cached_products,
            "new_products": new_products,
            "cache_info": cache_info,
            "cache_hit_rate": len(cached_products) / len(products) * 100 if products else 0,
        }

    def _infer_product_category(self, product_name: str) -> str:
        """Infer product category from name for context mapping with specific-first logic"""
        product_lower = product_name.lower()

        # Check most specific keywords first to avoid misclassification
        if any(word in product_lower for word in ["dish soap", "dish detergent", "dishwashing"]):
            return "Dish Soap"
        elif any(
            word in product_lower
            for word in ["laundry detergent", "fabric softener", "laundry soap"]
        ):
            return "Laundry Detergent"
        elif "dish" in product_lower and any(
            word in product_lower for word in ["soap", "liquid", "cleaner"]
        ):
            return "Dish Soap"
        elif (
            any(word in product_lower for word in ["detergent", "laundry"])
            and "dish" not in product_lower
        ):
            return "Laundry Detergent"
        elif any(word in product_lower for word in ["shampoo", "conditioner", "hair"]):
            return "Hair Care"
        elif any(word in product_lower for word in ["toothpaste", "dental", "oral"]):
            return "Oral Care"
        elif any(word in product_lower for word in ["soap"]) and "dish" not in product_lower:
            return "Personal Care"
        elif (
            any(word in product_lower for word in ["wash", "clean"]) and "dish" not in product_lower
        ):
            return "General CPG"
        else:
            return "General CPG"

    def _generate_product_context(self, category: str, region: str) -> dict[str, str]:
        """Generate context mapping for product category and region"""

        base_context = self.product_contexts.get(
            category,
            {
                "scene": "Modern home setting",
                "placement": "Product naturally positioned",
                "props": "Clean, organized environment",
                "lighting": "Natural lighting",
                "context": "Realistic usage scenario",
            },
        )

        regional_aesthetic = self._get_regional_aesthetic(region)

        return {
            **base_context,
            "placement_rules": "Product positioned naturally in usage context, NOT floating",
            "regional_aesthetic": regional_aesthetic,
        }

    def _get_regional_aesthetic(self, region: str) -> str:
        """Get regional aesthetic description"""
        return self.regional_aesthetics.get(
            region, {"description": "Clean modern aesthetic with natural lighting"}
        )["description"]

    def _load_brand_guidelines_index(self) -> dict[str, Any]:
        """Load brand guidelines index for quick lookup"""
        try:
            index_path = Path("../cache/brand_guidelines/index.json")
            if index_path.exists():
                with open(index_path) as f:
                    return json.load(f)
            else:
                logger.debug("Brand guidelines index not found, using empty index")
                return {"registered_brands": {}}
        except Exception as e:
            logger.error(f"Failed to load brand guidelines index: {e}")
            return {"registered_brands": {}}

    def _load_brand_guidelines(self, brand_guidelines_id: str) -> dict[str, Any] | None:
        """Load specific brand guidelines by ID"""
        try:
            # Check if brand is registered
            if brand_guidelines_id not in self.brand_guidelines.get("registered_brands", {}):
                logger.warning(f"Brand guidelines ID '{brand_guidelines_id}' not found in index")
                return None

            brand_info = self.brand_guidelines["registered_brands"][brand_guidelines_id]
            guidelines_path = Path(brand_info["guidelines_file"])

            if guidelines_path.exists():
                with open(guidelines_path) as f:
                    guidelines = json.load(f)
                logger.info(f"✓ Loaded brand guidelines for {brand_guidelines_id}")
                return guidelines
            else:
                logger.error(f"Brand guidelines file not found: {guidelines_path}")
                return None

        except Exception as e:
            logger.error(f"Failed to load brand guidelines for {brand_guidelines_id}: {e}")
            return None

    def _load_product_contexts(self) -> dict[str, dict[str, str]]:
        """Load product context mappings"""
        return {
            "Laundry Detergent": {
                "scene": "Modern laundry room with front-load washing machine",
                "placement": "Detergent bottle on counter next to folded towels",
                "props": "Basket of clean white clothes, fabric softener nearby",
                "lighting": "Bright natural light from window",
                "context": "Mid-laundry process, realistic home setting",
            },
            "Dish Soap": {
                "scene": "Contemporary kitchen with farmhouse sink",
                "placement": "Soap bottle beside clean dishes on drying rack",
                "props": "Sponge, clean plates and glasses, dish towel",
                "lighting": "Warm under-cabinet lighting",
                "context": "Post-dinner cleanup, lived-in kitchen",
            },
            "Hair Care": {
                "scene": "Modern bathroom with natural lighting",
                "placement": "Product on bathroom counter near mirror",
                "props": "Towels, natural bathroom accessories",
                "lighting": "Soft natural light from window",
                "context": "Morning routine, clean bathroom setting",
            },
            "Oral Care": {
                "scene": "Clean bathroom vanity area",
                "placement": "Product beside sink with other oral care items",
                "props": "Toothbrush, clean countertop, mirror",
                "lighting": "Bright vanity lighting",
                "context": "Daily oral care routine",
            },
        }

    def _load_regional_aesthetics(self) -> dict[str, dict[str, str]]:
        """Load regional aesthetic mappings"""
        return {
            "LATAM": {
                "description": "Warm vibrant colors, natural sunlight, tropical plants, family-oriented spaces",
                "colors": "oranges, yellows, bright whites",
                "lighting": "golden hour warmth, natural sunlight",
                "mood": "energetic, communal, family-oriented",
            },
            "APAC": {
                "description": "Clean whites, soft pastels, natural wood tones, organized spaces, quality appliances",
                "colors": "clean whites, soft pastels, natural wood",
                "lighting": "soft diffused light, minimal shadows",
                "mood": "calm, sophisticated, quality-focused",
            },
            "EMEA": {
                "description": "Sophisticated greys, deep blues, premium whites, contemporary design, architectural lighting",
                "colors": "sophisticated greys, deep blues, premium whites",
                "lighting": "contemporary LED lighting, architectural",
                "mood": "elegant, premium, contemporary",
            },
            "US": {
                "description": "Clean modern aesthetic with natural lighting and contemporary design",
                "colors": "neutral palette with accent colors",
                "lighting": "natural and contemporary lighting",
                "mood": "confident, modern, accessible",
            },
        }
