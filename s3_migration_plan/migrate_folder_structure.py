#!/usr/bin/env python3
"""
Folder Structure Migration Script

Migrates from current structure to optimized semantic structure:

Current:  output/{product}/{template}/{region}/{ratio}/
         output-examples/{ratio}/

Optimized: output/campaigns/{campaign_id}/outputs/{region}/{ratio}/
          output/library/products/{product_slug}/transparent/
          output/library/backgrounds/seasonal/{season}/{region}/{ratio}/
"""
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class FolderStructureMigrator:
    """Migrates folder structure from current to optimized semantic organization."""

    def __init__(self, current_output_dir: str = "output", backup_suffix: str = None):
        """
        Initialize migrator.

        Args:
            current_output_dir: Current output directory
            backup_suffix: Optional suffix for backup directory
        """
        self.current_dir = Path(current_output_dir)
        self.backup_suffix = backup_suffix or f"backup_{int(time.time())}"
        self.backup_dir = Path(f"{current_output_dir}_{self.backup_suffix}")

        # New structure directories
        self.campaigns_dir = self.current_dir / "campaigns"
        self.library_dir = self.current_dir / "library"
        self.temp_dir = self.current_dir / "temp"

        logger.info(f"Initialized migrator for: {self.current_dir}")

    def analyze_current_structure(self) -> Dict:
        """
        Analyze current folder structure and identify migration needs.

        Returns:
            Analysis report with current structure info
        """
        analysis = {
            "current_structure": "unknown",
            "total_files": 0,
            "total_size_bytes": 0,
            "products": [],
            "templates": [],
            "regions": [],
            "ratios": [],
            "migration_plan": [],
            "warnings": []
        }

        if not self.current_dir.exists():
            analysis["warnings"].append(f"Output directory does not exist: {self.current_dir}")
            return analysis

        # Check for current structure patterns
        has_product_dirs = False
        has_example_dirs = False
        has_direct_ratio_dirs = False

        for item in self.current_dir.iterdir():
            if not item.is_dir():
                continue

            if item.name == "output-examples":
                has_example_dirs = True
                analysis = self._analyze_examples_structure(item, analysis)
            elif item.name in ["campaigns", "library", "cache", "temp"]:
                # Already optimized
                analysis["current_structure"] = "optimized"
                analysis["warnings"].append("Structure appears already optimized")
                return analysis
            elif item.name in ["1x1", "9x16", "16x9", "4x5", "5x4", "4x3", "3x4", "2x3", "3x2", "21x9"]:
                # Direct aspect ratio directories (like output-examples structure)
                has_direct_ratio_dirs = True
                analysis = self._analyze_direct_ratio_structure(item, analysis)
            else:
                # Check if it follows product/{template}/{region}/{ratio} pattern
                template_dirs = [d for d in item.iterdir() if d.is_dir()]
                if template_dirs:
                    for template_dir in template_dirs:
                        region_dirs = [d for d in template_dir.iterdir() if d.is_dir()]
                        if region_dirs:
                            for region_dir in region_dirs:
                                ratio_dirs = [d for d in region_dir.iterdir() if d.is_dir()]
                                if ratio_dirs:
                                    has_product_dirs = True
                                    analysis = self._analyze_product_structure(item, template_dir, region_dir, analysis)

        # Determine structure type
        if has_direct_ratio_dirs:
            analysis["current_structure"] = "direct_ratio"
        elif has_example_dirs and not has_product_dirs:
            analysis["current_structure"] = "examples_only"
        elif has_product_dirs and not has_example_dirs:
            analysis["current_structure"] = "product_based"
        elif has_product_dirs and has_example_dirs:
            analysis["current_structure"] = "mixed"
        else:
            analysis["current_structure"] = "unknown"
            analysis["warnings"].append("Could not identify current structure pattern")

        # Remove duplicates
        analysis["products"] = list(set(analysis["products"]))
        analysis["templates"] = list(set(analysis["templates"]))
        analysis["regions"] = list(set(analysis["regions"]))
        analysis["ratios"] = list(set(analysis["ratios"]))

        return analysis

    def _analyze_examples_structure(self, examples_dir: Path, analysis: Dict) -> Dict:
        """Analyze output-examples structure."""
        for ratio_dir in examples_dir.iterdir():
            if not ratio_dir.is_dir():
                continue

            analysis["ratios"].append(ratio_dir.name)

            for file in ratio_dir.glob("*"):
                if file.suffix.lower() in ['.jpg', '.png']:
                    analysis["total_files"] += 1
                    analysis["total_size_bytes"] += file.stat().st_size

                    # Plan migration to library
                    analysis["migration_plan"].append({
                        "source": str(file),
                        "destination": f"library/backgrounds/neutral/{ratio_dir.name}/{file.name}",
                        "type": "example_background"
                    })

        return analysis

    def _analyze_direct_ratio_structure(self, ratio_dir: Path, analysis: Dict) -> Dict:
        """Analyze direct aspect ratio structure (like output-examples)."""
        analysis["ratios"].append(ratio_dir.name)

        for file in ratio_dir.glob("*"):
            if file.suffix.lower() in ['.jpg', '.png']:
                analysis["total_files"] += 1
                analysis["total_size_bytes"] += file.stat().st_size

                # Plan migration to library neutral backgrounds
                analysis["migration_plan"].append({
                    "source": str(file),
                    "destination": f"library/backgrounds/neutral/{ratio_dir.name}/{file.name}",
                    "type": "neutral_background",
                    "ratio": ratio_dir.name
                })

        return analysis

    def _analyze_product_structure(self, product_dir: Path, template_dir: Path, region_dir: Path, analysis: Dict) -> Dict:
        """Analyze product/{template}/{region}/{ratio} structure."""
        analysis["products"].append(product_dir.name)
        analysis["templates"].append(template_dir.name)
        analysis["regions"].append(region_dir.name)

        for ratio_dir in region_dir.iterdir():
            if not ratio_dir.is_dir():
                continue

            analysis["ratios"].append(ratio_dir.name)

            for file in ratio_dir.glob("*"):
                if file.suffix.lower() in ['.jpg', '.png']:
                    analysis["total_files"] += 1
                    analysis["total_size_bytes"] += file.stat().st_size

                    # Determine migration destination based on file pattern
                    if "transparent" in file.name or "no_bg" in file.name:
                        # Product transparent -> library
                        dest = f"library/products/{product_dir.name}/transparent/{file.name}"
                        migration_type = "product_transparent"
                    elif "background" in file.name or "bg" in file.name:
                        # Background -> library
                        dest = f"library/backgrounds/category/{product_dir.name}/{region_dir.name}/{ratio_dir.name}/{file.name}"
                        migration_type = "product_background"
                    else:
                        # Final creative -> campaign (generate campaign ID)
                        campaign_id = f"{product_dir.name}-{template_dir.name}-campaign"
                        dest = f"campaigns/{campaign_id}/outputs/{region_dir.name}/{ratio_dir.name}/{file.name}"
                        migration_type = "campaign_creative"

                    analysis["migration_plan"].append({
                        "source": str(file),
                        "destination": dest,
                        "type": migration_type,
                        "product": product_dir.name,
                        "template": template_dir.name,
                        "region": region_dir.name,
                        "ratio": ratio_dir.name
                    })

        return analysis

    def create_backup(self) -> bool:
        """
        Create backup of current structure.

        Returns:
            True if backup successful
        """
        try:
            if self.backup_dir.exists():
                logger.warning(f"Backup directory already exists: {self.backup_dir}")
                return False

            logger.info(f"Creating backup: {self.current_dir} -> {self.backup_dir}")
            shutil.copytree(self.current_dir, self.backup_dir)
            logger.info(f"✓ Backup created successfully: {self.backup_dir}")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def migrate(self, dry_run: bool = False, create_backup: bool = True) -> Dict:
        """
        Perform migration from current to optimized structure.

        Args:
            dry_run: If True, only simulate migration
            create_backup: If True, create backup before migration

        Returns:
            Migration result report
        """
        logger.info(f"Starting migration (dry_run={dry_run})")

        # Analyze current structure
        analysis = self.analyze_current_structure()

        if analysis["current_structure"] == "optimized":
            return {
                "success": True,
                "message": "Structure already optimized",
                "analysis": analysis
            }

        if analysis["current_structure"] == "unknown":
            return {
                "success": False,
                "message": "Could not identify current structure",
                "analysis": analysis
            }

        # Create backup if requested
        if create_backup and not dry_run:
            if not self.create_backup():
                return {
                    "success": False,
                    "message": "Failed to create backup",
                    "analysis": analysis
                }

        # Create new directory structure
        if not dry_run:
            self._create_optimized_structure()

        # Execute migration plan
        migration_results = {
            "moved_files": 0,
            "failed_moves": 0,
            "created_directories": 0,
            "errors": []
        }

        for plan_item in analysis["migration_plan"]:
            try:
                source_path = Path(plan_item["source"])
                dest_path = self.current_dir / plan_item["destination"]

                if dry_run:
                    logger.info(f"[DRY RUN] Would move: {source_path} -> {dest_path}")
                    migration_results["moved_files"] += 1
                else:
                    # Create destination directory
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Move file
                    shutil.move(str(source_path), str(dest_path))
                    logger.debug(f"Moved: {source_path} -> {dest_path}")
                    migration_results["moved_files"] += 1

                    # Create metadata file
                    self._create_migration_metadata(dest_path, plan_item)

            except Exception as e:
                error_msg = f"Failed to move {plan_item['source']}: {e}"
                logger.error(error_msg)
                migration_results["errors"].append(error_msg)
                migration_results["failed_moves"] += 1

        # Clean up empty directories
        if not dry_run:
            self._cleanup_empty_directories()

        return {
            "success": migration_results["failed_moves"] == 0,
            "message": f"Migration completed: {migration_results['moved_files']} files moved, {migration_results['failed_moves']} failed",
            "analysis": analysis,
            "migration_results": migration_results,
            "backup_location": str(self.backup_dir) if create_backup else None
        }

    def _create_optimized_structure(self):
        """Create optimized directory structure."""
        directories = [
            self.campaigns_dir,
            self.library_dir / "products",
            self.library_dir / "backgrounds" / "seasonal",
            self.library_dir / "backgrounds" / "category",
            self.library_dir / "backgrounds" / "neutral",
            self.library_dir / "brand-elements" / "logos",
            self.library_dir / "brand-elements" / "patterns",
            self.current_dir / "cache",
            self.temp_dir
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created directory: {directory}")

    def _create_migration_metadata(self, dest_path: Path, plan_item: Dict):
        """Create metadata file for migrated asset."""
        metadata = {
            "migrated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "original_path": plan_item["source"],
            "migration_type": plan_item["type"],
            "product": plan_item.get("product"),
            "template": plan_item.get("template"),
            "region": plan_item.get("region"),
            "ratio": plan_item.get("ratio")
        }

        metadata_path = dest_path.parent / "metadata.json"
        if metadata_path.exists():
            # Load existing metadata and merge
            try:
                with open(metadata_path) as f:
                    existing_metadata = json.load(f)
                metadata = {**existing_metadata, **metadata}
            except Exception as e:
                logger.warning(f"Failed to merge existing metadata: {e}")

        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def _cleanup_empty_directories(self):
        """Remove empty directories after migration."""
        def remove_empty_dirs(path: Path):
            if not path.exists() or not path.is_dir():
                return

            # Remove empty subdirectories first
            for child in path.iterdir():
                if child.is_dir():
                    remove_empty_dirs(child)

            # Remove this directory if it's empty
            try:
                if not any(path.iterdir()):
                    path.rmdir()
                    logger.debug(f"Removed empty directory: {path}")
            except OSError:
                pass  # Directory not empty or other issue

        # Clean up old structure
        for item in self.current_dir.iterdir():
            if item.is_dir() and item.name not in ["campaigns", "library", "cache", "temp"]:
                remove_empty_dirs(item)

    def validate_migration(self) -> Dict:
        """
        Validate migration by checking if optimized structure exists and is functional.

        Returns:
            Validation report
        """
        validation = {
            "structure_valid": True,
            "required_directories": [],
            "missing_directories": [],
            "file_counts": {},
            "warnings": []
        }

        required_dirs = [
            self.campaigns_dir,
            self.library_dir / "products",
            self.library_dir / "backgrounds",
            self.library_dir / "brand-elements"
        ]

        for req_dir in required_dirs:
            validation["required_directories"].append(str(req_dir))
            if not req_dir.exists():
                validation["missing_directories"].append(str(req_dir))
                validation["structure_valid"] = False

        # Count files in each section
        if self.campaigns_dir.exists():
            validation["file_counts"]["campaigns"] = len(list(self.campaigns_dir.rglob("*.jpg"))) + len(list(self.campaigns_dir.rglob("*.png")))

        if (self.library_dir / "products").exists():
            validation["file_counts"]["library_products"] = len(list((self.library_dir / "products").rglob("*.jpg"))) + len(list((self.library_dir / "products").rglob("*.png")))

        if (self.library_dir / "backgrounds").exists():
            validation["file_counts"]["library_backgrounds"] = len(list((self.library_dir / "backgrounds").rglob("*.jpg"))) + len(list((self.library_dir / "backgrounds").rglob("*.png")))

        return validation


def main():
    """CLI interface for migration script."""
    import argparse

    parser = argparse.ArgumentParser(description="Migrate folder structure to optimized semantic organization")
    parser.add_argument("--output-dir", default="output", help="Output directory to migrate")
    parser.add_argument("--analyze", action="store_true", help="Analyze current structure only")
    parser.add_argument("--migrate", action="store_true", help="Perform migration")
    parser.add_argument("--dry-run", action="store_true", help="Simulate migration without moving files")
    parser.add_argument("--no-backup", action="store_true", help="Skip backup creation")
    parser.add_argument("--validate", action="store_true", help="Validate migrated structure")

    args = parser.parse_args()

    migrator = FolderStructureMigrator(args.output_dir)

    if args.analyze:
        print("\n📊 Analyzing Current Structure...")
        analysis = migrator.analyze_current_structure()

        print(f"Current structure: {analysis['current_structure']}")
        print(f"Total files: {analysis['total_files']}")
        print(f"Total size: {analysis['total_size_bytes'] / (1024*1024):.1f} MB")
        print(f"Products: {len(analysis['products'])} ({', '.join(analysis['products'][:5])}{'...' if len(analysis['products']) > 5 else ''})")
        print(f"Templates: {', '.join(analysis['templates'])}")
        print(f"Regions: {', '.join(analysis['regions'])}")
        print(f"Ratios: {', '.join(analysis['ratios'])}")
        print(f"Migration plan: {len(analysis['migration_plan'])} items")

        if analysis['warnings']:
            print("\n⚠️  Warnings:")
            for warning in analysis['warnings']:
                print(f"  - {warning}")

    elif args.migrate:
        print(f"\n🚀 {'Simulating' if args.dry_run else 'Performing'} Migration...")
        result = migrator.migrate(dry_run=args.dry_run, create_backup=not args.no_backup)

        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")

        if result.get('backup_location'):
            print(f"Backup created: {result['backup_location']}")

        if result.get('migration_results'):
            mr = result['migration_results']
            print(f"Files moved: {mr['moved_files']}")
            print(f"Failed moves: {mr['failed_moves']}")

            if mr['errors']:
                print("\n❌ Errors:")
                for error in mr['errors'][:5]:
                    print(f"  - {error}")

    elif args.validate:
        print("\n✅ Validating Migrated Structure...")
        validation = migrator.validate_migration()

        print(f"Structure valid: {validation['structure_valid']}")
        print(f"File counts: {validation['file_counts']}")

        if validation['missing_directories']:
            print("\n❌ Missing directories:")
            for missing in validation['missing_directories']:
                print(f"  - {missing}")

        if validation['warnings']:
            print("\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")

    else:
        print("Use --analyze, --migrate, or --validate")


if __name__ == "__main__":
    main()