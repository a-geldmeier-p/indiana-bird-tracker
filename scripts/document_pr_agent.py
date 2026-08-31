"""Ask the OpenAI API for an allow-listed documentation patch for one PR."""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def response_text(payload: dict) -> str:
    """Extract text from a Responses API JSON response."""
    parts = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def request_patch(api_key: str, prompt: str) -> str:
    request_body = json.dumps(
        {"model": "gpt-5.6-luna", "input": prompt, "max_output_tokens": 12000}
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=request_body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            patch = response_text(json.load(response))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"OpenAI API request failed ({error.code}): {detail}") from error
    return normalize_patch(patch)


def normalize_patch(patch: str) -> str:
    """Remove model prose/fences while preserving a complete git patch."""
    patch = patch.replace("\\r\\n", "\\n").strip()
    if patch.startswith("*** Begin Patch"):
        patch = patch[len("*** Begin Patch") :].strip()
        if patch.endswith("*** End Patch"):
            patch = patch[: -len("*** End Patch")].rstrip()
    if "```" in patch:
        blocks = patch.split("```")
        fenced = [block for block in blocks if "diff --git " in block]
        if fenced:
            patch = fenced[0]
    marker = patch.find("diff --git ")
    if marker >= 0:
        patch = patch[marker:]
    if patch.endswith("```"):
        patch = patch[:-3].rstrip()
    return patch.strip()


def contents_to_patch(files: dict[str, str]) -> str:
    chunks = []
    for name, new_text in files.items():
        path = Path(name)
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        if old_text == new_text:
            continue
        diff = difflib.unified_diff(
            old_text.splitlines(True),
            new_text.splitlines(True),
            fromfile=f"a/{name}" if path.exists() else "/dev/null",
            tofile=f"b/{name}",
            lineterm="\n",
        )
        body = "".join(diff)
        if body:
            chunks.append(f"diff --git a/{name} b/{name}\n{body}")
    return "\n".join(chunks)


def allowed_agent_path(name: str) -> bool:
    """Reject structured fallback output outside the documented edit boundary."""
    path = Path(name)
    if path.is_absolute() or ".." in path.parts:
        return False
    exact = {
        "README.md",
        "NEWS.md",
        "USER_GUIDE.md",
        "WORKFLOW_INVENTORY.md",
        ".github/agents/workflow-contract.yml",
    }
    return name in exact or name.startswith(("R/", "man/", "tests/testthat/"))


def validate_patch_paths(patch: str) -> None:
    """Fail before application when a model patch targets a forbidden path."""
    paths = re.findall(r"^diff --git a/([^ ]+) b/([^ ]+)$", patch, re.MULTILINE)
    unexpected = sorted(
        {path for pair in paths for path in pair if not allowed_agent_path(path)}
    )
    if unexpected:
        raise SystemExit(f"Documentation agent patch targets forbidden paths: {unexpected}")


def preserves_video_placeholders(patch: str) -> bool:
    """Keep pending placeholders and existing verified video embeds.

    A complete-file fallback may move a protected block.  Git represents that
    move as a removal plus an identical addition, which is safe.  Reject only
    protected content removed without an exact replacement in the patch.
    """
    protected = ("VIDEO PLACEHOLDER:", 'id="tutorial-', "docs/playwright/artifacts/")
    lines = patch.splitlines()
    added = {line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")}
    removed = {line[1:] for line in lines if line.startswith("-") and not line.startswith("---")}
    return all(
        line in added
        for line in removed
        if any(marker in line for marker in protected)
    )


def protected_guide_blocks(guide: str) -> list[tuple[str, str]]:
    """Return each protected tutorial block with the section that owns it."""
    blocks = []
    patterns = (
        r"<!-- VIDEO PLACEHOLDER:.*?-->",
        r'<figure id="tutorial-[^"]+">.*?</figure>',
    )
    for pattern in patterns:
        for match in re.finditer(pattern, guide, re.DOTALL):
            heading_matches = list(re.finditer(r"^## (.+)$", guide[: match.start()], re.MULTILINE))
            heading = heading_matches[-1].group(1) if heading_matches else ""
            blocks.append((heading, match.group(0)))
    return blocks


def restore_protected_guide_blocks(candidate: str) -> str:
    """Keep recorded-video blocks while allowing the model to update surrounding prose."""
    original = read_text(Path("USER_GUIDE.md"))
    for heading, block in protected_guide_blocks(original):
        if block in candidate:
            continue
        marker = f"## {heading}"
        if marker in candidate:
            start = candidate.index(marker)
            next_heading = candidate.find("\n## ", start + len(marker))
            insertion = len(candidate) if next_heading < 0 else next_heading
            candidate = (
                candidate[:insertion].rstrip()
                + f"\n\n{block}\n"
                + candidate[insertion:]
            )
        else:
            candidate = candidate.rstrip() + f"\n\n{marker}\n\n{block}\n"
    return candidate


def request_file_contents(api_key: str, repository: str, pr_number: str, context: str, diff: str) -> str:
    prompt = f"""You are documenting {repository}, PR #{pr_number}.
Return ONLY a JSON object with this exact shape: {{\"files\": {{\"README.md\": \"full text\", \"NEWS.md\": \"full text\", \"USER_GUIDE.md\": \"full text\", \"WORKFLOW_INVENTORY.md\": \"full text\"}}}}.
Include only files that need truthful updates. The values must be complete replacement file contents, not diffs.
The `files` object may also contain `.github/agents/workflow-contract.yml` when a user-visible workflow changes.
Also include complete updated Roxygen source files or tests only when required by the PR, using their repository paths as keys.
Do not invent features, links, videos, screenshots, or test results.
When a user workflow changes, include the complete updated `.github/agents/workflow-contract.yml`.
Preserve every existing `VIDEO PLACEHOLDER:` comment in USER_GUIDE.md exactly unless
`docs/playwright/artifacts/result.json` already contains verified real artifact paths.
PR diff:\n{diff}\nCurrent files:\n{context}"""
    raw = request_patch(api_key, prompt)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        raise SystemExit("Documentation agent did not return structured file contents.")
    try:
        payload = json.loads(raw[start : end + 1])
        files = payload.get("files", {})
        if not isinstance(files, dict):
            raise ValueError("files must be an object")
        normalized = {str(k): str(v) for k, v in files.items()}
        unexpected = sorted(name for name in normalized if not allowed_agent_path(name))
        if unexpected:
            raise ValueError(f"files outside documentation allow-list: {unexpected}")
        if "USER_GUIDE.md" in normalized:
            normalized["USER_GUIDE.md"] = restore_protected_guide_blocks(
                normalized["USER_GUIDE.md"]
            )
        return contents_to_patch(normalized)
    except (json.JSONDecodeError, ValueError) as error:
        raise SystemExit(f"Documentation agent returned invalid structured content: {error}") from error


def restore_deleted_roxygen_params(patch: str, pr_diff: str) -> str:
    """Restore removed @param lines when the documented function still has that parameter.

    This covers a mechanical documentation regression deterministically.  It
    does not infer new documentation: it restores only an exact Roxygen line
    deleted by the pull request, and only when the current function signature
    still contains the named parameter.
    """
    deleted: dict[str, list[str]] = {}
    current_path = None
    for line in pr_diff.splitlines():
        header = re.match(r"^diff --git a/(R/[^ ]+) b/", line)
        if header:
            current_path = header.group(1)
            continue
        if current_path and line.startswith("-#' @param "):
            deleted.setdefault(current_path, []).append(line[1:])

    replacements = {}
    for name, lines in deleted.items():
        if f"diff --git a/{name} b/{name}" in patch:
            continue
        path = Path(name)
        if not path.exists():
            continue
        source = read_text(path)
        updated = source
        for roxygen_line in lines:
            parameter = re.match(r"#' @param ([A-Za-z][A-Za-z0-9_.]*)\b", roxygen_line)
            if not parameter or roxygen_line in updated or f"+{roxygen_line}" in patch:
                continue
            name_in_signature = parameter.group(1)
            block_pattern = re.compile(
                r"(?m)(?P<docs>(?:^#'.*\n)+)"
                r"(?P<definition>^[A-Za-z][A-Za-z0-9_.]*\s*<-\s*function\((?P<args>[^)]*)\))"
            )
            for block in block_pattern.finditer(updated):
                arguments = block.group("args")
                if not re.search(rf"\b{re.escape(name_in_signature)}\s*(?:=|,|$)", arguments):
                    continue
                docs = block.group("docs")
                insertion = docs.find("#' @return")
                insertion = len(docs) if insertion < 0 else insertion
                amended_docs = docs[:insertion] + roxygen_line + "\n" + docs[insertion:]
                updated = (
                    updated[: block.start("docs")]
                    + amended_docs
                    + updated[block.end("docs") :]
                )
                break
        if updated != source:
            replacements[name] = updated
    restoration = contents_to_patch(replacements)
    return patch + ("\n" if patch and restoration else "") + restoration


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr-number", required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--diff", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip().strip('"').strip("'")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required.")

    context_paths = [
        Path("README.md"),
        Path("NEWS.md"),
        Path("USER_GUIDE.md"),
        Path("WORKFLOW_INVENTORY.md"),
        Path(".github/agents/workflow-contract.yml"),
        Path("docs/agent-prompts/document-pr.md"),
    ]
    context = "\n\n".join(
        f"--- {path} ---\n{read_text(path)}"
        for path in context_paths
        if path.exists()
    )
    prompt = f"""You are the bounded documentation agent for {args.repository}, PR #{args.pr_number}.

Return ONLY a valid unified git patch. Do not use Markdown fences or explanations.
The patch must modify only paths allowed by this policy:
--- policy ---
{read_text(args.policy)}
--- end policy ---

Rules:
- You MUST return a valid unified git patch, and nothing else.
- You may edit only these paths:
  1. README.md — update setup, usage, or behavior notes affected by this PR.
  2. NEWS.md — add one concise entry under the current development heading.
  3. USER_GUIDE.md — update the relevant user-facing workflow instructions.
  4. WORKFLOW_INVENTORY.md — update user-visible workflow IDs and steps when this PR changes them.
  5. .github/agents/workflow-contract.yml — add or update the matching machine-readable
     workflow definition when user-visible steps, stable IDs, or workflows change. Each
     workflow requires guide_heading, stable_ids, and a complete deterministic Playwright
     `script`. Do not alter unchanged workflows.
  6. Roxygen comments in R source files and the generated man/ files.
  7. Focused tests under tests/testthat/ that cover behavior changed by this PR.
- Do not edit application behavior, dependencies, CI workflows, policy files other than
  workflow-contract.yml, or recorder/publisher scripts. Do not add unrelated tests or documentation.
- Make only changes supported by the PR diff. Do not invent features, links, videos,
  screenshots, or test results. Preserve existing Markdown structure and headings.
- Treat deleted Roxygen fields, focused tests, README capabilities, NEWS entries,
  user-guide steps, and workflow-inventory steps as stale-documentation gaps when
  the corresponding implementation still exists. Restore or replace that coverage.
- Preserve every existing `VIDEO PLACEHOLDER:` comment and published tutorial
  `<figure>`/`docs/playwright/artifacts/` reference in USER_GUIDE.md exactly.
  The deterministic Playwright publisher, not the model, replaces placeholders.
- If a file does not need a truthful update, leave it unchanged. If none need updates,
  return an empty response.
- Every changed file must have a complete `diff --git` header and valid hunk counts.

--- PR diff ---
{read_text(args.diff)}
--- end PR diff ---

--- current documentation context ---
{context}
--- end context ---
"""
    patch = request_patch(api_key, prompt)
    if patch:
        validate_patch_paths(patch)
        check = subprocess.run(["git", "apply", "--check"], input=patch, text=True, capture_output=True)
        if check.returncode:
            repair_prompt = f"""Repair this proposed unified git patch so `git apply --check` accepts it.
Return ONLY a standard git unified patch beginning with `diff --git`.
Do not use `*** Begin Patch`, `*** End Patch`, Markdown fences, or prose.
Include complete `---`, `+++`, and valid hunk line counts for every changed file.
Git error:
{check.stderr}
Patch:
{patch}
"""
            patch = request_patch(api_key, repair_prompt)
            validate_patch_paths(patch)
            repaired = subprocess.run(["git", "apply", "--check"], input=patch, text=True, capture_output=True)
            if repaired.returncode:
                patch = request_file_contents(
                    api_key, args.repository, args.pr_number, context, read_text(args.diff)
                )
                validate_patch_paths(patch)
                rebuilt = subprocess.run(
                    ["git", "apply", "--check"], input=patch, text=True, capture_output=True
                )
                if rebuilt.returncode:
                    raise SystemExit(
                        "Documentation agent could not produce a valid patch after "
                        f"structured retry:\n{rebuilt.stderr}"
                    )
        if not preserves_video_placeholders(patch):
            patch = request_file_contents(
                api_key, args.repository, args.pr_number, context, read_text(args.diff)
            )
            validate_patch_paths(patch)
            rebuilt = subprocess.run(
                ["git", "apply", "--check"], input=patch, text=True, capture_output=True
            )
            if rebuilt.returncode:
                raise SystemExit(
                    "Documentation agent could not produce a valid protected-guide "
                    f"fallback patch:\n{rebuilt.stderr}"
                )
    patch = restore_deleted_roxygen_params(patch, read_text(args.diff))
    final_check = subprocess.run(
        ["git", "apply", "--check"], input=patch, text=True, capture_output=True
    )
    if final_check.returncode:
        raise SystemExit(
            "Documentation patch plus deterministic Roxygen restoration is invalid:\n"
            f"{final_check.stderr}"
        )
    args.output.write_text(patch + ("\n" if patch else ""), encoding="utf-8")


if __name__ == "__main__":
    main()
