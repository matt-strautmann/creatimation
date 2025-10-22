"""
Integration tests with real API calls

These tests require OPENAI_API_KEY in .env and will make actual API calls.
They provide comprehensive coverage of image generation, background removal,
and compositing modules.

NOTE: These tests are for the legacy DALL-E integration and are currently skipped
since the system has migrated to Google Gemini 2.5 Flash Image.
"""

import pytest
from PIL import Image

# Skip all tests - legacy DALL-E integration tests, system migrated to Gemini
pytestmark = pytest.mark.skip(reason="Legacy DALL-E tests - system migrated to Gemini")


class TestImageGeneratorWithAPI:
    """Test image generation with real DALL-E API calls"""

    def test_generate_product_image(self, temp_dir):
        """Test generating a product image"""
        generator = ImageGenerator()

        # Simple product generation
        prompt = "A bottle of blue dish soap on white background, product photography"
        image = generator.generate_image(prompt, size="1024x1024")

        assert image is not None
        assert isinstance(image, Image.Image)
        assert image.size == (1024, 1024)

    def test_generate_with_caching(self, temp_dir):
        """Test generation with cache"""
        cache_mgr = CacheManager(cache_dir=str(temp_dir / "cache"))
        generator = ImageGenerator(cache_manager=cache_mgr)

        prompt = "A red laundry detergent bottle, professional product photo"

        # First generation (cache miss)
        image1 = generator.generate_image(prompt, size="1024x1024")
        assert image1 is not None

        # Second generation (should use cache)
        image2 = generator.generate_image(prompt, size="1024x1024")
        assert image2 is not None

        # Verify cache was used
        stats = cache_mgr.get_cache_stats()
        assert stats["total_entries"] > 0

    def test_generate_scene_background(self, temp_dir):
        """Test generating scene backgrounds"""
        generator = ImageGenerator()

        prompt = "Modern kitchen countertop with natural lighting, clean and bright"
        image = generator.generate_image(prompt, size="1024x1024")

        assert image is not None
        assert isinstance(image, Image.Image)


class TestBackgroundRemoverWithAPI:
    """Test background removal with real rembg processing"""

    def test_remove_background_from_generated_image(self, temp_dir):
        """Test removing background from a generated product image"""
        # First generate an image
        generator = ImageGenerator()
        prompt = "A green spray bottle on white background, product photography"
        product_image = generator.generate_image(prompt, size="1024x1024")

        # Remove background
        remover = BackgroundRemover(cache_dir=str(temp_dir / "bg_cache"))
        transparent_image, was_cached, processing_time, cache_key = remover.remove_background(
            product_image, product_name="test_spray_bottle"
        )

        assert transparent_image is not None
        assert isinstance(transparent_image, Image.Image)
        assert transparent_image.mode == "RGBA"
        assert was_cached is False  # First time
        assert processing_time > 0
        assert cache_key is not None

    def test_background_removal_caching(self, temp_dir):
        """Test that background removal uses cache on second call"""
        generator = ImageGenerator()
        prompt = "A yellow sponge on white background"
        product_image = generator.generate_image(prompt, size="1024x1024")

        remover = BackgroundRemover(cache_dir=str(temp_dir / "bg_cache"))

        # First removal
        img1, cached1, time1, key1 = remover.remove_background(
            product_image, product_name="test_sponge"
        )
        assert cached1 is False

        # Second removal (should be cached)
        img2, cached2, time2, key2 = remover.remove_background(
            product_image, product_name="test_sponge"
        )
        assert cached2 is True
        assert time2 < time1  # Cache should be faster
        assert key1 == key2


class TestCompositorWithAPI:
    """Test image composition with real generated images"""

    def test_composite_product_on_background(self, temp_dir):
        """Test compositing transparent product on generated background"""
        generator = ImageGenerator()
        remover = BackgroundRemover(cache_dir=str(temp_dir / "bg_cache"))
        compositor = CreativeCompositor()

        # Generate product
        product_prompt = "A blue bottle of cleaning spray on white background"
        product_img = generator.generate_image(product_prompt, size="1024x1024")

        # Remove background
        transparent_product, _, _, _ = remover.remove_background(
            product_img, product_name="test_cleaner"
        )

        # Generate scene
        scene_prompt = "Modern bathroom counter with marble, bright lighting"
        background_img = generator.generate_image(scene_prompt, size="1024x1024")

        # Composite
        result = compositor.composite_product_on_scene(
            transparent_product, background_img, position="center", scale=0.6
        )

        assert result is not None
        assert isinstance(result, Image.Image)
        assert result.size == background_img.size

    def test_composite_with_text_overlay(self, temp_dir):
        """Test adding text overlay to composition"""
        generator = ImageGenerator()
        compositor = CreativeCompositor()

        # Generate a simple background
        bg_prompt = "Clean white kitchen background"
        background = generator.generate_image(bg_prompt, size="1024x1024")

        # Add text overlay
        result = compositor.add_text_overlay(
            background,
            message="Spring Cleaning Sale",
            position="top",
            font_size=72,
            color=(0, 0, 0),
        )

        assert result is not None
        assert isinstance(result, Image.Image)
        # Result should be same size or larger
        assert result.size[0] >= background.size[0]


class TestImageProcessorWithAPI:
    """Test image processing utilities with real images"""

    def test_resize_generated_image(self, temp_dir):
        """Test resizing generated images to different aspect ratios"""
        generator = ImageGenerator()
        processor = ImageProcessor()

        # Generate square image
        prompt = "A product bottle, clean white background"
        square_img = generator.generate_image(prompt, size="1024x1024")

        # Resize to 9:16
        portrait = processor.resize_to_aspect_ratio(square_img, "9x16")
        assert portrait is not None
        # Should be 9:16 aspect ratio
        assert portrait.size[0] * 16 == portrait.size[1] * 9

        # Resize to 16:9
        landscape = processor.resize_to_aspect_ratio(square_img, "16x9")
        assert landscape is not None
        # Should be 16:9 aspect ratio
        assert landscape.size[0] * 9 == landscape.size[1] * 16

    def test_apply_brand_colors(self, temp_dir):
        """Test applying brand color adjustments"""
        generator = ImageGenerator()
        processor = ImageProcessor()

        # Generate image
        prompt = "A cleaning product bottle"
        image = generator.generate_image(prompt, size="1024x1024")

        # Apply brand colors
        brand_colors = [(0, 100, 200), (255, 200, 0)]  # Blue and yellow
        result = processor.apply_brand_colors(image, brand_colors)

        assert result is not None
        assert isinstance(result, Image.Image)


class TestFullPipelineIntegration:
    """Test complete pipeline flow with API calls"""

    def test_end_to_end_creative_generation(self, temp_dir):
        """Test full pipeline: generate product, remove bg, composite, resize"""
        # Initialize components
        generator = ImageGenerator()
        remover = BackgroundRemover(cache_dir=str(temp_dir / "bg_cache"))
        compositor = CreativeCompositor()
        processor = ImageProcessor()

        # Step 1: Generate product
        product_prompt = "A modern detergent bottle, white background, professional photo"
        product_img = generator.generate_image(product_prompt, size="1024x1024")
        assert product_img is not None

        # Step 2: Remove background
        transparent, _, _, _ = remover.remove_background(product_img, product_name="detergent")
        assert transparent is not None
        assert transparent.mode == "RGBA"

        # Step 3: Generate scene
        scene_prompt = "Bright modern laundry room with white walls"
        scene_img = generator.generate_image(scene_prompt, size="1024x1024")
        assert scene_img is not None

        # Step 4: Composite
        composite = compositor.composite_product_on_scene(
            transparent, scene_img, position="center", scale=0.5
        )
        assert composite is not None

        # Step 5: Add text
        with_text = compositor.add_text_overlay(
            composite, message="Clean Fresh Bright", position="bottom", font_size=48
        )
        assert with_text is not None

        # Step 6: Create variants in different aspect ratios
        portrait = processor.resize_to_aspect_ratio(with_text, "9x16")
        landscape = processor.resize_to_aspect_ratio(with_text, "16x9")

        assert portrait is not None
        assert landscape is not None

        # Verify we have 3 variants
        variants = [with_text, portrait, landscape]
        assert len(variants) == 3
        assert all(v is not None for v in variants)

    def test_pipeline_with_multiple_products(self, temp_dir):
        """Test generating creatives for multiple products"""
        generator = ImageGenerator()
        remover = BackgroundRemover(cache_dir=str(temp_dir / "bg_cache"))

        products = [
            "A blue dish soap bottle, professional product photography",
            "A red spray cleaner bottle, white background",
        ]

        generated_products = []

        for prompt in products:
            # Generate
            img = generator.generate_image(prompt, size="1024x1024")
            assert img is not None

            # Remove background
            transparent, _, _, _ = remover.remove_background(
                img, product_name=f"product_{len(generated_products)}"
            )
            assert transparent is not None

            generated_products.append(transparent)

        # Verify we generated both products
        assert len(generated_products) == 2
        assert all(p.mode == "RGBA" for p in generated_products)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
