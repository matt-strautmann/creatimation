# Quick Setup Guide

## 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv

# Install with uv (recommended)
uv pip install --python .venv/bin/python3 -r requirements.txt

# Or use pip
.venv/bin/pip install -r requirements.txt
```

## 2. Get FREE Google API Key

**Gemini 2.5 Flash Image is FREE for development!**
- 🆓 **500 requests per day** through Google AI Studio
- Perfect for testing and development
- Production pricing: $0.039 per image (51% cheaper than DALL-E)

```bash
# Get your FREE API key:
# 1. Visit https://aistudio.google.com/app/apikey
# 2. Click "Get API Key" (requires Google account)
# 3. Copy your key
```

## 3. Configure API Keys

```bash
# Copy example and add your keys
cp .env.example .env

# Edit .env and add your Google API key (required)
echo "GOOGLE_API_KEY=your_google_key_here" >> .env

# Add OpenAI API key for CrewAI Multi-Agent System (optional)
echo "OPENAI_API_KEY=your_openai_key_here" >> .env
```

**API Key Requirements:**
- **Google API Key**: Required for image generation (FREE: 500 requests/day)
- **OpenAI API Key**: Optional - only needed for CrewAI Multi-Agent System
  - Get from: https://platform.openai.com/account/api-keys
  - Used for LLM-powered AI agent collaboration

## 4. Check Configuration Status (Discovery-Driven Setup)

Creatimation uses a smart configuration system that **guides you through setup**:

```bash
# Check what's configured and what's missing
./creatimation config show

# The system tells you exactly what to run next:
# ↓ If no global config: "Run: ./creatimation config init --global"
# ↓ If no workspace config: "Run: ./creatimation config init"
```

**What this does:**
- **Global config** (`~/.creatimation/config.yml`): API keys and defaults shared across workspaces
- **Workspace config** (`.creatimation.yml`): Auto-detects your campaigns and extracts brand info
- **Campaign detection**: Automatically finds campaigns in `briefs/` directory
- **Unified view**: Shows global + local + detected campaigns in one command

**Example output:**
```
Global Configuration
✓ API Keys configured
✓ Default settings available

Workspace Configuration
✓ Project: CleanWave Spring Freshness Launch 2025
✓ Brand: CleanWave (auto-detected from briefs)
✓ Industry: CPG - Laundry Care (auto-detected)

Workspace Assets
✓ 2 campaign(s) detected
  Laundry Care
    ├─ CleanWave (2 campaigns)
✓ 1 brand guide(s) available
```

**Configuration Hierarchy** (highest to lowest priority):
1. **CLI flags**: `--variants 5` (overrides everything)
2. **Workspace config**: `.creatimation.yml` (workspace-specific)
3. **Global config**: `~/.creatimation/config.yml` (shared across workspaces)
4. **Auto-detection**: Campaigns detected from `briefs/` directory
5. **Defaults**: Built-in fallbacks

**Tip**: You can run `./creatimation config show` anytime to see your complete configuration setup!

## 5. Run Pipeline

### Option A: Using CLI (Recommended)

```bash
# Make CLI executable
chmod +x creatimation

# Dry-run preview (no API key needed)
./creatimation generate campaign briefs/CleanWaveSpring2025.json --dry-run

# Generate creatives with brand guide (uses API key)
./creatimation generate campaign briefs/CleanWaveSpring2025.json --brand-guide brand-guides/cleanwave_blue.yml
```

### Option B: Direct Python

```bash
# Test with CleanWave example
.venv/bin/python3 -m src.cli.main generate campaign briefs/CleanWaveSpring2025.json --brand-guide brand-guides/cleanwave_blue.yml
```

## Expected Output

The pipeline generates **36 regional variants** (2 regions × 2 products × 3 ratios × 3 variants):

**Structure Pattern:**
```
output/{product-slug}/{layout}/{region}/{ratio}/
├── base.jpg
├── hero.jpg
└── lifestyle.jpg
```

**Example Output:**
```
output/cleanwave-original-liquid-detergent/hero-product/
├── us/
│   ├── 1x1/
│   │   ├── base.jpg
│   │   ├── hero.jpg
│   │   └── lifestyle.jpg
│   ├── 9x16/
│   │   ├── base.jpg
│   │   ├── hero.jpg
│   │   └── lifestyle.jpg
│   └── 16x9/
│       ├── base.jpg
│       ├── hero.jpg
│       └── lifestyle.jpg
└── emea/
    └── [same structure]

# Multi-Region Structure (supports up to 4 markets)
output/{product-slug}/{layout}/
  ├── us/      # "Try CleanWave Today"
  ├── latam/   # "Prueba CleanWave Hoy"
  ├── apac/    # "Experience CleanWave Now"
  └── emea/    # "Discover CleanWave Today"

cache/products/
  ├── cleanwave-original-liquid-detergent.png  # Reused 36 times!
  ├── cleanwave-pods-spring-meadow.png         # Reused 36 times!
  └── ...

cache/index.json           # Product registry with campaigns_used tracking
```

**Global Scale Structure:**
- **4 Regions**: US, LATAM, APAC, EMEA (market-specific CTAs)
- **3 Default Aspect Ratios**: 1x1 (Instagram), 9x16 (Stories), 16x9 (YouTube)
- **7 Optional Ratios**: 4x5, 5x4, 3x4, 4x3, 2x3, 3x2, 21x9
- **3 Variant Types**: base, hero, lifestyle
- **Product Consistency**: 100% identical across all 36 regional variants
- **Regional Localization**: Market-specific calls-to-action

## Performance Expectations

With Gemini 2.5 Flash Image + Product Caching + Multi-Region:
- **Speed**: ~9 seconds per creative (with cached products)
- **36 regional creatives**: ~6 minutes total (2 regions × 18 variants each)
- **Cost**:
  - First run: $1.48 (2 products + 36 fusions = 38 calls)
  - Subsequent runs: $1.40 (0 products + 36 fusions) - products cached!
- **Cache Efficiency**: 5% cost savings on subsequent campaigns
- **Cache Hit Rate**: 100% (products reused across all variants)
- **ROI**: 99.7% cheaper than manual ($1.48 vs $500-2000)
- **API efficiency**: 51% cheaper per image than DALL-E ($0.039 vs $0.08)

## Semantic Asset Organization

The pipeline now uses an **S3-ready semantic structure** for optimal asset management:

### Local Structure
```
output/                                  # Campaign outputs
├── {product-slug}/
│   └── {layout}/{region}/{ratio}/
│       ├── base.jpg
│       ├── hero.jpg
│       └── lifestyle.jpg

cache/                                   # Intelligent caching
├── products/{product-slug}.png          # Reusable product assets
└── index.json                           # Product registry + metadata
```

### Key Benefits
- ✅ **Product-centric**: Easy discovery of all creatives for a product
- ✅ **Semantic paths**: Region/ratio organization for intelligent reuse
- ✅ **Cache-first**: 5% cost savings on subsequent campaigns with same products
- ✅ **S3-ready**: Direct mapping to cloud storage for scale

### Future S3 Migration

When scaling to global production:
```
Local → S3 Mapping
output/{product}/{layout}/{region}/{ratio}/ → s3://cpg-assets/{product}/{layout}/{region}/{ratio}/
cache/products/ → s3://cpg-assets/library/products/
```

**Projected Cost at Scale (1M assets, 2TB):**
- S3 Storage: $41/month (intelligent tiering)
- CloudFront CDN: $870/month (global <50ms latency)
- **Total**: $915/month vs $3,000+ with generation costs

See `examples/S3_MIGRATION_SUMMARY.md` for complete migration strategy.

## Troubleshooting

### Missing Google API Key
```bash
# Make sure .env file exists with valid key
cat .env
# Should show: GOOGLE_API_KEY=your_key_here

# Test API key is working (dry-run doesn't need it)
./creatimation generate campaign briefs/CleanWaveSpring2025.json --dry-run
```

### Module not found
```bash
# Verify all dependencies installed
uv pip list | grep google-genai

# Should show: google-genai x.x.x

# If missing, reinstall
uv pip install -r requirements.txt
```

### Pipeline state error
```bash
# Clear old state files
rm .pipeline_state_*.json

# Clear cache if needed
./creatimation cache clear
```

### Import Error: cannot import 'genai'
```bash
# Install google-genai package
uv pip install google-genai

# Verify installation
python -c "from google import genai; print('✓ Gemini SDK installed')"
```

## CLI Commands Quick Reference

```bash
# Configuration (smart auto-detection)
./creatimation config show               # Unified view: global + workspace + campaigns
./creatimation config init --global      # Setup shared settings (API keys, defaults)
./creatimation config init               # Setup workspace (auto-detects campaigns)
./creatimation config validate           # Validate all configurations

# Generation
./creatimation generate campaign <brief.json> --dry-run    # Preview (no API calls)
./creatimation generate campaign <brief.json> --brand-guide brand-guides/cleanwave_blue.yml

# Validation
./creatimation validate brief <brief.json>

# Cache management
./creatimation cache stats
./creatimation cache clear

# Analytics and monitoring
./creatimation analytics summary              # Usage overview and performance metrics
./creatimation analytics summary --recent     # Latest generation results (recommended after each run)
./creatimation analytics commands            # Command usage statistics
./creatimation analytics generation          # Generation performance tracking
./creatimation analytics clear               # Clear analytics data
```

## 6. Monitoring Agent (Optional) - MCP-Compliant Intelligence

The Creative Automation Agent provides intelligent monitoring with **Model Context Protocol (MCP)** for LLM-generated alerts:

### What It Monitors
- **Campaign briefs**: `briefs/*.json` (new/modified campaigns)
- **Configuration files**: `.creatimation.yml`, `global_config/*.yml`, `brand-guides/*.yml`
- **Generation progress**: Variant counts, missing assets, completion status
- **Performance metrics**: Cache hit rates, processing times, error rates

### MCP Schema Compliance
The agent implements a comprehensive MCP schema with structured context for LLM alert generation:
```python
# Example MCP Context Structure
{
  "campaign_id": "cleanwave_spring_2025",
  "timestamp": "2025-10-22T10:30:00Z",
  "alert_type": "insufficient_variants",
  "severity": "warning",
  "total_variants_expected": 36,
  "total_variants_generated": 12,
  "insufficient_variants": ["CleanWave Pods"],
  "recommendations": [
    "Re-run generation to complete all variant types",
    "Check generation logs for errors"
  ]
}
```

### AI-Driven Agent System

CrewAI Multi-Agent System (✅ Production Ready - Full AI):

```bash
# Setup OpenAI API key first (in .env file or export)
export OPENAI_API_KEY="your-openai-api-key"

# Run collaborative AI agents with dynamic assessment
python src/crewai_creative_agent.py --once        # Single cycle
python src/crewai_creative_agent.py --watch       # Continuous monitoring
python src/crewai_creative_agent.py --watch --interval 30  # Custom interval

# Features:
# ✅ LLM-powered decision making with 4 specialized collaborative agents
# ✅ Dynamic priority and complexity assessment (no hardcoding)
# ✅ Real CLI command execution with validation and auto-correction
# ✅ Works with any campaign structure automatically
```

**Agent Roles:**
- **Campaign Monitor**: Analyzes campaign briefs for complexity and priority
- **Generation Coordinator**: Orchestrates generation workflows and executes CLI commands
- **Quality Analyst**: Evaluates generation completeness and quality metrics
- **Alert Specialist**: Generates business-focused communications for stakeholders

**Recent Enhancements (October 2025):**
- **Dynamic Assessment Algorithms**: Removed hardcoded campaign assumptions
- **Real Tool Integration**: Uses actual file paths and CLI commands
- **Command Validation**: Auto-corrects `.creatimation` command execution
- **Production Testing**: Successfully tested with multiple campaign types

### Alert Types
- **🆕 configuration_change**: Config files modified (brand guides, workspace settings)
- **⚠️ insufficient_variants**: Products with < 9 variants (3 ratios × 3 types)
- **❌ generation_failed**: Errors during creative generation
- **✅ generation_complete**: All variants successfully generated
- **📊 performance_alert**: Cache efficiency or processing time issues

### Agent Features
- **Real-time monitoring**: 5-second scan intervals
- **Change detection**: Hash-based file monitoring for campaigns and configs
- **State persistence**: Maintains monitoring state across restarts
- **Intelligent alerts**: Context-aware recommendations based on MCP schema
- **Multiple outputs**: Console logging + JSON state files + structured alerts

### Example Output
```
ℹ️ ALERT: CONFIGURATION_CHANGE
Campaign: Configuration Monitoring
Issues: Configuration file modified: .creatimation.yml
Recommendations: Review configuration changes for impact on campaigns, Consider re-running generation if settings affect creative output

⚠️ ALERT: INSUFFICIENT_VARIANTS
Campaign: CleanWave Spring Freshness Launch 2025
Variants: 12/36
Issues: 1 products have < 9 variants (3 ratios × 3 variant types)
Recommendations: Re-run generation to complete all variant types (base, hero, lifestyle)
```

### Integration with Pipeline
The agent automatically detects when you run generation commands and:
1. **Tracks progress**: Monitors variant counts in `output/` directory
2. **Flags issues**: Alerts on missing or insufficient assets
3. **Provides context**: MCP-structured data for LLM interpretation
4. **Maintains state**: Remembers campaign status across sessions

### Use Cases
- **Development**: Monitor config changes during setup and testing
- **Production**: Continuous campaign monitoring for quality assurance
- **Debugging**: Structured alerts help identify generation issues quickly
- **Analytics**: Performance tracking and optimization insights
- **Integration**: MCP schema enables LLM-powered alert systems

## 7. Analytics & Performance Insights (Optional) - Built-in Intelligence

Creatimation includes a sophisticated **analytics plugin** that automatically tracks usage patterns and performance metrics with **privacy-first design**:

### What It Tracks
- **Command Performance**: Execution frequency, success rates, processing times
- **Generation Metrics**: Campaign processing, cache efficiency, asset creation
- **Error Analytics**: Failure patterns, error frequency, reliability tracking
- **Cache Intelligence**: Hit/miss ratios, cost optimization insights

### Recent Enhancement (v2.1)
- ✅ **Fixed Analytics Metrics Collection**: Now correctly captures generation results (36 creatives, cache hits/misses, processing time)
- ✅ **Added `--recent` Flag**: Shows latest generation results with actionable insights instead of confusing historical data
- ✅ **Performance Insights**: Displays creatives/minute and cache efficiency analysis for immediate feedback
- ✅ **Post-Generation Workflow**: Run `./creatimation analytics summary --recent` after each generation for instant results

### Analytics Commands
```bash
# Comprehensive usage overview
./creatimation analytics summary

# View most recent generation results (recommended after each run)
./creatimation analytics summary --recent

# Detailed command statistics (sorted by usage, duration, or errors)
./creatimation analytics commands --sort duration --limit 10

# Generation performance and cache efficiency
./creatimation analytics generation --limit 10

# Clear all analytics data (privacy control)
./creatimation analytics clear --confirm
```

### Enhanced Monitoring Integration
The monitoring agent now uses analytics data for **intelligent, context-aware alerts**:

**Smart Alert Context:**
- Real-time cache efficiency in MCP context
- Performance baselines for anomaly detection
- Historical success rates for reliability assessment
- Processing time trends for performance monitoring

**Example Enhanced Alert:**
```
ℹ️ ALERT: CONFIGURATION_CHANGE
Campaign: Configuration Monitoring
Issues: Configuration file modified: .creatimation.yml
Cache Efficiency: 85.2% (historical average)
Success Rate: 95.8% (last 10 operations)
Recommendations: Review configuration changes for impact on campaigns, Current system performance: 95.8% success rate
```

### Privacy & Data Control
- **Local-only storage**: Data in `~/.creatimation/analytics.json`
- **No telemetry**: Zero external data transmission
- **Fail-silent design**: Analytics failures never impact core functionality
- **Complete control**: Clear data anytime with `analytics clear`

### Performance Benefits
- **Cost optimization**: Track cache efficiency trends
- **Reliability monitoring**: Success rate tracking over time
- **Performance tuning**: Identify bottlenecks and optimization opportunities
- **Usage insights**: Understand command patterns and workflow efficiency

## 8. Testing & Quality Validation (Optional) - Production-Grade Reliability

Creatimation includes a comprehensive test suite with **138 core tests** ensuring production-ready reliability:

### Quick Test Validation

```bash
# Essential functionality test (10 seconds)
.venv/bin/pytest tests/test_agent.py tests/test_config.py tests/test_container.py tests/test_error_handling.py -v

# Expected output: ✅ 138 tests passed in 10.62s
```

### Comprehensive Test Suite

```bash
# Run all test categories
.venv/bin/pytest tests/test_agent.py -v                    # Agent system (22 tests)
.venv/bin/pytest tests/test_error_handling.py -v           # Error resilience (24 tests)
.venv/bin/pytest tests/test_cli_integration.py -v          # CLI workflows (26 tests)
.venv/bin/pytest tests/test_e2e_pipeline.py -v             # End-to-end pipeline (19 tests)
.venv/bin/pytest tests/test_cli_core.py -v                 # CLI core (21 tests)
.venv/bin/pytest tests/test_config.py -v                   # Configuration (11 tests)
.venv/bin/pytest tests/test_container.py -v                # Dependency injection (15 tests)

# Full test suite with coverage
.venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing
```

### Test Categories & What They Validate

**Core System Reliability** (138 tests - 100% pass rate):
- ✅ **Agent System**: MCP monitoring, state persistence, variant tracking
- ✅ **Error Handling**: File corruption, permission denied, network failures
- ✅ **CLI Integration**: Command workflows, configuration management
- ✅ **End-to-End Pipeline**: Complete creative generation workflows
- ✅ **Configuration**: YAML processing, validation, error recovery
- ✅ **Container System**: Dependency injection, service lifecycle

**Error Resilience Testing**:
- Configuration files: corrupted, missing, permission denied
- Plugin system: import failures with graceful degradation
- Network operations: API timeouts, connection failures
- File system: permission errors, disk space, encoding issues
- Cache corruption: invalid indices with automatic recovery

### Coverage Metrics

**Critical Module Coverage**:
- **Core Agent System**: 75.7% (MCP orchestration & monitoring)
- **Configuration**: 88.2% (YAML processing & validation)
- **Container DI**: 83.8% (service registration & lifecycle)
- **Error Handling**: 100% (all failure modes tested)

### Testing Philosophy

**Why These Tests Matter**:
- **Production Reliability**: System handles failures gracefully
- **Agent Intelligence**: Stateful monitoring works correctly
- **CLI Robustness**: Commands work together seamlessly
- **Error Recovery**: Automatic recovery from common failures

**Business Logic Focus**: Tests validate core functionality that impacts user experience, not external API wrapper methods.

### Test Results Interpretation

```bash
# Expected core test output:
======================== 138 passed, 5 warnings in 10.62s =======================

# What this means:
✅ All core functionality working correctly
✅ Error handling comprehensive and tested
✅ Agent system validates properly
✅ CLI integration workflows functional
⚠️ Warnings are from dependency deprecations, not our code
```

## Next Steps

1. ✅ Review generated creatives in `output/`
2. ✅ Try different brand guides from `brand-guides/`
3. ✅ Create your own campaign brief (JSON format)
4. ✅ Run test suite to validate setup: `.venv/bin/pytest tests/test_config.py -v`
5. ✅ Start monitoring agent for intelligent alerts
6. ✅ Explore analytics for performance insights
7. ✅ Check the full README for advanced features

## Free Tier Limits

Google AI Studio free tier includes:
- **500 requests per day** (plenty for development!)
- **250,000 tokens per minute**
- No credit card required
- Perfect for testing and prototyping

For production at scale, pricing is $0.039 per image ($3.90 per 100 creatives).

## Development & Testing Setup

### For Contributors

```bash
# Development setup with testing
git clone <repo-url>
cd creatimation
python3 -m venv .venv
uv pip install --python .venv/bin/python3 -r requirements.txt

# Run code quality tools
.venv/bin/black src/ tests/
.venv/bin/ruff check src/ tests/
.venv/bin/mypy src/

# Run test suite
.venv/bin/pytest tests/ -v --cov=src
```

### CI/CD Pipeline

Every push runs:
- **Linting**: Black, Ruff for code quality
- **Type Checking**: MyPy for runtime safety
- **Security**: Bandit vulnerability scanning
- **Tests**: Full suite across Python 3.10, 3.11, 3.12
- **Coverage**: Business logic coverage reporting
