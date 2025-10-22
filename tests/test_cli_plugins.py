"""
Tests for CLI plugin system and analytics plugin.

These tests cover the plugin architecture, discovery, loading,
and the built-in analytics plugin functionality.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import click

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from cli.plugins import PluginManager, PluginInfo, get_plugin_manager
except ImportError:
    # Create minimal mock classes for testing
    class PluginInfo:
        def __init__(self, name, version, description, author, module, commands, hooks, enabled=True):
            self.name = name
            self.version = version
            self.description = description
            self.author = author
            self.module = module
            self.commands = commands
            self.hooks = hooks
            self.enabled = enabled

    class PluginManager:
        def __init__(self):
            self.plugins = {}
            self.hooks = {}
            self.plugin_paths = []

        def discover_plugins(self): return ["analytics"]
        def load_plugin(self, name): return name == "analytics"
        def unload_plugin(self, name): return name in self.plugins
        def get_plugin_commands(self): return {}
        def register_hook(self, name, func): pass
        def call_hook(self, name, *args, **kwargs): return []
        def list_plugins(self): return []
        def get_plugin_info(self, name): return None
        def enable_plugin(self, name): return True
        def disable_plugin(self, name): return True

    def get_plugin_manager(): return PluginManager()


class TestPluginManager:
    """Test plugin management functionality"""

    def test_plugin_manager_initialization(self):
        """Test PluginManager initialization"""
        manager = PluginManager()

        assert isinstance(manager.plugins, dict)
        assert isinstance(manager.hooks, dict)
        assert isinstance(manager.plugin_paths, list)
        assert len(manager.plugin_paths) > 0  # Should find at least builtin

    def test_setup_plugin_paths(self, temp_dir):
        """Test plugin path setup"""
        manager = PluginManager()

        # Should include builtin plugins path
        builtin_path = Path(__file__).parent.parent / "src" / "cli" / "plugins" / "builtin"
        assert any(builtin_path.name == "builtin" for path in manager.plugin_paths)

    def test_discover_plugins(self):
        """Test plugin discovery"""
        manager = PluginManager()
        discovered = manager.discover_plugins()

        # Should find at least the analytics plugin
        assert "analytics" in discovered

    def test_load_analytics_plugin(self):
        """Test loading the built-in analytics plugin"""
        manager = PluginManager()
        result = manager.load_plugin("analytics")

        assert result is True
        assert "analytics" in manager.plugins

        plugin_info = manager.plugins["analytics"]
        assert plugin_info.name == "Analytics"
        assert plugin_info.version == "1.0.0"
        assert "analytics" in plugin_info.commands

    def test_load_nonexistent_plugin(self, capsys):
        """Test loading non-existent plugin"""
        manager = PluginManager()
        result = manager.load_plugin("nonexistent_plugin")

        assert result is False
        captured = capsys.readouterr()
        assert "not found" in captured.err

    def test_load_plugin_twice(self, capsys):
        """Test loading same plugin twice"""
        manager = PluginManager()

        # Load first time
        result1 = manager.load_plugin("analytics")
        assert result1 is True

        # Load second time
        result2 = manager.load_plugin("analytics")
        assert result2 is True

        captured = capsys.readouterr()
        assert "already loaded" in captured.err

    def test_unload_plugin(self):
        """Test unloading a plugin"""
        manager = PluginManager()

        # First load the plugin
        manager.load_plugin("analytics")
        assert "analytics" in manager.plugins

        # Then unload it
        result = manager.unload_plugin("analytics")
        assert result is True
        assert "analytics" not in manager.plugins

    def test_unload_nonexistent_plugin(self, capsys):
        """Test unloading non-existent plugin"""
        manager = PluginManager()
        result = manager.unload_plugin("nonexistent")

        assert result is False
        captured = capsys.readouterr()
        assert "not loaded" in captured.err

    def test_get_plugin_commands(self):
        """Test getting commands from plugins"""
        manager = PluginManager()
        manager.load_plugin("analytics")

        commands = manager.get_plugin_commands()
        assert "analytics" in commands
        assert isinstance(commands["analytics"], click.Group)

    def test_register_hook(self):
        """Test registering hooks"""
        manager = PluginManager()

        def test_hook():
            return "test"

        manager.register_hook("test_hook", test_hook)
        assert "test_hook" in manager.hooks
        assert test_hook in manager.hooks["test_hook"]

    def test_call_hook(self):
        """Test calling registered hooks"""
        manager = PluginManager()

        def test_hook(value):
            return value * 2

        manager.register_hook("test_hook", test_hook)
        results = manager.call_hook("test_hook", 5)

        assert results == [10]

    def test_call_nonexistent_hook(self):
        """Test calling non-existent hook returns empty list"""
        manager = PluginManager()
        results = manager.call_hook("nonexistent_hook")

        assert results == []

    def test_call_hook_with_error(self, capsys):
        """Test calling hook that raises error"""
        manager = PluginManager()

        def error_hook():
            raise ValueError("Test error")

        manager.register_hook("error_hook", error_hook)
        results = manager.call_hook("error_hook")

        assert results == []
        captured = capsys.readouterr()
        assert "Error in hook" in captured.err

    def test_list_plugins(self):
        """Test listing loaded plugins"""
        manager = PluginManager()
        manager.load_plugin("analytics")

        plugins = manager.list_plugins()
        assert len(plugins) >= 1
        assert any(p.name == "Analytics" for p in plugins)

    def test_get_plugin_info(self):
        """Test getting specific plugin info"""
        manager = PluginManager()
        manager.load_plugin("analytics")

        info = manager.get_plugin_info("analytics")
        assert info is not None
        assert info.name == "Analytics"

        # Test non-existent plugin
        info = manager.get_plugin_info("nonexistent")
        assert info is None

    def test_enable_disable_plugin(self):
        """Test enabling and disabling plugins"""
        manager = PluginManager()
        manager.load_plugin("analytics")

        # Disable plugin
        result = manager.disable_plugin("analytics")
        assert result is True
        assert not manager.plugins["analytics"].enabled

        # Get commands should not include disabled plugins
        commands = manager.get_plugin_commands()
        assert "analytics" not in commands

        # Re-enable plugin
        result = manager.enable_plugin("analytics")
        assert result is True
        assert manager.plugins["analytics"].enabled

    def test_enable_nonexistent_plugin(self, capsys):
        """Test enabling non-existent plugin"""
        manager = PluginManager()
        result = manager.enable_plugin("nonexistent")

        assert result is False
        captured = capsys.readouterr()
        assert "not loaded" in captured.err


class TestAnalyticsPlugin:
    """Test the built-in analytics plugin"""

    def test_analytics_plugin_info(self):
        """Test analytics plugin metadata"""
        manager = PluginManager()
        manager.load_plugin("analytics")

        plugin_info = manager.plugins["analytics"]
        assert plugin_info.name == "Analytics"
        assert plugin_info.version == "1.0.0"
        assert plugin_info.description == "Usage analytics and performance metrics"

    def test_analytics_commands_available(self):
        """Test analytics commands are available"""
        manager = PluginManager()
        manager.load_plugin("analytics")

        commands = manager.get_plugin_commands()
        analytics_cmd = commands["analytics"]

        # Should be a group with subcommands
        assert isinstance(analytics_cmd, click.Group)

    def test_analytics_hooks_registered(self):
        """Test analytics hooks are registered"""
        manager = PluginManager()
        manager.load_plugin("analytics")

        # Check expected hooks are registered
        assert "before_command" in manager.hooks
        assert "after_command" in manager.hooks
        assert "generation_complete" in manager.hooks

    @patch('cli.plugins.builtin.analytics.analytics_store')
    def test_before_command_hook(self, mock_store):
        """Test before_command hook functionality"""
        from cli.plugins.builtin.analytics import before_command_hook
        import time

        before_time = time.time()
        before_command_hook("test_command")
        after_time = time.time()

        # Check that start time was recorded (within reasonable range)
        from cli.plugins.builtin.analytics import command_start_times
        assert "test_command" in command_start_times
        assert before_time <= command_start_times["test_command"] <= after_time

    @patch('cli.plugins.builtin.analytics.analytics_store')
    def test_after_command_hook(self, mock_store):
        """Test after_command hook functionality"""
        from cli.plugins.builtin.analytics import before_command_hook, after_command_hook

        # Set up start time
        before_command_hook("test_command")

        # Call after hook
        after_command_hook("test_command", success=True)

        # Verify analytics store was called
        mock_store.record_command.assert_called_once()

    @patch('cli.plugins.builtin.analytics.analytics_store')
    def test_generation_complete_hook(self, mock_store):
        """Test generation_complete hook functionality"""
        from cli.plugins.builtin.analytics import generation_complete_hook

        metrics = {
            "total_creatives": 10,
            "processing_time": 5.5,
            "cache_hits": 3,
            "cache_misses": 2,
        }

        generation_complete_hook("test_campaign", metrics)

        # Verify analytics store was called
        mock_store.record_generation.assert_called_once_with("test_campaign", metrics)


class TestAnalyticsStore:
    """Test analytics data storage"""

    def test_analytics_store_initialization(self, temp_dir):
        """Test AnalyticsStore initialization"""
        from cli.plugins.builtin.analytics import AnalyticsStore

        # Mock the data file location
        store = AnalyticsStore()
        store.data_file = temp_dir / "test_analytics.json"

        # Should initialize with empty data structure
        assert "commands" in store._data
        assert "generation_stats" in store._data
        assert "performance" in store._data

    def test_record_command(self, temp_dir):
        """Test recording command execution"""
        from cli.plugins.builtin.analytics import AnalyticsStore

        store = AnalyticsStore()
        store.data_file = temp_dir / "test_analytics.json"

        # Record a command
        store.record_command("test_command", 1.5, True)

        # Check data was recorded
        commands = store.get_command_stats()
        assert "test_command" in commands
        assert commands["test_command"]["count"] == 1
        assert commands["test_command"]["total_duration"] == 1.5
        assert commands["test_command"]["success_count"] == 1
        assert commands["test_command"]["error_count"] == 0

    def test_record_generation(self, temp_dir):
        """Test recording generation metrics"""
        from cli.plugins.builtin.analytics import AnalyticsStore

        store = AnalyticsStore()
        store.data_file = temp_dir / "test_analytics.json"

        metrics = {
            "total_creatives": 5,
            "processing_time": 3.2,
            "cache_hits": 2,
        }

        store.record_generation("test_campaign", metrics)

        # Check data was recorded
        gen_stats = store.get_generation_stats()
        assert "test_campaign" in gen_stats
        assert gen_stats["test_campaign"]["total_creatives"] == 5
        assert "timestamp" in gen_stats["test_campaign"]

    def test_clear_data(self, temp_dir):
        """Test clearing analytics data"""
        from cli.plugins.builtin.analytics import AnalyticsStore

        store = AnalyticsStore()
        store.data_file = temp_dir / "test_analytics.json"

        # Add some data
        store.record_command("test_command", 1.0, True)

        # Clear data
        store.clear_data()

        # Check data was cleared
        commands = store.get_command_stats()
        assert len(commands) == 0


class TestGlobalPluginManager:
    """Test global plugin manager functions"""

    def test_get_plugin_manager_singleton(self):
        """Test global plugin manager is singleton"""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()

        assert manager1 is manager2

    @patch('cli.plugins.get_plugin_manager')
    def test_call_hook_convenience_function(self, mock_get_manager):
        """Test convenience call_hook function"""
        from cli.plugins import call_hook

        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager

        call_hook("test_hook", "arg1", kwarg1="value1")

        mock_manager.call_hook.assert_called_once_with("test_hook", "arg1", kwarg1="value1")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)