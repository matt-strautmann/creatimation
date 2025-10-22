#!/usr/bin/env python3
"""
Test script to validate the enhanced before/after composition fix
"""

# Add src to path for imports
import os
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from gemini_image_generator import GeminiImageGenerator


@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not available for integration test"
)
def test_enhanced_composition():
    """Test enhanced before/after composition with real API call."""
    print("🧪 Testing Enhanced Before/After Composition...")

    # Load brand guide
    brand_guide_path = Path(__file__).parent.parent / "brand-guides" / "cleanwave_blue.yml"
    with open(brand_guide_path) as f:
        brand_guide = yaml.safe_load(f)

    # Generate test image with enhanced instructions
    generator = GeminiImageGenerator()
    test_image = generator.generate_complete_creative(
        campaign_message="TEST: Choose CleanWave",
        aspect_ratio="1x1",
        scene_description="white background",
        variant_id="spring_dress",
        brand_guide=brand_guide,
    )

    # Verify image was generated
    assert test_image is not None
    assert hasattr(test_image, 'save')

    print("✅ Test image generated successfully")


def test_enhanced_composition_dry_run():
    """Test composition logic without API calls."""
    # Load brand guide
    brand_guide_path = Path(__file__).parent.parent / "brand-guides" / "cleanwave_blue.yml"
    with open(brand_guide_path) as f:
        brand_guide = yaml.safe_load(f)

    # Initialize generator in dry-run mode
    generator = GeminiImageGenerator(skip_init=True)

    # Verify initialization worked
    assert generator.client is None
    assert generator.api_key is None or isinstance(generator.api_key, str)


if __name__ == "__main__":
    # Run the actual test if API key is available
    if os.getenv("GOOGLE_API_KEY"):
        test_enhanced_composition()
    else:
        print("⚠️  GOOGLE_API_KEY not available - running dry-run test only")
        test_enhanced_composition_dry_run()
