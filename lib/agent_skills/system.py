from __future__ import annotations

import os
import shutil
from pathlib import Path

from agent_skills.adapters import agent_names, load_agent_adapters, parse_array, parse_string

IGNORED_NAMES = {".DS_Store", "__pycache__"}
GLOBAL_INSTALL_STRATEGY_SYMLINKED_VIEW = "symlinked-view"
GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR = "materialized-skill-dir"
NATIVE_GLOBAL_MANAGED_STATE = ".agent-skills-managed.agent-global.toml"


def config_dir() -> Path:
    return Path.home() / ".agent-skills"


def config_path() -> Path:
    return config_dir() / "config.toml"


def read_config() -> tuple[str | None, set[str]]:
    path = config_path()
    if not path.exists():
        return None, set()

    repo = None
    agents: set[str] = set()
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("repo_path"):
            _, value = line.split("=", 1)
            repo = parse_string(value.strip())
        elif line.startswith("installed_agents"):
            _, value = line.split("=", 1)
            agents = set(parse_array(value.strip()))
    return repo, agents


def escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_config(repo: Path, agents: set[str]) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    ordered = [agent for agent in agent_names(repo) if agent in agents]
    agent_list = ", ".join(f'"{agent}"' for agent in ordered)
    content = "\n".join(
        [
            f'repo_path = "{escape(str(repo))}"',
            f"installed_agents = [{agent_list}]",
            "",
        ]
    )
    config_path().write_text(content)


def agent_adapter(repo: Path, agent: str):
    adapters = load_agent_adapters(repo)
    return adapters[agent]


def agent_install_root(repo: Path, agent: str) -> Path:
    return agent_adapter(repo, agent).global_path()


def agent_global_view(repo: Path, agent: str) -> Path:
    return repo / "installs" / "agent-global" / agent


def agent_global_install_strategy(repo: Path, agent: str) -> str:
    return agent_adapter(repo, agent).global_install_strategy


def managed_native_global_state_path(install_root: Path) -> Path:
    return install_root / NATIVE_GLOBAL_MANAGED_STATE


def read_managed_native_global_state(install_root: Path) -> dict[str, str]:
    path = managed_native_global_state_path(install_root)
    if not path.exists():
        return {}

    data: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        data[key] = parse_string(value)
    return data


def write_managed_native_global_state(
    install_root: Path,
    repo: Path,
    agent: str,
    strategy: str,
) -> None:
    path = managed_native_global_state_path(install_root)
    path.write_text(
        "\n".join(
            [
                f'repo_path = "{escape(str(repo.resolve()))}"',
                f'agent = "{escape(agent)}"',
                f'strategy = "{escape(strategy)}"',
                "",
            ]
        )
    )


def relative_link(source: Path, dest_dir: Path) -> str:
    return os.path.relpath(source, start=dest_dir)


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if path.is_dir():
        shutil.rmtree(path)


def ensure_managed_symlink(dest: Path, source: Path, *, relative: bool) -> None:
    link_target = relative_link(source, dest.parent) if relative else str(source.resolve())
    if dest.is_symlink():
        current = dest.readlink().as_posix()
        if current == link_target:
            return
        dest.unlink()
    elif dest.exists():
        remove_path(dest)
    dest.symlink_to(link_target)


def sync_materialized_skill_dir(dest: Path, source: Path, *, relative: bool) -> None:
    if dest.is_symlink() or dest.is_file():
        remove_path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    desired_children: set[str] = set()
    for child in sorted(source.iterdir(), key=lambda item: item.name):
        if child.name in IGNORED_NAMES:
            continue
        desired_children.add(child.name)
        ensure_managed_symlink(dest / child.name, child.resolve(), relative=relative)

    for child in sorted(dest.iterdir(), key=lambda item: item.name):
        if child.name in IGNORED_NAMES or child.name == NATIVE_GLOBAL_MANAGED_STATE:
            continue
        if child.name not in desired_children:
            remove_path(child)


def sync_install_dir(
    dest_dir: Path,
    desired: dict[str, Path],
    strategy: str,
    *,
    relative: bool,
) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)

    existing = {
        path.name: path
        for path in dest_dir.iterdir()
        if path.name not in IGNORED_NAMES and path.name != NATIVE_GLOBAL_MANAGED_STATE
    }
    for name, path in existing.items():
        if name not in desired:
            remove_path(path)

    for name, source in desired.items():
        dest = dest_dir / name
        if strategy == GLOBAL_INSTALL_STRATEGY_SYMLINKED_VIEW:
            ensure_managed_symlink(dest, source, relative=relative)
        elif strategy == GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR:
            sync_materialized_skill_dir(dest, source, relative=relative)
        else:
            raise ValueError(f"Unknown global install strategy: {strategy}")


def is_effectively_empty(path: Path, *, ignored_names: set[str] | None = None) -> bool:
    ignored = IGNORED_NAMES | (ignored_names or set())
    if not path.is_dir():
        return False
    for child in path.iterdir():
        if child.name in ignored:
            continue
        return False
    return True


def classify_native_global_root(repo: Path, agent: str) -> str:
    install_root = agent_install_root(repo, agent)
    strategy = agent_global_install_strategy(repo, agent)

    if strategy == GLOBAL_INSTALL_STRATEGY_SYMLINKED_VIEW:
        desired = agent_global_view(repo, agent)
        if install_root.is_symlink():
            try:
                current = install_root.resolve()
            except FileNotFoundError:
                return "unmanaged"
            if current == desired.resolve():
                return "managed"
            return "unmanaged"
        if not install_root.exists():
            return "missing"
        if is_effectively_empty(install_root):
            return "empty"
        return "unmanaged"

    if strategy == GLOBAL_INSTALL_STRATEGY_MATERIALIZED_SKILL_DIR:
        if install_root.is_symlink():
            return "unmanaged"
        if not install_root.exists():
            return "missing"
        if is_effectively_empty(install_root, ignored_names={NATIVE_GLOBAL_MANAGED_STATE}):
            return "empty"
        state = read_managed_native_global_state(install_root)
        if (
            state.get("repo_path") == str(repo.resolve())
            and state.get("agent") == agent
            and state.get("strategy") == strategy
        ):
            return "managed"
        return "unmanaged"

    raise ValueError(f"Unknown global install strategy: {strategy}")
