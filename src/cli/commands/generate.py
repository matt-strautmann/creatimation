"""
Generate command group - Create creative assets with professional automation.

Provides command patterns for the core creative generation workflow.
Includes campaign generation, individual asset creation, and batch processing.
"""

import sys
import time
from pathlib import Path

import click
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..constants import (
    DEFAULT_ASPECT_RATIOS,
    DEFAULT_REGIONS,
    LIFESTYLE_VARIANT_TYPES,
    SUPPORTED_ASPECT_RATIOS,
)
from ..core import pass_context, require_workspace
from ..plugins import call_hook
from ..utils.output import console, error_console


@click.group(invoke_without_command=True)
@click.option("--brief", "-b", type=click.Path(exists=True), help="Campaign brief JSON file")
@click.option(
    "--output", "-o", type=click.Path(), help="Output directory (overrides workspace config)"
)
@click.option("--brand-guide", "-g", type=click.Path(exists=True), help="Brand guide YAML file")
@click.option("--no-cache", is_flag=True, help="Disable cache, regenerate everything")
@click.option("--resume", is_flag=True, help="Resume from saved pipeline state")
@click.option("--dry-run", is_flag=True, help="Preview generation plan without execution")
@pass_context
def generate(ctx, brief, output, brand_guide, no_cache, resume, dry_run):
    """
    Generate creative assets with intelligent automation.

    Creates professional-quality creative assets from campaign briefs with
    support for multiple regions, aspect ratios, and variant types.

    Examples:
        creatimation generate --brief campaign.json
        creatimation generate campaign --brief campaign.json --brand-guide guide.yml
        creatimation generate --brief campaign.json --dry-run

    Workspace Commands:
        campaign    Generate complete campaign assets
        asset       Generate individual creative asset
        batch       Batch process multiple campaigns
    """
    # If no subcommand and brief provided, run campaign generation
    click_ctx = click.get_current_context()
    if click_ctx.invoked_subcommand is None:
        if brief:
            ctx.invoke(
                campaign,
                brief=brief,
                output=output,
                brand_guide=brand_guide,
                no_cache=no_cache,
                resume=resume,
                dry_run=dry_run,
            )
        else:
            # Show help when no brief provided
            console.print()
            console.print("[yellow]No brief specified.[/yellow]")
            console.print(
                "Use [cyan]--brief[/cyan] to specify a campaign brief, or see [cyan]creatimation generate --help[/cyan]"
            )
            console.print()


@generate.command()
@click.argument("brief", type=click.Path(exists=True))
@click.option(
    "--output", "-o", type=click.Path(), help="Output directory (overrides workspace config)"
)
@click.option("--variants", "-n", type=int, help="Number of variants per configuration")
@click.option("--ratios", "-r", help="Comma-separated aspect ratios (e.g., 1x1,9x16,16x9)")
@click.option("--regions", help="Comma-separated target regions (e.g., US,EMEA,APAC)")
@click.option("--brand-guide", "-g", type=click.Path(exists=True), help="Brand guide YAML file")
@click.option("--no-cache", is_flag=True, help="Disable cache, regenerate everything")
@click.option("--resume", is_flag=True, help="Resume from saved pipeline state")
@click.option("--dry-run", is_flag=True, help="Preview generation plan without execution")
@click.option(
    "--simulate", is_flag=True, help="Fast simulation mode for demos (creates mock images)"
)
@click.option(
    "--parallel", "-j", type=int, default=3, help="Number of parallel workers (default: 3)"
)
@pass_context
@require_workspace
def campaign(
    ctx,
    brief,
    output,
    variants,
    ratios,
    regions,
    brand_guide,
    no_cache,
    resume,
    dry_run,
    simulate,
    parallel,
):
    """
    Generate complete campaign assets from brief.

    Processes a campaign brief to generate all required creative assets
    across specified regions, aspect ratios, and variant types.

    This is the primary generation workflow that handles:
    - Multi-region localization
    - Multiple aspect ratios (1x1, 9x16, 16x9, etc.)
    - Variant generation (base, color_shift, text_style, etc.)
    - Brand guide integration
    - Intelligent caching and resumption
    - Parallel generation for faster processing

    Examples:
        creatimation generate campaign briefs/spring2025.json
        creatimation generate campaign briefs/spring2025.json --brand-guide guides/minimal.yml
        creatimation generate campaign briefs/spring2025.json --ratios 1x1,16x9 --regions US,EMEA
        creatimation generate campaign briefs/spring2025.json --parallel 5
        creatimation generate campaign briefs/spring2025.json --dry-run
    """
    # Analytics hook: Track command start
    call_hook("before_command", command_name="generate_campaign")

    command_success = False
    start_time = time.time()

    try:
        # ========================================
        # INTELLIGENT PRE-FLIGHT CHECKS
        # ========================================

        console.print()
        console.print("[bold cyan]🔧 Pre-Flight Configuration[/bold cyan]")
        console.print()

        # 1. Load workspace and extract campaign info
        workspace = ctx.ensure_workspace()
        campaign_id = _extract_campaign_id(brief)

        # 2. Auto-update workspace config based on briefs
        _auto_update_workspace_config(ctx, brief)

        # 3. Validate configuration
        validation_passed = _validate_generation_config(ctx)

        # 4. Show effective configuration summary
        _show_effective_config_summary(ctx)

        if not validation_passed:
            error_console.print("[red]✗[/red] Configuration validation failed")
            console.print("Fix configuration issues before proceeding")
            sys.exit(1)

        console.print()
        console.print("[bold green]✓[/bold green] Pre-flight checks passed")
        console.print()

        # ========================================
        # GENERATION PIPELINE
        # ========================================

        # Get configured pipeline
        container = ctx.container
        pipeline = container.get_pipeline(
            campaign_id=campaign_id, no_cache=no_cache, dry_run=dry_run, max_workers=parallel
        )

        # Show generation plan
        _show_generation_plan(brief, brand_guide, dry_run)

        if dry_run:
            # Preview mode
            results = pipeline.process_campaign(brief, brand_guide_path=brand_guide, resume=False)
            _show_dry_run_results(results)

            # Analytics hook: Track dry run
            dry_run_metrics = {
                "campaign_id": campaign_id,
                "dry_run": True,
                "processing_time": time.time() - start_time,
                "success": True,
            }
            call_hook("generation_complete", campaign_id=campaign_id, metrics=dry_run_metrics)
            command_success = True
            return

        if simulate:
            # Fast simulation mode for demos
            results = _run_simulation(brief, brand_guide, campaign_id, ctx)
            _show_simulation_results(results)

            # Analytics hook: Track simulation
            simulation_metrics = {
                "campaign_id": campaign_id,
                "simulation": True,
                "processing_time": time.time() - start_time,
                "success": True,
                "total_creatives": results.get("total_creatives", 0),
            }
            call_hook("generation_complete", campaign_id=campaign_id, metrics=simulation_metrics)
            command_success = True
            return

        # Execute generation with progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            # Add main task
            main_task = progress.add_task("Generating campaign assets...", total=100)

            # Start generation
            start_time = time.time()
            results = pipeline.process_campaign(brief, brand_guide_path=brand_guide, resume=resume)

            # Complete progress
            progress.update(main_task, completed=100)

        # Show results
        _show_generation_results(results, time.time() - start_time)

        # Success message
        workspace_path = workspace.workspace_path
        console.print()
        console.print("[green]✓[/green] Campaign generated successfully")
        console.print(f"[dim]Assets saved to: {workspace_path / 'output'}[/dim]")
        console.print()

        # Analytics hook: Track successful generation
        generation_metrics = {
            "campaign_id": campaign_id,
            "total_creatives": results.get("total_creatives", 0),
            "processing_time": time.time() - start_time,
            "cache_hits": results.get("cache_hits", 0),
            "cache_misses": results.get("cache_misses", 0),
            "regions": len(regions) if regions else 2,
            "success": True,
        }
        call_hook("generation_complete", campaign_id=campaign_id, metrics=generation_metrics)
        command_success = True

    except Exception as e:
        error_console.print(f"[red]✗[/red] Generation failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()

        # Analytics hook: Track failed generation
        call_hook(
            "generation_complete",
            campaign_id=getattr(locals(), "campaign_id", "unknown"),
            metrics={
                "success": False,
                "error": str(e),
                "processing_time": time.time() - start_time,
            },
        )
        sys.exit(1)

    finally:
        # Analytics hook: Track command completion
        call_hook(
            "after_command",
            command_name="generate_campaign",
            success=command_success,
            duration=time.time() - start_time,
        )


@generate.command()
@click.option("--product", "-p", required=True, help="Product name")
@click.option("--message", "-m", required=True, help="Campaign message")
@click.option(
    "--ratio",
    "-r",
    type=click.Choice(SUPPORTED_ASPECT_RATIOS),
    default="1x1",
    help="Aspect ratio",
)
@click.option("--region", default="US", help="Target region")
@click.option("--variant", default="base", help="Variant type")
@click.option("--theme", help="Creative theme")
@click.option("--output", "-o", type=click.Path(), help="Output file path")
@click.option("--brand-guide", "-g", type=click.Path(exists=True), help="Brand guide YAML file")
@pass_context
@require_workspace
def asset(ctx, product, message, ratio, region, variant, theme, output, brand_guide):
    """
    Generate a single creative asset.

    Creates an individual creative asset with specified parameters.
    Useful for testing, prototyping, or generating specific variations.

    Examples:
        creatimation generate asset --product "Power Dish Soap" --message "Clean faster"
        creatimation generate asset -p "Eco Cleaner" -m "Go green" --ratio 16x9 --variant color_shift
        creatimation generate asset -p "Premium Detergent" -m "Premium clean" --theme "luxury" -o custom.jpg
    """
    try:
        ctx.ensure_workspace()

        # Get configured components
        container = ctx.container
        image_generator = container.get_image_generator()
        output_manager = container.get_output_manager()

        # Load brand guide if provided
        brand_guide_data = None
        if brand_guide:
            brand_guide_loader = container.get_brand_guide_loader()
            brand_guide_data = brand_guide_loader.load_brand_guide(brand_guide)

        console.print()
        console.print("[bold cyan]Generating creative asset[/bold cyan]")
        console.print(f"Product: {product}")
        console.print(f"Message: {message}")
        console.print(f"Ratio: {ratio} | Region: {region} | Variant: {variant}")
        if theme:
            console.print(f"Theme: {theme}")
        console.print()

        with console.status("[bold green]Generating asset..."):
            # Generate product image
            product_image = image_generator.generate_product_only(
                product_name=product, aspect_ratio="1x1"
            )

            # Generate creative
            final_image = image_generator.generate_product_creative(
                product_name=product,
                campaign_message=message,
                scene_description="modern clean environment, professional and appealing",
                aspect_ratio=ratio,
                theme=theme,
                region=region,
                variant_id=variant,
                product_image=product_image,
                brand_guide=brand_guide_data,
            )

            # Save output
            if output:
                final_image.save(output)
                output_path = output
            else:
                # Use output manager for semantic structure
                metadata = {
                    "product": product,
                    "message": message,
                    "ratio": ratio,
                    "region": region,
                    "variant": variant,
                    "theme": theme,
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }

                output_path = output_manager.save_creative(
                    final_image,
                    product,
                    ratio,
                    metadata,
                    template="hero-product",
                    region=region,
                    variant_id=variant,
                )

        console.print(f"[green]✓[/green] Asset generated: [cyan]{Path(output_path).name}[/cyan]")
        console.print(f"[dim]Saved to: {output_path}[/dim]")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Asset generation failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@generate.command()
@click.argument("briefs_dir", type=click.Path(exists=True, file_okay=False))
@click.option("--pattern", default="*.json", help="File pattern to match (default: *.json)")
@click.option(
    "--parallel",
    "-j",
    type=int,
    default=3,
    help="Number of parallel workers per campaign (default: 3)",
)
@click.option(
    "--brand-guide",
    "-g",
    type=click.Path(exists=True),
    help="Brand guide YAML file (applies to all campaigns)",
)
@click.option("--no-cache", is_flag=True, help="Disable cache for all campaigns")
@click.option("--dry-run", is_flag=True, help="Preview all campaigns without execution")
@pass_context
@require_workspace
def batch(ctx, briefs_dir, pattern, parallel, brand_guide, no_cache, dry_run):
    """
    Batch process multiple campaign briefs.

    Discovers and processes all campaign briefs in a directory.
    Supports parallel processing for improved performance.

    Examples:
        creatimation generate batch ./campaigns/
        creatimation generate batch ./campaigns/ --pattern "*spring*.json"
        creatimation generate batch ./campaigns/ --parallel 3 --brand-guide guide.yml
        creatimation generate batch ./campaigns/ --dry-run
    """
    try:
        from glob import glob

        ctx.ensure_workspace()

        # Find brief files
        brief_pattern = Path(briefs_dir) / pattern
        brief_files = list(glob(str(brief_pattern)))

        if not brief_files:
            error_console.print(f"[red]✗[/red] No brief files found matching: {brief_pattern}")
            sys.exit(1)

        console.print()
        console.print(f"[bold cyan]Batch processing {len(brief_files)} campaigns[/bold cyan]")

        if dry_run:
            console.print("[yellow]Dry run mode - no assets will be generated[/yellow]")

        console.print()

        # Show discovered briefs
        table = Table(title="Discovered Campaign Briefs", show_header=True)
        table.add_column("Brief File", style="cyan")
        table.add_column("Campaign ID", style="green")

        for brief_file in brief_files:
            campaign_id = _extract_campaign_id(brief_file)
            table.add_row(Path(brief_file).name, campaign_id or "Unknown")

        console.print(table)
        console.print()

        # Process each brief
        results = []
        failed = []

        for i, brief_file in enumerate(brief_files, 1):
            campaign_id = _extract_campaign_id(brief_file)

            console.print(
                f"[{i}/{len(brief_files)}] Processing: [cyan]{Path(brief_file).name}[/cyan]"
            )

            try:
                # Get pipeline for this campaign
                container = ctx.container
                pipeline = container.get_pipeline(
                    campaign_id=campaign_id or f"batch_{i}",
                    no_cache=no_cache,
                    dry_run=dry_run,
                    max_workers=parallel,
                )

                # Process campaign
                result = pipeline.process_campaign(
                    brief_file, brand_guide_path=brand_guide, resume=False
                )

                results.append({"brief": brief_file, "campaign_id": campaign_id, "result": result})

                console.print(f"  [green]✓[/green] Completed: {campaign_id}")

            except Exception as e:
                failed.append({"brief": brief_file, "campaign_id": campaign_id, "error": str(e)})
                console.print(f"  [red]✗[/red] Failed: {e}")

            console.print()

        # Show summary
        _show_batch_results(results, failed)

        if failed:
            sys.exit(1)

    except Exception as e:
        error_console.print(f"[red]✗[/red] Batch processing failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _extract_campaign_id(brief_path: str) -> str | None:
    """Extract campaign ID from brief file."""
    import json

    try:
        with open(brief_path) as f:
            brief_data = json.load(f)
        campaign_id = brief_data.get("campaign_id")
        return str(campaign_id) if campaign_id else None
    except (json.JSONDecodeError, FileNotFoundError, KeyError, OSError):
        # Fallback to filename
        return Path(brief_path).stem


def _show_generation_plan(brief: str, brand_guide: str | None, dry_run: bool):
    """Show generation plan before execution."""
    import json

    try:
        with open(brief) as f:
            brief_data = json.load(f)

        campaign_id = brief_data.get("campaign_id", "Unknown")
        products = brief_data.get("products", [])
        regions = brief_data.get("target_regions", ["US"])

        # Get creative requirements
        creative_reqs = brief_data.get("creative_requirements", {})
        ratios = creative_reqs.get("aspect_ratios", DEFAULT_ASPECT_RATIOS)
        variants = creative_reqs.get("variant_types", [])

        console.print()

        # Campaign info panel
        info_items = [
            f"[bold]Campaign:[/bold] {campaign_id}",
            f"[bold]Products:[/bold] {len(products)} ({', '.join(products[:3])}{'...' if len(products) > 3 else ''})",
            f"[bold]Regions:[/bold] {', '.join(regions)}",
            f"[bold]Aspect Ratios:[/bold] {', '.join(ratios)}",
            f"[bold]Variants:[/bold] {', '.join(variants) if variants else 'None specified'}",
        ]

        if brand_guide:
            info_items.append(f"[bold]Brand Guide:[/bold] {Path(brand_guide).name}")

        if dry_run:
            info_items.append("[yellow][bold]Mode:[/bold] Dry Run (Preview Only)[/yellow]")

        console.print(Panel("\n".join(info_items), title="🎨 Generation Plan", border_style="cyan"))

    except Exception:
        console.print(f"[dim]Brief: {Path(brief).name}[/dim]")


def _show_dry_run_results(results):
    """Show dry run preview results."""
    console.print()

    table = Table(title="Generation Preview", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Campaign ID", results.get("campaign_id", "Unknown"))
    table.add_row("Products", str(results.get("total_products", 0)))
    table.add_row("Regions", str(results.get("total_regions", 0)))
    table.add_row("Total Creatives", str(results.get("total_creatives_planned", 0)))

    if "products" in results:
        table.add_row("Product List", ", ".join(results["products"][:5]))

    if "regions" in results:
        table.add_row("Region List", ", ".join(results["regions"]))

    console.print(table)
    console.print()
    console.print("[yellow]This was a dry run - no assets were generated.[/yellow]")
    console.print("Remove [cyan]--dry-run[/cyan] to execute generation.")
    console.print()


def _show_generation_results(results, processing_time):
    """Show generation results summary."""
    console.print()

    table = Table(title="Generation Results", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Campaign ID", results.get("campaign_id", "Unknown"))
    table.add_row("Products Processed", str(len(results.get("products_processed", []))))
    table.add_row("Total Creatives", str(results.get("total_creatives", 0)))
    table.add_row("Cache Hits", str(results.get("cache_hits", 0)))
    table.add_row("Cache Misses", str(results.get("cache_misses", 0)))
    table.add_row("Processing Time", f"{processing_time:.1f}s")

    # Calculate cache hit rate
    total_cache = results.get("cache_hits", 0) + results.get("cache_misses", 0)
    if total_cache > 0:
        hit_rate = (results.get("cache_hits", 0) / total_cache) * 100
        table.add_row("Cache Hit Rate", f"{hit_rate:.1f}%")

    console.print(table)


def _show_batch_results(results, failed):
    """Show batch processing results."""
    console.print()
    console.print("[bold]Batch Processing Complete[/bold]")
    console.print()

    if results:
        console.print(f"[green]✓[/green] Successfully processed: {len(results)} campaigns")

        # Summary table
        table = Table(title="Successful Campaigns", show_header=True)
        table.add_column("Campaign", style="cyan")
        table.add_column("Creatives", style="green")
        table.add_column("Processing Time", style="yellow")

        for result in results:
            campaign_id = result["campaign_id"] or Path(result["brief"]).stem
            creatives = result["result"].get("total_creatives", 0)
            proc_time = result["result"].get("processing_time", 0)

            table.add_row(campaign_id, str(creatives), f"{proc_time:.1f}s")

        console.print(table)

    if failed:
        console.print()
        console.print(f"[red]✗[/red] Failed campaigns: {len(failed)}")

        for failure in failed:
            campaign_id = failure["campaign_id"] or Path(failure["brief"]).stem
            console.print(f"  [red]•[/red] {campaign_id}: {failure['error']}")

    console.print()


# ============================================================================
# PRE-FLIGHT CONFIGURATION HELPERS
# ============================================================================


def _auto_update_workspace_config(ctx, brief_path):
    """Auto-update workspace config based on brief analysis."""
    import json
    from pathlib import Path

    try:
        # Load the brief to analyze
        brief_file = Path(brief_path)
        if not brief_file.exists():
            console.print(f"[yellow]⚠[/yellow] Brief file not found: {brief_path}")
            return

        with open(brief_file) as f:
            json.load(f)

        # Check if workspace config needs update
        workspace_config_file = ctx.workspace_path / ".creatimation.yml"

        if not workspace_config_file.exists():
            console.print("[yellow]⚠[/yellow] No workspace config found")
            console.print("[cyan]🔧[/cyan] Auto-creating workspace configuration...")

            # Import config init function and template generator
            from .config import _get_config_template

            config_content = _get_config_template("complete", is_global=False)
            with open(workspace_config_file, "w") as f:
                f.write(config_content)
            console.print(f"[green]✓[/green] Created workspace config: {workspace_config_file}")
        else:
            console.print("[green]✓[/green] Workspace configuration exists")

    except Exception as e:
        console.print(f"[yellow]⚠[/yellow] Config auto-update failed: {e}")


def _validate_generation_config(ctx):
    """Validate configuration for generation and return success status."""
    console.print("[cyan]🔍[/cyan] Validating configuration...")

    errors = []
    warnings = []

    # Check global config
    from .config import _validate_global_config

    global_result = _validate_global_config()
    errors.extend(global_result.get("errors", []))
    warnings.extend(global_result.get("warnings", []))

    # Check workspace config
    if ctx.workspace_manager:
        from .config import _validate_workspace_config_file

        workspace_result = _validate_workspace_config_file(ctx.workspace_manager)
        errors.extend(workspace_result.get("errors", []))
        warnings.extend(workspace_result.get("warnings", []))

    # Check API key specifically
    import os

    if not os.getenv("GOOGLE_API_KEY"):
        errors.append("GOOGLE_API_KEY not found in environment")

    # Display results
    if errors:
        for error in errors:
            console.print(f"  [red]✗[/red] {error}")

    if warnings:
        for warning in warnings:
            console.print(f"  [yellow]⚠[/yellow] {warning}")

    if not errors and not warnings:
        console.print("  [green]✓[/green] All configurations valid")
    elif not errors:
        console.print(f"  [green]✓[/green] Configuration valid ({len(warnings)} warnings)")

    return len(errors) == 0


def _show_effective_config_summary(ctx):
    """Show concise effective configuration summary."""
    console.print()
    console.print("[cyan]📋[/cyan] Effective Configuration:")

    # Workspace info
    if ctx.workspace_manager:
        workspace_config = ctx.workspace_manager.get_config()
        project = workspace_config.get("project", {})

        console.print(
            f"  [green]✓[/green] Project: [white]{project.get('name', 'Unknown')}[/white]"
        )
        console.print(f"  [green]✓[/green] Brand: [white]{project.get('brand', 'Unknown')}[/white]")
        console.print(
            f"  [green]✓[/green] Industry: [white]{project.get('industry', 'Unknown')}[/white]"
        )

        # Count campaigns
        from .config import _detect_campaigns

        campaigns = _detect_campaigns(ctx.workspace_manager.workspace_path)
        console.print(f"  [green]✓[/green] Campaigns: [white]{len(campaigns)} detected[/white]")

        # Generation settings
        generation = workspace_config.get("generation", {})
        console.print(
            f"  [green]✓[/green] Default variants: [white]{generation.get('default_variants', 3)}[/white]"
        )

        ratios = generation.get("aspect_ratios", DEFAULT_ASPECT_RATIOS)
        console.print(f"  [green]✓[/green] Aspect ratios: [white]{', '.join(ratios)}[/white]")
    else:
        console.print("  [yellow]⚠[/yellow] No workspace configuration")

    # API status
    import os

    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        console.print("  [green]✓[/green] Google API: [white]Configured[/white]")
    else:
        console.print("  [red]✗[/red] Google API: Not configured")

    console.print()


def _run_simulation(brief_path, brand_guide_path, campaign_id, ctx):
    """Run fast simulation mode for demos."""
    import json
    import time
    from pathlib import Path

    from PIL import Image, ImageDraw, ImageFont
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

    # Load brief
    with open(brief_path) as f:
        brief_data = json.load(f)

    products = brief_data.get("products", [])
    regions = brief_data.get("target_regions", DEFAULT_REGIONS)
    ratios = brief_data.get("creative_requirements", {}).get("aspect_ratios", DEFAULT_ASPECT_RATIOS)
    variants = brief_data.get("creative_requirements", {}).get(
        "variant_types", LIFESTYLE_VARIANT_TYPES
    )

    total_creatives = len(products) * len(regions) * len(ratios) * len(variants)

    # Output directory for simulation (separate from real campaigns)
    output_dir = Path("output") / "simulations" / campaign_id
    output_dir.mkdir(parents=True, exist_ok=True)

    # Aspect ratio dimensions
    aspect_dims = {
        "1x1": (800, 800),
        "9x16": (800, 1422),
        "16x9": (1422, 800),
        "4x5": (800, 1000),
        "5x4": (1000, 800),
    }

    # Color schemes for variants
    variant_colors = {
        "base": ("#0066CC", "#FFFFFF"),  # Blue & White
        "hero": ("#FFB900", "#000000"),  # Yellow & Black
        "lifestyle": ("#00A86B", "#FFFFFF"),  # Green & White
        "color_shift": ("#FF6B35", "#FFFFFF"),
        "text_style": ("#6B73FF", "#FFFFFF"),
    }

    results = {
        "campaign_id": campaign_id,
        "total_creatives": total_creatives,
        "products_processed": len(products),
        "regions_processed": len(regions),
        "simulation": True,
        "output_dir": str(output_dir),
        "files_created": [],
    }

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]Simulating campaign generation..."),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:

        task = progress.add_task("", total=total_creatives)

        for product in products:
            product_name = product["name"] if isinstance(product, dict) else str(product)
            product_slug = product_name.lower().replace(" ", "-").replace("&", "-")

            for region in regions:
                for ratio in ratios:
                    for variant in variants:
                        # Create realistic directory structure
                        variant_slug = variant.replace("_", "-")
                        creative_dir = (
                            output_dir / product_slug / variant_slug / region.lower() / ratio
                        )
                        creative_dir.mkdir(parents=True, exist_ok=True)

                        # Generate mock image
                        dims = aspect_dims.get(ratio, (800, 800))
                        bg_color, text_color = variant_colors.get(variant, ("#0066CC", "#FFFFFF"))

                        img = Image.new("RGB", dims, bg_color)
                        draw = ImageDraw.Draw(img)

                        # Add product name
                        try:
                            font_size = max(24, dims[1] // 20)
                            font = ImageFont.load_default()  # Fallback font
                        except Exception:
                            font = ImageFont.load_default()

                        # Center text
                        text_lines = [
                            product_name,
                            f"{variant.title()} • {region}",
                            f"{ratio} • Demo Mode",
                        ]

                        y_start = dims[1] // 3
                        for i, line in enumerate(text_lines):
                            bbox = draw.textbbox((0, 0), line, font=font)
                            text_width = bbox[2] - bbox[0]
                            x = (dims[0] - text_width) // 2
                            y = y_start + (i * (font_size + 10))
                            draw.text((x, y), line, fill=text_color, font=font)

                        # Add decorative elements
                        draw.rectangle([20, 20, dims[0] - 20, 40], fill=text_color)
                        draw.rectangle(
                            [20, dims[1] - 40, dims[0] - 20, dims[1] - 20], fill=text_color
                        )

                        # Save image
                        filename = (
                            f"{product_slug}_{variant_slug}_{region.lower()}_{ratio}_creative.jpg"
                        )
                        image_path = creative_dir / filename
                        img.save(image_path, "JPEG", quality=90)
                        results["files_created"].append(str(image_path))

                        # Create metadata
                        metadata = {
                            "campaign_id": campaign_id,
                            "product_name": product_name,
                            "variant_type": variant,
                            "region": region,
                            "aspect_ratio": ratio,
                            "template": variant_slug,
                            "simulation": True,
                            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "file_size_bytes": (
                                image_path.stat().st_size if image_path.exists() else 0
                            ),
                            "dimensions": dims,
                        }

                        metadata_path = creative_dir / "metadata.json"
                        with open(metadata_path, "w") as f:
                            json.dump(metadata, f, indent=2)

                        progress.advance(task)
                        time.sleep(0.05)  # Small delay for realistic progress

    return results


def _show_simulation_results(results):
    """Show simulation results summary."""
    from rich.table import Table

    console.print()
    console.print("[bold green]🎬 Simulation Complete![/bold green]")
    console.print()

    # Results table
    table = Table(title="Simulation Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="white")

    table.add_row("Campaign ID", results["campaign_id"])
    table.add_row("Total Creatives", str(results["total_creatives"]))
    table.add_row("Products Processed", str(results["products_processed"]))
    table.add_row("Regions Processed", str(results["regions_processed"]))
    table.add_row("Output Directory", results["output_dir"])
    table.add_row("Mode", "🎬 Demo Simulation")

    console.print(table)
    console.print()

    # Show sample files
    if results["files_created"]:
        console.print("[cyan]📁 Sample Generated Files:[/cyan]")
        for file_path in results["files_created"][:5]:  # Show first 5
            # Use simple path display to avoid relative path issues
            display_path = str(file_path).replace(str(Path.cwd()) + "/", "")
            console.print(f"   {display_path}")

        if len(results["files_created"]) > 5:
            console.print(f"   ... and {len(results['files_created']) - 5} more")
        console.print()

    console.print(
        "[yellow]💡 This was a simulation - images are mock demos, not AI-generated.[/yellow]"
    )
    console.print("[green]✓[/green] Perfect for demonstrations and testing output structure!")
    console.print()
