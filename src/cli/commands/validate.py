"""
Validate command group - Validate briefs, brand guides, and configurations.

Provides validation patterns with comprehensive checks,
helpful error messages, and actionable recommendations.
"""

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.panel import Panel
from rich.table import Table

from ..constants import (
    BRIEF_REQUIRED_FIELDS,
    DEFAULT_CONFIG_FILENAME,
    DEFAULT_WORKSPACE_CONFIG_TEMPLATE,
    REQUIRED_BRAND_GUIDE_SECTIONS,
    REQUIRED_WORKSPACE_DIRS,
    SUPPORTED_ASPECT_RATIOS,
    SUPPORTED_REGIONS,
)
from ..core import pass_context
from ..utils.output import console, error_console


@click.group(invoke_without_command=True)
@click.argument("target", required=False)
@click.option("--fix", is_flag=True, help="Attempt to auto-fix common issues")
@click.option("--strict", is_flag=True, help="Enable strict validation (fail on warnings)")
@pass_context
def validate(ctx, target, fix, strict):
    """
    Validate briefs, brand guides, and configuration files.

    Performs comprehensive validation with helpful error messages and
    actionable recommendations for fixing issues.

    Examples:
        creatimation validate brief.json           # Auto-detect type
        creatimation validate brief brief.json     # Explicit brief validation
        creatimation validate config               # Validate workspace config
        creatimation validate --fix brief.json     # Auto-fix issues

    Validation Types:
        brief         Campaign brief JSON files
        brand-guide   Brand guide YAML files
        config        Workspace configuration
        workspace     Complete workspace validation
    """
    # If target provided without subcommand, auto-detect validation type
    click_ctx = click.get_current_context()
    if click_ctx.invoked_subcommand is None and target:
        # Check for special keywords first
        if target == "config":
            click_ctx.invoke(config, fix=fix, strict=strict)
            return
        elif target == "workspace":
            click_ctx.invoke(workspace, fix=fix, strict=strict)
            return

        # Auto-detect by file extension
        file_path = Path(target)
        if file_path.suffix == ".json":
            click_ctx.invoke(brief, brief_path=target, fix=fix, strict=strict)
        elif file_path.suffix in [".yml", ".yaml"]:
            click_ctx.invoke(brand_guide, guide_path=target, fix=fix, strict=strict)
        else:
            error_console.print(f"[red]✗[/red] Cannot auto-detect validation type for: {target}")
            console.print(
                "Use explicit subcommands: [cyan]brief[/cyan], [cyan]brand-guide[/cyan], or [cyan]config[/cyan]"
            )
            sys.exit(1)
    elif click_ctx.invoked_subcommand is None:
        # Show help when no arguments
        console.print()
        console.print("[yellow]No validation target specified.[/yellow]")
        console.print("See [cyan]creatimation validate --help[/cyan] for usage examples.")
        console.print()


@validate.command()
@click.argument("brief_path", type=click.Path(exists=True))
@click.option("--fix", is_flag=True, help="Attempt to auto-fix common issues")
@click.option(
    "--strict", is_flag=True, help="Fail on warnings (default: warnings are informational)"
)
@click.option("--schema", type=click.Path(exists=True), help="Custom JSON schema for validation")
@pass_context
def brief(ctx, brief_path, fix, strict, schema):
    """
    Validate campaign brief JSON file.

    Performs comprehensive validation including:
    - Required field checks
    - Data type validation
    - Business logic validation
    - Multi-region support verification
    - Creative requirements validation

    Examples:
        creatimation validate brief briefs/spring2025.json
        creatimation validate brief briefs/spring2025.json --fix
        creatimation validate brief briefs/spring2025.json --strict
    """
    try:
        console.print()
        console.print("[bold cyan]Validating Campaign Brief[/bold cyan]")
        console.print(f"File: {brief_path}")
        console.print()

        # Load and parse JSON
        try:
            with open(brief_path, encoding="utf-8") as f:
                brief_data = json.load(f)
        except json.JSONDecodeError as e:
            error_console.print(f"[red]✗[/red] Invalid JSON syntax: {e}")
            sys.exit(1)

        # Perform validation
        validation_result = _validate_brief_data(brief_data, brief_path)

        # Apply fixes if requested
        if fix and validation_result["fixable_issues"]:
            fixed_data = _apply_brief_fixes(brief_data, validation_result["fixable_issues"])

            # Save fixed version
            backup_path = f"{brief_path}.backup"
            Path(brief_path).rename(backup_path)

            with open(brief_path, "w", encoding="utf-8") as f:
                json.dump(fixed_data, f, indent=2)

            console.print(
                f"[green]✓[/green] Applied {len(validation_result['fixable_issues'])} fixes"
            )
            console.print(f"[dim]Original saved as: {backup_path}[/dim]")
            console.print()

            # Re-validate
            validation_result = _validate_brief_data(fixed_data, brief_path)

        # Display results
        _display_brief_validation_results(validation_result, brief_path)

        # Exit with appropriate code
        if validation_result["errors"]:
            sys.exit(1)
        elif strict and validation_result["warnings"]:
            sys.exit(1)
        else:
            console.print("[green]✓[/green] Brief validation completed successfully")
            console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Validation failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@validate.command(name="brand-guide")
@click.argument("guide_path", type=click.Path(exists=True))
@click.option("--fix", is_flag=True, help="Attempt to auto-fix common issues")
@click.option("--strict", is_flag=True, help="Fail on warnings")
@pass_context
def brand_guide(ctx, guide_path, fix, strict):
    """
    Validate brand guide YAML file.

    Checks brand guide structure, required fields, and validates
    color schemes, typography, and visual guidelines.

    Examples:
        creatimation validate brand-guide guides/minimal.yml
        creatimation validate brand-guide guides/minimal.yml --fix
        creatimation validate brand-guide guides/minimal.yml --strict
    """
    try:
        console.print()
        console.print("[bold cyan]Validating Brand Guide[/bold cyan]")
        console.print(f"File: {guide_path}")
        console.print()

        # Load brand guide using our loader
        container = ctx.container
        brand_guide_loader = container.get_brand_guide_loader()

        try:
            brand_guide_data = brand_guide_loader.load_brand_guide(guide_path)
        except Exception as e:
            error_console.print(f"[red]✗[/red] Failed to load brand guide: {e}")
            sys.exit(1)

        # Perform validation
        validation_result = _validate_brand_guide_data(brand_guide_data, guide_path)

        # Apply fixes if requested
        if fix and validation_result["fixable_issues"]:
            # Brand guide fixes would be implemented here
            console.print("[yellow]ℹ[/yellow] Auto-fix not yet implemented for brand guides")

        # Display results
        _display_brand_guide_validation_results(validation_result, guide_path)

        # Exit with appropriate code
        if validation_result["errors"]:
            sys.exit(1)
        elif strict and validation_result["warnings"]:
            sys.exit(1)
        else:
            console.print("[green]✓[/green] Brand guide validation completed successfully")
            console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Validation failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@validate.command()
@click.option("--fix", is_flag=True, help="Attempt to auto-fix configuration issues")
@click.option("--strict", is_flag=True, help="Fail on warnings")
@pass_context
def config(ctx, fix, strict):
    """
    Validate workspace configuration.

    Checks workspace structure, configuration files, and validates
    that all required components are properly configured.

    Examples:
        creatimation validate config
        creatimation validate config --fix
        creatimation validate config --strict
    """
    try:
        console.print()
        console.print("[bold cyan]Validating Workspace Configuration[/bold cyan]")
        console.print()

        # Check if we have a workspace
        if not ctx.workspace_manager:
            error_console.print("[red]✗[/red] No workspace found")
            console.print("Initialize a workspace with: [cyan]creatimation workspace init[/cyan]")
            sys.exit(1)

        workspace = ctx.workspace_manager
        validation_result = _validate_workspace_config(workspace)

        # Apply fixes if requested
        if fix and validation_result["fixable_issues"]:
            _apply_config_fixes(workspace, validation_result["fixable_issues"])
            console.print(
                f"[green]✓[/green] Applied {len(validation_result['fixable_issues'])} fixes"
            )
            console.print()

            # Re-validate
            validation_result = _validate_workspace_config(workspace)

        # Display results
        _display_config_validation_results(validation_result)

        # Exit with appropriate code
        if validation_result["errors"]:
            sys.exit(1)
        elif strict and validation_result["warnings"]:
            sys.exit(1)
        else:
            console.print("[green]✓[/green] Configuration validation completed successfully")
            console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Validation failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@validate.command()
@click.option("--fix", is_flag=True, help="Attempt to auto-fix all workspace issues")
@click.option("--strict", is_flag=True, help="Fail on any warnings")
@pass_context
def workspace(ctx, fix, strict):
    """
    Validate complete workspace setup.

    Performs comprehensive validation of the entire workspace including:
    - Workspace structure and files
    - Configuration validity
    - Available briefs and brand guides
    - Output directory structure
    - Cache setup

    Examples:
        creatimation validate workspace
        creatimation validate workspace --fix
        creatimation validate workspace --strict
    """
    try:
        console.print()
        console.print("[bold cyan]Validating Complete Workspace[/bold cyan]")
        console.print()

        # Validate workspace exists
        if not ctx.workspace_manager:
            error_console.print("[red]✗[/red] No workspace found")
            console.print("Initialize a workspace with: [cyan]creatimation workspace init[/cyan]")
            sys.exit(1)

        workspace = ctx.workspace_manager
        validation_results = _validate_complete_workspace(workspace, ctx.container)

        # Apply fixes if requested
        total_fixes = 0
        if fix:
            for component, result in validation_results.items():
                if result.get("fixable_issues"):
                    _apply_workspace_component_fixes(workspace, component, result["fixable_issues"])
                    total_fixes += len(result["fixable_issues"])

            if total_fixes > 0:
                console.print(f"[green]✓[/green] Applied {total_fixes} fixes across workspace")
                console.print()

                # Re-validate
                validation_results = _validate_complete_workspace(workspace, ctx.container)

        # Display comprehensive results
        _display_workspace_validation_results(validation_results)

        # Calculate overall status
        total_errors = sum(len(result.get("errors", [])) for result in validation_results.values())
        total_warnings = sum(
            len(result.get("warnings", [])) for result in validation_results.values()
        )

        if total_errors > 0:
            sys.exit(1)
        elif strict and total_warnings > 0:
            sys.exit(1)
        else:
            console.print("[green]✓[/green] Workspace validation completed successfully")
            console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Validation failed: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


# ============================================================================
# VALIDATION LOGIC
# ============================================================================


def _validate_brief_data(brief_data: dict[str, Any], file_path: str) -> dict[str, Any]:
    """Validate campaign brief data structure and content."""
    errors = []
    warnings = []
    fixable_issues = []
    info = []

    # Required fields validation
    required_fields = BRIEF_REQUIRED_FIELDS

    for field in required_fields:
        if field not in brief_data:
            errors.append(f"Missing required field: {field}")
        elif not brief_data[field]:
            errors.append(f"Required field is empty: {field}")

    # Products validation
    products = brief_data.get("products", [])
    if isinstance(products, list):
        if len(products) == 0:
            errors.append("No products specified")
        elif len(products) == 1:
            warnings.append("Only one product specified - consider adding more for variety")

        info.append(f"Products count: {len(products)}")
    else:
        errors.append("Products must be a list")

    # Target regions validation
    regions = brief_data.get("target_regions", [])
    if isinstance(regions, list):
        if len(regions) == 0:
            errors.append("No target regions specified")

        # Check for supported regions
        unsupported = [r for r in regions if r not in SUPPORTED_REGIONS]
        if unsupported:
            warnings.append(
                f"Unsupported regions (may need custom handling): {', '.join(unsupported)}"
            )

        info.append(f"Target regions: {', '.join(regions)}")
    else:
        errors.append("Target regions must be a list")

    # Creative requirements validation
    creative_reqs = brief_data.get("creative_requirements", {})
    if creative_reqs:
        # Aspect ratios
        ratios = creative_reqs.get("aspect_ratios", [])
        if ratios:
            unsupported_ratios = [r for r in ratios if r not in SUPPORTED_ASPECT_RATIOS]
            if unsupported_ratios:
                warnings.append(f"Unsupported aspect ratios: {', '.join(unsupported_ratios)}")
            info.append(f"Aspect ratios: {', '.join(ratios)}")

        # Variant types
        variants = creative_reqs.get("variant_types", [])
        if variants:
            info.append(f"Variant types: {', '.join(variants)}")

        # Variant themes
        variant_themes = creative_reqs.get("variant_themes", {})
        if variant_themes:
            info.append(f"Themed variants: {len(variant_themes)}")

    # Enhanced context validation
    enhanced_context = brief_data.get("enhanced_context", {})
    if enhanced_context:
        # Brand colors validation
        brand_colors = enhanced_context.get("brand_colors", {})
        if brand_colors:
            primary = brand_colors.get("primary")
            if primary and not primary.startswith("#"):
                warnings.append("Primary brand color should be a hex color code (e.g., #1234AB)")
            info.append("Brand colors configured")

    # Regional adaptations validation
    regional_adaptations = brief_data.get("regional_adaptations", {})
    if regional_adaptations:
        for region in regions:
            if region not in regional_adaptations:
                warnings.append(f"No regional adaptation for {region} - will use default messaging")
        info.append(f"Regional adaptations: {len(regional_adaptations)}")

    return {
        "errors": errors,
        "warnings": warnings,
        "fixable_issues": fixable_issues,
        "info": info,
        "valid": len(errors) == 0,
    }


def _validate_brand_guide_data(brand_guide_data: dict[str, Any], file_path: str) -> dict[str, Any]:
    """Validate brand guide data structure and content."""
    errors = []
    warnings = []
    fixable_issues = []
    info = []

    # Basic structure validation
    required_sections = REQUIRED_BRAND_GUIDE_SECTIONS
    for section in required_sections:
        if section not in brand_guide_data:
            errors.append(f"Missing required section: {section}")

    # Brand section validation
    brand_section = brand_guide_data.get("brand", {})
    if brand_section:
        if not brand_section.get("name"):
            errors.append("Brand name is required")
        else:
            info.append(f"Brand: {brand_section['name']}")

        industry = brand_section.get("industry")
        if industry:
            info.append(f"Industry: {industry}")

    # Colors validation
    colors_section = brand_guide_data.get("colors", {})
    if colors_section:
        primary = colors_section.get("primary")
        if primary:
            if not primary.startswith("#"):
                warnings.append("Primary color should be a hex color code")
            info.append(f"Primary color: {primary}")

        secondary = colors_section.get("secondary")
        if secondary:
            info.append(f"Secondary color: {secondary}")

    # Visual guidelines validation
    visual_section = brand_guide_data.get("visual", {})
    if visual_section:
        layout_style = visual_section.get("layout_style")
        if layout_style:
            info.append(f"Layout style: {layout_style}")

    # Messaging validation
    messaging_section = brand_guide_data.get("messaging", {})
    if messaging_section:
        tone = messaging_section.get("tone")
        if tone:
            info.append(f"Brand tone: {tone}")

    return {
        "errors": errors,
        "warnings": warnings,
        "fixable_issues": fixable_issues,
        "info": info,
        "valid": len(errors) == 0,
    }


def _validate_workspace_config(workspace_manager) -> dict[str, Any]:
    """Validate workspace configuration."""
    errors = []
    warnings = []
    fixable_issues = []
    info = []

    # Check workspace structure
    workspace_path = workspace_manager.workspace_path

    # Required directories
    required_dirs = REQUIRED_WORKSPACE_DIRS
    for dir_name in required_dirs:
        dir_path = workspace_path / dir_name
        if not dir_path.exists():
            fixable_issues.append(f"create_directory:{dir_name}")
            warnings.append(f"Missing directory: {dir_name}")
        else:
            info.append(f"Directory exists: {dir_name}")

    # Configuration file
    config_file = workspace_path / DEFAULT_CONFIG_FILENAME
    if not config_file.exists():
        warnings.append("No workspace configuration file found")
        fixable_issues.append("create_config_file")
    else:
        info.append("Configuration file exists")

    return {
        "errors": errors,
        "warnings": warnings,
        "fixable_issues": fixable_issues,
        "info": info,
        "valid": len(errors) == 0,
    }


def _validate_complete_workspace(workspace_manager, container) -> dict[str, dict[str, Any]]:
    """Validate complete workspace setup."""
    results = {}

    # Validate configuration
    results["configuration"] = _validate_workspace_config(workspace_manager)

    # Validate cache setup
    results["cache"] = _validate_cache_setup(container.get_cache_manager())

    # Validate output setup
    results["output"] = _validate_output_setup(container.get_output_manager())

    # Validate available content
    results["content"] = _validate_workspace_content(workspace_manager)

    return results


def _validate_cache_setup(cache_manager) -> dict[str, Any]:
    """Validate cache manager setup."""
    errors = []
    warnings = []
    fixable_issues = []
    info = []

    try:
        # Test cache functionality
        cache_manager.get("test_key")
        info.append("Cache manager operational")
    except Exception as e:
        errors.append(f"Cache manager error: {e}")

    return {
        "errors": errors,
        "warnings": warnings,
        "fixable_issues": fixable_issues,
        "info": info,
        "valid": len(errors) == 0,
    }


def _validate_output_setup(output_manager) -> dict[str, Any]:
    """Validate output manager setup."""
    errors = []
    warnings = []
    fixable_issues = []
    info = []

    try:
        # Check output directory
        output_dir = getattr(output_manager, "output_dir", None)
        if output_dir and Path(output_dir).exists():
            info.append(f"Output directory: {output_dir}")
        else:
            warnings.append("Output directory not accessible")
    except Exception as e:
        errors.append(f"Output manager error: {e}")

    return {
        "errors": errors,
        "warnings": warnings,
        "fixable_issues": fixable_issues,
        "info": info,
        "valid": len(errors) == 0,
    }


def _validate_workspace_content(workspace_manager) -> dict[str, Any]:
    """Validate workspace content availability."""
    errors = []
    warnings = []
    fixable_issues = []
    info = []

    workspace_path = workspace_manager.workspace_path

    # Check for briefs
    briefs_dir = workspace_path / "briefs"
    if briefs_dir.exists():
        brief_files = list(briefs_dir.glob("*.json"))
        if brief_files:
            info.append(f"Campaign briefs: {len(brief_files)}")
        else:
            warnings.append("No campaign briefs found")

    # Check for brand guides
    guides_dir = workspace_path / "brand-guides"
    if guides_dir.exists():
        guide_files = list(guides_dir.glob("*.yml")) + list(guides_dir.glob("*.yaml"))
        if guide_files:
            info.append(f"Brand guides: {len(guide_files)}")
        else:
            warnings.append("No brand guides found")

    return {
        "errors": errors,
        "warnings": warnings,
        "fixable_issues": fixable_issues,
        "info": info,
        "valid": len(errors) == 0,
    }


# ============================================================================
# FIX FUNCTIONS
# ============================================================================


def _apply_brief_fixes(brief_data: dict[str, Any], fixable_issues: list[str]) -> dict[str, Any]:
    """Apply automatic fixes to brief data."""
    fixed_data = brief_data.copy()

    # Implement fixes based on fixable_issues
    # This would contain logic to fix common brief issues

    return fixed_data


def _apply_config_fixes(workspace_manager, fixable_issues: list[str]) -> None:
    """Apply automatic fixes to workspace configuration."""
    workspace_path = workspace_manager.workspace_path

    for issue in fixable_issues:
        if issue.startswith("create_directory:"):
            dir_name = issue.split(":", 1)[1]
            (workspace_path / dir_name).mkdir(exist_ok=True)
        elif issue == "create_config_file":
            # Create basic config file
            config_content = DEFAULT_WORKSPACE_CONFIG_TEMPLATE
            config_file = workspace_path / DEFAULT_CONFIG_FILENAME
            config_file.write_text(config_content)


def _apply_workspace_component_fixes(
    workspace_manager, component: str, fixable_issues: list[str]
) -> None:
    """Apply fixes for specific workspace components."""
    if component == "configuration":
        _apply_config_fixes(workspace_manager, fixable_issues)
    # Add other component fixes as needed


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================


def _display_brief_validation_results(result: dict[str, Any], file_path: str):
    """Display brief validation results."""
    # Summary panel
    status = "✓ Valid" if result["valid"] else "✗ Invalid"
    status_color = "green" if result["valid"] else "red"

    summary = f"[{status_color}]{status}[/{status_color}]"
    if result["errors"]:
        summary += f" • {len(result['errors'])} errors"
    if result["warnings"]:
        summary += f" • {len(result['warnings'])} warnings"

    console.print(Panel(summary, title="Brief Validation", border_style="cyan"))
    console.print()

    # Errors table
    if result["errors"]:
        error_table = Table(title="Errors", show_header=False, box=None)
        error_table.add_column("", style="red")
        for error in result["errors"]:
            error_table.add_row(f"✗ {error}")
        console.print(error_table)
        console.print()

    # Warnings table
    if result["warnings"]:
        warning_table = Table(title="Warnings", show_header=False, box=None)
        warning_table.add_column("", style="yellow")
        for warning in result["warnings"]:
            warning_table.add_row(f"⚠ {warning}")
        console.print(warning_table)
        console.print()

    # Info table
    if result["info"]:
        info_table = Table(title="Brief Information", show_header=True)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")

        for info_item in result["info"]:
            if ": " in info_item:
                prop, value = info_item.split(": ", 1)
                info_table.add_row(prop, value)
            else:
                info_table.add_row("Info", info_item)

        console.print(info_table)
        console.print()


def _display_brand_guide_validation_results(result: dict[str, Any], file_path: str):
    """Display brand guide validation results."""
    status = "✓ Valid" if result["valid"] else "✗ Invalid"
    status_color = "green" if result["valid"] else "red"

    summary = f"[{status_color}]{status}[/{status_color}]"
    if result["errors"]:
        summary += f" • {len(result['errors'])} errors"
    if result["warnings"]:
        summary += f" • {len(result['warnings'])} warnings"

    console.print(Panel(summary, title="Brand Guide Validation", border_style="cyan"))
    console.print()

    # Display errors and warnings similar to brief validation
    if result["errors"]:
        for error in result["errors"]:
            console.print(f"[red]✗[/red] {error}")
        console.print()

    if result["warnings"]:
        for warning in result["warnings"]:
            console.print(f"[yellow]⚠[/yellow] {warning}")
        console.print()

    if result["info"]:
        for info_item in result["info"]:
            console.print(f"[dim]ℹ[/dim] {info_item}")
        console.print()


def _display_config_validation_results(result: dict[str, Any]):
    """Display configuration validation results."""
    status = "✓ Valid" if result["valid"] else "✗ Invalid"
    status_color = "green" if result["valid"] else "red"

    console.print(
        Panel(
            f"[{status_color}]{status}[/{status_color}]",
            title="Configuration Validation",
            border_style="cyan",
        )
    )
    console.print()

    if result["errors"]:
        for error in result["errors"]:
            console.print(f"[red]✗[/red] {error}")
        console.print()

    if result["warnings"]:
        for warning in result["warnings"]:
            console.print(f"[yellow]⚠[/yellow] {warning}")
        console.print()

    if result["info"]:
        for info_item in result["info"]:
            console.print(f"[green]✓[/green] {info_item}")
        console.print()


def _display_workspace_validation_results(results: dict[str, dict[str, Any]]):
    """Display comprehensive workspace validation results."""
    # Overall status
    total_errors = sum(len(result.get("errors", [])) for result in results.values())
    total_warnings = sum(len(result.get("warnings", [])) for result in results.values())

    if total_errors == 0:
        status = "✓ Valid"
        status_color = "green"
    else:
        status = "✗ Invalid"
        status_color = "red"

    summary = f"[{status_color}]{status}[/{status_color}]"
    if total_errors:
        summary += f" • {total_errors} errors"
    if total_warnings:
        summary += f" • {total_warnings} warnings"

    console.print(Panel(summary, title="Workspace Validation", border_style="cyan"))
    console.print()

    # Component results
    for component, result in results.items():
        component_title = component.replace("_", " ").title()

        if result["errors"] or result["warnings"]:
            console.print(f"[bold]{component_title}[/bold]")

            for error in result.get("errors", []):
                console.print(f"  [red]✗[/red] {error}")

            for warning in result.get("warnings", []):
                console.print(f"  [yellow]⚠[/yellow] {warning}")

            console.print()

        elif result["info"]:
            console.print(f"[bold green]✓[/bold green] {component_title}")
            for info_item in result["info"]:
                console.print(f"  [dim]{info_item}[/dim]")
            console.print()
