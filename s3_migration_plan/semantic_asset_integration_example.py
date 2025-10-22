#!/usr/bin/env python3
"""
Example: Integrating Semantic Asset Reuse into Creative Pipeline

This example demonstrates how to use the intelligent semantic asset reuse
system within the creative automation pipeline to:
1. Discover and reuse existing backgrounds
2. Register new assets for future reuse
3. Track usage patterns for learning
4. Get intelligent recommendations
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cache_manager import (
    AssetType,
    CacheManager,
    ProductCategory,
    Season,
    SemanticMetadata,
    VisualStyle,
)


def example_1_basic_registration():
    """Example 1: Register a new semantic asset"""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Registering Semantic Assets")
    print("=" * 70)

    manager = CacheManager()

    # Create semantic metadata for a background
    metadata = SemanticMetadata(
        asset_type=AssetType.SCENE_BACKGROUND,
        product_category=ProductCategory.LAUNDRY_DETERGENT,
        region="US",
        visual_style=VisualStyle.WARM,
        season=Season.SUMMER,
        color_palette=["#FFE5B4", "#FFA07A", "#87CEEB"],
        tags=["laundry", "fresh", "outdoor", "sunny"],
        dimensions=(1024, 1024),
        aspect_ratio="1x1",
    )

    # Register the asset
    cache_key = "scene_summer_laundry_us_001"
    manager.register_semantic_asset(
        cache_key=cache_key,
        file_path="cache/scenes/summer_laundry_us.jpg",
        metadata=metadata,
        campaign_id="summer_2025",
    )

    print(f"\nRegistered asset: {cache_key}")
    print(f"  Category: {metadata.product_category.value}")
    print(f"  Region: {metadata.region}")
    print(f"  Season: {metadata.season.value}")
    print(f"  Style: {metadata.visual_style.value}")
    print(f"  Tags: {', '.join(metadata.tags)}")


def example_2_find_similar_assets():
    """Example 2: Find similar assets for reuse"""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Finding Similar Assets")
    print("=" * 70)

    manager = CacheManager()

    # Define what we're looking for
    target_metadata = SemanticMetadata(
        asset_type=AssetType.SCENE_BACKGROUND,
        product_category=ProductCategory.LAUNDRY_DETERGENT,
        region="US",
        season=Season.SUMMER,
        visual_style=VisualStyle.WARM,
    )

    # Find similar assets
    similar = manager.find_similar_assets(
        target_metadata=target_metadata,
        asset_type=AssetType.SCENE_BACKGROUND,
        min_similarity=0.5,
        max_results=5,
    )

    if similar:
        print(f"\nFound {len(similar)} similar assets:")
        for cache_key, similarity, asset_entry in similar:
            metadata = asset_entry.get("semantic_metadata", {})
            print(f"\n  {similarity:.2f} - {cache_key}")
            print(f"    Season: {metadata.get('season', 'unknown')}")
            print(f"    Style: {metadata.get('visual_style', 'unknown')}")
            print(f"    Used: {asset_entry.get('usage_count', 0)} times")
            print(f"    File: {asset_entry.get('file_path', 'unknown')}")
    else:
        print("\nNo similar assets found")


def example_3_cross_campaign_discovery():
    """Example 3: Discover assets from other campaigns"""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Cross-Campaign Asset Discovery")
    print("=" * 70)

    manager = CacheManager()

    # Discover assets from other campaigns
    discovered = manager.discover_cross_campaign_assets(
        campaign_id="fall_2025",
        asset_types=[AssetType.SCENE_BACKGROUND, AssetType.PRODUCT_TRANSPARENT],
    )

    print("\nDiscovered assets from previous campaigns:")
    for asset_type, assets in discovered.items():
        print(f"\n  {asset_type}: {len(assets)} assets")
        for cache_key, asset_entry in assets[:3]:  # Show first 3
            campaign = asset_entry.get("campaign_id", "unknown")
            usage = asset_entry.get("usage_count", 0)
            print(f"    - {cache_key} (from {campaign}, used {usage}x)")


def example_4_seasonal_backgrounds():
    """Example 4: Get season-appropriate backgrounds"""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Seasonal Background Selection")
    print("=" * 70)

    manager = CacheManager()

    # Get background appropriate for current season
    from datetime import datetime

    background = manager.get_seasonal_background(
        product_category=ProductCategory.LAUNDRY_DETERGENT,
        region="US",
        current_date=datetime.now(),
        visual_style=VisualStyle.WARM,
    )

    if background:
        cache_key, asset_entry = background
        metadata = asset_entry.get("semantic_metadata", {})
        print("\nSelected seasonal background:")
        print(f"  Cache Key: {cache_key}")
        print(f"  Season: {metadata.get('season', 'unknown')}")
        print(f"  Style: {metadata.get('visual_style', 'unknown')}")
        print(f"  File: {asset_entry.get('file_path', 'unknown')}")
        print(f"  Used: {asset_entry.get('usage_count', 0)} times")
    else:
        print("\nNo seasonal background found")


def example_5_smart_recommendations():
    """Example 5: Get intelligent recommendations based on learned patterns"""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Intelligent Asset Recommendations")
    print("=" * 70)

    manager = CacheManager()

    # First, record some usage to build patterns
    manager.record_asset_reuse(
        source_cache_key="scene_summer_laundry_us_001",
        target_campaign="summer_2025",
        success=True,
        context="laundry_US",
    )

    # Get recommendations
    target_metadata = SemanticMetadata(
        asset_type=AssetType.SCENE_BACKGROUND,
        product_category=ProductCategory.LAUNDRY_DETERGENT,
        region="US",
        season=Season.SUMMER,
        visual_style=VisualStyle.WARM,
    )

    recommendations = manager.get_recommended_assets(
        target_metadata=target_metadata,
        campaign_id="summer_2025",
        max_results=5,
    )

    if recommendations:
        print(f"\nTop {len(recommendations)} recommendations:")
        for i, (cache_key, score, asset_entry) in enumerate(recommendations, 1):
            metadata = asset_entry.get("semantic_metadata", {})
            usage = asset_entry.get("usage_count", 0)
            print(f"\n  {i}. Score: {score:.2f} - {cache_key}")
            print(f"     Used {usage} times across campaigns")
            print(f"     Season: {metadata.get('season', 'unknown')}")
            print(f"     Style: {metadata.get('visual_style', 'unknown')}")
    else:
        print("\nNo recommendations available")


def example_6_pipeline_integration():
    """Example 6: Full pipeline integration pattern"""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Pipeline Integration Pattern")
    print("=" * 70)

    manager = CacheManager()
    campaign_id = "summer_2025"
    product_category = ProductCategory.DISH_SOAP
    region = "LATAM"

    # Step 1: Check for existing backgrounds
    print("\nStep 1: Checking for reusable backgrounds...")

    target_metadata = SemanticMetadata(
        asset_type=AssetType.SCENE_BACKGROUND,
        product_category=product_category,
        region=region,
        visual_style=VisualStyle.VIBRANT,
    )

    backgrounds = manager.find_similar_assets(
        target_metadata=target_metadata,
        asset_type=AssetType.SCENE_BACKGROUND,
        min_similarity=0.6,
        max_results=1,
    )

    if backgrounds:
        cache_key, similarity, asset_entry = backgrounds[0]
        print(f"  Found reusable background: {cache_key} (similarity: {similarity:.2f})")

        # Step 2: Reuse existing asset
        background_path = asset_entry["file_path"]
        print(f"  Reusing: {background_path}")

        # Step 3: Record reuse for learning
        manager.record_asset_reuse(
            source_cache_key=cache_key,
            target_campaign=campaign_id,
            success=True,
            context=f"{product_category.value}_{region}",
        )
        print("  Recorded reuse pattern")

    else:
        print("  No reusable backgrounds found")
        print("  Would generate new background here...")

        # In real pipeline, would call:
        # new_background = image_generator.generate_contextual_background(...)

        # Then register for future reuse:
        new_cache_key = f"scene_{product_category.value}_{region}_001"
        print(f"  Would register as: {new_cache_key}")


def example_7_asset_analytics():
    """Example 7: View asset reuse analytics"""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Asset Reuse Analytics")
    print("=" * 70)

    manager = CacheManager()

    # Get analytics for all campaigns
    analytics = manager.get_reuse_analytics()

    print("\nOverall Analytics:")
    print(f"  Total patterns: {analytics['total_patterns']}")
    print(f"  Total reuses: {analytics['total_reuses']}")
    print(f"  Average success rate: {analytics['average_success_rate']:.1%}")

    if analytics["most_reused_assets"]:
        print("\n  Top 5 most reused assets:")
        for asset_info in analytics["most_reused_assets"][:5]:
            print(f"    - {asset_info['cache_key']}: {asset_info['reuse_count']} reuses")

    # Get analytics for specific campaign
    campaign_analytics = manager.get_reuse_analytics(campaign_id="summer_2025")
    print("\nSummer 2025 Campaign:")
    print(f"  Campaign reuses: {campaign_analytics['total_reuses']}")
    print(f"  Success rate: {campaign_analytics['average_success_rate']:.1%}")


def example_8_seasonal_variants():
    """Example 8: Create seasonal variants"""
    print("\n" + "=" * 70)
    print("EXAMPLE 8: Creating Seasonal Variants")
    print("=" * 70)

    manager = CacheManager()

    source_key = "scene_master_laundry_us"

    # Create winter variant
    success = manager.create_seasonal_variant(
        source_cache_key=source_key,
        new_cache_key=f"{source_key}_winter",
        new_file_path="cache/variants/winter_laundry.jpg",
        target_season=Season.WINTER,
        change_notes="Added snow and winter elements",
    )

    if success:
        print(f"\nCreated winter variant for {source_key}")

        # Get version history
        versions = manager.get_version_history(source_key)
        print(f"\nVersion history ({len(versions)} versions):")
        for v in versions:
            print(f"  - {v.version}: {v.change_notes}")
    else:
        print("\nFailed to create variant (source not found)")


def main():
    """Run all examples"""
    print("\n" + "=" * 70)
    print("SEMANTIC ASSET REUSE INTEGRATION EXAMPLES")
    print("=" * 70)

    examples = [
        example_1_basic_registration,
        example_2_find_similar_assets,
        example_3_cross_campaign_discovery,
        example_4_seasonal_backgrounds,
        example_5_smart_recommendations,
        example_6_pipeline_integration,
        example_7_asset_analytics,
        example_8_seasonal_variants,
    ]

    print("\nRunning examples...")
    print("(Note: Some examples may show 'not found' if no assets are registered yet)")

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            print(f"\nError in {example_func.__name__}: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("EXAMPLES COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Review the code above to understand integration patterns")
    print("2. Check SEMANTIC_ASSET_REUSE.md for full documentation")
    print("3. Try CLI commands: python src/cache_manager.py --help")
    print("4. Integrate into your pipeline using these patterns")
    print()


if __name__ == "__main__":
    main()
