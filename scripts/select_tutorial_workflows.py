"""Select only new, changed, or artifact-missing tutorial workflows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tutorial_workflows import fingerprint, load_contract, load_manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path(".github/agents/workflow-contract.yml"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/playwright/manifest.yml"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    workflows = load_contract(args.contract)
    manifest = load_manifest(args.manifest)
    recorded = {row["id"]: row for row in manifest.get("workflows", [])}
    selected = []
    for workflow_id, workflow in workflows.items():
        current = fingerprint(workflow_id, workflow)
        previous = recorded.get(workflow_id, {})
        media = [previous.get("video"), previous.get("poster")]
        reasons = []
        if not previous:
            reasons.append("new")
        if previous.get("workflow_fingerprint") != current:
            reasons.append("changed")
        if not all(value and Path(value).is_file() and Path(value).stat().st_size for value in media):
            reasons.append("missing-artifact")
        if reasons:
            selected.append({"id": workflow_id, "fingerprint": current, "reasons": reasons})

    args.output.write_text(json.dumps({"workflows": selected}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"count": len(selected), "ids": [row["id"] for row in selected]}))


if __name__ == "__main__":
    main()
