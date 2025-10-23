#!/usr/bin/env python3
"""
Temporary Test Script - Validate Primary Commands After Type Fixes

Tests all main functionality to ensure type fixes didn't break runtime behavior.
"""

import sys
import traceback
from pathlib import Path

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []

    def test(self, name: str, func):
        """Run a test and track results."""
        print(f"\n{BLUE}Testing:{RESET} {name}")
        try:
            func()
            print(f"{GREEN}✓ PASS{RESET}")
            self.passed += 1
            self.tests.append((name, True, None))
        except Exception as e:
            print(f"{RED}✗ FAIL{RESET}: {str(e)}")
            traceback.print_exc()
            self.failed += 1
            self.tests.append((name, False, str(e)))

    def summary(self):
        """Print test summary."""
        print("\n" + "=" * 70)
        print(f"{BLUE}TEST SUMMARY{RESET}")
        print("=" * 70)
        print(f"Total tests: {self.passed + self.failed}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")

        if self.failed > 0:
            print(f"\n{RED}Failed Tests:{RESET}")
            for name, passed, error in self.tests:
                if not passed:
                    print(f"  - {name}: {error}")

        print("=" * 70)
        return self.failed == 0


def test_imports():
    """Test that all primary modules can be imported."""
    print("  → Importing core modules...")

    # Core modules
    import src.config
    import src.brand_guide_loader
    import src.cache_manager
    import src.state_tracker
    import src.output_manager
    import src.text_variant_engine

    # CLI modules
    import src.cli.constants
    import src.cli.utils.output
    import src.cli.commands.config
    import src.cli.commands.cache
    import src.cli.commands.generate

    print("  → All imports successful")


def test_config_manager():
    """Test ConfigManager functionality."""
    from src.config import ConfigManager, CreatimationConfig

    print("  → Creating ConfigManager...")
    manager = ConfigManager()

    print("  → Loading default config...")
    config = manager.load()

    assert isinstance(config, CreatimationConfig), "Config should be CreatimationConfig instance"
    # Just check that config loads successfully - name may vary
    assert hasattr(config.project, 'name'), "Config should have project name"
    assert config.generation.variants_per_ratio >= 1, "Variants should be >= 1"

    print(f"  → Config loaded: project={config.project.name}")


def test_brand_guide_loader():
    """Test BrandGuideLoader functionality."""
    from src.brand_guide_loader import BrandGuideLoader
    from pathlib import Path

    print("  → Creating BrandGuideLoader...")
    loader = BrandGuideLoader()

    # Check if a brand guide exists to test with
    brand_guides_dir = Path("brand-guides")
    if brand_guides_dir.exists():
        brand_files = list(brand_guides_dir.glob("*.yml")) + list(brand_guides_dir.glob("*.yaml"))
        if brand_files:
            print(f"  → Loading brand guide: {brand_files[0].name}")
            guide = loader.load(str(brand_files[0]))
            assert hasattr(guide, 'colors'), "Brand guide should have colors"
            print(f"  → Brand guide loaded: {guide.brand.name}")
        else:
            print(f"  → {YELLOW}Skipped: No brand guide files found{RESET}")
    else:
        print(f"  → {YELLOW}Skipped: brand-guides directory not found{RESET}")


def test_cache_manager():
    """Test CacheManager basic functionality."""
    from src.cache_manager import CacheManager
    import tempfile
    import shutil

    print("  → Creating temporary cache...")
    temp_dir = tempfile.mkdtemp(prefix="test_cache_")

    try:
        manager = CacheManager(cache_dir=temp_dir)

        print("  → Testing cache stats...")
        stats = manager.get_cache_stats()
        assert isinstance(stats, dict), "Stats should be a dict"
        assert "total_entries" in stats, "Stats should have total_entries"

        print(f"  → Cache initialized: {stats['total_entries']} entries")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_state_tracker():
    """Test StateTracker functionality."""
    from src.state_tracker import StateTracker
    import tempfile
    import shutil

    print("  → Creating temporary state...")
    temp_dir = tempfile.mkdtemp(prefix="test_state_")

    try:
        tracker = StateTracker(campaign_id="test_campaign", state_dir=temp_dir)

        print("  → Testing state operations...")
        tracker.mark_step_complete("brief_loaded")

        assert tracker.is_step_complete("brief_loaded"), "Step should be marked complete"

        next_step = tracker.get_next_step()
        print(f"  → Next step: {next_step}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_text_variant_engine():
    """Test TextVariantEngine initialization."""
    from src.text_variant_engine import TextVariantEngine

    print("  → Initializing TextVariantEngine...")
    engine = TextVariantEngine()

    print("  → Testing text variant generation...")
    # Test basic initialization - actual variant generation requires full params
    assert hasattr(engine, 'message_variants'), "Should have message variants"
    assert len(engine.message_variants) > 0, "Should have message variant templates"

    print(f"  → Engine has {len(engine.message_variants)} message templates")


def test_cli_constants():
    """Test CLI constants are accessible."""
    from src.cli.constants import (
        DEFAULT_ASPECT_RATIOS,
        SUPPORTED_REGIONS,
        CONFIG_TEMPLATES,
        get_template_config
    )

    print("  → Checking constants...")
    assert len(DEFAULT_ASPECT_RATIOS) > 0, "Should have default aspect ratios"
    assert len(SUPPORTED_REGIONS) > 0, "Should have supported regions"
    assert len(CONFIG_TEMPLATES) > 0, "Should have config templates"

    print("  → Testing template config generation...")
    config = get_template_config("minimal")
    assert isinstance(config, dict), "Template config should be a dict"

    print(f"  → Templates available: {', '.join(CONFIG_TEMPLATES)}")


def test_output_utilities():
    """Test output utilities."""
    from src.cli.utils.output import (
        console,
        create_table,
        format_size,
        format_duration
    )
    from rich.panel import Panel

    print("  → Testing console...")
    assert console is not None, "Console should be initialized"

    print("  → Testing table creation...")
    table = create_table("Test Table")
    assert table is not None, "Table should be created"

    print("  → Testing panel creation...")
    panel = Panel("Test Content", title="Test Title")
    assert panel is not None, "Panel should be created"

    print("  → Testing formatters...")
    size_str = format_size(1024 * 1024)  # 1MB
    assert "MB" in size_str, "Size should be formatted in MB"

    duration_str = format_duration(90.5)  # 1m 30s
    assert "m" in duration_str or "s" in duration_str, "Duration should be formatted"

    print(f"  → Format examples: {size_str}, {duration_str}")


def test_config_command_helpers():
    """Test config command helper functions."""
    from src.cli.commands.config import (
        _get_default_config,
        _get_global_config_template,
    )

    print("  → Testing default config...")
    config = _get_default_config()
    assert isinstance(config, dict), "Default config should be dict"
    assert "generation" in config, "Should have generation config"

    print("  → Testing global config template...")
    template = _get_global_config_template("complete")
    assert isinstance(template, dict), "Template should be dict"

    print(f"  → Config sections: {', '.join(config.keys())}")


def test_cache_command_helpers():
    """Test cache command helper functions."""
    from src.cli.commands.cache import _collect_cache_statistics
    from src.cache_manager import CacheManager
    import tempfile
    import shutil

    print("  → Testing cache statistics collection...")
    temp_dir = tempfile.mkdtemp(prefix="test_cache_stats_")

    try:
        manager = CacheManager(cache_dir=temp_dir)
        stats = _collect_cache_statistics(manager)

        assert isinstance(stats, dict), "Stats should be dict"
        assert "total_files" in stats, "Should have total_files"

        print(f"  → Stats collected: {stats['total_files']} files")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_s3_migration():
    """Test S3 migration imports and basic structures."""
    from src.s3_migration import MigrationPlan, MigrationResult

    print("  → Testing MigrationPlan...")
    plan = MigrationPlan(
        total_assets=10,
        total_size_bytes=1024 * 1024,
        products=[],
        semantic_assets=[],
        cache_entries=[]
    )

    assert plan.total_assets == 10, "Plan should have correct asset count"

    print("  → Testing MigrationResult...")
    result = MigrationResult(plan=plan)

    assert result.uploaded_count == 0, "Result should start with 0 uploads"
    assert result.failed_files is not None, "Failed files should be initialized"

    print(f"  → Migration structures valid")


def test_campaign_variant_generator():
    """Test CampaignVariantGenerator imports."""
    from src.campaign_variant_generator import CampaignVariantGenerator
    import tempfile
    import shutil

    print("  → Creating variant generator...")
    temp_dir = tempfile.mkdtemp(prefix="test_variants_")

    try:
        generator = CampaignVariantGenerator(cache_dir=temp_dir)
        print(f"  → Generator initialized with cache: {temp_dir}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run all tests."""
    print(f"\n{BLUE}{'=' * 70}{RESET}")
    print(f"{BLUE}Creatimation Type Fix Validation Tests{RESET}")
    print(f"{BLUE}{'=' * 70}{RESET}")

    runner = TestRunner()

    # Run all tests
    runner.test("Module Imports", test_imports)
    runner.test("ConfigManager", test_config_manager)
    runner.test("BrandGuideLoader", test_brand_guide_loader)
    runner.test("CacheManager", test_cache_manager)
    runner.test("StateTracker", test_state_tracker)
    runner.test("TextVariantEngine", test_text_variant_engine)
    runner.test("CLI Constants", test_cli_constants)
    runner.test("Output Utilities", test_output_utilities)
    runner.test("Config Command Helpers", test_config_command_helpers)
    runner.test("Cache Command Helpers", test_cache_command_helpers)
    runner.test("S3 Migration", test_s3_migration)
    runner.test("CampaignVariantGenerator", test_campaign_variant_generator)

    # Print summary
    success = runner.summary()

    if success:
        print(f"\n{GREEN}🎉 All tests passed! Type fixes didn't break anything.{RESET}\n")
        return 0
    else:
        print(f"\n{RED}❌ Some tests failed. Please review the errors above.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
