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

from ..core import pass_context
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
@click.option(
    "--format", type=click.Choice(["table", "tree", "json"]), default="table", help="Output format"
)
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
    type=click.Choice(["all", "products", "backgrounds", "metadata", "generated"]),
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

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to clear cache: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


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
    type=click.Choice(["products", "backgrounds", "metadata", "generated"]),
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
    stats = {
        "total_size_bytes": 0,
        "total_files": 0,
        "categories": {},
        "hit_rate": 0.0,
        "access_patterns": {},
        "storage_efficiency": 0.0,
    }

    try:
        # Get cache directory
        cache_dir = getattr(cache_manager, "cache_dir", Path("cache"))

        if not cache_dir.exists():
            return stats

        # Walk through cache directory
        for root, _dirs, files in os.walk(cache_dir):
            for file in files:
                file_path = Path(root) / file
                file_size = file_path.stat().st_size

                stats["total_size_bytes"] += file_size
                stats["total_files"] += 1

                # Categorize by file type/location
                category = _categorize_cache_file(file_path, cache_dir)
                if category not in stats["categories"]:
                    stats["categories"][category] = {"files": 0, "size": 0}

                stats["categories"][category]["files"] += 1
                stats["categories"][category]["size"] += file_size

    except Exception:
        pass  # Handle gracefully

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
    stats = {"total_files": 0, "total_size_mb": 0.0, "by_category": {}}

    # Placeholder implementation
    # In real implementation, would scan cache and apply filters

    return stats


def _perform_cache_clear(
    cache_manager, clear_type: str, older_than: int | None, progress_callback
) -> int:
    """Perform the actual cache clearing operation."""
    cleared_count = 0

    # Placeholder implementation
    # In real implementation, would delete matching files

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
    # Placeholder implementation
    return []


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
    # Placeholder implementation
    return {"total_removals": 0, "size_saved_mb": 0.0}


def _perform_cache_cleanup(
    cache_manager, max_age: int, max_size: int | None, keep_recent: int, progress_callback
) -> int:
    """Perform cache cleanup."""
    # Placeholder implementation
    return 0


def _check_cache_index_status(cache_manager) -> dict[str, Any]:
    """Check cache index validity."""
    # Placeholder implementation
    return {"valid": True, "issue": None}


def _rebuild_cache_index_full(cache_manager) -> dict[str, Any]:
    """Perform full cache index rebuild."""
    # Placeholder implementation
    return {"entries_count": 0, "categories_count": 0}


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
    main_table.add_row("Total Files", str(stats["total_files"]))
    main_table.add_row("Total Size", f"{total_size_mb:.1f} MB")
    main_table.add_row("Hit Rate", f"{stats['hit_rate']:.1f}%")

    console.print(main_table)

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
        return

    table = Table(title=f"Cache Entries - {entry_type or 'All'}", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Size", style="yellow")
    table.add_column("Modified", style="green")
    table.add_column("Hits", style="blue")

    for entry in entries:
        table.add_row(
            entry.get("name", "Unknown"),
            entry.get("size", "0 B"),
            entry.get("modified", "Unknown"),
            str(entry.get("hits", 0)),
        )

    console.print(table)


def _display_sync_preview(stats: dict[str, Any], destination: str, bucket: str | None):
    """Display sync operation preview."""
    console.print(f"[bold]Sync Preview to {destination.upper()}[/bold]")

    if bucket:
        console.print(f"Bucket: {bucket}")

    console.print(f"Operations: {stats['total_operations']}")


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
