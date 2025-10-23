# Creatimation Quick Reference

Quick command reference for common workflows and demo scenarios.

---

## 🚀 Quick Start (30 seconds)

```bash
# 1. Setup & Validation
./creatimation config init --global
./creatimation config init
./creatimation config show

# 2. Generate campaign (3 parallel workers by default)
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json --parallel 8

# 3. Check results
./creatimation analytics summary --recent
```

---

## 🎤 Live Presentation Walkthrough

Optimized sequence for demos and presentations:

```bash
# 1. Show configuration (< 5 seconds)
./creatimation config show

# 2. Preview campaign structure - NO API CALLS (< 1 second)
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json --dry-run

# 3. Fast simulation - mock images for demo (< 5 seconds)
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json --simulate

# 4. Show analytics
./creatimation analytics summary --recent

# 5. Generate single asset - real API call (~ 10 seconds)
./creatimation generate asset \
  --product "CleanWave Original Liquid Detergent" \
  --ratio 1x1 \
  --variant base \
  --region US \
  --message "Spring into freshness"

# 6. Full campaign with high parallelization (< 2 minutes for 36 creatives)
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json --parallel 5

# 7. Final analytics summary
./creatimation analytics summary --recent
./creatimation cache stats
```

**Timing Guide:**
- Steps 1-4: ~10 seconds (no API calls)
- Step 5: ~10 seconds (1 API call)
- Step 6: ~90-120 seconds (36 creatives with regional contextualization)
- Step 7: ~2 seconds

**Total presentation time: ~3-4 minutes including explanations**

---

## 🤖 AI Agent System (CrewAI Multi-Agent)

Autonomous campaign monitoring and generation:

```bash
# Setup (one-time)
export OPENAI_API_KEY="your-openai-key-here"

# Single monitoring cycle - runs once and exits
python src/crewai_creative_agent.py --once

# Continuous monitoring - watches briefs/ directory
python src/crewai_creative_agent.py --watch

# Custom monitoring interval (default: 60 seconds)
python src/crewai_creative_agent.py --watch --interval 30

# Watch with immediate action on detected campaigns
python src/crewai_creative_agent.py --watch --interval 10
```

**What the Agent Does:**
- ✅ Monitors `briefs/` directory for new/modified campaigns
- ✅ Analyzes priority and complexity automatically
- ✅ Triggers generation commands: `./creatimation generate campaign briefs/[campaign].json`
- ✅ Tracks progress across regions and variants
- ✅ Sends business-focused alerts with recommendations
- ✅ Validates output quality and completeness

**Agent Workflow Example:**
1. Agent detects `CleanWaveSpring2025_Concise.json`
2. Analyzes: 2 products, 2 regions, 36 total creatives
3. Executes: `./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json`
4. Monitors: Real-time progress tracking
5. Alerts: "✅ Campaign complete - 36/36 creatives generated"

---

## 📋 Configuration

```bash
# Initialize workspace
./creatimation config init

# Initialize global config
./creatimation config init --global

# Show current configuration
./creatimation config show

# Validate all configurations
./creatimation config validate

# Set specific values
./creatimation config set generation.variants 5
./creatimation config set output.directory ./custom-output
```

---

## 🎨 Campaign Generation

### Basic Campaign

```bash
# Preview without generating (no API cost)
./creatimation generate campaign briefs/CleanWaveSpring2025.json --dry-run

# Generate full campaign (default: 3 parallel workers)
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json  --parallel 8

# Generate with brand guide
./creatimation generate campaign briefs/CleanWaveSpring2025.json \
  --brand-guide brand-guides/cleanwave_blue.yml --parallel 8
```

### Parallelization Control

```bash
# Default: 3 workers (2.5-3x faster)
./creatimation generate campaign briefs/CleanWaveSpring2025.json

# Faster: 5 workers (4-5x faster)
./creatimation generate campaign briefs/CleanWaveSpring2025.json --parallel 5

# Sequential: 1 worker (debugging)
./creatimation generate campaign briefs/CleanWaveSpring2025.json --parallel 1

# Aggressive: 8 workers (6-8x faster)
./creatimation generate campaign briefs/CleanWaveSpring2025.json --parallel 8
```

### Custom Campaign Options

```bash
# Specific regions only
./creatimation generate campaign briefs/CleanWaveSpring2025.json \
  --regions US,EMEA

# Specific aspect ratios
./creatimation generate campaign briefs/CleanWaveSpring2025.json \
  --ratios 1x1,16x9

# Specific number of variants
./creatimation generate campaign briefs/CleanWaveSpring2025.json \
  --variants 2

# Combine all options
./creatimation generate campaign briefs/CleanWaveSpring2025.json \
  --regions US \
  --ratios 16x9 \
  --variants 1 \
  --parallel 5
```

### Fast Simulation Mode

```bash
# Fast simulation for demos (mock images, ~3 seconds)
./creatimation generate campaign briefs/CleanWaveSpring2025.json --simulate
```

---

## 🎯 Single Asset Generation

```bash
# Generate one specific creative
./creatimation generate asset \
  --product "CleanWave Original Liquid Detergent" \
  --ratio 16x9 \
  --variant hero \
  --region US \
  --message "Spring Into Freshness"

# Generate with brand guide
./creatimation generate asset \
  --product "CleanWave Pods Spring Meadow" \
  --ratio 1x1 \
  --variant base \
  --region EMEA \
  --message "Choose CleanWave" \
  --brand-guide brand-guides/cleanwave_blue.yml

# Generate with detailed product description
./creatimation generate asset \
  --product "Package of CleanWave laundry detergent pods - colorful gel-filled capsules in clear packaging" \
  --ratio 1x1 \
  --variant base \
  --region US \
  --message "CleanWave Pods"
```

---

## 📦 Batch Processing

```bash
# Process all briefs in directory
./creatimation generate batch briefs/

# Process with pattern
./creatimation generate batch briefs/ --pattern "*spring*.json"

# Process with parallelization
./creatimation generate batch briefs/ --parallel 5

# Process with brand guide
./creatimation generate batch briefs/ \
  --brand-guide brand-guides/cleanwave_blue.yml \
  --parallel 3
```

---

## ✅ Validation

```bash
# Validate campaign brief (auto-detect)
./creatimation validate briefs/CleanWaveSpring2025_Concise.json

# Validate brand guide (auto-detect)
./creatimation validate brand-guides/cleanwave_blue.yml

# Validate workspace configuration
./creatimation config validate
```

---

## 📊 Analytics

```bash
# Show recent generation summary
./creatimation analytics summary --recent

# Show all-time summary
./creatimation analytics summary

# Show detailed command statistics
./creatimation analytics commands

# Show generation statistics
./creatimation analytics generation

# Clear analytics data
./creatimation analytics clear
```

---

## 💾 Cache Management

```bash
# Show cache statistics
./creatimation cache stats

# Inspect cached entries (products, backgrounds, etc.)
./creatimation cache inspect
./creatimation cache inspect --type products
./creatimation cache inspect --sort size --limit 10

# Optimize cache storage
./creatimation cache optimize

# Clean up old entries
./creatimation cache cleanup --older-than 30

# Clear all cache
./creatimation cache clear --confirm

# Clear specific cache type
./creatimation cache clear --type products

# Rebuild cache index
./creatimation cache rebuild

# Generate without using cache
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json --no-cache
```

---

## 🔄 Resume Interrupted Campaigns

```bash
# Start generation
./creatimation generate campaign large-campaign.json

# If interrupted (Ctrl+C), resume with:
./creatimation generate campaign large-campaign.json --resume
```

---

## 🎬 Demo Workflow (Full Example)

```bash
# 1. Initial setup & validation
./creatimation config init --global
./creatimation config show
./creatimation config validate

# 2. Preview campaign (no API cost)
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json --dry-run

# 3. Fast simulation for testing (mock images)
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json --simulate

# 4. Generate single asset (real API call)
./creatimation generate asset \
  --product "CleanWave Original Liquid Detergent" \
  --ratio 1x1 \
  --variant base \
  --region US \
  --message "Spring into freshness"

# 5. Generate full campaign with high parallelization
./creatimation generate campaign briefs/CleanWaveSpring2025_Concise.json --parallel 8

# 6. Check results
./creatimation analytics summary --recent
./creatimation cache stats

# 7. Batch process multiple campaigns (optional)
./creatimation generate batch briefs/ --parallel 5
```

---

## 🛠️ Workspace Management

```bash
# Initialize new workspace
./creatimation workspace init my-brand

# List available workspaces
./creatimation workspace list

# Show current workspace info
./creatimation workspace info

# Switch to different workspace
./creatimation workspace switch my-brand

# Clone existing workspace
./creatimation workspace clone my-brand new-brand

# Remove workspace
./creatimation workspace remove old-brand
```

---

## ⚡ Performance Tips

### Optimal Parallelization

```bash
# For small campaigns (1-2 products, 12-24 creatives)
--parallel 3  # Default, safe, 2.5-3x faster

# For medium campaigns (2-4 products, 36-72 creatives)
--parallel 5  # Faster, 4-5x speedup

# For large campaigns (4+ products, 72+ creatives)
--parallel 8  # Aggressive, 6-8x speedup
```

### Cost Optimization

```bash
# Use simulation for testing
./creatimation generate campaign brief.json --simulate

# Use dry-run to preview
./creatimation generate campaign brief.json --dry-run

# Cache products for reuse (automatic)
# First run: $1.48, Subsequent: $1.40 (5% savings)
```

---

## 📖 Common Patterns

### Test Single Product First

```bash
# 1. Generate minimal campaign (1 product, 1 region, 1 ratio)
./creatimation generate campaign briefs/test.json \
  --regions US \
  --ratios 1x1 \
  --variants 1

# 2. Review output before scaling up
# 3. Scale to full campaign
./creatimation generate campaign briefs/CleanWaveSpring2025.json
```

### Regional Expansion

```bash
# Start with US only
./creatimation generate campaign brief.json --regions US

# Add EMEA
./creatimation generate campaign brief.json --regions US,EMEA

# Scale to global (4 regions)
./creatimation generate campaign brief.json --regions US,EMEA,APAC,LATAM
```

### Iterative Refinement

```bash
# 1. Generate base variants
./creatimation generate campaign brief.json --variants 1

# 2. Review and refine brief
# 3. Regenerate with more variants
./creatimation generate campaign brief.json --variants 3 --no-cache
```

---

## 🔧 Troubleshooting

```bash
# Check configuration
./creatimation config show
./creatimation config validate

# Test API key
./creatimation generate campaign brief.json --dry-run

# Clear cache if issues
./creatimation cache clear --confirm

# Run with sequential mode for debugging
./creatimation generate campaign brief.json --parallel 1

# Check logs
tail -f logs/creatimation.log
```

---

## 🛡️ Code Quality & Testing

```bash
# Code formatting
.venv/bin/black src/ tests/ s3_migration_plan/

# Linting (auto-fix issues)
.venv/bin/ruff check src/ tests/ s3_migration_plan/ --fix

# Type checking
.venv/bin/mypy src/

# Security scanning (high/medium severity only)
.venv/bin/bandit -r src/ tests/ s3_migration_plan/ -ll

# Run all quality checks at once
.venv/bin/black src/ tests/ s3_migration_plan/ --check && \
.venv/bin/ruff check src/ tests/ s3_migration_plan/ && \
.venv/bin/bandit -r src/ tests/ s3_migration_plan/ -ll

# Run tests
.venv/bin/pytest tests/ -v

# Run tests with coverage
.venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing
```

**Current Status:**
- ✅ Black: 72 files formatted, 0 errors
- ✅ Ruff: All checks passed (42 issues fixed)
- ✅ Bandit: 0 high/medium security issues (23,648 lines scanned)
- ✅ Tests: 138 core tests passing

---

## 💡 Cost Calculator

### Single Campaign (36 creatives)
- First run: **$1.48** (2 products + 36 scenes)
- Cached run: **$1.40** (0 products + 36 scenes)
- Per creative: **$0.039**

### Global Campaign (72 creatives)
- First run: **$2.89** (2 products + 72 scenes)
- Cached run: **$2.81** (0 products + 72 scenes)
- Per creative: **$0.039**

### Time Estimates (36 creatives)
- Sequential (--parallel 1): **~6 minutes**
- Default (--parallel 3): **~3 minutes**
- Fast (--parallel 5): **~2 minutes**
- Aggressive (--parallel 8): **~1.5 minutes**

---

## 📝 Environment Variables

```bash
# Required
export GOOGLE_API_KEY="your-api-key-here"

# Optional
export CREATIMATION_CONFIG=".creatimation.yml"
export CREATIMATION_WORKSPACE="."
export NO_COLOR=false
```

---

## 🔗 Quick Links

- Full docs: [CLI_REFERENCE.md](CLI_REFERENCE.md)
- Setup guide: [SETUP.md](SETUP.md)
- Main README: [README.md](README.md)

---

**Version**: 2.3.0
**Last Updated**: October 2025 (Regional Contextualization + Code Quality)
