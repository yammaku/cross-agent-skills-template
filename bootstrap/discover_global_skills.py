#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(REPO_LIB) not in sys.path:
    sys.path.insert(0, str(REPO_LIB))

from agent_skills.adapters import agent_names
from agent_skills.system import (
    IGNORED_NAMES,
    agent_global_view,
    agent_install_root,
    classify_native_global_root,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    choices = agent_names(repo_root())
    parser = argparse.ArgumentParser(
        description="Discover existing native agent-global skills for migration planning."
    )
    parser.add_argument(
        "--agent",
        action="append",
        choices=choices,
        required=True,
        help="Agent to inspect. Repeat for multiple agents.",
    )
    parser.add_argument(
        "--repo",
        help="Path to the local skills-registry repo clone. Defaults to the current repo.",
    )
    parser.add_argument(
        "--output",
        help="Write the discovery JSON to this file. Defaults to stdout.",
    )
    return parser


def entry_kind(path: Path) -> str:
    if path.is_dir():
        return "directory"
    if path.is_file():
        return "file"
    if path.is_symlink():
        return "symlink"
    return "missing"


def iter_skill_entries(root: Path) -> list[dict[str, object]]:
    if not (root.exists() or root.is_symlink()) or not root.is_dir():
        return []

    entries: list[dict[str, object]] = []
    for child in sorted(root.iterdir(), key=lambda item: item.name):
        if child.name in IGNORED_NAMES:
            continue
        skill_md = child / "SKILL.md"
        entries.append(
            {
                "name": child.name,
                "path": str(child),
                "kind": entry_kind(child),
                "is_symlink": child.is_symlink(),
                "skill_md_path": str(skill_md) if skill_md.exists() else None,
                "has_skill_md": skill_md.exists(),
            }
        )
    return entries


def discover_agent(repo: Path, agent: str) -> dict[str, object]:
    native_root = agent_install_root(repo, agent)
    managed_root = agent_global_view(repo, agent)
    status = classify_native_global_root(repo, agent)
    entries = iter_skill_entries(native_root)

    notes: list[str] = []
    if status == "managed":
        notes.append("Already linked to this repo's generated agent-global install view.")
    elif status == "missing":
        notes.append("No native global skill root exists for this agent on this machine.")
    elif status == "empty":
        notes.append("Native global skill root exists but is effectively empty.")
    else:
        notes.append("Unmanaged native global skill root detected; eligible for migration review.")

    return {
        "agent": agent,
        "native_global_root": str(native_root),
        "managed_global_root": str(managed_root),
        "status": status,
        "entry_count": len(entries),
        "entries": entries,
        "notes": notes,
    }


def main() -> None:
    args = build_parser().parse_args()
    repo = Path(args.repo).expanduser().resolve() if args.repo else repo_root()

    payload = {
        "format_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_path": str(repo),
        "selected_agents": sorted(set(args.agent)),
        "agents": {
            agent: discover_agent(repo, agent)
            for agent in sorted(set(args.agent))
        },
    }

    output = json.dumps(payload, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output).expanduser().resolve()
        path.write_text(output + "\n")
        print(f"[OK] Wrote discovery report: {path}")
        return

    print(output)


if __name__ == "__main__":
    main()
