"""
Config command group - Manage configuration and settings.

Provides configuration management with global and workspace
settings, profile support, and environment-specific configurations.
"""

import os
import sys
from pathlib import Path
from typing import Any

import click
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from ..constants import (
    CONFIG_TEMPLATES,
    CONFIG_OUTPUT_FORMATS,
    CONFIG_VALUE_TYPES,
    REQUIRED_CONFIG_SECTIONS,
    GLOBAL_CONFIG_DIR,
    GLOBAL_CONFIG_FILENAME,
    get_template_config,
    DEFAULT_CONFIG_VALUES,
    ENV_PREFIX,
)
from ..core import pass_context
from ..utils.output import console, error_console


@click.group(invoke_without_command=True)
@click.option("--global", "-g", "is_global", is_flag=True, help="Operate on global configuration")
@click.option("--list", "-l", is_flag=True, help="List all configuration values")
@pass_context
def config(ctx, is_global, list):
    """
    Manage configuration and settings.

    Handles both global and workspace-specific configuration with support
    for profiles, environment variables, and hierarchical settings.

    Configuration Hierarchy (highest to lowest priority):
    1. Command line flags
    2. Environment variables (CREATIMATION_*)
    3. Workspace configuration (.creatimation.yml)
    4. Global user configuration (~/.creatimation/config.yml)
    5. Default values

    Examples:
        creatimation config list
        creatimation config set cache.enabled true
        creatimation config get generation.variants
        creatimation config --global set auth.api_key abc123

    Config Commands:
        init        Create configuration template
        list        List all configuration values
        get         Get specific configuration value
        set         Set configuration value
        unset       Remove configuration value
        show        Show effective configuration
        validate    Validate configuration files
        reset       Reset configuration to defaults
    """
    # Get the Click context to check for subcommands
    click_ctx = click.get_current_context()

    if list:
        click_ctx.invoke(list_config, is_global=is_global)
    elif click_ctx.invoked_subcommand is None:
        # Show current config summary
        click_ctx.invoke(show, is_global=is_global)


@config.command()
@click.option("--global", "-g", "is_global", is_flag=True, help="Create global configuration")
@click.option(
    "--template",
    type=click.Choice(CONFIG_TEMPLATES),
    default="complete",
    help="Configuration template",
)
@click.option("--force", is_flag=True, help="Overwrite existing configuration")
@pass_context
def init(ctx, is_global, template, force):
    """
    Create configuration template.

    Generates a configuration file with defaults and documentation
    based on the selected template.

    Templates:
        minimal     Essential settings only
        complete    All available settings with documentation
        cpg         Consumer Packaged Goods optimized settings
        fashion     Fashion industry optimized settings
        tech        Technology company optimized settings

    Examples:
        creatimation config init
        creatimation config init --global --template minimal
        creatimation config init --template cpg --force
    """
    try:
        # Determine config file path
        if is_global:
            config_dir = Path.home() / GLOBAL_CONFIG_DIR
            config_file = config_dir / GLOBAL_CONFIG_FILENAME
            config_dir.mkdir(exist_ok=True)
        else:
            # Check if we're in a workspace directory (has briefs/ and brand-guides/)
            current = Path.cwd()
            if (current / "briefs").exists() and (current / "brand-guides").exists():
                # This is a valid workspace location, create WorkspaceManager directly
                from ..utils.workspace import WorkspaceManager

                ctx.workspace_manager = WorkspaceManager(current)
                ctx.workspace_path = current
                config_file = current / ".creatimation.yml"
            else:
                error_console.print("[red]✗[/red] No workspace found")
                console.print(
                    "This directory needs [cyan]briefs/[/cyan] and [cyan]brand-guides/[/cyan] directories"
                )
                console.print("Or run with [cyan]--global[/cyan] flag for global configuration")
                sys.exit(1)

        # Check if file exists
        if config_file.exists() and not force:
            if not Confirm.ask(f"Configuration file exists at {config_file}. Overwrite?"):
                console.print("Configuration creation cancelled.")
                return

        # Generate configuration content
        config_content = _get_config_template(template, is_global)

        # Write configuration file
        config_file.write_text(config_content)

        console.print()
        console.print(f"[green]✓[/green] Created configuration: [cyan]{config_file}[/cyan]")
        console.print(f"Template: {template}")

        if is_global:
            console.print("[dim]Global configuration affects all workspaces[/dim]")
        else:
            console.print("[dim]Workspace configuration overrides global settings[/dim]")

        console.print()
        console.print("Next steps:")
        console.print("  1. [cyan]./creatimation config validate[/cyan] - Validate configuration")
        console.print("  2. [cyan]./creatimation config show[/cyan] - View effective settings")
        console.print(f"  3. Edit {config_file} to customize settings")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to create configuration: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@config.command(name="list")
@click.option("--global", "-g", "is_global", is_flag=True, help="List global configuration only")
@click.option(
    "--format",
    type=click.Choice(CONFIG_OUTPUT_FORMATS),
    default="table",
    help="Output format",
)
@pass_context
def list_config(ctx, is_global, format):
    """
    List all configuration values.

    Shows the effective configuration with source information,
    helping understand where each setting comes from.

    Examples:
        creatimation config list
        creatimation config list --global
        creatimation config list --format yaml
        creatimation config list --format env
    """
    try:
        console.print()

        if is_global:
            config_data = _get_global_config()
            title = "Global Configuration"
        else:
            config_data = _get_effective_config(ctx)
            title = "Effective Configuration"

        if format == "table":
            _display_config_table(config_data, title)
        elif format == "yaml":
            _display_config_yaml(config_data)
        elif format == "json":
            _display_config_json(config_data)
        elif format == "env":
            _display_config_env(config_data)

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to list configuration: {e}")
        sys.exit(1)


@config.command()
@click.argument("key")
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Get from global configuration only"
)
@click.option("--source", is_flag=True, help="Show configuration source")
@pass_context
def get(ctx, key, is_global, source):
    """
    Get specific configuration value.

    Retrieves a configuration value by key, with support for
    nested keys using dot notation.

    Examples:
        creatimation config get generation.variants
        creatimation config get cache.enabled --source
        creatimation config get --global auth.api_key
    """
    try:
        if is_global:
            config_data = _get_global_config()
            config_source = "global"
        else:
            config_data, sources = _get_effective_config_with_sources(ctx)
            config_source = sources.get(key, "default")

        # Get nested value using dot notation
        value = _get_nested_value(config_data, key)

        if value is None:
            error_console.print(f"[red]✗[/red] Configuration key not found: {key}")
            sys.exit(1)

        console.print()
        console.print(f"[cyan]{key}[/cyan]: [green]{value}[/green]")

        if source:
            console.print(f"[dim]Source: {config_source}[/dim]")

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to get configuration: {e}")
        sys.exit(1)


@config.command()
@click.argument("key")
@click.argument("value")
@click.option("--global", "-g", "is_global", is_flag=True, help="Set in global configuration")
@click.option(
    "--type",
    type=click.Choice(CONFIG_VALUE_TYPES),
    help="Value type (auto-detected if not specified)",
)
@pass_context
def set(ctx, key, value, is_global, type):
    """
    Set configuration value.

    Sets a configuration value with automatic type detection
    or explicit type specification.

    Examples:
        creatimation config set generation.variants 5
        creatimation config set cache.enabled true --type bool
        creatimation config set --global auth.api_key abc123
        creatimation config set generation.aspect_ratios "1x1,9x16,16x9" --type list
    """
    try:
        # Determine target configuration file
        if is_global:
            config_dir = Path.home() / ".creatimation"
            config_file = config_dir / "config.yml"
            config_dir.mkdir(exist_ok=True)
        else:
            if not ctx.workspace_manager:
                error_console.print("[red]✗[/red] No workspace found")
                console.print("Run in a workspace or use [cyan]--global[/cyan] flag")
                sys.exit(1)

            config_file = ctx.workspace_manager.workspace_path / ".creatimation.yml"

        # Load existing configuration
        if config_file.exists():
            import yaml

            with open(config_file) as f:
                config_data = yaml.safe_load(f) or {}
        else:
            config_data = {}

        # Convert value to appropriate type
        typed_value = _convert_value(value, type)

        # Set nested value using dot notation
        _set_nested_value(config_data, key, typed_value)

        # Save configuration
        import yaml

        with open(config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        console.print()
        console.print(f"[green]✓[/green] Set [cyan]{key}[/cyan] = [green]{typed_value}[/green]")

        scope = "global" if is_global else "workspace"
        console.print(f"[dim]Scope: {scope}[/dim]")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to set configuration: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@config.command()
@click.argument("key")
@click.option("--global", "-g", "is_global", is_flag=True, help="Remove from global configuration")
@pass_context
def unset(ctx, key, is_global):
    """
    Remove configuration value.

    Removes a configuration key and its value from the
    specified configuration file.

    Examples:
        creatimation config unset generation.variants
        creatimation config unset --global auth.api_key
    """
    try:
        # Determine target configuration file
        if is_global:
            config_file = Path.home() / ".creatimation" / "config.yml"
        else:
            if not ctx.workspace_manager:
                error_console.print("[red]✗[/red] No workspace found")
                sys.exit(1)

            config_file = ctx.workspace_manager.workspace_path / ".creatimation.yml"

        if not config_file.exists():
            error_console.print(f"[red]✗[/red] Configuration file not found: {config_file}")
            sys.exit(1)

        # Load configuration
        import yaml

        with open(config_file) as f:
            config_data = yaml.safe_load(f) or {}

        # Remove nested value
        if _unset_nested_value(config_data, key):
            # Save configuration
            with open(config_file, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            console.print()
            console.print(f"[green]✓[/green] Removed [cyan]{key}[/cyan]")

            scope = "global" if is_global else "workspace"
            console.print(f"[dim]Scope: {scope}[/dim]")
            console.print()
        else:
            error_console.print(f"[red]✗[/red] Configuration key not found: {key}")
            sys.exit(1)

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to unset configuration: {e}")
        sys.exit(1)


@config.command()
@click.option("--global", "-g", "is_global", is_flag=True, help="Show global configuration only")
@click.option("--sources", is_flag=True, help="Show configuration sources")
@click.option("--campaigns", is_flag=True, help="Show detected campaigns and briefs")
@pass_context
def show(ctx, is_global, sources, campaigns):
    """
    Show dynamic workspace configuration.

    Displays the merged configuration from all sources plus
    detected campaigns, briefs, and brand guides in workspace.

    Examples:
        creatimation config show
        creatimation config show --campaigns
        creatimation config show --sources
        creatimation config show --global
    """
    try:
        console.print()

        if is_global:
            config_data = _get_global_config()
            console.print(Panel("Global Configuration", style="cyan"))
            _display_config_yaml(config_data)
        elif campaigns:
            _display_workspace_campaigns(ctx)
        else:
            if sources:
                config_data, source_info = _get_effective_config_with_sources(ctx)
                console.print(Panel("Effective Configuration with Sources", style="cyan"))
                _display_config_with_sources(config_data, source_info)
            else:
                # Show unified view: global + local + campaigns
                _display_unified_configuration(ctx)

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to show configuration: {e}")
        sys.exit(1)


@config.command()
@click.option(
    "--global", "-g", "is_global", is_flag=True, help="Validate global configuration only"
)
@click.option("--fix", is_flag=True, help="Attempt to fix validation issues")
@pass_context
def validate(ctx, is_global, fix):
    """
    Validate configuration files.

    Checks configuration syntax, required fields, and validates
    values against expected types and ranges.

    Examples:
        creatimation config validate
        creatimation config validate --global
        creatimation config validate --fix
    """
    try:
        console.print()
        console.print("[bold cyan]Validating Configuration[/bold cyan]")
        console.print()

        validation_results = []

        if is_global:
            # Validate global config only
            global_result = _validate_global_config()
            validation_results.append(("Global", global_result))
        else:
            # Validate all relevant configs
            global_result = _validate_global_config()
            validation_results.append(("Global", global_result))

            if ctx.workspace_manager:
                workspace_result = _validate_workspace_config_file(ctx.workspace_manager)
                validation_results.append(("Workspace", workspace_result))

        # Display results
        total_errors = 0
        total_warnings = 0

        for config_type, result in validation_results:
            _display_validation_result(config_type, result)
            total_errors += len(result.get("errors", []))
            total_warnings += len(result.get("warnings", []))

        # Apply fixes if requested
        if fix and total_errors > 0:
            console.print("[yellow]Auto-fix functionality not yet implemented[/yellow]")

        # Summary
        if total_errors == 0:
            console.print("[bold green]✓ All configurations are valid[/bold green]")
        else:
            console.print(
                f"[bold red]✗ Found {total_errors} errors and {total_warnings} warnings[/bold red]"
            )
            sys.exit(1)

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Configuration validation failed: {e}")
        sys.exit(1)


@config.command()
@click.option("--global", "-g", "is_global", is_flag=True, help="Reset global configuration")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@pass_context
def reset(ctx, is_global, force):
    """
    Reset configuration to defaults.

    Removes the current configuration file and recreates it
    with default values.

    Examples:
        creatimation config reset
        creatimation config reset --global --force
    """
    try:
        # Determine config file
        if is_global:
            config_file = Path.home() / ".creatimation" / "config.yml"
            scope = "global"
        else:
            if not ctx.workspace_manager:
                error_console.print("[red]✗[/red] No workspace found")
                sys.exit(1)

            config_file = ctx.workspace_manager.workspace_path / ".creatimation.yml"
            scope = "workspace"

        # Confirmation
        if not force:
            console.print()
            console.print(
                f"[bold red]Warning: This will reset {scope} configuration to defaults![/bold red]"
            )
            console.print(f"File: {config_file}")
            console.print()

            if not Confirm.ask("Continue?"):
                console.print("Reset cancelled.")
                return

        # Remove existing file
        if config_file.exists():
            config_file.unlink()

        # Recreate with defaults
        click_ctx = click.get_current_context()
        click_ctx.invoke(init, is_global=is_global, template="complete", force=True)

        console.print(f"[green]✓[/green] Reset {scope} configuration to defaults")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to reset configuration: {e}")
        sys.exit(1)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _get_config_template(template: str, is_global: bool) -> str:
    """Generate configuration template based on type."""
    import yaml

    if is_global:
        config = _get_global_config_template(template)
    else:
        config = _get_workspace_config_template(template)

    return yaml.dump(config, default_flow_style=False, sort_keys=False)


def _get_global_config_template(template: str) -> dict[str, Any]:
    """Generate global configuration template."""
    config = {
        "# Global Creatimation Configuration": None,
        "# This configuration applies to all workspaces": None,
        "auth": {
            "# API keys and authentication": None,
            "gemini_api_key": "${GEMINI_API_KEY}",
            "s3_access_key": "${AWS_ACCESS_KEY_ID}",
            "s3_secret_key": "${AWS_SECRET_ACCESS_KEY}",
        },
        "defaults": {
            "# Default settings for new workspaces": None,
            "generation": {
                "variants_per_ratio": 3,
                "aspect_ratios": ["1x1", "9x16", "16x9"],
                "quality": 95,
            },
            "cache": {"enabled": True, "max_size_gb": 10, "cleanup_after_days": 30},
            "output": {"format": "jpg", "semantic_structure": True},
        },
    }

    if template == "minimal":
        # Remove comments and optional sections
        config = {
            "auth": {"gemini_api_key": "${GEMINI_API_KEY}"},
            "defaults": {"generation": {"variants_per_ratio": 3}},
        }

    return config


def _get_workspace_config_template(template: str) -> dict[str, Any]:
    """Generate workspace configuration template."""
    # Try to detect existing campaigns to create appropriate config
    try:
        import json
        from pathlib import Path

        workspace_path = Path.cwd()
        briefs_dir = workspace_path / "briefs"

        # Look for existing campaign to base config on
        campaign_data = None
        if briefs_dir.exists():
            for brief_file in briefs_dir.glob("*.json"):
                try:
                    with open(brief_file) as f:
                        campaign_data = json.load(f)
                    break  # Use first valid campaign found
                except Exception:
                    continue

        if campaign_data:
            # Extract brand and industry from the detected campaign
            products = campaign_data.get("products", [])
            brand = "My Brand"
            industry = "consumer-goods"
            if products and isinstance(products[0], dict):
                product_name = products[0].get("name", "")
                if product_name:
                    brand = product_name.split()[0]
                industry = products[0].get("category", "Unknown")

            # Count total campaigns for project naming
            campaign_count = 0
            if briefs_dir.exists():
                campaign_count = len(list(briefs_dir.glob("*.json")))

            # Create project name based on campaign count
            if campaign_count == 1:
                project_name = campaign_data.get("campaign_name", f"{brand} Creative Project")
            else:
                project_name = f"{brand} Campaign Portfolio ({campaign_count} campaigns)"

            creative_req = campaign_data.get("creative_requirements", {})
            base_config = {
                "# Workspace Configuration": None,
                "project": {"name": project_name, "brand": brand, "industry": industry},
                "generation": {
                    "# Generation settings": None,
                    "default_variants": creative_req.get("variants_per_ratio", 3),
                    "aspect_ratios": creative_req.get("aspect_ratios", ["1x1", "9x16", "16x9"]),
                    "variant_types": creative_req.get(
                        "variant_types", ["base", "color_shift", "text_style"]
                    ),
                    "quality": 95,
                },
                "cache": {"# Cache configuration": None, "enabled": True, "directory": "cache"},
                "output": {
                    "# Output configuration": None,
                    "directory": "output",
                    "semantic_structure": True,
                    "format": "jpg",
                },
            }
        else:
            # Fallback to default template
            base_config = {
                "# Workspace Configuration": None,
                "project": {
                    "name": "My Creative Project",
                    "brand": "My Brand",
                    "industry": "consumer-goods",
                },
                "generation": {
                    "# Generation settings": None,
                    "default_variants": 3,
                    "aspect_ratios": ["1x1", "9x16", "16x9"],
                    "variant_types": ["base", "color_shift", "premium"],
                    "quality": 95,
                },
                "cache": {"# Cache configuration": None, "enabled": True, "directory": "cache"},
                "output": {
                    "# Output configuration": None,
                    "directory": "output",
                    "semantic_structure": True,
                    "format": "jpg",
                },
            }
    except Exception:
        # Fallback to default if detection fails
        base_config = {
            "# Workspace Configuration": None,
            "project": {
                "name": "My Creative Project",
                "brand": "My Brand",
                "industry": "consumer-goods",
            },
            "generation": {
                "# Generation settings": None,
                "default_variants": 3,
                "aspect_ratios": ["1x1", "9x16", "16x9"],
                "variant_types": ["base", "color_shift", "premium"],
                "quality": 95,
            },
            "cache": {"# Cache configuration": None, "enabled": True, "directory": "cache"},
            "output": {
                "# Output configuration": None,
                "directory": "output",
                "semantic_structure": True,
                "format": "jpg",
            },
        }

    # Template-specific modifications
    if template == "cpg":
        base_config["generation"]["aspect_ratios"] = ["1x1", "9x16", "16x9", "4x5", "5x4"]
        base_config["generation"]["default_variants"] = 5
        base_config["project"]["industry"] = "consumer-packaged-goods"

    elif template == "fashion":
        base_config["generation"]["aspect_ratios"] = ["9x16", "4x5", "1x1"]
        base_config["generation"]["variant_types"] = ["elegant", "casual", "bold"]
        base_config["project"]["industry"] = "fashion"

    elif template == "tech":
        base_config["generation"]["aspect_ratios"] = ["16x9", "1x1", "9x16"]
        base_config["generation"]["variant_types"] = ["professional", "consumer", "enterprise"]
        base_config["project"]["industry"] = "technology"

    elif template == "minimal":
        base_config = {
            "project": {"name": "My Project"},
            "generation": {"default_variants": 3},
            "output": {"directory": "output"},
        }

    return base_config


def _get_global_config() -> dict[str, Any]:
    """Load global configuration."""
    config_file = Path.home() / GLOBAL_CONFIG_DIR / GLOBAL_CONFIG_FILENAME

    if not config_file.exists():
        return {}

    try:
        import yaml

        with open(config_file) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_effective_config(ctx) -> dict[str, Any]:
    """Get effective configuration from all sources."""
    config, _ = _get_effective_config_with_sources(ctx)
    return config


def _get_effective_config_with_sources(ctx) -> tuple[dict[str, Any], dict[str, str]]:
    """Get effective configuration with source tracking."""
    config = {}
    sources = {}

    # 1. Start with defaults
    _merge_config(config, _get_default_config(), sources, "default")

    # 2. Apply global config
    global_config = _get_global_config()
    if global_config:
        _merge_config(config, global_config, sources, "global")

    # 3. Apply workspace config
    if ctx.workspace_manager:
        workspace_config = ctx.workspace_manager.get_config()
        if workspace_config:
            _merge_config(config, workspace_config, sources, "workspace")

    # 4. Apply environment variables
    env_config = _get_env_config()
    if env_config:
        _merge_config(config, env_config, sources, "environment")

    return config, sources


def _get_default_config() -> dict[str, Any]:
    """Get default configuration values."""
    config = DEFAULT_CONFIG_VALUES.copy()
    config["output"]["format"] = "jpg"  # Add format field not in base defaults
    return config


def _get_env_config() -> dict[str, Any]:
    """Get configuration from environment variables."""
    config = {}

    # Map environment variables to config keys
    env_mappings = {
        f"{ENV_PREFIX}CACHE_ENABLED": "cache.enabled",
        f"{ENV_PREFIX}OUTPUT_DIR": "output.directory",
        f"{ENV_PREFIX}VARIANTS": "generation.default_variants",
        "GEMINI_API_KEY": "auth.gemini_api_key",
    }

    for env_var, config_key in env_mappings.items():
        value = os.getenv(env_var)
        if value:
            # Convert string values to appropriate types
            if value.lower() in ("true", "false"):
                value = value.lower() == "true"
            elif value.isdigit():
                value = int(value)

            _set_nested_value(config, config_key, value)

    return config


def _merge_config(
    target: dict[str, Any], source: dict[str, Any], sources: dict[str, str], source_name: str
):
    """Merge configuration dictionaries with source tracking."""
    for key, value in source.items():
        if key.startswith("#"):  # Skip comments
            continue

        if isinstance(value, dict) and key in target and isinstance(target[key], dict):
            # Recursive merge for nested dictionaries
            _merge_config(target[key], value, sources, source_name)
        else:
            target[key] = value
            sources[key] = source_name


def _get_nested_value(data: dict[str, Any], key: str) -> Any:
    """Get nested value using dot notation."""
    keys = key.split(".")
    current = data

    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None

    return current


def _set_nested_value(data: dict[str, Any], key: str, value: Any):
    """Set nested value using dot notation."""
    keys = key.split(".")
    current = data

    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    current[keys[-1]] = value


def _unset_nested_value(data: dict[str, Any], key: str) -> bool:
    """Remove nested value using dot notation."""
    keys = key.split(".")
    current = data

    for k in keys[:-1]:
        if k not in current or not isinstance(current[k], dict):
            return False
        current = current[k]

    if keys[-1] in current:
        del current[keys[-1]]
        return True

    return False


def _convert_value(value: str, value_type: str | None) -> Any:
    """Convert string value to appropriate type."""
    if value_type == "bool":
        return value.lower() in ("true", "yes", "1", "on")
    elif value_type == "int":
        return int(value)
    elif value_type == "float":
        return float(value)
    elif value_type == "list":
        return [item.strip() for item in value.split(",")]
    elif value_type == "string":
        return value
    else:
        # Auto-detect type
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        elif value.isdigit():
            return int(value)
        elif "," in value:
            return [item.strip() for item in value.split(",")]
        else:
            try:
                return float(value)
            except ValueError:
                return value


def _validate_global_config() -> dict[str, Any]:
    """Validate global configuration."""
    errors = []
    warnings = []
    info = []

    config_file = Path.home() / ".creatimation" / "config.yml"

    if not config_file.exists():
        info.append("No global configuration file found")
        return {"errors": errors, "warnings": warnings, "info": info}

    try:
        import yaml

        with open(config_file) as f:
            config = yaml.safe_load(f)

        if not config:
            warnings.append("Global configuration file is empty")
            return {"errors": errors, "warnings": warnings, "info": info}

        # Validate auth section
        auth = config.get("auth", {})
        if auth and not auth.get("gemini_api_key"):
            warnings.append("No Gemini API key configured")

        info.append("Global configuration loaded successfully")

    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax: {e}")
    except Exception as e:
        errors.append(f"Configuration error: {e}")

    return {"errors": errors, "warnings": warnings, "info": info}


def _validate_workspace_config_file(workspace_manager) -> dict[str, Any]:
    """Validate workspace configuration file."""
    errors = []
    warnings = []
    info = []

    config_file = workspace_manager.workspace_path / ".creatimation.yml"

    if not config_file.exists():
        warnings.append("No workspace configuration file found")
        return {"errors": errors, "warnings": warnings, "info": info}

    try:
        import yaml

        with open(config_file) as f:
            config = yaml.safe_load(f)

        if not config:
            errors.append("Workspace configuration file is empty")
            return {"errors": errors, "warnings": warnings, "info": info}

        # Validate required sections
        required_sections = REQUIRED_CONFIG_SECTIONS
        for section in required_sections:
            if section not in config:
                warnings.append(f"Missing configuration section: {section}")

        # Validate project section
        project = config.get("project", {})
        if not project.get("name"):
            warnings.append("Project name not specified")

        info.append("Workspace configuration loaded successfully")

    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML syntax: {e}")
    except Exception as e:
        errors.append(f"Configuration error: {e}")

    return {"errors": errors, "warnings": warnings, "info": info}


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================


def _display_config_table(config_data: dict[str, Any], title: str):
    """Display configuration in table format."""
    table = Table(title=title, show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    def add_rows(data, prefix=""):
        for key, value in data.items():
            if key.startswith("#"):  # Skip comments
                continue

            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                add_rows(value, full_key)
            else:
                table.add_row(full_key, str(value))

    add_rows(config_data)
    console.print(table)


def _display_config_yaml(config_data: dict[str, Any]):
    """Display configuration in YAML format."""
    import yaml

    yaml_content = yaml.dump(config_data, default_flow_style=False, sort_keys=False)
    syntax = Syntax(yaml_content, "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)


def _display_config_json(config_data: dict[str, Any]):
    """Display configuration in JSON format."""
    import json

    json_content = json.dumps(config_data, indent=2)
    syntax = Syntax(json_content, "json", theme="monokai", line_numbers=True)
    console.print(syntax)


def _display_config_env(config_data: dict[str, Any]):
    """Display configuration as environment variables."""

    def to_env_vars(data, prefix="CREATIMATION"):
        env_vars = []
        for key, value in data.items():
            if key.startswith("#"):
                continue

            env_key = f"{prefix}_{key.upper()}"

            if isinstance(value, dict):
                env_vars.extend(to_env_vars(value, env_key))
            else:
                env_vars.append(f"{env_key}={value}")

        return env_vars

    env_vars = to_env_vars(config_data)

    for env_var in env_vars:
        console.print(f"[cyan]{env_var}[/cyan]")


def _display_config_with_sources(config_data: dict[str, Any], sources: dict[str, str]):
    """Display configuration with source information."""
    table = Table(title="Configuration with Sources", show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="yellow")

    def add_rows(data, prefix=""):
        for key, value in data.items():
            if key.startswith("#"):
                continue

            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict):
                add_rows(value, full_key)
            else:
                source = sources.get(full_key, "unknown")
                table.add_row(full_key, str(value), source)

    add_rows(config_data)
    console.print(table)


def _display_validation_result(config_type: str, result: dict[str, Any]):
    """Display validation result for a configuration."""
    console.print(f"[bold]{config_type} Configuration[/bold]")

    if result["errors"]:
        for error in result["errors"]:
            console.print(f"  [red]✗[/red] {error}")

    if result["warnings"]:
        for warning in result["warnings"]:
            console.print(f"  [yellow]⚠[/yellow] {warning}")

    if result["info"]:
        for info_item in result["info"]:
            console.print(f"  [green]ℹ[/green] {info_item}")

    if not result["errors"] and not result["warnings"] and not result["info"]:
        console.print("  [green]✓[/green] Valid")

    console.print()


def _display_dynamic_workspace_config(ctx):
    """Display dynamic workspace configuration with detected assets."""

    if not ctx.workspace_manager:
        error_console.print("[red]✗[/red] No workspace found")
        return

    workspace_path = ctx.workspace_manager.workspace_path

    # Detect campaigns
    campaigns = _detect_campaigns(workspace_path)
    brand_guides = _detect_brand_guides(workspace_path)

    # Show workspace overview
    console.print(Panel("Dynamic Workspace Configuration", style="cyan"))

    # Basic config
    config_data = _get_effective_config(ctx)
    basic_config = {
        "generation": config_data.get("generation", {}),
        "cache": config_data.get("cache", {}),
        "output": config_data.get("output", {}),
    }
    _display_config_yaml(basic_config)

    console.print()

    # Campaign summary
    if campaigns:
        console.print(Panel(f"Detected Campaigns ({len(campaigns)})", style="green"))
        campaign_table = Table(show_header=True)
        campaign_table.add_column("Campaign ID", style="cyan")
        campaign_table.add_column("Name", style="white")
        campaign_table.add_column("Products", style="green")
        campaign_table.add_column("Regions", style="yellow")

        for campaign in campaigns:
            products = ", ".join(
                [
                    p.get("name", str(p)) if isinstance(p, dict) else str(p)
                    for p in campaign.get("products", [])
                ]
            )
            regions = ", ".join(campaign.get("target_regions", [campaign.get("target_region", "")]))

            campaign_table.add_row(
                campaign.get("campaign_id", "unknown"),
                campaign.get("campaign_name", "Unknown"),
                products[:40] + "..." if len(products) > 40 else products,
                regions,
            )

        console.print(campaign_table)
        console.print()

    # Brand guides summary
    if brand_guides:
        console.print(Panel(f"Detected Brand Guides ({len(brand_guides)})", style="blue"))
        for guide in brand_guides:
            console.print(f"  [cyan]•[/cyan] {guide['name']} ({guide['file']})")
        console.print()

    # Generation hints
    console.print(Panel("Quick Commands", style="yellow"))
    if campaigns:
        campaigns[0]["campaign_id"]
        console.print(
            f"  [cyan]./creatimation generate campaign briefs/{campaigns[0]['_file']}[/cyan]"
        )
    if brand_guides:
        example_brand = brand_guides[0]["file"]
        console.print(
            f"  [cyan]./creatimation generate campaign briefs/{campaigns[0]['_file']} --brand-guide {example_brand}[/cyan]"
        )
    console.print(
        "  [cyan]./creatimation config show --campaigns[/cyan] - Show detailed campaign info"
    )


def _display_workspace_campaigns(ctx):
    """Display detailed campaign information."""

    if not ctx.workspace_manager:
        error_console.print("[red]✗[/red] No workspace found")
        return

    workspace_path = ctx.workspace_manager.workspace_path
    campaigns = _detect_campaigns(workspace_path)
    brand_guides = _detect_brand_guides(workspace_path)

    console.print(Panel("Workspace Campaigns & Assets", style="cyan"))

    if not campaigns:
        console.print("[yellow]No campaign briefs detected in briefs/ directory[/yellow]")
        console.print()
        return

    for i, campaign in enumerate(campaigns):
        if i > 0:
            console.print()

        # Campaign header
        console.print(
            f"[bold cyan]Campaign: {campaign.get('campaign_name', 'Unknown')}[/bold cyan]"
        )
        console.print(
            f"[dim]ID: {campaign.get('campaign_id', 'unknown')} | File: {campaign.get('_file', 'unknown')}[/dim]"
        )
        console.print()

        # Campaign details table
        details_table = Table(show_header=False, box=None)
        details_table.add_column("Field", style="cyan", width=20)
        details_table.add_column("Value", style="white")

        # Products
        products = campaign.get("products", [])
        if products:
            product_names = [
                p.get("name", str(p)) if isinstance(p, dict) else str(p) for p in products
            ]
            details_table.add_row("Products", ", ".join(product_names))

        # Regions
        regions = campaign.get("target_regions", [campaign.get("target_region", "")])
        if regions and regions != [""]:
            details_table.add_row("Regions", ", ".join(regions))

        # Message
        if campaign.get("campaign_message"):
            details_table.add_row("Message", campaign["campaign_message"])

        # Creative requirements
        creative_req = campaign.get("creative_requirements", {})
        if creative_req:
            if creative_req.get("aspect_ratios"):
                details_table.add_row("Aspect Ratios", ", ".join(creative_req["aspect_ratios"]))
            if creative_req.get("variant_types"):
                details_table.add_row("Variant Types", ", ".join(creative_req["variant_types"]))

        console.print(details_table)

    # Brand guides section
    if brand_guides:
        console.print()
        console.print("[bold cyan]Available Brand Guides:[/bold cyan]")
        for guide in brand_guides:
            console.print(f"  [cyan]•[/cyan] {guide['name']} ([dim]{guide['file']}[/dim])")


def _detect_campaigns(workspace_path: Path) -> list:
    """Detect campaign briefs in workspace."""
    import json

    campaigns = []
    briefs_dir = workspace_path / "briefs"

    if not briefs_dir.exists():
        return campaigns

    for brief_file in briefs_dir.glob("*.json"):
        try:
            with open(brief_file) as f:
                campaign_data = json.load(f)
            campaign_data["_file"] = brief_file.name
            campaigns.append(campaign_data)
        except Exception:
            continue

    return campaigns


def _detect_brand_guides(workspace_path: Path) -> list:
    """Detect brand guides in workspace."""
    guides = []
    brand_dir = workspace_path / "brand-guides"

    if not brand_dir.exists():
        return guides

    for guide_file in brand_dir.glob("*.yml"):
        try:
            import yaml

            with open(guide_file) as f:
                guide_data = yaml.safe_load(f)

            brand_name = guide_data.get("brand", {}).get("name", guide_file.stem)
            guides.append(
                {"name": brand_name, "file": f"brand-guides/{guide_file.name}", "data": guide_data}
            )
        except Exception:
            continue

    return guides


def _display_campaign_hierarchy(ctx):
    """Display campaigns organized by industry > brand > campaign hierarchy."""
    from collections import defaultdict

    if not ctx.workspace_manager:
        return

    workspace_path = ctx.workspace_manager.workspace_path
    campaigns = _detect_campaigns(workspace_path)

    if not campaigns:
        return

    console.print()

    # Organize campaigns by industry > brand > campaign
    hierarchy = defaultdict(lambda: defaultdict(list))

    for campaign in campaigns:
        # Extract industry from products or use default
        products = campaign.get("products", [])
        if products and isinstance(products[0], dict):
            industry = products[0].get("category", "Unknown Industry")
        else:
            industry = "Consumer Goods"

        # Extract brand name from campaign or products
        brand = "Unknown Brand"
        if campaign.get("campaign_name"):
            # Extract brand from campaign name (e.g., "CleanWave Spring..." -> "CleanWave")
            brand = campaign["campaign_name"].split()[0]
        elif products:
            if isinstance(products[0], dict):
                product_name = products[0].get("name", "")
                if product_name:
                    brand = product_name.split()[0]

        hierarchy[industry][brand].append(campaign)

    # Display hierarchy
    console.print(Panel("Campaigns", style="green"))

    for industry in sorted(hierarchy.keys()):
        console.print(f"[bold cyan]{industry}[/bold cyan]")

        brands = hierarchy[industry]
        for brand in sorted(brands.keys()):
            console.print(f"  [bold yellow]├─ {brand}[/bold yellow]")

            campaigns_for_brand = brands[brand]
            for i, campaign in enumerate(
                sorted(campaigns_for_brand, key=lambda c: c.get("campaign_id", ""))
            ):
                is_last = i == len(campaigns_for_brand) - 1
                prefix = "     └─" if is_last else "     ├─"

                campaign_name = campaign.get("campaign_name", "Unknown Campaign")
                campaign_id = campaign.get("campaign_id", "unknown")
                regions = campaign.get("target_regions", [campaign.get("target_region", "")])
                region_str = ", ".join([r for r in regions if r])

                console.print(
                    f"[dim]{prefix}[/dim] [white]{campaign_name}[/white] [dim]({campaign_id})[/dim]"
                )
                if region_str:
                    console.print(f"[dim]          Regions: {region_str}[/dim]")

            console.print()  # Extra space between brands


def _display_unified_configuration(ctx):
    """Display unified view of global + local + campaigns configuration."""
    console.print(Panel("Configuration Overview", style="bold cyan"))

    # 1. Global Configuration
    global_config = _get_global_config()
    if global_config:
        console.print()
        console.print("[bold cyan]Global Configuration[/bold cyan]")
        console.print("[dim]Shared across all workspaces[/dim]")

        # Show key global settings
        auth = global_config.get("auth", {})
        defaults = global_config.get("defaults", {})

        if auth and any(v for v in auth.values() if not str(v).startswith("#")):
            console.print("  [green]✓[/green] API Keys configured")
        else:
            console.print("  [yellow]⚠[/yellow] No API keys configured")

        if defaults:
            console.print("  [green]✓[/green] Default settings available")
    else:
        console.print()
        console.print("[bold cyan]Global Configuration[/bold cyan]")
        console.print("[yellow]  No global configuration found[/yellow]")
        console.print("[dim]  Run: ./creatimation config init --global[/dim]")

    # 2. Local Workspace Configuration
    if ctx.workspace_manager:
        workspace_config_file = ctx.workspace_manager.workspace_path / ".creatimation.yml"
        console.print()
        console.print("[bold cyan]Workspace Configuration[/bold cyan]")
        console.print(f"[dim]Location: {workspace_config_file}[/dim]")

        if workspace_config_file.exists():
            workspace_config = ctx.workspace_manager.get_config()
            project = workspace_config.get("project", {})

            if project:
                console.print(
                    f"  [green]✓[/green] Project: [white]{project.get('name', 'Unknown')}[/white]"
                )
                console.print(
                    f"  [green]✓[/green] Brand: [white]{project.get('brand', 'Unknown')}[/white]"
                )
                console.print(
                    f"  [green]✓[/green] Industry: [white]{project.get('industry', 'Unknown')}[/white]"
                )

                # Show campaign count
                campaigns_in_project = _detect_campaigns(ctx.workspace_manager.workspace_path)
                if campaigns_in_project:
                    console.print(
                        f"  [green]✓[/green] Campaigns: [white]{len(campaigns_in_project)} detected[/white]"
                    )
            else:
                console.print("  [yellow]⚠[/yellow] Basic configuration only")
        else:
            console.print("[yellow]  No workspace configuration found[/yellow]")
            console.print("[dim]  Run: ./creatimation config init[/dim]")
    else:
        console.print()
        console.print("[bold cyan]Workspace Configuration[/bold cyan]")
        console.print("[yellow]  Not in a workspace[/yellow]")
        console.print("[dim]  Need briefs/ and brand-guides/ directories[/dim]")

    # 3. Detected Campaigns
    if ctx.workspace_manager:
        campaigns = _detect_campaigns(ctx.workspace_manager.workspace_path)
        brand_guides = _detect_brand_guides(ctx.workspace_manager.workspace_path)

        console.print()
        console.print("[bold cyan]Workspace Assets[/bold cyan]")

        if campaigns:
            console.print(f"  [green]✓[/green] {len(campaigns)} campaign(s) detected")

            # Show campaign hierarchy
            from collections import defaultdict

            hierarchy = defaultdict(lambda: defaultdict(list))

            for campaign in campaigns:
                products = campaign.get("products", [])
                if products and isinstance(products[0], dict):
                    industry = products[0].get("category", "Unknown Industry")
                else:
                    industry = "Consumer Goods"

                brand = "Unknown Brand"
                if campaign.get("campaign_name"):
                    brand = campaign["campaign_name"].split()[0]
                elif products:
                    if isinstance(products[0], dict):
                        product_name = products[0].get("name", "")
                        if product_name:
                            brand = product_name.split()[0]

                hierarchy[industry][brand].append(campaign)

            # Display compact hierarchy
            for industry in sorted(hierarchy.keys()):
                console.print(f"    [cyan]{industry}[/cyan]")
                brands = hierarchy[industry]
                for brand in sorted(brands.keys()):
                    campaigns_count = len(brands[brand])
                    console.print(
                        f"      [yellow]├─ {brand}[/yellow] ({campaigns_count} campaign{'s' if campaigns_count != 1 else ''})"
                    )
        else:
            console.print("  [yellow]⚠[/yellow] No campaigns detected")
            console.print("      [dim]Add campaign briefs to briefs/ directory[/dim]")

        if brand_guides:
            console.print(f"  [green]✓[/green] {len(brand_guides)} brand guide(s) available")
        else:
            console.print("  [yellow]⚠[/yellow] No brand guides detected")
            console.print("      [dim]Add brand guides to brand-guides/ directory[/dim]")

    # 4. Quick Commands
    console.print()
    console.print("[bold cyan]Quick Commands[/bold cyan]")

    if not global_config:
        console.print(
            "  [cyan]./creatimation config init --global[/cyan] - Setup global configuration"
        )

    console.print("  [cyan]./creatimation config validate[/cyan] - Validate all configurations")

    if ctx.workspace_manager:
        workspace_config_file = ctx.workspace_manager.workspace_path / ".creatimation.yml"
        if not workspace_config_file.exists():
            console.print(
                "  [cyan]./creatimation config init[/cyan] - Setup workspace configuration"
            )

        campaigns = (
            _detect_campaigns(ctx.workspace_manager.workspace_path) if ctx.workspace_manager else []
        )
        if campaigns:
            example_campaign = campaigns[0]
            console.print(
                f"  [cyan]./creatimation generate campaign briefs/{example_campaign['_file']}[/cyan] - Generate campaign"
            )
