"""Fast, offline checks for selective tutorial recording."""

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from select_tutorial_workflows import select_workflows
from tutorial_workflows import fingerprint


class TutorialSelectionTests(unittest.TestCase):
    def test_source_changes_select_only_relevant_tutorial(self) -> None:
        with patch.object(Path, "is_file", return_value=True), patch.object(
            Path, "stat", return_value=SimpleNamespace(st_size=1)
        ):
            workflows = {
                "catalog": {
                    "guide_heading": "Browse catalog",
                    "stable_ids": ["species-search"],
                    "script": "async (page) => {}",
                    "source_paths": ["R/mod_species.R"],
                },
                "dashboard": {
                    "guide_heading": "View dashboard",
                    "stable_ids": ["dashboard-count"],
                    "script": "async (page) => {}",
                    "source_paths": ["R/mod_dashboard.R"],
                },
            }
            manifest = {"workflows": [
                {
                    "id": workflow_id,
                    "workflow_fingerprint": fingerprint(workflow_id, workflow),
                    "video": "artifacts/video.webm",
                    "poster": "artifacts/poster.png",
                }
                for workflow_id, workflow in workflows.items()
            ]}
            shared = ["R/app_ui.R", "inst/app/**"]

            self.assertEqual(select_workflows(workflows, manifest, shared, {"README.md"}), [])
            selected = select_workflows(workflows, manifest, shared, {"R/mod_species.R"})
            self.assertEqual([row["id"] for row in selected], ["catalog"])
            self.assertIn("source-changed", selected[0]["reasons"])
            self.assertEqual(
                {row["id"] for row in select_workflows(workflows, manifest, shared, {"R/app_ui.R"})},
                {"catalog", "dashboard"},
            )
            self.assertEqual(
                {row["id"] for row in select_workflows(workflows, manifest, shared, {"R/new_module.R"})},
                {"catalog", "dashboard"},
            )


if __name__ == "__main__":
    unittest.main()
