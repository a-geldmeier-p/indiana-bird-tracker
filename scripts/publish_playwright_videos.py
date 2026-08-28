"""Publish verified Playwright recordings into the user guide."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


WORKFLOWS = (
    (
        "catalog",
        "workflows-catalog-tutorial",
        "Catalog browsing and filtering",
        "<!-- VIDEO PLACEHOLDER: Catalog browsing and filtering (Playwright recording) -->",
    ),
    (
        "record_sighting",
        "workflows-record-sighting-tutorial",
        "Recording a sighting",
        "<!-- VIDEO PLACEHOLDER: Recording a sighting with a photo (Playwright recording) -->",
    ),
    (
        "my_sightings",
        "workflows-my-sightings-tutorial",
        "Filtering and reviewing My Sightings",
        "<!-- VIDEO PLACEHOLDER: Filtering and reviewing My Sightings (Playwright recording) -->",
    ),
    (
        "dashboard",
        "workflows-dashboard-tutorial",
        "Dashboard overview",
        "<!-- VIDEO PLACEHOLDER: Dashboard overview (Playwright recording) -->",
    ),
)


def find_video(results: Path, directory_name: str) -> Path:
    matches = [
        path
        for path in results.rglob("video.webm")
        if directory_name in path.parent.name
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"Expected one video for {directory_name}, found {len(matches)}: {matches}"
        )
    return matches[0]


def video_block(workflow_id: str, title: str) -> str:
    path = f"docs/playwright/artifacts/{workflow_id}.webm"
    return (
        f'<figure id="tutorial-{workflow_id}">\n'
        f'  <video controls preload="metadata" aria-label="{title} tutorial">\n'
        f'    <source src="{path}" type="video/webm">\n'
        "    Your browser does not support embedded WebM video.\n"
        "  </video>\n"
        f"  <figcaption>{title} tutorial.</figcaption>\n"
        "</figure>"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("test-results"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("docs/playwright/artifacts"))
    parser.add_argument("--guide", type=Path, default=Path("USER_GUIDE.md"))
    parser.add_argument("--manifest", type=Path, default=Path("docs/playwright/manifest.yml"))
    parser.add_argument("--commit-sha", required=True)
    args = parser.parse_args()

    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    keep_file = args.artifact_dir / ".gitkeep"
    if keep_file.exists():
        keep_file.unlink()
    guide = args.guide.read_text(encoding="utf-8")
    results = []
    manifest_lines = ["version: 1", "artifact_root: docs/playwright/artifacts", "workflows:"]

    for workflow_id, result_dir, title, placeholder in WORKFLOWS:
        source = find_video(args.results, result_dir)
        destination = args.artifact_dir / f"{workflow_id}.webm"
        shutil.copy2(source, destination)

        block = video_block(workflow_id, title)
        existing_start = f'<figure id="tutorial-{workflow_id}">'
        if placeholder in guide:
            guide = guide.replace(placeholder, block, 1)
        elif existing_start not in guide:
            raise SystemExit(
                f"USER_GUIDE.md contains neither the placeholder nor video block for {workflow_id}."
            )

        relative = destination.as_posix()
        results.append(
            {
                "workflow": workflow_id,
                "commit_sha": args.commit_sha,
                "video": relative,
            }
        )
        manifest_lines.extend(
            [
                f"  - id: {workflow_id}",
                f"    video: {relative}",
                f"    commit_sha: {args.commit_sha}",
            ]
        )

    args.guide.write_text(guide, encoding="utf-8")
    args.manifest.write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    (args.artifact_dir / "result.json").write_text(
        json.dumps({"commit_sha": args.commit_sha, "workflows": results}, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Published four verified Playwright videos into USER_GUIDE.md.")


if __name__ == "__main__":
    main()
