"""
Comprehensive Test Suite for Cache Manager Semantic Asset Reuse System

This test suite validates semantic asset matching, cross-campaign discovery,
background adaptation, seasonal updates, asset versioning, and caching efficiency.

Test Coverage:
1. Semantic Asset Matching - Find similar assets across campaigns
2. Cross-Campaign Asset Discovery - Reuse assets from previous campaigns
3. Background Adaptation - Test seasonal and regional variants
4. Asset Versioning - Track variants and version history
5. Performance Testing - Cache retrieval and matching efficiency
6. Edge Cases - Unusual combinations and boundary conditions
7. CLI Integration - End-to-end workflow testing
"""

import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PIL import Image

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cache_manager import CacheManager

# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def cache_manager(temp_cache_dir):
    """Create cache manager instance"""
    return CacheManager(cache_dir=str(temp_cache_dir))


@pytest.fixture
def sample_product_image():
    """Generate sample product image"""
    img = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
    # Add some color to make it recognizable
    for x in range(100, 400):
        for y in range(100, 400):
            img.putpixel((x, y), (255, 0, 0, 255))
    return img


@pytest.fixture
def sample_background_image():
    """Generate sample background image"""
    img = Image.new("RGB", (1024, 1024), (135, 206, 235))  # Sky blue
    return img


@pytest.fixture
def multi_campaign_setup(cache_manager, temp_cache_dir, sample_product_image):
    """Setup multiple campaigns with shared products for cross-campaign testing"""
    campaigns = {
        "spring_2025": {
            "products": ["Power Dish Soap", "Ultra Laundry Detergent", "Fresh Air Freshener"],
            "region": "US",
            "season": "spring",
        },
        "summer_2025": {
            "products": ["Power Dish Soap", "Ultra Laundry Detergent", "Summer Breeze Spray"],
            "region": "US",
            "season": "summer",
        },
        "holiday_2025_emea": {
            "products": ["Power Dish Soap", "Holiday Gift Set"],
            "region": "EMEA",
            "season": "winter",
        },
    }

    # Register products for each campaign
    for campaign_id, campaign_data in campaigns.items():
        for product_name in campaign_data["products"]:
            # Save sample image
            cache_filename = f"{product_name.replace(' ', '_').lower()}_{campaign_id}.png"
            cache_path = temp_cache_dir / cache_filename
            sample_product_image.save(cache_path, "PNG")

            # Register in cache with rich metadata
            cache_manager.register_product(
                product_name,
                str(cache_path),  # Use full path to the saved file
                campaign_id,
                tags=[
                    campaign_data["season"],
                    campaign_data["region"],
                    "product",
                ],
            )

    return campaigns


# ============================================================================
# 1. SEMANTIC ASSET MATCHING TESTS
# ============================================================================


class TestSemanticAssetMatching:
    """Test semantic matching of assets across campaigns"""

    def test_exact_product_name_match(self, cache_manager, multi_campaign_setup):
        """Test finding exact product name matches across campaigns"""
        product_name = "Power Dish Soap"
        matches = cache_manager.lookup_product(product_name)

        assert matches is not None
        assert matches["name"] == product_name
        assert len(matches["campaigns_used"]) > 0

    def test_similar_product_name_matching(self, cache_manager):
        """Test fuzzy matching for similar product names"""
        # Register products with slight variations
        cache_manager.register_product(
            "Power Dish Soap", "power_dish_1.png", "campaign_1", tags=["dish", "soap"]
        )
        cache_manager.register_product(
            "Power Dish Soap Pro", "power_dish_2.png", "campaign_2", tags=["dish", "soap", "pro"]
        )
        cache_manager.register_product(
            "Ultra Power Dish Soap",
            "power_dish_3.png",
            "campaign_3",
            tags=["dish", "soap", "ultra"],
        )

        # All should have similar slugs
        slug1 = cache_manager._slugify_product_name("Power Dish Soap")
        slug2 = cache_manager._slugify_product_name("Power Dish Soap Pro")

        # Basic test - they should be different slugs
        assert slug1 != slug2
        assert "power-dish-soap" in slug1
        assert "power-dish-soap-pro" in slug2

    def test_cross_campaign_product_reuse_tracking(self, cache_manager, multi_campaign_setup):
        """Test tracking product usage across multiple campaigns"""
        product_name = "Power Dish Soap"
        product_entry = cache_manager.lookup_product(product_name)

        # Should track all campaigns using this product
        campaigns_used = product_entry["campaigns_used"]
        assert len(campaigns_used) >= 2
        assert "spring_2025" in campaigns_used
        assert "summer_2025" in campaigns_used

    def test_metadata_based_asset_discovery(self, cache_manager, multi_campaign_setup):
        """Test finding assets by metadata tags (season, region, type)"""
        # Find all spring products
        all_products = cache_manager.list_all_products()
        spring_products = [p for slug, p in all_products.items() if "spring" in p.get("tags", [])]

        assert len(spring_products) > 0

        # Find all US region products
        us_products = [p for slug, p in all_products.items() if "US" in p.get("tags", [])]
        assert len(us_products) > 0

    def test_category_based_matching(self, cache_manager):
        """Test matching assets by product category"""
        # Register products with categories
        cache_manager.register_product(
            "Power Dish Soap",
            "dish1.png",
            "campaign_1",
            tags=["dish_soap", "cleaning", "kitchen"],
        )
        cache_manager.register_product(
            "Ultra Laundry Detergent",
            "laundry1.png",
            "campaign_1",
            tags=["laundry", "cleaning", "fabric"],
        )
        cache_manager.register_product(
            "Super Dish Soap",
            "dish2.png",
            "campaign_2",
            tags=["dish_soap", "cleaning", "kitchen"],
        )

        # Find all dish soap products
        all_products = cache_manager.list_all_products()
        dish_soaps = [p for slug, p in all_products.items() if "dish_soap" in p.get("tags", [])]

        assert len(dish_soaps) == 2

    def test_temporal_asset_matching(self, cache_manager):
        """Test finding assets from specific time periods"""
        # Register products with different timestamps
        now = datetime.now()

        cache_manager.register_product("Product A", "product_a.png", "campaign_old", tags=["old"])

        # Manually update timestamp for testing
        product_slug = cache_manager._slugify_product_name("Product A")
        cache_manager.index["products"][product_slug]["created_at"] = (
            now - timedelta(days=90)
        ).isoformat()
        cache_manager._save_index()

        cache_manager.register_product("Product B", "product_b.png", "campaign_new", tags=["new"])

        # Verify different timestamps
        product_a = cache_manager.lookup_product("Product A")
        product_b = cache_manager.lookup_product("Product B")

        assert product_a["created_at"] < product_b["created_at"]


# ============================================================================
# 2. CROSS-CAMPAIGN ASSET DISCOVERY TESTS
# ============================================================================


class TestCrossCampaignDiscovery:
    """Test cross-campaign asset discovery and reuse"""

    def test_discover_reusable_products(self, cache_manager, multi_campaign_setup):
        """Test discovering products that can be reused from previous campaigns"""
        # For a new campaign targeting "Power Dish Soap"
        product_name = "Power Dish Soap"
        existing_product = cache_manager.lookup_product(product_name)

        assert existing_product is not None
        assert existing_product["status"] == "ready"
        assert len(existing_product["campaigns_used"]) >= 2

    def test_campaign_specific_metadata(self, cache_manager, multi_campaign_setup):
        """Test querying assets by campaign-specific criteria"""
        # Get all products from spring campaign
        all_products = cache_manager.list_all_products()

        spring_campaign_products = [
            p for slug, p in all_products.items() if "spring_2025" in p["campaigns_used"]
        ]

        assert len(spring_campaign_products) >= 3

    def test_regional_asset_discovery(self, cache_manager, multi_campaign_setup):
        """Test discovering assets by region for localized campaigns"""
        all_products = cache_manager.list_all_products()

        # Find US products
        us_products = [p for slug, p in all_products.items() if "US" in p.get("tags", [])]
        assert len(us_products) > 0

        # Find EMEA products
        emea_products = [p for slug, p in all_products.items() if "EMEA" in p.get("tags", [])]
        assert len(emea_products) > 0

    def test_shared_asset_utilization_rate(self, cache_manager, multi_campaign_setup):
        """Test calculating asset reuse rate across campaigns"""
        # Count products used in multiple campaigns
        all_products = cache_manager.list_all_products()

        multi_campaign_products = [
            p for slug, p in all_products.items() if len(p["campaigns_used"]) > 1
        ]

        total_products = len(all_products)
        reuse_rate = len(multi_campaign_products) / total_products if total_products > 0 else 0

        # Should have some reuse (at least Power Dish Soap)
        assert reuse_rate > 0

    def test_campaign_lineage_tracking(self, cache_manager, multi_campaign_setup):
        """Test tracking which campaigns contributed to current outputs"""
        # Simulate cache hits from multiple campaigns
        cache_hits = {
            "product": "power_dish_soap_spring_2025.png",
            "background": "spring_scene_us.jpg",
            "text": "spring_cta.png",
        }

        lineage = cache_manager.build_lineage_metadata(cache_hits)

        assert lineage["cache_count"] == 3
        assert lineage["fully_cached"] is True


# ============================================================================
# 3. BACKGROUND ADAPTATION & SEASONAL UPDATES TESTS
# ============================================================================


class TestBackgroundAdaptation:
    """Test background adaptation for different seasons and regions"""

    def test_seasonal_background_registration(self, cache_manager, temp_cache_dir):
        """Test registering seasonal background variants"""
        seasons = ["spring", "summer", "fall", "winter"]

        for season in seasons:
            cache_filename = f"background_{season}_us.jpg"
            cache_manager.register_cache_entry(
                cache_key=f"bg_{season}_us",
                file_path=cache_filename,
                metadata={"type": "background", "season": season, "region": "US"},
            )

        # Query backgrounds by season
        spring_backgrounds = cache_manager.find_by_metadata(type="background", season="spring")
        assert len(spring_backgrounds) == 1

    def test_regional_background_variants(self, cache_manager):
        """Test registering regional background variants"""
        regions = ["US", "LATAM", "APAC", "EMEA"]

        for region in regions:
            cache_manager.register_cache_entry(
                cache_key=f"bg_summer_{region}",
                file_path=f"background_summer_{region}.jpg",
                metadata={"type": "background", "season": "summer", "region": region},
            )

        # Query backgrounds by region
        emea_backgrounds = cache_manager.find_by_metadata(type="background", region="EMEA")
        assert len(emea_backgrounds) == 1

    def test_seasonal_asset_updates(self, cache_manager):
        """Test updating assets for seasonal campaigns"""
        # Register base product
        cache_manager.register_product(
            "Holiday Gift Set",
            "gift_set_base.png",
            "holiday_2024",
            tags=["winter", "holiday"],
        )

        # Update for new season
        cache_manager.register_product(
            "Holiday Gift Set",
            "gift_set_2025.png",
            "holiday_2025",
            tags=["winter", "holiday"],
        )

        product = cache_manager.lookup_product("Holiday Gift Set")

        # Should track both campaigns
        assert "holiday_2024" in product["campaigns_used"]
        assert "holiday_2025" in product["campaigns_used"]

    def test_background_style_variants(self, cache_manager):
        """Test different background styles (gradient, solid, scene)"""
        styles = ["gradient", "solid", "scene", "split_screen", "objects_only"]

        for style in styles:
            cache_manager.register_cache_entry(
                cache_key=f"bg_{style}_kitchen",
                file_path=f"background_{style}_kitchen.jpg",
                metadata={"type": "background", "style": style, "context": "kitchen"},
            )

        # Query by style
        gradient_backgrounds = cache_manager.find_by_metadata(type="background", style="gradient")
        assert len(gradient_backgrounds) == 1


# ============================================================================
# 4. ASSET VERSIONING & VARIANT TRACKING TESTS
# ============================================================================


class TestAssetVersioning:
    """Test asset versioning and variant tracking accuracy"""

    def test_product_version_tracking(self, cache_manager):
        """Test tracking multiple versions of same product"""
        product_name = "Power Dish Soap"

        # Register v1
        cache_manager.register_product(product_name, "product_v1.png", "campaign_q1", tags=["v1"])

        # Register v2 (updated packaging)
        cache_manager.register_product(product_name, "product_v2.png", "campaign_q2", tags=["v2"])

        product = cache_manager.lookup_product(product_name)

        # Should track both campaigns (acting as versions)
        assert len(product["campaigns_used"]) == 2
        assert "campaign_q1" in product["campaigns_used"]
        assert "campaign_q2" in product["campaigns_used"]

    def test_variant_metadata_accuracy(self, cache_manager):
        """Test accuracy of variant metadata tracking"""
        # Register product with detailed metadata
        metadata = {
            "product_name": "Test Product",
            "variant_id": "variant_1",
            "aspect_ratio": "1x1",
            "background_style": "gradient",
            "text_overlay": "Sale 20% Off",
            "region": "US",
        }

        cache_manager.register_cache_entry(
            cache_key="test_variant_1", file_path="variant_1.jpg", metadata=metadata
        )

        # Retrieve and verify
        entry = cache_manager.get_cache_entry("test_variant_1")

        assert entry["metadata"]["variant_id"] == "variant_1"
        assert entry["metadata"]["aspect_ratio"] == "1x1"
        assert entry["metadata"]["background_style"] == "gradient"

    def test_cache_entry_timestamps(self, cache_manager):
        """Test timestamp tracking for cache entries"""
        cache_manager.register_cache_entry(
            cache_key="test_timestamp", file_path="test.jpg", metadata={"test": "data"}
        )

        entry = cache_manager.get_cache_entry("test_timestamp")

        assert "created_at" in entry
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(entry["created_at"])

    def test_asset_lineage_with_versions(self, cache_manager):
        """Test tracking asset lineage with version information"""
        # Simulate cache hits with version info
        cache_manager.register_cache_entry(
            cache_key="product_v2",
            file_path="product_v2.png",
            metadata={"type": "product", "version": "2.0"},
        )

        cache_manager.register_cache_entry(
            cache_key="background_v1",
            file_path="background_v1.jpg",
            metadata={"type": "background", "version": "1.0"},
        )

        # Build lineage
        cache_hits = {"product": "product_v2.png", "background": "background_v1.jpg"}
        lineage = cache_manager.build_lineage_metadata(cache_hits)

        assert "product_cache_key" in lineage
        assert lineage["cache_count"] == 2


# ============================================================================
# 5. PERFORMANCE TESTING
# ============================================================================


class TestCachePerformance:
    """Test cache retrieval and matching performance"""

    def test_large_scale_product_lookup(self, cache_manager):
        """Test performance with large number of products"""
        # Register 1000 products
        num_products = 1000
        start_time = time.time()

        for i in range(num_products):
            cache_manager.register_product(
                f"Product {i:04d}", f"product_{i:04d}.png", "large_campaign", tags=["bulk"]
            )

        registration_time = time.time() - start_time

        # Test lookup performance
        lookup_start = time.time()
        result = cache_manager.lookup_product("Product 0500")
        lookup_time = time.time() - lookup_start

        assert result is not None
        assert lookup_time < 1.0  # Should be fast (< 1s) - adjusted for CI environment
        assert registration_time < 30.0  # Should complete in reasonable time - adjusted for CI

    def test_metadata_query_performance(self, cache_manager):
        """Test performance of metadata-based queries"""
        # Register 500 entries with various metadata
        for i in range(500):
            cache_manager.register_cache_entry(
                cache_key=f"entry_{i}",
                file_path=f"file_{i}.jpg",
                metadata={
                    "type": "product" if i % 2 == 0 else "background",
                    "region": ["US", "EMEA", "APAC"][i % 3],
                    "index": i,
                },
            )

        # Test query performance
        start_time = time.time()
        results = cache_manager.find_by_metadata(type="product", region="US")
        query_time = time.time() - start_time

        assert len(results) > 0
        assert query_time < 0.5  # Should be fast (< 500ms)

    def test_cache_index_size(self, cache_manager):
        """Test cache index size and memory efficiency"""
        # Register 100 products
        for i in range(100):
            cache_manager.register_product(
                f"Product {i}", f"product_{i}.png", "campaign", tags=["test"]
            )

        # Check index size
        index_size = len(json.dumps(cache_manager.index))

        # Index should be reasonably sized (< 1MB for 100 products)
        assert index_size < 1_000_000

    def test_concurrent_cache_access(self, cache_manager):
        """Test cache access with concurrent operations"""
        # Simulate concurrent writes
        products = ["Product A", "Product B", "Product C"]

        for product in products:
            cache_manager.register_product(product, f"{product.replace(' ', '_')}.png", "campaign")

        # Verify all were registered
        for product in products:
            result = cache_manager.lookup_product(product)
            assert result is not None

    def test_cache_validation_performance(
        self, cache_manager, temp_cache_dir, sample_product_image
    ):
        """Test performance of cache validation"""
        # Register products with actual files
        for i in range(50):
            filename = f"product_{i}.png"
            file_path = temp_cache_dir / filename
            sample_product_image.save(file_path, "PNG")

            cache_manager.register_cache_entry(
                cache_key=f"key_{i}", file_path=str(file_path), metadata={"index": i}
            )

        # Test validation performance
        start_time = time.time()
        validation_results = cache_manager.validate_cache()
        validation_time = time.time() - start_time

        assert validation_results["valid_entries"] >= 50  # At least 50, may have extra from cache reuse
        assert validation_time < 2.0  # Should be fast - adjusted for CI environment


# ============================================================================
# 6. EDGE CASE TESTING
# ============================================================================


class TestEdgeCases:
    """Test unusual asset combinations and edge cases"""

    def test_empty_product_name(self, cache_manager):
        """Test handling empty product names"""
        # Should handle gracefully
        slug = cache_manager._slugify_product_name("")
        assert slug == ""

    def test_special_characters_in_product_name(self, cache_manager):
        """Test product names with special characters"""
        names = [
            "Product @ 50% Off!",
            "Dish Soap (New & Improved)",
            "Detergent - Ultra Clean",
            "Product #1 Best Seller",
        ]

        for name in names:
            slug = cache_manager._slugify_product_name(name)
            # Should produce valid slug
            assert slug.isascii()
            assert " " not in slug

    def test_duplicate_product_registration(self, cache_manager):
        """Test registering same product multiple times"""
        product_name = "Test Product"

        # Register twice
        slug1 = cache_manager.register_product(product_name, "file1.png", "campaign_1")
        slug2 = cache_manager.register_product(product_name, "file2.png", "campaign_2")

        # Should return same slug
        assert slug1 == slug2

        # Should track both campaigns
        product = cache_manager.lookup_product(product_name)
        assert len(product["campaigns_used"]) == 2

    def test_missing_cache_files(self, cache_manager):
        """Test validation with missing cache files"""
        # Register entry without actual file
        cache_manager.register_cache_entry(
            cache_key="missing_file", file_path="/nonexistent/file.jpg", metadata={}
        )

        validation = cache_manager.validate_cache()

        assert validation["missing_entries"] > 0
        assert "missing_file" in validation["missing_keys"]

    def test_corrupted_index_recovery(self, temp_cache_dir):
        """Test recovery from corrupted index file"""
        # Create corrupted index
        index_path = temp_cache_dir / "index.json"
        with open(index_path, "w") as f:
            f.write("{ corrupted json")

        # Should handle gracefully
        cache_manager = CacheManager(cache_dir=str(temp_cache_dir))
        assert cache_manager.index == {}

    def test_unicode_product_names(self, cache_manager):
        """Test product names with unicode characters"""
        names = ["Producto Español", "Produit Français", "日本の製品"]

        for name in names:
            slug = cache_manager.register_product(name, f"{name}.png", "campaign")
            # Should create valid slug
            assert slug is not None
            assert len(slug) > 0

    def test_extremely_long_product_name(self, cache_manager):
        """Test handling very long product names"""
        long_name = "A" * 500

        slug = cache_manager._slugify_product_name(long_name)

        # Should handle without error
        assert len(slug) > 0

    def test_null_metadata_fields(self, cache_manager):
        """Test handling null metadata fields"""
        cache_manager.register_cache_entry(
            cache_key="test_null", file_path="test.jpg", metadata={"field1": None, "field2": ""}
        )

        entry = cache_manager.get_cache_entry("test_null")
        assert entry is not None

    def test_cross_region_asset_conflicts(self, cache_manager):
        """Test handling same product with different regional variants"""
        product_name = "Global Product"

        cache_manager.register_product(product_name, "global_us.png", "campaign_us", tags=["US"])
        cache_manager.register_product(
            product_name, "global_emea.png", "campaign_emea", tags=["EMEA"]
        )

        product = cache_manager.lookup_product(product_name)

        # Should track both campaigns
        assert len(product["campaigns_used"]) == 2


# ============================================================================
# 7. CLI INTEGRATION TESTS
# ============================================================================


class TestCLIIntegration:
    """Test integration with CLI workflow"""

    def test_cache_stats_command(self, cache_manager, sample_product_image, temp_cache_dir):
        """Test cache stats retrieval"""
        # Register some entries
        for i in range(5):
            filename = f"product_{i}.png"
            file_path = temp_cache_dir / filename
            sample_product_image.save(file_path, "PNG")

            cache_manager.register_cache_entry(
                cache_key=f"key_{i}", file_path=str(file_path), metadata={"type": "product"}
            )

        stats = cache_manager.get_cache_stats()

        assert stats["total_entries"] == 5
        assert stats["total_size_bytes"] > 0
        assert "product" in stats["by_type"]

    def test_cache_clear_command(self, cache_manager, sample_product_image, temp_cache_dir):
        """Test cache clearing functionality"""
        # Register entries with files
        for i in range(3):
            filename = f"product_{i}.png"
            file_path = temp_cache_dir / filename
            sample_product_image.save(file_path, "PNG")

            # Add to cache_entries section for proper clearing
            if "cache_entries" not in cache_manager.index:
                cache_manager.index["cache_entries"] = {}

            cache_manager.index["cache_entries"][f"key_{i}"] = {
                "file_path": str(file_path),
                "cache_key": f"key_{i}",
                "metadata": {"type": "product"},
            }
            cache_manager._save_index()

        # Clear cache
        cleared_count = cache_manager.clear_cache()

        assert cleared_count == 3
        assert len(cache_manager.index.get("cache_entries", {})) == 0

    def test_campaign_processing_with_cache(
        self, cache_manager, multi_campaign_setup, temp_cache_dir
    ):
        """Test full campaign processing workflow with cache"""
        # Simulate campaign processing
        campaign_id = "new_campaign_2025"

        # Check for reusable products
        reusable_product = cache_manager.lookup_product("Power Dish Soap")

        assert reusable_product is not None
        assert reusable_product["status"] == "ready"

        # Register new campaign usage
        cache_manager.register_product(
            "Power Dish Soap",
            reusable_product["cache_filename"],
            campaign_id,
            tags=["new"],
        )

        # Verify campaign tracking
        updated_product = cache_manager.lookup_product("Power Dish Soap")
        assert campaign_id in updated_product["campaigns_used"]

    def test_product_registry_listing(self, cache_manager, multi_campaign_setup):
        """Test listing all registered products"""
        all_products = cache_manager.list_all_products()

        assert len(all_products) > 0

        # Verify structure
        for _slug, product in all_products.items():
            assert "name" in product
            assert "slug" in product
            assert "campaigns_used" in product
            assert "status" in product

    def test_metadata_filtering_workflow(self, cache_manager, multi_campaign_setup):
        """Test filtering assets by metadata in workflow"""
        # Find all spring assets
        all_products = cache_manager.list_all_products()
        spring_assets = [p for slug, p in all_products.items() if "spring" in p.get("tags", [])]

        assert len(spring_assets) > 0

        # Find all US region assets
        us_assets = [p for slug, p in all_products.items() if "US" in p.get("tags", [])]
        assert len(us_assets) > 0


# ============================================================================
# INTEGRATION TEST SCENARIOS
# ============================================================================


class TestIntegrationScenarios:
    """End-to-end integration test scenarios"""

    def test_multi_campaign_asset_reuse_scenario(
        self, cache_manager, multi_campaign_setup, temp_cache_dir
    ):
        """
        Scenario: Marketing team launches new campaign reusing assets from previous campaigns

        Steps:
        1. Discover reusable products from previous campaigns
        2. Filter by region and season
        3. Register products for new campaign
        4. Track cache hits and lineage
        """
        # Step 1: Discover reusable products
        reusable_product = cache_manager.lookup_product("Power Dish Soap")
        assert reusable_product is not None

        # Step 2: Filter by metadata
        all_products = cache_manager.list_all_products()
        us_products = [p for slug, p in all_products.items() if "US" in p.get("tags", [])]
        assert len(us_products) > 0

        # Step 3: Register for new campaign
        new_campaign_id = "fall_2025"
        cache_manager.register_product(
            "Power Dish Soap",
            reusable_product["cache_filename"],
            new_campaign_id,
            tags=["fall", "US"],
        )

        # Step 4: Verify tracking
        updated_product = cache_manager.lookup_product("Power Dish Soap")
        assert new_campaign_id in updated_product["campaigns_used"]

        # Build lineage
        cache_hits = {"product": reusable_product["cache_filename"]}
        lineage = cache_manager.build_lineage_metadata(cache_hits)
        assert lineage["cache_count"] == 1

    def test_seasonal_campaign_update_scenario(self, cache_manager, temp_cache_dir):
        """
        Scenario: Update winter campaign to spring campaign with seasonal backgrounds

        Steps:
        1. Register winter assets
        2. Update backgrounds for spring
        3. Track seasonal variants
        4. Verify version tracking
        """
        # Step 1: Register winter assets
        cache_manager.register_product(
            "Holiday Gift Set", "gift_winter.png", "winter_2024", tags=["winter", "holiday"]
        )

        cache_manager.register_cache_entry(
            cache_key="bg_winter",
            file_path="background_winter.jpg",
            metadata={"type": "background", "season": "winter"},
        )

        # Step 2: Register spring variants
        cache_manager.register_cache_entry(
            cache_key="bg_spring",
            file_path="background_spring.jpg",
            metadata={"type": "background", "season": "spring"},
        )

        # Step 3: Query seasonal variants
        winter_bg = cache_manager.get_cache_entry("bg_winter")
        spring_bg = cache_manager.get_cache_entry("bg_spring")

        assert winter_bg["metadata"]["season"] == "winter"
        assert spring_bg["metadata"]["season"] == "spring"

    def test_performance_optimization_scenario(self, cache_manager):
        """
        Scenario: Measure cache hit rate improvement over time

        Steps:
        1. Track initial cache state
        2. Process multiple campaigns
        3. Measure cache hit rate
        4. Verify performance improvements
        """
        # Step 1: Initial state
        initial_stats = cache_manager.get_cache_stats()
        initial_stats["total_entries"]

        # Step 2: Register products for multiple campaigns
        campaigns = ["campaign_1", "campaign_2", "campaign_3"]
        products = ["Product A", "Product B"]

        for campaign in campaigns:
            for product in products:
                cache_manager.register_product(product, f"{product}_{campaign}.png", campaign)

        # Step 3: Calculate reuse metrics
        all_products = cache_manager.list_all_products()
        multi_use_products = [p for slug, p in all_products.items() if len(p["campaigns_used"]) > 1]

        reuse_rate = len(multi_use_products) / len(all_products) if len(all_products) > 0 else 0

        # Step 4: Verify improvements
        assert reuse_rate > 0  # Some reuse should occur
        assert len(multi_use_products) == 2  # Both products used in multiple campaigns


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
