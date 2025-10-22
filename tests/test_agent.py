"""
Comprehensive tests for Creative Automation Agent

Tests the MCP-based agentic system including brief monitoring,
task triggering, variant tracking, and alert generation.
"""

import json
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from creative_automation_agent import (
    AlertSeverity,
    CreativeAutomationAgent,
    MCPContext,
    VariantStatus,
)


class TestBriefMonitoring:
    """Test campaign brief monitoring and change detection"""

    def test_scan_for_new_briefs(self, temp_dir, sample_brief_data, clean_agent):
        """Test scanning for new campaign briefs"""
        import json

        # Create a brief file directly in clean agent's directory
        brief_file = clean_agent.briefs_dir / "test_campaign.json"
        with open(brief_file, "w") as f:
            json.dump(sample_brief_data, f, indent=2)

        new_briefs = clean_agent.scan_for_new_briefs()

        assert len(new_briefs) > 0
        assert brief_file in new_briefs

    def test_ignore_unchanged_briefs(self, temp_dir, sample_brief_data, clean_agent):
        """Test that unchanged briefs are not detected as new"""
        import json

        # Create a brief file directly in clean agent's directory
        brief_file = clean_agent.briefs_dir / "test_campaign.json"
        with open(brief_file, "w") as f:
            json.dump(sample_brief_data, f, indent=2)

        # First scan
        clean_agent.scan_for_new_briefs()
        campaign_id, brief_data = clean_agent.analyze_campaign_brief(brief_file)
        clean_agent.trigger_generation_task(brief_file, campaign_id, brief_data)

        # Second scan should find no changes
        new_briefs = clean_agent.scan_for_new_briefs()
        assert brief_file not in new_briefs

    def test_detect_modified_briefs(self, temp_dir, sample_brief_data, clean_agent):
        """Test detection of modified campaign briefs"""
        import json

        # Create a brief file directly in clean agent's directory
        brief_file = clean_agent.briefs_dir / "test_campaign.json"
        with open(brief_file, "w") as f:
            json.dump(sample_brief_data, f, indent=2)

        # Initial scan
        clean_agent.scan_for_new_briefs()
        campaign_id, brief_data = clean_agent.analyze_campaign_brief(brief_file)
        clean_agent.trigger_generation_task(brief_file, campaign_id, brief_data)

        # Modify the brief
        with open(brief_file) as f:
            brief_data = json.load(f)
        brief_data["campaign_message"] = "Modified Message"
        with open(brief_file, "w") as f:
            json.dump(brief_data, f)

        # Should detect modification
        new_briefs = clean_agent.scan_for_new_briefs()
        assert brief_file in new_briefs


class TestTaskTriggering:
    """Test automated task triggering"""

    def test_trigger_generation_task(self, temp_dir, sample_brief_file):
        """Test triggering variant generation task"""
        agent = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        campaign_id, brief_data = agent.analyze_campaign_brief(sample_brief_file)
        agent.trigger_generation_task(sample_brief_file, campaign_id, brief_data)

        # Verify campaign is now monitored
        assert campaign_id in agent.monitored_campaigns
        state = agent.monitored_campaigns[campaign_id]

        # Verify state structure
        assert state.campaign_id == campaign_id
        assert len(state.products) == 2
        assert state.status == VariantStatus.IN_PROGRESS
        assert isinstance(state.variants_generated, dict)

    def test_state_persistence(self, temp_dir, sample_brief_file):
        """Test that agent state is persisted to disk"""
        agent1 = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        campaign_id, brief_data = agent1.analyze_campaign_brief(sample_brief_file)
        agent1.trigger_generation_task(sample_brief_file, campaign_id, brief_data)
        agent1._save_state()

        # Create new agent instance
        agent2 = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        # Verify state was loaded
        assert campaign_id in agent2.monitored_campaigns


class TestVariantTracking:
    """Test variant generation tracking"""

    def test_track_variant_generation(self, temp_dir, sample_brief_file, mock_output_structure):
        """Test tracking of generated variants"""
        agent = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        campaign_id, brief_data = agent.analyze_campaign_brief(sample_brief_file)
        agent.trigger_generation_task(sample_brief_file, campaign_id, brief_data)

        # Track variants from mock output
        agent.track_variant_generation(campaign_id, output_dir=mock_output_structure)

        state = agent.monitored_campaigns[campaign_id]

        # Verify variant counts (2 products × 3 ratios × 3 variants = 18)
        assert state.total_variants == 18

        # Verify per-product counts
        for product_name in ["Test Product A", "Test Product B"]:
            assert product_name in state.variants_generated
            product_variants = state.variants_generated[product_name]
            assert product_variants["1x1"] == 3
            assert product_variants["9x16"] == 3
            assert product_variants["16x9"] == 3

    def test_track_empty_output(self, temp_dir, sample_brief_file):
        """Test tracking with no generated output"""
        agent = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        campaign_id, brief_data = agent.analyze_campaign_brief(sample_brief_file)
        agent.trigger_generation_task(sample_brief_file, campaign_id, brief_data)

        # Track with empty output directory
        empty_output = temp_dir / "empty_output"
        empty_output.mkdir()

        agent.track_variant_generation(campaign_id, output_dir=empty_output)

        state = agent.monitored_campaigns[campaign_id]
        assert state.total_variants == 0


class TestVariantSufficiency:
    """Test variant sufficiency checking"""

    def test_check_sufficient_variants(self, temp_dir, sample_brief_file, mock_output_structure):
        """Test detection of sufficient variants"""
        agent = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        campaign_id, brief_data = agent.analyze_campaign_brief(sample_brief_file)
        agent.trigger_generation_task(sample_brief_file, campaign_id, brief_data)
        agent.track_variant_generation(campaign_id, output_dir=mock_output_structure)

        # Check sufficiency (should be sufficient: 9 variants per product across all ratios)
        insufficient = agent.check_variant_sufficiency(campaign_id)

        # With 9 variants per product (3 per ratio × 3 ratios), should be sufficient
        assert len(insufficient) == 0

    def test_check_insufficient_variants(self, temp_dir, sample_brief_data, clean_agent):
        """Test detection of insufficient variants"""
        import json

        # Create brief file
        brief_file = clean_agent.briefs_dir / "test_campaign.json"
        with open(brief_file, "w") as f:
            json.dump(sample_brief_data, f, indent=2)

        campaign_id, brief_data = clean_agent.analyze_campaign_brief(brief_file)
        clean_agent.trigger_generation_task(brief_file, campaign_id, brief_data)

        # Don't track any variants - all products should be insufficient
        insufficient = clean_agent.check_variant_sufficiency(campaign_id)

        # Both products should have insufficient variants
        assert len(insufficient) == 2

    def test_check_missing_campaign(self, temp_dir):
        """Test checking sufficiency for non-existent campaign"""
        agent = CreativeAutomationAgent(briefs_dir=str(temp_dir / "briefs"))

        insufficient = agent.check_variant_sufficiency("non_existent_campaign")

        # Should return empty list for missing campaign
        assert len(insufficient) == 0


class TestMCPContext:
    """Test Model Context Protocol data structure"""

    def test_mcp_context_creation(self):
        """Test creating MCP context"""
        context = MCPContext(
            campaign_id="test_campaign",
            campaign_name="Test Campaign",
            timestamp="2025-01-01T00:00:00",
            target_region="US",
            target_audience="Test Audience",
            total_products=2,
            products_processed=2,
            products_pending=[],
            products_failed=[],
            total_variants_expected=6,
            total_variants_generated=6,
            variants_by_ratio={"1x1": 2, "9x16": 2, "16x9": 2},
            variants_per_product={"Product A": 3, "Product B": 3},
            missing_assets=[],
            insufficient_variants=[],
            cache_hit_rate=50.0,
            processing_time=10.0,
            error_count=0,
            alert_type="test_alert",
            severity="info",
            issues=[],
            recommendations=[],
        )

        assert context.campaign_id == "test_campaign"
        assert context.total_variants_expected == 6
        assert context.total_variants_generated == 6

    def test_mcp_context_to_dict(self):
        """Test converting MCP context to dict"""
        context = MCPContext(
            campaign_id="test_campaign",
            campaign_name="Test Campaign",
            timestamp="2025-01-01T00:00:00",
            target_region="US",
            target_audience="Test Audience",
            total_products=2,
            products_processed=1,
            products_pending=["Product B"],
            products_failed=[],
            total_variants_expected=6,
            total_variants_generated=4,
            variants_by_ratio={"1x1": 2, "9x16": 2, "16x9": 0},
            variants_per_product={"Product A": 4},
            missing_assets=[],
            insufficient_variants=["Test Product"],
            cache_hit_rate=25.0,
            processing_time=15.0,
            error_count=0,
            alert_type="insufficient_variants",
            severity="warning",
            issues=["Product has < 3 variants"],
            recommendations=["Re-run generation"],
        )

        context_dict = context.to_dict()

        assert context_dict["campaign_id"] == "test_campaign"
        assert context_dict["total_variants_generated"] == 4
        assert len(context_dict["insufficient_variants"]) == 1

    def test_mcp_context_to_llm_prompt(self):
        """Test generating LLM prompt from MCP context"""
        context = MCPContext(
            campaign_id="test_campaign",
            campaign_name="Test Campaign",
            timestamp="2025-01-01T00:00:00",
            target_region="US",
            target_audience="Test Audience",
            total_products=2,
            products_processed=0,
            products_pending=["Test Product A", "Test Product B"],
            products_failed=[],
            total_variants_expected=6,
            total_variants_generated=2,
            variants_by_ratio={"1x1": 2, "9x16": 0, "16x9": 0},
            variants_per_product={"Product A": 2},
            missing_assets=[],
            insufficient_variants=["Test Product A", "Test Product B"],
            cache_hit_rate=0.0,
            processing_time=5.0,
            error_count=0,
            alert_type="insufficient_variants",
            severity="warning",
            issues=["2 products have < 3 variants"],
            recommendations=["Re-run generation with increased variant count"],
        )

        prompt = context.to_llm_prompt()

        # Verify prompt contains key information
        assert "test_campaign" in prompt
        assert "2/6" in prompt or "2 of 6" in prompt
        assert "Test Product A" in prompt or "products" in prompt.lower()


class TestAlertGeneration:
    """Test MCP alert generation"""

    def test_generate_mcp_alert(self, temp_dir, sample_brief_data, clean_agent):
        """Test generating MCP alert"""
        import json

        # Create brief file
        brief_file = clean_agent.briefs_dir / "test_campaign.json"
        with open(brief_file, "w") as f:
            json.dump(sample_brief_data, f, indent=2)

        campaign_id, brief_data = clean_agent.analyze_campaign_brief(brief_file)
        clean_agent.trigger_generation_task(brief_file, campaign_id, brief_data)

        # Generate alert for insufficient variants
        mcp_context = clean_agent.generate_mcp_alert(
            campaign_id, alert_type="insufficient_variants", severity=AlertSeverity.WARNING
        )

        assert isinstance(mcp_context, MCPContext)
        assert mcp_context.campaign_id == campaign_id
        assert mcp_context.total_variants_expected == 18  # 2 products × 3 ratios × 3 variants = 18
        assert len(mcp_context.insufficient_variants) > 0

    def test_generate_completion_alert(self, temp_dir, sample_brief_file, mock_output_structure):
        """Test generating completion alert"""
        agent = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        campaign_id, brief_data = agent.analyze_campaign_brief(sample_brief_file)
        agent.trigger_generation_task(sample_brief_file, campaign_id, brief_data)
        agent.track_variant_generation(campaign_id, output_dir=mock_output_structure)

        # Mark as complete
        agent.monitored_campaigns[campaign_id].status = VariantStatus.COMPLETED

        # Generate completion alert
        mcp_context = agent.generate_mcp_alert(
            campaign_id, alert_type="generation_complete", severity=AlertSeverity.INFO
        )

        assert mcp_context.total_variants_generated == 18
        assert len(mcp_context.insufficient_variants) == 0


class TestMonitoringCycle:
    """Test complete monitoring cycle"""

    def test_run_monitoring_cycle(self, temp_dir, sample_brief_file):
        """Test running a complete monitoring cycle"""
        agent = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        # Run monitoring cycle
        agent.run_monitoring_cycle()

        # Verify campaigns were detected and tracked
        assert len(agent.monitored_campaigns) > 0

    def test_completion_detection(self, temp_dir, sample_brief_file, mock_output_structure):
        """Test detecting campaign completion"""
        agent = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        # Initial setup
        campaign_id, brief_data = agent.analyze_campaign_brief(sample_brief_file)
        agent.trigger_generation_task(sample_brief_file, campaign_id, brief_data)

        # Track variants (should have sufficient variants)
        agent.track_variant_generation(campaign_id, output_dir=mock_output_structure)

        # Check if campaign should be marked complete
        state = agent.monitored_campaigns[campaign_id]

        # With 18 variants (sufficient for 2 products), campaign should be completable
        assert state.total_variants > 0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_briefs_directory(self, temp_dir):
        """Test handling empty briefs directory"""
        empty_dir = temp_dir / "empty_briefs"
        empty_dir.mkdir()

        agent = CreativeAutomationAgent(briefs_dir=str(empty_dir))

        new_briefs = agent.scan_for_new_briefs()
        assert len(new_briefs) == 0

    def test_invalid_brief_json(self, temp_dir):
        """Test handling invalid JSON in brief file"""
        briefs_dir = temp_dir / "briefs"
        briefs_dir.mkdir()

        invalid_brief = briefs_dir / "invalid.json"
        invalid_brief.write_text("{invalid json")

        agent = CreativeAutomationAgent(briefs_dir=str(briefs_dir))

        # Should handle gracefully
        try:
            agent.scan_for_new_briefs()
        except json.JSONDecodeError:
            # Expected behavior - graceful error handling
            pass

    def test_missing_campaign_id(self, temp_dir):
        """Test brief without campaign_id field"""
        briefs_dir = temp_dir / "briefs"
        briefs_dir.mkdir()

        brief_file = briefs_dir / "no_campaign_id.json"
        with open(brief_file, "w") as f:
            json.dump(
                {
                    "products": [{"name": "Test Product"}],
                    "target_region": "US",
                },
                f,
            )

        agent = CreativeAutomationAgent(briefs_dir=str(briefs_dir))

        # Should use filename as fallback campaign_id
        campaign_id, brief_data = agent.analyze_campaign_brief(brief_file)
        assert campaign_id == "no_campaign_id"


class TestStateManagement:
    """Test agent state management"""

    def test_save_and_load_state(self, temp_dir, sample_brief_file):
        """Test saving and loading agent state"""
        agent1 = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        campaign_id, brief_data = agent1.analyze_campaign_brief(sample_brief_file)
        agent1.trigger_generation_task(sample_brief_file, campaign_id, brief_data)

        # Manually save state
        agent1._save_state()

        # Create new agent and verify state loaded
        agent2 = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        assert campaign_id in agent2.monitored_campaigns
        assert agent2.monitored_campaigns[campaign_id].campaign_id == campaign_id

    def test_state_file_creation(self, temp_dir, sample_brief_file):
        """Test that state file is created"""
        agent = CreativeAutomationAgent(briefs_dir=str(sample_brief_file.parent))

        campaign_id, brief_data = agent.analyze_campaign_brief(sample_brief_file)
        agent.trigger_generation_task(sample_brief_file, campaign_id, brief_data)
        agent._save_state()

        assert agent.state_file.exists()
        assert agent.state_file.name == ".agent_state.json"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
