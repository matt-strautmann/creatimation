"""
Generate command group - Create creative assets with professional automation.

GitHub spec-kit inspired command patterns for the core creative generation workflow.
Provides campaign generation, individual asset creation, and batch processing.
"""
import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.panel import Panel
from rich.console import Group

from ..core import pass_context, require_workspace
from ..utils.output import console, error_console


@click.group(invoke_without_command=True)
@click.option(
    "--brief",
    "-b",
    type=click.Path(exists=True),
    help="Campaign brief JSON file"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output directory (overrides workspace config)"
)
@click.option(
    "--brand-guide",
    "-g",
    type=click.Path(exists=True),
    help="Brand guide YAML file"
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable cache, regenerate everything"
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from saved pipeline state"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview generation plan without execution"
)
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
    if ctx.invoked_subcommand is None:
        if brief:
            ctx.invoke(campaign, brief=brief, output=output, brand_guide=brand_guide,
                      no_cache=no_cache, resume=resume, dry_run=dry_run)
        else:
            # Show help when no brief provided
            console.print()
            console.print("[yellow]No brief specified.[/yellow]")
            console.print("Use [cyan]--brief[/cyan] to specify a campaign brief, or see [cyan]creatimation generate --help[/cyan]")
            console.print()


@generate.command()
@click.argument("brief", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output directory (overrides workspace config)"
)
@click.option(
    "--variants",
    "-n",
    type=int,
    help="Number of variants per configuration"
)
@click.option(
    "--ratios",
    "-r",
    help="Comma-separated aspect ratios (e.g., 1x1,9x16,16x9)"
)
@click.option(
    "--regions",
    help="Comma-separated target regions (e.g., US,EMEA,APAC)"
)
@click.option(
    "--brand-guide",
    "-g",
    type=click.Path(exists=True),
    help="Brand guide YAML file"
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable cache, regenerate everything"
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from saved pipeline state"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview generation plan without execution"
)
@pass_context
@require_workspace
def campaign(ctx, brief, output, variants, ratios, regions, brand_guide, no_cache, resume, dry_run):
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

    Examples:
        creatimation generate campaign briefs/spring2025.json
        creatimation generate campaign briefs/spring2025.json --brand-guide guides/minimal.yml
        creatimation generate campaign briefs/spring2025.json --ratios 1x1,16x9 --regions US,EMEA
        creatimation generate campaign briefs/spring2025.json --dry-run
    """
    try:
        # Load workspace and container
        workspace = ctx.ensure_workspace()
        campaign_id = _extract_campaign_id(brief)

        # Get configured pipeline
        container = ctx.container
        pipeline = container.get_pipeline(
            campaign_id=campaign_id,
            no_cache=no_cache,
            dry_run=dry_run
        )

        # Show generation plan
        _show_generation_plan(brief, brand_guide, dry_run)

        if dry_run:
            # Preview mode
            results = pipeline.process_campaign(brief, brand_guide, resume=False)
            _show_dry_run_results(results)
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
            results = pipeline.process_campaign(
                brief,
                brand_guide_path=brand_guide,
                resume=resume
            )

            # Complete progress
            progress.update(main_task, completed=100)

        # Show results
        _show_generation_results(results, time.time() - start_time)

        # Success message
        workspace_path = workspace.workspace_path
        console.print()
        console.print(f"[green]✓[/green] Campaign generated successfully")
        console.print(f"[dim]Assets saved to: {workspace_path / 'output'}[/dim]")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Generation failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@generate.command()
@click.option(
    "--product",
    "-p",
    required=True,
    help="Product name"
)
@click.option(
    "--message",
    "-m",
    required=True,
    help="Campaign message"
)
@click.option(
    "--ratio",
    "-r",
    type=click.Choice(["1x1", "9x16", "16x9", "4x5", "5x4", "4x3", "3x4", "2x3", "3x2", "21x9"]),
    default="1x1",
    help="Aspect ratio"
)
@click.option(
    "--region",
    default="US",
    help="Target region"
)
@click.option(
    "--variant",
    default="base",
    help="Variant type"
)
@click.option(
    "--theme",
    help="Creative theme"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file path"
)
@click.option(
    "--brand-guide",
    "-g",
    type=click.Path(exists=True),
    help="Brand guide YAML file"
)
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
        workspace = ctx.ensure_workspace()

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
        console.print(f"[bold cyan]Generating creative asset[/bold cyan]")
        console.print(f"Product: {product}")
        console.print(f"Message: {message}")
        console.print(f"Ratio: {ratio} | Region: {region} | Variant: {variant}")
        if theme:
            console.print(f"Theme: {theme}")
        console.print()

        with console.status("[bold green]Generating asset..."):
            # Generate product image
            product_image = image_generator.generate_product_only(
                product_name=product,
                aspect_ratio="1x1"
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
                brand_guide=brand_guide_data
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
                    "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")
                }

                output_path = output_manager.save_creative(
                    final_image,
                    product,
                    ratio,
                    metadata,
                    template="hero-product",
                    region=region,
                    variant_id=variant
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
@click.option(
    "--pattern",
    default="*.json",
    help="File pattern to match (default: *.json)"
)
@click.option(
    "--parallel",
    "-j",
    type=int,
    default=1,
    help="Number of parallel jobs"
)
@click.option(
    "--brand-guide",
    "-g",
    type=click.Path(exists=True),
    help="Brand guide YAML file (applies to all campaigns)"
)
@click.option(
    "--no-cache",
    is_flag=True,
    help="Disable cache for all campaigns"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview all campaigns without execution"
)
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

        workspace = ctx.ensure_workspace()

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

            console.print(f"[{i}/{len(brief_files)}] Processing: [cyan]{Path(brief_file).name}[/cyan]")

            try:
                # Get pipeline for this campaign
                container = ctx.container
                pipeline = container.get_pipeline(
                    campaign_id=campaign_id or f"batch_{i}",
                    no_cache=no_cache,
                    dry_run=dry_run
                )

                # Process campaign
                result = pipeline.process_campaign(
                    brief_file,
                    brand_guide_path=brand_guide,
                    resume=False
                )

                results.append({
                    "brief": brief_file,
                    "campaign_id": campaign_id,
                    "result": result
                })

                console.print(f"  [green]✓[/green] Completed: {campaign_id}")

            except Exception as e:
                failed.append({
                    "brief": brief_file,
                    "campaign_id": campaign_id,
                    "error": str(e)
                })
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

def _extract_campaign_id(brief_path: str) -> Optional[str]:
    """Extract campaign ID from brief file."""
    import json

    try:
        with open(brief_path) as f:
            brief_data = json.load(f)
        return brief_data.get("campaign_id")
    except:
        # Fallback to filename
        return Path(brief_path).stem


def _show_generation_plan(brief: str, brand_guide: Optional[str], dry_run: bool):
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
        ratios = creative_reqs.get("aspect_ratios", ["1x1", "9x16", "16x9"])
        variants = creative_reqs.get("variant_types", [])

        console.print()

        # Campaign info panel
        info_items = [
            f"[bold]Campaign:[/bold] {campaign_id}",
            f"[bold]Products:[/bold] {len(products)} ({', '.join(products[:3])}{'...' if len(products) > 3 else ''})",
            f"[bold]Regions:[/bold] {', '.join(regions)}",
            f"[bold]Aspect Ratios:[/bold] {', '.join(ratios)}",
            f"[bold]Variants:[/bold] {', '.join(variants) if variants else 'None specified'}"
        ]

        if brand_guide:
            info_items.append(f"[bold]Brand Guide:[/bold] {Path(brand_guide).name}")

        if dry_run:
            info_items.append("[yellow][bold]Mode:[/bold] Dry Run (Preview Only)[/yellow]")

        console.print(Panel(
            "\n".join(info_items),
            title="🎨 Generation Plan",
            border_style="cyan"
        ))

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
    console.print(f"[bold]Batch Processing Complete[/bold]")
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