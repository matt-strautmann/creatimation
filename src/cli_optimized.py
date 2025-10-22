#!/usr/bin/env python3
"""
Optimized Creative Automation Pipeline CLI.

This module provides a clean, well-structured CLI interface using
dependency injection and proper separation of concerns.

Usage:
    creatimation generate --brief campaign.json
    creatimation validate brief campaign.json
    creatimation cache stats
    creatimation config init
"""

import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from .config import ConfigManager

# Import the new architecture
from .container import configure_container, get_container

console = Console()


class CLIContext:
    """CLI context for sharing state between commands."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.container = get_container()


# ============================================================================
# MAIN CLI GROUP
# ============================================================================


@click.group()
@click.version_option(version="2.0.0", prog_name="creatimation")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to .creatimation.yml config file",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def cli(ctx, config, verbose):
    """
    Creative Automation Pipeline v2.0 - Generate professional social ad creatives at scale.

    Optimized architecture with dependency injection and SOLID principles.
    """
    # Initialize CLI context
    ctx.obj = CLIContext()

    # Load configuration if provided
    if config:
        try:
            config_data = ctx.obj.config_manager.load_config(config)
            configure_container(config_data)
            ctx.obj.container = get_container()
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            sys.exit(1)

    # Configure logging
    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)


# ============================================================================
# GENERATE COMMANDS
# ============================================================================


@cli.group()
def generate():
    """Generate creative assets from campaign briefs."""
    pass


@generate.command("all")
@click.option(
    "--brief",
    "-b",
    required=True,
    type=click.Path(exists=True),
    help="Path to campaign brief JSON file",
)
@click.option(
    "--brand-guide", "-g", type=click.Path(exists=True), help="Path to brand guide YAML file"
)
@click.option("--output", "-o", type=click.Path(), help="Output directory (overrides config)")
@click.option("--no-cache", is_flag=True, help="Disable cache usage")
@click.option("--resume", is_flag=True, help="Resume from previous execution")
@click.option("--dry-run", is_flag=True, help="Preview execution without generating assets")
@click.pass_context
def generate_all(ctx, brief, brand_guide, output, no_cache, resume, dry_run):
    """Generate all variants for a campaign."""
    try:
        # Get container and create pipeline
        container = ctx.obj.container

        # Override output directory if provided
        if output:
            config = {"output": {"directory": output}}
            container = get_container(config)

        # Extract campaign ID from brief for state tracking
        import json

        with open(brief) as f:
            brief_data = json.load(f)
        campaign_id = brief_data.get("campaign_id", Path(brief).stem)

        # Create pipeline
        pipeline = container.get_pipeline(
            campaign_id=campaign_id, no_cache=no_cache, dry_run=dry_run
        )

        # Execute pipeline
        console.print("\n[bold blue]Starting Creative Automation Pipeline v2.0[/bold blue]")
        console.print(f"Brief: {brief}")
        console.print("Config: optimized architecture")
        if brand_guide:
            console.print(f"Brand Guide: {brand_guide}")

        with console.status("[bold green]Processing campaign..."):
            results = pipeline.process_campaign(
                brief_path=brief, brand_guide_path=brand_guide, resume=resume
            )

        # Display results
        _display_results(results)

    except Exception as e:
        console.print(f"\n[red]❌ Pipeline failed: {e}[/red]")
        if ctx.obj.config_manager.config.get("debug", False):
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


# ============================================================================
# VALIDATION COMMANDS
# ============================================================================


@cli.group()
def validate():
    """Validate campaign briefs and brand guides."""
    pass


@validate.command("brief")
@click.argument("brief_path", type=click.Path(exists=True))
@click.pass_context
def validate_brief(ctx, brief_path):
    """Validate a campaign brief JSON file."""
    try:
        container = ctx.obj.container
        brief_loader = container.get_brief_loader()

        console.print(f"\n[bold]Validating brief:[/bold] {brief_path}")

        # Load and validate brief
        brief_data = brief_loader.load_brief(brief_path)
        is_valid = brief_loader.validate_brief(brief_data)

        if is_valid:
            console.print("[green]✓ Brief is valid[/green]")

            # Display brief summary
            table = Table(title="Brief Summary")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Campaign ID", brief_data.get("campaign_id", "N/A"))
            table.add_row("Products", str(len(brief_data.get("products", []))))
            table.add_row(
                "Target Regions",
                str(brief_data.get("target_regions", brief_data.get("target_region", "N/A"))),
            )

            creative_reqs = brief_data.get("creative_requirements", {})
            table.add_row("Aspect Ratios", str(len(creative_reqs.get("aspect_ratios", []))))
            table.add_row("Variant Types", str(len(creative_reqs.get("variant_types", []))))

            console.print(table)
        else:
            console.print("[red]❌ Brief validation failed[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error validating brief: {e}[/red]")
        sys.exit(1)


@validate.command("brand-guide")
@click.argument("guide_path", type=click.Path(exists=True))
@click.pass_context
def validate_brand_guide(ctx, guide_path):
    """Validate a brand guide YAML file."""
    try:
        container = ctx.obj.container
        brand_guide_loader = container.get_brand_guide_loader()

        console.print(f"\n[bold]Validating brand guide:[/bold] {guide_path}")

        # Load and validate brand guide
        guide_data = brand_guide_loader.load_brand_guide(guide_path)
        is_valid = brand_guide_loader.validate_brand_guide(guide_data)

        if is_valid:
            console.print("[green]✓ Brand guide is valid[/green]")

            # Display brand guide summary
            table = Table(title="Brand Guide Summary")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Brand Name", guide_data.get("brand_name", "N/A"))
            table.add_row("Industry", guide_data.get("industry", "N/A"))

            colors = guide_data.get("colors", {})
            table.add_row("Primary Color", colors.get("primary", "N/A"))
            table.add_row("Secondary Color", colors.get("secondary", "N/A"))
            table.add_row("Accent Color", colors.get("accent", "N/A"))

            console.print(table)
        else:
            console.print("[red]❌ Brand guide validation failed[/red]")
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]Error validating brand guide: {e}[/red]")
        sys.exit(1)


# ============================================================================
# CACHE COMMANDS
# ============================================================================


@cli.group()
def cache():
    """Manage the asset cache."""
    pass


@cache.command("clear")
@click.option("--force", is_flag=True, help="Force clear without confirmation")
@click.pass_context
def clear_cache(ctx, force):
    """Clear all cached assets."""
    if not force:
        if not click.confirm("Are you sure you want to clear all cached assets?"):
            console.print("Cache clear cancelled.")
            return

    try:
        container = ctx.obj.container
        cache_manager = container.get_cache_manager()

        cache_manager.clear()
        console.print("[green]✓ Cache cleared successfully[/green]")

    except Exception as e:
        console.print(f"[red]Error clearing cache: {e}[/red]")
        sys.exit(1)


@cache.command("stats")
@click.pass_context
def cache_stats(ctx):
    """Show cache statistics."""
    try:
        container = ctx.obj.container
        cache_manager = container.get_cache_manager()

        stats = cache_manager.get_stats()

        # Display cache statistics
        table = Table(title="Cache Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Total Entries", str(stats["total_entries"]))
        table.add_row("Total Size", f"{stats['total_size_mb']} MB")
        table.add_row("Cache Directory", stats["cache_directory"])
        table.add_row("S3 Enabled", str(stats["s3_enabled"]))

        # Add type breakdown
        for asset_type, count in stats.get("type_breakdown", {}).items():
            table.add_row(f"  {asset_type}", str(count))

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error getting cache stats: {e}[/red]")
        sys.exit(1)


@cache.command("cleanup")
@click.option("--max-age", default=30, help="Maximum age in days for cached assets")
@click.pass_context
def cleanup_cache(ctx, max_age):
    """Clean up stale cache entries."""
    try:
        container = ctx.obj.container
        cache_manager = container.get_cache_manager()

        removed_count = cache_manager.cleanup_stale_entries(max_age_days=max_age)
        console.print(f"[green]✓ Removed {removed_count} stale cache entries[/green]")

    except Exception as e:
        console.print(f"[red]Error cleaning cache: {e}[/red]")
        sys.exit(1)


# ============================================================================
# CONFIG COMMANDS
# ============================================================================


@cli.group()
def config():
    """Manage configuration."""
    pass


@config.command("init")
@click.option(
    "--output", type=click.Path(), default=".creatimation.yml", help="Output file for configuration"
)
@click.pass_context
def init_config(ctx, output):
    """Initialize a new configuration file."""
    try:
        config_path = Path(output)
        if config_path.exists():
            if not click.confirm(f"Config file {output} already exists. Overwrite?"):
                console.print("Configuration init cancelled.")
                return

        # Create default configuration
        default_config = {
            "cache": {"directory": "cache", "enable_s3": False},
            "output": {"directory": "output", "semantic_structure": True},
            "generation": {"default_aspect_ratios": ["1x1", "9x16", "16x9"], "quality": 95},
        }

        import yaml

        with open(config_path, "w") as f:
            yaml.dump(default_config, f, indent=2)

        console.print(f"[green]✓ Configuration created: {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error creating config: {e}[/red]")
        sys.exit(1)


@config.command("show")
@click.pass_context
def show_config(ctx):
    """Show current configuration."""
    try:
        config_data = ctx.obj.config_manager.config

        console.print("\n[bold]Current Configuration:[/bold]")
        console.print_json(data=config_data)

    except Exception as e:
        console.print(f"[red]Error showing config: {e}[/red]")
        sys.exit(1)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def _display_results(results: dict[str, Any]) -> None:
    """Display pipeline execution results."""
    console.print("\n[bold green]✨ Pipeline Completed Successfully![/bold green]")

    # Results table
    table = Table(title="Execution Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Campaign ID", results.get("campaign_id", "N/A"))
    table.add_row("Products Processed", str(len(results.get("products_processed", []))))
    table.add_row("Total Creatives", str(results.get("total_creatives", 0)))
    table.add_row("Cache Hits", str(results.get("cache_hits", 0)))
    table.add_row("Cache Misses", str(results.get("cache_misses", 0)))

    processing_time = results.get("processing_time", 0)
    table.add_row("Processing Time", f"{processing_time:.1f} seconds")

    if processing_time > 0 and results.get("total_creatives", 0) > 0:
        rate = results["total_creatives"] / processing_time
        table.add_row("Generation Rate", f"{rate:.2f} creatives/second")

    console.print(table)

    # Show target regions
    regions = results.get("target_regions", [])
    if regions:
        console.print(f"\n[bold]Target Regions:[/bold] {', '.join(regions)}")

    # Show dry run info
    if results.get("dry_run"):
        console.print("\n[yellow]ℹ️  This was a dry run - no assets were generated[/yellow]")


def main():
    """CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
