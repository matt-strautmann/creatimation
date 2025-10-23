#!/usr/bin/env python3
"""
CrewAI Creative Automation Agent
A true AI-driven agent for intelligent creative campaign monitoring and automation.

This agent uses CrewAI to provide intelligent decision-making, monitoring, and automation
capabilities that go beyond simple rule-based systems.
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from crewai import Agent, Crew, Process, Task
from crewai.tools import BaseTool
from crewai_tools import FileReadTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class CampaignBrief(BaseModel):
    """Campaign brief data structure"""
    campaign_id: str
    products: List[str]
    target_regions: List[str] = ["US"]
    target_audience: str = ""
    campaign_message: str = ""
    brief_path: str = ""


class CampaignStatus(BaseModel):
    """Campaign generation status"""
    campaign_id: str
    status: str  # "new", "generating", "completed", "failed"
    variants_expected: int = 0
    variants_generated: int = 0
    last_check: datetime
    errors: List[str] = []


class CreatimationTool(BaseTool):
    """Tool for executing creatimation CLI commands"""

    name: str = "creatimation_cli"
    description: str = "Execute creatimation CLI commands for creative generation"

    def _run(self, command: str) -> str:
        """Execute a creatimation CLI command"""
        try:
            # Validate and fix common command issues
            if not command.startswith("creatimation"):
                if "generate" in command or "analytics" in command or "cache" in command:
                    command = f"creatimation {command}"
                else:
                    return f"Invalid command. Must start with 'creatimation' or be a valid subcommand. Got: {command}"

            # Add ./creatimation prefix if needed
            if command.startswith("creatimation ") and not command.startswith("./creatimation"):
                command = command.replace("creatimation ", "./creatimation ", 1)

            # Add virtual environment activation
            full_command = f"source .venv/bin/activate && {command}"

            print(f"🚀 Executing: {full_command}")

            result = subprocess.run(
                full_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600
            )

            if result.returncode == 0:
                return f"✅ Command executed successfully:\n{result.stdout}"
            else:
                return f"❌ Command failed with error:\n{result.stderr}\n\nStdout: {result.stdout}"

        except subprocess.TimeoutExpired:
            return "⏰ Command timed out after 10 minutes"
        except Exception as e:
            return f"💥 Error executing command: {str(e)}"


class FileSystemTool(BaseTool):
    """Tool for monitoring filesystem changes"""

    name: str = "filesystem_monitor"
    description: str = "Monitor campaign briefs and generated assets in the filesystem"

    def _run(self, action: str, path: str = "") -> str:
        """Monitor filesystem for changes"""
        try:
            # Handle various action aliases that agents might use
            if action in ["scan_briefs", "scan", "monitor"]:
                briefs_dir = Path("briefs")
                if not briefs_dir.exists():
                    return "Briefs directory does not exist"

                campaign_summaries = []
                for brief_file in briefs_dir.glob("*.json"):
                    try:
                        with open(brief_file) as f:
                            brief_data = json.load(f)

                            # Create monitoring-focused summary
                            summary = {
                                "campaign_id": brief_data.get("campaign_id", "unknown"),
                                "brief_file": brief_file.name,
                                "brand": self._extract_brand_name(brief_data),
                                "products": len(brief_data.get("products", [])),
                                "target_regions": brief_data.get("target_regions", ["US"]),
                                "campaign_message": brief_data.get("campaign_message", "")[:50] + "..." if len(brief_data.get("campaign_message", "")) > 50 else brief_data.get("campaign_message", ""),
                                "priority": self._assess_priority(brief_data),
                                "complexity": self._assess_complexity(brief_data),
                                "expected_variants": self._calculate_expected_variants(brief_data),
                                "file_modified": brief_file.stat().st_mtime
                            }
                            campaign_summaries.append(summary)
                    except Exception as e:
                        continue

                if not campaign_summaries:
                    return "No campaign briefs found in briefs/ directory"

                return json.dumps({
                    "total_campaigns": len(campaign_summaries),
                    "campaigns": campaign_summaries
                }, indent=2)

            elif action in ["count_variants", "count"]:
                if not path:
                    return "Path required for variant counting"

                output_dir = Path("output/campaigns") / path
                if not output_dir.exists():
                    return "0"

                count = 0
                for file_path in output_dir.rglob("*.jpg"):
                    count += 1
                for file_path in output_dir.rglob("*.png"):
                    count += 1

                return str(count)

            elif action in ["check_generation_status", "status", "check_status"]:
                if not path:
                    return "Path required for status checking"

                output_dir = Path("output/campaigns") / path
                if not output_dir.exists():
                    return "not_started"

                # Count variants in structured way
                variant_count = 0
                for region in ["us", "emea", "latam", "apac"]:
                    region_dir = output_dir / region
                    if region_dir.exists():
                        for product_dir in region_dir.iterdir():
                            if product_dir.is_dir():
                                for ratio_dir in product_dir.iterdir():
                                    if ratio_dir.is_dir():
                                        for variant_file in ratio_dir.glob("*.jpg"):
                                            variant_count += 1
                                        for variant_file in ratio_dir.glob("*.png"):
                                            variant_count += 1

                if variant_count == 0:
                    return "not_started"
                elif variant_count > 0:
                    return f"in_progress:{variant_count}"

            elif action in ["list_campaigns", "list"]:
                # List all campaigns in output directory
                output_dir = Path("output/campaigns")
                if not output_dir.exists():
                    return "No campaigns found"

                campaigns = []
                for campaign_dir in output_dir.iterdir():
                    if campaign_dir.is_dir():
                        campaigns.append(campaign_dir.name)

                return json.dumps(campaigns, indent=2)

            return f"Unknown action '{action}'. Available actions: scan, count_variants, check_generation_status, list_campaigns"

        except Exception as e:
            return f"Error: {str(e)}"

    def _assess_priority(self, brief_data: dict) -> str:
        """Assess campaign priority based on brief content"""
        priority_score = 0

        # Factor 1: Region scope (0-3 points)
        regions = brief_data.get("target_regions", ["US"])
        if len(regions) >= 4:
            priority_score += 3  # Global campaign
        elif len(regions) == 3:
            priority_score += 2  # Multi-region
        elif len(regions) == 2:
            priority_score += 1  # Bi-regional

        # Factor 2: Urgent indicators (0-3 points)
        message = brief_data.get("campaign_message", "").lower()
        campaign_name = brief_data.get("campaign_name", "").lower()
        all_text = f"{message} {campaign_name}".lower()

        high_urgency = ["urgent", "asap", "critical", "emergency", "rush", "immediate"]
        medium_urgency = ["launch", "deadline", "time-sensitive", "limited", "exclusive"]

        if any(keyword in all_text for keyword in high_urgency):
            priority_score += 3
        elif any(keyword in all_text for keyword in medium_urgency):
            priority_score += 2

        # Factor 3: Campaign scale (0-2 points)
        products = brief_data.get("products", [])
        expected_variants = self._calculate_expected_variants(brief_data)

        if len(products) >= 3 or expected_variants > 50:
            priority_score += 2  # Large campaign
        elif len(products) == 2 or expected_variants > 20:
            priority_score += 1  # Medium campaign

        # Factor 4: Timeline indicators (0-2 points)
        timeline_urgent = ["today", "tomorrow", "this week", "next week"]
        if any(keyword in all_text for keyword in timeline_urgent):
            priority_score += 2

        # Calculate final priority
        if priority_score >= 6:
            return "CRITICAL"
        elif priority_score >= 4:
            return "HIGH"
        elif priority_score >= 2:
            return "MEDIUM"
        else:
            return "NORMAL"

    def _assess_complexity(self, brief_data: dict) -> str:
        """Assess campaign complexity"""
        complexity_score = 0

        # Factor 1: Variant volume (0-3 points)
        expected_variants = self._calculate_expected_variants(brief_data)
        if expected_variants > 100:
            complexity_score += 3  # Enterprise scale
        elif expected_variants > 50:
            complexity_score += 2  # Large scale
        elif expected_variants > 20:
            complexity_score += 1  # Medium scale

        # Factor 2: Product diversity (0-2 points)
        products = brief_data.get("products", [])
        if len(products) >= 5:
            complexity_score += 2  # Many products
        elif len(products) >= 3:
            complexity_score += 1  # Multiple products

        # Factor 3: Regional complexity (0-2 points)
        regions = brief_data.get("target_regions", ["US"])
        if len(regions) >= 4:
            complexity_score += 2  # Global
        elif len(regions) >= 3:
            complexity_score += 1  # Multi-regional

        # Factor 4: Creative requirements complexity (0-2 points)
        creative_req = brief_data.get("creative_requirements", {})
        variant_types = creative_req.get("variant_types", ["base", "hero", "lifestyle"])
        aspect_ratios = creative_req.get("aspect_ratios", ["1x1", "9x16", "16x9"])

        if len(variant_types) > 4 or len(aspect_ratios) > 5:
            complexity_score += 2  # High creative complexity
        elif len(variant_types) > 3 or len(aspect_ratios) > 3:
            complexity_score += 1  # Medium creative complexity

        # Factor 5: Special requirements (0-1 point)
        if brief_data.get("regional_adaptations") or creative_req.get("variant_themes"):
            complexity_score += 1

        # Calculate final complexity
        if complexity_score >= 7:
            return "VERY HIGH"
        elif complexity_score >= 5:
            return "HIGH"
        elif complexity_score >= 3:
            return "MEDIUM"
        elif complexity_score >= 1:
            return "LOW"
        else:
            return "MINIMAL"

    def _calculate_expected_variants(self, brief_data: dict) -> int:
        """Calculate expected number of variants"""
        products = len(brief_data.get("products", []))
        regions = len(brief_data.get("target_regions", ["US"]))

        # Default: 3 aspect ratios × 3 variant types = 9 per product per region
        creative_req = brief_data.get("creative_requirements", {})
        ratios = len(creative_req.get("aspect_ratios", ["1x1", "9x16", "16x9"]))
        variant_types = len(creative_req.get("variant_types", ["base", "hero", "lifestyle"]))

        return products * regions * ratios * variant_types

    def _extract_brand_name(self, brief_data: dict) -> str:
        """Extract brand name from campaign brief"""
        # Try multiple sources for brand name
        brand = brief_data.get("brand", {})
        if isinstance(brand, dict):
            brand_name = brand.get("name", "")
        else:
            brand_name = str(brand)

        # Fallback: extract from campaign name or product names
        if not brand_name:
            campaign_name = brief_data.get("campaign_name", "")
            if campaign_name:
                # Extract first word as likely brand name
                brand_name = campaign_name.split()[0]

        # Last fallback: extract from first product name
        if not brand_name:
            products = brief_data.get("products", [])
            if products and len(products) > 0:
                first_product = products[0]
                if isinstance(first_product, dict):
                    product_name = first_product.get("name", "")
                else:
                    product_name = str(first_product)

                if product_name:
                    # Extract first word as likely brand name
                    brand_name = product_name.split()[0]

        return brand_name or "Unknown Brand"


class CreativeAutomationCrew:
    """CrewAI-based creative automation system"""

    def __init__(self):
        self.monitored_campaigns: Dict[str, CampaignStatus] = {}
        self.tools = [CreatimationTool(), FileSystemTool(), FileReadTool()]

        # Setup LLM - use OpenAI GPT-4 or fallback to GPT-3.5
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️  Warning: OPENAI_API_KEY not found in environment")
            print("   Set your OpenAI API key to enable full AI capabilities")
            print("   Using mock LLM for demonstration purposes")
            # Use a simple mock LLM for testing without API key
            from crewai.llm import LLM
            self.llm = LLM(model="openai/gpt-4o-mini", api_key="mock-key")
        else:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.1,
                api_key=api_key
            )

        # Define agents
        self.campaign_monitor = Agent(
            role="Campaign Monitor",
            goal="Monitor campaign briefs and detect new or modified campaigns requiring generation",
            backstory="""You are an intelligent campaign monitoring specialist with deep expertise
            in creative automation workflows. You excel at detecting new campaigns, analyzing brief
            changes, and determining generation priorities based on business impact.

            IMPORTANT: You work in the current directory. Campaign briefs are in the 'briefs/'
            directory and generated assets are in 'output/campaigns/'. Use these exact paths.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=True
        )

        self.generation_coordinator = Agent(
            role="Generation Coordinator",
            goal="Coordinate and trigger creative asset generation tasks intelligently",
            backstory="""You are a seasoned creative production coordinator who understands
            the complexities of multi-region, multi-format creative generation. You excel at
            orchestrating generation workflows, managing dependencies, and ensuring quality outputs.

            AVAILABLE CLI COMMANDS:
            - creatimation generate campaign briefs/CampaignName.json --dry-run (preview without API calls)
            - creatimation generate campaign briefs/CampaignName.json (real generation)
            - creatimation generate campaign briefs/CampaignName.json --simulate (fast demo mode)
            - creatimation analytics summary --recent (check results)
            - creatimation cache stats (check cache efficiency)

            ALWAYS use dry-run for testing and real campaign brief filenames from the detected campaigns.
            Use the actual brief_file names found in the filesystem scan.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=True
        )

        self.quality_analyst = Agent(
            role="Quality Analyst",
            goal="Analyze generated assets and campaign completion status with intelligent insights",
            backstory="""You are a meticulous quality assurance specialist with expertise in
            creative asset evaluation. You provide intelligent analysis of generation completeness,
            identify potential issues, and recommend optimization strategies.""",
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        self.alert_specialist = Agent(
            role="Alert Specialist",
            goal="Generate intelligent, context-aware alerts and recommendations for stakeholders",
            backstory="""You are a communications expert specializing in marketing operations.
            You excel at translating technical generation status into clear, actionable insights
            that marketing managers can understand and act upon immediately.""",
            tools=[],  # Alert specialist doesn't need tools, just analysis
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

    def create_monitoring_tasks(self) -> List[Task]:
        """Create tasks for campaign monitoring cycle"""

        monitor_task = Task(
            description="""
            Scan the 'briefs/' directory for campaign brief JSON files.
            Use filesystem_monitor tool with action='scan' to detect briefs.
            For each brief found:
            1. Analyze the campaign requirements (products, regions, target audience)
            2. Determine if this is a new campaign or an update to existing campaign
            3. Assess the priority and complexity of the generation task
            4. Provide recommendations for generation approach

            Return a structured analysis of all detected campaigns with priorities.
            """,
            agent=self.campaign_monitor,
            expected_output="JSON list of campaigns with analysis and priority rankings"
        )

        coordinate_task = Task(
            description="""
            Based on the campaign analysis, coordinate generation tasks:
            1. For new high-priority campaigns, trigger generation using:
               creatimation generate campaign briefs/[filename].json --dry-run
            2. For modified campaigns, determine what needs regeneration
            3. Execute actual creatimation CLI commands with real brief filenames
            4. Monitor generation progress and handle any immediate errors

            IMPORTANT: Use real brief filenames from the detected campaigns.
            Get actual filenames from the Campaign Monitor Agent's scan results.
            Always start with --dry-run for safety.
            """,
            agent=self.generation_coordinator,
            expected_output="Summary of triggered generation tasks with execution status"
        )

        quality_task = Task(
            description="""
            Analyze the current state of all monitored campaigns:
            1. Use filesystem_monitor with action='check_generation_status' and path='campaign_id'
            2. Count and validate generated variants in 'output/campaigns/[campaign_id]/'
            3. Identify campaigns with insufficient or missing assets
            4. Detect potential quality issues or generation failures
            5. Assess overall pipeline health and performance

            Check actual campaign directories like: output/campaigns/[campaign_id]/
            Provide intelligent analysis beyond simple rule-based checking.
            """,
            agent=self.quality_analyst,
            expected_output="Comprehensive quality analysis report with specific findings"
        )

        alert_task = Task(
            description="""
            Generate intelligent, human-readable alerts based on the quality analysis:
            1. Create priority-ranked alerts for stakeholder attention
            2. Provide clear, actionable recommendations for each issue
            3. Include business impact assessment and urgency levels
            4. Generate summary dashboard information for management

            Focus on business value and clear next steps rather than technical details.
            """,
            agent=self.alert_specialist,
            expected_output="Professional alert report with prioritized recommendations"
        )

        return [monitor_task, coordinate_task, quality_task, alert_task]

    def run_monitoring_cycle(self) -> Dict:
        """Execute one complete monitoring cycle using CrewAI"""

        tasks = self.create_monitoring_tasks()

        crew = Crew(
            agents=[
                self.campaign_monitor,
                self.generation_coordinator,
                self.quality_analyst,
                self.alert_specialist
            ],
            tasks=tasks,
            process=Process.sequential,
            verbose=True
        )

        print("\n🤖 Starting CrewAI Creative Automation Cycle...")
        print("=" * 60)

        try:
            result = crew.kickoff()

            print("\n✅ CrewAI Cycle Complete!")
            print("=" * 60)
            print(result)

            return {"status": "success", "result": result}

        except Exception as e:
            print(f"\n❌ CrewAI Cycle Failed: {str(e)}")
            return {"status": "error", "error": str(e)}

    def start_continuous_monitoring(self, interval: int = 60):
        """Start continuous monitoring with specified interval"""

        print(f"\n🚀 Starting Continuous Creative Automation Agent")
        print(f"   Monitoring interval: {interval} seconds")
        print(f"   Press Ctrl+C to stop\n")

        try:
            while True:
                self.run_monitoring_cycle()
                print(f"\n⏸️  Waiting {interval} seconds until next cycle...")
                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n🛑 Creative Automation Agent stopped by user")
        except Exception as e:
            print(f"\n\n💥 Critical error in monitoring loop: {str(e)}")


def main():
    """CLI entry point for CrewAI Creative Agent"""
    import argparse

    parser = argparse.ArgumentParser(
        description="CrewAI Creative Automation Agent - Intelligent Campaign Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single monitoring cycle
  python src/crewai_creative_agent.py --once

  # Start continuous monitoring (60 second interval)
  python src/crewai_creative_agent.py --watch

  # Custom monitoring interval
  python src/crewai_creative_agent.py --watch --interval 30
        """
    )

    parser.add_argument("--once", action="store_true", help="Run single monitoring cycle")
    parser.add_argument("--watch", action="store_true", help="Start continuous monitoring")
    parser.add_argument("--interval", type=int, default=60, help="Monitoring interval in seconds")

    args = parser.parse_args()

    agent = CreativeAutomationCrew()

    if args.once:
        agent.run_monitoring_cycle()
    elif args.watch:
        agent.start_continuous_monitoring(args.interval)
    else:
        # Default to single run
        agent.run_monitoring_cycle()


if __name__ == "__main__":
    main()