"""
Plugin system for Creatimation CLI.

Provides plugin architecture that allows extending
the CLI with custom commands, hooks, and functionality.
"""

import importlib
import importlib.util
import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from ..utils.output import console, error_console, print_warning


@dataclass
class PluginInfo:
    """Information about a loaded plugin."""

    name: str
    version: str
    description: str
    author: str
    module: Any
    commands: list[str]
    hooks: list[str]
    enabled: bool = True


class PluginManager:
    """
    Manages CLI plugins with discovery, loading, and lifecycle management.

    Supports both built-in plugins and external plugins with automatic
    discovery and safe loading.
    """

    def __init__(self):
        self.plugins: dict[str, PluginInfo] = {}
        self.hooks: dict[str, list[Callable]] = {}
        self.plugin_paths: list[Path] = []
        self._setup_plugin_paths()

    def _setup_plugin_paths(self):
        """Setup plugin discovery paths."""
        # Built-in plugins directory
        builtin_plugins = Path(__file__).parent / "builtin"
        if builtin_plugins.exists():
            self.plugin_paths.append(builtin_plugins)

        # User plugins directory
        user_plugins = Path.home() / ".creatimation" / "plugins"
        if user_plugins.exists():
            self.plugin_paths.append(user_plugins)

        # Workspace plugins directory
        workspace_plugins = Path.cwd() / ".creatimation" / "plugins"
        if workspace_plugins.exists():
            self.plugin_paths.append(workspace_plugins)

        # Environment variable plugin paths
        env_paths = os.getenv("CREATIMATION_PLUGIN_PATH", "")
        if env_paths:
            for path_str in env_paths.split(os.pathsep):
                path = Path(path_str)
                if path.exists():
                    self.plugin_paths.append(path)

    def discover_plugins(self) -> list[str]:
        """
        Discover available plugins in configured paths.

        Returns:
            List of discovered plugin names
        """
        discovered = []

        for plugin_path in self.plugin_paths:
            if not plugin_path.exists():
                continue

            for item in plugin_path.iterdir():
                if item.name.startswith("__"):
                    continue  # Skip __pycache__, __init__.py, etc.

                if item.is_dir() and (item / "__init__.py").exists():
                    # Python package plugin
                    discovered.append(item.name)
                elif item.is_file() and item.suffix == ".py":
                    # Single file plugin
                    discovered.append(item.stem)

        return list(set(discovered))  # Remove duplicates

    def load_plugin(self, plugin_name: str) -> bool:
        """
        Load a specific plugin by name.

        Args:
            plugin_name: Name of the plugin to load

        Returns:
            True if loaded successfully, False otherwise
        """
        if plugin_name in self.plugins:
            print_warning(f"Plugin '{plugin_name}' is already loaded")
            return True

        # Find plugin in search paths
        plugin_module = None
        for plugin_path in self.plugin_paths:
            if not plugin_path.exists():
                continue

            # Try package-style plugin
            package_path = plugin_path / plugin_name
            if package_path.is_dir() and (package_path / "__init__.py").exists():
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"creatimation_plugin_{plugin_name}", package_path / "__init__.py"
                    )
                    plugin_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin_module)
                    break
                except Exception as e:
                    error_console.print(f"Failed to load package plugin '{plugin_name}': {e}")
                    continue

            # Try single-file plugin
            file_path = plugin_path / f"{plugin_name}.py"
            if file_path.is_file():
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"creatimation_plugin_{plugin_name}", file_path
                    )
                    plugin_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(plugin_module)
                    break
                except Exception as e:
                    error_console.print(f"Failed to load file plugin '{plugin_name}': {e}")
                    continue

        if not plugin_module:
            error_console.print(f"Plugin '{plugin_name}' not found")
            return False

        # Validate plugin structure
        if not hasattr(plugin_module, "PLUGIN_INFO"):
            error_console.print(f"Plugin '{plugin_name}' missing PLUGIN_INFO")
            return False

        plugin_info_dict = plugin_module.PLUGIN_INFO
        required_fields = ["name", "version", "description", "author"]

        for field in required_fields:
            if field not in plugin_info_dict:
                error_console.print(f"Plugin '{plugin_name}' missing required field: {field}")
                return False

        # Create plugin info
        plugin_info = PluginInfo(
            name=plugin_info_dict["name"],
            version=plugin_info_dict["version"],
            description=plugin_info_dict["description"],
            author=plugin_info_dict["author"],
            module=plugin_module,
            commands=getattr(plugin_module, "COMMANDS", []),
            hooks=getattr(plugin_module, "HOOKS", []),
        )

        # Initialize plugin
        if hasattr(plugin_module, "initialize"):
            try:
                plugin_module.initialize()
            except Exception as e:
                error_console.print(f"Failed to initialize plugin '{plugin_name}': {e}")
                return False

        # Register hooks
        if hasattr(plugin_module, "register_hooks"):
            try:
                hooks = plugin_module.register_hooks()
                for hook_name, hook_func in hooks.items():
                    self.register_hook(hook_name, hook_func)
            except Exception as e:
                error_console.print(f"Failed to register hooks for plugin '{plugin_name}': {e}")

        # Store plugin
        self.plugins[plugin_name] = plugin_info

        console.print(f"[green]✓[/green] Loaded plugin: {plugin_info.name} v{plugin_info.version}")
        return True

    def load_all_plugins(self) -> int:
        """
        Load all discovered plugins.

        Returns:
            Number of successfully loaded plugins
        """
        discovered = self.discover_plugins()
        loaded_count = 0

        for plugin_name in discovered:
            if self.load_plugin(plugin_name):
                loaded_count += 1

        return loaded_count

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a specific plugin.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            True if unloaded successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            print_warning(f"Plugin '{plugin_name}' is not loaded")
            return False

        plugin_info = self.plugins[plugin_name]

        # Call cleanup if available
        if hasattr(plugin_info.module, "cleanup"):
            try:
                plugin_info.module.cleanup()
            except Exception as e:
                error_console.print(f"Error during plugin cleanup: {e}")

        # Remove hooks registered by this plugin
        for hook_name in list(self.hooks.keys()):
            self.hooks[hook_name] = [
                hook
                for hook in self.hooks[hook_name]
                if getattr(hook, "_plugin_name", None) != plugin_name
            ]
            if not self.hooks[hook_name]:
                del self.hooks[hook_name]

        # Remove plugin
        del self.plugins[plugin_name]

        console.print(f"[green]✓[/green] Unloaded plugin: {plugin_info.name}")
        return True

    def get_plugin_commands(self) -> dict[str, click.Command]:
        """
        Get all commands provided by loaded plugins.

        Returns:
            Dictionary mapping command names to Click command objects
        """
        commands = {}

        for plugin_info in self.plugins.values():
            if not plugin_info.enabled:
                continue

            if hasattr(plugin_info.module, "get_commands"):
                try:
                    plugin_commands = plugin_info.module.get_commands()
                    for cmd_name, cmd_obj in plugin_commands.items():
                        # Add plugin metadata to command
                        cmd_obj._plugin_name = plugin_info.name
                        commands[cmd_name] = cmd_obj
                except Exception as e:
                    error_console.print(
                        f"Error getting commands from plugin '{plugin_info.name}': {e}"
                    )

        return commands

    def register_hook(self, hook_name: str, hook_func: Callable):
        """
        Register a hook function.

        Args:
            hook_name: Name of the hook
            hook_func: Function to call for this hook
        """
        if hook_name not in self.hooks:
            self.hooks[hook_name] = []

        self.hooks[hook_name].append(hook_func)

    def call_hook(self, hook_name: str, *args, **kwargs) -> list[Any]:
        """
        Call all registered functions for a hook.

        Args:
            hook_name: Name of the hook to call
            *args: Positional arguments to pass to hook functions
            **kwargs: Keyword arguments to pass to hook functions

        Returns:
            List of results from hook functions
        """
        if hook_name not in self.hooks:
            return []

        results = []
        for hook_func in self.hooks[hook_name]:
            try:
                result = hook_func(*args, **kwargs)
                results.append(result)
            except Exception as e:
                error_console.print(f"Error in hook '{hook_name}': {e}")

        return results

    def list_plugins(self) -> list[PluginInfo]:
        """
        Get list of all loaded plugins.

        Returns:
            List of PluginInfo objects
        """
        return list(self.plugins.values())

    def get_plugin_info(self, plugin_name: str) -> PluginInfo | None:
        """
        Get information about a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            PluginInfo object or None if not found
        """
        return self.plugins.get(plugin_name)

    def enable_plugin(self, plugin_name: str) -> bool:
        """
        Enable a loaded plugin.

        Args:
            plugin_name: Name of the plugin to enable

        Returns:
            True if enabled successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            error_console.print(f"Plugin '{plugin_name}' is not loaded")
            return False

        self.plugins[plugin_name].enabled = True
        console.print(f"[green]✓[/green] Enabled plugin: {plugin_name}")
        return True

    def disable_plugin(self, plugin_name: str) -> bool:
        """
        Disable a loaded plugin.

        Args:
            plugin_name: Name of the plugin to disable

        Returns:
            True if disabled successfully, False otherwise
        """
        if plugin_name not in self.plugins:
            error_console.print(f"Plugin '{plugin_name}' is not loaded")
            return False

        self.plugins[plugin_name].enabled = False
        console.print(f"[yellow]⚠[/yellow] Disabled plugin: {plugin_name}")
        return True


# Global plugin manager instance
_plugin_manager = None


def get_plugin_manager() -> PluginManager:
    """Get the global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def load_plugins():
    """Load all available plugins."""
    manager = get_plugin_manager()
    return manager.load_all_plugins()


def call_hook(hook_name: str, *args, **kwargs):
    """Convenience function to call a hook."""
    manager = get_plugin_manager()
    return manager.call_hook(hook_name, *args, **kwargs)


# Common hook names
class Hooks:
    """Standard hook names for plugin integration."""

    # CLI lifecycle hooks
    CLI_STARTUP = "cli_startup"
    CLI_SHUTDOWN = "cli_shutdown"

    # Command hooks
    BEFORE_COMMAND = "before_command"
    AFTER_COMMAND = "after_command"
    COMMAND_ERROR = "command_error"

    # Generation pipeline hooks
    BEFORE_GENERATION = "before_generation"
    AFTER_GENERATION = "after_generation"
    GENERATION_ERROR = "generation_error"

    # Cache hooks
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"

    # Workspace hooks
    WORKSPACE_CREATED = "workspace_created"
    WORKSPACE_LOADED = "workspace_loaded"

    # Configuration hooks
    CONFIG_LOADED = "config_loaded"
    CONFIG_CHANGED = "config_changed"
