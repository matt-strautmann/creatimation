#!/usr/bin/env python3
"""Quick debug script to test agent behavior"""

import json
import tempfile
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from creative_automation_agent import CreativeAutomationAgent

def main():
    # Create temp structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create briefs directory and sample brief
        briefs_dir = temp_path / "briefs"
        briefs_dir.mkdir()

        brief_data = {
            "campaign_id": "test_campaign_2025",
            "products": ["Test Product A", "Test Product B"],
            "target_region": "US",
            "target_audience": "Test audience",
            "campaign_message": "Test Message",
        }

        brief_file = briefs_dir / "test_campaign.json"
        with open(brief_file, "w") as f:
            json.dump(brief_data, f, indent=2)

        print(f"Created brief file: {brief_file}")
        print(f"Brief file exists: {brief_file.exists()}")
        print(f"Briefs dir contents: {list(briefs_dir.glob('*.json'))}")

        # Create agent
        agent = CreativeAutomationAgent(briefs_dir=str(briefs_dir))
        print(f"Agent briefs_dir: {agent.briefs_dir}")
        print(f"Agent briefs_dir exists: {agent.briefs_dir.exists()}")

        # Test scan
        new_briefs = agent.scan_for_new_briefs()
        print(f"New briefs found: {new_briefs}")
        print(f"Monitored campaigns: {agent.monitored_campaigns}")

if __name__ == "__main__":
    main()