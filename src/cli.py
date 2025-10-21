#!/usr/bin/env python3
"""
Creative Automation Pipeline CLI

Professional CLI with subcommands, config file support, and rich output.
Built with Click framework for excellent UX.

Usage:
    creatimation generate --brief campaign.json
    creatimation validate brief campaign.json
    creatimation cache stats
    creatimation config init
"""
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Import pipeline components
from .config import ConfigManager, CreatimationConfig
from .brand_guide_loader import BrandGuideLoader


console = Console()


# ============================================================================
# GLOBAL OPTIONS
# ============================================================================


@click.group()
@click.version_option(version="1.0.0", prog_name="creatimation")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to .creatimation.yml config file",
)
@click.pass_context
def cli(ctx, config):
    """
    Creative Automation Pipeline - Generate professional social ad creatives at scale.

    Use subcommands to generate creatives, validate inputs, manage cache, and more.

    Examples:
        creatimation generate --brief campaign.json
        creatimation validate brief campaign.json
        creatimation cache stats
        creatimation config init
    """
    # Store config path in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


# ============================================================================
# GENERATE COMMAND GROUP
# ============================================================================


@cli.group()
def generate():
    """Generate creative assets (full pipeline or individual stages)."""
    pass


@generate.command(name="all")
@click.option("--brief", "-b", required=True, type=click.Path(exists=True), help="Campaign brief JSON file")
@click.option("--output", "-o", type=click.Path(), help="Output directory (overrides config)")
@click.option("--variants", "-n", type=int, help="Variants per ratio (overrides config)")
@click.option("--ratios", "-r", help="Comma-separated aspect ratios (e.g., 1x1,9x16,16x9)")
@click.option("--brand-guide", "-g", type=click.Path(exists=True), help="Brand guide YAML file")
@click.option("--no-cache", is_flag=True, help="Disable cache, regenerate everything")
@click.option("--resume", is_flag=True, help="Resume from saved pipeline state")
@click.option("--dry-run", is_flag=True, help="Preview without execution")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.pass_context
def generate_all(ctx, brief, output, variants, ratios, brand_guide, no_cache, resume, dry_run, verbose):
    """
    Generate all creative assets (full pipeline).

    This runs the complete pipeline: product generation → scene backgrounds →
    compositing → text overlay → output management.

    Examples:
        # Basic usage with defaults from .creatimation.yml
        creatimation generate all --brief campaign.json

        # Override config with CLI flags
        creatimation generate all --brief campaign.json --variants 5 --ratios 1x1,16x9

        # Use brand guide
        creatimation generate all --brief campaign.json --brand-guide brand-guides/minimal_blue.yml

        # Dry run to preview
        creatimation generate all --brief campaign.json --dry-run
    """
    # Build CLI overrides
    cli_overrides = _build_cli_overrides(output, variants, ratios, brand_guide)

    # Load configuration with precedence chain
    config_manager = ConfigManager(ctx.obj.get("config_path"))
    config = config_manager.load(cli_overrides)

    # Import and run pipeline
    from .main import CreativePipeline

    try:
        console.print(f"\n[bold cyan]Starting Creative Automation Pipeline[/bold cyan]")
        console.print(f"Brief: {brief}")
        console.print(f"Config: {config.project.name}")

        if brand_guide:
            console.print(f"Brand Guide: {brand_guide}")

        console.print()

        # Initialize pipeline
        pipeline = CreativePipeline(no_cache=no_cache, dry_run=dry_run)

        # Apply brand guide if specified
        enhanced_brief = brief
        if brand_guide:
            from .brand_guide_loader import apply_brand_guide
            import json

            with open(brief) as f:
                brief_dict = json.load(f)

            enhanced_brief_dict = apply_brand_guide(brief_dict, brand_guide)

            # Save enhanced brief temporarily
            enhanced_brief = Path(brief).parent / f"{Path(brief).stem}_enhanced.json"
            with open(enhanced_brief, "w") as f:
                json.dump(enhanced_brief_dict, f, indent=2)

        # Run pipeline
        results = pipeline.process_campaign(
            str(enhanced_brief),
            resume=resume
        )

        # Display summary
        _display_results(results)

        console.print("\n[bold green]✓ Pipeline completed successfully[/bold green]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Pipeline failed: {e}[/bold red]\n")
        if verbose:
            console.print_exception()
        sys.exit(1)


# Stage-specific commands removed - see README Future Improvements section
# These would require pipeline refactoring to extract individual stages


# ============================================================================
# VALIDATE COMMAND GROUP
# ============================================================================


@cli.group()
def validate():
    """Validate briefs, brand guides, and configuration."""
    pass


@validate.command()
@click.argument("brief_path", type=click.Path(exists=True))
def brief(brief_path):
    """
    Validate campaign brief JSON file.

    Checks for required fields, data types, and common issues.

    Example:
        creatimation validate brief briefs/campaign.json
    """
    import json

    try:
        console.print(f"\n[bold]Validating brief: {brief_path}[/bold]\n")

        with open(brief_path) as f:
            brief_data = json.load(f)

        # Required fields
        required = ["campaign_id", "products", "target_region", "campaign_message"]
        missing = [field for field in required if field not in brief_data]

        if missing:
            console.print(f"[red]✗ Missing required fields: {', '.join(missing)}[/red]")
            sys.exit(1)

        # Validate products
        products = brief_data.get("products", [])
        if not products:
            console.print("[red]✗ No products specified[/red]")
            sys.exit(1)

        if len(products) < 2:
            console.print("[yellow]⚠ Only 1 product - consider adding more for variety[/yellow]")

        # Display summary
        table = Table(title="Brief Validation Results")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Campaign ID", brief_data.get("campaign_id"))
        table.add_row("Products", str(len(products)))
        table.add_row("Target Region", brief_data.get("target_region"))
        table.add_row("Campaign Message", brief_data.get("campaign_message"))

        console.print(table)
        console.print("\n[bold green]✓ Brief is valid[/bold green]\n")

    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        sys.exit(1)


@validate.command(name="brand-guide")
@click.argument("guide_path", type=click.Path(exists=True))
def validate_brand_guide(guide_path):
    """
    Validate brand guide YAML file.

    Checks schema, required fields, and provides recommendations.

    Example:
        creatimation validate brand-guide brand-guides/minimal_blue.yml
    """
    from .brand_guide_loader import validate_brand_guide as validate_guide

    try:
        console.print(f"\n[bold]Validating brand guide: {guide_path}[/bold]\n")

        result = validate_guide(guide_path)

        if not result["valid"]:
            console.print(f"[red]✗ Invalid brand guide: {result['error']}[/red]")
            sys.exit(1)

        # Display brand guide info
        brand_guide = result["brand_guide"]

        table = Table(title="Brand Guide Validation Results")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Brand Name", brand_guide.brand.name)
        table.add_row("Industry", brand_guide.brand.industry or "(not specified)")
        table.add_row("Primary Color", brand_guide.colors.primary)
        table.add_row("Layout Style", brand_guide.visual.layout_style)
        table.add_row("Tone", brand_guide.messaging.tone)

        console.print(table)

        # Show warnings
        if result["warnings"]:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in result["warnings"]:
                console.print(f"  • {warning}")

        console.print("\n[bold green]✓ Brand guide is valid[/bold green]\n")

    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        sys.exit(1)


# ============================================================================
# CACHE COMMAND GROUP
# ============================================================================


@cli.group()
def cache():
    """Manage pipeline cache (clear, stats, inspect)."""
    pass


@cache.command()
def clear():
    """
    Clear all pipeline cache.

    Example:
        creatimation cache clear
    """
    from .cache_manager import CacheManager
    from .background_remover import BackgroundRemover

    try:
        console.print("[bold]Clearing all cache...[/bold]")

        cache_mgr = CacheManager()
        bg_remover = BackgroundRemover()

        cleared = cache_mgr.clear_cache()
        cleared_bg = bg_remover.clear_cache()

        console.print(f"[green]✓ Cleared {cleared} product cache entries[/green]")
        console.print(f"[green]✓ Cleared {cleared_bg} background removal cache entries[/green]")
        console.print("\n[bold green]Cache cleared successfully[/bold green]\n")

    except Exception as e:
        console.print(f"[red]✗ Failed to clear cache: {e}[/red]")
        sys.exit(1)


@cache.command()
def stats():
    """
    Show cache statistics.

    Example:
        creatimation cache stats
    """
    from .cache_manager import CacheManager
    import os

    try:
        cache_mgr = CacheManager()

        # Calculate cache size
        cache_dir = Path("cache")
        total_size = 0
        file_count = 0

        if cache_dir.exists():
            for root, dirs, files in os.walk(cache_dir):
                for file in files:
                    if file.endswith(('.jpg', '.png', '.json')):
                        file_path = Path(root) / file
                        total_size += file_path.stat().st_size
                        file_count += 1

        size_mb = total_size / (1024 * 1024)

        table = Table(title="Cache Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Files", str(file_count))
        table.add_row("Total Size", f"{size_mb:.2f} MB")
        table.add_row("Cache Directory", str(cache_dir.absolute()))

        console.print("\n")
        console.print(table)
        console.print("\n")

    except Exception as e:
        console.print(f"[red]✗ Failed to get cache stats: {e}[/red]")
        sys.exit(1)


# ============================================================================
# CONFIG COMMAND GROUP
# ============================================================================


@cli.group()
def config():
    """Manage configuration files."""
    pass


@config.command()
@click.option("--output", "-o", type=click.Path(), help="Output path (default: .creatimation.yml)")
def init(output):
    """
    Create .creatimation.yml configuration template.

    Generates a template with all available settings and inline documentation.

    Example:
        creatimation config init
        creatimation config init --output my-config.yml
    """
    from .config import init_config

    try:
        output_path = init_config(output)
        console.print(f"\n[green]✓ Created config template: {output_path}[/green]")
        console.print("\nEdit this file to customize pipeline defaults.")
        console.print("CLI flags will override these settings.\n")

    except Exception as e:
        console.print(f"[red]✗ Failed to create config: {e}[/red]")
        sys.exit(1)


@config.command()
@click.pass_context
def show(ctx):
    """
    Show effective configuration.

    Displays the merged configuration from CLI flags, config file, and defaults.

    Example:
        creatimation config show
    """
    from .config import ConfigManager

    try:
        config_manager = ConfigManager(ctx.obj.get("config_path"))
        output = config_manager.show_effective_config()

        console.print()
        console.print(Panel(output, title="Effective Configuration", border_style="cyan"))
        console.print()

    except Exception as e:
        console.print(f"[red]✗ Failed to show config: {e}[/red]")
        sys.exit(1)


@config.command(name="validate")
@click.pass_context
def validate_config(ctx):
    """
    Validate .creatimation.yml configuration file.

    Example:
        creatimation config validate
    """
    from .config import validate_config as validate_cfg

    try:
        result = validate_cfg(ctx.obj.get("config_path"))

        if not result["valid"]:
            console.print(f"\n[red]✗ Invalid configuration: {result['error']}[/red]\n")
            sys.exit(1)

        console.print("\n[green]✓ Configuration is valid[/green]")

        if result["warnings"]:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in result["warnings"]:
                console.print(f"  • {warning}")

        console.print()

    except Exception as e:
        console.print(f"[red]✗ Validation failed: {e}[/red]")
        sys.exit(1)


# ============================================================================
# INSPECT COMMAND GROUP
# ============================================================================


@cli.group()
def inspect():
    """Inspect pipeline state, outputs, and metadata."""
    pass


@inspect.command()
@click.argument("campaign_id")
def state(campaign_id):
    """
    Inspect pipeline state for a campaign.

    Example:
        creatimation inspect state spring_refresh_2025
    """
    from .state_tracker import StateTracker

    try:
        tracker = StateTracker(campaign_id)

        if not tracker.can_resume():
            console.print(f"\n[yellow]No state found for campaign: {campaign_id}[/yellow]\n")
            sys.exit(1)

        summary = tracker.get_summary()

        table = Table(title=f"Pipeline State: {campaign_id}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Progress", f"{summary['progress_percentage']}%")
        table.add_row("Current Step", summary['next_step'])
        table.add_row("Products Processed", str(summary.get('products_processed', 0)))

        console.print("\n")
        console.print(table)
        console.print("\n")

    except Exception as e:
        console.print(f"[red]✗ Failed to inspect state: {e}[/red]")
        sys.exit(1)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _build_cli_overrides(output, variants, ratios, brand_guide) -> Dict[str, Any]:
    """Build CLI overrides dictionary"""
    overrides = {}

    if output:
        overrides["project"] = {"output_dir": output}

    if variants:
        overrides["generation"] = overrides.get("generation", {})
        overrides["generation"]["variants_per_ratio"] = variants

    if ratios:
        overrides["generation"] = overrides.get("generation", {})
        overrides["generation"]["aspect_ratios"] = [r.strip() for r in ratios.split(",")]

    if brand_guide:
        overrides["generation"] = overrides.get("generation", {})
        overrides["generation"]["brand_guide"] = brand_guide

    return overrides


def _display_results(results: Dict[str, Any]):
    """Display pipeline results in a nice table"""
    table = Table(title="Pipeline Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Campaign ID", results.get("campaign_id", "N/A"))
    table.add_row("Products Processed", str(len(results.get("products_processed", []))))
    table.add_row("Total Creatives", str(results.get("total_creatives", 0)))
    table.add_row("Processing Time", f"{results.get('processing_time', 0)}s")
    table.add_row("Cache Hit Rate", f"{results.get('cache_hit_rate', 0)}%")

    console.print("\n")
    console.print(table)


def main():
    """CLI entry point"""
    cli(obj={})


if __name__ == "__main__":
    main()
