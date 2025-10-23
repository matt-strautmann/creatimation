#!/usr/bin/env python3
"""
S3 Integration Examples

Practical examples demonstrating S3 storage integration with the
Creative Automation Pipeline cache manager.

Run these examples to see S3 integration in action.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def example_1_basic_s3_upload():
    """Example 1: Basic S3 file upload"""
    print("\n" + "=" * 60)
    print("EXAMPLE 1: Basic S3 Upload")
    print("=" * 60)

    from s3_storage_manager import S3Config, S3StorageManager

    # Initialize S3 manager (reads from .env)
    try:
        config = S3Config.from_env()
        s3_manager = S3StorageManager(config=config)

        # Create test file
        test_file = Path("/tmp/test_asset.txt")  # nosec B108
        test_file.write_text("Test creative asset content")

        # Upload to S3
        result = s3_manager.upload_file(
            local_path=test_file,
            s3_key="examples/test_asset.txt",
            metadata={"type": "example", "version": "1.0"},
            tags={"project": "creative-automation", "environment": "test"},
        )

        if result.success:
            print("\nUpload successful!")
            print(f"  S3 Key: {result.s3_key}")
            print(f"  Size: {result.size_bytes} bytes")
            print(f"  Duration: {result.duration_seconds:.2f}s")
            print(f"  ETag: {result.etag}")
        else:
            print(f"\nUpload failed: {result.error}")

        # Clean up
        test_file.unlink()

    except Exception as e:
        print(f"\nError: {e}")
        print("Make sure S3_BUCKET_NAME is set in your .env file")


def example_2_batch_upload():
    """Example 2: Batch upload multiple files"""
    print("\n" + "=" * 60)
    print("EXAMPLE 2: Batch Upload with Progress")
    print("=" * 60)

    import shutil
    import tempfile

    from PIL import Image

    from s3_storage_manager import S3Config, S3StorageManager

    try:
        config = S3Config.from_env()
        s3_manager = S3StorageManager(config=config)

        # Create temporary directory with test files
        temp_dir = Path(tempfile.mkdtemp())

        print("\nCreating 10 test images...")
        file_mappings = []

        for i in range(10):
            # Create test image
            img = Image.new("RGB", (100, 100), color=(i * 25, i * 25, i * 25))
            img_path = temp_dir / f"test_image_{i}.png"
            img.save(img_path, "PNG")

            # Add to batch
            file_mappings.append(
                (
                    img_path,
                    f"examples/batch/image_{i}.png",
                    {"type": "test-image", "index": str(i)},
                )
            )

        print(f"Uploading {len(file_mappings)} files to S3...")

        # Progress callback
        def progress_callback(progress):
            percent = progress.percent_complete
            uploaded = progress.uploaded
            total = progress.total_files
            speed = progress.upload_speed_mbps

            print(
                f"  Progress: {percent:5.1f}% ({uploaded}/{total}) - {speed:.2f} MB/s",
                end="\r",
            )

        # Batch upload
        results, final_progress = s3_manager.batch_upload(
            file_mappings, progress_callback=progress_callback
        )

        print("\n\nBatch upload complete!")
        print(f"  Uploaded: {final_progress.uploaded}")
        print(f"  Failed: {final_progress.failed}")
        print(f"  Total size: {final_progress.uploaded_bytes / 1024:.1f} KB")
        print(f"  Duration: {final_progress.elapsed_time:.2f}s")
        print(f"  Average speed: {final_progress.upload_speed_mbps:.2f} MB/s")

        # Clean up
        shutil.rmtree(temp_dir)

    except Exception as e:
        print(f"\nError: {e}")


def example_3_hybrid_cache():
    """Example 3: Hybrid cache with automatic S3 integration"""
    print("\n" + "=" * 60)
    print("EXAMPLE 3: Hybrid Local/S3 Cache")
    print("=" * 60)

    import shutil
    import tempfile

    from PIL import Image

    from cache_manager import AssetType, ProductCategory, SemanticMetadata
    from cache_manager_s3 import S3CacheManager

    try:
        # Create temporary cache directory
        cache_dir = Path(tempfile.mkdtemp())

        # Initialize hybrid cache manager
        print("\nInitializing hybrid cache manager...")
        cache_manager = S3CacheManager(
            cache_dir=str(cache_dir),
            enable_s3=True,
            local_cache_size_limit_gb=0.01,  # 10 MB for demo
        )

        if cache_manager.s3_enabled:
            print("  S3 integration: ENABLED")
        else:
            print("  S3 integration: DISABLED (local-only mode)")
            print("  Set S3_BUCKET_NAME in .env to enable S3")

        # Create test asset
        print("\nCreating test product asset...")
        img = Image.new("RGB", (200, 200), color=(255, 0, 0))
        img_path = cache_dir / "dish_soap_product.png"
        img.save(img_path, "PNG")

        # Register with semantic metadata
        print("Registering asset with semantic metadata...")
        metadata = SemanticMetadata(
            asset_type=AssetType.PRODUCT_TRANSPARENT,
            product_category=ProductCategory.DISH_SOAP,
            region="US",
            tags=["test", "example"],
        )

        cache_manager.register_semantic_asset(
            cache_key="dish-soap-us-001",
            file_path=str(img_path),
            metadata=metadata,
            campaign_id="test_campaign",
            upload_to_s3=True,  # Automatically uploads to S3
        )

        print("  Asset registered successfully")

        # Retrieve asset (downloads from S3 if not local)
        print("\nRetrieving asset...")
        asset_path = cache_manager.get_asset_path(
            cache_key="dish-soap-us-001",
            auto_download=True,
        )

        if asset_path:
            print(f"  Asset available at: {asset_path}")
            print(f"  File exists: {asset_path.exists()}")
        else:
            print("  Asset not found")

        # Show statistics
        if cache_manager.s3_enabled:
            print("\nS3 Statistics:")
            stats = cache_manager.get_s3_stats()
            print(f"  S3 assets: {stats['s3_assets']}")
            print(f"  Uploads: {stats['uploads']}")
            print(f"  Downloads: {stats['downloads']}")
            print(f"  Cache hit rate: {stats['cache_hit_rate']}%")
            print(f"  Local cache size: {stats['local_cache_size_mb']:.2f} MB")

        # Clean up
        shutil.rmtree(cache_dir)

    except Exception as e:
        print(f"\nError: {e}")


def example_4_semantic_discovery():
    """Example 4: Discover assets with semantic filtering"""
    print("\n" + "=" * 60)
    print("EXAMPLE 4: Semantic Asset Discovery")
    print("=" * 60)

    from s3_storage_manager import S3Config, S3StorageManager

    try:
        config = S3Config.from_env()
        s3_manager = S3StorageManager(config=config)

        # Discover product assets
        print("\nDiscovering product assets...")
        products = s3_manager.find_assets_by_semantic_filter(
            asset_type="product",
            category="dish_soap",
        )

        if products:
            print(f"\nFound {len(products)} product assets:")
            for asset in products[:5]:  # Show first 5
                print(f"\n  {asset['s3_key']}")
                print(f"    Size: {asset['size_bytes'] / 1024:.1f} KB")
                print(f"    Modified: {asset['last_modified']}")

                parsed = asset.get("parsed", {})
                if parsed.get("product_slug"):
                    print(f"    Product: {parsed['product_slug']}")
        else:
            print("  No product assets found")

        # Discover background assets
        print("\nDiscovering background assets...")
        backgrounds = s3_manager.find_assets_by_semantic_filter(
            asset_type="background", region="US", season="spring"
        )

        if backgrounds:
            print(f"\nFound {len(backgrounds)} background assets:")
            for asset in backgrounds[:3]:  # Show first 3
                print(f"  {asset['s3_key']}")
        else:
            print("  No background assets found")

    except Exception as e:
        print(f"\nError: {e}")


def example_5_migration():
    """Example 5: Migrate local cache to S3"""
    print("\n" + "=" * 60)
    print("EXAMPLE 5: Cache Migration to S3")
    print("=" * 60)

    import shutil
    import tempfile

    from PIL import Image

    from cache_manager import CacheManager
    from s3_migration import S3MigrationManager
    from s3_storage_manager import S3Config, S3StorageManager

    try:
        # Create temporary cache with sample data
        cache_dir = Path(tempfile.mkdtemp())

        print("\nCreating sample cache...")
        cache_manager = CacheManager(cache_dir=str(cache_dir))

        # Create sample assets
        for i in range(3):
            img = Image.new("RGB", (100, 100), color=(i * 80, 0, 0))
            img_path = cache_dir / f"product_{i}.png"
            img.save(img_path, "PNG")

            cache_manager.register_product(
                product_name=f"Test Product {i}",
                cache_filename=f"product_{i}.png",
                campaign_id="test_campaign",
            )

        # Initialize S3 migration
        print("Initializing migration...")
        config = S3Config.from_env()
        s3_manager = S3StorageManager(config=config)
        migration_manager = S3MigrationManager(cache_manager, s3_manager)

        # Create migration plan
        print("\nCreating migration plan...")
        plan = migration_manager.create_migration_plan()

        print("\nMigration Plan:")
        print(f"  Total assets: {plan.total_assets}")
        print(f"  Total size: {plan.total_size_mb:.2f} MB")
        print(f"  Products: {len(plan.products)}")

        # Estimate costs
        cost = migration_manager.estimate_migration_cost(plan)
        print("\nEstimated Monthly Costs:")
        print(f"  Standard Storage: ${cost['storage_cost_monthly']}")
        print(f"  Size: {cost['size_gb']:.3f} GB")

        # Dry run migration
        print("\nExecuting dry run...")
        result = migration_manager.execute_migration(plan, dry_run=True)

        print("\nDry Run Results:")
        print(f"  Would upload: {result.uploaded_count} files")
        print(f"  Total size: {result.uploaded_bytes / 1024:.1f} KB")

        # Clean up
        shutil.rmtree(cache_dir)

    except Exception as e:
        print(f"\nError: {e}")


def example_6_presigned_urls():
    """Example 6: Generate presigned URLs for temporary access"""
    print("\n" + "=" * 60)
    print("EXAMPLE 6: Presigned URLs for Temporary Access")
    print("=" * 60)

    from s3_storage_manager import S3Config, S3StorageManager

    try:
        config = S3Config.from_env()
        s3_manager = S3StorageManager(config=config)

        # Create test file
        test_file = Path("/tmp/shared_asset.txt")  # nosec B108
        test_file.write_text("Shared creative asset")

        # Upload to S3
        result = s3_manager.upload_file(
            local_path=test_file,
            s3_key="examples/shared_asset.txt",
            metadata={"type": "shared"},
        )

        if result.success:
            # Generate presigned URL (valid for 1 hour)
            print("\nGenerating presigned URL...")
            url = s3_manager.get_presigned_url(
                s3_key="examples/shared_asset.txt",
                expiration=3600,  # 1 hour
            )

            if url:
                print("\nPresigned URL generated successfully!")
                print("  URL (valid for 1 hour):")
                print(f"  {url[:80]}...")
                print("\n  Anyone with this URL can download the file for 1 hour")
                print("  No AWS credentials needed")
            else:
                print("  Failed to generate presigned URL")

        # Clean up
        test_file.unlink()

    except Exception as e:
        print(f"\nError: {e}")


def main():
    """Run all examples"""
    print("\n" + "=" * 60)
    print("S3 INTEGRATION EXAMPLES")
    print("=" * 60)
    print("\nThese examples demonstrate S3 integration capabilities.")
    print("Make sure S3_BUCKET_NAME is set in your .env file.")
    print("\nPress Enter to continue or Ctrl+C to cancel...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled")
        return

    # Run examples
    example_1_basic_s3_upload()
    example_2_batch_upload()
    example_3_hybrid_cache()
    example_4_semantic_discovery()
    example_5_migration()
    example_6_presigned_urls()

    print("\n" + "=" * 60)
    print("EXAMPLES COMPLETE")
    print("=" * 60)
    print("\nFor more information, see docs/S3_INTEGRATION.md and docs/S3_QUICKSTART.md")


if __name__ == "__main__":
    main()
