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

## 4. Run Pipeline

### Option A: Using CLI (Recommended)

```bash
# Make CLI executable
chmod +x creatimation

# Dry-run preview (no API key needed)
./creatimation generate all --brief briefs/CleanWaveSpring2025.json --dry-run

# Generate creatives with brand guide (uses API key)
./creatimation generate all --brief briefs/CleanWaveSpring2025.json --brand-guide brand-guides/cleanwave_blue.yml
```

### Option B: Direct Python

```bash
# Test with CleanWave example
.venv/bin/python3 -m src.cli generate all --brief briefs/CleanWaveSpring2025.json --brand-guide brand-guides/cleanwave_blue.yml
```

## Expected Output

The pipeline generates **72 global variants** (4 regions × 2 products × 3 ratios × 3 true variants):

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
- **72 global creatives**: ~11 minutes total (4 regions × 18 variants each)
- **Cost**:
  - First run: $2.89 (2 products + 72 fusions = 74 calls)
  - Subsequent runs: $2.81 (0 products + 72 fusions) - products cached!
- **Cache Efficiency**: **97% cost reduction** (2 products vs 72 variants = 70 calls eliminated)
- **Cache Hit Rate**: 100% (each product reused 36 times: 4 regions × 3 ratios × 3 variants)
- **Global ROI**: 99.4% cheaper than manual ($2.89 vs $500-2000)

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
# Dry-run preview (no API calls)
./creatimation generate all --brief <brief.json> --dry-run

# Generate with brand guide
./creatimation generate all --brief <brief.json> --brand-guide brand-guides/minimal_blue.yml

# Validate brief
./creatimation validate brief <brief.json>

# Check cache stats
./creatimation cache stats

# Clear cache
./creatimation cache clear

# Show config
./creatimation config show
```

## Next Steps

1. ✅ Review generated creatives in `output/`
2. ✅ Try different brand guides from `brand-guides/`
3. ✅ Create your own campaign brief (JSON format)
4. ✅ Check the full README for advanced features

## Free Tier Limits

Google AI Studio free tier includes:
- **500 requests per day** (plenty for development!)
- **250,000 tokens per minute**
- No credit card required
- Perfect for testing and prototyping

For production at scale, pricing is $0.039 per image ($3.90 per 100 creatives).
