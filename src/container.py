"""
Dependency Injection Container for Creative Automation Pipeline.

This module provides a simple dependency injection container that wires
together all the components of the creative automation pipeline.
"""
from typing import Dict, Any, Optional

try:
    from .core.interfaces import (
        CacheManagerInterface,
        OutputManagerInterface,
        ImageGeneratorInterface,
        BriefLoaderInterface,
        BrandGuideLoaderInterface,
        StateTrackerInterface
    )

    # Import concrete implementations
    from .managers.cache_manager import UnifiedCacheManager
    from .managers.output_manager import UnifiedOutputManager
    from .gemini_image_generator import GeminiImageGenerator
    from .enhanced_brief_loader import EnhancedBriefLoader
    from .brand_guide_loader import BrandGuideLoader
    from .state_tracker import StateTracker
    from .pipeline.creative_pipeline import CreativePipeline
except ImportError:
    # Fallback for direct execution
    from src.core.interfaces import (
        CacheManagerInterface,
        OutputManagerInterface,
        ImageGeneratorInterface,
        BriefLoaderInterface,
        BrandGuideLoaderInterface,
        StateTrackerInterface
    )

    from src.managers.cache_manager import UnifiedCacheManager
    from src.managers.output_manager import UnifiedOutputManager
    from src.gemini_image_generator import GeminiImageGenerator
    from src.enhanced_brief_loader import EnhancedBriefLoader
    from src.brand_guide_loader import BrandGuideLoader
    from src.state_tracker import StateTracker
    from src.pipeline.creative_pipeline import CreativePipeline


class DIContainer:
    """
    Simple dependency injection container.

    Provides factory methods for creating properly configured instances
    of all pipeline components.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize container with optional configuration."""
        self.config = config or {}
        self._instances = {}

    def get_cache_manager(self) -> CacheManagerInterface:
        """Get configured cache manager instance."""
        if 'cache_manager' not in self._instances:
            cache_config = self.config.get('cache', {})
            self._instances['cache_manager'] = UnifiedCacheManager(
                cache_dir=cache_config.get('directory', 'cache'),
                enable_s3=cache_config.get('enable_s3', False),
                s3_bucket=cache_config.get('s3_bucket')
            )
        return self._instances['cache_manager']

    def get_output_manager(self) -> OutputManagerInterface:
        """Get configured output manager instance."""
        if 'output_manager' not in self._instances:
            output_config = self.config.get('output', {})
            self._instances['output_manager'] = UnifiedOutputManager(
                output_dir=output_config.get('directory', 'output'),
                use_semantic_structure=output_config.get('semantic_structure', True)
            )
        return self._instances['output_manager']

    def get_image_generator(self) -> ImageGeneratorInterface:
        """Get configured image generator instance."""
        if 'image_generator' not in self._instances:
            self._instances['image_generator'] = GeminiImageGenerator()
        return self._instances['image_generator']

    def get_brief_loader(self) -> BriefLoaderInterface:
        """Get configured brief loader instance."""
        if 'brief_loader' not in self._instances:
            cache_manager = self.get_cache_manager()
            self._instances['brief_loader'] = EnhancedBriefLoader(cache_manager)
        return self._instances['brief_loader']

    def get_brand_guide_loader(self) -> BrandGuideLoaderInterface:
        """Get configured brand guide loader instance."""
        if 'brand_guide_loader' not in self._instances:
            self._instances['brand_guide_loader'] = BrandGuideLoader()
        return self._instances['brand_guide_loader']

    def get_state_tracker(self, campaign_id: str) -> StateTrackerInterface:
        """Get configured state tracker instance."""
        # State tracker is campaign-specific, so don't cache it
        return StateTracker(campaign_id)

    def get_pipeline(
        self,
        campaign_id: str,
        no_cache: bool = False,
        dry_run: bool = False
    ) -> CreativePipeline:
        """Get configured pipeline instance."""
        return CreativePipeline(
            cache_manager=self.get_cache_manager(),
            output_manager=self.get_output_manager(),
            image_generator=self.get_image_generator(),
            brief_loader=self.get_brief_loader(),
            brand_guide_loader=self.get_brand_guide_loader(),
            state_tracker=self.get_state_tracker(campaign_id),
            no_cache=no_cache,
            dry_run=dry_run
        )

    def create_from_config(self, config_path: str) -> 'DIContainer':
        """Create container from configuration file."""
        import yaml
        from pathlib import Path

        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            return DIContainer(config)
        else:
            raise FileNotFoundError(f"Config file not found: {config_path}")

    def reset(self) -> None:
        """Reset all cached instances."""
        self._instances.clear()


# Global container instance for convenience
_default_container = DIContainer()


def get_container(config: Optional[Dict[str, Any]] = None) -> DIContainer:
    """Get the default container instance."""
    if config:
        return DIContainer(config)
    return _default_container


def configure_container(config: Dict[str, Any]) -> None:
    """Configure the default container."""
    global _default_container
    _default_container = DIContainer(config)