# S3 Integration Quick Start

Get started with S3 cloud storage for your creative automation pipeline in 5 minutes.

## Prerequisites

- AWS account with S3 access
- AWS credentials configured
- boto3 installed (`pip install boto3`)

## Step 1: Configure Environment

Add to your `.env` file:

```bash
# Required
S3_BUCKET_NAME=your-creative-assets-bucket

# Optional (with defaults)
S3_REGION=us-east-1
S3_STORAGE_CLASS=STANDARD
S3_MAX_PARALLEL_UPLOADS=10
```

## Step 2: Create S3 Bucket

```bash
# Via AWS CLI
aws s3 mb s3://your-creative-assets-bucket --region us-east-1

# Or via AWS Console
# 1. Go to S3 console
# 2. Click "Create bucket"
# 3. Enter bucket name
# 4. Select region
# 5. Keep default settings
# 6. Click "Create bucket"
```

## Step 3: Upload Existing Cache

```bash
# Dry run (preview what will be uploaded)
python src/cli_s3.py upload --cache-dir cache --dry-run

# Upload to S3
python src/cli_s3.py upload --cache-dir cache

# Validate migration
python src/cli_s3.py validate --cache-dir cache
```

## Step 4: Use S3 in Your Code

```python
from cache_manager_s3 import S3CacheManager
from cache_manager import SemanticMetadata, AssetType, ProductCategory

# Initialize with S3 support (auto-detects from .env)
cache_manager = S3CacheManager(
    cache_dir="cache",
    enable_s3=True,
    local_cache_size_limit_gb=10.0
)

# Register asset (automatically uploads to S3)
metadata = SemanticMetadata(
    asset_type=AssetType.PRODUCT_TRANSPARENT,
    product_category=ProductCategory.DISH_SOAP,
    region="US",
)

cache_manager.register_semantic_asset(
    cache_key="dish-soap-001",
    file_path="cache/products/dish_soap.png",
    metadata=metadata,
    campaign_id="spring_2025",
    upload_to_s3=True  # Uploads to S3
)

# Get asset (downloads from S3 if not local)
asset_path = cache_manager.get_asset_path(
    cache_key="dish-soap-001",
    auto_download=True
)

print(f"Asset available at: {asset_path}")
```

## Step 5: Monitor and Manage

```bash
# View statistics
python src/cli_s3.py stats

# List assets in S3
python src/cli_s3.py list --asset-type product

# Manage cache tiers (hot local, cold S3)
python src/cli_s3.py tier-manage --cold-days 30
```

## Common Operations

### Upload Single File

```python
from s3_storage_manager import S3Config, S3StorageManager
from pathlib import Path

config = S3Config.from_env()
s3_manager = S3StorageManager(config=config)

result = s3_manager.upload_file(
    local_path=Path("image.png"),
    s3_key="products/transparent/dish_soap/image.png",
    metadata={"type": "product", "category": "dish_soap"}
)

if result.success:
    print(f"Uploaded: {result.s3_key}")
```

### Download Asset

```bash
python src/cli_s3.py download creative-assets/products/image.png --output ./local/image.png
```

### List Assets

```bash
# List all
python src/cli_s3.py list

# List with metadata
python src/cli_s3.py list --metadata --max-results 50

# Filter by type
python src/cli_s3.py list --asset-type product
```

## S3 Folder Structure

Your assets are organized semantically in S3:

```
s3://your-bucket/creative-assets/
├── products/
│   ├── transparent/
│   │   └── {category}/{product-slug}/product.png
│   └── original/
│       └── {category}/{product-slug}/product.png
├── backgrounds/
│   └── scene/{region}/{season}/background.jpg
├── composites/
│   └── {campaign-id}/{product-slug}/{aspect-ratio}/final.jpg
└── metadata/
    └── index.json
```

## Cost Optimization

### Enable Lifecycle Policies

```python
from s3_storage_manager import S3Config, S3StorageManager

config = S3Config.from_env()
s3_manager = S3StorageManager(config=config)

# Move to Glacier after 90 days
s3_manager.setup_lifecycle_policy(
    transition_days=90,
    archive_storage_class="GLACIER"
)
```

### Use Intelligent-Tiering

In `.env`:
```bash
S3_STORAGE_CLASS=INTELLIGENT_TIERING
```

### Manage Cache Tiers

```bash
# Keep frequently used assets local
# Move cold assets to S3-only
python src/cli_s3.py tier-manage --cold-days 30
```

## Troubleshooting

### AWS Credentials Not Found

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

### Bucket Access Denied

1. Check IAM permissions include:
   - `s3:PutObject`
   - `s3:GetObject`
   - `s3:ListBucket`
   - `s3:DeleteObject`

2. Verify bucket name in `.env` is correct

### Slow Upload Speeds

```bash
# Increase parallel uploads in .env
S3_MAX_PARALLEL_UPLOADS=20
```

## Next Steps

- Read [full documentation](./S3_INTEGRATION.md)
- Configure [CloudFront CDN](./S3_INTEGRATION.md#cdn-integration)
- Setup [lifecycle policies](./S3_INTEGRATION.md#cost-optimization)
- Implement [disaster recovery](./S3_INTEGRATION.md#multi-region-replication)

## Estimate Costs

```bash
# Get cost estimate before uploading
python src/cli_s3.py estimate --cache-dir cache
```

Example output:
```
Migration Plan:
  Total assets: 150
  Total size: 2.35 GB

Estimated S3 Costs:
  Standard Storage:
    Monthly: $0.05
    Yearly: $0.65

  Intelligent-Tiering:
    Monthly: $0.03
    Yearly: $0.35
```

## Resources

- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Full Integration Guide](./S3_INTEGRATION.md)
