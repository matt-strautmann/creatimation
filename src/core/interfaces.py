"""
Core interfaces for the creative automation pipeline.

Defines the contracts for all major components to enable proper
dependency injection and testing.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path
from PIL import Image


class CacheManagerInterface(ABC):
    """Interface for cache management operations."""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache."""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """Store item in cache."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if item exists in cache."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass


class OutputManagerInterface(ABC):
    """Interface for output management operations."""

    @abstractmethod
    def save_creative(
        self,
        image: Image.Image,
        product_name: str,
        ratio: str,
        metadata: Dict[str, Any],
        template: str,
        region: str,
        variant_id: Optional[str] = None
    ) -> str:
        """Save creative with metadata."""
        pass

    @abstractmethod
    def get_output_path(
        self,
        product_name: str,
        template: str,
        region: str,
        ratio: str
    ) -> Path:
        """Get standardized output path."""
        pass


class ImageGeneratorInterface(ABC):
    """Interface for image generation operations."""

    @abstractmethod
    def generate_product_only(
        self,
        product_name: str,
        aspect_ratio: str = "1x1"
    ) -> Image.Image:
        """Generate product-only image."""
        pass

    @abstractmethod
    def generate_product_creative(
        self,
        product_name: str,
        campaign_message: str,
        scene_description: str,
        aspect_ratio: str,
        theme: Optional[str] = None,
        color_scheme: Optional[str] = None,
        region: str = "US",
        variant_id: str = "variant_1",
        product_image: Optional[Image.Image] = None,
        brand_guide: Optional[Dict[str, Any]] = None
    ) -> Image.Image:
        """Generate complete creative with product and scene."""
        pass


class BriefLoaderInterface(ABC):
    """Interface for loading and validating campaign briefs."""

    @abstractmethod
    def load_brief(self, brief_path: str) -> Dict[str, Any]:
        """Load and validate campaign brief."""
        pass

    @abstractmethod
    def validate_brief(self, brief: Dict[str, Any]) -> bool:
        """Validate brief structure and content."""
        pass


class BrandGuideLoaderInterface(ABC):
    """Interface for loading brand guides."""

    @abstractmethod
    def load_brand_guide(self, guide_path: str) -> Dict[str, Any]:
        """Load brand guide configuration."""
        pass

    @abstractmethod
    def validate_brand_guide(self, guide: Dict[str, Any]) -> bool:
        """Validate brand guide structure."""
        pass


class StateTrackerInterface(ABC):
    """Interface for pipeline state management."""

    @abstractmethod
    def update_product_state(
        self,
        product_id: str,
        state: Dict[str, Any]
    ) -> None:
        """Update state for a product."""
        pass

    @abstractmethod
    def get_product_state(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get current state for a product."""
        pass

    @abstractmethod
    def can_resume(self) -> bool:
        """Check if pipeline can be resumed."""
        pass

    @abstractmethod
    def get_summary(self) -> Dict[str, Any]:
        """Get pipeline execution summary."""
        pass