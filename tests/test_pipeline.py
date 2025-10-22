"""
Integration tests for Creative Automation Pipeline

Tests the end-to-end pipeline with all components integrated.
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cache_manager import CacheManager
from output_manager import OutputManager
from state_tracker import StateTracker


class TestCacheManager:
    """Test cache management functionality"""

    def test_cache_initialization(self, temp_dir):
        """Test cache manager initialization"""
        cache_mgr = CacheManager(cache_dir=str(temp_dir / "cache"))

        assert cache_mgr.cache_dir.exists()
        assert (cache_mgr.cache_dir / "products").exists()
        assert cache_mgr.index_path.exists()

    def test_register_and_get_cache_entry(self, temp_dir):
        """Test registering and retrieving cache entries"""
        cache_mgr = CacheManager(cache_dir=str(temp_dir / "cache"))

        metadata = {
            "product_name": "Test Product",
            "generated_at": "2025-01-01",
            "method": "DALL-E 3",
        }

        cache_mgr.register_cache_entry("test_key_123", "test_product.jpg", metadata)

        # Retrieve entry
        entry = cache_mgr.get_cache_entry("test_key_123")
        assert entry is not None
        assert entry["file_path"] == "test_product.jpg"
        assert entry["metadata"]["product_name"] == "Test Product"

    def test_cache_hit_query(self, temp_dir):
        """Test querying cache by metadata"""
        cache_mgr = CacheManager(cache_dir=str(temp_dir / "cache"))

        metadata1 = {"product_name": "Product A", "region": "US"}
        metadata2 = {"product_name": "Product B", "region": "EMEA"}

        cache_mgr.register_cache_entry("key1", "product_a.jpg", metadata1)
        cache_mgr.register_cache_entry("key2", "product_b.jpg", metadata2)

        # Query by product name
        matches = cache_mgr.query_cache(product_name="Product A")
        assert len(matches) == 1
        assert matches[0]["file_path"] == "product_a.jpg"

    def test_get_cache_stats(self, temp_dir):
        """Test cache statistics"""
        cache_mgr = CacheManager(cache_dir=str(temp_dir / "cache"))

        metadata1 = {"product_name": "Product A"}
        metadata2 = {"product_name": "Product B"}

        cache_mgr.register_cache_entry("key1", "product_a.jpg", metadata1)
        cache_mgr.register_cache_entry("key2", "product_b.jpg", metadata2)

        stats = cache_mgr.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["cache_dir"] == str(cache_mgr.cache_dir)


class TestOutputManager:
    """Test output file management"""

    def test_slugify(self, temp_dir):
        """Test product name slugification"""
        output_mgr = OutputManager(output_dir=str(temp_dir / "output"))

        assert output_mgr._slugify("Power Dish Soap") == "power-dish-soap"
        assert output_mgr._slugify("Ultra Laundry Detergent") == "ultra-laundry-detergent"
        assert output_mgr._slugify("Product With Special!@# Chars") == "product-with-special-chars"
        assert output_mgr._slugify("Multiple___Underscores") == "multiple-underscores"
        assert output_mgr._slugify("  Spaces  Everywhere  ") == "spaces-everywhere"

    def test_save_creative(self, temp_dir, sample_image):
        """Test saving creative with metadata"""
        output_mgr = OutputManager(output_dir=str(temp_dir / "output"))

        metadata = {"campaign_id": "test_campaign", "product": "Test Product", "ratio": "1x1"}

        output_path = output_mgr.save_creative(
            sample_image,
            product_name="Test Product",
            ratio="1x1",
            metadata=metadata,
            template="hero-product",
            region="US",
        )

        # Verify file was created
        assert Path(output_path).exists()
        assert Path(output_path).suffix == ".jpg"

        # Verify directory structure
        assert "test-product" in output_path
        assert "hero-product" in output_path
        assert "us" in output_path
        assert "1x1" in output_path

        # Verify metadata file was created
        metadata_path = Path(output_path).parent / "metadata.json"
        assert metadata_path.exists()

        # Verify metadata content
        with open(metadata_path) as f:
            saved_metadata = json.load(f)
            assert saved_metadata["campaign_id"] == "test_campaign"
            assert saved_metadata["ratio"] == "1x1"
            assert saved_metadata["template"] == "hero-product"
            assert saved_metadata["region"] == "US"
            assert "saved_at" in saved_metadata

    def test_save_creative_with_variant_id(self, temp_dir, sample_image):
        """Test saving creative with variant ID for A/B testing"""
        output_mgr = OutputManager(output_dir=str(temp_dir / "output"))

        metadata = {"campaign_id": "test_campaign"}

        output_path = output_mgr.save_creative(
            sample_image,
            product_name="Test Product",
            ratio="1x1",
            metadata=metadata,
            template="minimal_blue",
            region="APAC",
            variant_id="v1",
        )

        # Verify variant ID in filename
        assert "_v1_" in output_path
        assert "minimal_blue" in output_path
        assert "apac" in output_path

    def test_get_output_summary(self, temp_dir, sample_image):
        """Test output directory summary"""
        output_mgr = OutputManager(output_dir=str(temp_dir / "output"))

        metadata = {"campaign_id": "test"}

        # Save multiple creatives
        output_mgr.save_creative(sample_image, "Product A", "1x1", metadata, "hero-product", "US")
        output_mgr.save_creative(sample_image, "Product B", "9x16", metadata, "hero-product", "US")

        summary = output_mgr.get_output_summary()
        assert summary["total_creatives"] == 2
        assert summary["total_size_bytes"] > 0
        assert "product-a" in summary["products"] or "product-b" in summary["products"]


class TestStateTracker:
    """Test pipeline state tracking"""

    def test_state_tracker_initialization(self, temp_dir):
        """Test state tracker initialization"""
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        assert state_tracker.campaign_id == "test_campaign"
        assert state_tracker.state_file.exists()
        assert state_tracker.state["campaign_id"] == "test_campaign"

    def test_update_product_state(self, temp_dir):
        """Test updating product state"""
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        state_tracker.update_product_state(
            "test-product", {"product_generated": True, "background_removed": True}
        )

        # Verify state was saved
        product_state = state_tracker.get_product_state("test-product")
        assert product_state is not None
        assert product_state["product_generated"] is True
        assert product_state["background_removed"] is True
        assert "updated_at" in product_state

    def test_mark_step_complete(self, temp_dir):
        """Test marking pipeline steps as complete"""
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        # Mark valid steps
        state_tracker.mark_step_complete("brief_loaded")
        state_tracker.mark_step_complete("products_generated")

        # Verify steps are marked
        assert state_tracker.is_step_complete("brief_loaded")
        assert state_tracker.is_step_complete("products_generated")
        assert not state_tracker.is_step_complete("scenes_generated")

    def test_get_next_step(self, temp_dir):
        """Test getting next step to execute"""
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        # Initially should return first step
        next_step = state_tracker.get_next_step()
        assert next_step == "brief_loaded"

        # After marking first step complete
        state_tracker.mark_step_complete("brief_loaded")
        next_step = state_tracker.get_next_step()
        assert next_step == "products_generated"

    def test_get_summary(self, temp_dir):
        """Test getting state summary"""
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        state_tracker.mark_step_complete("brief_loaded")
        state_tracker.mark_step_complete("products_generated")

        summary = state_tracker.get_summary()
        assert summary["campaign_id"] == "test_campaign"
        assert "progress" in summary
        assert "progress_percentage" in summary
        assert summary["progress_percentage"] > 0
        assert summary["next_step"] == "scenes_generated"

    def test_log_error(self, temp_dir):
        """Test logging errors"""
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        state_tracker.log_error("Test error message", {"step": "product_generation"})

        summary = state_tracker.get_summary()
        assert summary["errors_count"] == 1
        assert len(state_tracker.state["errors"]) == 1
        assert state_tracker.state["errors"][0]["message"] == "Test error message"

    def test_log_warning(self, temp_dir):
        """Test logging warnings"""
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        state_tracker.log_warning("Test warning", {"context": "cache"})

        summary = state_tracker.get_summary()
        assert summary["warnings_count"] == 1

    def test_can_resume(self, temp_dir):
        """Test resume functionality"""
        # Create initial state
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        state_tracker.mark_step_complete("brief_loaded")
        state_tracker._save_state()

        # Create new tracker for same campaign
        state_tracker2 = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        assert state_tracker2.can_resume()
        assert state_tracker2.is_step_complete("brief_loaded")

    def test_clear_state(self, temp_dir):
        """Test clearing state"""
        state_tracker = StateTracker(campaign_id="test_campaign", state_dir=str(temp_dir))

        state_tracker.mark_step_complete("brief_loaded")
        assert state_tracker.state_file.exists()

        state_tracker.clear_state()
        assert not state_tracker.state_file.exists()
        assert not state_tracker.is_step_complete("brief_loaded")


class TestPipelineIntegration:
    """End-to-end pipeline integration tests"""

    @pytest.mark.skip(reason="Requires OpenAI API key and actual execution")
    def test_full_pipeline_execution(self, temp_dir, sample_brief_file):
        """
        Full pipeline test with actual execution.
        Skipped by default - run manually with valid OpenAI API key.
        """
        from main import CreativePipeline

        pipeline = CreativePipeline(no_cache=True)

        results = pipeline.process_campaign(str(sample_brief_file), dry_run=False, resume=False)

        # Verify results
        assert results["total_creatives"] > 0
        assert len(results["products_processed"]) == 2

    def test_dry_run_execution(self, temp_dir, sample_brief_file):
        """Test pipeline dry run mode"""
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        from main import CreativePipeline

        pipeline = CreativePipeline()

        results = pipeline.process_campaign(str(sample_brief_file), dry_run=True, resume=False)

        assert results["dry_run"] is True
        assert results["products"] == 2
        assert "ratios" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
