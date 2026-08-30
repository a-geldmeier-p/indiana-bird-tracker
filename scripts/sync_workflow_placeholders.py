"""Create manifest entries and guide placeholders for newly contracted workflows."""

from __future__ import annotations

import re
from pathlib import Path


CONTRACT = Path(".github/agents/workflow-contract.yml")
MANIFEST = Path("docs/playwright/manifest.yml")
GUIDE = Path("USER_GUIDE.md")


def contracted_workflows(text: str) -> list[tuple[str, str]]:
    workflows = []
    current_id = None
    for line in text.splitlines():
        match = re.match(r"^  ([a-z0-9_]+):\s*$", line)
        if match:
            current_id = match.group(1)
            continue
        heading = re.match(r"^    guide_heading:\s*(.+?)\s*$", line)
        if current_id and heading:
            workflows.append((current_id, heading.group(1).strip('"\'')))
            current_id = None
    return workflows


def insert_after_section(guide: str, heading: str, placeholder: str) -> str:
    marker = f"## {heading}"
    if marker not in guide:
        return guide.rstrip() + f"\n\n{marker}\n\n{placeholder}\n"
    start = guide.index(marker)
    next_heading = guide.find("\n## ", start + len(marker))
    insertion = len(guide) if next_heading < 0 else next_heading
    return guide[:insertion].rstrip() + f"\n\n{placeholder}\n" + guide[insertion:]


def existing_placeholder(manifest: str, workflow_id: str) -> str | None:
    match = re.search(
        rf"^  - id:\s*{re.escape(workflow_id)}\s*$"
        rf"(?P<body>.*?)(?=^  - id:|\Z)",
        manifest,
        re.MULTILINE | re.DOTALL,
    )
    if not match:
        return None
    placeholder = re.search(r'^    video_placeholder:\s*"(.*)"\s*$', match.group("body"), re.MULTILINE)
    return placeholder.group(1) if placeholder else None


def main() -> None:
    contract = CONTRACT.read_text(encoding="utf-8")
    manifest = MANIFEST.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")

    for workflow_id, heading in contracted_workflows(contract):
        has_video = (
            f'id="tutorial-{workflow_id}"' in guide
            or f"docs/playwright/artifacts/{workflow_id}.webm" in guide
        )
        placeholder = existing_placeholder(manifest, workflow_id) or (
            f"<!-- VIDEO PLACEHOLDER: {heading} (Playwright recording) -->"
        )

        if not re.search(rf"^\s*- id:\s*{re.escape(workflow_id)}\s*$", manifest, re.MULTILINE):
            manifest = manifest.rstrip() + (
                f"\n  - id: {workflow_id}\n"
                f"    guide_heading: {heading}\n"
                f'    video_placeholder: "{placeholder}"\n'
            )

        if not has_video and placeholder not in guide:
            guide = insert_after_section(guide, heading, placeholder)

    MANIFEST.write_text(manifest.rstrip() + "\n", encoding="utf-8")
    GUIDE.write_text(guide.rstrip() + "\n", encoding="utf-8")
    print("Workflow placeholders and manifest entries are synchronized.")


if __name__ == "__main__":
    main()
