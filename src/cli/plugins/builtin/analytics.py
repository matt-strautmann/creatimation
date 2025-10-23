"""
Analytics plugin for Creatimation CLI.

Provides usage analytics, performance metrics, and reporting capabilities
with privacy-first design and optional data collection.
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import click

# Try relative import first, fall back to absolute import
try:
    from ...utils.output import console, create_table, format_duration
except ImportError:
    try:
        from src.cli.utils.output import console, create_table, format_duration
    except ImportError:
        # Fallback to basic rich imports if utils not available
        from rich.console import Console

        console = Console()

        def create_table(title=None, headers=None):
            from rich.table import Table

            table = Table(title=title)
            if headers:
                for header in headers:
                    table.add_column(header)
            return table

        def format_duration(seconds):
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


# Plugin metadata
PLUGIN_INFO = {
    "name": "Analytics",
    "version": "1.0.0",
    "description": "Usage analytics and performance metrics",
    "author": "Creatimation Team",
    "homepage": "https://github.com/your-org/creatimation",
}

# Commands provided by this plugin
COMMANDS = ["analytics"]

# Hooks registered by this plugin
HOOKS = ["before_command", "after_command", "generation_complete"]


# Analytics data storage
class AnalyticsStore:
    """Simple local analytics storage."""

    def __init__(self):
        self.data_file = Path.home() / ".creatimation" / "analytics.json"
        self.data_file.parent.mkdir(exist_ok=True)
        self._data = self._load_data()

    def _load_data(self) -> dict[str, Any]:
        """Load analytics data from file."""
        if not self.data_file.exists():
            return {
                "commands": {},
                "generation_stats": {},
                "performance": {},
                "created_at": datetime.now().isoformat(),
            }

        try:
            with open(self.data_file) as f:
                return json.load(f)
        except Exception:
            return {
                "commands": {},
                "generation_stats": {},
                "performance": {},
                "created_at": datetime.now().isoformat(),
            }

    def _save_data(self):
        """Save analytics data to file."""
        try:
            with open(self.data_file, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception:
            pass  # Fail silently for analytics

    def record_command(self, command: str, duration: float, success: bool):
        """Record command execution."""
        if "commands" not in self._data:
            self._data["commands"] = {}

        if command not in self._data["commands"]:
            self._data["commands"][command] = {
                "count": 0,
                "total_duration": 0,
                "success_count": 0,
                "error_count": 0,
                "last_used": None,
            }

        stats = self._data["commands"][command]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["last_used"] = datetime.now().isoformat()

        if success:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1

        self._save_data()

    def record_generation(self, campaign_id: str, metrics: dict[str, Any]):
        """Record generation metrics."""
        if "generation_stats" not in self._data:
            self._data["generation_stats"] = {}

        self._data["generation_stats"][campaign_id] = {
            **metrics,
            "timestamp": datetime.now().isoformat(),
        }

        self._save_data()

    def get_command_stats(self) -> dict[str, Any]:
        """Get command usage statistics."""
        return self._data.get("commands", {})

    def get_generation_stats(self) -> dict[str, Any]:
        """Get generation statistics."""
        return self._data.get("generation_stats", {})

    def clear_data(self):
        """Clear all analytics data."""
        self._data = {
            "commands": {},
            "generation_stats": {},
            "performance": {},
            "created_at": datetime.now().isoformat(),
        }
        self._save_data()


# Global analytics store
analytics_store = AnalyticsStore()

# Command execution tracking
command_start_times = {}


def initialize():
    """Initialize the analytics plugin."""
    console.print("[dim]Analytics plugin loaded[/dim]")


def cleanup():
    """Cleanup when plugin is unloaded."""
    pass


def register_hooks() -> dict[str, callable]:
    """Register hook functions."""
    return {
        "before_command": before_command_hook,
        "after_command": after_command_hook,
        "generation_complete": generation_complete_hook,
    }


def before_command_hook(command_name: str, **kwargs):
    """Hook called before command execution."""
    command_start_times[command_name] = time.time()


def after_command_hook(command_name: str, success: bool = True, **kwargs):
    """Hook called after command execution."""
    start_time = command_start_times.get(command_name)
    if start_time:
        duration = time.time() - start_time
        analytics_store.record_command(command_name, duration, success)
        del command_start_times[command_name]


def generation_complete_hook(campaign_id: str, metrics: dict[str, Any], **kwargs):
    """Hook called when generation completes."""
    analytics_store.record_generation(campaign_id, metrics)


def get_commands() -> dict[str, click.Command]:
    """Get commands provided by this plugin."""
    return {"analytics": analytics}


# Analytics command group
@click.group()
def analytics():
    """
    View usage analytics and performance metrics.

    Provides insights into CLI usage patterns, command performance,
    and generation statistics with privacy-first design.

    Examples:
        creatimation analytics summary
        creatimation analytics commands
        creatimation analytics generation
        creatimation analytics clear
    """
    pass


@analytics.command()
@click.option(
    "--period",
    type=click.Choice(["day", "week", "month", "all"]),
    default="week",
    help="Time period for statistics",
)
@click.option(
    "--recent",
    is_flag=True,
    help="Show most recent generation instead of cumulative stats",
)
def summary(period, recent):
    """
    Show analytics summary.

    Displays overview of CLI usage, most used commands,
    and generation statistics for the specified period.
    Use --recent to see the latest generation results.
    """
    console.print()

    if recent:
        console.print("[bold cyan]Recent Generation Results[/bold cyan]")
        _show_recent_generation()
        return
    else:
        console.print("[bold cyan]Analytics Summary[/bold cyan]")

    console.print()

    command_stats = analytics_store.get_command_stats()
    generation_stats = analytics_store.get_generation_stats()

    if not command_stats and not generation_stats:
        console.print("[yellow]No analytics data available[/yellow]")
        console.print("Use Creatimation commands to start collecting data.")
        console.print("Use [cyan]--recent[/cyan] to see the latest generation results.")
        console.print()
        return

    # Commands summary
    if command_stats:
        total_commands = sum(stats["count"] for stats in command_stats.values())
        total_duration = sum(stats["total_duration"] for stats in command_stats.values())
        avg_duration = total_duration / total_commands if total_commands > 0 else 0

        summary_table = create_table(title="Command Usage Summary", headers=["Metric", "Value"])

        summary_table.add_row("Total Commands", str(total_commands))
        summary_table.add_row("Total Time", format_duration(total_duration))
        summary_table.add_row("Average Duration", format_duration(avg_duration))
        summary_table.add_row("Most Used", _get_most_used_command(command_stats))

        console.print(summary_table)
        console.print()

    # Generation summary
    if generation_stats:
        total_campaigns = len(generation_stats)
        total_creatives = sum(
            metrics.get("total_creatives", 0) for metrics in generation_stats.values()
        )

        gen_table = create_table(title="Generation Summary", headers=["Metric", "Value"])

        gen_table.add_row("Campaigns Generated", str(total_campaigns))
        gen_table.add_row("Total Creatives", str(total_creatives))

        if total_campaigns > 0:
            avg_creatives = total_creatives / total_campaigns
            gen_table.add_row("Avg Creatives/Campaign", f"{avg_creatives:.1f}")

        console.print(gen_table)
        console.print()


@analytics.command()
@click.option(
    "--sort",
    type=click.Choice(["usage", "duration", "errors"]),
    default="usage",
    help="Sort commands by metric",
)
@click.option("--limit", type=int, default=10, help="Limit number of commands to show")
def commands(sort, limit):
    """
    Show detailed command statistics.

    Displays usage frequency, performance metrics, and error rates
    for each CLI command.
    """
    console.print()
    console.print("[bold cyan]Command Statistics[/bold cyan]")
    console.print()

    command_stats = analytics_store.get_command_stats()

    if not command_stats:
        console.print("[yellow]No command statistics available[/yellow]")
        console.print()
        return

    # Sort commands
    sorted_commands = _sort_commands(command_stats, sort)

    # Create table
    table = create_table(
        title=f"Commands (sorted by {sort})",
        headers=["Command", "Count", "Avg Duration", "Success Rate", "Last Used"],
    )

    for command, stats in sorted_commands[:limit]:
        avg_duration = stats["total_duration"] / stats["count"] if stats["count"] > 0 else 0
        success_rate = (stats["success_count"] / stats["count"] * 100) if stats["count"] > 0 else 0
        last_used = _format_relative_time(stats.get("last_used"))

        table.add_row(
            command,
            str(stats["count"]),
            format_duration(avg_duration),
            f"{success_rate:.1f}%",
            last_used,
        )

    console.print(table)
    console.print()


@analytics.command()
@click.option("--limit", type=int, default=10, help="Limit number of campaigns to show")
def generation(limit):
    """
    Show generation statistics.

    Displays metrics for recent campaign generations including
    creative counts, processing times, and cache performance.
    """
    console.print()
    console.print("[bold cyan]Generation Statistics[/bold cyan]")
    console.print()

    generation_stats = analytics_store.get_generation_stats()

    if not generation_stats:
        console.print("[yellow]No generation statistics available[/yellow]")
        console.print()
        return

    # Sort by timestamp (most recent first)
    sorted_campaigns = sorted(
        generation_stats.items(), key=lambda x: x[1].get("timestamp", ""), reverse=True
    )

    # Create table
    table = create_table(
        title="Recent Generations",
        headers=["Campaign", "Creatives", "Processing Time", "Cache Hit Rate", "Generated"],
    )

    for campaign_id, metrics in sorted_campaigns[:limit]:
        creatives = metrics.get("total_creatives", 0)
        proc_time = metrics.get("processing_time", 0)

        cache_hits = metrics.get("cache_hits", 0)
        cache_misses = metrics.get("cache_misses", 0)
        total_cache = cache_hits + cache_misses
        hit_rate = (cache_hits / total_cache * 100) if total_cache > 0 else 0

        generated_time = _format_relative_time(metrics.get("timestamp"))

        table.add_row(
            campaign_id,
            str(creatives),
            format_duration(proc_time),
            f"{hit_rate:.1f}%",
            generated_time,
        )

    console.print(table)
    console.print()


@analytics.command()
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
def clear(confirm):
    """
    Clear all analytics data.

    Removes all stored usage statistics and generation metrics.
    This action cannot be undone.
    """
    if not confirm:
        if not click.confirm("Are you sure you want to clear all analytics data?"):
            console.print("Operation cancelled.")
            return

    analytics_store.clear_data()

    console.print()
    console.print("[green]✓[/green] Analytics data cleared")
    console.print()


# Helper functions
def _get_most_used_command(command_stats: dict[str, Any]) -> str:
    """Get the most frequently used command."""
    if not command_stats:
        return "None"

    most_used = max(command_stats.items(), key=lambda x: x[1]["count"])
    return f"{most_used[0]} ({most_used[1]['count']} times)"


def _sort_commands(command_stats: dict[str, Any], sort_by: str) -> list[tuple]:
    """Sort commands by specified metric."""
    if sort_by == "usage":
        return sorted(command_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    elif sort_by == "duration":
        return sorted(
            command_stats.items(),
            key=lambda x: x[1]["total_duration"] / x[1]["count"] if x[1]["count"] > 0 else 0,
            reverse=True,
        )
    elif sort_by == "errors":
        return sorted(command_stats.items(), key=lambda x: x[1]["error_count"], reverse=True)
    else:
        return list(command_stats.items())


def _format_relative_time(timestamp_str: str) -> str:
    """Format timestamp as relative time."""
    if not timestamp_str:
        return "Never"

    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now()
        delta = now - timestamp

        if delta < timedelta(minutes=1):
            return "Just now"
        elif delta < timedelta(hours=1):
            minutes = int(delta.total_seconds() / 60)
            return f"{minutes}m ago"
        elif delta < timedelta(days=1):
            hours = int(delta.total_seconds() / 3600)
            return f"{hours}h ago"
        elif delta < timedelta(days=7):
            days = delta.days
            return f"{days}d ago"
        else:
            return timestamp.strftime("%Y-%m-%d")

    except Exception:
        return "Unknown"


def _show_recent_generation():
    """Show the most recent generation results."""
    generation_stats = analytics_store.get_generation_stats()

    if not generation_stats:
        console.print("[yellow]No generation data available[/yellow]")
        console.print("Run a campaign generation to see results here.")
        console.print()
        return

    # Filter out simulations
    real_generations = {
        campaign_id: metrics
        for campaign_id, metrics in generation_stats.items()
        if not metrics.get("simulation", False)
    }

    if not real_generations:
        console.print("[yellow]No real generation data available[/yellow]")
        console.print("Only simulation runs found. Run a real campaign generation to see results here.")
        console.print()
        return

    # Get most recent real generation by timestamp
    most_recent = max(
        real_generations.items(),
        key=lambda x: x[1].get("timestamp", "")
    )
    campaign_id, metrics = most_recent

    console.print()

    # Recent generation table
    table = create_table(title="Most Recent Generation", headers=["Metric", "Value"])

    table.add_row("Campaign ID", campaign_id)
    table.add_row("Total Creatives", str(metrics.get("total_creatives", 0)))
    table.add_row("Cache Hits", str(metrics.get("cache_hits", 0)))
    table.add_row("Cache Misses", str(metrics.get("cache_misses", 0)))

    # Calculate cache hit rate
    cache_hits = metrics.get("cache_hits", 0)
    cache_misses = metrics.get("cache_misses", 0)
    total_cache_ops = cache_hits + cache_misses
    if total_cache_ops > 0:
        hit_rate = (cache_hits / total_cache_ops) * 100
        table.add_row("Cache Hit Rate", f"{hit_rate:.1f}%")

    processing_time = metrics.get("processing_time", 0)
    table.add_row("Processing Time", format_duration(processing_time))

    success = metrics.get("success", False)
    status = "✅ Success" if success else "❌ Failed"
    table.add_row("Status", status)

    if "timestamp" in metrics:
        # Parse and format timestamp
        try:
            from datetime import datetime
            ts = datetime.fromisoformat(metrics["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            table.add_row("Completed At", ts)
        except:
            pass

    console.print(table)
    console.print()

    # Additional insights
    if success and metrics.get("total_creatives", 0) > 0:
        creatives_per_minute = (metrics.get("total_creatives", 0) / processing_time) * 60
        console.print(f"[green]Performance:[/green] {creatives_per_minute:.1f} creatives/minute")

        cache_total = cache_hits + cache_misses
        if cache_total > 0:
            cache_efficiency = (cache_hits / cache_total) * 100
            if cache_efficiency > 50:
                console.print(f"[green]Cache:[/green] Excellent efficiency ({cache_efficiency:.1f}%)")
            elif cache_efficiency > 0:
                console.print(f"[yellow]Cache:[/yellow] Room for improvement ({cache_efficiency:.1f}%)")
            else:
                console.print(f"[red]Cache:[/red] No cache hits - consider optimizing")

    console.print()
