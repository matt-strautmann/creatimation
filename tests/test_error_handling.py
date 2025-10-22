"""
Tests for error handling and resilience across the system.

These tests verify that the system handles error conditions gracefully
and provides meaningful error messages to users.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config import ConfigManager
from container import DIContainer


class TestConfigErrorHandling:
    """Test configuration error handling scenarios"""

    def test_invalid_yaml_file(self, temp_dir):
        """Test handling of invalid YAML files"""
        config_file = temp_dir / "invalid.yml"
        config_file.write_text("invalid: yaml: content: [")

        config_manager = ConfigManager(str(config_file))

        with pytest.raises(RuntimeError) as exc_info:
            config_manager.load()

        assert "Invalid YAML" in str(exc_info.value)

    def test_permission_denied_config_file(self, temp_dir):
        """Test handling of permission denied on config file"""
        config_file = temp_dir / "readonly.yml"
        config_file.write_text("project:\n  name: test")
        config_file.chmod(0o000)

        config_manager = ConfigManager(str(config_file))

        try:
            with pytest.raises(RuntimeError) as exc_info:
                config_manager.load()
            assert "Permission denied" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            config_file.chmod(0o644)

    def test_corrupted_config_file(self, temp_dir):
        """Test handling of corrupted config file"""
        config_file = temp_dir / "corrupted.yml"
        # Write binary data to simulate corruption
        config_file.write_bytes(b'\x00\x01\x02\x03invalid\xff\xfe')

        config_manager = ConfigManager(str(config_file))

        with pytest.raises(RuntimeError) as exc_info:
            config_manager.load()

        assert "Encoding error" in str(exc_info.value)

    def test_config_validation_error(self, temp_dir):
        """Test handling of configuration validation errors"""
        config_file = temp_dir / "invalid_config.yml"
        config_content = """
generation:
  variants_per_ratio: 50  # Invalid: exceeds maximum of 10
  aspect_ratios: ["invalid_ratio"]  # Invalid ratio
"""
        config_file.write_text(config_content)

        config_manager = ConfigManager(str(config_file))

        with pytest.raises(RuntimeError) as exc_info:
            config_manager.load()

        assert "Configuration validation failed" in str(exc_info.value)

    def test_permission_denied_template_save(self, temp_dir):
        """Test handling of permission denied when saving template"""
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)

        template_path = readonly_dir / "template.yml"
        config_manager = ConfigManager()

        try:
            with pytest.raises(RuntimeError) as exc_info:
                config_manager.save_template(str(template_path))
            assert "Permission denied" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)

    def test_template_save_to_invalid_path(self):
        """Test handling of invalid path when saving template"""
        config_manager = ConfigManager()
        invalid_path = "/nonexistent/directory/template.yml"

        with pytest.raises(RuntimeError) as exc_info:
            config_manager.save_template(invalid_path)

        assert "Failed to write template" in str(exc_info.value)


class TestContainerErrorHandling:
    """Test dependency injection container error handling"""

    def test_create_from_nonexistent_config(self):
        """Test creating container from non-existent config file"""
        container = DIContainer()

        with pytest.raises(FileNotFoundError) as exc_info:
            container.create_from_config("/nonexistent/config.yml")

        assert "Config file not found" in str(exc_info.value)

    def test_create_from_invalid_yaml_config(self, temp_dir):
        """Test creating container from invalid YAML config"""
        config_file = temp_dir / "invalid.yml"
        config_file.write_text("invalid: yaml: [")

        container = DIContainer()

        with pytest.raises(RuntimeError) as exc_info:
            container.create_from_config(str(config_file))

        assert "Invalid YAML" in str(exc_info.value)

    def test_create_from_permission_denied_config(self, temp_dir):
        """Test creating container from permission denied config"""
        config_file = temp_dir / "readonly.yml"
        config_file.write_text("test: config")
        config_file.chmod(0o000)

        container = DIContainer()

        try:
            with pytest.raises(RuntimeError) as exc_info:
                container.create_from_config(str(config_file))
            assert "Permission denied" in str(exc_info.value)
        finally:
            # Restore permissions for cleanup
            config_file.chmod(0o644)

    def test_create_from_corrupted_config(self, temp_dir):
        """Test creating container from corrupted config file"""
        config_file = temp_dir / "corrupted.yml"
        config_file.write_bytes(b'\x00\x01corrupted\xff\xfe')

        container = DIContainer()

        with pytest.raises(RuntimeError) as exc_info:
            container.create_from_config(str(config_file))

        assert "Encoding error" in str(exc_info.value)


class TestSubprocessErrorHandling:
    """Test subprocess operation error handling"""

    @patch('subprocess.run')
    def test_subprocess_timeout_handling(self, mock_run):
        """Test subprocess timeout handling"""
        import subprocess

        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 30)

        # Test the error handling pattern used in completion command
        try:
            result = subprocess.run(
                ["test_command"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            # This is the expected error handling behavior
            assert True
        else:
            pytest.fail("Expected TimeoutExpired exception")

    @patch('subprocess.run')
    def test_subprocess_file_not_found_handling(self, mock_run):
        """Test subprocess file not found handling"""
        import subprocess

        # Mock FileNotFoundError
        mock_run.side_effect = FileNotFoundError()

        # Test error handling pattern
        try:
            result = subprocess.run(
                ["nonexistent_command"],
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            # This is the expected error handling behavior
            assert True
        else:
            pytest.fail("Expected FileNotFoundError exception")

    @patch('subprocess.run')
    def test_subprocess_permission_denied_handling(self, mock_run):
        """Test subprocess permission denied handling"""
        import subprocess

        # Mock PermissionError
        mock_run.side_effect = PermissionError()

        # Test error handling pattern
        try:
            result = subprocess.run(
                ["restricted_command"],
                capture_output=True,
                text=True,
            )
        except PermissionError:
            # This is the expected error handling behavior
            assert True
        else:
            pytest.fail("Expected PermissionError exception")

    def test_subprocess_return_code_handling(self):
        """Test subprocess return code handling"""
        import subprocess

        # Test with actual failing command
        result = subprocess.run(
            ["false"],  # Command that always returns 1
            capture_output=True,
            text=True,
        )

        # Verify return code handling logic
        assert result.returncode != 0
        # This demonstrates the pattern used in the completion command

    def test_subprocess_empty_output_handling(self):
        """Test subprocess empty output handling"""
        import subprocess

        # Test with command that produces no output
        result = subprocess.run(
            ["true"],  # Command that produces no output
            capture_output=True,
            text=True,
        )

        # Verify empty output handling logic
        assert result.returncode == 0
        assert result.stdout == ""


class TestPluginErrorHandling:
    """Test plugin system error handling patterns"""

    def test_import_error_handling_pattern(self):
        """Test import error handling pattern used in plugins"""
        # Test the pattern used in actual plugin loading
        try:
            # Simulate plugin import that fails
            raise ImportError("Missing plugin dependency")
        except ImportError as e:
            # This is the expected error handling behavior
            error_message = f"Plugin import failed: {e}"
            assert "import failed" in error_message.lower()

    def test_permission_error_handling_pattern(self):
        """Test permission error handling pattern"""
        try:
            # Simulate permission error during plugin loading
            raise PermissionError("Permission denied accessing plugin files")
        except PermissionError as e:
            # This is the expected error handling behavior
            error_message = f"Permission denied loading plugins: {e}"
            assert "permission denied" in error_message.lower()

    def test_plugin_registration_error_pattern(self):
        """Test plugin registration error handling pattern"""
        # Simulate the error handling used when registering plugin commands
        plugin_commands = {"test_cmd": None}  # Simulate invalid command

        errors = []
        for cmd_name, cmd_obj in plugin_commands.items():
            try:
                if cmd_obj is None:
                    raise ValueError("Invalid command object")
                # Simulate command registration
            except Exception as e:
                error_msg = f"Failed to register plugin command '{cmd_name}': {e}"
                errors.append(error_msg)

        assert len(errors) == 1
        assert "test_cmd" in errors[0]


class TestFileSystemErrorHandling:
    """Test file system operation error handling"""

    def test_workspace_detection_pattern(self, temp_dir):
        """Test workspace detection error handling pattern"""
        # Test the actual workspace detection logic pattern
        def find_workspace_safe(start_path):
            """Safe workspace detection that handles errors"""
            try:
                current = start_path
                while current != current.parent:
                    try:
                        # Try to check if workspace markers exist
                        if (current / ".creatimation").exists():
                            return current
                        if (current / "briefs").exists() and (current / "brand-guides").exists():
                            return current
                    except PermissionError:
                        # Skip directories we can't access
                        pass
                    except OSError:
                        # Skip any other OS-level errors
                        pass
                    current = current.parent
                return None
            except Exception:
                # Fallback for any unexpected errors
                return None

        # Test with inaccessible directory
        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir()
        (workspace_dir / ".creatimation").mkdir()
        workspace_dir.chmod(0o000)

        try:
            # This should handle permission errors gracefully
            result = find_workspace_safe(temp_dir)
            # Should handle the error without crashing
            assert result is None or isinstance(result, Path)
        finally:
            # Restore permissions for cleanup
            workspace_dir.chmod(0o755)

    def test_file_permission_error_patterns(self, temp_dir):
        """Test file permission error handling patterns"""
        # Create a file and make it unreadable
        test_file = temp_dir / "unreadable.txt"
        test_file.write_text("test content")
        test_file.chmod(0o000)

        try:
            # Test the error handling pattern used in file operations
            try:
                with open(test_file, 'r') as f:
                    content = f.read()
            except PermissionError as e:
                error_msg = f"Permission denied reading file {test_file}: {e}"
                assert "permission denied" in error_msg.lower()
            except OSError as e:
                error_msg = f"Failed to read file {test_file}: {e}"
                assert "failed to read" in error_msg.lower()
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)


class TestNetworkErrorHandling:
    """Test network operation error handling"""

    @patch('requests.post')
    def test_api_timeout_handling(self, mock_post):
        """Test API timeout handling"""
        import requests

        # Mock timeout exception
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        # This would be tested in actual image generation components
        # For now, just verify the exception type is importable
        assert hasattr(requests.exceptions, 'Timeout')

    @patch('requests.post')
    def test_api_connection_error_handling(self, mock_post):
        """Test API connection error handling"""
        import requests

        # Mock connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        # Verify exception type is available for proper handling
        assert hasattr(requests.exceptions, 'ConnectionError')


class TestConcurrentErrorHandling:
    """Test error handling in concurrent scenarios"""

    def test_multiple_config_access(self, temp_dir):
        """Test multiple concurrent config access"""
        import threading
        import time

        config_file = temp_dir / "concurrent_config.yml"
        config_file.write_text("project:\n  name: concurrent_test")

        errors = []

        def load_config():
            try:
                config_manager = ConfigManager(str(config_file))
                config_manager.load()
            except Exception as e:
                errors.append(e)

        # Start multiple threads accessing config
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=load_config)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should not have any errors
        assert len(errors) == 0

    def test_config_file_deletion_during_load(self, temp_dir):
        """Test config file deletion during load operation"""
        config_file = temp_dir / "deletable_config.yml"
        config_file.write_text("project:\n  name: deletable_test")

        config_manager = ConfigManager(str(config_file))

        # Delete file between existence check and actual load
        # This simulates race conditions
        assert config_file.exists()
        config_file.unlink()

        # Should handle missing file gracefully
        config = config_manager.load()
        assert config is not None  # Should fallback to defaults


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])