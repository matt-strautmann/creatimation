#!/usr/bin/env python3
"""
S3 CLI Commands - Command-line interface for S3 operations

Provides comprehensive CLI for S3 storage management, migration,
and asset operations.
"""

import argparse
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_upload(args):
    """Upload local cache to S3"""
    from s3_migration import migrate_with_progress_bar

    logger.info("Starting S3 upload...")

    result = migrate_with_progress_bar(
        cache_dir=args.cache_dir,
        bucket_name=args.bucket,
        prefix=args.prefix,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("\nDRY RUN complete - no files were uploaded")
    else:
        print("\nUpload complete!")
        print(f"  Uploaded: {result.uploaded_count} files")
        print(f"  Failed: {result.failed_count} files")
        print(f"  Total size: {result.uploaded_bytes / 1024 / 1024:.2f} MB")

    return 0 if result.failed_count == 0 else 1


def cmd_download(args):
    """Download specific asset from S3"""
    from s3_storage_manager import S3Config, S3StorageManager

    try:
        config = (
            S3Config.from_env()
            if not args.bucket
            else S3Config(
                bucket_name=args.bucket,
                prefix=args.prefix,
            )
        )

        s3_manager = S3StorageManager(config=config)

        output_path = Path(args.output) if args.output else Path(args.s3_key).name

        print(f"Downloading {args.s3_key} to {output_path}...")

        success = s3_manager.download_file(
            s3_key=args.s3_key,
            local_path=output_path,
        )

        if success:
            print(f"Download complete: {output_path}")
            return 0
        else:
            print("Download failed")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_list(args):
    """List assets in S3"""
    from s3_storage_manager import S3Config, S3StorageManager

    try:
        config = (
            S3Config.from_env()
            if not args.bucket
            else S3Config(
                bucket_name=args.bucket,
                prefix=args.prefix,
            )
        )

        s3_manager = S3StorageManager(config=config)

        print(f"Listing assets in s3://{config.bucket_name}/{config.prefix}...")

        # Build prefix filter
        search_prefix = config.prefix
        if args.asset_type:
            search_prefix = f"{config.prefix}/{args.asset_type}s"

        objects = s3_manager.list_objects(
            prefix=search_prefix,
            max_keys=args.max_results,
            include_metadata=args.metadata,
        )

        if not objects:
            print("No assets found")
            return 0

        print(f"\nFound {len(objects)} assets:\n")

        # Display assets
        for obj in objects:
            print(f"  {obj['s3_key']}")
            print(f"    Size: {obj['size_bytes'] / 1024:.1f} KB")
            print(f"    Modified: {obj['last_modified']}")

            if args.metadata and obj.get("metadata"):
                print("    Metadata:")
                for key, value in obj["metadata"].items():
                    print(f"      {key}: {value}")

            parsed = obj.get("parsed", {})
            if parsed:
                print(f"    Type: {parsed.get('type', 'unknown')}")
                if parsed.get("category"):
                    print(f"    Category: {parsed['category']}")
                if parsed.get("campaign_id"):
                    print(f"    Campaign: {parsed['campaign_id']}")

            print()

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_validate(args):
    """Validate migration"""
    from cache_manager import CacheManager
    from s3_migration import S3MigrationManager
    from s3_storage_manager import S3Config, S3StorageManager

    try:
        cache_manager = CacheManager(cache_dir=args.cache_dir)

        config = (
            S3Config.from_env()
            if not args.bucket
            else S3Config(
                bucket_name=args.bucket,
                prefix=args.prefix,
            )
        )

        s3_manager = S3StorageManager(config=config)
        migration_manager = S3MigrationManager(cache_manager, s3_manager)

        print("Creating migration plan...")
        plan = migration_manager.create_migration_plan()

        print("Validating migration...")
        report = migration_manager.validate_migration(plan)

        print("\nValidation Report:")
        print(f"  Total assets: {report['total_assets']}")
        print(f"  Validated: {report['validated']}")
        print(f"  Missing in S3: {report['missing']}")
        print(f"  Size mismatches: {report['size_mismatches']}")
        print(f"  Success rate: {report['success_rate']:.1f}%")

        if report["missing_details"]:
            print("\nMissing assets (first 10):")
            for missing in report["missing_details"]:
                print(f"  {missing['local_path']} -> {missing['s3_key']}")

        if report["mismatch_details"]:
            print("\nSize mismatches (first 10):")
            for mismatch in report["mismatch_details"]:
                print(
                    f"  {mismatch['local_path']}: "
                    f"local={mismatch['local_size']}, s3={mismatch['s3_size']}"
                )

        return 0 if report["missing"] == 0 and report["size_mismatches"] == 0 else 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_stats(args):
    """Show S3 statistics"""
    from cache_manager_s3 import S3CacheManager

    try:
        cache_manager = S3CacheManager(cache_dir=args.cache_dir)

        if not cache_manager.s3_enabled:
            print("S3 is not enabled. Set S3_BUCKET_NAME in your .env file.")
            return 1

        print("\nS3 Cache Statistics")
        print("=" * 60)

        stats = cache_manager.get_s3_stats()

        print("\nS3 Configuration:")
        print(f"  Bucket: {stats.get('bucket_name', 'N/A')}")
        print(f"  Assets in S3: {stats.get('s3_assets', 0)}")

        if stats.get("s3_total_objects"):
            print(f"  Total S3 objects: {stats['s3_total_objects']}")
            print(f"  Total S3 size: {stats.get('s3_total_size_mb', 0):.2f} MB")

        print("\nCache Operations:")
        print(f"  Uploads: {stats.get('uploads', 0)}")
        print(f"  Downloads: {stats.get('downloads', 0)}")
        print(f"  Cache hits: {stats.get('cache_hits', 0)}")
        print(f"  Cache misses: {stats.get('cache_misses', 0)}")
        print(f"  Cache hit rate: {stats.get('cache_hit_rate', 0):.1f}%")

        print("\nLocal Cache:")
        print(f"  Size: {stats.get('local_cache_size_mb', 0):.2f} MB")

        # Get regular cache stats
        cache_stats = cache_manager.get_cache_stats()
        print(f"\nTotal Cache Entries: {cache_stats['total_entries']}")
        print(f"Total Cache Size: {cache_stats['total_size_mb']:.2f} MB")

        print()
        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_discover(args):
    """Discover assets in S3"""
    from cache_manager_s3 import S3CacheManager

    try:
        cache_manager = S3CacheManager(cache_dir=args.cache_dir)

        if not cache_manager.s3_enabled:
            print("S3 is not enabled. Set S3_BUCKET_NAME in your .env file.")
            return 1

        print("Discovering assets in S3...")

        assets = cache_manager.discover_s3_assets(sync_to_local=args.sync)

        print(f"\nDiscovered {len(assets)} assets:\n")

        # Group by type
        by_type = {}
        for asset in assets:
            asset_type = asset.get("parsed", {}).get("type", "unknown")
            by_type.setdefault(asset_type, []).append(asset)

        for asset_type, type_assets in by_type.items():
            print(f"\n{asset_type.upper()}:")
            for asset in type_assets[:10]:  # Show first 10
                print(f"  {asset['s3_key']}")
                print(f"    Size: {asset['size_bytes'] / 1024:.1f} KB")

            if len(type_assets) > 10:
                print(f"  ... and {len(type_assets) - 10} more")

        if args.sync:
            print(f"\nSynced {len(assets)} assets to local index")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_tier_manage(args):
    """Manage cache tiers"""
    from cache_manager_s3 import S3CacheManager

    try:
        cache_manager = S3CacheManager(cache_dir=args.cache_dir)

        if not cache_manager.s3_enabled:
            print("S3 is not enabled. Set S3_BUCKET_NAME in your .env file.")
            return 1

        print("Managing cache tiers...")

        result = cache_manager.manage_cache_tiers(
            promote_hot_assets=not args.no_promote,
            demote_cold_assets=not args.no_demote,
            cold_threshold_days=args.cold_days,
        )

        print("\nTier Management Results:")
        print(f"  Promoted (S3 -> local): {result['promoted']}")
        print(f"  Demoted (local -> S3 only): {result['demoted']}")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def cmd_estimate(args):
    """Estimate migration costs"""
    from cache_manager import CacheManager
    from s3_migration import S3MigrationManager
    from s3_storage_manager import S3Config, S3StorageManager

    try:
        cache_manager = CacheManager(cache_dir=args.cache_dir)

        config = (
            S3Config.from_env()
            if not args.bucket
            else S3Config(
                bucket_name=args.bucket,
                prefix=args.prefix,
            )
        )

        s3_manager = S3StorageManager(config=config)
        migration_manager = S3MigrationManager(cache_manager, s3_manager)

        print("Analyzing cache for migration...")
        plan = migration_manager.create_migration_plan()

        print("\nMigration Plan:")
        print(f"  Total assets: {plan.total_assets}")
        print(
            f"  Total size: {plan.total_size_mb:.2f} MB ({plan.total_size_bytes / 1024 / 1024 / 1024:.3f} GB)"
        )
        print(f"  Products: {len(plan.products)}")
        print(f"  Semantic assets: {len(plan.semantic_assets)}")
        print(f"  Cache entries: {len(plan.cache_entries)}")

        print("\nEstimated S3 Costs:")

        # Standard storage
        cost = migration_manager.estimate_migration_cost(plan, cost_per_gb=0.023)
        print("\n  Standard Storage:")
        print(f"    Monthly: ${cost['storage_cost_monthly']}")
        print(f"    Yearly: ${cost['storage_cost_yearly']}")

        # Intelligent-Tiering
        cost_it = migration_manager.estimate_migration_cost(plan, cost_per_gb=0.0125)
        print("\n  Intelligent-Tiering:")
        print(f"    Monthly: ${cost_it['storage_cost_monthly']}")
        print(f"    Yearly: ${cost_it['storage_cost_yearly']}")

        # Glacier
        cost_glacier = migration_manager.estimate_migration_cost(plan, cost_per_gb=0.004)
        print("\n  Glacier (archive):")
        print(f"    Monthly: ${cost_glacier['storage_cost_monthly']}")
        print(f"    Yearly: ${cost_glacier['storage_cost_yearly']}")

        print("\nNote: Costs are estimates and don't include transfer or request charges.")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="S3 Storage Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload cache to S3
  python src/cli_s3.py upload --cache-dir cache

  # Upload with dry run
  python src/cli_s3.py upload --cache-dir cache --dry-run

  # List S3 assets
  python src/cli_s3.py list

  # List with metadata
  python src/cli_s3.py list --metadata

  # Validate migration
  python src/cli_s3.py validate --cache-dir cache

  # Show S3 statistics
  python src/cli_s3.py stats

  # Discover S3 assets and sync to local index
  python src/cli_s3.py discover --sync

  # Manage cache tiers
  python src/cli_s3.py tier-manage --cold-days 30

  # Estimate migration costs
  python src/cli_s3.py estimate --cache-dir cache
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Upload command
    upload_parser = subparsers.add_parser("upload", help="Upload cache to S3")
    upload_parser.add_argument("--cache-dir", default="cache", help="Cache directory")
    upload_parser.add_argument("--bucket", help="S3 bucket name (overrides env)")
    upload_parser.add_argument("--prefix", default="creative-assets", help="S3 prefix")
    upload_parser.add_argument(
        "--dry-run", action="store_true", help="Simulate upload without uploading"
    )

    # Download command
    download_parser = subparsers.add_parser("download", help="Download asset from S3")
    download_parser.add_argument("s3_key", help="S3 key to download")
    download_parser.add_argument("--output", help="Output path (default: same as S3 key)")
    download_parser.add_argument("--bucket", help="S3 bucket name (overrides env)")
    download_parser.add_argument("--prefix", default="creative-assets", help="S3 prefix")

    # List command
    list_parser = subparsers.add_parser("list", help="List assets in S3")
    list_parser.add_argument("--bucket", help="S3 bucket name (overrides env)")
    list_parser.add_argument("--prefix", default="creative-assets", help="S3 prefix")
    list_parser.add_argument(
        "--asset-type",
        choices=["product", "background", "composite"],
        help="Filter by asset type",
    )
    list_parser.add_argument("--max-results", type=int, default=100, help="Max results")
    list_parser.add_argument("--metadata", action="store_true", help="Include metadata")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate migration")
    validate_parser.add_argument("--cache-dir", default="cache", help="Cache directory")
    validate_parser.add_argument("--bucket", help="S3 bucket name (overrides env)")
    validate_parser.add_argument("--prefix", default="creative-assets", help="S3 prefix")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show S3 statistics")
    stats_parser.add_argument("--cache-dir", default="cache", help="Cache directory")

    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Discover S3 assets")
    discover_parser.add_argument("--cache-dir", default="cache", help="Cache directory")
    discover_parser.add_argument(
        "--sync", action="store_true", help="Sync discovered assets to local index"
    )

    # Tier management command
    tier_parser = subparsers.add_parser("tier-manage", help="Manage cache tiers")
    tier_parser.add_argument("--cache-dir", default="cache", help="Cache directory")
    tier_parser.add_argument("--no-promote", action="store_true", help="Don't promote hot assets")
    tier_parser.add_argument("--no-demote", action="store_true", help="Don't demote cold assets")
    tier_parser.add_argument(
        "--cold-days", type=int, default=30, help="Days to consider asset cold"
    )

    # Estimate command
    estimate_parser = subparsers.add_parser("estimate", help="Estimate costs")
    estimate_parser.add_argument("--cache-dir", default="cache", help="Cache directory")
    estimate_parser.add_argument("--bucket", help="S3 bucket name (overrides env)")
    estimate_parser.add_argument("--prefix", default="creative-assets", help="S3 prefix")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Map commands to functions
    commands = {
        "upload": cmd_upload,
        "download": cmd_download,
        "list": cmd_list,
        "validate": cmd_validate,
        "stats": cmd_stats,
        "discover": cmd_discover,
        "tier-manage": cmd_tier_manage,
        "estimate": cmd_estimate,
    }

    try:
        return commands[args.command](args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
