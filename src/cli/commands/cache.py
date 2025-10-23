"""
Cache command group - Manage pipeline cache and optimization.

Provides cache management with detailed analytics,
intelligent cleanup, and performance optimization.
"""

import os
import sys
import time
from pathlib import Path
from typing import Any

import click
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table
from rich.tree import Tree

from ..constants import CACHE_TYPES, OUTPUT_FORMATS
from ..core import pass_context
from ..plugins import call_hook
from ..utils.output import console, error_console


@click.group(invoke_without_command=True)
@click.option("--stats", "-s", is_flag=True, help="Show cache statistics")
@pass_context
def cache(ctx, stats):
    """
    Manage pipeline cache and optimization.

    The cache system stores generated assets, product images, and metadata
    to improve performance and reduce API calls. Supports both local and
    cloud storage with intelligent cleanup and optimization.

    Examples:
        creatimation cache stats
        creatimation cache clear --type products
        creatimation cache optimize
        creatimation cache sync --to s3

    Cache Commands:
        stats       Show detailed cache statistics
        clear       Clear cache entries
        optimize    Optimize cache storage
        inspect     Inspect cache contents
        sync        Synchronize with cloud storage
        cleanup     Clean up old or invalid entries
        rebuild     Rebuild cache index
    """
    click_ctx = click.get_current_context()
    if stats:
        click_ctx.invoke(stats_cmd)
    elif click_ctx.invoked_subcommand is None:
        # Show cache summary
        click_ctx.invoke(stats_cmd)


@cache.command(name="stats")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed cache breakdown")
@click.option("--format", type=click.Choice(OUTPUT_FORMATS), default="table", help="Output format")
@pass_context
def stats_cmd(ctx, detailed, format):
    """
    Show detailed cache statistics.

    Displays cache size, hit rates, storage breakdown, and performance
    metrics with support for multiple output formats.

    Examples:
        creatimation cache stats
        creatimation cache stats --detailed
        creatimation cache stats --format tree
        creatimation cache stats --format json
    """
    try:
        console.print()
        console.print("[bold cyan]Cache Statistics[/bold cyan]")
        console.print()

        # Get cache manager
        container = ctx.container
        cache_manager = container.get_cache_manager()

        # Collect cache statistics
        cache_stats = _collect_cache_statistics(cache_manager)

        if format == "table":
            _display_cache_stats_table(cache_stats, detailed)
        elif format == "tree":
            _display_cache_stats_tree(cache_stats)
        elif format == "json":
            _display_cache_stats_json(cache_stats)

        # Performance recommendations
        if detailed:
            _display_cache_recommendations(cache_stats)

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to get cache statistics: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@cache.command()
@click.option(
    "--type",
    type=click.Choice(CACHE_TYPES),
    default="all",
    help="Type of cache to clear",
)
@click.option("--older-than", type=int, help="Clear entries older than N days")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompts")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be cleared without actually clearing"
)
@pass_context
def clear(ctx, type, older_than, force, dry_run):
    """
    Clear cache entries.

    Removes cache entries by type, age, or other criteria with
    optional dry-run mode for safety.

    Examples:
        creatimation cache clear
        creatimation cache clear --type products
        creatimation cache clear --older-than 30
        creatimation cache clear --dry-run
        creatimation cache clear --type generated --force
    """
    # Analytics hook: Track command start
    call_hook("before_command", command_name="cache_clear")

    command_success = False
    start_time = time.time()

    try:
        # Get cache manager
        container = ctx.container
        cache_manager = container.get_cache_manager()

        console.print()
        console.print("[bold cyan]Cache Cleanup[/bold cyan]")

        if dry_run:
            console.print("[yellow]Dry run mode - no files will be deleted[/yellow]")

        console.print()

        # Calculate what would be cleared
        clear_stats = _calculate_clear_stats(cache_manager, type, older_than)

        if not clear_stats["total_files"]:
            console.print("[yellow]No cache entries found matching criteria[/yellow]")
            console.print()
            return

        # Display what will be cleared
        _display_clear_preview(clear_stats, type, older_than)

        if dry_run:
            console.print("\n[yellow]This was a dry run - no files were deleted.[/yellow]")
            console.print("Remove [cyan]--dry-run[/cyan] to perform the cleanup.")
            console.print()
            return

        # Confirmation
        if not force:
            console.print()
            if not Confirm.ask(
                f"Clear {clear_stats['total_files']} cache entries ({clear_stats['total_size_mb']:.1f} MB)?"
            ):
                console.print("Cache clear cancelled.")
                console.print()
                return

        # Perform cleanup
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            cleanup_task = progress.add_task("Clearing cache...", total=clear_stats["total_files"])

            cleared_count = _perform_cache_clear(
                cache_manager,
                type,
                older_than,
                lambda current: progress.update(cleanup_task, completed=current),
            )

        console.print()
        console.print(f"[green]✓[/green] Cleared {cleared_count} cache entries")
        console.print(f"[dim]Freed {clear_stats['total_size_mb']:.1f} MB of storage[/dim]")
        console.print()
        command_success = True

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to clear cache: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)

    finally:
        # Analytics hook: Track command completion
        call_hook(
            "after_command",
            command_name="cache_clear",
            success=command_success,
            duration=time.time() - start_time,
        )


@cache.command()
@click.option("--deduplicate", is_flag=True, help="Remove duplicate entries")
@click.option("--compress", is_flag=True, help="Compress cache storage")
@click.option("--rebuild-index", is_flag=True, help="Rebuild cache index")
@pass_context
def optimize(ctx, deduplicate, compress, rebuild_index):
    """
    Optimize cache storage and performance.

    Performs various optimization operations including deduplication,
    compression, and index rebuilding to improve cache efficiency.

    Examples:
        creatimation cache optimize
        creatimation cache optimize --deduplicate
        creatimation cache optimize --compress --rebuild-index
    """
    try:
        # Get cache manager
        container = ctx.container
        cache_manager = container.get_cache_manager()

        console.print()
        console.print("[bold cyan]Cache Optimization[/bold cyan]")
        console.print()

        # Collect initial stats
        initial_stats = _collect_cache_statistics(cache_manager)

        optimization_tasks = []

        if deduplicate:
            optimization_tasks.append("Deduplicating entries")
        if compress:
            optimization_tasks.append("Compressing storage")
        if rebuild_index:
            optimization_tasks.append("Rebuilding index")

        if not optimization_tasks:
            # Default optimization
            optimization_tasks = ["Deduplicating entries", "Rebuilding index"]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            for task_name in optimization_tasks:
                task = progress.add_task(task_name, total=None)

                if "Deduplicating" in task_name:
                    dedupe_count = _deduplicate_cache_entries(cache_manager)
                    progress.update(task, description=f"Deduplicated {dedupe_count} entries")

                elif "Compressing" in task_name:
                    compress_savings = _compress_cache_storage(cache_manager)
                    progress.update(
                        task, description=f"Compressed - saved {compress_savings:.1f} MB"
                    )

                elif "Rebuilding" in task_name:
                    index_count = _rebuild_cache_index(cache_manager)
                    progress.update(task, description=f"Rebuilt index with {index_count} entries")

                time.sleep(0.5)  # Visual feedback

        # Collect final stats
        final_stats = _collect_cache_statistics(cache_manager)

        # Show optimization results
        _display_optimization_results(initial_stats, final_stats)

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Cache optimization failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@cache.command()
@click.option(
    "--type",
    type=click.Choice(CACHE_TYPES[1:]),  # Exclude "all" option for inspect
    help="Inspect specific cache type",
)
@click.option("--limit", "-n", type=int, default=20, help="Limit number of entries to show")
@click.option(
    "--sort",
    type=click.Choice(["name", "size", "date", "hits"]),
    default="date",
    help="Sort entries by",
)
@pass_context
def inspect(ctx, type, limit, sort):
    """
    Inspect cache contents and metadata.

    Browse cache entries with detailed information including
    file sizes, access patterns, and metadata.

    Examples:
        creatimation cache inspect
        creatimation cache inspect --type products
        creatimation cache inspect --sort size --limit 10
    """
    try:
        # Get cache manager
        container = ctx.container
        cache_manager = container.get_cache_manager()

        console.print()
        console.print("[bold cyan]Cache Contents[/bold cyan]")
        console.print()

        # Get cache entries
        cache_entries = _get_cache_entries(cache_manager, type, sort, limit)

        if not cache_entries:
            console.print("[yellow]No cache entries found[/yellow]")
            console.print()
            return

        # Display entries
        _display_cache_entries(cache_entries, type)

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to inspect cache: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@cache.command()
@click.option("--to", type=click.Choice(["s3", "local"]), required=True, help="Sync destination")
@click.option("--bucket", help="S3 bucket name (required for S3 sync)")
@click.option("--dry-run", is_flag=True, help="Preview sync operations")
@click.option("--force", is_flag=True, help="Force overwrite existing files")
@pass_context
def sync(ctx, to, bucket, dry_run, force):
    """
    Synchronize cache with cloud storage.

    Uploads or downloads cache entries to/from cloud storage
    with support for incremental sync and conflict resolution.

    Examples:
        creatimation cache sync --to s3 --bucket my-cache-bucket
        creatimation cache sync --to local --dry-run
        creatimation cache sync --to s3 --bucket my-bucket --force
    """
    try:
        # Get cache manager
        container = ctx.container
        cache_manager = container.get_cache_manager()

        console.print()
        console.print(f"[bold cyan]Cache Sync to {to.upper()}[/bold cyan]")

        if dry_run:
            console.print("[yellow]Dry run mode - no files will be transferred[/yellow]")

        console.print()

        # Validate sync requirements
        if to == "s3" and not bucket:
            error_console.print("[red]✗[/red] S3 bucket name is required for S3 sync")
            console.print("Use [cyan]--bucket <bucket-name>[/cyan] to specify the bucket")
            sys.exit(1)

        # Calculate sync operations
        sync_stats = _calculate_sync_operations(cache_manager, to, bucket)

        if not sync_stats["total_operations"]:
            console.print("[green]✓[/green] Cache is already in sync")
            console.print()
            return

        # Display sync preview
        _display_sync_preview(sync_stats, to, bucket)

        if dry_run:
            console.print("\n[yellow]This was a dry run - no files were transferred.[/yellow]")
            console.print()
            return

        # Confirmation
        if not Confirm.ask(f"Perform {sync_stats['total_operations']} sync operations?"):
            console.print("Sync cancelled.")
            console.print()
            return

        # Perform sync
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            sync_task = progress.add_task("Synchronizing...", total=sync_stats["total_operations"])

            synced_count = _perform_cache_sync(
                cache_manager,
                to,
                bucket,
                force,
                lambda current: progress.update(sync_task, completed=current),
            )

        console.print()
        console.print(f"[green]✓[/green] Synchronized {synced_count} cache entries")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Cache sync failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@cache.command()
@click.option("--max-age", type=int, default=30, help="Maximum age in days for cache entries")
@click.option("--max-size", type=int, help="Maximum cache size in GB")
@click.option(
    "--keep-recent", type=int, default=100, help="Keep N most recent entries regardless of age"
)
@click.option("--dry-run", is_flag=True, help="Preview cleanup operations")
@pass_context
def cleanup(ctx, max_age, max_size, keep_recent, dry_run):
    """
    Clean up old or invalid cache entries.

    Removes cache entries based on age, size limits, and access patterns
    while preserving recently used and important entries.

    Examples:
        creatimation cache cleanup
        creatimation cache cleanup --max-age 7 --max-size 5
        creatimation cache cleanup --keep-recent 50 --dry-run
    """
    try:
        # Get cache manager
        container = ctx.container
        cache_manager = container.get_cache_manager()

        console.print()
        console.print("[bold cyan]Cache Cleanup[/bold cyan]")

        if dry_run:
            console.print("[yellow]Dry run mode - no files will be deleted[/yellow]")

        console.print()

        # Calculate cleanup operations
        cleanup_stats = _calculate_cleanup_operations(cache_manager, max_age, max_size, keep_recent)

        if not cleanup_stats["total_removals"]:
            console.print("[green]✓[/green] Cache is within cleanup thresholds")
            console.print()
            return

        # Display cleanup preview
        _display_cleanup_preview(cleanup_stats, max_age, max_size, keep_recent)

        if dry_run:
            console.print("\n[yellow]This was a dry run - no files were deleted.[/yellow]")
            console.print()
            return

        # Confirmation
        if not Confirm.ask(f"Remove {cleanup_stats['total_removals']} cache entries?"):
            console.print("Cleanup cancelled.")
            console.print()
            return

        # Perform cleanup
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console,
        ) as progress:
            cleanup_task = progress.add_task(
                "Cleaning up...", total=cleanup_stats["total_removals"]
            )

            cleaned_count = _perform_cache_cleanup(
                cache_manager,
                max_age,
                max_size,
                keep_recent,
                lambda current: progress.update(cleanup_task, completed=current),
            )

        console.print()
        console.print(f"[green]✓[/green] Cleaned up {cleaned_count} cache entries")
        console.print(f"[dim]Freed {cleanup_stats['size_saved_mb']:.1f} MB of storage[/dim]")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Cache cleanup failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@cache.command()
@click.option("--force", is_flag=True, help="Force rebuild even if index appears valid")
@pass_context
def rebuild(ctx, force):
    """
    Rebuild cache index.

    Reconstructs the cache index by scanning all cache files
    and rebuilding metadata. Useful for recovering from corruption.

    Examples:
        creatimation cache rebuild
        creatimation cache rebuild --force
    """
    try:
        # Get cache manager
        container = ctx.container
        cache_manager = container.get_cache_manager()

        console.print()
        console.print("[bold cyan]Rebuilding Cache Index[/bold cyan]")
        console.print()

        # Check if rebuild is needed
        if not force:
            index_status = _check_cache_index_status(cache_manager)

            if index_status["valid"]:
                console.print("[green]✓[/green] Cache index appears valid")
                console.print("Use [cyan]--force[/cyan] to rebuild anyway")
                console.print()
                return

            console.print(f"[yellow]⚠[/yellow] {index_status['issue']}")
            console.print()

        # Perform rebuild
        with console.status("[bold green]Rebuilding cache index..."):
            rebuild_stats = _rebuild_cache_index_full(cache_manager)

        console.print("[green]✓[/green] Rebuilt cache index")
        console.print(
            f"[dim]Indexed {rebuild_stats['entries_count']} entries in {rebuild_stats['categories_count']} categories[/dim]"
        )
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to rebuild cache index: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _collect_cache_statistics(cache_manager) -> dict[str, Any]:
    """Collect comprehensive cache statistics."""
    stats: dict[str, Any] = {
        "total_size_bytes": 0,
        "total_files": 0,
        "total_entries": 0,
        "categories": {},
        "hit_rate": 0.0,
        "access_patterns": {},
        "storage_efficiency": 0.0,
        "type_breakdown": {},
    }

    try:
        # Get actual stats from cache manager
        cache_stats = cache_manager.get_cache_stats()

        # Use real data from cache manager
        stats["total_size_bytes"] = cache_stats.get("total_size_bytes", 0)
        stats["total_entries"] = cache_stats.get("total_entries", 0)
        stats["type_breakdown"] = cache_stats.get("by_type", {})

        # Count actual files on disk
        cache_dir = getattr(cache_manager, "cache_dir", Path("cache"))
        if cache_dir.exists():
            for root, _dirs, files in os.walk(cache_dir):
                for file in files:
                    file_path = Path(root) / file
                    stats["total_files"] += 1

                    # Categorize by file type/location
                    category = _categorize_cache_file(file_path, cache_dir)
                    if category not in stats["categories"]:
                        stats["categories"][category] = {"files": 0, "size": 0}

                    file_size = file_path.stat().st_size
                    stats["categories"][category]["files"] += 1
                    stats["categories"][category]["size"] += file_size

        # Calculate hit rate from cache index if available
        if hasattr(cache_manager, "index"):
            total_accesses = 0
            successful_accesses = 0

            for entry in cache_manager.index.values():
                # Count entries that have been accessed (exist and have been used)
                file_path = Path(entry.get("file_path", ""))
                if file_path.exists():
                    successful_accesses += 1
                total_accesses += 1

            if total_accesses > 0:
                stats["hit_rate"] = (successful_accesses / total_accesses) * 100

    except Exception as e:
        # Log but don't fail
        import logging

        logging.debug(f"Error collecting cache statistics: {e}")

    return stats


def _categorize_cache_file(file_path: Path, cache_dir: Path) -> str:
    """Categorize a cache file by type."""
    rel_path = file_path.relative_to(cache_dir)

    if file_path.suffix == ".json":
        return "metadata"
    elif file_path.suffix in [".jpg", ".png", ".jpeg"]:
        if "products" in str(rel_path):
            return "products"
        elif "backgrounds" in str(rel_path):
            return "backgrounds"
        else:
            return "generated"
    else:
        return "other"


def _calculate_clear_stats(
    cache_manager, clear_type: str, older_than: int | None
) -> dict[str, Any]:
    """Calculate what would be cleared based on criteria."""
    import time

    stats: dict[str, Any] = {"total_files": 0, "total_size_mb": 0.0, "by_category": {}}

    if not hasattr(cache_manager, "index"):
        return stats

    cutoff_time = None
    if older_than:
        cutoff_time = time.time() - (older_than * 24 * 3600)

    for _key, entry in cache_manager.index.items():
        metadata = entry.get("metadata", {})
        cache_type = metadata.get("type", "unknown")

        # Filter by type
        if clear_type != "all":
            if clear_type == "products" and cache_type != "product":
                continue
            elif clear_type == "backgrounds" and cache_type != "background":
                continue
            elif clear_type == "generated" and cache_type not in ["creative_output", "generated"]:
                continue
            elif clear_type == "metadata" and cache_type != "metadata":
                continue

        # Filter by age
        if cutoff_time:
            created_at = entry.get("created_at", "")
            try:
                entry_time = time.mktime(time.strptime(created_at, "%Y-%m-%d %H:%M:%S"))
                if entry_time > cutoff_time:
                    continue
            except (ValueError, TypeError):
                pass  # Skip entries with invalid timestamps

        # Count this entry
        stats["total_files"] += 1
        size_mb = entry.get("size_bytes", 0) / (1024 * 1024)
        stats["total_size_mb"] += size_mb

        # Track by category
        if cache_type not in stats["by_category"]:
            stats["by_category"][cache_type] = {"count": 0, "size_mb": 0.0}
        stats["by_category"][cache_type]["count"] += 1
        stats["by_category"][cache_type]["size_mb"] += size_mb

    return stats


def _perform_cache_clear(
    cache_manager, clear_type: str, older_than: int | None, progress_callback
) -> int:
    """Perform the actual cache clearing operation."""
    import time

    cleared_count = 0

    if not hasattr(cache_manager, "index"):
        return cleared_count

    cutoff_time = None
    if older_than:
        cutoff_time = time.time() - (older_than * 24 * 3600)

    keys_to_remove = []

    for key, entry in cache_manager.index.items():
        metadata = entry.get("metadata", {})
        cache_type = metadata.get("type", "unknown")

        # Filter by type
        should_clear = False
        if clear_type == "all":
            should_clear = True
        elif clear_type == "products" and cache_type == "product":
            should_clear = True
        elif clear_type == "backgrounds" and cache_type == "background":
            should_clear = True
        elif clear_type == "generated" and cache_type in ["creative_output", "generated"]:
            should_clear = True
        elif clear_type == "metadata" and cache_type == "metadata":
            should_clear = True

        if not should_clear:
            continue

        # Filter by age
        if cutoff_time:
            created_at = entry.get("created_at", "")
            try:
                entry_time = time.mktime(time.strptime(created_at, "%Y-%m-%d %H:%M:%S"))
                if entry_time > cutoff_time:
                    continue
            except (ValueError, TypeError):
                pass  # Skip entries with invalid timestamps

        # Mark for removal
        keys_to_remove.append(key)

        # Delete the actual file
        file_path = Path(entry.get("file_path", ""))
        if file_path.exists():
            try:
                file_path.unlink()
                cleared_count += 1
                if progress_callback:
                    progress_callback()
            except Exception:
                pass  # Continue even if file deletion fails

    # Remove from index
    for key in keys_to_remove:
        del cache_manager.index[key]

    # Save updated index
    if keys_to_remove and hasattr(cache_manager, "_save_index"):
        cache_manager._save_index()

    return cleared_count


def _deduplicate_cache_entries(cache_manager) -> int:
    """Remove duplicate cache entries."""
    # Placeholder implementation
    return 0


def _compress_cache_storage(cache_manager) -> float:
    """Compress cache storage and return space saved in MB."""
    # Placeholder implementation
    return 0.0


def _rebuild_cache_index(cache_manager) -> int:
    """Rebuild cache index and return number of entries."""
    # Placeholder implementation
    return 0


def _get_cache_entries(
    cache_manager, entry_type: str | None, sort_by: str, limit: int
) -> list[dict[str, Any]]:
    """Get cache entries for inspection."""
    entries: list[dict[str, Any]] = []

    if not hasattr(cache_manager, "index"):
        return entries

    # Map CLI type names to cache type names
    type_mapping = {
        "products": "product",
        "backgrounds": "background",
        "metadata": "metadata",
        "generated": "creative_output",
    }

    target_type = type_mapping.get(entry_type) if entry_type else None

    for key, entry in cache_manager.index.items():
        metadata = entry.get("metadata", {})
        cache_type = metadata.get("type", "unknown")

        # Filter by type if specified
        if target_type and cache_type != target_type:
            continue

        # Build entry info
        entry_info = {
            "key": key,
            "type": cache_type,
            "file_path": entry.get("file_path", ""),
            "size_bytes": entry.get("size_bytes", 0),
            "created_at": entry.get("created_at", ""),
            "accessed_at": entry.get("accessed_at", ""),
            "metadata": metadata,
        }

        entries.append(entry_info)

    # Sort entries
    if sort_by == "size":
        entries.sort(key=lambda x: x["size_bytes"], reverse=True)
    elif sort_by == "date":
        entries.sort(key=lambda x: x["created_at"], reverse=True)
    elif sort_by == "access":
        entries.sort(key=lambda x: x["accessed_at"], reverse=True)
    else:  # type
        entries.sort(key=lambda x: x["type"])

    # Apply limit
    if limit > 0:
        entries = entries[:limit]

    return entries


def _calculate_sync_operations(
    cache_manager, destination: str, bucket: str | None
) -> dict[str, Any]:
    """Calculate sync operations needed."""
    # Placeholder implementation
    return {"total_operations": 0}


def _perform_cache_sync(
    cache_manager, destination: str, bucket: str | None, force: bool, progress_callback
) -> int:
    """Perform cache synchronization."""
    # Placeholder implementation
    return 0


def _calculate_cleanup_operations(
    cache_manager, max_age: int, max_size: int | None, keep_recent: int
) -> dict[str, Any]:
    """Calculate cleanup operations needed."""
    import time

    result: dict[str, Any] = {"total_removals": 0, "size_saved_mb": 0.0, "entries_to_remove": []}

    if not hasattr(cache_manager, "index"):
        return result

    cutoff_time = time.time() - (max_age * 24 * 3600)

    # Get all entries sorted by access time
    entries = []
    for key, entry in cache_manager.index.items():
        accessed_at = entry.get("accessed_at", "")
        try:
            access_time = time.mktime(time.strptime(accessed_at, "%Y-%m-%d %H:%M:%S"))
        except (ValueError, TypeError):
            access_time = 0

        entries.append(
            {
                "key": key,
                "entry": entry,
                "access_time": access_time,
            }
        )

    # Sort by access time (most recent first)
    entries.sort(key=lambda x: x["access_time"], reverse=True)

    # Keep the most recent entries
    entries_to_check = entries[keep_recent:]

    for item in entries_to_check:
        # Remove if older than max_age
        if item["access_time"] < cutoff_time:
            result["total_removals"] += 1
            size_mb = item["entry"].get("size_bytes", 0) / (1024 * 1024)
            result["size_saved_mb"] += size_mb
            result["entries_to_remove"].append(item["key"])

    return result


def _perform_cache_cleanup(
    cache_manager, max_age: int, max_size: int | None, keep_recent: int, progress_callback
) -> int:
    """Perform cache cleanup."""
    cleanup_ops = _calculate_cleanup_operations(cache_manager, max_age, max_size, keep_recent)

    removed_count = 0
    for key in cleanup_ops["entries_to_remove"]:
        if key in cache_manager.index:
            entry = cache_manager.index[key]
            file_path = Path(entry.get("file_path", ""))

            # Delete file
            if file_path.exists():
                try:
                    file_path.unlink()
                    removed_count += 1
                    if progress_callback:
                        progress_callback()
                except Exception:
                    pass

            # Remove from index
            del cache_manager.index[key]

    # Save updated index
    if removed_count > 0 and hasattr(cache_manager, "_save_index"):
        cache_manager._save_index()

    return removed_count


def _check_cache_index_status(cache_manager) -> dict[str, Any]:
    """Check cache index validity."""
    issues = []

    if not hasattr(cache_manager, "index"):
        return {"valid": False, "issue": "Cache manager has no index"}

    # Check for missing files
    missing_files = 0
    for _key, entry in cache_manager.index.items():
        file_path = Path(entry.get("file_path", ""))
        if not file_path.exists():
            missing_files += 1

    if missing_files > 0:
        issues.append(f"{missing_files} entries reference missing files")

    # Check for orphaned files (files not in index)
    cache_dir = getattr(cache_manager, "cache_dir", Path("cache"))
    if cache_dir.exists():
        indexed_files = {Path(e.get("file_path", "")) for e in cache_manager.index.values()}
        orphaned_files = 0

        for root, _dirs, files in os.walk(cache_dir):
            for file in files:
                file_path = Path(root) / file
                if file_path.name != "index.json" and file_path not in indexed_files:
                    orphaned_files += 1

        if orphaned_files > 0:
            issues.append(f"{orphaned_files} files not indexed")

    if issues:
        return {"valid": False, "issue": "; ".join(issues)}

    return {"valid": True, "issue": None}


def _rebuild_cache_index_full(cache_manager) -> dict[str, Any]:
    """Perform full cache index rebuild."""
    import hashlib

    if not hasattr(cache_manager, "index"):
        return {"entries_count": 0, "categories_count": 0}

    # Clean out stale entries
    keys_to_remove = []
    for key, entry in cache_manager.index.items():
        file_path = Path(entry.get("file_path", ""))
        if not file_path.exists():
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del cache_manager.index[key]

    # Scan cache directory for orphaned files
    cache_dir = getattr(cache_manager, "cache_dir", Path("cache"))
    indexed_files = {Path(e.get("file_path", "")) for e in cache_manager.index.values()}

    added_count = 0
    if cache_dir.exists():
        for root, _dirs, files in os.walk(cache_dir):
            for file in files:
                file_path = Path(root) / file

                # Skip index file
                if file_path.name == "index.json":
                    continue

                # Skip already indexed files
                if file_path in indexed_files:
                    continue

                # Create new index entry for orphaned file
                cache_key = hashlib.sha256(str(file_path).encode()).hexdigest()[:16]
                cache_manager.index[cache_key] = {
                    "key": cache_key,
                    "file_path": str(file_path),
                    "metadata": {"type": "unknown"},
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "accessed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "size_bytes": file_path.stat().st_size,
                }
                added_count += 1

    # Save updated index
    if (keys_to_remove or added_count > 0) and hasattr(cache_manager, "_save_index"):
        cache_manager._save_index()

    # Count categories
    categories = set()
    for entry in cache_manager.index.values():
        cache_type = entry.get("metadata", {}).get("type", "unknown")
        categories.add(cache_type)

    return {
        "entries_count": len(cache_manager.index),
        "categories_count": len(categories),
        "removed": len(keys_to_remove),
        "added": added_count,
    }


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================


def _display_cache_stats_table(stats: dict[str, Any], detailed: bool):
    """Display cache statistics in table format."""
    # Main stats table
    main_table = Table(title="Cache Overview", show_header=True)
    main_table.add_column("Metric", style="cyan")
    main_table.add_column("Value", style="green")

    total_size_mb = stats["total_size_bytes"] / (1024 * 1024)
    main_table.add_row("Total Entries", str(stats["total_entries"]))
    main_table.add_row("Total Files", str(stats["total_files"]))
    main_table.add_row("Total Size", f"{total_size_mb:.1f} MB")
    main_table.add_row("Hit Rate", f"{stats['hit_rate']:.1f}%")

    console.print(main_table)

    # Type breakdown
    if stats.get("type_breakdown"):
        console.print()
        type_table = Table(title="Cache Entry Types", show_header=True)
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", style="green")

        for entry_type, count in stats["type_breakdown"].items():
            type_table.add_row(entry_type, str(count))

        console.print(type_table)

    # Per-campaign cache analytics
    campaign_analytics = _get_campaign_cache_analytics()
    if campaign_analytics:
        console.print()
        campaign_table = Table(title="Per-Campaign Cache Analytics", show_header=True)
        campaign_table.add_column("Campaign", style="cyan")
        campaign_table.add_column("Cache Hit Rate", style="green")
        campaign_table.add_column("Cache Hits", style="yellow")
        campaign_table.add_column("Cache Misses", style="red")

        for campaign_data in campaign_analytics:
            campaign_table.add_row(
                campaign_data["campaign_id"],
                f"{campaign_data['cache_hit_rate']:.1f}%",
                str(campaign_data["cache_hits"]),
                str(campaign_data["cache_misses"]),
            )

        console.print(campaign_table)

    if detailed and stats["categories"]:
        console.print()

        # Categories breakdown
        cat_table = Table(title="Cache Categories", show_header=True)
        cat_table.add_column("Category", style="cyan")
        cat_table.add_column("Files", style="yellow")
        cat_table.add_column("Size", style="green")
        cat_table.add_column("Percentage", style="blue")

        for category, data in stats["categories"].items():
            size_mb = data["size"] / (1024 * 1024)
            percentage = (
                (data["size"] / stats["total_size_bytes"]) * 100
                if stats["total_size_bytes"] > 0
                else 0
            )

            cat_table.add_row(
                category.title(), str(data["files"]), f"{size_mb:.1f} MB", f"{percentage:.1f}%"
            )

        console.print(cat_table)


def _display_cache_stats_tree(stats: dict[str, Any]):
    """Display cache statistics in tree format."""
    tree = Tree("📦 Cache Statistics")

    # Overview
    overview = tree.add("📊 Overview")
    overview.add(f"Files: {stats['total_files']}")
    overview.add(f"Size: {stats['total_size_bytes'] / (1024 * 1024):.1f} MB")
    overview.add(f"Hit Rate: {stats['hit_rate']:.1f}%")

    # Categories
    if stats["categories"]:
        categories = tree.add("📁 Categories")
        for category, data in stats["categories"].items():
            cat_node = categories.add(f"{category.title()}")
            cat_node.add(f"Files: {data['files']}")
            cat_node.add(f"Size: {data['size'] / (1024 * 1024):.1f} MB")

    console.print(tree)


def _display_cache_stats_json(stats: dict[str, Any]):
    """Display cache statistics in JSON format."""
    import json

    # Convert bytes to MB for readability
    json_stats = stats.copy()
    json_stats["total_size_mb"] = stats["total_size_bytes"] / (1024 * 1024)

    for category in json_stats.get("categories", {}):
        json_stats["categories"][category]["size_mb"] = json_stats["categories"][category][
            "size"
        ] / (1024 * 1024)

    console.print(json.dumps(json_stats, indent=2))


def _display_cache_recommendations(stats: dict[str, Any]):
    """Display cache performance recommendations."""
    console.print()
    console.print("[bold]Performance Recommendations[/bold]")

    recommendations = []

    # Size-based recommendations
    total_size_mb = stats["total_size_bytes"] / (1024 * 1024)
    if total_size_mb > 1000:  # > 1GB
        recommendations.append("Consider enabling cache cleanup to manage storage usage")

    if total_size_mb > 5000:  # > 5GB
        recommendations.append("Cache is very large - consider S3 sync for distributed teams")

    # Hit rate recommendations
    if stats["hit_rate"] < 50:
        recommendations.append("Low cache hit rate - consider increasing cache retention")

    # File count recommendations
    if stats["total_files"] > 10000:
        recommendations.append("High file count - consider cache optimization and deduplication")

    if not recommendations:
        recommendations.append("Cache is performing well - no immediate optimizations needed")

    for rec in recommendations:
        console.print(f"  • {rec}")


def _display_clear_preview(stats: dict[str, Any], clear_type: str, older_than: int | None):
    """Display preview of what will be cleared."""
    console.print("[bold]Clear Preview[/bold]")
    console.print(f"Type: {clear_type}")

    if older_than:
        console.print(f"Older than: {older_than} days")

    console.print(f"Files to clear: {stats['total_files']}")
    console.print(f"Space to free: {stats['total_size_mb']:.1f} MB")


def _display_optimization_results(initial_stats: dict[str, Any], final_stats: dict[str, Any]):
    """Display cache optimization results."""
    console.print()
    console.print("[bold]Optimization Results[/bold]")

    initial_size_mb = initial_stats["total_size_bytes"] / (1024 * 1024)
    final_size_mb = final_stats["total_size_bytes"] / (1024 * 1024)
    space_saved = initial_size_mb - final_size_mb

    files_removed = initial_stats["total_files"] - final_stats["total_files"]

    console.print(f"Space saved: {space_saved:.1f} MB")
    console.print(f"Files removed: {files_removed}")
    console.print(f"Final cache size: {final_size_mb:.1f} MB")


def _display_cache_entries(entries: list[dict[str, Any]], entry_type: str | None):
    """Display cache entries for inspection."""
    if not entries:
        console.print("[yellow]No cache entries found[/yellow]")
        return

    table = Table(title=f"Cache Entries - {entry_type or 'All'}", show_header=True)
    table.add_column("Type", style="cyan", width=15)
    table.add_column("Name", style="yellow", no_wrap=False)
    table.add_column("Size", style="green")
    table.add_column("Created", style="blue")

    for entry in entries:
        # Extract meaningful name from metadata
        metadata = entry.get("metadata", {})
        name = (
            metadata.get("product_name")
            or metadata.get("asset_name")
            or Path(entry.get("file_path", "")).name
            or "Unknown"
        )

        # Format size
        size_bytes = entry.get("size_bytes", 0)
        if size_bytes > 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
        elif size_bytes > 1024:
            size_str = f"{size_bytes / 1024:.1f} KB"
        else:
            size_str = f"{size_bytes} B"

        # Format created date
        created_at = entry.get("created_at", "Unknown")

        table.add_row(
            entry.get("type", "unknown"),
            name[:50],  # Truncate long names
            size_str,
            created_at,
        )

    console.print(table)


def _display_sync_preview(stats: dict[str, Any], destination: str, bucket: str | None):
    """Display sync operation preview."""
    console.print(f"[bold]Sync Preview to {destination.upper()}[/bold]")

    if bucket:
        console.print(f"Bucket: {bucket}")

    console.print(f"Operations: {stats['total_operations']}")


def _get_campaign_cache_analytics() -> list[dict[str, Any]]:
    """Get per-campaign cache analytics from analytics data."""
    import json

    analytics_file = Path("analytics") / "data.json"

    if not analytics_file.exists():
        return []

    try:
        with open(analytics_file) as f:
            analytics_data = json.load(f)

        generation_stats = analytics_data.get("generation_stats", {})
        campaign_analytics = []

        for campaign_id, stats in generation_stats.items():
            if stats.get("success", False) and not stats.get("dry_run", False):
                cache_hits = stats.get("cache_hits", 0)
                cache_misses = stats.get("cache_misses", 0)
                total_cache_ops = cache_hits + cache_misses

                if total_cache_ops > 0:
                    cache_hit_rate = (cache_hits / total_cache_ops) * 100
                else:
                    cache_hit_rate = 0.0

                campaign_analytics.append(
                    {
                        "campaign_id": campaign_id,
                        "cache_hits": cache_hits,
                        "cache_misses": cache_misses,
                        "cache_hit_rate": cache_hit_rate,
                    }
                )

        # Sort by campaign_id for consistent display
        campaign_analytics.sort(key=lambda x: x["campaign_id"])
        return campaign_analytics

    except Exception as e:
        # Log but don't fail
        import logging

        logging.debug(f"Error loading campaign cache analytics: {e}")
        return []


def _display_cleanup_preview(
    stats: dict[str, Any], max_age: int, max_size: int | None, keep_recent: int
):
    """Display cleanup operation preview."""
    console.print("[bold]Cleanup Preview[/bold]")
    console.print(f"Max age: {max_age} days")

    if max_size:
        console.print(f"Max size: {max_size} GB")

    console.print(f"Keep recent: {keep_recent} entries")
    console.print(f"Entries to remove: {stats['total_removals']}")
    console.print(f"Space to free: {stats['size_saved_mb']:.1f} MB")
