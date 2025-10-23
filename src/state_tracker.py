#!/usr/bin/env python3
"""
State Tracker - Pipeline state management for error recovery and --resume

Tracks pipeline execution state, enabling graceful error recovery and
resume capability after failures or interruptions.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class StateTracker:
    """Manages pipeline state for error recovery and resume capability"""

    def __init__(self, campaign_id: str, state_dir: str = "."):
        """
        Initialize state tracker.

        Args:
            campaign_id: Campaign identifier for state file naming
            state_dir: Directory to store state files
        """
        self.campaign_id = campaign_id
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)

        # State file path: .pipeline_state_{campaign_id}.json
        self.state_file = self.state_dir / f".pipeline_state_{campaign_id}.json"

        self.state = self._load_state()
        logger.info(f"StateTracker initialized for campaign: {campaign_id}")

    def _load_state(self) -> dict[Any, Any]:
        """Load state from disk if exists"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state: dict[Any, Any] = json.load(f)
                logger.info(f"Loaded existing state from {self.state_file}")
                return state
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

        # Initialize new state
        return {
            "campaign_id": self.campaign_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "steps_completed": {
                "brief_loaded": False,
                "products_generated": False,
                "scenes_generated": False,
                "backgrounds_removed": False,
                "composited": False,
                "text_overlays_added": False,
                "output_saved": False,
            },
            "products_state": {},  # Per-product state tracking
            "errors": [],  # Error history
            "warnings": [],  # Warning history
        }

    def _save_state(self) -> None:
        """Save current state to disk"""
        try:
            self.state["updated_at"] = datetime.now().isoformat()

            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)

            logger.debug(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def mark_step_complete(self, step: str) -> None:
        """
        Mark a pipeline step as completed.

        Args:
            step: Step name (brief_loaded, products_generated, etc.)
        """
        if step in self.state["steps_completed"]:
            self.state["steps_completed"][step] = True
            self._save_state()
            logger.info(f"✓ Step completed: {step}")
        else:
            logger.warning(f"Unknown step: {step}")

    def is_step_complete(self, step: str) -> bool:
        """
        Check if a step is completed.

        Args:
            step: Step name

        Returns:
            True if step is completed
        """
        return bool(self.state["steps_completed"].get(step, False))

    def get_next_step(self) -> str | None:
        """
        Determine the next step to execute.

        Returns:
            Next step name or None if complete
        """
        steps_order = [
            "brief_loaded",
            "products_generated",
            "scenes_generated",
            "backgrounds_removed",
            "composited",
            "text_overlays_added",
            "output_saved",
        ]

        for step in steps_order:
            if not self.is_step_complete(step):
                return step

        return None  # All steps complete

    def update_product_state(self, product_slug: str, updates: dict) -> None:
        """
        Update state for a specific product.

        Args:
            product_slug: Product slug identifier
            updates: Dict with state updates
        """
        if product_slug not in self.state["products_state"]:
            self.state["products_state"][product_slug] = {
                "product_slug": product_slug,
                "created_at": datetime.now().isoformat(),
            }

        self.state["products_state"][product_slug].update(updates)
        self.state["products_state"][product_slug]["updated_at"] = datetime.now().isoformat()
        self._save_state()

    def get_product_state(self, product_slug: str) -> dict[Any, Any] | None:
        """
        Get state for a specific product.

        Args:
            product_slug: Product slug identifier

        Returns:
            Product state dict or None
        """
        result = self.state["products_state"].get(product_slug)
        return result if result is None else dict(result)

    def log_error(self, error_message: str, context: dict | None = None) -> None:
        """
        Log an error to state history.

        Args:
            error_message: Error message
            context: Optional context dict
        """
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": error_message,
            "context": context or {},
        }

        self.state["errors"].append(error_entry)
        self._save_state()
        logger.error(f"Error logged: {error_message}")

    def log_warning(self, warning_message: str, context: dict | None = None) -> None:
        """
        Log a warning to state history.

        Args:
            warning_message: Warning message
            context: Optional context dict
        """
        warning_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": warning_message,
            "context": context or {},
        }

        self.state["warnings"].append(warning_entry)
        self._save_state()
        logger.warning(f"Warning logged: {warning_message}")

    def get_summary(self) -> dict:
        """
        Get pipeline state summary.

        Returns:
            Dict with state summary
        """
        completed_steps = sum(1 for v in self.state["steps_completed"].values() if v)
        total_steps = len(self.state["steps_completed"])

        return {
            "campaign_id": self.campaign_id,
            "progress": f"{completed_steps}/{total_steps} steps",
            "progress_percentage": int((completed_steps / total_steps) * 100),
            "next_step": self.get_next_step(),
            "products_tracked": len(self.state["products_state"]),
            "errors_count": len(self.state["errors"]),
            "warnings_count": len(self.state["warnings"]),
            "created_at": self.state["created_at"],
            "updated_at": self.state["updated_at"],
        }

    def clear_state(self) -> None:
        """Clear saved state file"""
        if self.state_file.exists():
            self.state_file.unlink()
            logger.info(f"Cleared state file: {self.state_file}")

        # Reinitialize state
        self.state = self._load_state()

    def can_resume(self) -> bool:
        """
        Check if pipeline can be resumed.

        Returns:
            True if there's state to resume from
        """
        return self.state_file.exists() and not self.is_step_complete("output_saved")


# ============================================================================
# CLI INTERFACE FOR TESTING
# ============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    parser = argparse.ArgumentParser(description="State tracker utilities")
    parser.add_argument("campaign_id", help="Campaign ID")
    parser.add_argument("--summary", action="store_true", help="Show state summary")
    parser.add_argument("--clear", action="store_true", help="Clear state")
    parser.add_argument("--mark-complete", help="Mark step as complete")

    args = parser.parse_args()

    tracker = StateTracker(args.campaign_id)

    if args.summary:
        summary = tracker.get_summary()
        print("\n📊 Pipeline State Summary:")
        print(f"  Campaign: {summary['campaign_id']}")
        print(f"  Progress: {summary['progress']} ({summary['progress_percentage']}%)")
        print(f"  Next step: {summary['next_step'] or 'Complete'}")
        print(f"  Products tracked: {summary['products_tracked']}")
        print(f"  Errors: {summary['errors_count']}")
        print(f"  Warnings: {summary['warnings_count']}")
        print(f"  Last updated: {summary['updated_at']}")

    elif args.clear:
        tracker.clear_state()
        print(f"✓ State cleared for campaign: {args.campaign_id}")

    elif args.mark_complete:
        tracker.mark_step_complete(args.mark_complete)
        print(f"✓ Marked {args.mark_complete} as complete")

    else:
        print("Use --summary, --clear, or --mark-complete")
