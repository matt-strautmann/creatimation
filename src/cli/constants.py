"""
CLI constants and configuration defaults.

Centralizes all hardcoded values from CLI commands to make them
configurable and maintainable.
"""

from typing import Any

# Directory structure
DEFAULT_WORKSPACE_DIRS = ["briefs", "brand-guides", "output", "cache", "templates", "assets"]
KEY_WORKSPACE_DIRS = ["briefs", "brand-guides", "output", "cache", "templates", "assets"]
REQUIRED_WORKSPACE_DIRS = ["briefs", "brand-guides", "output"]

# Configuration files
DEFAULT_CONFIG_FILENAME = ".creatimation.yml"
GLOBAL_CONFIG_DIR = ".creatimation"
GLOBAL_CONFIG_FILENAME = "config.yml"

# Supported regions
SUPPORTED_REGIONS = ["US", "EMEA", "APAC", "LATAM", "CA", "EU", "UK"]
DEFAULT_REGIONS = ["US"]

# Aspect ratios
SUPPORTED_ASPECT_RATIOS = ["1x1", "9x16", "16x9", "4x5", "5x4", "4x3", "3x4", "2x3", "3x2", "21x9"]
DEFAULT_ASPECT_RATIOS = ["1x1", "9x16", "16x9"]

# Template configurations
WORKSPACE_TEMPLATES = ["minimal", "cpg", "fashion", "tech", "custom"]
CONFIG_TEMPLATES = ["minimal", "complete", "cpg", "fashion", "tech"]

# Template-specific aspect ratios
TEMPLATE_ASPECT_RATIOS = {
    "cpg": ["1x1", "9x16", "16x9", "4x5", "5x4"],
    "fashion": ["9x16", "4x5", "1x1", "16x9"],
    "tech": ["16x9", "1x1", "9x16"],
    "minimal": DEFAULT_ASPECT_RATIOS,
    "complete": DEFAULT_ASPECT_RATIOS,
    "custom": DEFAULT_ASPECT_RATIOS,
}

# Default variant types
DEFAULT_VARIANT_TYPES = ["base", "color_shift", "text_style"]
LIFESTYLE_VARIANT_TYPES = ["base", "hero", "lifestyle"]

# Template-specific variant types
TEMPLATE_VARIANT_TYPES = {
    "cpg": ["base", "color_shift", "premium"],
    "fashion": ["elegant", "casual", "bold"],
    "tech": ["professional", "consumer", "enterprise"],
    "minimal": DEFAULT_VARIANT_TYPES,
    "complete": DEFAULT_VARIANT_TYPES,
    "custom": DEFAULT_VARIANT_TYPES,
}

# Brand guide sections
REQUIRED_BRAND_GUIDE_SECTIONS = ["brand", "colors", "visual", "messaging"]

# Configuration sections
REQUIRED_CONFIG_SECTIONS = ["project", "generation", "output"]

# Output formats
OUTPUT_FORMATS = ["table", "tree", "json"]
CONFIG_OUTPUT_FORMATS = ["table", "yaml", "json", "env"]

# Value types for configuration
CONFIG_VALUE_TYPES = ["string", "int", "float", "bool", "list"]

# Cache types
CACHE_TYPES = ["all", "products", "backgrounds", "metadata", "generated"]

# Default configuration values
DEFAULT_CONFIG_VALUES = {
    "generation": {
        "default_variants": 3,
        "aspect_ratios": DEFAULT_ASPECT_RATIOS,
        "variant_types": DEFAULT_VARIANT_TYPES,
        "quality": 95,
        "variants_per_ratio": 3,
    },
    "cache": {
        "enabled": True,
        "directory": "cache",
    },
    "output": {
        "directory": "output",
        "semantic_structure": True,
    },
    "project": {
        "template": "minimal",
    },
}

# Template-specific sample data
TEMPLATE_SAMPLE_PRODUCTS = {
    "cpg": ["Power Dish Soap", "Eco Laundry Detergent", "Multi-Surface Cleaner"],
    "fashion": ["Summer Collection", "Evening Wear", "Casual Essentials"],
    "tech": ["Smart Device", "Mobile App", "Cloud Service"],
    "minimal": ["Product A", "Product B"],
}

TEMPLATE_SAMPLE_REGIONS = {
    "cpg": ["US", "EMEA", "APAC"],
    "fashion": ["US", "EMEA"],
    "tech": ["US", "APAC"],
    "minimal": ["US"],
}

TEMPLATE_SAMPLE_MESSAGES = {
    "cpg": "Clean with confidence",
    "fashion": "Style that speaks to you",
    "tech": "Innovation that works",
    "minimal": "Quality you can trust",
}


# Configuration templates for different templates
def get_template_config(template: str) -> dict[str, Any]:
    """Get configuration template for specific template type."""
    base_config = DEFAULT_CONFIG_VALUES.copy()

    if template in TEMPLATE_ASPECT_RATIOS:
        base_config["generation"]["aspect_ratios"] = TEMPLATE_ASPECT_RATIOS[template]

    if template in TEMPLATE_VARIANT_TYPES:
        base_config["generation"]["variant_types"] = TEMPLATE_VARIANT_TYPES[template]

    # Template-specific adjustments
    if template == "cpg":
        base_config["generation"]["default_variants"] = 5
        base_config["project"]["industry"] = "consumer-packaged-goods"
    elif template == "fashion":
        base_config["project"]["industry"] = "fashion"
    elif template == "tech":
        base_config["project"]["industry"] = "technology"

    return base_config


def get_sample_brief_data(template: str) -> dict[str, Any]:
    """Get sample brief data for template."""
    return {
        "campaign_id": f"sample_{template}_campaign",
        "products": TEMPLATE_SAMPLE_PRODUCTS.get(template, TEMPLATE_SAMPLE_PRODUCTS["minimal"]),
        "target_regions": TEMPLATE_SAMPLE_REGIONS.get(template, TEMPLATE_SAMPLE_REGIONS["minimal"]),
        "campaign_message": TEMPLATE_SAMPLE_MESSAGES.get(
            template, TEMPLATE_SAMPLE_MESSAGES["minimal"]
        ),
        "creative_requirements": {
            "aspect_ratios": TEMPLATE_ASPECT_RATIOS.get(template, DEFAULT_ASPECT_RATIOS),
            "variant_types": TEMPLATE_VARIANT_TYPES.get(template, DEFAULT_VARIANT_TYPES),
        },
    }


# Environment variable prefix
ENV_PREFIX = "CREATIMATION_"

# Validation constants
BRIEF_REQUIRED_FIELDS = ["campaign_id", "products", "target_regions", "campaign_message"]

# Default workspace configuration template
DEFAULT_WORKSPACE_CONFIG_TEMPLATE = """# Creatimation Workspace Configuration
project:
  name: "My Creative Workspace"
  output_dir: "output"

generation:
  default_variants: 3
  aspect_ratios: ["1x1", "9x16", "16x9"]

cache:
  enabled: true
  directory: "cache"
"""
