#!/usr/bin/env python3
"""
Creative Automation Agent - MCP-Based Intelligent Monitoring System

This agent implements the requirements from PRD Task 2:
- Monitor incoming campaign briefs
- Monitor configuration files (.creatimation.yml, global_config/, brand-guides/)
- Trigger automated generation tasks
- Track count and diversity of creative variants
- Flag missing or insufficient assets (< 9 variants per product: 3 ratios × 3 variant types)
- Alert and logging mechanism
- Model Context Protocol for LLM-generated human-readable alerts

Model Context Protocol (MCP) Schema:
===============================

The agent implements a comprehensive MCP schema that provides structured context
to LLMs for generating human-readable alerts. The schema includes:

1. Campaign Context:
   - campaign_id: Unique identifier for the campaign
   - campaign_name: Human-readable campaign name
   - timestamp: ISO timestamp of the alert
   - target_region: Geographic target (US, EMEA, etc.)
   - target_audience: Defined audience segment

2. Product Processing Status:
   - total_products: Number of products in campaign
   - products_processed: Number of products with generated variants
   - products_pending: List of products awaiting processing
   - products_failed: List of products that failed generation

3. Variant Generation Metrics:
   - total_variants_expected: Expected total variants (products × 3 ratios × 3 types)
   - total_variants_generated: Actual variants generated
   - variants_by_ratio: Count breakdown by aspect ratio (1x1, 9x16, 16x9)
   - variants_per_product: Count breakdown by product name

4. Asset Quality Tracking:
   - missing_assets: Products with zero generated variants
   - insufficient_variants: Products with < 9 variants (below 3×3 target)

5. Performance Metrics:
   - cache_hit_rate: Percentage of assets reused from cache
   - processing_time: Total generation time in seconds
   - error_count: Number of errors encountered

6. Alert Metadata:
   - alert_type: Type of alert (insufficient_variants, generation_complete, configuration_change)
   - severity: Alert level (info, warning, error, critical)
   - issues: List of specific problems identified
   - recommendations: List of suggested actions

The MCP context is serializable to JSON and provides a to_llm_prompt() method
that formats the data for LLM consumption, enabling intelligent, context-aware
alert generation that marketing managers can understand and act upon.

Configuration Monitoring:
========================

The agent monitors configuration files for changes:
- .creatimation.yml (workspace configuration)
- global_config/*.yml (global settings)
- brand-guides/*.yml (brand guideline files)

Changes trigger configuration_change alerts through the MCP system.
"""

import hashlib
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class VariantStatus(Enum):
    """Status of creative variant generation"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INSUFFICIENT = "insufficient"  # < 3 variants


@dataclass
class MCPContext:
    """
    Model Context Protocol Data Structure

    This defines the information the LLM sees to draft human-readable alerts.
    Includes all relevant campaign context, metrics, and issues.
    """

    campaign_id: str
    campaign_name: str
    timestamp: str
    target_region: str
    target_audience: str

    # Products and variants tracking
    total_products: int
    products_processed: int
    products_pending: list[str]
    products_failed: list[str]

    # Variant diversity metrics
    total_variants_expected: int
    total_variants_generated: int
    variants_by_ratio: dict[str, int]
    variants_per_product: dict[str, int]

    # Asset tracking
    missing_assets: list[str]
    insufficient_variants: list[str]  # Products with < 3 variants

    # Quality metrics
    cache_hit_rate: float
    processing_time: float
    error_count: int

    # Alert details
    alert_type: str
    severity: str
    issues: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    def to_llm_prompt(self) -> str:
        """
        Convert MCP context to LLM prompt for generating human-readable alerts.

        Returns:
            str: Formatted prompt for LLM to generate alert message
        """
        prompt = f"""You are a creative automation assistant. Generate a concise, human-readable alert based on the following campaign monitoring data:

CAMPAIGN DETAILS:
- Campaign ID: {self.campaign_id}
- Campaign Name: {self.campaign_name}
- Target Region: {self.target_region}
- Target Audience: {self.target_audience}
- Timestamp: {self.timestamp}

PROCESSING STATUS:
- Products: {self.products_processed}/{self.total_products} processed
- Pending: {", ".join(self.products_pending) if self.products_pending else "None"}
- Failed: {", ".join(self.products_failed) if self.products_failed else "None"}

VARIANT GENERATION:
- Total Variants: {self.total_variants_generated}/{self.total_variants_expected}
- By Aspect Ratio: {json.dumps(self.variants_by_ratio, indent=2)}
- Per Product: {json.dumps(self.variants_per_product, indent=2)}

ASSET TRACKING:
- Missing Assets: {", ".join(self.missing_assets) if self.missing_assets else "None"}
- Insufficient Variants (< 3): {", ".join(self.insufficient_variants) if self.insufficient_variants else "None"}

PERFORMANCE METRICS:
- Cache Hit Rate: {self.cache_hit_rate:.1f}%
- Processing Time: {self.processing_time:.1f}s
- Errors: {self.error_count}

ALERT INFORMATION:
- Type: {self.alert_type}
- Severity: {self.severity}
- Issues: {", ".join(self.issues)}
- Recommendations: {", ".join(self.recommendations)}

Generate a clear, actionable alert message (2-3 sentences) that a marketing manager would understand. Focus on business impact and next steps.
"""
        return prompt


@dataclass
class CampaignMonitoringState:
    """State tracking for a single campaign"""

    campaign_id: str
    brief_path: str
    brief_hash: str
    start_time: float
    last_updated: float
    status: VariantStatus
    products: list[str]
    variants_generated: dict[str, dict[str, int]]  # {product: {ratio: count}}
    total_variants: int
    errors: list[str]
    alerts: list[dict]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "campaign_id": self.campaign_id,
            "brief_path": self.brief_path,
            "brief_hash": self.brief_hash,
            "start_time": self.start_time,
            "last_updated": self.last_updated,
            "status": self.status.value,
            "products": self.products,
            "variants_generated": self.variants_generated,
            "total_variants": self.total_variants,
            "errors": self.errors,
            "alerts": self.alerts,
        }


class CreativeAutomationAgent:
    """
    Intelligent agent for monitoring and orchestrating creative automation pipeline.

    Implements PRD Task 2 requirements:
    1. Monitor incoming campaign briefs
    2. Trigger automated generation tasks
    3. Track count and diversity of creative variants
    4. Flag missing or insufficient assets
    5. Alert and logging mechanism using Model Context Protocol
    """

    def __init__(self, briefs_dir: str = "briefs", watch_interval: int = 5):
        """
        Initialize the creative automation agent.

        Args:
            briefs_dir: Directory to monitor for campaign briefs
            watch_interval: Seconds between directory scans
        """
        self.briefs_dir = Path(briefs_dir)
        self.watch_interval = watch_interval
        self.monitored_campaigns: dict[str, CampaignMonitoringState] = {}
        self.state_file = Path(".agent_state.json")

        # Configuration monitoring paths
        self.workspace_config = Path(".creatimation.yml")
        self.global_config_dir = Path("global_config")
        self.brand_guides_dir = Path("brand-guides")

        # Track config file hashes for change detection
        self.config_hashes: dict[str, str] = {}

        # Load previous state if exists
        self._load_state()

        logger.info("Creative Automation Agent initialized")
        logger.info(f"Monitoring directory: {self.briefs_dir}")
        logger.info(
            f"Monitoring config files: {self.workspace_config}, {self.global_config_dir}, {self.brand_guides_dir}"
        )
        logger.info(f"Watch interval: {self.watch_interval}s")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file content for change detection"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:8]
        except (FileNotFoundError, PermissionError):
            return ""

    def _calculate_brief_hash(self, brief_path: Path) -> str:
        """Calculate hash of brief file content for change detection"""
        return self._calculate_file_hash(brief_path)

    def _load_state(self):
        """Load previous agent state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state_data = json.load(f)
                    for camp_id, camp_state in state_data.items():
                        # Reconstruct CampaignMonitoringState objects
                        camp_state["status"] = VariantStatus(camp_state["status"])
                        self.monitored_campaigns[camp_id] = CampaignMonitoringState(**camp_state)
                logger.info(f"Loaded state for {len(self.monitored_campaigns)} campaigns")
            except Exception as e:
                logger.error(f"Failed to load agent state: {e}")

    def _save_state(self):
        """Save current agent state to disk"""
        try:
            state_data = {
                camp_id: camp_state.to_dict()
                for camp_id, camp_state in self.monitored_campaigns.items()
            }
            with open(self.state_file, "w") as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save agent state: {e}")

    def scan_for_new_briefs(self) -> list[Path]:
        """
        Scan briefs directory for new or modified campaign briefs.

        Returns:
            List of brief file paths that are new or have changed
        """
        if not self.briefs_dir.exists():
            logger.warning(f"Briefs directory does not exist: {self.briefs_dir}")
            return []

        new_or_modified_briefs = []

        for brief_file in self.briefs_dir.glob("*.json"):
            brief_hash = self._calculate_brief_hash(brief_file)

            # Load brief to get campaign_id
            with open(brief_file) as f:
                brief_data = json.load(f)
                campaign_id = brief_data.get("campaign_id", brief_file.stem)

            # Check if this is new or modified
            if campaign_id not in self.monitored_campaigns:
                logger.info(f"New campaign brief detected: {brief_file.name}")
                new_or_modified_briefs.append(brief_file)
            elif self.monitored_campaigns[campaign_id].brief_hash != brief_hash:
                logger.info(f"Modified campaign brief detected: {brief_file.name}")
                new_or_modified_briefs.append(brief_file)

        return new_or_modified_briefs

    def scan_for_config_changes(self) -> list[str]:
        """
        Scan for configuration file changes.

        Returns:
            List of changed configuration files
        """
        changed_configs = []

        # Monitor workspace config
        if self.workspace_config.exists():
            config_hash = self._calculate_file_hash(self.workspace_config)
            stored_hash = self.config_hashes.get(str(self.workspace_config), "")
            if config_hash != stored_hash:
                if stored_hash:  # Don't alert on first scan
                    logger.info(f"Workspace config changed: {self.workspace_config}")
                    changed_configs.append(str(self.workspace_config))
                self.config_hashes[str(self.workspace_config)] = config_hash

        # Monitor global config directory
        if self.global_config_dir.exists():
            for config_file in self.global_config_dir.glob("*.yml"):
                config_hash = self._calculate_file_hash(config_file)
                stored_hash = self.config_hashes.get(str(config_file), "")
                if config_hash != stored_hash:
                    if stored_hash:  # Don't alert on first scan
                        logger.info(f"Global config changed: {config_file}")
                        changed_configs.append(str(config_file))
                    self.config_hashes[str(config_file)] = config_hash

        # Monitor brand guides directory
        if self.brand_guides_dir.exists():
            for brand_file in self.brand_guides_dir.glob("*.yml"):
                brand_hash = self._calculate_file_hash(brand_file)
                stored_hash = self.config_hashes.get(str(brand_file), "")
                if brand_hash != stored_hash:
                    if stored_hash:  # Don't alert on first scan
                        logger.info(f"Brand guide changed: {brand_file}")
                        changed_configs.append(str(brand_file))
                    self.config_hashes[str(brand_file)] = brand_hash

        return changed_configs

    def generate_config_change_alert(self, changed_configs: list[str]):
        """
        Generate MCP-compliant alert for configuration changes.

        Args:
            changed_configs: List of changed configuration file paths
        """
        if not changed_configs:
            return

        # Load analytics for enhanced context
        analytics_data = self._load_analytics_data()
        performance_metrics = self._calculate_performance_metrics(analytics_data)

        # Create a configuration change alert using MCP structure
        mcp_context = MCPContext(
            campaign_id="config_monitor",
            campaign_name="Configuration Monitoring",
            timestamp=datetime.now().isoformat(),
            target_region="GLOBAL",
            target_audience="Development Team",
            total_products=0,
            products_processed=0,
            products_pending=[],
            products_failed=[],
            total_variants_expected=0,
            total_variants_generated=0,
            variants_by_ratio={},
            variants_per_product={},
            missing_assets=[],
            insufficient_variants=[],
            cache_hit_rate=performance_metrics.get("cache_efficiency", 0.0),
            processing_time=performance_metrics.get("avg_command_duration", 0.0),
            error_count=0,
            alert_type="configuration_change",
            severity=AlertSeverity.INFO.value,
            issues=[f"Configuration file modified: {config}" for config in changed_configs],
            recommendations=[
                "Review configuration changes for impact on campaigns",
                "Consider re-running generation if settings affect creative output",
                "Validate configuration syntax and values",
                f"Current system performance: {performance_metrics.get('command_success_rate', 0):.1f}% success rate",
            ],
        )

        self.log_alert(mcp_context)

    def analyze_campaign_brief(self, brief_path: Path) -> tuple[str, dict]:
        """
        Analyze a campaign brief and extract key information.

        Args:
            brief_path: Path to campaign brief JSON file

        Returns:
            Tuple of (campaign_id, brief_data)
        """
        with open(brief_path) as f:
            brief_data = json.load(f)

        campaign_id = brief_data.get("campaign_id", brief_path.stem)
        products = brief_data.get("products", [])

        # Extract product names
        product_names = []
        for p in products:
            if isinstance(p, str):
                product_names.append(p)
            elif isinstance(p, dict):
                product_names.append(p.get("name", str(p)))

        logger.info(f"Analyzed campaign '{campaign_id}' with {len(product_names)} products")

        return campaign_id, brief_data

    def trigger_generation_task(self, brief_path: Path, campaign_id: str, brief_data: dict):
        """
        Trigger automated creative generation task.

        Args:
            brief_path: Path to campaign brief
            campaign_id: Campaign identifier
            brief_data: Parsed brief data
        """
        logger.info(f"Triggering generation task for campaign: {campaign_id}")

        # Initialize monitoring state
        products = brief_data.get("products", [])
        product_names = []
        for p in products:
            if isinstance(p, str):
                product_names.append(p)
            elif isinstance(p, dict):
                product_names.append(p.get("name", str(p)))

        brief_hash = self._calculate_brief_hash(brief_path)

        campaign_state = CampaignMonitoringState(
            campaign_id=campaign_id,
            brief_path=str(brief_path),
            brief_hash=brief_hash,
            start_time=time.time(),
            last_updated=time.time(),
            status=VariantStatus.IN_PROGRESS,
            products=product_names,
            variants_generated={},
            total_variants=0,
            errors=[],
            alerts=[],
        )

        self.monitored_campaigns[campaign_id] = campaign_state
        self._save_state()

        # Log trigger event
        logger.info(f"Generation task triggered for {len(product_names)} products")
        logger.info(
            f"Expected variants: {len(product_names) * 3 * 3} (3 aspect ratios × 3 variant types per product)"
        )

    def track_variant_generation(self, campaign_id: str, output_dir: Path = Path("output")):
        """
        Track creative variant generation progress by scanning output directory.

        Args:
            campaign_id: Campaign identifier
            output_dir: Root output directory containing generated creatives
        """
        if campaign_id not in self.monitored_campaigns:
            logger.warning(f"Campaign {campaign_id} not being monitored")
            return

        campaign_state = self.monitored_campaigns[campaign_id]

        # Scan output directory for generated variants
        variants_by_product = {}
        total_variants = 0

        for product_name in campaign_state.products:
            # Create product slug (simplified version)
            product_slug = product_name.lower().replace(" ", "-")
            product_dir = output_dir / product_slug

            if not product_dir.exists():
                variants_by_product[product_name] = {"1x1": 0, "9x16": 0, "16x9": 0}
                continue

            # Count variants by aspect ratio
            # Try both possible region names (us, US, or from brief metadata)
            ratio_counts = {}
            for ratio in ["1x1", "9x16", "16x9"]:
                # Check common path patterns for region
                for region in ["us", "US", "default"]:
                    ratio_dir = product_dir / "hero-product" / region / ratio
                    if ratio_dir.exists():
                        variant_files = list(ratio_dir.glob("*.jpg")) + list(
                            ratio_dir.glob("*.png")
                        )
                        ratio_counts[ratio] = len(variant_files)
                        total_variants += len(variant_files)
                        break
                else:
                    ratio_counts[ratio] = 0

            variants_by_product[product_name] = ratio_counts

        # Update campaign state
        campaign_state.variants_generated = variants_by_product
        campaign_state.total_variants = total_variants
        campaign_state.last_updated = time.time()

        self._save_state()

        logger.debug(f"Tracked {total_variants} total variants for campaign {campaign_id}")

    def check_variant_sufficiency(self, campaign_id: str) -> list[str]:
        """
        Check if campaign has sufficient variants (at least 3 per product).

        Args:
            campaign_id: Campaign identifier

        Returns:
            List of products with insufficient variants
        """
        if campaign_id not in self.monitored_campaigns:
            return []

        campaign_state = self.monitored_campaigns[campaign_id]
        insufficient_products = []

        # Check all products from the campaign, not just those in variants_generated
        for product_name in campaign_state.products:
            ratio_counts = campaign_state.variants_generated.get(product_name, {})
            total_for_product = sum(ratio_counts.values())
            # Each product should have 9 variants (3 aspect ratios × 3 variant types)
            if total_for_product < 9:
                insufficient_products.append(product_name)
                logger.warning(
                    f"Product '{product_name}' has insufficient variants: {total_for_product}/9"
                )

        return insufficient_products

    def generate_mcp_alert(
        self, campaign_id: str, alert_type: str, severity: AlertSeverity
    ) -> MCPContext:
        """
        Generate Model Context Protocol alert with full context for LLM.

        Args:
            campaign_id: Campaign identifier
            alert_type: Type of alert (e.g., "insufficient_variants", "generation_complete")
            severity: Alert severity level

        Returns:
            MCPContext object with full campaign context
        """
        if campaign_id not in self.monitored_campaigns:
            raise ValueError(f"Campaign {campaign_id} not found")

        campaign_state = self.monitored_campaigns[campaign_id]

        # Calculate metrics
        total_products = len(campaign_state.products)
        products_processed = len(
            [p for p in campaign_state.products if p in campaign_state.variants_generated]
        )
        products_pending = [
            p for p in campaign_state.products if p not in campaign_state.variants_generated
        ]

        # Check for issues
        insufficient_variants = self.check_variant_sufficiency(campaign_id)
        missing_assets = [
            p
            for p, counts in campaign_state.variants_generated.items()
            if sum(counts.values()) == 0
        ]

        # Build variant statistics
        variants_by_ratio = {"1x1": 0, "9x16": 0, "16x9": 0}
        variants_per_product = {}
        for product, ratios in campaign_state.variants_generated.items():
            variants_per_product[product] = sum(ratios.values())
            for ratio, count in ratios.items():
                variants_by_ratio[ratio] += count

        # Load analytics data for enhanced metrics
        analytics_data = self._load_analytics_data()
        performance_metrics = self._calculate_performance_metrics(analytics_data)

        # Determine issues and recommendations
        issues = []
        recommendations = []

        if insufficient_variants:
            issues.append(
                f"{len(insufficient_variants)} products have < 9 variants (3 ratios × 3 variant types)"
            )
            recommendations.append(
                "Re-run generation to complete all variant types (base, color_shift, text_style)"
            )

        if missing_assets:
            issues.append(f"{len(missing_assets)} products have no generated assets")
            recommendations.append("Check generation logs for errors")

        if campaign_state.errors:
            issues.append(f"{len(campaign_state.errors)} errors during generation")
            recommendations.append("Review error logs and retry failed products")

        # Create MCP context
        mcp_context = MCPContext(
            campaign_id=campaign_id,
            campaign_name=campaign_state.campaign_id.replace("_", " ").title(),
            timestamp=datetime.now().isoformat(),
            target_region="US",  # TODO: Extract from brief
            target_audience="N/A",  # TODO: Extract from brief
            total_products=total_products,
            products_processed=products_processed,
            products_pending=products_pending,
            products_failed=[],  # TODO: Track failed products
            total_variants_expected=total_products * 3 * 3,  # 3 aspect ratios × 3 variant types
            total_variants_generated=campaign_state.total_variants,
            variants_by_ratio=variants_by_ratio,
            variants_per_product=variants_per_product,
            missing_assets=missing_assets,
            insufficient_variants=insufficient_variants,
            cache_hit_rate=performance_metrics.get("cache_efficiency", 0.0),
            processing_time=performance_metrics.get(
                "avg_generation_time", campaign_state.last_updated - campaign_state.start_time
            ),
            error_count=len(campaign_state.errors),
            alert_type=alert_type,
            severity=severity.value,
            issues=issues,
            recommendations=recommendations,
        )

        return mcp_context

    def log_alert(self, mcp_context: MCPContext):
        """
        Log alert and save to campaign monitoring state.

        Args:
            mcp_context: MCP context with alert information
        """
        campaign_id = mcp_context.campaign_id

        if campaign_id in self.monitored_campaigns:
            campaign_state = self.monitored_campaigns[campaign_id]
            alert_record = {
                "timestamp": mcp_context.timestamp,
                "type": mcp_context.alert_type,
                "severity": mcp_context.severity,
                "issues": mcp_context.issues,
                "recommendations": mcp_context.recommendations,
            }
            campaign_state.alerts.append(alert_record)
            self._save_state()

        # Log to console
        severity_emoji = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.ERROR: "❌",
            AlertSeverity.CRITICAL: "🚨",
        }

        emoji = severity_emoji.get(AlertSeverity(mcp_context.severity), "📢")
        logger.info(f"\n{emoji} ALERT: {mcp_context.alert_type.upper()}")
        logger.info(f"Campaign: {mcp_context.campaign_name}")
        logger.info(
            f"Variants: {mcp_context.total_variants_generated}/{mcp_context.total_variants_expected}"
        )

        if mcp_context.issues:
            logger.warning(f"Issues: {', '.join(mcp_context.issues)}")

        if mcp_context.recommendations:
            logger.info(f"Recommendations: {', '.join(mcp_context.recommendations)}")

    def run_monitoring_cycle(self):
        """
        Execute one complete monitoring cycle:
        1. Scan for configuration changes
        2. Scan for new briefs
        3. Trigger generation tasks
        4. Track variant generation
        5. Check for issues and generate alerts
        """
        logger.info("Starting monitoring cycle...")

        # Step 1: Scan for configuration changes
        changed_configs = self.scan_for_config_changes()
        if changed_configs:
            self.generate_config_change_alert(changed_configs)

        # Step 2: Scan for new or modified briefs
        new_briefs = self.scan_for_new_briefs()

        # Step 3: Analyze and trigger generation for new briefs
        for brief_path in new_briefs:
            campaign_id, brief_data = self.analyze_campaign_brief(brief_path)
            self.trigger_generation_task(brief_path, campaign_id, brief_data)

        # Step 4: Track variant generation for all monitored campaigns
        for campaign_id in list(self.monitored_campaigns.keys()):
            self.track_variant_generation(campaign_id)

            # Step 5: Check for issues and generate alerts
            campaign_state = self.monitored_campaigns[campaign_id]

            # Only check if generation is in progress or just completed
            if campaign_state.status == VariantStatus.IN_PROGRESS:
                # Check for insufficient variants
                insufficient = self.check_variant_sufficiency(campaign_id)

                if insufficient:
                    mcp_context = self.generate_mcp_alert(
                        campaign_id,
                        alert_type="insufficient_variants",
                        severity=AlertSeverity.WARNING,
                    )
                    self.log_alert(mcp_context)

                # Check if generation is complete (all products have variants)
                all_products_have_variants = all(
                    product in campaign_state.variants_generated
                    and sum(campaign_state.variants_generated[product].values()) > 0
                    for product in campaign_state.products
                )

                if all_products_have_variants:
                    campaign_state.status = VariantStatus.COMPLETED
                    mcp_context = self.generate_mcp_alert(
                        campaign_id, alert_type="generation_complete", severity=AlertSeverity.INFO
                    )
                    self.log_alert(mcp_context)
                    self._save_state()

        logger.info("Monitoring cycle complete")

    def _load_analytics_data(self) -> dict[str, Any]:
        """
        Load analytics data for enhanced MCP context.

        Returns:
            Dictionary with analytics data or empty dict if not available
        """
        analytics_file = Path.home() / ".creatimation" / "analytics.json"
        if not analytics_file.exists():
            return {}

        try:
            with open(analytics_file) as f:
                return json.load(f)
        except Exception as e:
            logger.debug(f"Failed to load analytics data: {e}")
            return {}

    def _calculate_performance_metrics(self, analytics_data: dict[str, Any]) -> dict[str, float]:
        """
        Calculate performance metrics from analytics data.

        Args:
            analytics_data: Raw analytics data

        Returns:
            Dictionary with calculated performance metrics
        """
        metrics = {
            "avg_command_duration": 0.0,
            "command_success_rate": 0.0,
            "total_campaigns_generated": 0,
            "avg_generation_time": 0.0,
            "cache_efficiency": 0.0,
        }

        # Command performance
        commands = analytics_data.get("commands", {})
        if commands:
            total_duration = sum(cmd["total_duration"] for cmd in commands.values())
            total_count = sum(cmd["count"] for cmd in commands.values())
            total_success = sum(cmd["success_count"] for cmd in commands.values())

            if total_count > 0:
                metrics["avg_command_duration"] = total_duration / total_count
                metrics["command_success_rate"] = (total_success / total_count) * 100

        # Generation performance
        generation_stats = analytics_data.get("generation_stats", {})
        if generation_stats:
            metrics["total_campaigns_generated"] = len(generation_stats)

            successful_generations = [
                stats
                for stats in generation_stats.values()
                if stats.get("success", False) and not stats.get("dry_run", False)
            ]

            if successful_generations:
                total_gen_time = sum(
                    gen.get("processing_time", 0) for gen in successful_generations
                )
                metrics["avg_generation_time"] = total_gen_time / len(successful_generations)

                # Calculate cache efficiency
                total_hits = sum(gen.get("cache_hits", 0) for gen in successful_generations)
                total_misses = sum(gen.get("cache_misses", 0) for gen in successful_generations)
                total_cache_ops = total_hits + total_misses

                if total_cache_ops > 0:
                    metrics["cache_efficiency"] = (total_hits / total_cache_ops) * 100

        return metrics

    def start_watch_mode(self):
        """
        Start continuous monitoring in watch mode.
        Runs monitoring cycles at regular intervals.
        """
        logger.info("Starting agent in watch mode...")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                self.run_monitoring_cycle()
                time.sleep(self.watch_interval)
        except KeyboardInterrupt:
            logger.info("\nStopping agent...")
            self._save_state()
            logger.info("Agent stopped")


def main():
    """CLI entry point for the creative automation agent"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Creative Automation Agent - MCP-Based Monitoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start agent in watch mode (continuous monitoring)
  python src/creative_automation_agent.py --watch

  # Run single monitoring cycle
  python src/creative_automation_agent.py --once

  # Monitor specific directory
  python src/creative_automation_agent.py --briefs-dir custom_briefs --watch
        """,
    )

    parser.add_argument(
        "--watch", action="store_true", help="Run in watch mode (continuous monitoring)"
    )
    parser.add_argument("--once", action="store_true", help="Run single monitoring cycle and exit")
    parser.add_argument(
        "--briefs-dir",
        default="briefs",
        help="Directory to monitor for campaign briefs (default: briefs)",
    )
    parser.add_argument(
        "--interval", type=int, default=5, help="Watch interval in seconds (default: 5)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize agent
    agent = CreativeAutomationAgent(briefs_dir=args.briefs_dir, watch_interval=args.interval)

    if args.watch:
        agent.start_watch_mode()
    elif args.once:
        agent.run_monitoring_cycle()
    else:
        # Default to watch mode
        agent.start_watch_mode()


if __name__ == "__main__":
    main()
