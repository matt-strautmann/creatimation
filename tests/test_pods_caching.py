#!/usr/bin/env python3
"""
Test script to verify product caching with CleanWave Pods.

This script will:
1. Clear existing cache for pods
2. Generate the pods product image
3. Verify it's cached with correct metadata
4. Generate a creative using the cached product
"""

import json
import logging
from pathlib import Path

from src.container import DIContainer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    print("\n" + "="*70)
    print("Testing Product Caching with CleanWave Pods")
    print("="*70 + "\n")

    # Initialize container
    container = DIContainer()
    cache_manager = container.get_cache_manager()

    # Step 1: Check initial cache state
    print("📋 STEP 1: Checking initial cache state")
    print("-" * 70)

    pods_product = cache_manager.lookup_product("CleanWave Pods Spring Meadow")
    if pods_product:
        print(f"✓ Found existing cache entry:")
        print(f"  - File: {pods_product['file_path']}")
        print(f"  - Campaigns: {pods_product.get('campaigns_used', [])}")

        # Remove it to test fresh generation
        cache_key = pods_product['cache_key']
        if cache_key in cache_manager.index:
            del cache_manager.index[cache_key]
            cache_manager._save_index()
            print(f"  - Removed from cache to test fresh generation")
    else:
        print("✗ No existing cache entry (expected for fresh test)")

    print()

    # Step 2: Generate product using pipeline
    print("📋 STEP 2: Generating pods product through pipeline")
    print("-" * 70)

    # Create minimal brief for just the pods
    brief_path = "briefs/CleanWaveSpring2025_Demo.json"

    # Load brief
    with open(brief_path) as f:
        brief_data = json.load(f)

    # Keep only the pods product
    brief_data['products'] = [p for p in brief_data['products'] if 'Pods' in p['name']]
    brief_data['target_regions'] = ['US']  # Just one region for speed
    brief_data['creative_requirements']['aspect_ratios'] = ['1x1']  # Just one ratio
    brief_data['creative_requirements']['variant_types'] = ['base']  # Just one variant

    # Save temporary brief
    temp_brief_path = Path("briefs/temp_pods_test.json")
    with open(temp_brief_path, 'w') as f:
        json.dump(brief_data, f, indent=2)

    print(f"Created test brief: {temp_brief_path}")
    print(f"  - Product: {brief_data['products'][0]['name']}")
    print(f"  - Regions: {brief_data['target_regions']}")
    print(f"  - Ratios: {brief_data['creative_requirements']['aspect_ratios']}")
    print(f"  - Variants: {brief_data['creative_requirements']['variant_types']}")

    try:
        # Process campaign
        print("\n🎨 Processing campaign (this will generate the product)...")
        pipeline = container.get_pipeline(campaign_id="cleanwave_spring_demo_2025")

        # Enable simulation mode to avoid actual API calls
        pipeline.dry_run = False
        pipeline.image_generator.simulation_mode = True

        results = pipeline.process_campaign(str(temp_brief_path))

        print(f"\n✓ Campaign processed successfully!")
        print(f"  - Creatives generated: {results['total_creatives']}")
        print(f"  - Cache hits: {results['cache_hits']}")
        print(f"  - Cache misses: {results['cache_misses']}")

    except Exception as e:
        print(f"\n✗ Error processing campaign: {e}")
        import traceback
        traceback.print_exc()
        return

    finally:
        # Clean up temp brief
        if temp_brief_path.exists():
            temp_brief_path.unlink()
            print(f"\nCleaned up: {temp_brief_path}")

    print()

    # Step 3: Verify product is now cached
    print("📋 STEP 3: Verifying product is cached")
    print("-" * 70)

    pods_product = cache_manager.lookup_product("CleanWave Pods Spring Meadow")

    if pods_product:
        print("✓ Product successfully cached!")
        print(f"  - Cache key: {pods_product['cache_key']}")
        print(f"  - File path: {pods_product['file_path']}")
        print(f"  - File exists: {Path(pods_product['file_path']).exists()}")
        print(f"  - Campaigns used: {pods_product.get('campaigns_used', [])}")
        print(f"  - Tags: {pods_product.get('tags', [])}")

        # Check metadata
        metadata = pods_product.get('metadata', {})
        print(f"\n  Metadata:")
        print(f"    - Type: {metadata.get('type')}")
        print(f"    - Product name: {metadata.get('product_name')}")
        print(f"    - Product slug: {metadata.get('product_slug')}")
        print(f"    - Campaign ID: {metadata.get('campaign_id')}")
    else:
        print("✗ Product NOT found in cache (unexpected!)")

    print()

    # Step 4: Check cache stats
    print("📋 STEP 4: Cache statistics")
    print("-" * 70)

    stats = cache_manager.get_stats()
    print(f"Total entries: {stats['total_entries']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"Type breakdown:")
    for asset_type, count in stats['type_breakdown'].items():
        print(f"  - {asset_type}: {count}")

    print()

    # Step 5: Show cache index content
    print("📋 STEP 5: Cache index entries (product types only)")
    print("-" * 70)

    product_entries = {
        k: v for k, v in cache_manager.index.items()
        if v.get('metadata', {}).get('type') == 'product'
    }

    print(f"Found {len(product_entries)} product entries:")
    for key, entry in product_entries.items():
        metadata = entry.get('metadata', {})
        print(f"\n  {metadata.get('product_name', 'Unknown')}")
        print(f"    - Key: {key}")
        print(f"    - Campaigns: {metadata.get('campaigns_used', [])}")
        print(f"    - Size: {entry.get('size_bytes', 0):,} bytes")

    print("\n" + "="*70)
    print("✓ Test Complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
