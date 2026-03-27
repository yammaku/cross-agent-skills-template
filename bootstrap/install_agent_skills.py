#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(REPO_LIB) not in sys.path:
    sys.path.insert(0, str(REPO_LIB))

from agent_skills.adapters import agent_names
from agent_skills.system import (
    GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR,
    agent_global_view,
    agent_global_install_strategy,
    agent_install_root,
    classify_native_global_root,
    config_dir,
    config_path,
    read_config,
    sync_install_dir,
    write_managed_native_global_state,
    write_config,
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def install_agent(
    agent: str,
    repo: Path,
    backup_root: Path,
    *,
    replace_existing: bool,
) -> None:
    install_root = agent_install_root(repo, agent)
    desired = agent_global_view(repo, agent)
    strategy = agent_global_install_strategy(repo, agent)

    install_root.parent.mkdir(parents=True, exist_ok=True)

    status = classify_native_global_root(repo, agent)

    if strategy == GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR:
        desired_entries = {
            entry.name: entry.resolve()
            for entry in desired.iterdir()
            if entry.name not in {".DS_Store", "__pycache__"}
        }

        if status == "unmanaged" and not replace_existing:
            raise SystemExit(
                "[ERROR] Existing unmanaged skills detected for "
                f"{agent} at {install_root}. "
                "Use the README migration flow, or rerun with --replace-existing "
                "only after the user explicitly chooses a fresh install that backs up and replaces the current root."
            )

        if status == "unmanaged" and (install_root.exists() or install_root.is_symlink()):
            backup_target = backup_root / f"{agent}-skills"
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(install_root), str(backup_target))
            print(f"[OK] {agent}: backed up existing skills to {backup_target}")

        sync_install_dir(
            install_root,
            desired_entries,
            GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR,
            relative=False,
        )
        write_managed_native_global_state(
            install_root,
            repo,
            agent,
            GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR,
        )
        print(f"[OK] {agent}: materialized managed skills at {install_root}")
        return

    if status == "managed":
        print(f"[OK] {agent}: already linked to {desired}")
        return
    if status == "missing":
        install_root.symlink_to(desired)
        print(f"[OK] {agent}: linked {install_root} -> {desired}")
        return
    if status == "empty":
        if install_root.exists():
            install_root.rmdir()
        install_root.symlink_to(desired)
        print(f"[OK] {agent}: linked empty root {install_root} -> {desired}")
        return

    if not replace_existing:
        raise SystemExit(
            "[ERROR] Existing unmanaged skills detected for "
            f"{agent} at {install_root}. "
            "Use the README migration flow, or rerun with --replace-existing "
            "only after the user explicitly chooses a fresh install that backs up and replaces the current root."
        )

    if install_root.exists() or install_root.is_symlink():
        backup_target = backup_root / f"{agent}-skills"
        backup_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(install_root), str(backup_target))
        print(f"[OK] {agent}: backed up existing skills to {backup_target}")

    install_root.symlink_to(desired)
    print(f"[OK] {agent}: linked {install_root} -> {desired}")


def sync_agent_global(repo: Path, agents: list[str]) -> None:
    script = repo / "skills" / "shared" / "manage-agent-skills" / "scripts" / "manage_agent_skills.py"
    env = dict(os.environ)
    env["AGENT_SKILLS_REPO"] = str(repo)
    args = [sys.executable, str(script), "sync-agent-global"]
    for agent in agents:
        args.extend(["--agent", agent])
    subprocess.run(args, check=True, env=env)
    subprocess.run([sys.executable, str(script), "check"], check=True, env=env)


def build_parser() -> argparse.ArgumentParser:
    choices = agent_names(repo_root())
    parser = argparse.ArgumentParser(
        description="Bootstrap the local cross-agent skills registry on a new machine."
    )
    parser.add_argument(
        "--agent",
        action="append",
        choices=choices,
        required=True,
        help="Agent to wire up locally. Repeat for multiple agents.",
    )
    parser.add_argument(
        "--repo",
        help="Path to the local skills-registry repo clone. Defaults to the current repo.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help=(
            "Back up and replace existing unmanaged native skill roots. "
            "Use only after the user explicitly chooses a fresh install instead of migration."
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    repo = Path(args.repo).expanduser().resolve() if args.repo else repo_root()
    if not (repo / "skills").is_dir():
        raise SystemExit(f"[ERROR] Not a skills-registry repo: {repo}")

    requested = set(args.agent)
    existing_repo, installed = read_config()
    if existing_repo and Path(existing_repo).expanduser().resolve() != repo:
        print(
            f"[WARN] Replacing configured repo {Path(existing_repo).expanduser()} with {repo}"
        )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = config_dir() / "backups" / timestamp

    sync_agent_global(repo, sorted(requested))
    for agent in sorted(requested):
        install_agent(agent, repo, backup_root, replace_existing=args.replace_existing)

    write_config(repo, installed | requested)

    print(f"[OK] Wrote config: {config_path()}")
    print(f"[OK] Repo: {repo}")
    print(f"[OK] Installed agents: {', '.join(sorted(installed | requested))}")


if __name__ == "__main__":
    main()
