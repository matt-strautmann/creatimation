"""
Core domain models for the creative automation pipeline.

These models represent the business entities and value objects
in the creative automation domain.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any
from pathlib import Path


class AssetType(Enum):
    """Types of creative assets."""
    PRODUCT_TRANSPARENT = "product_transparent"
    SCENE_BACKGROUND = "scene_background"
    COMPOSITE = "composite"
    TEXT_OVERLAY = "text_overlay"


class Season(Enum):
    """Seasonal variants for campaigns."""
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"
    NONE = "none"


class ProductCategory(Enum):
    """Product categories for targeting."""
    LAUNDRY_CARE = "laundry_care"
    DISH_CARE = "dish_care"
    SURFACE_CARE = "surface_care"
    AIR_CARE = "air_care"
    PERSONAL_CARE = "personal_care"


@dataclass
class CreativeSpec:
    """Specification for generating a creative asset."""
    product_name: str
    campaign_message: str
    aspect_ratio: str
    region: str
    variant_type: str
    template: str
    theme: Optional[str] = None
    color_scheme: Optional[str] = None
    scene_description: Optional[str] = None


@dataclass
class BrandColors:
    """Brand color palette."""
    primary: str
    secondary: str
    accent: str

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'BrandColors':
        """Create from dictionary."""
        return cls(
            primary=data.get('primary', '#000000'),
            secondary=data.get('secondary', '#FFFFFF'),
            accent=data.get('accent', '#FF0000')
        )


@dataclass
class RegionalAdaptation:
    """Regional customization for campaigns."""
    currency: str
    legal_disclaimer: str
    call_to_action: str
    cultural_notes: str


@dataclass
class CampaignBrief:
    """Complete campaign brief with all requirements."""
    campaign_id: str
    campaign_name: str
    products: List[Dict[str, Any]]
    target_regions: List[str]
    creative_requirements: Dict[str, Any]
    regional_adaptations: Dict[str, RegionalAdaptation]
    brand_guide: Optional[str] = None
    enhanced_context: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CampaignBrief':
        """Create campaign brief from dictionary."""
        # Convert regional adaptations
        regional_adaptations = {}
        for region, adaptation in data.get('regional_adaptations', {}).items():
            regional_adaptations[region] = RegionalAdaptation(**adaptation)

        return cls(
            campaign_id=data['campaign_id'],
            campaign_name=data['campaign_name'],
            products=data['products'],
            target_regions=data.get('target_regions', [data.get('target_region', 'US')]),
            creative_requirements=data['creative_requirements'],
            regional_adaptations=regional_adaptations,
            brand_guide=data.get('brand_guide'),
            enhanced_context=data.get('enhanced_context')
        )


@dataclass
class GenerationResult:
    """Result of a creative generation operation."""
    success: bool
    output_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    file_path: str
    metadata: Dict[str, Any]
    created_at: str
    accessed_at: str
    size_bytes: int


@dataclass
class PipelineState:
    """Current state of the pipeline execution."""
    campaign_id: str
    total_products: int
    processed_products: int
    total_creatives: int
    generated_creatives: int
    cache_hits: int
    cache_misses: int
    errors: List[str]
    start_time: Optional[str] = None
    end_time: Optional[str] = None