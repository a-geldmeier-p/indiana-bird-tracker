"""Publish verified recordings for only the selected tutorial workflows."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

import yaml

from tutorial_workflows import load_contract, load_manifest


class IndentDumper(yaml.SafeDumper):
    """Keep manifest sequence entries indented under `workflows:`."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def find_artifact(source_dir: Path, name: str) -> Path:
    matches = list(source_dir.rglob(name))
    if len(matches) != 1 or matches[0].stat().st_size == 0:
        raise SystemExit(f"Expected one non-empty MCP artifact named {name}; found {matches}")
    return matches[0]


def video_block(workflow_id: str, title: str) -> str:
    video = f"docs/playwright/artifacts/{workflow_id}.webm"
    poster = f"docs/playwright/artifacts/{workflow_id}.png"
    return (
        f'<figure id="tutorial-{workflow_id}">\n'
        f'  <video controls preload="metadata" poster="{poster}" aria-label="{title} tutorial">\n'
        f'    <source src="{video}" type="video/webm">\n'
        "    Your browser does not support embedded WebM video.\n"
        "  </video>\n"
        f"  <figcaption>{title} tutorial.</figcaption>\n"
        "</figure>"
    )


def replace_guide_media(guide: str, workflow_id: str, title: str) -> str:
    placeholder_pattern = re.compile(
        rf"<!-- VIDEO PLACEHOLDER: .*?\(Playwright recording\) -->",
        re.DOTALL,
    )
    heading = f"## {title}"
    section_start = guide.find(heading)
    if section_start < 0:
        raise SystemExit(f"USER_GUIDE.md is missing heading: {title}")
    next_heading = guide.find("\n## ", section_start + len(heading))
    section_end = len(guide) if next_heading < 0 else next_heading
    section = guide[section_start:section_end]
    block = video_block(workflow_id, title)
    figure_pattern = re.compile(
        rf'<figure id="tutorial-{re.escape(workflow_id)}">.*?</figure>', re.DOTALL
    )
    if figure_pattern.search(section):
        section = figure_pattern.sub(block, section, count=1)
    elif placeholder_pattern.search(section):
        section = placeholder_pattern.sub(block, section, count=1)
    else:
        raise SystemExit(f"Guide section {title!r} has neither placeholder nor tutorial figure.")
    return guide[:section_start] + section + guide[section_end:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=Path(".github/agents/workflow-contract.yml"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("docs/playwright/artifacts"))
    parser.add_argument("--guide", type=Path, default=Path("USER_GUIDE.md"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/playwright/manifest.yml"))
    parser.add_argument("--commit-sha", required=True)
    args = parser.parse_args()

    selected = json.loads(args.selection.read_text(encoding="utf-8")).get("workflows", [])
    if not selected:
        print("No selected tutorial recordings to publish.")
        return

    workflows = load_contract(args.contract)
    manifest = load_manifest(args.manifest)
    rows = {row["id"]: row for row in manifest.get("workflows", [])}
    guide = args.guide.read_text(encoding="utf-8")
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for selected_row in selected:
        workflow_id = selected_row["id"]
        workflow = workflows.get(workflow_id)
        if not workflow:
            raise SystemExit(f"Selected workflow is absent from contract: {workflow_id}")
        source_video = find_artifact(args.source_dir, f"{workflow_id}.webm")
        source_poster = find_artifact(args.source_dir, f"{workflow_id}.png")
        video = args.artifact_dir / f"{workflow_id}.webm"
        poster = args.artifact_dir / f"{workflow_id}.png"
        shutil.copy2(source_video, video)
        shutil.copy2(source_poster, poster)
        guide = replace_guide_media(guide, workflow_id, workflow["guide_heading"])

        row = rows.setdefault(workflow_id, {"id": workflow_id})
        row.update(
            {
                "guide_heading": workflow["guide_heading"],
                "workflow_fingerprint": selected_row["fingerprint"],
                "video": video.as_posix(),
                "poster": poster.as_posix(),
                "commit_sha": args.commit_sha,
            }
        )
        results.append({"workflow": workflow_id, **row})

    # Contract order is authoritative; unchanged manifest rows are preserved.
    manifest["workflows"] = [rows[workflow_id] for workflow_id in workflows if workflow_id in rows]
    args.guide.write_text(guide.rstrip() + "\n", encoding="utf-8")
    args.manifest.write_text(
        yaml.dump(manifest, Dumper=IndentDumper, sort_keys=False), encoding="utf-8"
    )
    (args.artifact_dir / "result.json").write_text(
        json.dumps({"commit_sha": args.commit_sha, "workflows": results}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Published {len(results)} verified MCP tutorial workflow(s).")


if __name__ == "__main__":
    main()
