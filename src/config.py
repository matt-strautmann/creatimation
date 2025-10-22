#!/usr/bin/env python3
"""
Configuration Management for Creative Automation Pipeline

Implements precedence chain: CLI flags > .creatimation.yml > hardcoded defaults
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, validator

# ============================================================================
# PYDANTIC MODELS FOR VALIDATION
# ============================================================================


class ProjectConfig(BaseModel):
    """Project-level settings"""

    name: str = Field(default="creative-automation", description="Project name")
    output_dir: str = Field(default="output/", description="Output directory")
    cache_dir: str = Field(default="cache/", description="Cache directory")


class GenerationConfig(BaseModel):
    """Creative generation settings"""

    aspect_ratios: list[str] = Field(
        default=["1x1", "9x16", "16x9"], description="Aspect ratios to generate"
    )
    variants_per_ratio: int = Field(
        default=3, ge=1, le=10, description="Number of variants per aspect ratio"
    )
    brand_guide: str | None = Field(default=None, description="Path to brand guide YAML file")

    @validator("aspect_ratios")
    def validate_ratios(cls, v):
        """Validate aspect ratio format"""
        valid_ratios = {"1x1", "9x16", "16x9", "4x5", "16x10"}
        for ratio in v:
            if ratio not in valid_ratios:
                raise ValueError(f"Invalid aspect ratio: {ratio}. Must be one of {valid_ratios}")
        return v


class CacheConfig(BaseModel):
    """Cache settings"""

    enabled: bool = Field(default=True, description="Enable caching")
    ttl_days: int = Field(default=30, ge=1, le=365, description="Cache TTL in days")
    max_size_mb: int = Field(default=1000, ge=100, description="Max cache size in MB")


class QualityConfig(BaseModel):
    """Quality and compliance settings"""

    image_size: int = Field(default=1024, ge=512, le=2048, description="Image generation size")
    compression: int = Field(default=85, ge=1, le=100, description="JPEG compression quality")
    brand_compliance_threshold: float = Field(
        default=0.75, ge=0.0, le=1.0, description="Brand compliance threshold"
    )


class OpenAIConfig(BaseModel):
    """OpenAI API settings"""

    model: str = Field(default="dall-e-3", description="DALL-E model version")
    timeout: int = Field(default=120, ge=30, le=300, description="API timeout in seconds")
    api_key: str | None = Field(default=None, description="OpenAI API key")


class CreatimationConfig(BaseModel):
    """Complete configuration schema"""

    project: ProjectConfig = Field(default_factory=ProjectConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)


# ============================================================================
# CONFIG MANAGER
# ============================================================================


class ConfigManager:
    """
    Configuration manager with precedence chain:
    1. CLI flags (highest priority)
    2. .creatimation.yml file
    3. Hardcoded defaults (lowest priority)
    """

    def __init__(self, config_path: str | None = None):
        """
        Initialize config manager.

        Args:
            config_path: Path to .creatimation.yml file (default: .creatimation.yml in cwd)
        """
        self.config_path = Path(config_path) if config_path else Path(".creatimation.yml")
        self._config: CreatimationConfig | None = None

    def load(self, cli_overrides: dict[str, Any] | None = None) -> CreatimationConfig:
        """
        Load configuration with precedence chain.

        Args:
            cli_overrides: Dictionary of CLI flag overrides

        Returns:
            CreatimationConfig object with merged configuration

        Precedence:
            1. CLI overrides (cli_overrides parameter)
            2. .creatimation.yml file (if exists)
            3. Hardcoded defaults (from Pydantic models)
        """
        # Start with defaults
        config_dict = {}

        # Layer 2: Load from .creatimation.yml if exists
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    file_config = yaml.safe_load(f) or {}
                    config_dict = self._deep_merge(config_dict, file_config)
            except PermissionError as e:
                raise RuntimeError(f"Permission denied reading config file {self.config_path}: {e}")
            except yaml.YAMLError as e:
                raise RuntimeError(f"Invalid YAML in config file {self.config_path}: {e}")
            except UnicodeDecodeError as e:
                raise RuntimeError(f"Encoding error in config file {self.config_path}: {e}")
            except OSError as e:
                raise RuntimeError(f"Failed to read config file {self.config_path}: {e}")
            except Exception as e:
                raise RuntimeError(f"Unexpected error reading config file {self.config_path}: {e}")

        # Layer 1: Apply CLI overrides (highest priority)
        if cli_overrides:
            config_dict = self._deep_merge(config_dict, cli_overrides)

        # Validate and create config object
        try:
            self._config = CreatimationConfig(**config_dict)
        except Exception as e:
            # Provide helpful validation error messages
            if "validation error" in str(e).lower():
                raise RuntimeError(f"Configuration validation failed: {e}")
            else:
                raise RuntimeError(f"Failed to create configuration: {e}")

        # Override OpenAI API key from environment if not in config
        if not self._config.openai.api_key:
            self._config.openai.api_key = os.getenv("OPENAI_API_KEY")

        return self._config

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """
        Deep merge two dictionaries, with override taking precedence.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def save_template(self, output_path: str | None = None) -> Path:
        """
        Save a .creatimation.yml template with defaults and comments.

        Args:
            output_path: Path to save template (default: .creatimation.yml)

        Returns:
            Path to saved template
        """
        template_path = Path(output_path) if output_path else self.config_path

        template = """# Creative Automation Pipeline Configuration
# This file defines project defaults. CLI flags override these settings.
#
# Precedence: CLI flags > .creatimation.yml > hardcoded defaults

# Project settings
project:
  name: creative-automation
  output_dir: output/          # Where generated creatives are saved
  cache_dir: cache/            # Where cached assets are stored

# Generation settings
generation:
  aspect_ratios: [1x1, 9x16, 16x9]  # Aspect ratios to generate
  variants_per_ratio: 3              # Number of text variants per ratio (1-10)
  brand_guide: null                  # Path to brand guide YAML (optional)

# Cache settings
cache:
  enabled: true                # Enable intelligent caching
  ttl_days: 30                 # Cache time-to-live in days
  max_size_mb: 1000            # Maximum cache size in megabytes

# Quality settings
quality:
  image_size: 1024             # DALL-E image generation size (512-2048)
  compression: 85              # JPEG compression quality (1-100)
  brand_compliance_threshold: 0.75  # Minimum compliance score (0.0-1.0)

# OpenAI settings (can also use .env file)
openai:
  model: dall-e-3              # DALL-E model version
  timeout: 120                 # API timeout in seconds
  # api_key: sk-...            # Optional: override .env OPENAI_API_KEY
"""

        try:
            with open(template_path, "w", encoding="utf-8") as f:
                f.write(template)
        except PermissionError as e:
            raise RuntimeError(f"Permission denied writing template to {template_path}: {e}")
        except OSError as e:
            raise RuntimeError(f"Failed to write template to {template_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error writing template to {template_path}: {e}")

        return template_path

    def validate(self) -> dict[str, Any]:
        """
        Validate configuration file.

        Returns:
            Dictionary with validation results
        """
        if not self.config_path.exists():
            return {
                "valid": False,
                "error": f"Config file not found: {self.config_path}",
                "warnings": [],
            }

        try:
            with open(self.config_path) as f:
                config_dict = yaml.safe_load(f) or {}

            # Validate against Pydantic model
            config = CreatimationConfig(**config_dict)

            warnings = []

            # Check for common issues
            if config.generation.variants_per_ratio > 5:
                warnings.append(
                    f"variants_per_ratio is {config.generation.variants_per_ratio}. "
                    "This will increase API costs significantly."
                )

            if config.cache.max_size_mb < 500:
                warnings.append(
                    f"cache.max_size_mb is {config.cache.max_size_mb}MB. "
                    "Consider increasing for better performance."
                )

            if config.generation.brand_guide and not Path(config.generation.brand_guide).exists():
                warnings.append(f"Brand guide file not found: {config.generation.brand_guide}")

            return {"valid": True, "config": config, "warnings": warnings}

        except Exception as e:
            return {"valid": False, "error": str(e), "warnings": []}

    def show_effective_config(self, cli_overrides: dict[str, Any] | None = None) -> str:
        """
        Show effective configuration after precedence chain applied.

        Args:
            cli_overrides: CLI flag overrides

        Returns:
            Formatted string showing effective config
        """
        config = self.load(cli_overrides)

        output = ["Effective Configuration", "=" * 50, ""]

        # Show precedence chain
        output.append("Precedence Chain:")
        output.append("  1. CLI flags (highest priority)")
        if self.config_path.exists():
            output.append(f"  2. {self.config_path} ✓")
        else:
            output.append(f"  2. {self.config_path} (not found)")
        output.append("  3. Hardcoded defaults (fallback)")
        output.append("")

        # Show config sections
        output.append("Project:")
        output.append(f"  name: {config.project.name}")
        output.append(f"  output_dir: {config.project.output_dir}")
        output.append(f"  cache_dir: {config.project.cache_dir}")
        output.append("")

        output.append("Generation:")
        output.append(f"  aspect_ratios: {', '.join(config.generation.aspect_ratios)}")
        output.append(f"  variants_per_ratio: {config.generation.variants_per_ratio}")
        output.append(f"  brand_guide: {config.generation.brand_guide or '(none)'}")
        output.append("")

        output.append("Cache:")
        output.append(f"  enabled: {config.cache.enabled}")
        output.append(f"  ttl_days: {config.cache.ttl_days}")
        output.append(f"  max_size_mb: {config.cache.max_size_mb}")
        output.append("")

        output.append("Quality:")
        output.append(f"  image_size: {config.quality.image_size}")
        output.append(f"  compression: {config.quality.compression}")
        output.append(f"  brand_compliance_threshold: {config.quality.brand_compliance_threshold}")
        output.append("")

        output.append("OpenAI:")
        output.append(f"  model: {config.openai.model}")
        output.append(f"  timeout: {config.openai.timeout}s")
        api_key_status = "✓ set" if config.openai.api_key else "✗ not set"
        output.append(f"  api_key: {api_key_status}")

        return "\n".join(output)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def load_config(
    config_path: str | None = None, cli_overrides: dict[str, Any] | None = None
) -> CreatimationConfig:
    """
    Convenience function to load configuration.

    Args:
        config_path: Path to .creatimation.yml
        cli_overrides: CLI flag overrides

    Returns:
        CreatimationConfig object
    """
    manager = ConfigManager(config_path)
    return manager.load(cli_overrides)


def init_config(output_path: str | None = None) -> Path:
    """
    Initialize .creatimation.yml template.

    Args:
        output_path: Where to save template

    Returns:
        Path to saved template
    """
    manager = ConfigManager()
    return manager.save_template(output_path)


def validate_config(config_path: str | None = None) -> dict[str, Any]:
    """
    Validate configuration file.

    Args:
        config_path: Path to .creatimation.yml

    Returns:
        Validation results
    """
    manager = ConfigManager(config_path)
    return manager.validate()
