"""
Workspace command group - Manage creative automation workspaces.

Provides workspace management with project isolation,
templates, and collaborative features.
"""

import shutil
import sys
from pathlib import Path
from typing import Any

import click
from rich.prompt import Confirm
from rich.table import Table
from rich.tree import Tree

from ..constants import (
    DEFAULT_WORKSPACE_DIRS,
    KEY_WORKSPACE_DIRS,
    OUTPUT_FORMATS,
    WORKSPACE_TEMPLATES,
    get_template_config,
    get_sample_brief_data,
)
from ..core import pass_context
from ..utils.output import console, error_console


@click.group(invoke_without_command=True)
@click.option("--list", "-l", "list_workspaces", is_flag=True, help="List available workspaces")
@pass_context
def workspace(ctx, list_workspaces):
    """
    Manage creative automation workspaces.

    Workspaces provide isolated environments for different brands,
    campaigns, or projects with their own configuration, assets,
    and output management.

    Examples:
        creatimation workspace init my-brand
        creatimation workspace list
        creatimation workspace info
        creatimation workspace switch my-brand

    Workspace Commands:
        init        Create new workspace
        list        List available workspaces
        info        Show current workspace information
        switch      Switch to different workspace
        clone       Clone existing workspace
        remove      Remove workspace
    """
    if list_workspaces:
        ctx.invoke(list_workspaces_cmd)
    elif ctx.invoked_subcommand is None:
        # Show current workspace info or help
        if ctx.workspace_manager:
            ctx.invoke(info)
        else:
            console.print()
            console.print("[yellow]No workspace active.[/yellow]")
            console.print(
                "Create a workspace with: [cyan]creatimation workspace init <name>[/cyan]"
            )
            console.print("Or see [cyan]creatimation workspace --help[/cyan] for more options.")
            console.print()


@workspace.command()
@click.argument("name")
@click.option(
    "--template",
    "-t",
    type=click.Choice(WORKSPACE_TEMPLATES),
    default="minimal",
    help="Workspace template to use",
)
@click.option("--brand", "-b", help="Brand name for workspace")
@click.option("--industry", "-i", help="Industry vertical")
@click.option("--path", "-p", type=click.Path(), help="Custom workspace path (default: ./<name>)")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing workspace")
@pass_context
def init(ctx, name, template, brand, industry, path, force):
    """
    Create a new creative automation workspace.

    Sets up a complete workspace with configuration, directory structure,
    and template files based on the selected template.

    Templates:
        minimal     Basic setup for simple projects
        cpg         Consumer Packaged Goods template
        fashion     Fashion and lifestyle brands
        tech        Technology and software companies
        custom      Minimal setup for custom configuration

    Examples:
        creatimation workspace init my-brand
        creatimation workspace init my-brand --template cpg --brand "Power Clean"
        creatimation workspace init my-brand --path ./workspaces/my-brand
        creatimation workspace init my-brand --industry "consumer-goods" --force
    """
    try:
        # Determine workspace path
        if path:
            workspace_path = Path(path).resolve()
        else:
            workspace_path = Path.cwd() / name

        # Check if workspace already exists
        if workspace_path.exists() and any(workspace_path.iterdir()):
            if not force:
                if not Confirm.ask(
                    f"Directory {workspace_path} exists and is not empty. Continue?"
                ):
                    console.print("Workspace creation cancelled.")
                    return

        # Create workspace structure
        console.print()
        console.print(f"[bold cyan]Creating workspace: {name}[/bold cyan]")
        console.print(f"Template: {template}")
        console.print(f"Path: {workspace_path}")
        console.print()

        # Create directories
        directories = DEFAULT_WORKSPACE_DIRS

        for directory in directories:
            dir_path = workspace_path / directory
            dir_path.mkdir(parents=True, exist_ok=True)
            console.print(f"[green]✓[/green] Created directory: [cyan]{directory}[/cyan]")

        # Create configuration file
        config_content = _get_template_config(template, name, brand, industry)
        config_file = workspace_path / ".creatimation.yml"
        config_file.write_text(config_content)
        console.print("[green]✓[/green] Created configuration: [cyan].creatimation.yml[/cyan]")

        # Create template files based on template type
        _create_template_files(workspace_path, template, brand)

        # Create README
        readme_content = _get_workspace_readme(name, template, brand)
        readme_file = workspace_path / "README.md"
        readme_file.write_text(readme_content)
        console.print("[green]✓[/green] Created documentation: [cyan]README.md[/cyan]")

        # Create .gitignore
        gitignore_content = _get_workspace_gitignore()
        gitignore_file = workspace_path / ".gitignore"
        gitignore_file.write_text(gitignore_content)
        console.print("[green]✓[/green] Created version control: [cyan].gitignore[/cyan]")

        console.print()
        console.print(f"[bold green]✓ Workspace '{name}' created successfully![/bold green]")
        console.print()
        console.print("Next steps:")
        console.print(f"  1. [cyan]cd {workspace_path.name}[/cyan]")
        console.print("  2. [cyan]creatimation validate workspace[/cyan]")
        console.print("  3. Add your campaign briefs to [cyan]briefs/[/cyan]")
        console.print("  4. [cyan]creatimation generate --brief briefs/your-campaign.json[/cyan]")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to create workspace: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@workspace.command(name="list")
@click.option(
    "--format", type=click.Choice(OUTPUT_FORMATS), default="table", help="Output format"
)
@pass_context
def list_workspaces_cmd(ctx, format):
    """
    List available workspaces.

    Discovers workspaces in the current directory and common workspace
    locations, showing status and basic information.

    Examples:
        creatimation workspace list
        creatimation workspace list --format tree
        creatimation workspace list --format json
    """
    try:
        workspaces = _discover_workspaces()

        if not workspaces:
            console.print()
            console.print("[yellow]No workspaces found.[/yellow]")
            console.print(
                "Create a workspace with: [cyan]creatimation workspace init <name>[/cyan]"
            )
            console.print()
            return

        console.print()

        if format == "table":
            _display_workspaces_table(workspaces)
        elif format == "tree":
            _display_workspaces_tree(workspaces)
        elif format == "json":
            _display_workspaces_json(workspaces)

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to list workspaces: {e}")
        sys.exit(1)


@workspace.command()
@click.option("--detailed", "-d", is_flag=True, help="Show detailed workspace information")
@pass_context
def info(ctx, detailed):
    """
    Show current workspace information.

    Displays configuration, structure, and status of the current workspace.

    Examples:
        creatimation workspace info
        creatimation workspace info --detailed
    """
    try:
        if not ctx.workspace_manager:
            error_console.print("[red]✗[/red] No workspace found")
            console.print("Initialize a workspace with: [cyan]creatimation workspace init[/cyan]")
            sys.exit(1)

        workspace = ctx.workspace_manager
        workspace_path = workspace.workspace_path

        console.print()
        console.print("[bold cyan]Workspace Information[/bold cyan]")
        console.print()

        # Basic info table
        info_table = Table(show_header=False, box=None)
        info_table.add_column("Property", style="cyan", width=20)
        info_table.add_column("Value", style="green")

        info_table.add_row("Name", workspace_path.name)
        info_table.add_row("Path", str(workspace_path))

        # Get configuration if available
        config_file = workspace_path / ".creatimation.yml"
        if config_file.exists():
            import yaml

            try:
                with open(config_file) as f:
                    config = yaml.safe_load(f)

                project_info = config.get("project", {})
                if project_info.get("name"):
                    info_table.add_row("Project", project_info["name"])
                if project_info.get("brand"):
                    info_table.add_row("Brand", project_info["brand"])
                if project_info.get("industry"):
                    info_table.add_row("Industry", project_info["industry"])

            except Exception:
                info_table.add_row("Config", "Error reading configuration")
        else:
            info_table.add_row("Config", "No configuration file")

        console.print(info_table)

        if detailed:
            console.print()
            _display_detailed_workspace_info(workspace_path)

        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to show workspace info: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@workspace.command()
@click.argument("workspace_name")
@pass_context
def switch(ctx, workspace_name):
    """
    Switch to a different workspace.

    Changes the active workspace context for subsequent commands.

    Examples:
        creatimation workspace switch my-brand
        creatimation workspace switch ../other-workspace
    """
    try:
        # Look for workspace
        workspace_path = _find_workspace(workspace_name)

        if not workspace_path:
            error_console.print(f"[red]✗[/red] Workspace not found: {workspace_name}")

            # Suggest available workspaces
            workspaces = _discover_workspaces()
            if workspaces:
                console.print("\nAvailable workspaces:")
                for ws in workspaces[:5]:  # Show first 5
                    console.print(f"  • {ws['name']}")
                if len(workspaces) > 5:
                    console.print(f"  ... and {len(workspaces) - 5} more")

            sys.exit(1)

        # Switch workspace (this would typically involve updating environment or config)
        console.print()
        console.print(f"[green]✓[/green] Switched to workspace: [cyan]{workspace_name}[/cyan]")
        console.print(f"[dim]Path: {workspace_path}[/dim]")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to switch workspace: {e}")
        sys.exit(1)


@workspace.command()
@click.argument("source_workspace")
@click.argument("new_name")
@click.option("--path", "-p", type=click.Path(), help="Custom path for cloned workspace")
@pass_context
def clone(ctx, source_workspace, new_name, path):
    """
    Clone an existing workspace.

    Creates a copy of an existing workspace with a new name,
    preserving structure and configuration but clearing outputs.

    Examples:
        creatimation workspace clone my-brand my-brand-v2
        creatimation workspace clone my-brand new-project --path ./workspaces/
    """
    try:
        # Find source workspace
        source_path = _find_workspace(source_workspace)
        if not source_path:
            error_console.print(f"[red]✗[/red] Source workspace not found: {source_workspace}")
            sys.exit(1)

        # Determine target path
        if path:
            target_path = Path(path) / new_name
        else:
            target_path = Path.cwd() / new_name

        if target_path.exists():
            if not Confirm.ask(f"Directory {target_path} exists. Overwrite?"):
                console.print("Clone cancelled.")
                return

        console.print()
        console.print("[bold cyan]Cloning workspace[/bold cyan]")
        console.print(f"Source: {source_path}")
        console.print(f"Target: {target_path}")
        console.print()

        # Copy workspace structure
        shutil.copytree(source_path, target_path, dirs_exist_ok=True)

        # Clear output and cache directories
        output_dir = target_path / "output"
        cache_dir = target_path / "cache"

        if output_dir.exists():
            shutil.rmtree(output_dir)
            output_dir.mkdir()
            console.print("[green]✓[/green] Cleared output directory")

        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            cache_dir.mkdir()
            console.print("[green]✓[/green] Cleared cache directory")

        # Update configuration with new name
        config_file = target_path / ".creatimation.yml"
        if config_file.exists():
            import yaml

            try:
                with open(config_file) as f:
                    config = yaml.safe_load(f)

                if "project" not in config:
                    config["project"] = {}
                config["project"]["name"] = new_name

                with open(config_file, "w") as f:
                    yaml.dump(config, f, default_flow_style=False)

                console.print("[green]✓[/green] Updated configuration")

            except Exception as e:
                console.print(f"[yellow]⚠[/yellow] Could not update config: {e}")

        console.print()
        console.print("[bold green]✓ Workspace cloned successfully![/bold green]")
        console.print(f"[dim]New workspace: {target_path}[/dim]")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to clone workspace: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


@workspace.command()
@click.argument("workspace_name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@pass_context
def remove(ctx, workspace_name, force):
    """
    Remove a workspace.

    Permanently deletes a workspace and all its contents.
    Use with caution!

    Examples:
        creatimation workspace remove old-workspace
        creatimation workspace remove old-workspace --force
    """
    try:
        # Find workspace
        workspace_path = _find_workspace(workspace_name)
        if not workspace_path:
            error_console.print(f"[red]✗[/red] Workspace not found: {workspace_name}")
            sys.exit(1)

        # Confirmation
        if not force:
            console.print()
            console.print(
                "[bold red]Warning: This will permanently delete the workspace![/bold red]"
            )
            console.print(f"Path: {workspace_path}")
            console.print()

            if not Confirm.ask("Are you sure you want to continue?"):
                console.print("Removal cancelled.")
                return

        # Remove workspace
        shutil.rmtree(workspace_path)

        console.print()
        console.print(f"[green]✓[/green] Workspace removed: [cyan]{workspace_name}[/cyan]")
        console.print()

    except Exception as e:
        error_console.print(f"[red]✗[/red] Failed to remove workspace: {e}")
        if ctx.verbose >= 2:
            console.print_exception()
        sys.exit(1)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _discover_workspaces():
    """Discover available workspaces."""
    workspaces = []

    # Check current directory and subdirectories
    for path in Path.cwd().iterdir():
        if path.is_dir() and (path / ".creatimation.yml").exists():
            workspace_info = _get_workspace_info(path)
            workspaces.append(workspace_info)

    return workspaces


def _get_workspace_info(workspace_path: Path) -> dict[str, Any]:
    """Get information about a workspace."""
    info = {"name": workspace_path.name, "path": workspace_path, "valid": False, "config": {}}

    # Check if valid workspace
    config_file = workspace_path / ".creatimation.yml"
    if config_file.exists():
        try:
            import yaml

            with open(config_file) as f:
                config = yaml.safe_load(f)
            info["config"] = config
            info["valid"] = True
        except Exception:
            pass

    # Count content
    briefs_dir = workspace_path / "briefs"
    if briefs_dir.exists():
        info["briefs_count"] = len(list(briefs_dir.glob("*.json")))

    guides_dir = workspace_path / "brand-guides"
    if guides_dir.exists():
        info["guides_count"] = len(list(guides_dir.glob("*.yml")) + list(guides_dir.glob("*.yaml")))

    return info


def _find_workspace(name: str) -> Path | None:
    """Find workspace by name or path."""
    # Check if it's a direct path
    path = Path(name)
    if path.exists() and (path / ".creatimation.yml").exists():
        return path.resolve()

    # Search in current directory
    current_dir = Path.cwd()
    workspace_path = current_dir / name
    if workspace_path.exists() and (workspace_path / ".creatimation.yml").exists():
        return workspace_path.resolve()

    return None


def _get_template_config(template: str, name: str, brand: str | None, industry: str | None) -> str:
    """Generate configuration content based on template."""
    # Get base configuration from constants
    config = get_template_config(template)

    # Set project-specific details
    config["project"]["name"] = brand or name
    config["project"]["workspace"] = name

    if brand:
        config["project"]["brand"] = brand

    if industry:
        config["project"]["industry"] = industry

    # Set template type
    config["project"]["template"] = template

    import yaml

    return yaml.dump(config, default_flow_style=False, sort_keys=False)


def _create_template_files(workspace_path: Path, template: str, brand: str | None):
    """Create template files based on template type."""

    # Create sample brief
    if template == "cpg":
        brief_content = _get_cpg_sample_brief(brand or "Sample Brand")
    elif template == "fashion":
        brief_content = _get_fashion_sample_brief(brand or "Sample Brand")
    elif template == "tech":
        brief_content = _get_tech_sample_brief(brand or "Sample Brand")
    else:
        brief_content = _get_minimal_sample_brief(brand or "Sample Brand")

    brief_file = workspace_path / "briefs" / "sample-campaign.json"
    brief_file.write_text(brief_content)

    # Create sample brand guide
    brand_guide_content = _get_sample_brand_guide(brand or "Sample Brand", template)
    guide_file = workspace_path / "brand-guides" / "brand-guide.yml"
    guide_file.write_text(brand_guide_content)

    console.print(
        "[green]✓[/green] Created template files: [cyan]sample brief & brand guide[/cyan]"
    )


def _get_cpg_sample_brief(brand: str) -> str:
    """Generate CPG sample brief."""
    import json

    brief = get_sample_brief_data("cpg")
    brief["enhanced_context"] = {
        "setting": "modern kitchen environment",
        "mood": "fresh and efficient",
        "brand_colors": {"primary": "#2E7D32", "secondary": "#66BB6A"},
        "brand_tone": "confident and reassuring",
        "target_audience": f"{brand} customers seeking effective cleaning solutions",
    }
    brief["regional_adaptations"] = {
        "US": {"call_to_action": "Try Now"},
        "EMEA": {"call_to_action": "Discover More"},
        "APAC": {"call_to_action": "Learn More"},
    }

    return json.dumps(brief, indent=2)


def _get_fashion_sample_brief(brand: str) -> str:
    """Generate fashion sample brief."""
    import json

    brief = get_sample_brief_data("fashion")
    brief["enhanced_context"] = {
        "setting": "urban lifestyle environment",
        "mood": "confident and stylish",
        "brand_colors": {"primary": "#E91E63", "secondary": "#9C27B0"},
        "brand_tone": "inspiring and aspirational",
        "target_audience": f"{brand} fashion-forward individuals",
    }

    return json.dumps(brief, indent=2)


def _get_tech_sample_brief(brand: str) -> str:
    """Generate tech sample brief."""
    import json

    brief = get_sample_brief_data("tech")
    brief["enhanced_context"] = {
        "setting": "modern office environment",
        "mood": "innovative and efficient",
        "brand_colors": {"primary": "#1976D2", "secondary": "#42A5F5"},
        "brand_tone": "professional and forward-thinking",
        "target_audience": f"{brand} technology professionals and businesses",
    }

    return json.dumps(brief, indent=2)


def _get_minimal_sample_brief(brand: str) -> str:
    """Generate minimal sample brief."""
    import json

    brief = get_sample_brief_data("minimal")
    brief["enhanced_context"] = {
        "setting": "clean modern environment",
        "mood": "professional and trustworthy",
        "brand_colors": {"primary": "#1565C0"},
        "brand_tone": "reliable and straightforward",
        "target_audience": f"{brand} customers",
    }

    return json.dumps(brief, indent=2)


def _get_sample_brand_guide(brand: str, template: str) -> str:
    """Generate sample brand guide."""
    import yaml

    brand_guide = {
        "brand": {
            "name": brand,
            "tagline": "Quality and innovation",
            "industry": "consumer goods" if template == "cpg" else template,
        },
        "colors": {"primary": "#1565C0", "secondary": "#42A5F5", "accent": "#FFA726"},
        "visual": {
            "layout_style": "clean and modern",
            "logo_placement": "top-left",
            "font_style": "sans-serif",
        },
        "messaging": {
            "tone": "professional yet approachable",
            "voice": "confident and helpful",
            "keywords": ["quality", "innovation", "trust"],
        },
    }

    return yaml.dump(brand_guide, default_flow_style=False)


def _get_workspace_readme(name: str, template: str, brand: str | None) -> str:
    """Generate workspace README."""
    brand_name = brand or name

    return f"""# {brand_name} Creative Workspace

This workspace contains creative automation assets and configuration for {brand_name}.

## Structure

- `briefs/` - Campaign briefs in JSON format
- `brand-guides/` - Brand guidelines in YAML format
- `output/` - Generated creative assets
- `cache/` - Cached assets for performance
- `templates/` - Custom templates
- `assets/` - Source assets and resources

## Quick Start

1. **Validate Setup**
   ```bash
   creatimation validate workspace
   ```

2. **Generate Creatives**
   ```bash
   creatimation generate --brief briefs/sample-campaign.json
   ```

3. **View Results**
   ```bash
   ls output/
   ```

## Configuration

Workspace configuration is stored in `.creatimation.yml`.
Template: {template}

## Next Steps

1. Update `briefs/sample-campaign.json` with your campaign details
2. Customize `brand-guides/brand-guide.yml` with your brand guidelines
3. Run generation and review outputs
4. Iterate and refine as needed

For more information, see: https://github.com/your-org/creatimation
"""


def _get_workspace_gitignore() -> str:
    """Generate workspace .gitignore."""
    return """# Creatimation Workspace
output/
cache/
*.log

# OS Files
.DS_Store
Thumbs.db

# Editor Files
.vscode/
.idea/
*.swp
*.tmp

# Python
__pycache__/
*.pyc
.env

# Temporary Files
*.backup
*.temp
"""


def _display_workspaces_table(workspaces):
    """Display workspaces in table format."""
    table = Table(title="Available Workspaces", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Path", style="dim")
    table.add_column("Brand", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Briefs", style="blue")

    for ws in workspaces:
        brand = ws.get("config", {}).get("project", {}).get("brand", "-")
        status = "✓ Valid" if ws["valid"] else "✗ Invalid"
        briefs = str(ws.get("briefs_count", 0))

        table.add_row(ws["name"], str(ws["path"]), brand, status, briefs)

    console.print(table)


def _display_workspaces_tree(workspaces):
    """Display workspaces in tree format."""
    tree = Tree("📁 Workspaces")

    for ws in workspaces:
        workspace_node = tree.add(f"[cyan]{ws['name']}[/cyan]")

        status = "✓" if ws["valid"] else "✗"
        workspace_node.add(f"Status: {status}")
        workspace_node.add(f"Path: [dim]{ws['path']}[/dim]")

        brand = ws.get("config", {}).get("project", {}).get("brand")
        if brand:
            workspace_node.add(f"Brand: [green]{brand}[/green]")

        briefs_count = ws.get("briefs_count", 0)
        if briefs_count > 0:
            workspace_node.add(f"Briefs: {briefs_count}")

    console.print(tree)


def _display_workspaces_json(workspaces):
    """Display workspaces in JSON format."""
    import json

    # Convert Path objects to strings for JSON serialization
    json_data = []
    for ws in workspaces:
        ws_copy = ws.copy()
        ws_copy["path"] = str(ws_copy["path"])
        json_data.append(ws_copy)

    console.print(json.dumps(json_data, indent=2))


def _display_detailed_workspace_info(workspace_path: Path):
    """Display detailed workspace information."""

    # Directory structure
    console.print("[bold]Directory Structure[/bold]")

    structure_tree = Tree("📁 Workspace")

    key_dirs = KEY_WORKSPACE_DIRS
    for dir_name in key_dirs:
        dir_path = workspace_path / dir_name
        if dir_path.exists():
            dir_node = structure_tree.add(f"📁 {dir_name}")

            # Count files in directory
            files = list(dir_path.iterdir())
            if files:
                for file in files[:3]:  # Show first 3 files
                    if file.is_file():
                        dir_node.add(f"📄 {file.name}")
                if len(files) > 3:
                    dir_node.add(f"... and {len(files) - 3} more")
            else:
                dir_node.add("[dim](empty)[/dim]")
        else:
            structure_tree.add(f"[red]📁 {dir_name} (missing)[/red]")

    console.print(structure_tree)
