"""
Tests for CLI output utilities and rich formatting.

These tests cover the output formatting, progress tracking,
and rich console functionality.
"""

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console
from rich.table import Table

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli.utils.output import (
    console,
    error_console,
    create_progress_bar,
    create_status_indicator,
    print_header,
    print_success,
    print_error,
    print_warning,
    print_info,
    create_table,
    create_info_panel,
    create_tree,
    format_size,
    format_duration,
    format_percentage,
    create_command_help_table,
    create_config_table,
    create_status_table,
    print_welcome_banner,
    with_spinner,
    ProgressTracker,
)
from pathlib import Path


class TestConsoleSetup:
    """Test console configuration and setup"""

    def test_console_instances_exist(self):
        """Test that console instances are properly configured"""
        assert console is not None
        assert error_console is not None
        assert isinstance(console, Console)
        assert isinstance(error_console, Console)

    def test_console_theme(self):
        """Test that console has custom theme"""
        # Check that theme colors are available
        theme = console._theme
        assert theme is not None
        assert "primary" in theme.styles
        assert "success" in theme.styles
        assert "error" in theme.styles


class TestProgressAndStatus:
    """Test progress bars and status indicators"""

    def test_create_progress_bar_basic(self):
        """Test creating basic progress bar"""
        progress = create_progress_bar()
        assert progress is not None

    def test_create_progress_bar_with_options(self):
        """Test creating progress bar with options"""
        progress = create_progress_bar(
            show_speed=True,
            show_time=False,
            show_percentage=True
        )
        assert progress is not None

    def test_create_status_indicator(self):
        """Test creating status indicator"""
        status = create_status_indicator("Processing...")
        assert status is not None

    def test_create_status_indicator_custom_spinner(self):
        """Test creating status indicator with custom spinner"""
        status = create_status_indicator("Loading...", spinner="arc")
        assert status is not None

    def test_progress_tracker_context_manager(self):
        """Test ProgressTracker as context manager"""
        with ProgressTracker(3, "Testing") as tracker:
            assert tracker.total_steps == 3
            assert tracker.current_step == 0

            tracker.step("Step 1")
            assert tracker.current_step == 1

            tracker.step("Step 2")
            assert tracker.current_step == 2

    def test_progress_tracker_set_total(self):
        """Test updating total steps in ProgressTracker"""
        with ProgressTracker(3, "Testing") as tracker:
            tracker.set_total(5)
            assert tracker.total_steps == 5


class TestPrintFunctions:
    """Test print utility functions"""

    def test_print_success(self, capsys):
        """Test print_success function"""
        print_success("Operation completed")
        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "Operation completed" in captured.out

    def test_print_success_with_details(self, capsys):
        """Test print_success with details"""
        print_success("Operation completed", "All files processed")
        captured = capsys.readouterr()
        assert "✓" in captured.out
        assert "Operation completed" in captured.out
        assert "All files processed" in captured.out

    def test_print_error(self, capsys):
        """Test print_error function"""
        print_error("Something went wrong")
        captured = capsys.readouterr()
        assert "✗" in captured.err
        assert "Something went wrong" in captured.err

    def test_print_warning(self, capsys):
        """Test print_warning function"""
        print_warning("Be careful")
        captured = capsys.readouterr()
        assert "⚠" in captured.out
        assert "Be careful" in captured.out

    def test_print_info(self, capsys):
        """Test print_info function"""
        print_info("Information message")
        captured = capsys.readouterr()
        assert "ℹ" in captured.out
        assert "Information message" in captured.out

    def test_print_header(self, capsys):
        """Test print_header function"""
        print_header("Test Header")
        captured = capsys.readouterr()
        assert "Test Header" in captured.out

    def test_print_header_with_subtitle(self, capsys):
        """Test print_header with subtitle"""
        print_header("Main Title", "Subtitle")
        captured = capsys.readouterr()
        assert "Main Title" in captured.out
        assert "Subtitle" in captured.out


class TestTableCreation:
    """Test table creation utilities"""

    def test_create_table_basic(self):
        """Test creating basic table"""
        table = create_table()
        assert isinstance(table, Table)

    def test_create_table_with_title(self):
        """Test creating table with title"""
        table = create_table(title="Test Table")
        assert isinstance(table, Table)
        assert table.title == "Test Table"

    def test_create_table_with_headers(self):
        """Test creating table with headers"""
        headers = ["Name", "Value", "Status"]
        table = create_table(headers=headers)
        assert isinstance(table, Table)
        assert len(table.columns) == 3

    def test_create_command_help_table(self):
        """Test creating command help table"""
        commands = {
            "generate": {"description": "Generate creatives"},
            "validate": {"description": "Validate inputs"},
        }
        table = create_command_help_table(commands)
        assert isinstance(table, Table)

    def test_create_config_table(self):
        """Test creating configuration table"""
        config_data = {
            "api_key": "secret",
            "timeout": 30,
            "nested": {
                "option1": "value1",
                "option2": "value2"
            }
        }
        table = create_config_table(config_data)
        assert isinstance(table, Table)

    def test_create_status_table(self):
        """Test creating status table"""
        items = {
            "Database": "ok",
            "Cache": "warning",
            "API": "error",
            "Unknown": "unknown"
        }
        table = create_status_table(items)
        assert isinstance(table, Table)


class TestFormatFunctions:
    """Test formatting utility functions"""

    def test_format_size_bytes(self):
        """Test formatting size in bytes"""
        assert format_size(0) == "0 B"
        assert format_size(1024) == "1.0 KB"
        assert format_size(1024 * 1024) == "1.0 MB"
        assert format_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_format_size_large(self):
        """Test formatting very large sizes"""
        size_tb = 1024 ** 4
        result = format_size(size_tb)
        assert "TB" in result

    def test_format_duration_seconds(self):
        """Test formatting duration in seconds"""
        assert format_duration(30.5) == "30.5s"
        assert format_duration(5.0) == "5.0s"

    def test_format_duration_minutes(self):
        """Test formatting duration in minutes"""
        assert format_duration(90) == "1m 30s"
        assert format_duration(120) == "2m 0s"

    def test_format_duration_hours(self):
        """Test formatting duration in hours"""
        assert format_duration(3661) == "1h 1m"
        assert format_duration(7200) == "2h 0m"

    def test_format_percentage_normal(self):
        """Test formatting percentage"""
        assert format_percentage(25, 100) == "25.0%"
        assert format_percentage(33, 100) == "33.0%"

    def test_format_percentage_zero_total(self):
        """Test formatting percentage with zero total"""
        assert format_percentage(10, 0) == "0.0%"

    def test_format_percentage_float_precision(self):
        """Test formatting percentage with float precision"""
        result = format_percentage(1, 3)
        assert "33.3%" in result or "33.4%" in result  # Allow for rounding


class TestRichComponents:
    """Test Rich component creation"""

    def test_create_info_panel(self):
        """Test creating info panel"""
        panel = create_info_panel("Test content", "Test Title")
        assert panel is not None

    def test_create_tree(self):
        """Test creating tree structure"""
        tree = create_tree("Root Node")
        assert tree is not None

    def test_create_tree_with_children(self):
        """Test creating tree with children"""
        tree = create_tree("Root")
        child = tree.add("Child 1")
        grandchild = child.add("Grandchild")

        assert tree is not None
        assert child is not None
        assert grandchild is not None


class TestWelcomeBanner:
    """Test welcome banner functionality"""

    def test_print_welcome_banner_default(self, capsys):
        """Test printing welcome banner with defaults"""
        print_welcome_banner()
        captured = capsys.readouterr()
        assert "Creatimation" in captured.out
        assert "2.0" in captured.out

    def test_print_welcome_banner_custom(self, capsys):
        """Test printing welcome banner with custom values"""
        print_welcome_banner("CustomApp", "1.0", "Custom Subtitle")
        captured = capsys.readouterr()
        assert "CustomApp" in captured.out
        assert "1.0" in captured.out
        assert "Custom Subtitle" in captured.out


class TestSpinnerContext:
    """Test spinner context manager"""

    def test_with_spinner_basic(self):
        """Test with_spinner function"""
        def test_func():
            return "result"

        result = with_spinner(test_func, "Processing...")
        assert result == "result"

    def test_with_spinner_with_args(self):
        """Test with_spinner with function arguments"""
        def test_func(a, b, c=None):
            return a + b + (c or 0)

        result = with_spinner(test_func, "Processing...", 1, 2, c=3)
        assert result == 6

    def test_with_spinner_exception_handling(self):
        """Test with_spinner handles exceptions"""
        def error_func():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            with_spinner(error_func, "Processing...")


class TestConsoleFileOutput:
    """Test console output to files/strings"""

    def test_console_capture_output(self):
        """Test capturing console output"""
        string_io = io.StringIO()
        test_console = Console(file=string_io, width=80)

        test_console.print("Test message")
        output = string_io.getvalue()
        assert "Test message" in output

    def test_error_console_separate_stream(self):
        """Test that error console uses stderr"""
        # This is more of a configuration test
        assert error_console.file.name == "<stderr>"  # Should use stderr by default


class TestLayoutAndDashboard:
    """Test layout and dashboard utilities"""

    def test_create_dashboard_layout(self):
        """Test creating dashboard layout"""
        from cli.utils.output import create_dashboard_layout

        layout = create_dashboard_layout()
        assert layout is not None
        assert "header" in layout
        assert "main" in layout
        assert "footer" in layout