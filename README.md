# Creatimation

> AI-powered creative automation pipeline for generating social ad campaigns at scale

Generate professional social ad creatives at scale using Google Gemini 2.5 Flash Image. Built for CPG brands that need hundreds of localized campaigns without the traditional time and cost overhead.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Gemini 2.5](https://img.shields.io/badge/Gemini-2.5%20Flash%20Image-blue.svg)](https://ai.google.dev/gemini-api/docs/image-generation)
[![Code Quality](https://img.shields.io/badge/code%20quality-production-green.svg)]()

## Overview

This pipeline transforms creative production from a 2-3 day manual process costing $500-2000 per campaign into an automated workflow that generates 36 regional variants in ~3 minutes for $1.48.

**Key Innovation**: Generate each product once with perfect consistency, then compose it into multiple scenes with different backgrounds and regional messaging.

### The Problem It Solves

Traditional creative production at CPG companies faces:
- 2-3 days per campaign with $500-2000 costs
- Inconsistent products across variants
- Manual regional localization overhead
- Creative teams stuck on repetitive work

### The Solution

- **36 regional variants in ~3 minutes** (with parallelization)
- **$1.48 per campaign** (99.7% cost reduction)
- **100% product consistency** across all variants
- **Automated regional localization** for global campaigns
- **Production-ready code quality** (138 tests, zero critical security issues)

## Quick Start

```bash
# 1. Install dependencies
python3 -m venv .venv
uv pip install --python .venv/bin/python3 -r requirements.txt

# 2. Get FREE Google API key (500/day limit)
# Visit: https://aistudio.google.com/app/apikey
echo "GOOGLE_API_KEY=your_key_here" > .env

# 3. Generate creatives (uses 3 parallel workers by default)
./creatimation generate campaign briefs/CleanWaveSpring2025.json

# 4. Check results
./creatimation analytics summary --recent
```

See [Setup Guide](docs/SETUP.md) for detailed installation and configuration.

## Key Features

### 🎨 Two-Step Generation Workflow
1. **Generate products once** - Clean product shots with neutral backgrounds
2. **Compose into scenes** - Fuse products into different backgrounds with regional messaging

This ensures 100% consistent products across all variants.

### 🌍 Regional Localization
- Supports up to 4 regions (US, LATAM, APAC, EMEA)
- Automatic messaging adaptation per region
- Same product, different cultural contexts

### ⚡ Smart Parallelization
- 3 parallel workers by default (2.7x speedup)
- Configurable 1-8+ workers for different use cases
- Conservative defaults for API rate limits

### 💾 Intelligent Caching
- Products cached and reused across campaigns
- ~5% cost savings on subsequent runs
- Automatic cache validation and management

### 🤖 AI-Driven Agent System
- Multi-agent collaboration with CrewAI
- Autonomous campaign monitoring and generation
- Real-time quality analysis and alerts

### 📊 Built-in Analytics
- Command usage and performance tracking
- Generation metrics and cache efficiency
- Comprehensive cost and time analysis

## Architecture

**Core Components:**
- Enhanced Brief Loader - Campaign brief processing and validation
- Gemini Image Generator - Unified product + scene generation
- Output Manager - Multi-format asset organization
- Cache Manager - Product caching and registry
- CLI System - Command interface with plugin architecture

**Advanced Features:**
- CrewAI Multi-Agent System - AI-driven automation
- Analytics Plugin - Performance and cost tracking
- S3 Integration - Cloud storage and CDN support
- Brand Guide System - Consistent styling across campaigns

See [Architecture Overview](docs/AGENTIC_SYSTEM_DESIGN.md) for detailed system design.

## Performance Metrics

Real-world results from CleanWave example campaign:

| Metric | Traditional | Creatimation | Improvement |
|--------|------------|--------------|-------------|
| Time | 2-3 days | ~3 minutes | 800x faster |
| Cost | $500-2000 | $1.48 | 99.7% reduction |
| Consistency | Variable | 100% | Perfect |
| API Cost vs DALL-E | $0.08/image | $0.039/image | 51% cheaper |

## Use Cases

This repository serves as a reference implementation for:

1. **AI-Powered Creative Automation** - Learn how to build scalable image generation pipelines
2. **Multi-Agent Systems** - See CrewAI in production with real tool integration
3. **CLI Design Patterns** - Study modular CLI architecture with plugins
4. **Production Python Projects** - Explore testing, code quality, and CI/CD patterns
5. **Cost-Effective AI Solutions** - Understand API optimization and caching strategies

## Documentation

- **[Quick Reference](docs/QUICK_REF.md)** - Common commands and workflows
- **[Setup Guide](docs/SETUP.md)** - Installation and configuration
- **[CLI Reference](docs/CLI_REFERENCE.md)** - Complete command documentation
- **[AI Agent System](docs/CREWAI_CAMPAIGN_MONITOR_AGENT.md)** - Multi-agent automation
- **[Architecture](docs/AGENTIC_SYSTEM_DESIGN.md)** - System design and patterns

## Campaign Examples

Minimum viable campaign brief:
```json
{
  "campaign_id": "test",
  "products": [{"name": "Product A"}],
  "creative_requirements": {
    "variant_types": ["base"]
  }
}
```

Full-featured example: See [CleanWaveSpring2025.json](briefs/CleanWaveSpring2025.json)

## Testing & Code Quality

Production-grade code quality:

```bash
# Code formatting
.venv/bin/black src/ tests/ s3_migration_plan/

# Linting
.venv/bin/ruff check src/ tests/ s3_migration_plan/ --fix

# Type checking
.venv/bin/mypy src/

# Security scanning
.venv/bin/bandit -r src/ tests/ s3_migration_plan/ -ll

# Full test suite (138 tests)
.venv/bin/pytest tests/ -v --cov=src
```

**Status**: ✅ All checks passing, zero high/medium security vulnerabilities across 23,648 lines of code

See [pyproject.toml](pyproject.toml) for complete configuration.

## Technology Stack

- **Python 3.10+** - Modern Python with type hints
- **Google Gemini 2.5 Flash** - Image generation API
- **CrewAI** - Multi-agent orchestration
- **Click + Rich** - Beautiful CLI interface
- **Pydantic** - Data validation and settings
- **Pytest** - Comprehensive test coverage

## Project Status

This is an **archived reference repository** showcasing production-ready patterns for:
- AI-powered creative automation
- Multi-agent system architecture
- Scalable CLI design
- Cost-effective API integration

Feel free to use this as a reference, learning resource, or foundation for your own projects.

## Cost Analysis

**First Campaign Run (36 creatives):**
- Product generation: $0.078
- Scene composition: $1.40
- **Total**: $1.48

**Subsequent Runs (cached products):**
- Scene composition: $1.40
- **Total**: $1.40 (5% savings)

**vs DALL-E:**
- 51% cheaper per image ($0.039 vs $0.08)
- 93% faster with parallelization

**vs Manual Process:**
- 99.7% cost reduction
- 800x faster

## Future Possibilities

Potential extensions explored in the codebase:
- Multi-language support beyond English
- Video generation (6-second social ads)
- Meta Ads API integration
- Adobe Firefly Custom Models
- Predictive analytics for creative performance

## Requirements

- Python 3.10+
- Google API key (free tier: 500 requests/day)
- ~2GB disk space for cache
- Optional: OpenAI API key for CrewAI agent system

For production deployment, consider PostgreSQL + Redis for state management and S3 for asset storage.

## License

MIT License - See [LICENSE](LICENSE) for details

## Author

Built by [Matt Strautmann](https://github.com/matt-strautmann)

**Version**: 2.2 (AI Agent System Completion)

---

**Note**: This is an archived reference repository. It demonstrates production-ready patterns but is not actively maintained. Feel free to fork and adapt for your needs.
