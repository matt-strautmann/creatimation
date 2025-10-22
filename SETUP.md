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

## 3. Configure API Key

```bash
# Copy example and add your key
cp .env.example .env

# Edit .env and add your Google API key
echo "GOOGLE_API_KEY=your_key_here" > .env
```

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

The pipeline generates **18 regional variants** (2 regions × 1 product × 3 ratios × 3 true variants):

```
output/{product-slug}/hero-product/{region}/{ratio}/
  ├── {product}_{layout}_{region}_{ratio}_base_creative.jpg         # Base colors/typography
  ├── {product}_{layout}_{region}_{ratio}_color_shift_creative.jpg  # Accent palette (#FFB900)
  ├── {product}_{layout}_{region}_{ratio}_text_style_creative.jpg   # Typography variation
  ├── metadata_base.json          # Variant-specific metadata (no overwrite!)
  ├── metadata_color_shift.json
  └── metadata_text_style.json

# Multi-Region Structure (4 markets)
output/cleanwave-original-liquid-detergent/hero-product/
  ├── us/      # "Try CleanWave Today"
  ├── latam/   # "Prueba CleanWave Hoy"
  ├── apac/    # "Experience CleanWave Now"
  └── emea/    # "Discover CleanWave Today"

cache/products/
  ├── cleanwave-original-liquid-detergent.png  # 962KB - Reused 36 times!
  ├── cleanwave-pods-spring-meadow.png         # Reused 36 times!
  └── ...

cache/index.json           # Product registry with campaigns_used tracking
```

**Global Scale Structure:**
- **4 Regions**: US, LATAM, APAC, EMEA (market-specific CTAs)
- **3 Default Aspect Ratios**: 1x1 (Instagram), 9x16 (Stories), 16x9 (YouTube)
- **7 Optional Ratios**: 4x5, 5x4, 3x4, 4x3, 2x3, 3x2, 21x9
- **3 True Variants**: base, color_shift (accent #FFB900), text_style
- **Product Consistency**: 100% identical across all 72 regional variants
- **Regional Localization**: Market-specific calls-to-action
- **Bug Fixes**: color_scheme properly applied, separate metadata files per variant

## Performance Expectations

With Gemini 2.5 Flash Image + Product Caching + Multi-Region:
- **Speed**: ~9 seconds per creative (with cached products)
- **18 regional creatives**: ~3 minutes total (2 regions × 9 variants each)
- **Cost**:
  - First run: $0.74 (1 product + 18 fusions = 19 calls)
  - Subsequent runs: $0.70 (0 products + 18 fusions) - products cached!
- **Cache Efficiency**: **95% cost reduction** (1 product vs 18 variants = 17 calls eliminated)
- **Cache Hit Rate**: 100% (product reused 18 times: 2 regions × 3 ratios × 3 variants)
- **ROI**: 99.8% cheaper than manual ($0.74 vs $500-2000)

## Semantic Asset Organization

The pipeline now uses an **S3-ready semantic structure** for optimal asset management:

### Local Structure
```
output/                                  # Campaign outputs
├── {product-slug}/
│   └── {layout}/{region}/{ratio}/
│       └── *_{variant}.jpg

cache/                                   # Intelligent caching
├── products/{product-slug}.png          # Reusable product assets
└── index.json                           # Product registry + metadata
```

### Key Benefits
- ✅ **Product-centric**: Easy discovery of all creatives for a product
- ✅ **Semantic paths**: Region/ratio organization for intelligent reuse
- ✅ **Cache-first**: 30-50% cost savings through product reuse
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
./creatimation generate all --brief briefs/SpringRefreshCampaign.json --dry-run
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
  "total_variants_expected": 18,
  "total_variants_generated": 12,
  "insufficient_variants": ["CleanWave Pods"],
  "recommendations": [
    "Re-run generation to complete all variant types",
    "Check generation logs for errors"
  ]
}
```

### Start Monitoring
```bash
# Install and activate environment
uv run python src/creative_automation_agent.py --watch

# Alternative: Direct execution
.venv/bin/python3 src/creative_automation_agent.py --watch

# Monitor specific directory
uv run python src/creative_automation_agent.py --briefs-dir custom_briefs --watch

# Single monitoring cycle (for testing)
uv run python src/creative_automation_agent.py --once

# Verbose logging
uv run python src/creative_automation_agent.py --watch --verbose
```

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
Variants: 12/18
Issues: 1 products have < 9 variants (3 ratios × 3 variant types)
Recommendations: Re-run generation to complete all variant types (base, color_shift, text_style)
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

### Analytics Commands
```bash
# Comprehensive usage overview
./creatimation analytics summary

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

## Next Steps

1. ✅ Review generated creatives in `output/`
2. ✅ Try different brand guides from `brand-guides/`
3. ✅ Create your own campaign brief (JSON format)
4. ✅ Start monitoring agent for intelligent alerts
5. ✅ Explore analytics for performance insights
6. ✅ Check the full README for advanced features

## Free Tier Limits

Google AI Studio free tier includes:
- **500 requests per day** (plenty for development!)
- **250,000 tokens per minute**
- No credit card required
- Perfect for testing and prototyping

For production at scale, pricing is $0.039 per image ($3.90 per 100 creatives).
