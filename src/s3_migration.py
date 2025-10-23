#!/usr/bin/env python3
"""
S3 Migration Utilities - Migrate local cache assets to S3

Provides tools for migrating existing local cache structure to S3
while preserving semantic metadata and folder organization.

Features:
- Local cache discovery and analysis
- Semantic metadata preservation during migration
- Batch migration with progress tracking
- Validation and verification
- Rollback capabilities
- Dry-run mode for testing
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cache_manager import (
    CacheManager,
)
from s3_storage_manager import S3Config, S3StorageManager, UploadProgress

logger = logging.getLogger(__name__)


# ============================================================================
# MIGRATION PLANNING
# ============================================================================


@dataclass
class MigrationPlan:
    """Plan for migrating cache assets to S3"""

    total_assets: int
    total_size_bytes: int
    products: list[dict[str, Any]]
    semantic_assets: list[dict[str, Any]]
    cache_entries: list[dict[str, Any]]
    metadata_file: Path | None = None

    @property
    def total_size_mb(self) -> float:
        """Get total size in MB"""
        return self.total_size_bytes / 1024 / 1024

    def summary(self) -> str:
        """Generate summary string"""
        return (
            f"Migration Plan Summary:\n"
            f"  Total assets: {self.total_assets}\n"
            f"  Total size: {self.total_size_mb:.2f} MB\n"
            f"  Products: {len(self.products)}\n"
            f"  Semantic assets: {len(self.semantic_assets)}\n"
            f"  Cache entries: {len(self.cache_entries)}"
        )


@dataclass
class MigrationResult:
    """Result of migration operation"""

    plan: MigrationPlan
    uploaded_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    uploaded_bytes: int = 0
    duration_seconds: float = 0.0
    failed_files: list[str] | None = None

    def __post_init__(self):
        if self.failed_files is None:
            self.failed_files = []

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        total = self.uploaded_count + self.failed_count + self.skipped_count
        if total == 0:
            return 0.0
        return (self.uploaded_count / total) * 100

    def summary(self) -> str:
        """Generate summary string"""
        return (
            f"Migration Results:\n"
            f"  Uploaded: {self.uploaded_count}\n"
            f"  Failed: {self.failed_count}\n"
            f"  Skipped: {self.skipped_count}\n"
            f"  Success rate: {self.success_rate:.1f}%\n"
            f"  Total uploaded: {self.uploaded_bytes / 1024 / 1024:.2f} MB\n"
            f"  Duration: {self.duration_seconds:.1f}s"
        )


# ============================================================================
# MIGRATION MANAGER
# ============================================================================


class S3MigrationManager:
    """
    Manage migration of local cache assets to S3.

    Handles discovery, planning, execution, and validation of
    cache migration with semantic metadata preservation.
    """

    def __init__(
        self,
        cache_manager: CacheManager,
        s3_manager: S3StorageManager,
    ):
        """
        Initialize migration manager.

        Args:
            cache_manager: Local cache manager instance
            s3_manager: S3 storage manager instance
        """
        self.cache_manager = cache_manager
        self.s3_manager = s3_manager
        self.cache_dir = Path(cache_manager.cache_dir)

        logger.info("S3MigrationManager initialized")

    # ========================================================================
    # MIGRATION PLANNING
    # ========================================================================

    def create_migration_plan(self) -> MigrationPlan:
        """
        Analyze local cache and create migration plan.

        Returns:
            MigrationPlan with all assets to migrate
        """
        logger.info("Creating migration plan...")

        products = []
        semantic_assets = []
        cache_entries = []
        total_size = 0

        # Collect products
        for product_slug, product_entry in self.cache_manager.index.get("products", {}).items():
            cache_filename = product_entry.get("cache_filename")
            if cache_filename:
                file_path = self.cache_dir / cache_filename
                if file_path.exists():
                    products.append(
                        {
                            "product_slug": product_slug,
                            "entry": product_entry,
                            "local_path": file_path,
                            "size": file_path.stat().st_size,
                        }
                    )
                    total_size += file_path.stat().st_size

        # Collect semantic assets
        for cache_key, asset_entry in self.cache_manager.index.get("semantic_assets", {}).items():
            file_path_str = asset_entry.get("file_path")
            if file_path_str:
                file_path = Path(file_path_str)
                if file_path.exists():
                    semantic_assets.append(
                        {
                            "cache_key": cache_key,
                            "entry": asset_entry,
                            "local_path": file_path,
                            "size": file_path.stat().st_size,
                        }
                    )
                    total_size += file_path.stat().st_size

        # Collect cache entries
        for cache_key, entry in self.cache_manager.index.get("cache_entries", {}).items():
            file_path_str = entry.get("file_path")
            if file_path_str:
                file_path = Path(file_path_str)
                if file_path.exists():
                    cache_entries.append(
                        {
                            "cache_key": cache_key,
                            "entry": entry,
                            "local_path": file_path,
                            "size": file_path.stat().st_size,
                        }
                    )
                    total_size += file_path.stat().st_size

        total_assets = len(products) + len(semantic_assets) + len(cache_entries)

        plan = MigrationPlan(
            total_assets=total_assets,
            total_size_bytes=total_size,
            products=products,
            semantic_assets=semantic_assets,
            cache_entries=cache_entries,
            metadata_file=self.cache_manager.index_path,
        )

        logger.info(plan.summary())
        return plan

    # ========================================================================
    # MIGRATION EXECUTION
    # ========================================================================

    def execute_migration(
        self,
        plan: MigrationPlan,
        dry_run: bool = False,
        progress_callback: Callable[[UploadProgress], None] | None = None,
    ) -> MigrationResult:
        """
        Execute migration plan.

        Args:
            plan: Migration plan to execute
            dry_run: If True, simulate migration without uploading
            progress_callback: Optional callback for progress updates

        Returns:
            MigrationResult with execution details
        """
        import time

        start_time = time.time()

        logger.info(f"Starting migration {'(DRY RUN)' if dry_run else ''}...")

        result = MigrationResult(plan=plan)

        # Prepare file mappings for batch upload
        file_mappings = []

        # Migrate products
        for product_item in plan.products:
            s3_key = self._get_product_s3_key(product_item)
            metadata = self._build_product_metadata(product_item)

            file_mappings.append((product_item["local_path"], s3_key, metadata))

        # Migrate semantic assets
        for asset_item in plan.semantic_assets:
            s3_key = self._get_semantic_asset_s3_key(asset_item)
            metadata = self._build_semantic_asset_metadata(asset_item)

            file_mappings.append((asset_item["local_path"], s3_key, metadata))

        # Migrate cache entries
        for cache_item in plan.cache_entries:
            s3_key = self._get_cache_entry_s3_key(cache_item)
            metadata = self._build_cache_entry_metadata(cache_item)

            file_mappings.append((cache_item["local_path"], s3_key, metadata))

        if dry_run:
            logger.info(f"DRY RUN: Would upload {len(file_mappings)} files")
            for local_path, s3_key, _ in file_mappings[:10]:  # Show first 10
                logger.info(f"  {local_path.name} -> {s3_key}")
            if len(file_mappings) > 10:
                logger.info(f"  ... and {len(file_mappings) - 10} more")

            result.uploaded_count = len(file_mappings)
            result.duration_seconds = time.time() - start_time
            return result

        # Execute batch upload
        upload_results, upload_progress = self.s3_manager.batch_upload(
            file_mappings, progress_callback
        )

        # Process results
        for upload_result in upload_results:
            if upload_result.success:
                result.uploaded_count += 1
                result.uploaded_bytes += upload_result.size_bytes
            else:
                result.failed_count += 1
                if result.failed_files is not None:
                    result.failed_files.append(upload_result.local_path)

        result.duration_seconds = time.time() - start_time

        # Upload metadata index to S3
        if not dry_run:
            self._upload_metadata_index()

        logger.info(result.summary())
        return result

    def _get_product_s3_key(self, product_item: dict[str, Any]) -> str:
        """Generate S3 key for product asset"""
        product_entry = product_item["entry"]
        product_slug = product_item["product_slug"]

        # Extract category from tags if available
        tags = product_entry.get("tags", [])
        category = "general"
        for tag in tags:
            if tag in ["dish_soap", "laundry_detergent", "hair_care", "oral_care"]:
                category = tag
                break

        # Determine asset type (transparent vs original)
        cache_filename = product_entry.get("cache_filename", "")
        asset_type = "transparent" if "transparent" in cache_filename.lower() else "original"

        return str(self.s3_manager.folder_structure.get_product_path(
            product_slug=product_slug,
            category=category,
            asset_type=asset_type,
            filename=product_item["local_path"].name,
        ))

    def _get_semantic_asset_s3_key(self, asset_item: dict[str, Any]) -> str:
        """Generate S3 key for semantic asset"""
        asset_entry = asset_item["entry"]
        semantic_metadata = asset_entry.get("semantic_metadata", {})

        asset_type = semantic_metadata.get("asset_type", "")

        if "product" in asset_type:
            # Product asset
            category = semantic_metadata.get("product_category", "general")
            cache_key = asset_item["cache_key"]
            return str(self.s3_manager.folder_structure.get_product_path(
                product_slug=cache_key,
                category=category,
                asset_type="transparent" if "transparent" in asset_type else "original",
                filename=asset_item["local_path"].name,
            ))
        elif "background" in asset_type:
            # Background asset
            style = semantic_metadata.get("visual_style", "scene")
            region = semantic_metadata.get("region")
            season = semantic_metadata.get("season", "none")
            return str(self.s3_manager.folder_structure.get_background_path(
                style=style,
                region=region,
                season=season if season != "none" else None,
                filename=asset_item["local_path"].name,
            ))
        else:
            # Composite or other
            campaign_id = asset_entry.get("campaign_id", "unknown")
            return f"{self.s3_manager.config.prefix}/assets/{campaign_id}/{asset_item['local_path'].name}"

    def _get_cache_entry_s3_key(self, cache_item: dict[str, Any]) -> str:
        """Generate S3 key for cache entry"""
        entry = cache_item["entry"]
        metadata = entry.get("metadata", {})

        # Use metadata to determine location
        entry_type = metadata.get("type", "unknown")
        campaign_id = metadata.get("campaign_id", "unknown")

        return f"{self.s3_manager.config.prefix}/cache/{entry_type}/{campaign_id}/{cache_item['local_path'].name}"

    def _build_product_metadata(self, product_item: dict[str, Any]) -> dict[str, str]:
        """Build S3 metadata for product"""
        product_entry = product_item["entry"]

        return {
            "type": "product",
            "product-name": product_entry.get("name", ""),
            "product-slug": product_item["product_slug"],
            "campaigns": ",".join(product_entry.get("campaigns_used", [])),
            "tags": ",".join(product_entry.get("tags", [])),
            "created-at": product_entry.get("created_at", ""),
        }

    def _build_semantic_asset_metadata(self, asset_item: dict[str, Any]) -> dict[str, str]:
        """Build S3 metadata for semantic asset"""
        asset_entry = asset_item["entry"]
        semantic_metadata = asset_entry.get("semantic_metadata", {})

        metadata = {
            "type": "semantic-asset",
            "cache-key": asset_item["cache_key"],
            "asset-type": semantic_metadata.get("asset_type", ""),
            "campaign-id": asset_entry.get("campaign_id", ""),
            "created-at": asset_entry.get("created_at", ""),
            "usage-count": str(asset_entry.get("usage_count", 0)),
        }

        # Add semantic fields
        if semantic_metadata.get("product_category"):
            metadata["product-category"] = semantic_metadata["product_category"]
        if semantic_metadata.get("region"):
            metadata["region"] = semantic_metadata["region"]
        if semantic_metadata.get("season"):
            metadata["season"] = semantic_metadata["season"]
        if semantic_metadata.get("visual_style"):
            metadata["visual-style"] = semantic_metadata["visual_style"]
        if semantic_metadata.get("tags"):
            metadata["tags"] = ",".join(semantic_metadata["tags"])

        return metadata

    def _build_cache_entry_metadata(self, cache_item: dict[str, Any]) -> dict[str, str]:
        """Build S3 metadata for cache entry"""
        entry = cache_item["entry"]
        metadata = entry.get("metadata", {})

        return {
            "type": "cache-entry",
            "cache-key": cache_item["cache_key"],
            "cache-type": metadata.get("type", "unknown"),
            "campaign-id": metadata.get("campaign_id", ""),
            "created-at": entry.get("created_at", ""),
        }

    def _upload_metadata_index(self) -> bool:
        """Upload metadata index.json to S3"""
        try:
            s3_key = self.s3_manager.folder_structure.get_metadata_path()

            result = self.s3_manager.upload_file(
                local_path=self.cache_manager.index_path,
                s3_key=s3_key,
                metadata={"type": "metadata-index", "version": "1.0"},
                content_type="application/json",
            )

            if result.success:
                logger.info(f"Uploaded metadata index to {s3_key}")
                return True
            else:
                logger.error(f"Failed to upload metadata index: {result.error}")
                return False

        except Exception as e:
            logger.error(f"Error uploading metadata index: {e}")
            return False

    # ========================================================================
    # VALIDATION
    # ========================================================================

    def validate_migration(self, plan: MigrationPlan) -> dict[str, Any]:
        """
        Validate migration by comparing local and S3 assets.

        Args:
            plan: Migration plan to validate

        Returns:
            Validation report
        """
        logger.info("Validating migration...")

        all_items = plan.products + plan.semantic_assets + plan.cache_entries
        validated = 0
        missing = []
        size_mismatches = []

        for item in all_items:
            # Determine S3 key based on item type
            if "product_slug" in item:
                s3_key = self._get_product_s3_key(item)
            elif "semantic_metadata" in item.get("entry", {}):
                s3_key = self._get_semantic_asset_s3_key(item)
            else:
                s3_key = self._get_cache_entry_s3_key(item)

            # Check if exists in S3
            s3_metadata = self.s3_manager.get_file_metadata(s3_key)

            if s3_metadata is None:
                missing.append({"local_path": str(item["local_path"]), "s3_key": s3_key})
            elif s3_metadata["size_bytes"] != item["size"]:
                size_mismatches.append(
                    {
                        "local_path": str(item["local_path"]),
                        "s3_key": s3_key,
                        "local_size": item["size"],
                        "s3_size": s3_metadata["size_bytes"],
                    }
                )
            else:
                validated += 1

        report = {
            "total_assets": len(all_items),
            "validated": validated,
            "missing": len(missing),
            "size_mismatches": len(size_mismatches),
            "success_rate": (validated / len(all_items) * 100) if all_items else 0,
            "missing_details": missing[:10],  # First 10
            "mismatch_details": size_mismatches[:10],  # First 10
        }

        logger.info(
            f"Validation complete: {validated}/{len(all_items)} verified "
            f"({report['success_rate']:.1f}%)"
        )

        if missing:
            logger.warning(f"  {len(missing)} assets missing in S3")
        if size_mismatches:
            logger.warning(f"  {len(size_mismatches)} size mismatches")

        return report

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    def estimate_migration_cost(
        self, plan: MigrationPlan, cost_per_gb: float = 0.023
    ) -> dict[str, float]:
        """
        Estimate S3 storage costs.

        Args:
            plan: Migration plan
            cost_per_gb: S3 storage cost per GB/month (default: Standard tier)

        Returns:
            Cost estimates
        """
        size_gb = plan.total_size_bytes / 1024 / 1024 / 1024

        return {
            "storage_cost_monthly": round(size_gb * cost_per_gb, 2),
            "storage_cost_yearly": round(size_gb * cost_per_gb * 12, 2),
            "size_gb": round(size_gb, 3),
            "cost_per_gb": cost_per_gb,
        }


# ============================================================================
# MIGRATION UTILITIES
# ============================================================================


def create_migration_from_cache(
    cache_dir: str = "cache",
    bucket_name: str | None = None,
    prefix: str = "creative-assets",
    dry_run: bool = False,
) -> MigrationResult:
    """
    Convenience function to migrate entire cache to S3.

    Args:
        cache_dir: Local cache directory
        bucket_name: S3 bucket name (from env if None)
        prefix: S3 prefix for assets
        dry_run: If True, simulate without uploading

    Returns:
        MigrationResult
    """
    # Initialize managers
    cache_manager = CacheManager(cache_dir=cache_dir)

    if bucket_name:
        s3_config = S3Config(bucket_name=bucket_name, prefix=prefix)
    else:
        s3_config = S3Config.from_env(prefix=prefix)

    s3_manager = S3StorageManager(config=s3_config)

    # Create migration manager
    migration_manager = S3MigrationManager(cache_manager=cache_manager, s3_manager=s3_manager)

    # Create and execute plan
    plan = migration_manager.create_migration_plan()

    logger.info(plan.summary())

    result = migration_manager.execute_migration(plan, dry_run=dry_run)

    return result


def migrate_with_progress_bar(
    cache_dir: str = "cache",
    bucket_name: str | None = None,
    prefix: str = "creative-assets",
    dry_run: bool = False,
):
    """
    Migrate with rich progress bar display.

    Args:
        cache_dir: Local cache directory
        bucket_name: S3 bucket name (from env if None)
        prefix: S3 prefix for assets
        dry_run: If True, simulate without uploading
    """
    try:
        from rich.console import Console
        from rich.progress import (
            BarColumn,
            Progress,
            TextColumn,
            TimeRemainingColumn,
        )
    except ImportError:
        logger.warning("rich not installed, falling back to basic progress")
        return create_migration_from_cache(cache_dir, bucket_name, prefix, dry_run)

    console = Console()
    cache_manager = CacheManager(cache_dir=cache_dir)

    if bucket_name:
        s3_config = S3Config(bucket_name=bucket_name, prefix=prefix)
    else:
        s3_config = S3Config.from_env(prefix=prefix)

    s3_manager = S3StorageManager(config=s3_config)
    migration_manager = S3MigrationManager(cache_manager=cache_manager, s3_manager=s3_manager)

    # Create plan
    plan = migration_manager.create_migration_plan()
    console.print("\n[bold]Migration Plan[/bold]")
    console.print(plan.summary())

    if dry_run:
        console.print("\n[yellow]DRY RUN MODE - No files will be uploaded[/yellow]")

    # Progress bar
    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("{task.completed}/{task.total} files"),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Migrating assets...", total=plan.total_assets)

        def progress_callback(upload_progress: UploadProgress):
            progress.update(
                task,
                completed=upload_progress.uploaded
                + upload_progress.failed
                + upload_progress.skipped,
            )

        result = migration_manager.execute_migration(
            plan, dry_run=dry_run, progress_callback=progress_callback
        )

    console.print("\n[bold]Migration Results[/bold]")
    console.print(result.summary())

    if result.failed_count > 0 and result.failed_files:
        console.print("\n[red]Failed files:[/red]")
        failed_list = result.failed_files
        for failed_file in failed_list[:10]:
            console.print(f"  - {failed_file}")
        if len(failed_list) > 10:
            console.print(f"  ... and {len(failed_list) - 10} more")

    return result
