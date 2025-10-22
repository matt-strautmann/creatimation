# S3 Storage Integration Guide

Complete guide for using the S3 storage integration with the Creative Automation Pipeline.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Setup](#setup)
4. [Usage](#usage)
5. [Migration](#migration)
6. [CLI Reference](#cli-reference)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Overview

The S3 integration provides cloud storage capabilities for the cache manager system, enabling:

- **Semantic Asset Organization**: Intelligent folder structure based on asset metadata
- **Hybrid Storage**: Transparent local/cloud tier management
- **Batch Operations**: Parallel uploads with progress tracking
- **Cost Optimization**: Lifecycle policies and storage class management
- **CDN Integration**: CloudFront cache invalidation support
- **High Availability**: S3 versioning and multi-region support

## Architecture

### Storage Tiers

```
┌─────────────────────────────────────────────────┐
│              Application Layer                  │
│        (cache_manager_s3.py)                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐          ┌──────────────┐   │
│  │  Hot Tier    │          │  Cold Tier   │   │
│  │   (Local)    │◄────────►│    (S3)      │   │
│  │              │          │              │   │
│  │ • Fast access│          │ • Cost-eff.  │   │
│  │ • Frequently │          │ • Scalable   │   │
│  │   used assets│          │ • Versioned  │   │
│  └──────────────┘          └──────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

### S3 Folder Structure

```
s3://your-bucket/creative-assets/
├── products/
│   ├── transparent/
│   │   ├── dish_soap/
│   │   │   └── power-dish-soap/
│   │   │       └── product.png
│   │   └── laundry_detergent/
│   │       └── ultra-clean/
│   │           └── product.png
│   └── original/
│       └── {category}/{product-slug}/
├── backgrounds/
│   ├── scene/
│   │   └── {region}/{season}/
│   │       └── background.jpg
│   ├── gradient/
│   │   └── {style}/
│   └── solid/
│       └── {color}/
├── composites/
│   └── {campaign-id}/{product-slug}/{aspect-ratio}/
│       └── final.jpg
└── metadata/
    └── index.json
```

## Setup

### 1. Install Dependencies

```bash
pip install boto3 botocore
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Set up AWS credentials using one of these methods:

**Option A: AWS CLI Configuration**
```bash
aws configure
```

**Option B: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

**Option C: IAM Role** (recommended for EC2/ECS)
- Attach IAM role with S3 permissions to your instance

### 3. Configure S3 Settings

Create or update `.env` file:

```bash
# Required
S3_BUCKET_NAME=your-creative-assets-bucket
S3_REGION=us-east-1

# Optional
S3_STORAGE_CLASS=STANDARD
CLOUDFRONT_DISTRIBUTION_ID=your-distribution-id
S3_MAX_PARALLEL_UPLOADS=10
S3_ENABLE_VERSIONING=true
S3_ENABLE_ENCRYPTION=true
```

### 4. Create S3 Bucket

```bash
aws s3 mb s3://your-creative-assets-bucket --region us-east-1
```

### 5. Set Bucket Permissions

Example IAM policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:GetObjectMetadata",
        "s3:PutObjectTagging"
      ],
      "Resource": [
        "arn:aws:s3:::your-creative-assets-bucket",
        "arn:aws:s3:::your-creative-assets-bucket/*"
      ]
    }
  ]
}
```

## Usage

### Basic Operations

#### Upload Cache to S3

```bash
# Standard upload
python src/cli_s3.py upload --cache-dir cache

# Dry run (no actual upload)
python src/cli_s3.py upload --cache-dir cache --dry-run

# Custom bucket
python src/cli_s3.py upload --cache-dir cache --bucket my-bucket
```

#### List S3 Assets

```bash
# List all assets
python src/cli_s3.py list

# Filter by type
python src/cli_s3.py list --asset-type product

# Include metadata
python src/cli_s3.py list --metadata --max-results 50
```

#### Download Asset

```bash
# Download specific asset
python src/cli_s3.py download creative-assets/products/transparent/dish_soap/product.png

# Custom output path
python src/cli_s3.py download creative-assets/products/product.png --output ./local/product.png
```

#### Show Statistics

```bash
python src/cli_s3.py stats
```

### Python API

#### Using S3CacheManager

```python
from cache_manager_s3 import S3CacheManager
from cache_manager import SemanticMetadata, AssetType, ProductCategory

# Initialize with S3 support
cache_manager = S3CacheManager(
    cache_dir="cache",
    enable_s3=True,
    local_cache_size_limit_gb=10.0
)

# Register asset with automatic S3 upload
metadata = SemanticMetadata(
    asset_type=AssetType.PRODUCT_TRANSPARENT,
    product_category=ProductCategory.DISH_SOAP,
    region="US",
)

cache_manager.register_semantic_asset(
    cache_key="dish-soap-us-001",
    file_path="cache/products/dish_soap.png",
    metadata=metadata,
    campaign_id="spring_2025",
    upload_to_s3=True  # Automatically uploads to S3
)

# Get asset (downloads from S3 if not local)
asset_path = cache_manager.get_asset_path(
    cache_key="dish-soap-us-001",
    auto_download=True
)

# Get S3 statistics
stats = cache_manager.get_s3_stats()
print(f"S3 Assets: {stats['s3_assets']}")
print(f"Cache Hit Rate: {stats['cache_hit_rate']}%")
```

#### Using S3StorageManager Directly

```python
from s3_storage_manager import S3Config, S3StorageManager
from pathlib import Path

# Initialize
config = S3Config.from_env()
s3_manager = S3StorageManager(config=config)

# Upload single file
result = s3_manager.upload_file(
    local_path=Path("image.png"),
    s3_key="products/transparent/dish_soap/image.png",
    metadata={"type": "product", "category": "dish_soap"},
    tags={"campaign": "spring_2025"}
)

if result.success:
    print(f"Uploaded: {result.s3_key}")
    print(f"Size: {result.size_bytes / 1024:.1f} KB")
    print(f"Duration: {result.duration_seconds:.2f}s")

# Batch upload
file_mappings = [
    (Path("image1.png"), "path/image1.png", {"type": "product"}),
    (Path("image2.png"), "path/image2.png", {"type": "background"}),
]

results, progress = s3_manager.batch_upload(file_mappings)
print(f"Uploaded {progress.uploaded}/{progress.total_files} files")
print(f"Speed: {progress.upload_speed_mbps:.2f} MB/s")

# List objects
objects = s3_manager.list_objects(prefix="products/", max_keys=100)
for obj in objects:
    print(f"{obj['s3_key']}: {obj['size_bytes']} bytes")

# Download file
success = s3_manager.download_file(
    s3_key="products/image.png",
    local_path=Path("downloads/image.png")
)
```

## Migration

### One-Time Migration

Migrate existing local cache to S3:

```bash
# 1. Analyze cache
python src/cli_s3.py estimate --cache-dir cache

# 2. Test migration (dry run)
python src/cli_s3.py upload --cache-dir cache --dry-run

# 3. Execute migration
python src/cli_s3.py upload --cache-dir cache

# 4. Validate migration
python src/cli_s3.py validate --cache-dir cache
```

### Progressive Migration

For large caches, migrate incrementally:

```python
from s3_migration import S3MigrationManager
from cache_manager import CacheManager
from s3_storage_manager import S3Config, S3StorageManager

cache_manager = CacheManager(cache_dir="cache")
s3_manager = S3StorageManager(config=S3Config.from_env())
migration_manager = S3MigrationManager(cache_manager, s3_manager)

# Create plan
plan = migration_manager.create_migration_plan()
print(f"Total to migrate: {plan.total_size_mb:.2f} MB")

# Migrate with progress tracking
def progress_callback(progress):
    print(f"Progress: {progress.percent_complete:.1f}% "
          f"({progress.uploaded}/{progress.total_files} files)")

result = migration_manager.execute_migration(
    plan,
    progress_callback=progress_callback
)

print(f"Migration complete: {result.success_rate:.1f}% success")
```

## CLI Reference

### Upload Command

```bash
python src/cli_s3.py upload [OPTIONS]

Options:
  --cache-dir TEXT    Cache directory (default: cache)
  --bucket TEXT       S3 bucket name (overrides env)
  --prefix TEXT       S3 prefix (default: creative-assets)
  --dry-run           Simulate without uploading
```

### List Command

```bash
python src/cli_s3.py list [OPTIONS]

Options:
  --bucket TEXT       S3 bucket name
  --prefix TEXT       S3 prefix
  --asset-type TEXT   Filter by type (product/background/composite)
  --max-results INT   Maximum results (default: 100)
  --metadata          Include metadata
```

### Download Command

```bash
python src/cli_s3.py download S3_KEY [OPTIONS]

Arguments:
  S3_KEY             S3 key to download

Options:
  --output TEXT      Output path
  --bucket TEXT      S3 bucket name
```

### Validate Command

```bash
python src/cli_s3.py validate [OPTIONS]

Options:
  --cache-dir TEXT   Cache directory
  --bucket TEXT      S3 bucket name
  --prefix TEXT      S3 prefix
```

### Stats Command

```bash
python src/cli_s3.py stats [OPTIONS]

Options:
  --cache-dir TEXT   Cache directory
```

### Discover Command

```bash
python src/cli_s3.py discover [OPTIONS]

Options:
  --cache-dir TEXT   Cache directory
  --sync             Sync discovered assets to local index
```

### Tier Management Command

```bash
python src/cli_s3.py tier-manage [OPTIONS]

Options:
  --cache-dir TEXT    Cache directory
  --no-promote        Don't promote hot assets
  --no-demote         Don't demote cold assets
  --cold-days INT     Days to consider asset cold (default: 30)
```

### Estimate Command

```bash
python src/cli_s3.py estimate [OPTIONS]

Options:
  --cache-dir TEXT   Cache directory
  --bucket TEXT      S3 bucket name
  --prefix TEXT      S3 prefix
```

## Best Practices

### Cost Optimization

1. **Use Lifecycle Policies**
```python
s3_manager.setup_lifecycle_policy(
    transition_days=90,      # Move to Glacier after 90 days
    expiration_days=365,     # Delete after 1 year
    archive_storage_class="GLACIER"
)
```

2. **Enable Intelligent-Tiering**
```bash
# In .env
S3_STORAGE_CLASS=INTELLIGENT_TIERING
```

3. **Manage Cache Tiers**
```bash
# Keep hot cache local, demote cold to S3
python src/cli_s3.py tier-manage --cold-days 30
```

### Performance Optimization

1. **Parallel Uploads**
```bash
# In .env
S3_MAX_PARALLEL_UPLOADS=20  # Increase for faster uploads
```

2. **Use Presigned URLs**
```python
# For temporary public access without auth
url = s3_manager.get_presigned_url(
    s3_key="products/image.png",
    expiration=3600  # 1 hour
)
```

3. **CDN Integration**
```python
# Invalidate CloudFront cache after updates
s3_manager.invalidate_cloudfront_cache(
    paths=["/products/*", "/backgrounds/*"]
)
```

### Security Best Practices

1. **Enable Encryption**
```bash
# In .env
S3_ENABLE_ENCRYPTION=true
```

2. **Use IAM Roles** (not access keys)

3. **Enable Versioning**
```bash
# In .env
S3_ENABLE_VERSIONING=true
```

4. **Implement Bucket Policies**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::bucket/*",
      "Condition": {
        "Bool": {
          "aws:SecureTransport": "false"
        }
      }
    }
  ]
}
```

## Troubleshooting

### Common Issues

#### 1. Bucket Access Denied

**Error**: `Access denied to S3 bucket`

**Solutions**:
- Verify IAM permissions include `s3:PutObject`, `s3:GetObject`, `s3:ListBucket`
- Check bucket policy doesn't block your IP/role
- Ensure AWS credentials are correctly configured

#### 2. Slow Upload Speeds

**Error**: Uploads taking too long

**Solutions**:
- Increase parallel uploads: `S3_MAX_PARALLEL_UPLOADS=20`
- Check network bandwidth
- Consider using S3 Transfer Acceleration
- Use multi-region buckets closer to your location

#### 3. Cache Misses

**Error**: High S3 download rate, low cache hits

**Solutions**:
```python
# Promote frequently accessed assets
cache_manager.manage_cache_tiers(
    promote_hot_assets=True,
    cold_threshold_days=7  # More aggressive promotion
)
```

#### 4. Large Local Cache

**Error**: Local cache growing too large

**Solutions**:
```python
# Reduce local cache limit
cache_manager = S3CacheManager(
    cache_dir="cache",
    local_cache_size_limit_gb=5.0  # Reduce from 10GB
)

# Run tier management
cache_manager.manage_cache_tiers(demote_cold_assets=True)
```

#### 5. Migration Validation Failures

**Error**: Assets missing or size mismatches

**Solutions**:
```bash
# Re-run migration for failed files
python src/cli_s3.py upload --cache-dir cache

# Check S3 object metadata
python src/cli_s3.py list --metadata

# Verify file integrity
python src/cli_s3.py validate --cache-dir cache
```

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or via CLI:
```bash
export LOG_LEVEL=DEBUG
python src/cli_s3.py upload --cache-dir cache
```

### Support

For issues not covered here:
1. Check S3 CloudWatch metrics for throttling/errors
2. Review S3 access logs
3. Enable S3 server access logging
4. Check AWS Service Health Dashboard

## Advanced Topics

### Custom Storage Classes

```python
config = S3Config(
    bucket_name="bucket",
    storage_class="INTELLIGENT_TIERING"  # or GLACIER, DEEP_ARCHIVE
)
```

### Multi-Region Replication

Configure S3 replication for disaster recovery:

```bash
aws s3api put-bucket-replication \
  --bucket source-bucket \
  --replication-configuration file://replication.json
```

### S3 Event Notifications

Trigger Lambda on asset uploads:

```python
# Lambda function to process new assets
def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        # Process asset...
```

## Monitoring

### CloudWatch Metrics

Monitor these key metrics:
- `NumberOfObjects` - Total objects in bucket
- `BucketSizeBytes` - Total storage used
- `AllRequests` - Request rate
- `4xxErrors` - Client errors
- `5xxErrors` - Server errors

### Cost Tracking

```python
# Estimate monthly costs
stats = s3_manager.get_bucket_size()
storage_cost = stats['total_size_gb'] * 0.023  # $0.023/GB/month for Standard
print(f"Estimated monthly cost: ${storage_cost:.2f}")
```

### Performance Metrics

```python
stats = cache_manager.get_s3_stats()
print(f"Cache Hit Rate: {stats['cache_hit_rate']}%")
print(f"Total Downloads: {stats['downloads']}")
print(f"Total Uploads: {stats['uploads']}")
```
