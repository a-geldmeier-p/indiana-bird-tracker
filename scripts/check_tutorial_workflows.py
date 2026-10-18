"""Validate the contract/manifest/guide relationship before browser recording."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from tutorial_workflows import load_contract, load_manifest


DEFAULT_TAB_PATTERN = r'shiny::tabPanel\(\s*"([^"]+)"'


def missing_tab_tutorials(
    workflows: dict[str, dict], app_ui: str, tab_pattern: str = DEFAULT_TAB_PATTERN
) -> list[str]:
    """Find top-level Shiny tabs that no contracted tutorial opens."""
    labels = re.findall(tab_pattern, app_ui)
    scripts = "\n".join(workflow["script"] for workflow in workflows.values())
    return [
        label
        for label in labels
        if not re.search(rf"name:\s*['\"]{re.escape(label)}['\"]", scripts)
    ]


def main() -> None:
    policy = yaml.safe_load(
        Path(".github/agents/documentation-policy.yml").read_text(encoding="utf-8")
    ) or {}
    discovery = policy.get("workflow_discovery", {})
    ui_files = discovery.get("ui_files", ["R/app_ui.R"])
    tab_pattern = discovery.get("tab_panel_regex", DEFAULT_TAB_PATTERN)
    missing_ui = [name for name in ui_files if not Path(name).is_file()]
    if missing_ui:
        raise SystemExit("Configured workflow UI files do not exist: " + ", ".join(missing_ui))

    workflows = load_contract(Path(".github/agents/workflow-contract.yml"))
    manifest = load_manifest(Path("docs/playwright/manifest.yml"))
    guide = Path("USER_GUIDE.md").read_text(encoding="utf-8")
    app_ui = "\n".join(Path(name).read_text(encoding="utf-8") for name in ui_files)
    discovered_tabs = re.findall(tab_pattern, app_ui)
    if not discovered_tabs:
        raise SystemExit(
            "Workflow discovery found no user-visible tabs; update workflow_discovery "
            "in documentation-policy.yml."
        )
    missing_tabs = missing_tab_tutorials(workflows, app_ui, tab_pattern)
    if missing_tabs:
        raise SystemExit(
            "Workflow contract is missing tutorial scripts for Shiny tabs: "
            + ", ".join(missing_tabs)
        )
    rows = manifest.get("workflows", [])
    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("Tutorial manifest contains duplicate workflow IDs.")

    for workflow_id, workflow in workflows.items():
        script = workflow["script"]
        if "http://127.0.0.1:3838" not in script:
            raise SystemExit(f"Workflow {workflow_id} does not target the isolated Shiny app.")
        destinations = re.findall(r"page\.goto\(['\"]([^'\"]+)", script)
        if not destinations or any(url != "http://127.0.0.1:3838/" for url in destinations):
            raise SystemExit(f"Workflow {workflow_id} contains a non-local navigation target.")
        heading = f"## {workflow['guide_heading']}"
        if heading not in guide:
            raise SystemExit(f"User guide is missing workflow heading: {heading}")
        row = next((item for item in rows if item.get("id") == workflow_id), None)
        if row is None:
            raise SystemExit(f"Manifest is missing contracted workflow: {workflow_id}")
        has_media = f'id="tutorial-{workflow_id}"' in guide
        has_placeholder = "video_placeholder" in row and row["video_placeholder"] in guide
        if not has_media and not has_placeholder:
            raise SystemExit(f"Workflow {workflow_id} has neither guide media nor placeholder.")

    print(f"Validated {len(workflows)} tutorial workflow contract entries.")


if __name__ == "__main__":
    main()
