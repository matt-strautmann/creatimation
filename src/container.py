"""
Dependency Injection Container for Creative Automation Pipeline.

This module provides a simple dependency injection container that wires
together all the components of the creative automation pipeline.
"""

from typing import Any

try:
    from .brand_guide_loader import BrandGuideLoader
    from .core.interfaces import (
        BrandGuideLoaderInterface,
        BriefLoaderInterface,
        CacheManagerInterface,
        ImageGeneratorInterface,
        OutputManagerInterface,
        StateTrackerInterface,
    )
    from .enhanced_brief_loader import EnhancedBriefLoader
    from .gemini_image_generator import GeminiImageGenerator

    # Import concrete implementations
    from .managers.cache_manager import UnifiedCacheManager
    from .managers.output_manager import UnifiedOutputManager
    from .pipeline.creative_pipeline import CreativePipeline
    from .state_tracker import StateTracker
except ImportError:
    # Fallback for direct execution
    from src.brand_guide_loader import BrandGuideLoader
    from src.core.interfaces import (
        BrandGuideLoaderInterface,
        BriefLoaderInterface,
        CacheManagerInterface,
        ImageGeneratorInterface,
        OutputManagerInterface,
        StateTrackerInterface,
    )
    from src.enhanced_brief_loader import EnhancedBriefLoader
    from src.gemini_image_generator import GeminiImageGenerator
    from src.managers.cache_manager import UnifiedCacheManager
    from src.managers.output_manager import UnifiedOutputManager
    from src.pipeline.creative_pipeline import CreativePipeline
    from src.state_tracker import StateTracker


class DIContainer:
    """
    Simple dependency injection container.

    Provides factory methods for creating properly configured instances
    of all pipeline components.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize container with optional configuration."""
        self.config = config or {}
        self._instances = {}

    def get_cache_manager(self) -> CacheManagerInterface:
        """Get configured cache manager instance."""
        if "cache_manager" not in self._instances:
            cache_config = self.config.get("cache", {})
            self._instances["cache_manager"] = UnifiedCacheManager(
                cache_dir=cache_config.get("directory", "cache"),
                enable_s3=cache_config.get("enable_s3", False),
                s3_bucket=cache_config.get("s3_bucket"),
            )
        return self._instances["cache_manager"]

    def get_output_manager(self) -> OutputManagerInterface:
        """Get configured output manager instance."""
        if "output_manager" not in self._instances:
            output_config = self.config.get("output", {})
            self._instances["output_manager"] = UnifiedOutputManager(
                output_dir=output_config.get("directory", "output"),
                use_semantic_structure=output_config.get("semantic_structure", True),
            )
        return self._instances["output_manager"]

    def get_image_generator(self, skip_init: bool = False) -> ImageGeneratorInterface:
        """Get configured image generator instance."""
        cache_key = f"image_generator_{skip_init}"
        if cache_key not in self._instances:
            self._instances[cache_key] = GeminiImageGenerator(skip_init=skip_init)
        return self._instances[cache_key]

    def get_brief_loader(self) -> BriefLoaderInterface:
        """Get configured brief loader instance."""
        if "brief_loader" not in self._instances:
            cache_manager = self.get_cache_manager()
            self._instances["brief_loader"] = EnhancedBriefLoader(cache_manager)
        return self._instances["brief_loader"]

    def get_brand_guide_loader(self) -> BrandGuideLoaderInterface:
        """Get configured brand guide loader instance."""
        if "brand_guide_loader" not in self._instances:
            self._instances["brand_guide_loader"] = BrandGuideLoader()
        return self._instances["brand_guide_loader"]

    def get_state_tracker(self, campaign_id: str) -> StateTrackerInterface:
        """Get configured state tracker instance."""
        # State tracker is campaign-specific, so don't cache it
        return StateTracker(campaign_id)

    def get_pipeline(
        self, campaign_id: str, no_cache: bool = False, dry_run: bool = False
    ) -> CreativePipeline:
        """Get configured pipeline instance."""
        return CreativePipeline(
            cache_manager=self.get_cache_manager(),
            output_manager=self.get_output_manager(),
            image_generator=self.get_image_generator(skip_init=dry_run),
            brief_loader=self.get_brief_loader(),
            brand_guide_loader=self.get_brand_guide_loader(),
            state_tracker=self.get_state_tracker(campaign_id),
            no_cache=no_cache,
            dry_run=dry_run,
        )

    def create_from_config(self, config_path: str) -> "DIContainer":
        """Create container from configuration file."""
        from pathlib import Path

        import yaml

        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        try:
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            return DIContainer(config)
        except PermissionError as e:
            raise RuntimeError(f"Permission denied reading config file {config_path}: {e}")
        except yaml.YAMLError as e:
            raise RuntimeError(f"Invalid YAML in config file {config_path}: {e}")
        except UnicodeDecodeError as e:
            raise RuntimeError(f"Encoding error in config file {config_path}: {e}")
        except OSError as e:
            raise RuntimeError(f"Failed to read config file {config_path}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error reading config file {config_path}: {e}")

    def reset(self) -> None:
        """Reset all cached instances."""
        self._instances.clear()


# Global container instance for convenience
_default_container = DIContainer()


def get_container(config: dict[str, Any] | None = None) -> DIContainer:
    """Get the default container instance."""
    if config:
        return DIContainer(config)
    return _default_container


def configure_container(config: dict[str, Any]) -> None:
    """Configure the default container."""
    global _default_container
    _default_container = DIContainer(config)
