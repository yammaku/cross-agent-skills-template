#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(REPO_LIB) not in sys.path:
    sys.path.insert(0, str(REPO_LIB))

from agent_skills.adapters import agent_names, parse_array
from agent_skills.system import config_path

IGNORED_NAMES = {".DS_Store", "__pycache__"}
NAME_RE = re.compile(r"^[a-z0-9-]+$")


class MigrationError(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Apply an approved agent-global migration plan into the skills-registry repo."
    )
    parser.add_argument(
        "--plan",
        required=True,
        help="Path to the approved migration plan JSON.",
    )
    parser.add_argument(
        "--repo",
        help="Path to the local skills-registry repo clone. Defaults to the current repo.",
    )
    return parser


def validate_name(name: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise MigrationError(
            f"Invalid target skill name '{name}'. Use lowercase letters, digits, and hyphens only."
        )


def shared_dir(root: Path) -> Path:
    return root / "skills" / "shared"


def agent_dir(root: Path, agent: str) -> Path:
    return root / "skills" / agent


def agent_global_manifest_path(root: Path, agent: str) -> Path:
    return root / "manifests" / "agent-global" / f"{agent}.toml"


def read_agent_global_manifest(path: Path) -> set[str]:
    if not path.exists():
        return set()
    match = re.search(r"skills\s*=\s*(\[[\s\S]*?\])", path.read_text())
    if not match:
        return set()
    return set(parse_array(match.group(1)))


def write_agent_global_manifest(path: Path, refs: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# One agent only. Use explicit catalog refs like 'shared/example-skill' or 'codex/example-agent-skill'.",
        "skills = [",
    ]
    for ref in sorted(refs):
        lines.append(f'  "{ref}",')
    lines.append("]")
    lines.append("")
    path.write_text("\n".join(lines))


def load_plan(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise MigrationError(f"Invalid migration plan JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise MigrationError("Migration plan root must be a JSON object.")
    return data


def ensure_copy_source(path: Path) -> Path:
    if not path.exists():
        raise MigrationError(f"Preferred source does not exist: {path}")
    if path.is_symlink():
        resolved = path.resolve()
        if not resolved.exists():
            raise MigrationError(f"Preferred source symlink is broken: {path}")
        path = resolved
    if not path.is_dir():
        raise MigrationError(f"Preferred source must be a directory: {path}")
    return path


def ignore_copy(_src: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_NAMES}


def validate_plan(root: Path, plan: dict[str, object]) -> tuple[list[str], list[dict[str, object]]]:
    known_agents = set(agent_names(root))

    format_version = plan.get("format_version")
    if format_version != 1:
        raise MigrationError(
            f"Migration plan format_version must be 1, got {format_version!r}."
        )

    raw_selected = plan.get("selected_agents")
    if not isinstance(raw_selected, list) or not raw_selected:
        raise MigrationError("Migration plan must include a non-empty 'selected_agents' list.")
    selected_agents = []
    for raw in raw_selected:
        if not isinstance(raw, str) or raw not in known_agents:
            raise MigrationError(f"Unknown agent in selected_agents: {raw!r}")
        if raw not in selected_agents:
            selected_agents.append(raw)

    raw_items = plan.get("migrations")
    if not isinstance(raw_items, list) or not raw_items:
        raise MigrationError("Migration plan must include a non-empty 'migrations' list.")

    seen_targets: set[tuple[str, str, str | None]] = set()
    normalized: list[dict[str, object]] = []

    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise MigrationError(f"Migration item #{index + 1} must be a JSON object.")

        category = item.get("target_category")
        if category not in {"shared", "agent-specific", "skip"}:
            raise MigrationError(
                f"Migration item #{index + 1} has invalid target_category: {category!r}"
            )

        raw_sources = item.get("sources")
        if not isinstance(raw_sources, list) or not raw_sources:
            raise MigrationError(f"Migration item #{index + 1} must include non-empty 'sources'.")

        sources: list[dict[str, str]] = []
        for source in raw_sources:
            if not isinstance(source, dict):
                raise MigrationError(f"Migration item #{index + 1} has an invalid source entry.")
            agent = source.get("agent")
            name = source.get("name")
            path = source.get("path")
            if not isinstance(agent, str) or agent not in known_agents:
                raise MigrationError(f"Migration item #{index + 1} has invalid source agent: {agent!r}")
            if agent not in selected_agents:
                raise MigrationError(
                    f"Migration item #{index + 1} source agent {agent!r} is not in selected_agents."
                )
            if not isinstance(name, str) or not name:
                raise MigrationError(f"Migration item #{index + 1} has invalid source name: {name!r}")
            if not isinstance(path, str) or not path:
                raise MigrationError(f"Migration item #{index + 1} has invalid source path: {path!r}")
            sources.append({"agent": agent, "name": name, "path": path})

        preferred_source = item.get("preferred_source")
        if not isinstance(preferred_source, str) or not preferred_source:
            raise MigrationError(f"Migration item #{index + 1} must include preferred_source.")
        source_paths = {source["path"] for source in sources}
        if preferred_source not in source_paths:
            raise MigrationError(
                f"Migration item #{index + 1} preferred_source must match one of its sources."
            )

        install_agents: list[str] = []
        raw_install_agents = item.get("install_agents", [])
        if category != "skip":
            if not isinstance(raw_install_agents, list) or not raw_install_agents:
                raise MigrationError(
                    f"Migration item #{index + 1} must include non-empty install_agents."
                )
            for agent in raw_install_agents:
                if not isinstance(agent, str) or agent not in selected_agents:
                    raise MigrationError(
                        f"Migration item #{index + 1} install_agents contains invalid agent: {agent!r}"
                    )
                if agent not in install_agents:
                    install_agents.append(agent)

        target_name = item.get("target_name")
        if category == "skip":
            target_name = None
        elif not isinstance(target_name, str) or not target_name:
            raise MigrationError(f"Migration item #{index + 1} must include target_name.")
        else:
            validate_name(target_name)

        target_agent = item.get("target_agent")
        if category == "shared":
            if target_agent not in (None, ""):
                raise MigrationError(
                    f"Migration item #{index + 1} is shared and must not set target_agent."
                )
            target_agent = None
        elif category == "agent-specific":
            if not isinstance(target_agent, str) or target_agent not in selected_agents:
                raise MigrationError(
                    f"Migration item #{index + 1} must set target_agent to one selected agent."
                )
        else:
            target_agent = None

        reason = item.get("reason")
        if reason is not None and not isinstance(reason, str):
            raise MigrationError(f"Migration item #{index + 1} reason must be a string if set.")

        dedupe_key = (category, target_name or "", target_agent)
        if category != "skip" and dedupe_key in seen_targets:
            raise MigrationError(
                f"Duplicate migration target detected for item #{index + 1}: {dedupe_key}"
            )
        seen_targets.add(dedupe_key)

        normalized.append(
            {
                "target_category": category,
                "target_name": target_name,
                "target_agent": target_agent,
                "install_agents": install_agents,
                "preferred_source": preferred_source,
                "sources": sources,
                "reason": reason,
            }
        )

    return selected_agents, normalized


def target_path(root: Path, item: dict[str, object]) -> Path | None:
    category = item["target_category"]
    name = item["target_name"]
    if category == "skip" or name is None:
        return None
    if category == "shared":
        return shared_dir(root) / name
    return agent_dir(root, str(item["target_agent"])) / name


def copy_into_catalog(root: Path, items: list[dict[str, object]]) -> None:
    for item in items:
        destination = target_path(root, item)
        if destination is None:
            continue
        if destination.exists() or destination.is_symlink():
            raise MigrationError(
                f"Migration target already exists and must be resolved manually: {destination}"
            )
        source = ensure_copy_source(Path(str(item["preferred_source"])).expanduser())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, destination, symlinks=True, ignore=ignore_copy)


def update_manifests(root: Path, items: list[dict[str, object]]) -> None:
    refs_by_agent: dict[str, set[str]] = {
        agent: read_agent_global_manifest(agent_global_manifest_path(root, agent))
        for agent in agent_names(root)
    }

    for item in items:
        category = item["target_category"]
        name = item["target_name"]
        if category == "skip" or name is None:
            continue
        if category == "shared":
            ref = f"shared/{name}"
        else:
            ref = f"{item['target_agent']}/{name}"
        for agent in item["install_agents"]:
            refs_by_agent[str(agent)].add(ref)

    for agent, refs in refs_by_agent.items():
        write_agent_global_manifest(agent_global_manifest_path(root, agent), refs)


def run_repo_command(repo: Path, args: list[str]) -> None:
    env = dict(os.environ)
    env["AGENT_SKILLS_REPO"] = str(repo)
    subprocess.run(args, check=True, env=env)


def rewire_selected_agents(repo: Path, agents: list[str]) -> None:
    install_script = repo / "bootstrap" / "install_agent_skills.py"
    args = [
        sys.executable,
        str(install_script),
        "--repo",
        str(repo),
        "--replace-existing",
    ]
    for agent in agents:
        args.extend(["--agent", agent])
    subprocess.run(args, check=True)


def post_apply_checks(repo: Path) -> None:
    manager = repo / "skills" / "shared" / "manage-agent-skills" / "scripts" / "manage_agent_skills.py"
    run_repo_command(repo, [sys.executable, str(manager), "sync-agent-global"])
    run_repo_command(repo, [sys.executable, str(manager), "check"])


def main() -> None:
    args = build_parser().parse_args()
    repo = Path(args.repo).expanduser().resolve() if args.repo else repo_root()
    plan_path = Path(args.plan).expanduser().resolve()
    plan = load_plan(plan_path)
    selected_agents, items = validate_plan(repo, plan)

    if not config_path().exists():
        print(
            "[WARN] ~/.agent-skills/config.toml does not exist yet. "
            "This is expected on first migration."
        )

    copy_into_catalog(repo, items)
    update_manifests(repo, items)
    rewire_selected_agents(repo, selected_agents)
    post_apply_checks(repo)

    kept = sum(1 for item in items if item["target_category"] != "skip")
    skipped = sum(1 for item in items if item["target_category"] == "skip")
    print("[OK] Applied migration plan.")
    print(f"[OK] Imported skills: {kept}")
    print(f"[OK] Skipped skills: {skipped}")
    print("[OK] Review git diff and create an initial migration commit if the result looks correct.")


if __name__ == "__main__":
    try:
        main()
    except MigrationError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
