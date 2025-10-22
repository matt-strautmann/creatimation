"""
Output utilities for rich terminal experience.

Provides consistent output formatting with rich styling,
progress indicators, and professional visual hierarchy.
"""

from typing import Any

from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.status import Status
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.traceback import install as install_traceback
from rich.tree import Tree

# Custom theme for creatimation
CREATIMATION_THEME = Theme(
    {
        "primary": "cyan",
        "secondary": "blue",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "info": "dim cyan",
        "prompt": "magenta",
        "highlight": "bold cyan",
        "dim": "dim white",
        "brand": "bold blue",
        "code": "green",
        "path": "blue",
        "value": "green",
        "key": "cyan",
        "command": "bold cyan",
        "option": "yellow",
        "progress.description": "white",
        "progress.percentage": "cyan",
        "progress.download": "green",
        "progress.filesize": "blue",
        "bar.back": "grey23",
        "bar.complete": "cyan",
        "bar.finished": "green",
    }
)


# Global console instances
console = Console(
    theme=CREATIMATION_THEME,
    highlighter=ReprHighlighter(),
    force_terminal=None,
    soft_wrap=True,
    width=None,
    stderr=False,
)

error_console = Console(
    theme=CREATIMATION_THEME,
    highlighter=ReprHighlighter(),
    force_terminal=None,
    soft_wrap=True,
    width=None,
    stderr=True,
)


def setup_console(main_console: Console | None = None):
    """
    Setup console configuration and error handling.

    Args:
        main_console: Optional console instance to configure
    """
    # Install rich traceback handling
    install_traceback(
        console=error_console,
        show_locals=False,
        suppress=[
            # Suppress common framework modules
            "click",
            "rich",
        ],
    )

    # Configure main console if provided
    if main_console:
        global console
        console = main_console


def create_progress_bar(
    show_speed: bool = False, show_time: bool = True, show_percentage: bool = True
) -> Progress:
    """
    Create a standardized progress bar for operations.

    Args:
        show_speed: Whether to show transfer speed
        show_time: Whether to show time information
        show_percentage: Whether to show percentage

    Returns:
        Configured Progress instance
    """
    columns = [
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
    ]

    if show_percentage:
        columns.extend(
            [
                BarColumn(),
                TaskProgressColumn(),
            ]
        )

    if show_time:
        columns.extend(
            [
                TimeElapsedColumn(),
                TimeRemainingColumn(),
            ]
        )

    if show_speed:
        columns.append(TextColumn("[progress.filesize]{task.fields[speed]}"))

    return Progress(
        *columns,
        console=console,
        transient=False,
        refresh_per_second=10,
    )


def create_status_indicator(message: str, spinner: str = "dots") -> Status:
    """
    Create a status indicator for long-running operations.

    Args:
        message: Status message to display
        spinner: Spinner style (dots, arc, line, etc.)

    Returns:
        Configured Status instance
    """
    return Status(message, console=console, spinner=spinner, speed=1.0)


def print_header(title: str, subtitle: str | None = None, style: str = "primary"):
    """
    Print a formatted header with consistent styling.

    Args:
        title: Main header title
        subtitle: Optional subtitle
        style: Color style for the header
    """
    console.print()

    header_text = Text(title, style=f"bold {style}")
    if subtitle:
        header_text.append(f" - {subtitle}", style="dim")

    console.print(header_text)
    console.print("─" * len(title), style=style)
    console.print()


def print_success(message: str, details: str | None = None):
    """
    Print a success message with consistent formatting.

    Args:
        message: Success message
        details: Optional additional details
    """
    console.print(f"[success]✓[/success] {message}")
    if details:
        console.print(f"[dim]{details}[/dim]")


def print_error(message: str, details: str | None = None):
    """
    Print an error message with consistent formatting.

    Args:
        message: Error message
        details: Optional additional details
    """
    error_console.print(f"[error]✗[/error] {message}")
    if details:
        error_console.print(f"[dim]{details}[/dim]")


def print_warning(message: str, details: str | None = None):
    """
    Print a warning message with consistent formatting.

    Args:
        message: Warning message
        details: Optional additional details
    """
    console.print(f"[warning]⚠[/warning] {message}")
    if details:
        console.print(f"[dim]{details}[/dim]")


def print_info(message: str, details: str | None = None):
    """
    Print an info message with consistent formatting.

    Args:
        message: Info message
        details: Optional additional details
    """
    console.print(f"[info]ℹ[/info] {message}")
    if details:
        console.print(f"[dim]{details}[/dim]")


def create_table(
    title: str | None = None,
    headers: list | None = None,
    show_header: bool = True,
    show_lines: bool = False,
) -> Table:
    """
    Create a standardized table with consistent styling.

    Args:
        title: Optional table title
        headers: List of column headers
        show_header: Whether to show the header row
        show_lines: Whether to show grid lines

    Returns:
        Configured Table instance
    """
    table = Table(
        title=title,
        show_header=show_header,
        show_lines=show_lines,
        header_style="bold cyan",
        title_style="bold blue",
    )

    if headers:
        for header in headers:
            table.add_column(header, style="white")

    return table


def create_info_panel(content: str, title: str | None = None, style: str = "primary") -> Panel:
    """
    Create an information panel with consistent styling.

    Args:
        content: Panel content
        title: Optional panel title
        style: Panel border style

    Returns:
        Configured Panel instance
    """
    return Panel(content, title=title, border_style=style, padding=(1, 2))


def create_tree(root_label: str) -> Tree:
    """
    Create a tree structure with consistent styling.

    Args:
        root_label: Label for the root node

    Returns:
        Configured Tree instance
    """
    return Tree(root_label, style="primary", guide_style="dim")


def format_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"

    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


def format_percentage(value: float, total: float) -> str:
    """
    Format a percentage with consistent styling.

    Args:
        value: Current value
        total: Total value

    Returns:
        Formatted percentage string
    """
    if total == 0:
        return "0.0%"

    percentage = (value / total) * 100
    return f"{percentage:.1f}%"


def create_command_help_table(commands: dict[str, dict[str, str]]) -> Table:
    """
    Create a help table for commands.

    Args:
        commands: Dictionary of command info with 'description' keys

    Returns:
        Formatted help table
    """
    table = create_table(
        title="Available Commands", headers=["Command", "Description"], show_lines=True
    )

    for command, info in commands.items():
        table.add_row(
            f"[command]{command}[/command]", info.get("description", "No description available")
        )

    return table


def create_config_table(config_data: dict[str, Any]) -> Table:
    """
    Create a table for configuration display.

    Args:
        config_data: Configuration dictionary

    Returns:
        Formatted configuration table
    """
    table = create_table(title="Configuration", headers=["Setting", "Value"], show_lines=False)

    def add_config_rows(data: dict[str, Any], prefix: str = ""):
        for key, value in data.items():
            if isinstance(value, dict):
                add_config_rows(value, f"{prefix}{key}.")
            else:
                full_key = f"{prefix}{key}"
                formatted_value = str(value) if value is not None else "[dim]not set[/dim]"
                table.add_row(f"[key]{full_key}[/key]", f"[value]{formatted_value}[/value]")

    add_config_rows(config_data)
    return table


def create_status_table(items: dict[str, str]) -> Table:
    """
    Create a status table with icons.

    Args:
        items: Dictionary of item names to status values

    Returns:
        Formatted status table
    """
    table = create_table(title="Status", headers=["Component", "Status"], show_header=True)

    status_icons = {
        "ok": "[success]✓[/success]",
        "error": "[error]✗[/error]",
        "warning": "[warning]⚠[/warning]",
        "info": "[info]ℹ[/info]",
        "unknown": "[dim]?[/dim]",
    }

    for item, status in items.items():
        icon = status_icons.get(status.lower(), status_icons["unknown"])
        table.add_row(item, f"{icon} {status}")

    return table


def print_welcome_banner(
    app_name: str = "Creatimation",
    version: str = "2.0",
    subtitle: str = "Creative Automation Pipeline",
):
    """
    Print a welcome banner for the application.

    Args:
        app_name: Application name
        version: Version string
        subtitle: Application subtitle
    """
    console.print()

    # Create welcome text
    welcome_text = Text()
    welcome_text.append("🎨 ", style="primary")
    welcome_text.append(app_name, style="brand")
    welcome_text.append(f" v{version}", style="dim")
    welcome_text.append(f"\n{subtitle}", style="secondary")

    # Create panel
    panel = Panel(
        welcome_text,
        title="Welcome",
        subtitle="Creative Automation",
        border_style="primary",
        padding=(1, 2),
    )

    console.print(panel)
    console.print()


def create_dashboard_layout() -> Layout:
    """
    Create a dashboard layout for complex displays.

    Returns:
        Configured Layout instance
    """
    layout = Layout()

    layout.split_column(
        Layout(name="header", size=3), Layout(name="main"), Layout(name="footer", size=3)
    )

    layout["main"].split_row(Layout(name="left"), Layout(name="right"))

    return layout


def with_spinner(func, message: str = "Working...", *args, **kwargs):
    """
    Execute a function with a spinner indicator.

    Args:
        func: Function to execute
        message: Spinner message
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result
    """
    with create_status_indicator(message):
        return func(*args, **kwargs)


class ProgressTracker:
    """
    Context manager for tracking multi-step progress.
    """

    def __init__(self, total_steps: int, description: str = "Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.progress = None
        self.task = None

    def __enter__(self):
        self.progress = create_progress_bar()
        self.task = self.progress.add_task(self.description, total=self.total_steps)
        self.progress.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.__exit__(exc_type, exc_val, exc_tb)

    def step(self, message: str | None = None):
        """Advance to the next step."""
        self.current_step += 1
        if self.progress and self.task:
            if message:
                self.progress.update(self.task, description=message, completed=self.current_step)
            else:
                self.progress.update(self.task, completed=self.current_step)

    def set_total(self, total: int):
        """Update the total number of steps."""
        self.total_steps = total
        if self.progress and self.task:
            self.progress.update(self.task, total=total)


# Export commonly used functions
__all__ = [
    "console",
    "error_console",
    "setup_console",
    "create_progress_bar",
    "create_status_indicator",
    "print_header",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "create_table",
    "create_info_panel",
    "create_tree",
    "format_size",
    "format_duration",
    "format_percentage",
    "create_command_help_table",
    "create_config_table",
    "create_status_table",
    "print_welcome_banner",
    "create_dashboard_layout",
    "with_spinner",
    "ProgressTracker",
]
