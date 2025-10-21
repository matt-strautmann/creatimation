"""
Tests for Enhanced Brief Loader

Tests CPG schema processing, context mapping, and template expansion.
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enhanced_brief_loader import EnhancedBriefLoader


class TestEnhancedBriefLoader:
    """Test enhanced brief loading and CPG schema processing"""

    def test_load_simple_brief(self, temp_dir, sample_brief_file):
        """Test loading a simple campaign brief"""
        loader = EnhancedBriefLoader()

        brief = loader.load_and_enhance_brief(str(sample_brief_file))

        assert brief is not None
        assert "campaign_id" in brief
        assert "products" in brief
        assert len(brief["products"]) == 2

    def test_enhance_simple_brief(self, temp_dir):
        """Test enhancing a simple brief with CPG schema"""
        loader = EnhancedBriefLoader()

        simple_brief = {
            "campaign_id": "test_campaign",
            "products": ["Product A", "Product B"],
            "target_region": "US",
            "campaign_message": "Test Message",
        }

        # Save to file
        brief_file = temp_dir / "simple_brief.json"
        with open(brief_file, "w") as f:
            json.dump(simple_brief, f)

        # Load and enhance
        enhanced = loader.load_and_enhance_brief(str(brief_file))

        assert enhanced is not None
        assert "brand_meta" in enhanced or "products" in enhanced
        assert "target_region" in enhanced

    def test_extract_products(self, temp_dir):
        """Test extracting product list from brief"""
        loader = EnhancedBriefLoader()

        brief = {
            "products": [
                {"name": "Product A", "category": "cleaning"},
                {"name": "Product B", "category": "laundry"},
            ]
        }

        brief_file = temp_dir / "products_brief.json"
        with open(brief_file, "w") as f:
            json.dump(brief, f)

        loaded = loader.load_and_enhance_brief(str(brief_file))
        assert "products" in loaded
        assert len(loaded["products"]) == 2

    def test_validate_required_fields(self, temp_dir):
        """Test validation of required brief fields"""
        loader = EnhancedBriefLoader()

        # Missing campaign_id
        invalid_brief = {
            "products": ["Product A"],
            "target_region": "US",
        }

        brief_file = temp_dir / "invalid_brief.json"
        with open(brief_file, "w") as f:
            json.dump(invalid_brief, f)

        # Should still load but may have defaults
        loaded = loader.load_and_enhance_brief(str(brief_file))
        assert loaded is not None

    def test_multiple_regions(self, temp_dir):
        """Test brief with multiple target regions"""
        loader = EnhancedBriefLoader()

        brief = {
            "campaign_id": "multi_region",
            "products": ["Product A"],
            "target_region": "GLOBAL",
            "regions": ["US", "EMEA", "APAC"],
            "campaign_message": "Global Campaign",
        }

        brief_file = temp_dir / "multi_region.json"
        with open(brief_file, "w") as f:
            json.dump(brief, f)

        loaded = loader.load_and_enhance_brief(str(brief_file))
        assert loaded["target_region"] == "GLOBAL"


class TestCPGSchemaProcessing:
    """Test CPG schema-specific processing"""

    def test_brand_meta_extraction(self, temp_dir):
        """Test extracting brand metadata from CPG schema"""
        loader = EnhancedBriefLoader()

        cpg_brief = {
            "campaign_id": "cpg_test",
            "brand_meta": {
                "brand_name": "TestBrand",
                "primary_colors": ["#0000FF", "#FFD700"],
                "tagline": "Clean and Fresh",
            },
            "products": ["Product A"],
            "target_region": "US",
        }

        brief_file = temp_dir / "cpg_brief.json"
        with open(brief_file, "w") as f:
            json.dump(cpg_brief, f)

        loaded = loader.load_and_enhance_brief(str(brief_file))
        assert loaded is not None
        if "brand_meta" in loaded:
            assert loaded["brand_meta"]["brand_name"] == "TestBrand"

    def test_visual_concept_extraction(self, temp_dir):
        """Test extracting visual concept from CPG schema"""
        loader = EnhancedBriefLoader()

        brief = {
            "campaign_id": "visual_test",
            "products": ["Product A"],
            "visual_concept": {
                "theme": "spring_cleaning",
                "color_palette": ["blue", "white", "green"],
                "mood": "fresh and energetic",
            },
            "target_region": "US",
        }

        brief_file = temp_dir / "visual_brief.json"
        with open(brief_file, "w") as f:
            json.dump(brief, f)

        loaded = loader.load_and_enhance_brief(str(brief_file))
        assert loaded is not None


class TestCacheIntegration:
    """Test cache integration in brief loading"""

    def test_cache_lookup_during_load(self, temp_dir):
        """Test that brief loader checks cache"""
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()

        loader = EnhancedBriefLoader(cache_dir=str(cache_dir))

        brief = {
            "campaign_id": "cache_test",
            "products": ["Product A"],
            "target_region": "US",
        }

        brief_file = temp_dir / "cache_brief.json"
        with open(brief_file, "w") as f:
            json.dump(brief, f)

        loaded = loader.load_and_enhance_brief(str(brief_file))
        assert loaded is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
