#!/usr/bin/env python3
"""
Brand Guide Loader for Creative Automation Pipeline

Loads brand guides from YAML files and provides defaults that can override
campaign brief settings.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, validator

# ============================================================================
# BRAND GUIDE MODELS
# ============================================================================


class BrandColors(BaseModel):
    """Brand color palette"""

    primary: str = Field(..., description="Primary brand color (hex)")
    secondary: str | None = Field(None, description="Secondary brand color (hex)")
    accent: str | None = Field(None, description="Accent color (hex)")
    background: str | None = Field(None, description="Background color (hex)")
    text: str | None = Field(None, description="Text color (hex)")

    @validator("primary", "secondary", "accent", "background", "text")
    def validate_hex_color(cls, v):
        """Validate hex color format"""
        if v and not v.startswith("#"):
            return f"#{v}"
        if v and len(v) not in [4, 7]:  # #RGB or #RRGGBB
            raise ValueError(f"Invalid hex color: {v}")
        return v


class BrandTypography(BaseModel):
    """Brand typography settings"""

    font_family: str | None = Field(None, description="Primary font family")
    headline_size: int | None = Field(None, ge=12, le=72, description="Headline font size")
    body_size: int | None = Field(None, ge=8, le=24, description="Body font size")
    font_weight: str | None = Field(None, description="Font weight (normal, bold, etc.)")


class VisualStyle(BaseModel):
    """Visual styling preferences"""

    layout_style: str = Field(
        default="hero-product",
        description="Layout style (hero-product, minimal, vibrant, lifestyle)",
    )
    text_positioning: str = Field(
        default="top", description="Default text position (top, bottom, center, dynamic)"
    )
    scene_style: str | None = Field(
        None, description="Scene background style (kitchen, bathroom, lifestyle, etc.)"
    )
    mood: str | None = Field(None, description="Visual mood (clean, energetic, calm, professional)")


class MessagingGuidelines(BaseModel):
    """Brand messaging and tone"""

    tone: str = Field(
        default="professional", description="Brand tone (professional, friendly, energetic)"
    )
    max_headline_length: int = Field(
        default=40, ge=10, le=100, description="Maximum headline character length"
    )
    max_subheadline_length: int | None = Field(
        None, ge=10, le=200, description="Maximum subheadline character length"
    )
    avoid_words: list[str] = Field(default_factory=list, description="Words to avoid in messaging")
    preferred_phrases: list[str] = Field(
        default_factory=list, description="Brand-preferred phrases"
    )


class BrandMetadata(BaseModel):
    """Brand metadata"""

    name: str = Field(..., description="Brand name")
    industry: str | None = Field(None, description="Industry/category")
    target_audience: str | None = Field(None, description="Primary target audience")
    values: list[str] = Field(default_factory=list, description="Brand values")


class BrandGuide(BaseModel):
    """Complete brand guide schema"""

    brand: BrandMetadata
    colors: BrandColors
    typography: BrandTypography = Field(default_factory=BrandTypography.model_construct)
    visual: VisualStyle = Field(default_factory=VisualStyle.model_construct)
    messaging: MessagingGuidelines = Field(default_factory=MessagingGuidelines.model_construct)

    # Allow additional fields like variants, style_guidelines, etc.
    class Config:
        extra = "allow"


# ============================================================================
# BRAND GUIDE LOADER
# ============================================================================


class BrandGuideLoader:
    """Load and apply brand guides to campaign briefs"""

    def __init__(self):
        """Initialize brand guide loader"""
        self._loaded_guides: dict[str, BrandGuide] = {}

    def load_brand_guide(self, guide_path: str) -> dict[str, Any]:
        """Load brand guide - interface method that returns dictionary."""
        brand_guide = self.load(guide_path)
        return brand_guide.model_dump()

    def validate_brand_guide(self, guide: dict[str, Any]) -> bool:
        """Validate brand guide structure."""
        try:
            BrandGuide(**guide)
            return True
        except Exception:
            return False

    def load(self, brand_guide_path: str) -> BrandGuide:
        """
        Load brand guide from YAML file.

        Args:
            brand_guide_path: Path to brand guide YAML file

        Returns:
            BrandGuide object

        Raises:
            FileNotFoundError: If brand guide file doesn't exist
            ValueError: If brand guide YAML is invalid
        """
        path = Path(brand_guide_path)

        if not path.exists():
            raise FileNotFoundError(f"Brand guide not found: {brand_guide_path}")

        # Check cache
        if str(path) in self._loaded_guides:
            return self._loaded_guides[str(path)]

        # Load and parse YAML
        with open(path) as f:
            guide_dict = yaml.safe_load(f)

        # Validate and create BrandGuide object
        try:
            brand_guide = BrandGuide(**guide_dict)
            self._loaded_guides[str(path)] = brand_guide
            return brand_guide
        except Exception as e:
            raise ValueError(f"Invalid brand guide YAML: {e}") from e

    def apply_to_brief(self, brief: dict[str, Any], brand_guide: BrandGuide) -> dict[str, Any]:
        """
        Apply brand guide overrides to campaign brief.

        Args:
            brief: Campaign brief dictionary
            brand_guide: BrandGuide object

        Returns:
            Enhanced brief with brand guide overrides applied

        Precedence:
            - Explicit brief values take precedence
            - Brand guide fills in missing values
            - Original brief is not modified (returns copy)
        """
        enhanced_brief = brief.copy()

        # Add brand metadata if not present
        if "brand_meta" not in enhanced_brief:
            enhanced_brief["brand_meta"] = {}

        brand_meta = enhanced_brief["brand_meta"]

        # Apply brand metadata
        if not brand_meta.get("brand_name"):
            brand_meta["brand_name"] = brand_guide.brand.name

        if not brand_meta.get("industry"):
            brand_meta["industry"] = brand_guide.brand.industry

        if not brand_meta.get("target_audience") and brand_guide.brand.target_audience:
            enhanced_brief["target_audience"] = brand_guide.brand.target_audience

        # Apply color palette
        if "brand_colors" not in brand_meta:
            brand_meta["brand_colors"] = {}

        brand_colors = brand_meta["brand_colors"]
        brand_colors["primary"] = brand_colors.get("primary", brand_guide.colors.primary)

        if brand_guide.colors.secondary:
            brand_colors["secondary"] = brand_colors.get("secondary", brand_guide.colors.secondary)

        if brand_guide.colors.accent:
            brand_colors["accent"] = brand_colors.get("accent", brand_guide.colors.accent)

        # Apply visual styling
        if "enhanced_context" not in enhanced_brief:
            enhanced_brief["enhanced_context"] = {}

        context = enhanced_brief["enhanced_context"]

        # Layout style from brand guide
        if not context.get("layout_style"):
            context["layout_style"] = brand_guide.visual.layout_style

        # Scene style preference
        if not context.get("scene_description") and brand_guide.visual.scene_style:
            context["scene_style_preference"] = brand_guide.visual.scene_style

        # Mood/tone
        if not context.get("mood") and brand_guide.visual.mood:
            context["mood"] = brand_guide.visual.mood

        # Typography preferences
        if brand_guide.typography.font_family:
            context["font_family"] = context.get("font_family", brand_guide.typography.font_family)

        # Messaging guidelines
        if "messaging" not in enhanced_brief:
            enhanced_brief["messaging"] = {}

        messaging = enhanced_brief["messaging"]
        messaging["tone"] = messaging.get("tone", brand_guide.messaging.tone)
        messaging["max_headline_length"] = messaging.get(
            "max_headline_length", brand_guide.messaging.max_headline_length
        )

        if brand_guide.messaging.avoid_words:
            messaging["avoid_words"] = brand_guide.messaging.avoid_words

        if brand_guide.messaging.preferred_phrases:
            messaging["preferred_phrases"] = brand_guide.messaging.preferred_phrases

        # Add brand guide reference
        enhanced_brief["brand_guide_applied"] = True

        return enhanced_brief

    def validate(self, brand_guide_path: str) -> dict[str, Any]:
        """
        Validate brand guide file.

        Args:
            brand_guide_path: Path to brand guide YAML

        Returns:
            Validation result dictionary
        """
        try:
            brand_guide = self.load(brand_guide_path)

            warnings = []

            # Check for recommended fields
            if not brand_guide.colors.secondary:
                warnings.append("No secondary color defined - may limit design options")

            if not brand_guide.typography.font_family:
                warnings.append("No font family specified - will use default fonts")

            if not brand_guide.brand.values:
                warnings.append("No brand values defined - may affect messaging tone")

            return {
                "valid": True,
                "brand_guide": brand_guide,
                "warnings": warnings,
            }

        except FileNotFoundError as e:
            return {"valid": False, "error": str(e), "warnings": []}
        except ValueError as e:
            return {"valid": False, "error": str(e), "warnings": []}
        except Exception as e:
            return {"valid": False, "error": f"Unexpected error: {e}", "warnings": []}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def load_brand_guide(brand_guide_path: str) -> BrandGuide:
    """
    Convenience function to load a brand guide.

    Args:
        brand_guide_path: Path to brand guide YAML file

    Returns:
        BrandGuide object
    """
    loader = BrandGuideLoader()
    return loader.load(brand_guide_path)


def apply_brand_guide(brief: dict[str, Any], brand_guide_path: str) -> dict[str, Any]:
    """
    Load brand guide and apply to brief.

    Args:
        brief: Campaign brief dictionary
        brand_guide_path: Path to brand guide YAML

    Returns:
        Enhanced brief with brand guide applied
    """
    loader = BrandGuideLoader()
    brand_guide = loader.load(brand_guide_path)
    return loader.apply_to_brief(brief, brand_guide)


def validate_brand_guide(brand_guide_path: str) -> dict[str, Any]:
    """
    Validate brand guide file.

    Args:
        brand_guide_path: Path to brand guide YAML

    Returns:
        Validation results
    """
    loader = BrandGuideLoader()
    return loader.validate(brand_guide_path)
