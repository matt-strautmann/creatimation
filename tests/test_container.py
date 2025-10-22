"""
Tests for dependency injection container.

These tests cover the DIContainer class and service registration/retrieval.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from container import DIContainer, get_container
except ImportError:
    # Add src to path and try again
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from container import DIContainer, get_container


class TestDIContainer:
    """Test dependency injection container functionality"""

    def test_container_initialization(self):
        """Test DIContainer initialization"""
        container = DIContainer()
        assert container is not None
        assert hasattr(container, 'config')
        assert hasattr(container, '_instances')

    def test_container_with_config(self):
        """Test DIContainer with configuration"""
        config = {"test_setting": "test_value"}
        container = DIContainer(config)
        assert container.config == config

    def test_get_cache_manager(self):
        """Test getting cache manager"""
        container = DIContainer()
        cache_manager = container.get_cache_manager()
        assert cache_manager is not None
        # Should return same instance on second call (singleton behavior)
        cache_manager2 = container.get_cache_manager()
        assert cache_manager is cache_manager2

    def test_get_output_manager(self):
        """Test getting output manager"""
        container = DIContainer()
        output_manager = container.get_output_manager()
        assert output_manager is not None
        # Should return same instance on second call
        output_manager2 = container.get_output_manager()
        assert output_manager is output_manager2

    def test_get_image_generator(self):
        """Test getting image generator"""
        container = DIContainer()
        image_generator = container.get_image_generator(skip_init=True)
        assert image_generator is not None

    def test_get_brief_loader(self):
        """Test getting brief loader"""
        container = DIContainer()
        brief_loader = container.get_brief_loader()
        assert brief_loader is not None

    def test_get_brand_guide_loader(self):
        """Test getting brand guide loader"""
        container = DIContainer()
        brand_guide_loader = container.get_brand_guide_loader()
        assert brand_guide_loader is not None

    def test_get_state_tracker(self):
        """Test getting state tracker"""
        container = DIContainer()
        state_tracker = container.get_state_tracker("test_campaign")
        assert state_tracker is not None

    def test_get_pipeline(self):
        """Test getting pipeline"""
        container = DIContainer()
        pipeline = container.get_pipeline("test_campaign", dry_run=True)
        assert pipeline is not None

    def test_container_reset(self):
        """Test container reset functionality"""
        container = DIContainer()

        # Get some services to populate the cache
        cache_manager1 = container.get_cache_manager()
        output_manager1 = container.get_output_manager()

        # Reset the container
        container.reset()

        # Get services again - should be new instances
        cache_manager2 = container.get_cache_manager()
        output_manager2 = container.get_output_manager()

        assert cache_manager1 is not cache_manager2
        assert output_manager1 is not output_manager2


class TestGlobalContainer:
    """Test global container functionality"""

    def test_get_container_function(self):
        """Test get_container global function"""
        container = get_container()
        assert isinstance(container, DIContainer)

    def test_get_container_with_config(self):
        """Test get_container with configuration"""
        config = {"test": "value"}
        container = get_container(config)
        assert container.config == config

    def test_container_singleton_behavior(self):
        """Test global container default behavior"""
        container1 = get_container()
        container2 = get_container()

        # Should return the default singleton
        assert container1 is container2


class TestServiceIntegration:
    """Test service integration scenarios"""

    def test_full_service_stack(self):
        """Test getting full service stack"""
        container = DIContainer()

        # Get all core services
        cache = container.get_cache_manager()
        output = container.get_output_manager()
        brief_loader = container.get_brief_loader()
        brand_guide = container.get_brand_guide_loader()

        assert cache is not None
        assert output is not None
        assert brief_loader is not None
        assert brand_guide is not None

    def test_container_with_custom_config(self):
        """Test container with custom configuration"""
        config = {
            "cache": {"directory": "custom_cache"},
            "output": {"directory": "custom_output"}
        }
        container = DIContainer(config)

        cache_manager = container.get_cache_manager()
        output_manager = container.get_output_manager()

        assert cache_manager is not None
        assert output_manager is not None