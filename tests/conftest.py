"""
Pytest configuration and shared fixtures for test suite.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_brief_data():
    """Sample campaign brief data"""
    return {
        "campaign_id": "test_campaign_2025",
        "products": ["Test Product A", "Test Product B"],
        "target_region": "US",
        "target_audience": "Test audience",
        "campaign_message": "Test Message",
    }


@pytest.fixture
def sample_brief_file(temp_dir, sample_brief_data):
    """Create a sample brief JSON file"""
    brief_path = temp_dir / "briefs" / "test_campaign.json"
    brief_path.parent.mkdir(parents=True, exist_ok=True)

    with open(brief_path, "w") as f:
        json.dump(sample_brief_data, f, indent=2)

    return brief_path


@pytest.fixture
def sample_image():
    """Generate a sample test image"""
    img = Image.new("RGB", (100, 100), color="red")
    return img


@pytest.fixture
def mock_output_structure(temp_dir):
    """Create mock output directory structure with sample files matching agent's expected structure"""
    output_dir = temp_dir / "output"

    # Create structure for 2 products, 3 ratios each
    # Structure: output/{product-slug}/hero-product/test/ratio/files.jpg
    products = ["test-product-a", "test-product-b"]
    ratios = ["1x1", "9x16", "16x9"]

    for product in products:
        for ratio in ratios:
            # Agent expects: product_dir / "hero-product" / campaign_id.split("_")[0] / ratio
            # For campaign_id "test_campaign_2025", first part is "test"
            ratio_dir = output_dir / product / "hero-product" / "test" / ratio
            ratio_dir.mkdir(parents=True, exist_ok=True)

            # Create sample variant files
            for i in range(3):
                variant_file = ratio_dir / f"{product}_hero-product_test_{ratio}_variant_{i+1}.jpg"
                # Create empty file
                variant_file.touch()

    return output_dir
