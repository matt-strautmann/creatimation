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
./creatimation generate all --brief briefs/SpringRefreshCampaign.json --dry-run

# Generate creatives (uses API key)
./creatimation generate all --brief briefs/SpringRefreshCampaign.json
```

### Option B: Direct Python

```bash
# Test with sample brief
.venv/bin/python3 -m src.cli generate all --brief briefs/SpringRefreshCampaign.json
```

## Expected Output

The pipeline generates **100 variants per campaign** (2 products × 10 ratios × 5 text variants):

```
output/{product}/{template}/{region}/{ratio}/
  ├── {product}_{template}_{region}_{ratio}_variant_1.jpg
  ├── {product}_{template}_{region}_{ratio}_variant_2.jpg
  ├── {product}_{template}_{region}_{ratio}_variant_3.jpg
  ├── {product}_{template}_{region}_{ratio}_variant_4.jpg
  ├── {product}_{template}_{region}_{ratio}_variant_5.jpg
  └── metadata.json
```

**10 Aspect Ratios Supported:**
- 1x1 (Square - Instagram/Facebook)
- 9x16 (Vertical - Stories/Reels)
- 16x9 (Horizontal - YouTube/Display)
- 4x5, 5x4, 3x4, 4x3, 2x3, 3x2, 21x9 (Various formats)

## Performance Expectations

With Gemini 2.5 Flash Image:
- **Speed**: ~3.2 seconds per creative
- **100 creatives**: ~8 minutes total
- **Cost**: FREE (under 500/day) or $3.90 in production

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
