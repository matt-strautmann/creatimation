"""
Core CLI infrastructure inspired by GitHub spec-kit patterns.

Provides the foundation for a world-class developer experience with
rich formatting, intelligent configuration, and extensible architecture.
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import print as rprint

from ..container import DIContainer, get_container
from ..config import ConfigManager
from .utils.workspace import WorkspaceManager
from .utils.output import console, error_console


class CreatimationContext:
    """
    CLI context that manages global state and configuration.

    Inspired by GitHub CLI's context pattern for maintaining state
    across command invocations.
    """

    def __init__(self):
        self.config_manager: Optional[ConfigManager] = None
        self.workspace_manager: Optional[WorkspaceManager] = None
        self.container: Optional[DIContainer] = None
        self.verbose: int = 0
        self.quiet: bool = False
        self.no_color: bool = False
        self.output_format: str = "auto"
        self.profile: Optional[str] = None
        self.workspace_path: Optional[Path] = None
        self._initialized: bool = False

    def initialize(
        self,
        config_file: Optional[str] = None,
        workspace: Optional[str] = None,
        profile: Optional[str] = None,
        verbose: int = 0,
        quiet: bool = False,
        no_color: bool = False,
        output_format: str = "auto"
    ):
        """Initialize CLI context with configuration and workspace."""
        self.verbose = verbose
        self.quiet = quiet
        self.no_color = no_color
        self.output_format = output_format
        self.profile = profile

        # Setup console based on options
        if no_color:
            console._color_system = None
            error_console._color_system = None

        # Initialize configuration
        self.config_manager = ConfigManager()
        if config_file:
            try:
                self.config_manager.load_config(config_file)
            except Exception as e:
                error_console.print(f"[red]Failed to load config: {e}[/red]")
                sys.exit(1)

        # Initialize workspace
        if workspace:
            self.workspace_path = Path(workspace)
        else:
            # Look for workspace in current directory or parents
            self.workspace_path = self._find_workspace()

        if self.workspace_path:
            self.workspace_manager = WorkspaceManager(self.workspace_path)

        # Initialize dependency injection container
        config_data = {}
        if self.config_manager:
            try:
                # Try to get config data if available
                if hasattr(self.config_manager, 'get_all'):
                    config_data = self.config_manager.get_all()
                elif hasattr(self.config_manager, 'config'):
                    config_data = self.config_manager.config
            except Exception:
                pass
        if self.workspace_manager:
            # Merge workspace config
            workspace_config = self.workspace_manager.get_config()
            config_data.update(workspace_config)

        self.container = get_container(config_data)
        self._initialized = True

    def ensure_initialized(self):
        """Ensure context is initialized."""
        if not self._initialized:
            self.initialize()

    def ensure_workspace(self) -> WorkspaceManager:
        """Ensure workspace exists or exit with helpful message."""
        if not self.workspace_manager:
            error_console.print("[red]No workspace found[/red]")
            console.print("Initialize a workspace with: [cyan]creatimation workspace init[/cyan]")
            sys.exit(1)
        return self.workspace_manager

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value with workspace override."""
        if self.workspace_manager:
            value = self.workspace_manager.get_config_value(key)
            if value is not None:
                return value

        if self.config_manager:
            return self.config_manager.get(key, default)

        return default

    def set_config_value(self, key: str, value: Any, workspace_only: bool = False):
        """Set configuration value."""
        if workspace_only and self.workspace_manager:
            self.workspace_manager.set_config_value(key, value)
        elif self.config_manager:
            self.config_manager.set(key, value)
        else:
            error_console.print("[red]No configuration manager available[/red]")
            sys.exit(1)

    def _find_workspace(self) -> Optional[Path]:
        """Find workspace in current directory or parents."""
        current = Path.cwd()
        while current != current.parent:
            if (current / ".creatimation").exists():
                return current
            current = current.parent
        return None

    def debug(self, message: str):
        """Print debug message if verbose mode enabled."""
        if self.verbose >= 2:
            console.print(f"[dim]DEBUG: {message}[/dim]")

    def info(self, message: str):
        """Print info message if not quiet."""
        if not self.quiet:
            console.print(message)

    def success(self, message: str):
        """Print success message."""
        if not self.quiet:
            console.print(f"[green]✓[/green] {message}")

    def warning(self, message: str):
        """Print warning message."""
        console.print(f"[yellow]⚠[/yellow] {message}")

    def error(self, message: str):
        """Print error message."""
        error_console.print(f"[red]✗[/red] {message}")


class CreatimationGroup(click.Group):
    """
    Custom Click group with enhanced help formatting.

    Provides GitHub-style help output with better organization
    and visual hierarchy.
    """

    def format_help(self, ctx, formatter):
        """Format help with rich styling."""
        # Use click's default formatting but enhance it
        super().format_help(ctx, formatter)

    def list_commands(self, ctx):
        """Return list of commands in logical order."""
        commands = super().list_commands(ctx)

        # Define logical command order
        command_order = [
            "generate",    # Primary workflow
            "validate",    # Validation
            "workspace",   # Workspace management
            "config",      # Configuration
            "cache",       # System commands
            "completion",  # Shell integration
        ]

        # Sort commands by defined order, then alphabetically
        def sort_key(cmd):
            try:
                return (command_order.index(cmd), cmd)
            except ValueError:
                return (len(command_order), cmd)

        return sorted(commands, key=sort_key)

    def get_command(self, ctx, cmd_name):
        """Get command with enhanced error handling."""
        command = super().get_command(ctx, cmd_name)
        if command is None:
            # Suggest similar commands
            available = self.list_commands(ctx)
            suggestions = [cmd for cmd in available if cmd.startswith(cmd_name)]

            if suggestions:
                error_console.print(f"[red]Unknown command: {cmd_name}[/red]")
                console.print(f"Did you mean: {', '.join(suggestions)}?")
            else:
                error_console.print(f"[red]Unknown command: {cmd_name}[/red]")
                console.print(f"Available commands: {', '.join(available)}")

        return command


# Context decorator for commands
pass_context = click.make_pass_decorator(CreatimationContext, ensure=True)


def show_welcome(ctx: CreatimationContext):
    """Show welcome message when no command is provided."""
    console.print()

    # Welcome panel
    welcome_text = Text()
    welcome_text.append("Creative Automation Pipeline", style="bold blue")
    welcome_text.append(" v2.0\n", style="dim")
    welcome_text.append("Professional creative generation at scale")

    console.print(Panel(
        welcome_text,
        title="🎨 Creatimation",
        subtitle="Inspired by GitHub spec-kit",
        border_style="blue"
    ))

    # Quick start table
    table = Table(title="Quick Start", show_header=True, header_style="bold cyan")
    table.add_column("Command", style="cyan", width=30)
    table.add_column("Description", style="white")

    table.add_row(
        "creatimation workspace init",
        "Create a new workspace for your brand"
    )
    table.add_row(
        "creatimation generate campaign",
        "Generate creatives from a campaign brief"
    )
    table.add_row(
        "creatimation validate brief",
        "Validate campaign brief format"
    )
    table.add_row(
        "creatimation config init",
        "Setup global configuration"
    )

    console.print()
    console.print(table)

    # Status information
    console.print()
    if ctx.workspace_manager:
        console.print(f"[green]✓[/green] Workspace: {ctx.workspace_path}")
    else:
        console.print("[dim]No workspace found[/dim]")

    try:
        if ctx.config_manager:
            console.print(f"[green]✓[/green] Configuration loaded")
        else:
            console.print("[dim]No configuration found[/dim]")
    except Exception:
        console.print("[dim]No configuration found[/dim]")

    console.print()
    console.print("Run [cyan]creatimation --help[/cyan] for more information.")
    console.print()


def require_workspace(f):
    """Decorator to require a workspace for command execution."""
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context().find_object(CreatimationContext)
        if ctx:
            ctx.ensure_workspace()
        return f(*args, **kwargs)
    return wrapper


def require_config(f):
    """Decorator to require configuration for command execution."""
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context().find_object(CreatimationContext)
        if ctx and not ctx.config_manager:
            error_console.print("[red]No configuration found[/red]")
            console.print("Initialize configuration with: [cyan]creatimation config init[/cyan]")
            sys.exit(1)
        return f(*args, **kwargs)
    return wrapper