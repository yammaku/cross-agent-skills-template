#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

REPO_HINT = Path(__file__).resolve()
for _parent in REPO_HINT.parents:
    candidate = _parent / "lib"
    if candidate.is_dir():
        if str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
        break

from agent_skills.adapters import load_agent_adapters
from agent_skills.system import (
    GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR,
    GLOBAL_INSTALL_STRATEGY_SYMLINKED_VIEW,
    NATIVE_GLOBAL_MANAGED_STATE,
    agent_global_install_strategy,
    agent_install_root,
    read_config,
    remove_path,
    sync_install_dir,
    sync_materialized_skill_dir,
    write_managed_native_global_state,
)

RESOURCE_KINDS = ("scripts", "references", "assets")
NAME_RE = re.compile(r"^[a-z0-9-]+$")
IGNORED_NAMES = {".DS_Store", "__pycache__"}
PROJECT_LEGACY_INSTALL_DIR = Path(".agent") / "skills"
PROJECT_BACKUPS_DIR = ".agent-skills-backups"

SKILL_TEMPLATE = """---
name: {name}
description: [TODO: Explain what this skill does and when to use it.]
---

# {title}

## Overview

[TODO: 1-2 sentences explaining what this skill enables]

## Procedure

[TODO: Add the workflow, decision tree, or capability guide that the agent should follow]
"""


class SkillRepoError(Exception):
    pass


def adapters(root: Path):
    return load_agent_adapters(root)


def agent_names(root: Path) -> tuple[str, ...]:
    return tuple(adapters(root).keys())


def title_case(skill_name: str) -> str:
    return " ".join(part.capitalize() for part in skill_name.split("-"))


def short_description(display_name: str) -> str:
    options = [
        f"Help with {display_name} tasks",
        f"Help with {display_name} workflows",
        f"Manage {display_name} tasks and workflows",
        f"{display_name} helper",
    ]
    for option in options:
        if 25 <= len(option) <= 64:
            return option
    trimmed = display_name[:57].rstrip()
    return f"{trimmed} helper"


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def parse_resources(raw: str | None) -> list[str]:
    if not raw:
        return []
    resources = [item.strip() for item in raw.split(",") if item.strip()]
    invalid = [item for item in resources if item not in RESOURCE_KINDS]
    if invalid:
        raise SkillRepoError(
            f"Unknown resource type(s): {', '.join(sorted(invalid))}. "
            f"Allowed: {', '.join(RESOURCE_KINDS)}"
        )
    return resources


def validate_name(name: str) -> None:
    if not NAME_RE.fullmatch(name):
        raise SkillRepoError(
            f"Invalid skill name '{name}'. Use lowercase letters, digits, and hyphens only."
        )
    if name.startswith("-") or name.endswith("-") or "--" in name:
        raise SkillRepoError(f"Invalid skill name '{name}'.")


def parse_string(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return raw


def parse_array(raw: str) -> list[str]:
    raw = raw.strip()
    if not raw.startswith("[") or not raw.endswith("]"):
        return []
    body = raw[1:-1].strip()
    if not body:
        return []
    items: list[str] = []
    for item in body.split(","):
        item = item.strip()
        if not item:
            continue
        items.append(parse_string(item))
    return items


def configured_repo_root() -> Path | None:
    env_path = os.environ.get("AGENT_SKILLS_REPO")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if (candidate / "skills").is_dir():
            return candidate

    config = Path.home() / ".agent-skills" / "config.toml"
    if not config.exists():
        return None

    for raw_line in config.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or not line.startswith("repo_path"):
            continue
        _, value = line.split("=", 1)
        candidate = Path(parse_string(value.strip())).expanduser().resolve()
        if (candidate / "skills").is_dir():
            return candidate
    return None


def repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "skills").is_dir() and (parent / "README.md").exists():
            return parent
    configured = configured_repo_root()
    if configured is not None:
        return configured
    raise SkillRepoError("Could not locate the skills-registry repo root.")


def shared_dir(root: Path) -> Path:
    return root / "skills" / "shared"


def agent_dir(root: Path, agent: str) -> Path:
    if agent not in agent_names(root):
        raise SkillRepoError(f"Unknown agent '{agent}'.")
    return root / "skills" / agent


def agent_global_dir(root: Path, agent: str) -> Path:
    return root / "installs" / "agent-global" / agent


def agent_global_manifest_dir(root: Path) -> Path:
    return root / "manifests" / "agent-global"


def agent_global_manifest_path(root: Path, agent: str) -> Path:
    return agent_global_manifest_dir(root) / f"{agent}.toml"


def project_manifest_path(project: Path) -> Path:
    return project / ".agent-skills.toml"


def project_managed_state_path(project: Path) -> Path:
    return project / ".agents" / ".agent-skills-managed.project.toml"


def project_legacy_install_dir(project: Path) -> Path:
    return project / PROJECT_LEGACY_INSTALL_DIR


def project_backups_dir(project: Path) -> Path:
    return project / PROJECT_BACKUPS_DIR


def interoperable_project_install_dir(project: Path) -> Path:
    return project / ".agents" / "skills"


def project_install_dirs(root: Path, project: Path) -> list[Path]:
    paths: list[Path] = [interoperable_project_install_dir(project)]
    for adapter in adapters(root).values():
        native = adapter.project_path(project)
        if native not in paths:
            paths.append(native)
    return paths


def project_candidate_skill_roots(root: Path, project: Path) -> list[Path]:
    paths = project_install_dirs(root, project)
    legacy = project_legacy_install_dir(project)
    if legacy not in paths:
        paths.append(legacy)
    return paths


def empty_project_manifest() -> dict[str, set[str]]:
    return {"shared": set()}


def read_project_manifest(path: Path) -> dict[str, set[str]]:
    data = empty_project_manifest()
    if not path.exists():
        return data

    section = None
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if section != "skills" or "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if key in data:
            data[key] = set(parse_array(value))
            continue
        legacy_values = parse_array(value)
        if legacy_values:
            raise SkillRepoError(
                "Project installs are shared-only. "
                f"Found unsupported project skill bucket '{key}' in {path}. "
                "Move agent-specific skills to agent-global manifests instead."
            )
    return data


def write_project_manifest(path: Path, data: dict[str, set[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["[skills]"]
    values = ", ".join(f'"{value}"' for value in sorted(data["shared"]))
    lines.append(f"shared = [{values}]")
    lines.append("")
    path.write_text("\n".join(lines))


def read_agent_global_manifest(path: Path) -> list[str]:
    if not path.exists():
        return []
    match = re.search(r"skills\s*=\s*(\[[\s\S]*?\])", path.read_text())
    if match:
        return parse_array(match.group(1))
    return []


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


def read_project_managed_state(project: Path) -> tuple[str | None, set[str]]:
    path = project_managed_state_path(project)
    if not path.exists():
        return None, set()

    profile = None
    names: set[str] = set()
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if key == "profile":
            profile = parse_string(value)
        elif key == "agent":
            profile = parse_string(value)
        elif key == "names":
            names = set(parse_array(value))
    return profile, names


def write_project_managed_state(project: Path, names: set[str]) -> None:
    path = project_managed_state_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    values = ", ".join(f'"{value}"' for value in sorted(names))
    content = "\n".join(
        [
            'profile = "shared-project"',
            f"names = [{values}]",
            "",
        ]
    )
    path.write_text(content)


def iter_catalog_shared(root: Path):
    for path in sorted(shared_dir(root).iterdir()):
        if path.name.startswith(".") or path.name in IGNORED_NAMES:
            continue
        if path.is_dir() and not path.is_symlink():
            yield path


def skill_path(base: Path, name: str) -> Path:
    return base / name


def exists_or_link(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def path_is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def visible_skill_entry_names(path: Path) -> list[str]:
    if not path.is_dir():
        return []
    names: list[str] = []
    for child in sorted(path.iterdir(), key=lambda item: item.name):
        if child.name.startswith(".") or child.name in IGNORED_NAMES:
            continue
        if child.is_dir() or child.is_symlink():
            names.append(child.name)
    return names


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_fingerprint(path: Path) -> tuple[tuple[str, ...], ...]:
    entries: list[tuple[str, ...]] = []
    for current_root, dirnames, filenames in os.walk(path, topdown=True, followlinks=True):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_NAMES)
        filenames = sorted(name for name in filenames if name not in IGNORED_NAMES)
        rel_root = os.path.relpath(current_root, start=path)
        rel_root = "" if rel_root == "." else rel_root.replace(os.sep, "/")
        entries.append(("dir", rel_root))
        for filename in filenames:
            file_path = Path(current_root) / filename
            rel_path = f"{rel_root}/{filename}" if rel_root else filename
            executable = "x" if os.access(file_path, os.X_OK) else "-"
            entries.append(("file", rel_path, executable, file_digest(file_path)))
    return tuple(entries)


def project_legacy_mirror_target(project: Path, name: str) -> Path:
    return interoperable_project_install_dir(project) / name


def is_legacy_project_mirror_entry(project: Path, path: Path, name: str) -> bool:
    if not path.is_symlink():
        return False
    try:
        return path.resolve() == project_legacy_mirror_target(project, name).resolve()
    except FileNotFoundError:
        return False


def backup_path(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.is_symlink():
        dest.symlink_to(source.readlink())
        return
    if source.is_dir():
        shutil.copytree(source, dest, symlinks=True)
        return
    shutil.copy2(source, dest, follow_symlinks=False)


def write_scaffold(path: Path, name: str, resources: list[str]) -> None:
    path.mkdir(parents=True, exist_ok=False)
    (path / "SKILL.md").write_text(SKILL_TEMPLATE.format(name=name, title=title_case(name)))

    agents_dir = path / "agents"
    agents_dir.mkdir()
    display = title_case(name)
    default_prompt = f"Help create or update the {display} skill."
    openai_yaml = "\n".join(
        [
            "interface:",
            f"  display_name: {yaml_quote(display)}",
            f"  short_description: {yaml_quote(short_description(display))}",
            f"  default_prompt: {yaml_quote(default_prompt)}",
            "",
        ]
    )
    (agents_dir / "openai.yaml").write_text(openai_yaml)

    for resource in resources:
        (path / resource).mkdir()


def ensure_not_present(path: Path, label: str) -> None:
    if exists_or_link(path):
        raise SkillRepoError(f"{label} already exists: {path}")


def catalog_path(root: Path, scope: str, name: str) -> Path:
    if scope == "shared":
        return skill_path(shared_dir(root), name)
    if scope in agent_names(root):
        return skill_path(agent_dir(root, scope), name)
    raise SkillRepoError(f"Unknown catalog scope '{scope}'.")


def resolve_catalog_source(root: Path, agent: str, name: str) -> tuple[str, Path]:
    shared_skill = skill_path(shared_dir(root), name)
    if shared_skill.is_dir() and not shared_skill.is_symlink():
        return "shared", shared_skill

    agent_skill = skill_path(agent_dir(root, agent), name)
    if agent_skill.is_dir() and not agent_skill.is_symlink():
        return agent, agent_skill

    raise SkillRepoError(f"Could not find skill '{name}' in shared or {agent} catalog.")


def resolve_shared_catalog_source(root: Path, name: str) -> Path:
    shared_skill = skill_path(shared_dir(root), name)
    if shared_skill.is_dir() and not shared_skill.is_symlink():
        return shared_skill
    raise SkillRepoError(
        f"Project installs are shared-only. Could not find shared skill '{name}'."
    )


def parse_catalog_ref(root: Path, ref: str) -> tuple[str, str, Path]:
    if "/" not in ref:
        raise SkillRepoError(
            f"Invalid skill ref '{ref}'. Use '<scope>/<name>' like 'shared/example-skill'."
        )
    scope, name = ref.split("/", 1)
    if not scope or not name:
        raise SkillRepoError(
            f"Invalid skill ref '{ref}'. Use '<scope>/<name>' like 'shared/example-skill'."
        )
    source = catalog_path(root, scope, name)
    if not source.is_dir() or source.is_symlink():
        raise SkillRepoError(f"Catalog ref points to missing skill: {ref}")
    return scope, name, source


def normalize_catalog_ref(root: Path, agent: str, raw: str) -> str:
    if "/" in raw:
        scope, name, _ = parse_catalog_ref(root, raw)
        return f"{scope}/{name}"

    scope, _ = resolve_catalog_source(root, agent, raw)
    return f"{scope}/{raw}"


def normalize_project_skill_name(root: Path, raw: str) -> str:
    if "/" in raw:
        scope, name, _ = parse_catalog_ref(root, raw)
        if scope != "shared":
            raise SkillRepoError(
                "Project installs are shared-only. "
                f"Use agent-global install for '{scope}/{name}'."
            )
        return name

    resolve_shared_catalog_source(root, raw)
    return raw


def relative_link(source: Path, dest_dir: Path) -> str:
    return os.path.relpath(source, start=dest_dir)


def ensure_symlink(dest: Path, source: Path, *, relative: bool) -> None:
    link_target = relative_link(source, dest.parent) if relative else str(source.resolve())
    if dest.is_symlink():
        current = dest.readlink().as_posix()
        if current != link_target:
            dest.unlink()
            dest.symlink_to(link_target)
        return
    if dest.exists():
        raise SkillRepoError(f"Cannot create managed link at {dest}: path already exists.")
    dest.symlink_to(link_target)


def materialize_agent_global(root: Path, agent: str, refs: list[str]) -> None:
    dest_dir = agent_global_dir(root, agent)
    desired: dict[str, Path] = {}
    for ref in refs:
        _, name, source = parse_catalog_ref(root, ref)
        if name in desired:
            raise SkillRepoError(
                f"Agent-global manifest for {agent} has duplicate install name '{name}'."
            )
        desired[name] = source
    sync_install_dir(
        dest_dir,
        desired,
        agent_global_install_strategy(root, agent),
        relative=True,
    )


def sync_materialized_native_root(root: Path, agent: str, refs: list[str]) -> None:
    desired: dict[str, Path] = {}
    for ref in refs:
        _, name, source = parse_catalog_ref(root, ref)
        desired[name] = source

    native_root = agent_install_root(root, agent)
    sync_install_dir(
        native_root,
        desired,
        GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR,
        relative=False,
    )
    write_managed_native_global_state(
        native_root,
        root,
        agent,
        GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR,
    )


def sync_agent_global(root: Path, agents: list[str] | None = None) -> None:
    targets = agents or list(agent_names(root))
    for agent in targets:
        refs = read_agent_global_manifest(agent_global_manifest_path(root, agent))
        materialize_agent_global(root, agent, refs)

    configured_repo, installed_agents = read_config()
    if configured_repo and Path(configured_repo).expanduser().resolve() == root.resolve():
        for agent in targets:
            if agent not in installed_agents:
                continue
            if agent_global_install_strategy(root, agent) != GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR:
                continue
            refs = read_agent_global_manifest(agent_global_manifest_path(root, agent))
            sync_materialized_native_root(root, agent, refs)
    print("[OK] Agent-global install views are synced.")


def materialize_project_dir(
    dest_dir: Path,
    desired: dict[str, Path],
    previous_names: set[str],
) -> set[str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing_names = set()

    for name, source in desired.items():
        dest = dest_dir / name
        existing_names.add(name)
        if dest.exists() or dest.is_symlink():
            if name not in previous_names:
                raise SkillRepoError(
                    f"Project install path already contains unmanaged entry: {dest}"
                )
        sync_materialized_skill_dir(dest, source, relative=False)

    for name in previous_names - existing_names:
        stale = dest_dir / name
        if stale.exists() or stale.is_symlink():
            remove_path(stale)

    return existing_names


def sync_project(root: Path, project: Path) -> None:
    manifest = read_project_manifest(project_manifest_path(project))
    desired: dict[str, Path] = {}
    for name in manifest["shared"]:
        desired[name] = skill_path(shared_dir(root), name)

    for name, source in desired.items():
        if not source.is_dir() or source.is_symlink():
            raise SkillRepoError(f"Project manifest points to missing catalog skill: {name}")

    previous_agent, previous_names = read_project_managed_state(project)
    existing_names = set()
    for install_dir in project_install_dirs(root, project):
        existing_names = materialize_project_dir(install_dir, desired, previous_names)

    write_project_managed_state(project, existing_names)
    print(
        "[OK] Project install view is synced. "
        "Shared project surfaces updated "
        f"(previous managed profile: {previous_agent or 'none'})."
    )


def discover_project_adopt_names(
    root: Path,
    project: Path,
    previous_names: set[str],
    source_dir: Path | None,
) -> list[str]:
    names: set[str] = set()
    managed_roots = set(project_install_dirs(root, project))
    for root_dir in ([source_dir] if source_dir is not None else project_candidate_skill_roots(root, project)):
        if root_dir is None or not root_dir.is_dir():
            continue
        for name in visible_skill_entry_names(root_dir):
            entry = root_dir / name
            if root_dir in managed_roots and name in previous_names:
                continue
            if root_dir == project_legacy_install_dir(project) and is_legacy_project_mirror_entry(
                project, entry, name
            ):
                continue
            names.add(name)
    return sorted(names)


def collect_project_adopt_candidates(
    root: Path,
    project: Path,
    name: str,
    previous_names: set[str],
    source_dir: Path | None,
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    managed_roots = set(project_install_dirs(root, project))
    roots = [source_dir] if source_dir is not None else project_candidate_skill_roots(root, project)

    for index, root_dir in enumerate(roots):
        if root_dir is None:
            continue
        entry = root_dir / name
        if not exists_or_link(entry):
            continue
        try:
            if not entry.is_dir():
                continue
        except FileNotFoundError:
            continue
        if source_dir is None and root_dir in managed_roots and name in previous_names:
            continue
        if source_dir is None and root_dir == project_legacy_install_dir(project):
            if is_legacy_project_mirror_entry(project, entry, name):
                continue
        candidates.append(
            {
                "entry": entry,
                "root": root_dir,
                "index": index,
                "is_symlink": entry.is_symlink(),
                "fingerprint": directory_fingerprint(entry),
            }
        )
    return candidates


def choose_project_adopt_source(
    root: Path,
    project: Path,
    name: str,
    previous_names: set[str],
    source_dir: Path | None,
) -> Path:
    candidates = collect_project_adopt_candidates(root, project, name, previous_names, source_dir)
    if not candidates:
        roots = [source_dir] if source_dir is not None else project_candidate_skill_roots(root, project)
        rendered_roots = ", ".join(str(path) for path in roots if path is not None)
        raise SkillRepoError(
            f"Could not find a local project skill source for '{name}' under {rendered_roots}."
        )

    chosen = candidates[0]
    for candidate in candidates[1:]:
        if candidate["fingerprint"] != chosen["fingerprint"]:
            locations = ", ".join(str(item["entry"]) for item in candidates)
            raise SkillRepoError(
                f"Project skill '{name}' has conflicting local contents across: {locations}. "
                "Reconcile them or rerun adopt-project with --source-dir."
            )
        if bool(chosen["is_symlink"]) and not bool(candidate["is_symlink"]):
            chosen = candidate
            continue
        if bool(chosen["is_symlink"]) == bool(candidate["is_symlink"]) and int(candidate["index"]) < int(
            chosen["index"]
        ):
            chosen = candidate
    return Path(chosen["entry"])


def import_project_skill_into_shared(root: Path, name: str, source: Path) -> bool:
    validate_name(name)
    destination = skill_path(shared_dir(root), name)
    if destination.exists():
        if destination.is_symlink():
            raise SkillRepoError(
                f"Shared catalog path for '{name}' is a symlink. Resolve that before adopting project skills."
            )
        if directory_fingerprint(destination) != directory_fingerprint(source):
            raise SkillRepoError(
                f"Shared catalog skill '{name}' already exists but differs from the local project copy at {source}. "
                "Rename it, reconcile it manually, or fork deliberately before adoption."
            )
        return False

    shutil.copytree(source, destination, symlinks=False)
    return True


def backup_and_remove_project_entry(project: Path, backup_root: Path, entry: Path) -> None:
    relative = entry.relative_to(project)
    destination = backup_root / relative
    if destination.exists() or destination.is_symlink():
        raise SkillRepoError(f"Backup path already exists: {destination}")
    backup_path(entry, destination)
    remove_path(entry)


def refresh_legacy_project_mirror(project: Path, names: set[str]) -> None:
    legacy_root = project_legacy_install_dir(project)
    if not legacy_root.exists():
        return
    legacy_root.mkdir(parents=True, exist_ok=True)
    source_root = interoperable_project_install_dir(project)
    for name in sorted(names):
        target = source_root / name
        if not target.exists() and not target.is_symlink():
            continue
        ensure_symlink(legacy_root / name, target, relative=True)


def adopt_project(
    root: Path,
    project: Path,
    raw_names: list[str],
    *,
    source_dir: Path | None,
) -> None:
    previous_profile, previous_names = read_project_managed_state(project)
    if source_dir is not None:
        if not source_dir.exists() or not source_dir.is_dir():
            raise SkillRepoError(f"--source-dir must be an existing directory: {source_dir}")
        if not path_is_within(source_dir, project):
            raise SkillRepoError("--source-dir must be inside the target project.")

    names = raw_names[:]
    if not names:
        names = discover_project_adopt_names(root, project, previous_names, source_dir)
    if not names:
        raise SkillRepoError(
            "No adoptable local project skills were found. "
            "If the project already tracks .agent-skills.toml, try sync-project instead."
        )

    for name in names:
        validate_name(name)

    unique_names = sorted(dict.fromkeys(names))
    imported: list[str] = []
    reused: list[str] = []
    for name in unique_names:
        source = choose_project_adopt_source(root, project, name, previous_names, source_dir)
        if import_project_skill_into_shared(root, name, source):
            imported.append(name)
        else:
            reused.append(name)

    backup_root = project_backups_dir(project) / f"adopt-project-{timestamp_slug()}"
    cleanup_roots = project_candidate_skill_roots(root, project)
    if source_dir is not None and source_dir not in cleanup_roots:
        cleanup_roots.append(source_dir)

    for name in unique_names:
        for root_dir in cleanup_roots:
            entry = root_dir / name
            if not exists_or_link(entry):
                continue
            backup_and_remove_project_entry(project, backup_root, entry)

    update_project_manifest_with_skills(
        root,
        project_manifest_path(project),
        unique_names,
        add=True,
    )
    sync_project(root, project)

    manifest = read_project_manifest(project_manifest_path(project))
    refresh_legacy_project_mirror(project, manifest["shared"])

    print(
        "[OK] Adopted project-local skills into the shared registry and resynced the project."
    )
    if imported:
        print(f"[OK] Imported into shared catalog: {', '.join(imported)}")
    if reused:
        print(f"[OK] Already matched existing shared catalog skills: {', '.join(reused)}")
    if backup_root.exists():
        print(f"[OK] Backups saved under: {backup_root}")
    if previous_profile:
        print(f"[OK] Previous managed project profile: {previous_profile}")


def update_project_manifest_with_skills(
    root: Path,
    manifest_path: Path,
    raw_names: list[str],
    *,
    add: bool,
) -> None:
    manifest = read_project_manifest(manifest_path)
    for raw in raw_names:
        name = normalize_project_skill_name(root, raw)
        bucket = manifest["shared"]
        if add:
            bucket.add(name)
        else:
            bucket.discard(name)
    write_project_manifest(manifest_path, manifest)


def update_agent_global_manifest_with_skills(
    root: Path,
    agent: str,
    raw_names: list[str],
    *,
    add: bool,
) -> None:
    path = agent_global_manifest_path(root, agent)
    refs = set(read_agent_global_manifest(path))
    for raw in raw_names:
        ref = normalize_catalog_ref(root, agent, raw)
        if add:
            refs.add(ref)
        else:
            refs.discard(ref)
    write_agent_global_manifest(path, refs)


def create_shared(root: Path, name: str, resources: list[str]) -> None:
    shared_skill = skill_path(shared_dir(root), name)
    ensure_not_present(shared_skill, "Shared skill")
    for agent in agent_names(root):
        existing = skill_path(agent_dir(root, agent), name)
        if exists_or_link(existing):
            raise SkillRepoError(
                f"Cannot create shared skill '{name}': {agent} already has that name."
            )
    write_scaffold(shared_skill, name, resources)
    print(f"[OK] Created shared catalog skill: {shared_skill}")


def create_agent(root: Path, agent: str, name: str, resources: list[str]) -> None:
    shared_skill = skill_path(shared_dir(root), name)
    if exists_or_link(shared_skill):
        raise SkillRepoError(
            f"Shared skill '{name}' already exists. Fork it with a renamed agent-specific variant instead."
        )
    agent_skill = skill_path(agent_dir(root, agent), name)
    ensure_not_present(agent_skill, "Agent-specific skill")
    write_scaffold(agent_skill, name, resources)
    print(f"[OK] Created {agent}-specific catalog skill: {agent_skill}")


def promote(root: Path, agent: str, name: str) -> None:
    source = skill_path(agent_dir(root, agent), name)
    destination = skill_path(shared_dir(root), name)

    if not source.exists() or source.is_symlink():
        raise SkillRepoError(
            f"Expected a real agent-owned catalog folder at {source} before promotion."
        )
    ensure_not_present(destination, "Shared skill")

    for other in agent_names(root):
        if other == agent:
            continue
        conflict = skill_path(agent_dir(root, other), name)
        if conflict.exists() and not conflict.is_symlink():
            raise SkillRepoError(
                f"Cannot promote '{name}': {other} already has a real folder with that name."
            )

    shutil.move(str(source), str(destination))
    print(f"[OK] Promoted {agent}/{name} to shared/{name}")


def fork_shared(root: Path, agent: str, name: str, new_name: str) -> None:
    source = skill_path(shared_dir(root), name)
    if not source.exists() or source.is_symlink():
        raise SkillRepoError(f"Shared skill '{name}' does not exist as a real folder.")
    if new_name == name:
        raise SkillRepoError("Forked agent-specific variant must use a different name.")
    variant = skill_path(agent_dir(root, agent), new_name)
    ensure_not_present(variant, "Agent-specific variant")
    shared_variant = skill_path(shared_dir(root), new_name)
    ensure_not_present(shared_variant, "Shared skill")
    shutil.copytree(source, variant, symlinks=True)
    print(f"[OK] Forked shared/{name} to {agent}/{new_name}")


def check(root: Path) -> None:
    issues: list[str] = []

    shared_names = set()
    for shared_skill in iter_catalog_shared(root):
        shared_names.add(shared_skill.name)

    shared_dir_path = shared_dir(root)
    for path in shared_dir_path.iterdir():
        if path.name in IGNORED_NAMES or path.name.startswith("."):
            continue
        if not path.is_dir():
            issues.append(f"shared/{path.name} must be a directory")
        elif path.is_symlink():
            issues.append(f"shared/{path.name} must be a real folder, not a symlink")

    catalog_agent_names = agent_names(root)
    for agent in catalog_agent_names:
        for path in agent_dir(root, agent).iterdir():
            if path.name in IGNORED_NAMES or path.name.startswith("."):
                continue
            if path.is_symlink():
                issues.append(f"{agent}/{path.name} should not be a symlink in the catalog")
                continue
            if path.is_dir():
                if path.name in shared_names:
                    issues.append(f"{agent}/{path.name} shadows a shared skill name")

    installs_root = root / "installs" / "agent-global"
    for agent in catalog_agent_names:
        refs = read_agent_global_manifest(agent_global_manifest_path(root, agent))
        strategy = agent_global_install_strategy(root, agent)
        desired_names: set[str] = set()
        for ref in refs:
            try:
                scope, name, _ = parse_catalog_ref(root, ref)
            except SkillRepoError as exc:
                issues.append(f"{agent} manifest: {exc}")
                continue
            if scope != "shared" and scope != agent:
                issues.append(
                    f"{agent} manifest references '{ref}', which belongs to a different agent."
                )
            if name in desired_names:
                issues.append(f"{agent} manifest installs duplicate skill name '{name}'.")
            desired_names.add(name)

        if installs_root.exists():
            install_dir = agent_global_dir(root, agent)
            if not install_dir.exists():
                if desired_names:
                    issues.append(f"installs/agent-global/{agent} is missing")
                continue
            actual: set[str] = set()
            for path in install_dir.iterdir():
                if path.name in IGNORED_NAMES or path.name == NATIVE_GLOBAL_MANAGED_STATE:
                    continue
                actual.add(path.name)
                if strategy == GLOBAL_INSTALL_STRATEGY_SYMLINKED_VIEW and not path.is_symlink():
                    issues.append(
                        f"installs/agent-global/{agent}/{path.name} should be a symlink"
                    )
                if (
                    strategy == GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR
                    and path.is_symlink()
                ):
                    issues.append(
                        f"installs/agent-global/{agent}/{path.name} should be a real directory"
                    )
                if (
                    strategy == GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR
                    and not path.is_dir()
                ):
                    issues.append(
                        f"installs/agent-global/{agent}/{path.name} must be a directory"
                    )
            missing = desired_names - actual
            extra = actual - desired_names
            for name in sorted(missing):
                issues.append(f"installs/agent-global/{agent}/{name} is missing")
            for name in sorted(extra):
                issues.append(f"installs/agent-global/{agent}/{name} is extra")

    if issues:
        print("[ERROR] Skill system check failed:")
        for issue in issues:
            print(f" - {issue}")
        raise SystemExit(1)

    print("[OK] Skill system check passed.")


def build_parser() -> argparse.ArgumentParser:
    choices = agent_names(repo_root())
    parser = argparse.ArgumentParser(
        description="Manage the agent-skills catalog, agent-global installs, and project installs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_shared_parser = subparsers.add_parser(
        "create", help="Create a new shared catalog skill."
    )
    create_shared_parser.add_argument("name")
    create_shared_parser.add_argument("--resources")

    create_agent_parser = subparsers.add_parser(
        "create-agent", help="Create a new agent-specific catalog skill."
    )
    create_agent_parser.add_argument("agent", choices=choices)
    create_agent_parser.add_argument("name")
    create_agent_parser.add_argument("--resources")

    promote_parser = subparsers.add_parser(
        "promote", help="Promote an agent-specific catalog skill into shared."
    )
    promote_parser.add_argument("agent", choices=choices)
    promote_parser.add_argument("name")

    fork_parser = subparsers.add_parser(
        "fork", help="Create a renamed agent-specific fork of a shared skill."
    )
    fork_parser.add_argument("agent", choices=choices)
    fork_parser.add_argument("name")
    fork_parser.add_argument("--new-name")

    sync_global_parser = subparsers.add_parser(
        "sync-agent-global",
        help="Sync agent-global install views from manifests/agent-global/<agent>.toml.",
    )
    sync_global_parser.add_argument("--agent", action="append", choices=choices)

    sync_project_parser = subparsers.add_parser(
        "sync-project",
        help="Sync shared project skill installs from .agent-skills.toml into all project surfaces.",
    )
    sync_project_parser.add_argument("--project", required=True)

    adopt_project_parser = subparsers.add_parser(
        "adopt-project",
        help=(
            "Adopt unmanaged project-local skills into the shared catalog, "
            "update .agent-skills.toml, and resync project install surfaces."
        ),
    )
    adopt_project_parser.add_argument("--project", required=True)
    adopt_project_parser.add_argument(
        "--source-dir",
        help="Optional project-local directory to treat as the canonical source root.",
    )
    adopt_project_parser.add_argument("skills", nargs="*")

    install_global_parser = subparsers.add_parser(
        "install-agent-global",
        help="Add skills to one agent-global manifest and resync only that agent.",
    )
    install_global_parser.add_argument("--agent", required=True, choices=choices)
    install_global_parser.add_argument("skills", nargs="+")

    remove_global_parser = subparsers.add_parser(
        "remove-agent-global",
        help="Remove skills from one agent-global manifest and resync only that agent.",
    )
    remove_global_parser.add_argument("--agent", required=True, choices=choices)
    remove_global_parser.add_argument("skills", nargs="+")

    install_project_parser = subparsers.add_parser(
        "install-project",
        help="Add shared skills to a project's .agent-skills.toml and sync all project install surfaces.",
    )
    install_project_parser.add_argument("--project", required=True)
    install_project_parser.add_argument("skills", nargs="+")

    remove_project_parser = subparsers.add_parser(
        "remove-project",
        help="Remove shared skills from a project's .agent-skills.toml and sync all project install surfaces.",
    )
    remove_project_parser.add_argument("--project", required=True)
    remove_project_parser.add_argument("skills", nargs="+")

    subparsers.add_parser(
        "check", help="Validate catalog and agent-global install invariants."
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    root = repo_root()

    try:
        if args.command == "create":
            validate_name(args.name)
            create_shared(root, args.name, parse_resources(args.resources))
        elif args.command == "create-agent":
            validate_name(args.name)
            create_agent(root, args.agent, args.name, parse_resources(args.resources))
        elif args.command == "promote":
            validate_name(args.name)
            promote(root, args.agent, args.name)
        elif args.command == "fork":
            validate_name(args.name)
            new_name = args.new_name or f"{args.name}-{args.agent}"
            validate_name(new_name)
            fork_shared(root, args.agent, args.name, new_name)
        elif args.command == "sync-agent-global":
            sync_agent_global(root, args.agent)
        elif args.command == "sync-project":
            sync_project(root, Path(args.project).expanduser().resolve())
        elif args.command == "adopt-project":
            adopt_project(
                root,
                Path(args.project).expanduser().resolve(),
                args.skills,
                source_dir=(
                    Path(args.source_dir).expanduser().resolve()
                    if args.source_dir
                    else None
                ),
            )
        elif args.command == "install-agent-global":
            update_agent_global_manifest_with_skills(
                root,
                args.agent,
                args.skills,
                add=True,
            )
            sync_agent_global(root, [args.agent])
        elif args.command == "remove-agent-global":
            update_agent_global_manifest_with_skills(
                root,
                args.agent,
                args.skills,
                add=False,
            )
            sync_agent_global(root, [args.agent])
        elif args.command == "install-project":
            project = Path(args.project).expanduser().resolve()
            update_project_manifest_with_skills(
                root,
                project_manifest_path(project),
                args.skills,
                add=True,
            )
            sync_project(root, project)
        elif args.command == "remove-project":
            project = Path(args.project).expanduser().resolve()
            update_project_manifest_with_skills(
                root,
                project_manifest_path(project),
                args.skills,
                add=False,
            )
            sync_project(root, project)
        elif args.command == "check":
            check(root)
    except SkillRepoError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
