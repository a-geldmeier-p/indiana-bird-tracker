"""Validate the contract/manifest/guide relationship before browser recording."""

from __future__ import annotations

import re
from pathlib import Path

from tutorial_workflows import load_contract, load_manifest


def main() -> None:
    workflows = load_contract(Path(".github/agents/workflow-contract.yml"))
    manifest = load_manifest(Path("docs/playwright/manifest.yml"))
    guide = Path("USER_GUIDE.md").read_text(encoding="utf-8")
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
