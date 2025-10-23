# Creatimation CLI Reference

Complete reference for the `creatimation` command-line interface.

## Table of Contents

- [Overview](#overview)
- [Global Options](#global-options)
- [Commands](#commands)
  - [generate](#generate)
  - [validate](#validate)
  - [cache](#cache)
  - [analytics](#analytics)
  - [config](#config)
  - [workspace](#workspace)
- [Configuration](#configuration)
- [Brand Guides](#brand-guides)
- [Examples](#examples)

---

## Overview

The `creatimation` CLI provides a professional interface for generating creative assets, managing configuration, and inspecting pipeline state.

**Basic Usage**:
```bash
./creatimation COMMAND [OPTIONS]
```

**Get Help**:
```bash
./creatimation --help
./creatimation COMMAND --help
```

---

## Global Options

These options apply to all commands:

| Option | Description |
|--------|-------------|
| `--version` | Show version and exit |
| `-c, --config PATH` | Path to config file |
| `-w, --workspace PATH` | Path to workspace directory |
| `-p, --profile TEXT` | Configuration profile to use |
| `-v, --verbose` | Increase verbosity (use -vv for debug) |
| `-q, --quiet` | Suppress output except errors |
| `--no-color` | Disable colored output |
| `--format [auto|json|yaml|table]` | Output format |
| `-h, --help` | Show help message |

**Example**:
```bash
./creatimation --config custom-config.yml generate campaign campaign.json
```

---

## Commands

### `generate`

Generate creative assets (campaign, individual assets, or batch processing).

#### `generate campaign`

Generate complete campaign assets from a brief.

**Usage**:
```bash
./creatimation generate campaign BRIEF_PATH [OPTIONS]
```

**Arguments**:
- `BRIEF` - Campaign brief JSON file (required)

**Options**:
| Option | Description | Example |
|--------|-------------|------------|
| `-o, --output PATH` | Output directory (overrides config) | `--output ./custom-output` |
| `-n, --variants INT` | Number of variants per configuration | `--variants 5` |
| `-r, --ratios TEXT` | Comma-separated aspect ratios | `--ratios 1x1,16x9` |
| `--regions TEXT` | Comma-separated target regions | `--regions US,EMEA` |
| `-g, --brand-guide PATH` | Brand guide YAML file | `--brand-guide guides/brand.yml` |
| `-j, --parallel INT` | Number of parallel workers (default: 3) | `--parallel 5` |
| `--no-cache` | Disable cache, regenerate everything | |
| `--resume` | Resume from saved pipeline state | |
| `--dry-run` | Preview without execution | |
| `--simulate` | Fast simulation mode (mock images) | |

**Examples**:
```bash
# Basic campaign generation
./creatimation generate campaign briefs/CleanWaveSpring2025.json

# With brand guide
./creatimation generate campaign campaign.json --brand-guide brand-guides/minimal_blue.yml

# Override defaults
./creatimation generate campaign campaign.json --variants 5 --ratios 1x1,16x9

# Control parallelization (default: 3 workers)
./creatimation generate campaign campaign.json --parallel 5  # Faster with 5 workers
./creatimation generate campaign campaign.json --parallel 1  # Sequential (debugging)

# Dry run to preview
./creatimation generate campaign campaign.json --dry-run

# Fast simulation for demos
./creatimation generate campaign campaign.json --simulate

# Disable cache
./creatimation generate campaign campaign.json --no-cache

# Resume after interruption
./creatimation generate campaign campaign.json --resume
```

#### `generate asset`

Generate a single creative asset.

**Usage**:
```bash
./creatimation generate asset [OPTIONS]
```

#### `generate batch`

Batch process multiple campaign briefs.

**Usage**:
```bash
./creatimation generate batch PATTERN [OPTIONS]
```

**Options**:
| Option | Description | Example |
|--------|-------------|------------|
| `-j, --parallel INT` | Number of parallel workers per campaign (default: 3) | `--parallel 5` |
| `-g, --brand-guide PATH` | Brand guide YAML file (applies to all campaigns) | `--brand-guide guides/brand.yml` |
| `--no-cache` | Disable cache for all campaigns | |
| `--dry-run` | Preview all campaigns without execution | |

**Examples**:
```bash
# Process all briefs in directory
./creatimation generate batch "briefs/*.json"

# Process with parallelization
./creatimation generate batch "briefs/*.json" --parallel 5

# Process with brand guide
./creatimation generate batch "briefs/*.json" --brand-guide brand-guides/minimal.yml
```

---

### `validate`

Validate briefs, brand guides, and configuration files.

**Auto-detect Mode** (Recommended):
```bash
# Automatically detects file type by extension
./creatimation validate <file>           # Auto-detect .json (brief) or .yml/.yaml (brand guide)
./creatimation validate config           # Validate workspace config
./creatimation validate workspace        # Validate entire workspace
```

**Explicit Mode** (Advanced):
```bash
./creatimation validate brief <file>           # Explicitly validate as brief
./creatimation validate brand-guide <file>     # Explicitly validate as brand guide
```

#### `validate brief`

Validate campaign brief JSON file.

**Usage**:
```bash
./creatimation validate brief BRIEF_PATH [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--fix` | Attempt to auto-fix common issues |

**Checks**:
- Required fields (campaign_id, products)
- Data types and structure
- Product count
- Common issues

**Example**:
```bash
# Auto-detect (recommended)
./creatimation validate briefs/CleanWaveSpring2025.json
./creatimation validate campaign.json --fix

# Explicit subcommand
./creatimation validate brief briefs/CleanWaveSpring2025.json
./creatimation validate brief campaign.json --fix
```

#### `validate brand-guide`

Validate brand guide YAML file.

**Usage**:
```bash
./creatimation validate brand-guide GUIDE_PATH
```

**Checks**:
- YAML syntax
- Required schema fields
- Color format validation

**Example**:
```bash
# Auto-detect (recommended)
./creatimation validate brand-guides/minimal_blue.yml

# Explicit subcommand
./creatimation validate brand-guide brand-guides/minimal_blue.yml
```

---

### `cache`

Manage pipeline cache and optimization.

#### `cache stats`

Show cache statistics.

**Usage**:
```bash
./creatimation cache stats
```

**Output**:
```
                Cache Statistics
┌─────────────────┬─────────────────────────────┐
│ Metric          │ Value                       │
├─────────────────┼─────────────────────────────┤
│ Total Files     │ 24                          │
│ Total Size      │ 45.32 MB                    │
│ Cache Directory │ /path/to/cache              │
└─────────────────┴─────────────────────────────┘
```

#### `cache clear`

Clear pipeline cache entries.

**Usage**:
```bash
./creatimation cache clear [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--confirm` | Skip confirmation prompt |

**Example**:
```bash
# Clear all cache (with confirmation)
./creatimation cache clear

# Skip confirmation
./creatimation cache clear --confirm
```

---

### `analytics`

View usage analytics and performance metrics (provided by analytics plugin).

#### `analytics summary`

Show comprehensive usage overview and performance metrics.

**Usage**:
```bash
./creatimation analytics summary [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--recent` | Show most recent generation results instead of cumulative stats |
| `--period PERIOD` | Time period: day, week, month, all (default: week) |

**Examples**:
```bash
# View cumulative usage statistics
./creatimation analytics summary

# View latest generation results (recommended after each run)
./creatimation analytics summary --recent
```

**Output (--recent)**:
```
Recent Generation Results

             Most Recent Generation
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric          ┃ Value                      ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Campaign ID     │ cleanwave_spring_demo_2025 │
│ Total Creatives │ 36                         │
│ Cache Hits      │ 2                          │
│ Cache Misses    │ 0                          │
│ Processing Time │ 337.2s                     │
│ Total Cost      │ $1.40                      │
│ Status          │ ✅ Success                 │
│ Completed At    │ 2025-10-22 18:47:29        │
└─────────────────┴────────────────────────────┘
```

#### `analytics commands`

Show detailed command usage statistics.

**Usage**:
```bash
./creatimation analytics commands [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--sort METRIC` | Sort by: usage, duration, errors (default: usage) |
| `--limit N` | Limit number of commands shown (default: 10) |

**Example**:
```bash
./creatimation analytics commands --sort duration --limit 5
```

#### `analytics generation`

Show generation performance and cache efficiency metrics.

**Usage**:
```bash
./creatimation analytics generation [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--limit N` | Limit number of campaigns shown (default: 10) |

#### `analytics clear`

Clear all analytics data.

**Usage**:
```bash
./creatimation analytics clear [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--confirm` | Skip confirmation prompt |

**Example**:
```bash
./creatimation analytics clear --confirm
```

**Note**: Analytics data is stored locally in `~/.creatimation/analytics.json` with privacy-first design. No data is transmitted externally.

---

### `config`

Manage configuration and settings.

#### `config init`

Create configuration template.

**Usage**:
```bash
./creatimation config init [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `-g, --global` | Create global configuration (~/.creatimation/config.yml) |
| `-o, --output PATH` | Output path (default: .creatimation.yml) |

**Example**:
```bash
# Create workspace config
./creatimation config init

# Create global config
./creatimation config init --global

# Custom location
./creatimation config init --output custom-config.yml
```

#### `config show`

Show effective configuration after precedence chain applied.

**Usage**:
```bash
./creatimation config show
```

**Output**:
```
╭────────────────────────── Effective Configuration ──────────────────────────╮
│ Configuration Hierarchy (highest to lowest priority):                       │
│   1. Command line flags                                                     │
│   2. Environment variables (CREATIMATION_*)                                 │
│   3. Workspace configuration (.creatimation.yml) ✓                          │
│   4. Global user configuration (~/.creatimation/config.yml)                 │
│   5. Default values                                                         │
│                                                                             │
│ Project:                                                                    │
│   name: creative-automation                                                 │
│   output_dir: output/                                                       │
│   cache_dir: cache/                                                         │
│ ...                                                                         │
╰─────────────────────────────────────────────────────────────────────────────╯
```

#### `config list`

List all configuration values.

**Usage**:
```bash
./creatimation config list [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `-g, --global` | List global configuration |

#### `config get`

Get specific configuration value.

**Usage**:
```bash
./creatimation config get KEY
```

**Example**:
```bash
./creatimation config get generation.variants
./creatimation config get cache.enabled
```

#### `config set`

Set configuration value.

**Usage**:
```bash
./creatimation config set KEY VALUE [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `-g, --global` | Set in global configuration |

**Examples**:
```bash
# Set workspace config
./creatimation config set cache.enabled true
./creatimation config set output.quality 95

# Set global config
./creatimation config --global set auth.api_key abc123
```

#### `config unset`

Remove configuration value.

**Usage**:
```bash
./creatimation config unset KEY [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `-g, --global` | Remove from global configuration |

#### `config validate`

Validate configuration files.

**Usage**:
```bash
./creatimation config validate
```

**Checks**:
- YAML syntax
- Schema validation
- Value ranges
- Common configuration issues

#### `config reset`

Reset configuration to defaults.

**Usage**:
```bash
./creatimation config reset [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `-g, --global` | Reset global configuration |
| `--confirm` | Skip confirmation prompt |

---

### `workspace`

Manage creative automation workspaces.

#### `workspace init`

Create a new workspace with templates and structure.

**Usage**:
```bash
./creatimation workspace init [NAME] [OPTIONS]
```

**Options**:
| Option | Description |
|--------|-------------|
| `--template TEXT` | Workspace template: cpg, agency, basic (default: basic) |
| `--path PATH` | Custom workspace path |

**Examples**:
```bash
# Create workspace with default template
./creatimation workspace init

# Create CPG workspace
./creatimation workspace init my-brand --template cpg

# Custom path
./creatimation workspace init --path /path/to/workspace
```

**What it creates**:
```
workspace/
├── .creatimation.yml       # Workspace configuration
├── briefs/                 # Campaign brief templates
├── brand-guides/           # Brand guide templates
├── output/                 # Generated creatives
└── cache/                  # Product cache
```

#### `workspace list`

List available workspaces.

**Usage**:
```bash
./creatimation workspace list
```

---

### `completion`

Generate shell completion scripts.

**Usage**:
```bash
./creatimation completion [bash|zsh|fish]
```

**Examples**:
```bash
# Bash
./creatimation completion bash > /etc/bash_completion.d/creatimation

# Zsh
./creatimation completion zsh > ~/.zsh/completion/_creatimation

# Fish
./creatimation completion fish > ~/.config/fish/completions/creatimation.fish
```

---

## Configuration

### Configuration File (.creatimation.yml)

The `.creatimation.yml` file sets project defaults. Create it with:

```bash
./creatimation config init
```

**Full Schema**:
```yaml
# Project settings
project:
  name: creative-automation
  output_dir: output/
  cache_dir: cache/

# Generation settings
generation:
  aspect_ratios: [1x1, 9x16, 16x9]
  variants_per_ratio: 3
  brand_guide: null  # Optional path to YAML brand guide
  regions: [US]      # Default target regions

# Cache settings
cache:
  enabled: true
  ttl_days: 30
  max_size_mb: 1000

# Quality settings
quality:
  image_size: 1024
  compression: 85

# Google Gemini settings
gemini:
  model: gemini-2.0-flash-exp
  timeout: 120
  # api_key: ...  # Use .env instead
```

### Precedence Chain

Configuration is loaded with this precedence:

1. **CLI flags** (highest priority) - Explicit command-line arguments
2. **Environment variables** - `CREATIMATION_*` variables
3. **Workspace configuration** - `.creatimation.yml`
4. **Global configuration** - `~/.creatimation/config.yml`
5. **Default values** (lowest priority) - Built-in fallbacks

**Example**:
```bash
# .creatimation.yml has variants_per_ratio: 3
# CLI flag overrides to 5
./creatimation generate campaign campaign.json --variants 5
# Result: 5 variants (CLI wins)
```

---

## Brand Guides

### Brand Guide YAML

Brand guides define visual styling, colors, typography, and messaging.

**Example** (`brand-guides/minimal_blue.yml`):
```yaml
brand:
  name: Minimal Blue
  industry: Technology / SaaS
  target_audience: Tech-savvy professionals
  values:
    - Trust
    - Simplicity
    - Innovation

colors:
  primary: "#2E5CFF"
  secondary: "#F0F4FF"
  accent: "#1A3FCC"
  background: "#FFFFFF"
  text: "#1A1A1A"

typography:
  font_family: "Inter, Helvetica, Arial, sans-serif"
  headline_size: 48
  body_size: 16
  font_weight: "600"

visual:
  layout_style: "minimal"
  text_positioning: "top"
  scene_style: "clean studio"
  mood: "professional"

messaging:
  tone: "professional"
  max_headline_length: 40
  max_subheadline_length: 80
  avoid_words:
    - "cheap"
    - "discount"
  preferred_phrases:
    - "Enterprise-grade"
    - "Professional quality"
```

### Using Brand Guides

Apply brand guide to generation:

```bash
./creatimation generate campaign briefs/campaign.json \
  --brand-guide brand-guides/minimal_blue.yml
```

Or set in config file:

```yaml
generation:
  brand_guide: brand-guides/minimal_blue.yml
```

---

## Examples

### Basic Campaign Generation

```bash
# 1. Validate brief first (auto-detect)
./creatimation validate briefs/CleanWaveSpring2025.json

# 2. Dry run to preview
./creatimation generate campaign briefs/CleanWaveSpring2025.json --dry-run

# 3. Generate creatives (uses 3 parallel workers by default)
./creatimation generate campaign briefs/CleanWaveSpring2025.json

# Optional: control parallelization
./creatimation generate campaign briefs/CleanWaveSpring2025.json --parallel 5  # Faster
./creatimation generate campaign briefs/CleanWaveSpring2025.json --parallel 1  # Sequential

# 4. Check results
./creatimation analytics summary --recent
```

### Workspace Setup

```bash
# 1. Create workspace
./creatimation workspace init my-brand --template cpg

# 2. Configure
./creatimation config init
./creatimation config set generation.variants 5

# 3. Generate
./creatimation generate campaign briefs/campaign.json
```

### Brand Guide Workflow

```bash
# 1. Validate brand guide (auto-detect)
./creatimation validate brand-guides/minimal_blue.yml

# 2. Generate with brand guide
./creatimation generate campaign campaign.json \
  --brand-guide brand-guides/minimal_blue.yml
```

### Cache Management

```bash
# Check cache size
./creatimation cache stats

# Clear cache
./creatimation cache clear --confirm

# Generate without cache
./creatimation generate campaign campaign.json --no-cache
```

### Resume Interrupted Pipeline

```bash
# Start generation
./creatimation generate campaign large-campaign.json

# If interrupted (Ctrl+C), resume with:
./creatimation generate campaign large-campaign.json --resume
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Validation failed |
| 130 | User interrupted (Ctrl+C) |

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google Gemini API key (required) | None |
| `CREATIMATION_CONFIG` | Path to configuration file | `.creatimation.yml` |
| `CREATIMATION_WORKSPACE` | Path to workspace directory | `.` |
| `CREATIMATION_PROFILE` | Configuration profile to use | `default` |
| `NO_COLOR` | Disable colored output | `false` |

---

## Troubleshooting

### "Module not found" errors

Ensure you're using the creatimation script:
```bash
# Use the creatimation script
./creatimation --help  # ✓ Correct

# Not direct Python
python src/cli/main.py --help  # ✗ Wrong
```

### "Config file not found"

Create config file:
```bash
./creatimation config init
```

### "Google API key not set"

Add to `.env` file:
```bash
echo "GOOGLE_API_KEY=your-key-here" > .env
```

### "Cache directory not writable"

Check permissions:
```bash
chmod 755 cache/
```

---

## AI-Driven Agent Integration

The creatimation CLI works seamlessly with the intelligent CrewAI agent system:

```bash
# CrewAI Multi-Agent System (LLM-powered collaboration)
export OPENAI_API_KEY="your-key"
python src/crewai_creative_agent.py --once        # Single cycle
python src/crewai_creative_agent.py --watch       # Continuous monitoring
python src/crewai_creative_agent.py --watch --interval 30  # Custom interval
```

**Agent Features:**
- **Automatic Command Execution**: Agents trigger `.creatimation` commands intelligently
- **Dynamic Campaign Analysis**: Priority and complexity assessment without hardcoding
- **Real-time Progress Tracking**: Monitors generation across regions and formats
- **Business-Focused Alerts**: Context-aware notifications for stakeholders

## See Also

- [README.md](README.md) - Project overview
- [AGENTIC_SYSTEM_DESIGN.md](AGENTIC_SYSTEM_DESIGN.md) - Agent architecture (✅ Production Ready)
- [SETUP.md](SETUP.md) - Setup guide with agent configuration

---

**Version**: 2.2.0
**Last Updated**: October 2025 (Parallelization + Agent System)
