#!/usr/bin/env python3
"""
Creative Automation CLI - Modern command-line interface.

A world-class CLI for creative automation with excellent developer experience.

Usage:
    creatimation generate campaign --brief campaign.json
    creatimation workspace init my-brand
    creatimation validate brief campaign.json
    creatimation config set output.quality 95
"""

import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.traceback import install

# Load environment variables from .env file
load_dotenv()

# Install rich tracebacks for better error display
install(show_locals=True)

# Import CLI modules
from .commands import cache, config, generate, validate, workspace
from .core import CreatimationContext, CreatimationGroup, show_welcome
from .plugins import get_plugin_manager, load_plugins
from .utils.output import error_console, setup_console

# Global console instance
console = Console()
setup_console(console)


# ============================================================================
# MAIN CLI GROUP WITH GITHUB-STYLE PATTERNS
# ============================================================================


@click.group(
    cls=CreatimationGroup,
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(
    version="2.0.0",
    prog_name="creatimation",
    message="%(prog)s %(version)s - Creative Automation Pipeline",
)
@click.option(
    "--config",
    "-c",
    "config_file",
    type=click.Path(exists=True),
    help="Path to configuration file",
    envvar="CREATIMATION_CONFIG",
)
@click.option(
    "--workspace",
    "-w",
    type=click.Path(exists=True),
    help="Path to workspace directory",
    envvar="CREATIMATION_WORKSPACE",
)
@click.option("--profile", "-p", help="Configuration profile to use", envvar="CREATIMATION_PROFILE")
@click.option("--verbose", "-v", count=True, help="Increase verbosity (use -vv for debug level)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output except errors")
@click.option("--no-color", is_flag=True, help="Disable colored output", envvar="NO_COLOR")
@click.option(
    "--format",
    type=click.Choice(["auto", "json", "yaml", "table"]),
    default="auto",
    help="Output format",
)
@click.pass_context
def main(
    click_ctx,
    config_file: str | None,
    workspace: str | None,
    profile: str | None,
    verbose: int,
    quiet: bool,
    no_color: bool,
    format: str,
):
    """
    Creative Automation Pipeline - Generate professional creatives at scale.

    A modern CLI inspired by GitHub's developer experience patterns.
    Create, validate, and manage creative campaigns with intelligent automation.

    Examples:
        creatimation generate campaign --brief campaign.json
        creatimation workspace init my-brand --template cpg
        creatimation validate brief campaign.json --fix
        creatimation config set cache.s3_bucket my-bucket

    Get started:
        creatimation workspace init          # Create new workspace
        creatimation config init             # Setup configuration
        creatimation generate --help         # See generation options
    """
    # Get or create our custom context
    ctx = click_ctx.ensure_object(CreatimationContext)

    # Initialize CLI context
    ctx.initialize(
        config_file=config_file,
        workspace=workspace,
        profile=profile,
        verbose=verbose,
        quiet=quiet,
        no_color=no_color,
        output_format=format,
    )

    # If no command provided, show helpful info
    if click_ctx.invoked_subcommand is None:
        show_welcome(ctx)


# ============================================================================
# REGISTER COMMAND GROUPS
# ============================================================================

# Core workflow commands
main.add_command(generate.generate)
main.add_command(validate.validate)

# Workspace and configuration
main.add_command(workspace.workspace)
main.add_command(config.config)

# System commands
main.add_command(cache.cache)

# Load and register plugins
loaded_count = 0
try:
    loaded_count = load_plugins()
    if loaded_count > 0:
        console.print(f"[dim]Loaded {loaded_count} plugins[/dim]")
except ImportError as e:
    error_console.print(f"[yellow]Warning: Plugin import failed: {e}[/yellow]")
except FileNotFoundError as e:
    error_console.print(f"[yellow]Warning: Plugin files not found: {e}[/yellow]")
except PermissionError as e:
    error_console.print(f"[yellow]Warning: Permission denied loading plugins: {e}[/yellow]")
except Exception as e:
    error_console.print(f"[yellow]Warning: Plugin loading failed: {e}[/yellow]")

# Register plugin commands (only if plugins were loaded successfully)
if loaded_count > 0:
    try:
        plugin_manager = get_plugin_manager()
        plugin_commands = plugin_manager.get_plugin_commands()

        for cmd_name, cmd_obj in plugin_commands.items():
            try:
                main.add_command(cmd_obj, name=cmd_name)
            except Exception as e:
                error_console.print(f"[yellow]Warning: Failed to register plugin command '{cmd_name}': {e}[/yellow]")
    except Exception as e:
        error_console.print(f"[yellow]Warning: Plugin command registration failed: {e}[/yellow]")


# Add completion command for shell integration
@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completion(shell):
    """Generate shell completion scripts."""
    import subprocess
    import os

    try:
        # Set up environment for completion generation
        env = os.environ.copy()
        env["_CREATIMATION_COMPLETE"] = f"{shell}_source"

        result = subprocess.run(
            ["_CREATIMATION_COMPLETE", f"{shell}_source", "creatimation"],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,  # Prevent hanging
        )

        if result.returncode != 0:
            error_console.print(f"Completion generation failed with exit code {result.returncode}")
            if result.stderr:
                error_console.print(f"Error output: {result.stderr}")
            sys.exit(1)

        if result.stdout:
            console.print(result.stdout)
        else:
            error_console.print("No completion script generated")
            sys.exit(1)

    except subprocess.TimeoutExpired:
        error_console.print("Completion generation timed out")
        sys.exit(1)
    except FileNotFoundError:
        error_console.print("Completion command not found. Ensure click is properly installed.")
        sys.exit(1)
    except PermissionError:
        error_console.print("Permission denied executing completion command")
        sys.exit(1)
    except Exception as e:
        error_console.print(f"Failed to generate completion: {e}")
        sys.exit(1)


# ============================================================================
# ERROR HANDLING
# ============================================================================


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler with rich formatting."""
    if issubclass(exc_type, KeyboardInterrupt):
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)

    # Use rich traceback for better error display
    console.print_exception()


# Install global exception handler
sys.excepthook = handle_exception


# ============================================================================
# CLI ENTRY POINT
# ============================================================================


def cli_main():
    """Main CLI entry point."""
    try:
        main()
    except click.ClickException as e:
        e.show()
        sys.exit(e.exit_code)
    except Exception as e:
        error_console.print(f"[red]Unexpected error: {e}[/red]")
        if "--verbose" in sys.argv or "-v" in sys.argv:
            console.print_exception()
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
