"""Ask the OpenAI API for an allow-listed documentation patch for one PR."""

from __future__ import annotations

import argparse
import difflib
import fnmatch
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath

import yaml


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


def read_policy(path: Path) -> dict:
    """Load repository-specific discovery and documentation requirements."""
    return yaml.safe_load(read_text(path)) or {}


def request_model_text(api_key: str, prompt: str) -> str:
    request_body = json.dumps(
        {"model": "gpt-5.6-luna", "input": prompt, "max_output_tokens": 16000}
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
    return patch


def request_patch(api_key: str, prompt: str) -> str:
    return normalize_patch(request_model_text(api_key, prompt))


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
        new_text = new_text.replace("\r\n", "\n").replace("\r", "\n")
        if new_text and not new_text.endswith("\n"):
            new_text += "\n"
        path = Path(name)
        existed = path.exists()
        old_text = path.read_text(encoding="utf-8") if existed else ""
        if old_text == new_text:
            continue
        diff = difflib.unified_diff(
            old_text.splitlines(True),
            new_text.splitlines(True),
            fromfile=f"a/{name}" if existed else "/dev/null",
            tofile=f"b/{name}",
            lineterm="\n",
        )
        body = "".join(diff)
        if body:
            metadata = "" if existed else "new file mode 100644\n"
            chunks.append(f"diff --git a/{name} b/{name}\n{metadata}{body}")
    return "\n".join(chunks)


def changed_paths_in_patch(patch: str) -> set[str]:
    """Return repository paths changed by a generated unified patch."""
    return {
        right
        for _, right in re.findall(
            r"^diff --git a/([^ ]+) b/([^ ]+)$", patch, re.MULTILINE
        )
    }


def normalize_structured_files(files: dict[object, object]) -> dict[str, str]:
    """Trim accidental key whitespace without weakening the path allow-list."""
    normalized = {}
    for raw_name, raw_text in files.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError("file paths must not be empty")
        if name in normalized:
            raise ValueError(f"duplicate file path after normalization: {name}")
        normalized[name] = str(raw_text)
    return normalized


def extract_structured_payload(raw: str) -> dict:
    """Merge complete JSON objects containing file mappings.

    Large model responses may be emitted as multiple JSON values. ``json.loads``
    rejects the response as extra data, while accepting only the first value can
    discard required files from later values. Decode every complete top-level
    object, merge complementary files, and reject conflicting duplicates.
    """
    decoder = json.JSONDecoder()
    merged_files = {}
    found_payload = False
    for marker in (match.start() for match in re.finditer(r"\{", raw)):
        try:
            payload, _ = decoder.raw_decode(raw[marker:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and isinstance(payload.get("files"), dict):
            found_payload = True
            for raw_name, content in payload["files"].items():
                name = str(raw_name).strip()
                if name in merged_files and merged_files[name] != content:
                    raise ValueError(
                        f"response contains conflicting content for file: {name}"
                    )
                merged_files[name] = content
    if not found_payload:
        raise ValueError(
            "response does not contain a complete JSON object with a files mapping"
        )
    return {"files": merged_files}


def changed_source_paths(pr_diff: str, prefixes: list[str]) -> list[str]:
    """Return changed source paths selected by repository policy."""
    paths = re.findall(r"^diff --git a/([^ ]+) b/", pr_diff, re.MULTILINE)
    return sorted({path for path in paths if path.startswith(tuple(prefixes))})


def functions_by_source(paths: list[str]) -> dict[str, list[str]]:
    """Inventory ordinary R functions defined in the selected source files."""
    functions = {}
    pattern = re.compile(
        r"^([A-Za-z][A-Za-z0-9._]*)\s*<-\s*function\s*\(", re.MULTILINE
    )
    for name in paths:
        path = Path(name)
        if path.is_file():
            found = pattern.findall(read_text(path))
            if found:
                functions[name] = found
    return functions


def has_roxygen_block(source: str, function_name: str) -> bool:
    """Check that a function definition is immediately preceded by Roxygen."""
    return bool(
        re.search(
            rf"(?m)(?:^#'[^\n]*\n)+^{re.escape(function_name)}\s*<-\s*function\s*\(",
            source,
        )
    )


def files_for_globs(patterns: list[str]) -> list[Path]:
    """Resolve policy globs to a stable, de-duplicated file list."""
    paths = []
    for pattern in patterns:
        paths.extend(path for path in Path(".").glob(pattern) if path.is_file())
    return sorted(set(paths))


def existing_function_coverage(
    functions: dict[str, list[str]],
    manual_globs: list[str] | None = None,
    test_globs: list[str] | None = None,
) -> str:
    """Summarize current manual aliases and test references for the model."""
    manual_globs = manual_globs or ["man/**/*.Rd"]
    test_globs = test_globs or ["tests/testthat/**/*.R"]
    man_text = "\n".join(
        read_text(path) for path in files_for_globs(manual_globs)
    )
    test_text = "\n".join(
        read_text(path) for path in files_for_globs(test_globs)
    )
    rows = []
    for source, names in functions.items():
        for name in names:
            documented = bool(
                re.search(rf"\\(?:name|alias)\{{{re.escape(name)}\}}", man_text)
            )
            tested = bool(re.search(rf"\b{re.escape(name)}\b", test_text))
            rows.append(
                f"- {source}: {name} | man alias: {'yes' if documented else 'no'} "
                f"| test reference: {'yes' if tested else 'no'}"
            )
    return "\n".join(rows) or "- No ordinary R function definitions were detected."


def application_behavior_changed(pr_diff: str, prefixes: list[str]) -> bool:
    """Identify PRs whose committed diff changes application behavior or UI."""
    paths = re.findall(r"^diff --git a/([^ ]+) b/", pr_diff, re.MULTILINE)
    return any(path.startswith(tuple(prefixes)) for path in paths)


def missing_required_application_files(
    files: dict[str, str],
    changed_sources: list[str],
    required_exact: list[str],
    required_prefixes: list[str],
    required_functions: dict[str, list[str]],
) -> list[str]:
    """Return mandatory self-documenting outputs absent from structured content."""
    missing = sorted(set(required_exact).difference(files))
    for prefix in required_prefixes:
        if not any(name.startswith(prefix) for name in files):
            missing.append(prefix + "**")
    for source, functions in required_functions.items():
        candidate = files.get(source, "")
        for function_name in functions:
            if not has_roxygen_block(candidate, function_name):
                missing.append(f"Roxygen for {source}:{function_name}")
    test_text = "\n".join(
        text
        for name, text in files.items()
        if any(name.startswith(prefix) for prefix in required_prefixes)
    )
    for functions in required_functions.values():
        for function_name in functions:
            if not re.search(rf"\b{re.escape(function_name)}\b", test_text):
                missing.append(f"test coverage for {function_name}")
    return missing


def allowed_agent_path(name: str, patterns: list[str] | None = None) -> bool:
    """Reject structured fallback output outside the documented edit boundary."""
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        return False
    patterns = patterns or [
        "R/**",
        "man/**",
        "tests/testthat/**",
        "README.md",
        "NEWS.md",
        "USER_GUIDE.md",
        "WORKFLOW_INVENTORY.md",
        ".github/agents/workflow-contract.yml",
    ]
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def validate_patch_paths(patch: str, allowed_patterns: list[str] | None = None) -> None:
    """Fail before application when a model patch targets a forbidden path."""
    paths = re.findall(r"^diff --git a/([^ ]+) b/([^ ]+)$", patch, re.MULTILINE)
    unexpected = sorted(
        {
            path
            for pair in paths
            for path in pair
            if not allowed_agent_path(path, allowed_patterns)
        }
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


def request_file_contents(
    api_key: str,
    repository: str,
    pr_number: str,
    context: str,
    diff: str,
    required_application_sources: list[str] | None = None,
    required_exact_paths: list[str] | None = None,
    required_path_prefixes: list[str] | None = None,
    allowed_patterns: list[str] | None = None,
    required_functions: dict[str, list[str]] | None = None,
    manual_globs: list[str] | None = None,
    test_globs: list[str] | None = None,
) -> str:
    application_outputs_required = required_application_sources is not None
    required_application_sources = required_application_sources or []
    required_exact_paths = required_exact_paths or []
    required_path_prefixes = required_path_prefixes or []
    required_functions = required_functions or {}
    required_note = ""
    if application_outputs_required:
        roxygen_requirement = ""
        if required_application_sources:
            roxygen_requirement = f"""
- Roxygen comments in the relevant changed R source file. Changed R sources are:
  {', '.join(required_application_sources)}"""
        required_note = f"""
This PR changes application behavior. The `files` object MUST include every category below,
even when the existing text did not become inaccurate:
- Every exact path configured by policy: {', '.join(required_exact_paths)}
- At least one focused file under each policy prefix: {', '.join(required_path_prefixes)}
{roxygen_requirement}
Do not return an empty object and do not omit a category because another check may generate it.

Function coverage audit before this update:
{existing_function_coverage(required_functions, manual_globs, test_globs)}

For every listed function, return its complete R source file with an immediate Roxygen block
and return focused tests that reference and exercise that function. Roxygen will generate man files.
"""
    prompt = f"""You are documenting {repository}, PR #{pr_number}.
Return ONLY a JSON object with this exact shape: {{\"files\": {{\"repository/relative/path\": \"complete replacement text\"}}}}.
Include only files that need truthful updates. The values must be complete replacement file contents, not diffs.
File-path keys must match repository-relative paths exactly, with no leading or trailing whitespace.
The `files` object may also contain `.github/agents/workflow-contract.yml` when a user-visible workflow changes.
Also include complete updated Roxygen source files or tests only when required by the PR, using their repository paths as keys.
Do not invent features, links, videos, screenshots, or test results.
When a user workflow changes, include the complete updated `.github/agents/workflow-contract.yml`.
Preserve every existing `VIDEO PLACEHOLDER:` comment in USER_GUIDE.md exactly unless
`docs/playwright/artifacts/result.json` already contains verified real artifact paths.
{required_note}
PR diff:\n{diff}\nCurrent files:\n{context}"""
    raw = request_model_text(api_key, prompt)
    try:
        payload = extract_structured_payload(raw)
        files = payload.get("files", {})
        if not isinstance(files, dict):
            raise ValueError("files must be an object")
        normalized = normalize_structured_files(files)
        unexpected = sorted(
            name
            for name in normalized
            if not allowed_agent_path(name, allowed_patterns)
        )
        if unexpected:
            raise ValueError(f"files outside documentation allow-list: {unexpected}")
        if application_outputs_required:
            missing = missing_required_application_files(
                normalized,
                required_application_sources,
                required_exact_paths,
                required_path_prefixes,
                required_functions,
            )
            if missing:
                raise ValueError(
                    "required self-documenting outputs are missing: " + ", ".join(missing)
                )
        if "USER_GUIDE.md" in normalized:
            normalized["USER_GUIDE.md"] = restore_protected_guide_blocks(
                normalized["USER_GUIDE.md"]
            )
        patch = contents_to_patch(normalized)
        if application_outputs_required:
            changed = changed_paths_in_patch(patch)
            changed_files = {
                name: text for name, text in normalized.items() if name in changed
            }
            unchanged_required = missing_required_application_files(
                changed_files,
                required_application_sources,
                required_exact_paths,
                required_path_prefixes,
                required_functions,
            )
            if unchanged_required:
                raise ValueError(
                    "required self-documenting files were returned unchanged: "
                    + ", ".join(unchanged_required)
                )
        return patch
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

    policy = read_policy(args.policy)
    context_paths = [
        Path("DESCRIPTION"),
        Path("NAMESPACE"),
        Path("README.md"),
        Path("NEWS.md"),
        Path("USER_GUIDE.md"),
        Path("WORKFLOW_INVENTORY.md"),
        Path(".github/agents/workflow-contract.yml"),
        Path("docs/agent-prompts/document-pr.md"),
    ]
    for pattern in policy.get(
        "agent_context_globs",
        ["R/**/*.R", "man/**/*.Rd", "tests/testthat/**/*.R"],
    ):
        context_paths.extend(path for path in Path(".").glob(pattern) if path.is_file())
    context_paths = list(dict.fromkeys(context_paths))
    context = "\n\n".join(
        f"--- {path.as_posix()} ---\n{read_text(path)}"
        for path in context_paths
        if path.exists()
    )
    allowed_patterns = policy.get("allowed_paths")
    detection = policy.get("application_detection", {})
    application_prefixes = detection.get("changed_path_prefixes", ["R/", "inst/app/"])
    roxygen_prefixes = detection.get("roxygen_source_prefixes", ["R/"])
    required_outputs = policy.get("required_application_outputs", {})
    required_exact_paths = required_outputs.get(
        "exact_paths",
        [
            "README.md",
            "NEWS.md",
            "USER_GUIDE.md",
            "WORKFLOW_INVENTORY.md",
            ".github/agents/workflow-contract.yml",
        ],
    )
    required_path_prefixes = required_outputs.get(
        "path_prefixes", ["tests/testthat/"]
    )
    coverage = policy.get("function_coverage", {})
    manual_globs = coverage.get("manual_globs", ["man/**/*.Rd"])
    test_globs = coverage.get("test_globs", ["tests/testthat/**/*.R"])
    pr_diff = read_text(args.diff)
    application_change = application_behavior_changed(pr_diff, application_prefixes)
    application_sources = (
        changed_source_paths(pr_diff, roxygen_prefixes) if application_change else []
    )
    application_functions = functions_by_source(application_sources)
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
{pr_diff}
--- end PR diff ---

--- current documentation context ---
{context}
--- end context ---
"""
    if application_change:
        patch = request_file_contents(
            api_key,
            args.repository,
            args.pr_number,
            context,
            pr_diff,
            required_application_sources=application_sources,
            required_exact_paths=required_exact_paths,
            required_path_prefixes=required_path_prefixes,
            allowed_patterns=allowed_patterns,
            required_functions=application_functions,
            manual_globs=manual_globs,
            test_globs=test_globs,
        )
    else:
        patch = request_patch(api_key, prompt)
    if patch:
        validate_patch_paths(patch, allowed_patterns)
        check = subprocess.run(["git", "apply", "--check"], input=patch, text=True, capture_output=True)
        if check.returncode:
            if application_change:
                raise SystemExit(
                    "Deterministic structured patch construction failed before application:\n"
                    f"{check.stderr}"
                )
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
            validate_patch_paths(patch, allowed_patterns)
            repaired = subprocess.run(["git", "apply", "--check"], input=patch, text=True, capture_output=True)
            if repaired.returncode:
                patch = request_file_contents(
                    api_key,
                    args.repository,
                    args.pr_number,
                    context,
                    pr_diff,
                    required_application_sources=(
                        application_sources if application_change else None
                    ),
                    required_exact_paths=required_exact_paths,
                    required_path_prefixes=required_path_prefixes,
                    allowed_patterns=allowed_patterns,
                    required_functions=application_functions,
                    manual_globs=manual_globs,
                    test_globs=test_globs,
                )
                validate_patch_paths(patch, allowed_patterns)
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
                api_key,
                args.repository,
                args.pr_number,
                context,
                pr_diff,
                required_application_sources=(
                    application_sources if application_change else None
                ),
                required_exact_paths=required_exact_paths,
                required_path_prefixes=required_path_prefixes,
                allowed_patterns=allowed_patterns,
                required_functions=application_functions,
                manual_globs=manual_globs,
                test_globs=test_globs,
            )
            validate_patch_paths(patch, allowed_patterns)
            rebuilt = subprocess.run(
                ["git", "apply", "--check"], input=patch, text=True, capture_output=True
            )
            if rebuilt.returncode:
                raise SystemExit(
                    "Documentation agent could not produce a valid protected-guide "
                    f"fallback patch:\n{rebuilt.stderr}"
                )
    patch = restore_deleted_roxygen_params(patch, pr_diff)
    # `git apply --check` treats an empty stream as an error. An empty patch is
    # nevertheless a valid agent result when the PR requires no truthful
    # documentation changes and there is no deterministic Roxygen restoration.
    if patch:
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
