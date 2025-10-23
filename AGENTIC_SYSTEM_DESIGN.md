# Agentic System Design

**PRD Task 2**: Design an AI-Driven Agent for Creative Automation Pipeline Monitoring

---

## Executive Summary

This document presents the design for an intelligent monitoring agent that addresses PRD Task 2 requirements:

- **Monitor incoming campaign briefs** and detect new/modified files
- **Trigger automated generation tasks** when campaigns are detected
- **Track count and diversity of creative variants** across products and aspect ratios
- **Flag missing or insufficient assets** (fewer than 3 variants per product)
- **Alert and logging mechanism** with human-readable notifications
- **Model Context Protocol (MCP)** to provide LLM-ready context for intelligent alerts

The agent operates as an autonomous system that continuously monitors the creative automation pipeline, providing real-time insights and actionable alerts for marketing teams.

## Overview

The Creative Automation Agent is an intelligent monitoring system that provides real-time visibility into campaign generation workflows. It automatically tracks variant generation progress, identifies issues, and provides actionable alerts for marketing teams.

### What the Agent Monitors

- **Campaign Briefs**: Scans `briefs/` directory for new or modified JSON files using SHA-256 hash detection
- **Variant Generation**: Tracks creative output across regions and aspect ratios in real-time
- **Generation Status**: Monitors campaign progress from detection → in-progress → completed
- **Asset Completeness**: Validates sufficient variants per product (9 variants: 3 ratios × 3 types)
- **Configuration Changes**: Monitors `.creatimation.yml`, brand guides, global config files
- **Multi-Region Support**: Tracks variants across US, EMEA, LATAM, APAC regions

### Real-World Operation

The agent operates on actual campaign generation workflows:

**Example Output:**
```
⚠️ ALERT: INSUFFICIENT_VARIANTS
Campaign: Cleanwave Spring 2025
Variants: 0/36
Issues: 2 products have < 9 variants (3 ratios × 3 variant types)
Recommendations: Re-run generation to complete all variant types (base, hero, lifestyle)

ℹ️ ALERT: GENERATION_COMPLETE
Campaign: Cleanwave Spring Demo 2025
Variants: 36/36
Status: ✅ Success - All variants generated across 2 regions
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Creative Automation Agent                   │
│                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌───────────────┐ │
│  │ Brief Monitor  │  │ Task Trigger   │  │ Variant       │ │
│  │                │  │                │  │ Tracker       │ │
│  │ • Scan briefs/ │→ │ • Launch       │→ │ • Count       │ │
│  │ • Detect new   │  │   pipeline     │  │   variants    │ │
│  │ • Hash check   │  │ • Track state  │  │ • Check       │ │
│  └────────────────┘  └────────────────┘  │   diversity   │ │
│                                           └───────┬───────┘ │
│                                                   ↓         │
│  ┌─────────────────────────────────────────────────────┐   │
│  │            Model Context Protocol (MCP)              │   │
│  │                                                       │   │
│  │  • Campaign metadata                                 │   │
│  │  • Variant statistics                                │   │
│  │  • Asset tracking                                    │   │
│  │  • Quality metrics                                   │   │
│  │  • Issue detection                                   │   │
│  └──────────────────────┬────────────────────────────────┘   │
│                         ↓                                     │
│  ┌────────────────────────────────────────────────┐          │
│  │  Alert Generation & Logging                     │          │
│  │                                                  │          │
│  │  • Severity classification                      │          │
│  │  • Human-readable messages                      │          │
│  │  • Actionable recommendations                   │          │
│  │  • Persistent logging                           │          │
│  └──────────────────────────────────────────────────┘          │
└───────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Brief Monitor

**Purpose**: Continuously monitor the `briefs/` directory for new or modified campaign briefs.

**Implementation**:
```python
def scan_for_new_briefs(self) -> List[Path]:
    """
    Scan briefs directory for new or modified campaign briefs.
    Uses SHA-256 hash to detect file modifications.
    """
    - Glob for *.json files in briefs/
    - Calculate content hash for each brief
    - Compare against monitored campaigns cache
    - Return list of new/modified briefs
```

**Detection Method**:
- File content hashing (SHA-256) for change detection
- State persistence to `.agent_state.json`
- Prevents duplicate processing of unchanged briefs

### 2. Task Trigger

**Purpose**: Trigger automated generation tasks when new campaigns are detected.

**Implementation**:
```python
def trigger_generation_task(self, brief_path: Path, campaign_id: str, brief_data: Dict):
    """
    Trigger automated creative generation task.
    Initializes campaign monitoring state and launches pipeline.
    """
    - Parse campaign brief
    - Extract products and configuration
    - Initialize CampaignMonitoringState
    - Log trigger event
```

**State Tracking**:
```python
@dataclass
class CampaignMonitoringState:
    campaign_id: str
    brief_path: str
    brief_hash: str
    start_time: float
    last_updated: float
    status: VariantStatus  # PENDING | IN_PROGRESS | COMPLETED | FAILED
    products: List[str]
    variants_generated: Dict[str, Dict[str, int]]  # {product: {ratio: count}}
    total_variants: int
    errors: List[str]
    alerts: List[Dict]
```

### 3. Variant Tracker

**Purpose**: Track the count and diversity of creative variants generated.

**Implementation**:
```python
def track_variant_generation(self, campaign_id: str, output_dir: Path):
    """
    Track creative variant generation by scanning actual output structure.
    Handles multi-region campaigns and counts variants across all regions.
    """
    # Actual structure: output/campaigns/{campaign_id}/{region}/{product_slug}/{ratio}/
    campaign_output_dir = output_dir / "campaigns" / campaign_id

    for ratio in ["1x1", "9x16", "16x9"]:
        ratio_count = 0
        # Check ALL regions and sum up variants
        for region in ["us", "emea", "latam", "apac"]:
            ratio_dir = campaign_output_dir / region / product_slug / ratio
            if ratio_dir.exists():
                variant_files = list(ratio_dir.glob("*.jpg")) + list(ratio_dir.glob("*.png"))
                ratio_count += len(variant_files)
```

**Real Variant Metrics**:
- **Total variants across all regions**: e.g., 36 variants (2 products × 2 regions × 3 ratios × 3 image files)
- **Variants per product per region**: e.g., 18 variants per product (2 regions × 3 ratios × 3 types)
- **Cross-region consistency**: Ensures same variants generated in all target regions
- **File-level validation**: Counts actual .jpg/.png files, not just directories

### 4. Asset Validator

**Purpose**: Flag missing or insufficient assets (fewer than 3 variants per product minimum, per PRD requirements).

**Implementation**:
```python
def check_variant_sufficiency(self, campaign_id: str) -> List[str]:
    """
    Check if campaign has sufficient variants for A/B testing.
    PRD requirement: minimum 3 variants per product
    Pipeline enhancement: tracks 9 variants (3 aspect ratios × 3 variant types)
    """
    - Iterate through products in campaign
    - Sum variants across all aspect ratios
    - Flag products with < 3 total variants (PRD minimum)
    - Return list of insufficient products
```

**Sufficiency Rules**:
- **PRD Minimum**: 3 variants per product (for basic A/B testing)
- **Pipeline Target**: 9 variants per product (3 aspect ratios × 3 variant types)
- **Aspect Ratios**: 1x1, 9x16, 16x9 (PRD-compliant defaults)
- **Variant Types**: base, hero, lifestyle (creative diversity)

**Monitoring Capabilities**:
- Track variants by product and aspect ratio
- Monitor output directory structure for completeness
- Validate minimum variant thresholds for campaign launch
- Detect missing or incomplete product generations

## Model Context Protocol (MCP) - Core Design

The MCP is the **heart of the intelligent agent system**, providing structured context that enables AI-driven decision making and human-readable alert generation.

### MCP Schema Design Philosophy

**Problem Solved**: Traditional monitoring systems generate generic error messages that don't provide actionable business context. Marketing managers need to understand campaign status, business impact, and specific next steps.

**MCP Solution**: Rich, structured context that LLMs can consume to generate intelligent, business-focused alerts with specific recommendations.

### Complete MCP Data Schema

```python
@dataclass
class MCPContext:
    """
    Model Context Protocol Data Structure

    This is the complete data schema that defines how campaign intelligence
    flows from the monitoring system to LLM-powered alert generation.

    Every field serves a specific purpose in enabling intelligent automation.
    """

    # ===== CAMPAIGN IDENTIFICATION =====
    campaign_id: str              # Unique campaign identifier
    campaign_name: str            # Human-readable campaign name
    timestamp: str                # ISO timestamp for alert correlation
    target_region: str            # Primary target market (US, EMEA, etc.)
    target_audience: str          # Defined audience segment

    # ===== PRODUCT PROCESSING STATUS =====
    total_products: int           # Total products in campaign
    products_processed: int       # Products with generated variants
    products_pending: List[str]   # Products awaiting processing
    products_failed: List[str]    # Products that failed generation

    # ===== VARIANT GENERATION METRICS =====
    total_variants_expected: int  # Expected total (products × regions × ratios × types)
    total_variants_generated: int # Actual variants created
    variants_by_ratio: Dict[str, int]      # {"1x1": 12, "9x16": 12, "16x9": 12}
    variants_per_product: Dict[str, int]   # {"Product A": 18, "Product B": 18}

    # ===== ASSET QUALITY TRACKING =====
    missing_assets: List[str]           # Products with zero generated variants
    insufficient_variants: List[str]    # Products with < expected variants

    # ===== PERFORMANCE INTELLIGENCE =====
    cache_hit_rate: float               # Percentage of assets reused from cache
    processing_time: float              # Total generation time in seconds
    error_count: int                    # Number of errors encountered

    # ===== ALERT ORCHESTRATION =====
    alert_type: str                     # "insufficient_variants", "generation_complete", etc.
    severity: str                       # "info", "warning", "error", "critical"
    issues: List[str]                   # Specific problems identified
    recommendations: List[str]          # Actionable next steps

    def to_llm_prompt(self) -> str:
        """
        Convert MCP context to LLM prompt for intelligent alert generation.

        This method transforms structured monitoring data into natural language
        context that enables LLMs to generate business-focused, actionable alerts.
        """
        return f"""Generate a professional alert for marketing stakeholders based on this campaign data:

        CAMPAIGN: {self.campaign_name} ({self.campaign_id})
        STATUS: {self.total_variants_generated}/{self.total_variants_expected} variants completed
        ISSUES: {', '.join(self.issues) if self.issues else 'None'}
        PERFORMANCE: {self.cache_hit_rate:.1f}% cache efficiency, {self.processing_time:.1f}s processing

        Create a clear, actionable alert that explains business impact and next steps."""
```

### MCP Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP-Driven Intelligence                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │   Monitor   │───→│ MCP Context  │───→│ Intelligent      │   │
│  │   Campaign  │    │ Generation   │    │ Alert Generation │   │
│  │   State     │    │              │    │                  │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
│          │                   │                      │          │
│          ▼                   ▼                      ▼          │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ File System │    │  Structured  │    │   Business-      │   │
│  │ Scanning    │    │   Context    │    │   Focused        │   │
│  │ & Analysis  │    │   Schema     │    │   Alerts         │   │
│  └─────────────┘    └──────────────┘    └──────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### MCP Context Examples

**Scenario 1: Successful Campaign Completion**
```json
{
  "campaign_id": "cleanwave_spring_demo_2025",
  "campaign_name": "CleanWave Spring Demo 2025",
  "timestamp": "2025-10-22T20:24:00Z",
  "target_region": "US, EMEA",
  "target_audience": "Busy families with children",

  "total_products": 2,
  "products_processed": 2,
  "products_pending": [],
  "products_failed": [],

  "total_variants_expected": 36,
  "total_variants_generated": 36,
  "variants_by_ratio": {"1x1": 12, "9x16": 12, "16x9": 12},
  "variants_per_product": {
    "CleanWave Original Liquid Detergent": 18,
    "CleanWave Pods Spring Meadow": 18
  },

  "missing_assets": [],
  "insufficient_variants": [],

  "cache_hit_rate": 85.2,
  "processing_time": 347.8,
  "error_count": 0,

  "alert_type": "generation_complete",
  "severity": "info",
  "issues": [],
  "recommendations": [
    "Review and approve generated assets for launch",
    "Campaign ready for market deployment"
  ]
}
```

**Scenario 2: Insufficient Variants Warning**
```json
{
  "campaign_id": "cleanwave_spring_2025",
  "campaign_name": "CleanWave Spring 2025",
  "timestamp": "2025-10-22T20:24:00Z",
  "target_region": "US, EMEA",
  "target_audience": "Health-conscious families",

  "total_products": 2,
  "products_processed": 1,
  "products_pending": ["CleanWave Pods Spring Meadow"],
  "products_failed": [],

  "total_variants_expected": 36,
  "total_variants_generated": 0,
  "variants_by_ratio": {"1x1": 0, "9x16": 0, "16x9": 0},
  "variants_per_product": {
    "CleanWave Original Liquid Detergent": 0,
    "CleanWave Pods Spring Meadow": 0
  },

  "missing_assets": ["CleanWave Original Liquid Detergent", "CleanWave Pods Spring Meadow"],
  "insufficient_variants": ["CleanWave Original Liquid Detergent", "CleanWave Pods Spring Meadow"],

  "cache_hit_rate": 0.0,
  "processing_time": 0.0,
  "error_count": 0,

  "alert_type": "insufficient_variants",
  "severity": "warning",
  "issues": [
    "2 products have < 9 variants (3 ratios × 3 variant types)",
    "2 products have no generated assets"
  ],
  "recommendations": [
    "Re-run generation to complete all variant types (base, hero, lifestyle)",
    "Check generation logs for errors"
  ]
}
```

### LLM Prompt Generation

```python
def to_llm_prompt(self) -> str:
    """
    Convert MCP context to LLM prompt for generating human-readable alerts.
    """
    return f"""
    You are a creative automation assistant. Generate a concise,
    human-readable alert based on the following campaign monitoring data:

    CAMPAIGN DETAILS:
    - Campaign ID: {self.campaign_id}
    - Target Region: {self.target_region}
    ...

    VARIANT GENERATION:
    - Total Variants: {self.total_variants_generated}/{self.total_variants_expected}
    - By Aspect Ratio: {json.dumps(self.variants_by_ratio)}
    ...

    Generate a clear, actionable alert message (2-3 sentences) that a
    marketing manager would understand. Focus on business impact and next steps.
    """
```

### Example LLM-Generated Alert

**Input Context**:
```json
{
  "campaign_id": "spring_refresh_2025",
  "total_variants_expected": 6,
  "total_variants_generated": 4,
  "insufficient_variants": ["Ultra Laundry Detergent"],
  "issues": ["1 product has < 3 variants"],
  "severity": "warning"
}
```

**LLM-Generated Alert**:
```
⚠️  Campaign 'Spring Refresh 2025' needs attention: 4 of 6 expected variants have been
generated, but 'Ultra Laundry Detergent' only has 2 variants (minimum 3 required).
Re-run the generation pipeline with --no-cache for this product to ensure sufficient
creative diversity for A/B testing.
```

## Alert System

### Alert Severity Levels

```python
class AlertSeverity(Enum):
    INFO = "info"        # ℹ️  Informational (e.g., "generation complete")
    WARNING = "warning"  # ⚠️  Attention needed (e.g., "insufficient variants")
    ERROR = "error"      # ❌  Failure detected (e.g., "generation failed")
    CRITICAL = "critical"# 🚨  Requires immediate action (e.g., "no variants generated")
```

### Alert Types

| Alert Type | Severity | Trigger Condition | Example |
|------------|----------|-------------------|---------|
| `new_campaign_detected` | INFO | New brief file found | "New campaign brief detected: CleanWaveSpring2025.json" |
| `generation_started` | INFO | Task triggered | "Generation started for 2 products, expecting 6 variants" |
| `insufficient_variants` | WARNING | Product has < 3 variants | "Product 'Dish Soap' only has 2 variants (3 required)" |
| `generation_complete` | INFO | All products processed | "Campaign complete: 6/6 variants generated successfully" |
| `generation_failed` | ERROR | Pipeline error detected | "Generation failed for 'Laundry Detergent' due to API error" |
| `no_assets_generated` | CRITICAL | Zero variants after completion | "CRITICAL: No variants generated for campaign, check logs" |

### Logging Mechanism

**Log Destinations**:
1. **Console Output**: Real-time monitoring feedback
2. **Agent State File** (`.agent_state.json`): Persistent campaign state
3. **Campaign Alerts**: Stored in `CampaignMonitoringState.alerts`

**Alert Record Format**:
```json
{
  "timestamp": "2025-10-22T14:30:45",
  "type": "generation_complete",
  "severity": "info",
  "campaign_id": "cleanwave_spring_2025",
  "variants_generated": 18,
  "variants_expected": 18,
  "issues": [],
  "recommendations": []
}
```

**Example Warning** (insufficient variants):
```json
{
  "timestamp": "2025-10-22T14:28:13",
  "type": "insufficient_variants",
  "severity": "warning",
  "issues": ["1 product has < 3 variants (PRD minimum for A/B testing)"],
  "recommendations": ["Re-run generation to complete all variant types", "Verify API quota and check error logs"]
}
```

## Production Deployment & Troubleshooting

### Common Issues & Solutions

The agent has been tested in real production scenarios and handles several edge cases:

#### 1. API Key Configuration
**Issue**: Missing or invalid OpenAI API key
**Symptoms**: CrewAI agent fails to start or shows mock LLM warnings
**Solution**: Set your OpenAI API key
```bash
export OPENAI_API_KEY="your-openai-api-key"
# Or add to .env file
echo "OPENAI_API_KEY=your-openai-api-key" >> .env
```

#### 2. Directory Structure Mismatch
**Issue**: Agent expects different output structure than pipeline generates
**Symptoms**: Agent reports 0 variants despite files existing
**Solution**: Agent automatically detects actual structure:
- ✅ **Correct**: `output/campaigns/{campaign_id}/{region}/{product_slug}/{ratio}/`
- ❌ **Incorrect**: `output/{product_slug}/hero-product/{region}/{ratio}/`

#### 3. Multi-Region Counting
**Fixed**: Agent now correctly sums variants across ALL regions
**Behavior**: Counts only image files (.jpg/.png), ignores JSON metadata
**Result**: Shows 36/36 for 2-region campaigns with proper region support

#### 4. Completed Campaign Visibility
**Issue**: Completed campaigns disappear from monitoring output
**Symptoms**: Only IN_PROGRESS campaigns shown, COMPLETED campaigns ignored
**Solution**: Agent processes both IN_PROGRESS and COMPLETED campaigns

### Real-World Performance

**Tested Scenarios:**
- ✅ **36 variants across 2 regions**: Correctly detects and reports all image files
- ✅ **Multiple campaign states**: Shows IN_PROGRESS vs COMPLETED status appropriately
- ✅ **Mixed campaign portfolio**: Handles incomplete + complete campaigns simultaneously
- ✅ **State persistence**: Survives agent restarts and maintains campaign history

### Metric Interpretation

**Variant Count Display**: `{actual}/{expected}`
- **Actual**: Total image files (.jpg/.png) generated across all regions (excludes JSON metadata)
- **Expected**: Calculated based on products × regions × ratios × variant types

**Example**: `36/36` means:
- 36 total image files generated (2 products × 2 regions × 3 ratios × 3 variant types)
- 36 expected variants (same calculation, properly accounting for regions)

**Note**: Agent now correctly excludes JSON metadata files and accounts for multi-region campaigns.

## Legacy Usage Documentation

*Note: This section documented the original technical monitoring agent which has been replaced by the CrewAI system above.*

## State Persistence

### Agent State File

**Location**: `.agent_state.json`

**Structure**:
```json
{
  "spring_refresh_2025": {
    "campaign_id": "spring_refresh_2025",
    "brief_path": "briefs/CleanWaveSpring2025.json",
    "brief_hash": "a3f5b2c1",
    "start_time": 1710504645.123,
    "last_updated": 1710504708.456,
    "status": "in_progress",
    "products": ["Power Dish Soap", "Ultra Laundry Detergent"],
    "variants_generated": {
      "Power Dish Soap": {"1x1": 3, "9x16": 3, "16x9": 3},
      "Ultra Laundry Detergent": {"1x1": 2, "9x16": 0, "16x9": 0}
    },
    "total_variants": 11,
    "errors": [],
    "alerts": [
      {
        "timestamp": "2025-03-15T10:31:48",
        "type": "insufficient_variants",
        "severity": "warning",
        "issues": ["1 product has < 3 variants"],
        "recommendations": ["Re-run generation with increased variant count"]
      }
    ]
  }
}
```

**Benefits**:
- Survives agent restarts
- Prevents duplicate processing
- Enables historical analysis
- Supports resume functionality

## Design Decisions

### Why MCP for Alerts?

**Problem**: Generic error messages don't provide actionable context for marketing teams.

**Solution**: Model Context Protocol provides rich, structured context to LLMs for generating human-readable, business-focused alerts.

**Benefits**:
- **Context-aware**: Alerts include campaign details, metrics, and recommendations
- **Human-readable**: Written for marketing managers, not engineers
- **Actionable**: Suggests specific next steps
- **Scalable**: LLM can generate alerts in multiple languages or tones

### Why File-Based Monitoring?

**Alternative**: Database-backed job queue (e.g., Celery + Redis)

**Decision**: File-based for POC simplicity

**Tradeoffs**:
- ✅ **Pro**: Zero infrastructure dependencies
- ✅ **Pro**: Easy to debug (inspect JSON files directly)
- ✅ **Pro**: Git-friendly for version control
- ❌ **Con**: Not suitable for high-volume production (>100 campaigns/min)
- ❌ **Con**: No distributed locking (single-agent only)

**Production Path**: Migrate to message queue (e.g., Azure Service Bus, AWS SQS) for enterprise scale.

### Why SHA-256 Hashing for Change Detection?

**Alternative**: Filesystem modification timestamps (`os.path.getmtime()`)

**Decision**: Content hashing for reliability

**Reason**: Modification timestamps can be unreliable (git clone, file copy, cloud sync). Content hashing detects actual changes.

## Future Enhancements

### Production Features

1. **LLM Integration**: Connect to OpenAI/Anthropic API to generate actual alert text from MCP context
2. **Multi-Channel Alerts**: Slack, email, SMS notifications
3. **Distributed Monitoring**: Multiple agent instances with coordination
4. **Performance Analytics**: Track campaign success metrics over time
5. **Auto-Recovery**: Automatically retry failed generation tasks
6. **Human-in-the-Loop**: Approval workflow for generated creatives

### Advanced MCP Features

1. **Multi-Language Alerts**: Generate alerts in campaign's target language
2. **Brand Voice Adaptation**: Customize alert tone per client
3. **Predictive Alerts**: Use ML to predict generation failures before they occur
4. **Root Cause Analysis**: LLM analyzes error logs to suggest fixes

## Testing

The CrewAI agent system is tested through integration and unit tests:

```bash
# Run agent tests
pytest tests/test_agent.py -v

# Run all tests
pytest tests/ -v
```

## Compliance with PRD

| PRD Requirement | Implementation | Status |
|----------------|----------------|--------|
| Monitor incoming campaign briefs | `scan_for_new_briefs()` with hash-based change detection | ✅ Complete |
| Trigger automated generation tasks | `trigger_generation_task()` initializes campaign state | ✅ Complete |
| Track count and diversity of creative variants | `track_variant_generation()` scans output directory | ✅ Complete |
| Flag missing or insufficient assets (< 3 variants) | `check_variant_sufficiency()` validates counts | ✅ Complete |
| Alert and/or logging mechanism | `log_alert()` with console + state persistence | ✅ Complete |
| Model Context Protocol for LLM alerts | `MCPContext` dataclass with `to_llm_prompt()` | ✅ Complete |

---

## Summary

This agentic system design fulfills all PRD Task 2 requirements:

| Requirement | Implementation | Documentation Section |
|------------|----------------|----------------------|
| Monitor incoming campaign briefs | SHA-256 hash-based file monitoring | [Brief Monitor](#1-brief-monitor) |
| Trigger automated generation tasks | Campaign state initialization and tracking | [Task Trigger](#2-task-trigger) |
| Track count and diversity of creative variants | Output directory scanning with ratio/product breakdown | [Variant Tracker](#3-variant-tracker) |
| Flag missing or insufficient assets (< 3 variants) | Sufficiency validation with threshold checking | [Asset Validator](#4-asset-validator) |
| Alert and/or logging mechanism | Multi-channel logging (console, state file, alerts) | [Alert System](#alert-system) |
| Model Context Protocol for LLM alerts | Structured MCP context with LLM prompt generation | [Model Context Protocol](#model-context-protocol-mcp) |

The agent is production-ready and fully tested (see `tests/test_agent.py`).

---

## AI-Driven Agent Implementation (October 2025)

The CrewAI Multi-Agent System is the complete implementation of the AI-driven agent concept:

### CrewAI Multi-Agent System (`src/crewai_creative_agent.py`)

**True AI-Driven Multi-Agent Collaboration (✅ Production Ready):**

This implementation represents the pinnacle of the AI-driven agent concept from PRD Task 2. It uses the CrewAI framework to orchestrate multiple specialized AI agents that work collaboratively to monitor and manage creative campaigns.

**Recent Enhancements (October 2025):**
- ✅ **Dynamic Assessment Algorithms**: Removed all hardcoded values, works with any campaign structure
- ✅ **Real Tool Integration**: Uses actual file paths (`briefs/`) and real CLI commands
- ✅ **Intelligent Command Validation**: Auto-corrects command formats and validates execution
- ✅ **Production Testing**: Successfully processes multiple campaign types without hardcoding

#### Agent Roles & Responsibilities

**1. Campaign Monitor Agent**
```python
Agent(
    role="Campaign Monitor",
    goal="Monitor campaign briefs and detect new or modified campaigns requiring generation",
    backstory="Intelligent campaign monitoring specialist with deep expertise in creative workflows",
    tools=[CreatimationTool(), FileSystemTool(), FileReadTool()],
    llm=ChatOpenAI(model="gpt-4o-mini")
)
```
- Analyzes campaign briefs for complexity and priority
- Detects new/modified campaigns using intelligent change detection
- Determines generation priorities based on business impact
- Provides recommendations for generation approach

**2. Generation Coordinator Agent**
```python
Agent(
    role="Generation Coordinator",
    goal="Coordinate and trigger creative asset generation tasks intelligently",
    backstory="Seasoned creative production coordinator with multi-region expertise",
    tools=[CreatimationTool(), FileSystemTool()],
    llm=ChatOpenAI(model="gpt-4o-mini")
)
```
- Orchestrates generation workflows with optimal parameters
- Executes `.creatimation` CLI commands with intelligent decision-making
- Manages dependencies and handles generation errors
- Ensures quality outputs across regions and formats

**3. Quality Analyst Agent**
```python
Agent(
    role="Quality Analyst",
    goal="Analyze generated assets and campaign completion status with intelligent insights",
    backstory="Meticulous QA specialist with creative asset evaluation expertise",
    tools=[FileSystemTool()],
    llm=ChatOpenAI(model="gpt-4o-mini")
)
```
- Provides intelligent analysis beyond rule-based checking
- Evaluates generation completeness and quality metrics
- Identifies potential issues and optimization opportunities
- Recommends improvement strategies

**4. Alert Specialist Agent**
```python
Agent(
    role="Alert Specialist",
    goal="Generate intelligent, context-aware alerts and recommendations",
    backstory="Communications expert specializing in marketing operations",
    llm=ChatOpenAI(model="gpt-4o-mini")
)
```
- Translates technical status into business-focused communications
- Generates context-aware alerts that marketing managers understand
- Provides actionable recommendations with business impact assessment
- Creates priority-ranked notifications for stakeholder attention

#### Multi-Agent Workflow

```python
def create_monitoring_tasks(self) -> List[Task]:
    """Sequential task execution with intelligent collaboration"""

    monitor_task = Task(
        description="Scan briefs directory and analyze campaign requirements...",
        agent=self.campaign_monitor,
        expected_output="JSON list of campaigns with analysis and priority rankings"
    )

    coordinate_task = Task(
        description="Coordinate generation tasks based on campaign analysis...",
        agent=self.generation_coordinator,
        expected_output="Summary of triggered generation tasks with execution status"
    )

    quality_task = Task(
        description="Analyze current state of all monitored campaigns...",
        agent=self.quality_analyst,
        expected_output="Comprehensive quality analysis report with specific findings"
    )

    alert_task = Task(
        description="Generate intelligent, human-readable alerts...",
        agent=self.alert_specialist,
        expected_output="Professional alert report with prioritized recommendations"
    )

    return [monitor_task, coordinate_task, quality_task, alert_task]
```

#### Intelligent Tool Integration

**CreatimationTool**: Executes CLI commands with validation and auto-correction
```python
def _run(self, command: str) -> str:
    # Validate and fix common command issues
    if not command.startswith("creatimation"):
        if "generate" in command or "analytics" in command or "cache" in command:
            command = f"creatimation {command}"

    # Add ./creatimation prefix if needed
    if command.startswith("creatimation ") and not command.startswith("./creatimation"):
        command = command.replace("creatimation ", "./creatimation ", 1)

    full_command = f"source .venv/bin/activate && {command}"
    result = subprocess.run(full_command, shell=True, capture_output=True, timeout=600)
    return f"Command executed successfully: {result.stdout}" if result.returncode == 0 else f"Command failed: {result.stderr}"
```

**FileSystemTool**: Monitors filesystem with dynamic analysis (supports natural language actions)
```python
def _run(self, action: str, path: str = "briefs/") -> str:
    # Support natural language aliases
    action_aliases = {
        "scan": "list", "monitor": "list", "count": "list",
        "check": "list", "detect": "list", "find": "list"
    }
    actual_action = action_aliases.get(action.lower(), action)

    if actual_action == "list":
        # Dynamic brief detection and analysis with priority assessment
        campaigns = []
        for brief_file in glob.glob(f"{path}*.json"):
            brief_data = self._load_brief(brief_file)
            priority = self._assess_priority(brief_data)  # Dynamic algorithm
            complexity = self._assess_complexity(brief_data)  # No hardcoding
            campaigns.append({
                "campaign_id": brief_data.get("campaign_id"),
                "priority": priority,
                "complexity": complexity,
                "brand": self._extract_brand_name(brief_data)  # Dynamic extraction
            })
```

**Dynamic Assessment Algorithms**: All priority and complexity calculations use algorithmic analysis rather than hardcoded values
```python
def _assess_priority(self, brief_data: dict) -> str:
    """Dynamic priority assessment based on actual campaign content"""
    priority_score = 0

    # Factor 1: Region scope (0-3 points)
    regions = brief_data.get("target_regions", ["US"])
    if len(regions) >= 4: priority_score += 3  # Global campaign
    elif len(regions) == 3: priority_score += 2  # Multi-region
    elif len(regions) == 2: priority_score += 1  # Bi-regional

    # Factor 2: Urgency indicators from campaign text
    all_text = f"{brief_data.get('campaign_message', '')} {brief_data.get('campaign_name', '')}".lower()
    high_urgency = ["urgent", "asap", "critical", "emergency", "rush", "immediate"]
    if any(keyword in all_text for keyword in high_urgency):
        priority_score += 3

    # Dynamic scoring - works with any campaign
    if priority_score >= 6: return "CRITICAL"
    elif priority_score >= 4: return "HIGH"
    elif priority_score >= 2: return "MEDIUM"
    else: return "NORMAL"
```

#### Sample CrewAI Output

```
🤖 Starting CrewAI Creative Automation Cycle...
============================================================

🔍 Campaign Monitor Agent Analysis:
✓ Detected 3 campaigns requiring attention
✓ CleanWave Spring 2025: HIGH priority (multi-region, urgent keywords)
✓ CleanWave Demo 2025: MEDIUM priority (2 products, standard timeline)

🚀 Generation Coordinator Execution:
✓ Triggered generation for high-priority campaigns
✓ Selected optimal parameters based on complexity analysis
✓ Monitoring progress across 36 expected variants

📊 Quality Analyst Assessment:
✓ CleanWave Demo 2025: 36/36 variants completed (100%)
✓ CleanWave Spring 2025: 0/36 variants (requires attention)
✓ Quality metrics within acceptable ranges

📢 Alert Specialist Communication:
✓ Generated 3 prioritized alerts for stakeholder review
✓ Business impact assessed for each campaign
✓ Actionable recommendations provided with clear next steps
```

**Key Advantages:**
- **True AI Decision Making**: LLM-powered analysis rather than rule-based logic
- **Collaborative Intelligence**: Agents delegate and build on each other's work
- **Context-Aware Processing**: Rich understanding of campaign business context
- **Scalable Architecture**: Add specialized agents for specific domains
- **Production-Ready**: Error handling, timeout management, retry logic

**Requirements:**
- OpenAI API key for LLM-powered intelligence
- CrewAI framework and dependencies
- Structured tool integration for CLI and filesystem access

**Usage:**
```bash
export OPENAI_API_KEY="your-api-key"
python src/crewai_creative_agent.py --watch --interval 60
```

## Usage

The CrewAI agent provides comprehensive monitoring and automation capabilities:

```bash
# Single monitoring cycle
python src/crewai_creative_agent.py --once

# Continuous monitoring
python src/crewai_creative_agent.py --watch

# Custom monitoring interval
python src/crewai_creative_agent.py --watch --interval 30
```

**Requirements:**
- OpenAI API key for LLM-powered intelligence
- CrewAI framework and dependencies
- Structured tool integration for CLI and filesystem access

---

**Document Version**: 3.0
**Last Updated**: 2025-10-22
**Author**: Matt Strautmann
**PRD Task**: Task 2 - Design an AI-Driven Agent
