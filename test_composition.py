#!/usr/bin/env python3
"""
Test script to validate the enhanced before/after composition fix
"""

from src.gemini_image_generator import GeminiImageGenerator
from PIL import Image
import yaml

def test_enhanced_composition():
    print("🧪 Testing Enhanced Before/After Composition...")

    # Load brand guide
    with open('testing/focused_test.yml') as f:
        brand_guide = yaml.safe_load(f)

    # Generate test image with enhanced instructions
    generator = GeminiImageGenerator()
    test_image = generator.generate_complete_creative(
        campaign_message='TEST: Choose CleanWave',
        aspect_ratio='1x1',
        scene_description='white background',
        variant_id='spring_dress',
        brand_guide=brand_guide
    )

    # Save test image
    test_image.save('test_before_after.jpg')
    print('✅ Test image saved as test_before_after.jpg')
    print()
    print("🔍 Expected layout:")
    print("   LEFT: Dirty, stained dress shirt (folded)")
    print("   RIGHT: Clean dress shirt (folded)")
    print("   BACKGROUND: White")
    print("   TEXT: 'TEST: Choose CleanWave'")
    print()
    print("📂 View the test image:")
    print("   open test_before_after.jpg")

if __name__ == "__main__":
    test_enhanced_composition()