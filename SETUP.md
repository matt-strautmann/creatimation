# Quick Setup Guide

## 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv .venv

# Install with uv (recommended)
uv pip install --python .venv/bin/python3 pillow openai python-dotenv pydantic requests
```

## 2. Configure API Key

```bash
# Copy example and add your key
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=your_key_here
```

## 3. Run Pipeline

```bash
# Test with sample brief
.venv/bin/python3 src/main.py --brief briefs/CleanHomeSpringPromo.json
```

## Expected Output

The pipeline will generate creatives in:
```
output/{product}/{template}/{region}/{ratio}/
```

Files use semantic naming:
```
{product}_{template}_{region}_{ratio}_creative.jpg
```

## Troubleshooting

**Missing OpenAI API key:**
Make sure `.env` file exists with valid `OPENAI_API_KEY`

**Module not found:**
Ensure all dependencies are installed: `uv pip list`

**Pipeline state error:**
Delete `.pipeline_state_*.json` files and retry
