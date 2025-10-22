"""
Tests for configuration management.

These tests cover the ConfigManager class and configuration handling.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from config import ConfigManager
except ImportError:
    # Add src to path and try again
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from config import ConfigManager


class TestConfigManager:
    """Test configuration manager functionality"""

    def test_config_manager_initialization(self):
        """Test ConfigManager initialization"""
        config_manager = ConfigManager()
        assert config_manager is not None
        assert hasattr(config_manager, 'config_path')
        assert hasattr(config_manager, '_config')

    def test_config_manager_with_file(self, temp_dir):
        """Test ConfigManager with config file"""
        config_file = temp_dir / "test_config.yml"
        config_manager = ConfigManager(str(config_file))
        assert config_manager.config_path == config_file

    def test_load_config_nonexistent_file(self, temp_dir):
        """Test loading configuration with non-existent file"""
        config_file = temp_dir / "nonexistent.yml"
        config_manager = ConfigManager(str(config_file))

        # Should load defaults even if file doesn't exist
        config = config_manager.load()
        assert config is not None
        assert hasattr(config, 'project')
        assert hasattr(config, 'generation')

    def test_load_config_with_cli_overrides(self, temp_dir):
        """Test loading configuration with CLI overrides"""
        config_manager = ConfigManager()
        cli_overrides = {"project": {"name": "test_project"}}

        config = config_manager.load(cli_overrides)
        assert config.project.name == "test_project"

    def test_save_template(self, temp_dir):
        """Test saving configuration template"""
        config_file = temp_dir / "test_template.yml"
        config_manager = ConfigManager(str(config_file))

        template_path = config_manager.save_template()
        assert template_path.exists()
        assert template_path == config_file

        # Check template contains expected content
        content = template_path.read_text()
        assert "Creative Automation Pipeline Configuration" in content
        assert "project:" in content
        assert "generation:" in content

    def test_validate_config(self, temp_dir):
        """Test config validation"""
        config_file = temp_dir / "valid_config.yml"
        config_manager = ConfigManager(str(config_file))

        # Create valid config file
        config_manager.save_template()

        result = config_manager.validate()
        assert result["valid"] is True
        assert "config" in result
        assert isinstance(result["warnings"], list)

    def test_config_with_yaml_file(self, temp_dir):
        """Test loading configuration from YAML file"""
        config_file = temp_dir / "config.yml"
        yaml_content = """
project:
  name: test_project
  output_dir: test_output/

generation:
  aspect_ratios: [1x1, 16x9]
  variants_per_ratio: 2
"""
        config_file.write_text(yaml_content)

        config_manager = ConfigManager(str(config_file))
        config = config_manager.load()

        assert config.project.name == "test_project"
        assert config.project.output_dir == "test_output/"
        assert config.generation.aspect_ratios == ["1x1", "16x9"]
        assert config.generation.variants_per_ratio == 2

    def test_config_precedence_chain(self, temp_dir):
        """Test configuration precedence chain"""
        config_file = temp_dir / "config.yml"
        yaml_content = """
project:
  name: file_project
"""
        config_file.write_text(yaml_content)

        config_manager = ConfigManager(str(config_file))

        # CLI overrides should take precedence
        cli_overrides = {"project": {"name": "cli_project"}}
        config = config_manager.load(cli_overrides)

        assert config.project.name == "cli_project"

    def test_show_effective_config(self, temp_dir):
        """Test showing effective configuration"""
        config_manager = ConfigManager()

        # Should show configuration string
        config_str = config_manager.show_effective_config()
        assert isinstance(config_str, str)
        assert "Effective Configuration" in config_str
        assert "Precedence Chain" in config_str

    def test_config_environment_openai_key(self):
        """Test OpenAI API key from environment"""
        config_manager = ConfigManager()

        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            config = config_manager.load()
            assert config.openai.api_key == "test_key"

    def test_config_validation_warnings(self, temp_dir):
        """Test configuration validation with warnings"""
        config_file = temp_dir / "config_with_warnings.yml"
        yaml_content = """
generation:
  variants_per_ratio: 8  # Should trigger warning
cache:
  max_size_mb: 200      # Should trigger warning
"""
        config_file.write_text(yaml_content)

        config_manager = ConfigManager(str(config_file))
        result = config_manager.validate()

        assert result["valid"] is True
        assert len(result["warnings"]) > 0
        assert any("variants_per_ratio" in warning for warning in result["warnings"])
        assert any("max_size_mb" in warning for warning in result["warnings"])


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)