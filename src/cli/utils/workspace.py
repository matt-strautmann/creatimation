"""
Workspace management utilities.

GitHub spec-kit inspired workspace patterns with project isolation,
configuration management, and collaborative features.
"""
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List

from .output import console, error_console, print_warning, print_error


class WorkspaceManager:
    """
    Manages workspace configuration and structure.

    Provides methods for workspace discovery, configuration management,
    and directory structure maintenance.
    """

    def __init__(self, workspace_path: Path):
        """
        Initialize workspace manager.

        Args:
            workspace_path: Path to the workspace directory
        """
        self.workspace_path = Path(workspace_path).resolve()
        self._config_cache = None
        self._config_file = self.workspace_path / ".creatimation.yml"

    def exists(self) -> bool:
        """Check if workspace exists and is valid."""
        return (
            self.workspace_path.exists() and
            self.workspace_path.is_dir() and
            self._config_file.exists()
        )

    def get_config(self) -> Dict[str, Any]:
        """
        Get workspace configuration.

        Returns:
            Configuration dictionary
        """
        if self._config_cache is None:
            self._load_config()

        return self._config_cache or {}

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation like 'project.name')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        config = self.get_config()
        keys = key.split('.')

        current = config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default

        return current

    def set_config_value(self, key: str, value: Any) -> None:
        """
        Set a configuration value using dot notation.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        config = self.get_config()
        keys = key.split('.')

        # Navigate to the parent dictionary
        current = config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value

        # Save configuration
        self._save_config(config)
        self._config_cache = config

    def validate_structure(self) -> Dict[str, Any]:
        """
        Validate workspace directory structure.

        Returns:
            Validation result with errors, warnings, and recommendations
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "recommendations": []
        }

        # Check required directories
        required_dirs = {
            "briefs": "Campaign brief JSON files",
            "brand-guides": "Brand guide YAML files",
            "output": "Generated creative assets",
            "cache": "Cached assets and metadata"
        }

        for dir_name, description in required_dirs.items():
            dir_path = self.workspace_path / dir_name
            if not dir_path.exists():
                result["warnings"].append(f"Missing {dir_name}/ directory ({description})")
                result["recommendations"].append(f"Create {dir_name}/ directory")

        # Check configuration file
        if not self._config_file.exists():
            result["errors"].append("Missing .creatimation.yml configuration file")
            result["valid"] = False
        else:
            # Validate configuration content
            try:
                config = self.get_config()
                if not config:
                    result["warnings"].append("Configuration file is empty")

                # Check required configuration sections
                required_sections = ["project", "generation", "output"]
                for section in required_sections:
                    if section not in config:
                        result["warnings"].append(f"Missing '{section}' section in configuration")

            except Exception as e:
                result["errors"].append(f"Configuration file is invalid: {e}")
                result["valid"] = False

        # Check for content
        self._check_workspace_content(result)

        return result

    def create_structure(self) -> None:
        """Create workspace directory structure."""
        # Create main workspace directory
        self.workspace_path.mkdir(parents=True, exist_ok=True)

        # Create standard directories
        directories = [
            "briefs",
            "brand-guides",
            "output",
            "cache",
            "templates",
            "assets"
        ]

        for directory in directories:
            (self.workspace_path / directory).mkdir(exist_ok=True)

        console.print(f"[green]✓[/green] Created workspace structure at {self.workspace_path}")

    def list_briefs(self) -> List[Dict[str, Any]]:
        """
        List all campaign briefs in the workspace.

        Returns:
            List of brief information dictionaries
        """
        briefs = []
        briefs_dir = self.workspace_path / "briefs"

        if not briefs_dir.exists():
            return briefs

        for brief_file in briefs_dir.glob("*.json"):
            try:
                with open(brief_file) as f:
                    brief_data = json.load(f)

                brief_info = {
                    "file": brief_file.name,
                    "path": brief_file,
                    "campaign_id": brief_data.get("campaign_id", "Unknown"),
                    "products": brief_data.get("products", []),
                    "regions": brief_data.get("target_regions", []),
                    "valid": True
                }

                briefs.append(brief_info)

            except Exception as e:
                briefs.append({
                    "file": brief_file.name,
                    "path": brief_file,
                    "campaign_id": "Error",
                    "products": [],
                    "regions": [],
                    "valid": False,
                    "error": str(e)
                })

        return briefs

    def list_brand_guides(self) -> List[Dict[str, Any]]:
        """
        List all brand guides in the workspace.

        Returns:
            List of brand guide information dictionaries
        """
        guides = []
        guides_dir = self.workspace_path / "brand-guides"

        if not guides_dir.exists():
            return guides

        for guide_file in guides_dir.glob("*.yml"):
            try:
                with open(guide_file) as f:
                    guide_data = yaml.safe_load(f)

                guide_info = {
                    "file": guide_file.name,
                    "path": guide_file,
                    "brand_name": guide_data.get("brand", {}).get("name", "Unknown"),
                    "industry": guide_data.get("brand", {}).get("industry"),
                    "valid": True
                }

                guides.append(guide_info)

            except Exception as e:
                guides.append({
                    "file": guide_file.name,
                    "path": guide_file,
                    "brand_name": "Error",
                    "industry": None,
                    "valid": False,
                    "error": str(e)
                })

        return guides

    def get_output_summary(self) -> Dict[str, Any]:
        """
        Get summary of generated outputs.

        Returns:
            Output summary with counts and sizes
        """
        summary = {
            "total_files": 0,
            "total_size_bytes": 0,
            "campaigns": {},
            "file_types": {}
        }

        output_dir = self.workspace_path / "output"
        if not output_dir.exists():
            return summary

        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                summary["total_files"] += 1

                try:
                    file_size = file_path.stat().st_size
                    summary["total_size_bytes"] += file_size

                    # Categorize by file extension
                    ext = file_path.suffix.lower()
                    if ext not in summary["file_types"]:
                        summary["file_types"][ext] = {"count": 0, "size": 0}
                    summary["file_types"][ext]["count"] += 1
                    summary["file_types"][ext]["size"] += file_size

                    # Try to identify campaign from path structure
                    path_parts = file_path.relative_to(output_dir).parts
                    if path_parts:
                        campaign = path_parts[0]
                        if campaign not in summary["campaigns"]:
                            summary["campaigns"][campaign] = {"count": 0, "size": 0}
                        summary["campaigns"][campaign]["count"] += 1
                        summary["campaigns"][campaign]["size"] += file_size

                except OSError:
                    pass  # Skip files we can't access

        return summary

    def clean_outputs(self, campaign_id: Optional[str] = None) -> int:
        """
        Clean generated outputs.

        Args:
            campaign_id: Optional campaign ID to clean (None for all)

        Returns:
            Number of files cleaned
        """
        output_dir = self.workspace_path / "output"
        if not output_dir.exists():
            return 0

        cleaned_count = 0

        if campaign_id:
            # Clean specific campaign
            campaign_dir = output_dir / campaign_id
            if campaign_dir.exists():
                import shutil
                shutil.rmtree(campaign_dir)
                cleaned_count = 1
        else:
            # Clean all outputs
            for item in output_dir.iterdir():
                if item.is_dir():
                    import shutil
                    shutil.rmtree(item)
                    cleaned_count += 1
                elif item.is_file():
                    item.unlink()
                    cleaned_count += 1

        return cleaned_count

    def export_workspace_info(self) -> Dict[str, Any]:
        """
        Export workspace information for sharing or backup.

        Returns:
            Complete workspace information dictionary
        """
        return {
            "workspace_path": str(self.workspace_path),
            "config": self.get_config(),
            "structure_validation": self.validate_structure(),
            "briefs": self.list_briefs(),
            "brand_guides": self.list_brand_guides(),
            "output_summary": self.get_output_summary(),
            "created_at": self._get_creation_time()
        }

    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self._config_file.exists():
            self._config_cache = {}
            return

        try:
            with open(self._config_file, 'r') as f:
                self._config_cache = yaml.safe_load(f) or {}
        except Exception as e:
            print_error(f"Failed to load workspace configuration: {e}")
            self._config_cache = {}

    def _save_config(self, config: Dict[str, Any]) -> None:
        """Save configuration to file."""
        try:
            with open(self._config_file, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print_error(f"Failed to save workspace configuration: {e}")

    def _check_workspace_content(self, result: Dict[str, Any]) -> None:
        """Check workspace content and add recommendations."""
        # Check for briefs
        briefs = self.list_briefs()
        if not briefs:
            result["recommendations"].append("Add campaign briefs to briefs/ directory")
        elif len(briefs) == 1:
            result["recommendations"].append("Consider adding more campaign briefs for variety")

        # Check for brand guides
        guides = self.list_brand_guides()
        if not guides:
            result["recommendations"].append("Add brand guides to brand-guides/ directory")

        # Check for outputs
        output_summary = self.get_output_summary()
        if output_summary["total_files"] == 0:
            result["recommendations"].append("Run generation to create output assets")

    def _get_creation_time(self) -> Optional[str]:
        """Get workspace creation time."""
        try:
            stat = self.workspace_path.stat()
            import time
            return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime))
        except:
            return None


def discover_workspaces(search_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Discover workspaces in a directory tree.

    Args:
        search_path: Path to search (defaults to current directory)

    Returns:
        List of workspace information dictionaries
    """
    if search_path is None:
        search_path = Path.cwd()

    workspaces = []

    # Search current directory and immediate subdirectories
    for item in search_path.iterdir():
        if item.is_dir():
            config_file = item / ".creatimation.yml"
            if config_file.exists():
                workspace_info = {
                    "name": item.name,
                    "path": item,
                    "config_file": config_file,
                    "valid": True
                }

                # Try to load basic info
                try:
                    manager = WorkspaceManager(item)
                    config = manager.get_config()
                    workspace_info["project_name"] = config.get("project", {}).get("name")
                    workspace_info["brand"] = config.get("project", {}).get("brand")

                    # Validate structure
                    validation = manager.validate_structure()
                    workspace_info["valid"] = validation["valid"]
                    workspace_info["warnings"] = len(validation["warnings"])
                    workspace_info["errors"] = len(validation["errors"])

                except Exception as e:
                    workspace_info["valid"] = False
                    workspace_info["error"] = str(e)

                workspaces.append(workspace_info)

    return workspaces


def find_workspace_root(start_path: Optional[Path] = None) -> Optional[Path]:
    """
    Find workspace root by walking up the directory tree.

    Args:
        start_path: Starting path (defaults to current directory)

    Returns:
        Path to workspace root or None if not found
    """
    if start_path is None:
        start_path = Path.cwd()

    current = Path(start_path).resolve()

    while current != current.parent:
        config_file = current / ".creatimation.yml"
        if config_file.exists():
            return current
        current = current.parent

    return None


def create_workspace_from_template(
    workspace_path: Path,
    template_name: str,
    **template_vars
) -> WorkspaceManager:
    """
    Create a workspace from a template.

    Args:
        workspace_path: Path for the new workspace
        template_name: Template identifier
        **template_vars: Variables for template substitution

    Returns:
        WorkspaceManager for the new workspace
    """
    # Create workspace manager
    manager = WorkspaceManager(workspace_path)

    # Create directory structure
    manager.create_structure()

    # Generate configuration from template
    config = _generate_config_from_template(template_name, **template_vars)

    # Save configuration
    manager._save_config(config)

    # Create template files
    _create_template_files(workspace_path, template_name, **template_vars)

    return manager


def validate_workspace_name(name: str) -> bool:
    """
    Validate workspace name according to conventions.

    Args:
        name: Proposed workspace name

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False

    # Check length
    if len(name) < 2 or len(name) > 50:
        return False

    # Check characters (alphanumeric, hyphens, underscores)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False

    # Check for reserved names
    reserved_names = {
        'con', 'prn', 'aux', 'nul',
        'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
        'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
    }

    if name.lower() in reserved_names:
        return False

    return True


def _generate_config_from_template(template_name: str, **vars) -> Dict[str, Any]:
    """Generate configuration from template."""
    base_config = {
        "project": {
            "name": vars.get("name", "My Project"),
            "workspace": vars.get("workspace_name", "my-workspace")
        },
        "generation": {
            "default_variants": 3,
            "aspect_ratios": ["1x1", "9x16", "16x9"]
        },
        "cache": {
            "enabled": True,
            "directory": "cache"
        },
        "output": {
            "directory": "output",
            "semantic_structure": True
        }
    }

    # Apply template-specific modifications
    if template_name == "cpg":
        base_config["generation"]["aspect_ratios"] = ["1x1", "9x16", "16x9", "4x5", "5x4"]
        base_config["generation"]["default_variants"] = 5
        base_config["project"]["industry"] = "consumer-packaged-goods"

    elif template_name == "fashion":
        base_config["generation"]["aspect_ratios"] = ["9x16", "4x5", "1x1"]
        base_config["project"]["industry"] = "fashion"

    elif template_name == "tech":
        base_config["generation"]["aspect_ratios"] = ["16x9", "1x1", "9x16"]
        base_config["project"]["industry"] = "technology"

    # Apply variable substitutions
    if "brand" in vars:
        base_config["project"]["brand"] = vars["brand"]

    if "industry" in vars:
        base_config["project"]["industry"] = vars["industry"]

    return base_config


def _create_template_files(workspace_path: Path, template_name: str, **vars):
    """Create template files for the workspace."""
    # Create sample brief
    brief_content = _generate_sample_brief(template_name, **vars)
    brief_file = workspace_path / "briefs" / "sample-campaign.json"
    brief_file.write_text(brief_content)

    # Create sample brand guide
    guide_content = _generate_sample_brand_guide(template_name, **vars)
    guide_file = workspace_path / "brand-guides" / "brand-guide.yml"
    guide_file.write_text(guide_content)


def _generate_sample_brief(template_name: str, **vars) -> str:
    """Generate a sample campaign brief."""
    brand_name = vars.get("brand", "Sample Brand")

    brief = {
        "campaign_id": "sample_campaign",
        "products": ["Product A", "Product B"],
        "target_regions": ["US"],
        "campaign_message": f"Quality you can trust from {brand_name}",
        "creative_requirements": {
            "aspect_ratios": ["1x1", "9x16", "16x9"],
            "variant_types": ["base"],
            "variant_themes": {
                "base": "clean and professional"
            }
        },
        "enhanced_context": {
            "setting": "modern clean environment",
            "mood": "professional and trustworthy",
            "brand_colors": {
                "primary": "#1565C0"
            }
        }
    }

    return json.dumps(brief, indent=2)


def _generate_sample_brand_guide(template_name: str, **vars) -> str:
    """Generate a sample brand guide."""
    brand_name = vars.get("brand", "Sample Brand")

    guide = {
        "brand": {
            "name": brand_name,
            "tagline": "Quality and innovation",
            "industry": vars.get("industry", "consumer goods")
        },
        "colors": {
            "primary": "#1565C0",
            "secondary": "#42A5F5",
            "accent": "#FFA726"
        },
        "visual": {
            "layout_style": "clean and modern",
            "logo_placement": "top-left",
            "font_style": "sans-serif"
        },
        "messaging": {
            "tone": "professional yet approachable",
            "voice": "confident and helpful",
            "keywords": ["quality", "innovation", "trust"]
        }
    }

    return yaml.dump(guide, default_flow_style=False)