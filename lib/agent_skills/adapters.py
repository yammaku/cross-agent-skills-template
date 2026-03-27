from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentAdapter:
    name: str
    native_global_skills_dir: str
    native_project_skills_dir: str
    preferred_instruction_files: tuple[str, ...]
    global_install_strategy: str = "symlinked-view"

    def global_path(self) -> Path:
        return Path(self.native_global_skills_dir).expanduser()

    def project_path(self, project: Path) -> Path:
        return project / Path(self.native_project_skills_dir)


def parse_string(raw: str) -> str:
    if len(raw) >= 2 and raw[0] == raw[-1] == '"':
        return raw[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return raw


def parse_array(raw: str) -> tuple[str, ...]:
    raw = raw.strip()
    if not raw.startswith("[") or not raw.endswith("]"):
        return ()
    body = raw[1:-1].strip()
    if not body:
        return ()
    items: list[str] = []
    for item in body.split(","):
        item = item.strip()
        if not item:
            continue
        items.append(parse_string(item))
    return tuple(items)


def parse_adapter_file(path: Path) -> AgentAdapter:
    data: dict[str, object] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = [part.strip() for part in line.split("=", 1)]
        if key == "preferred_instruction_files":
            data[key] = parse_array(value)
        else:
            data[key] = parse_string(value)

    name = str(data.get("name") or path.stem)
    return AgentAdapter(
        name=name,
        native_global_skills_dir=str(data["native_global_skills_dir"]),
        native_project_skills_dir=str(data["native_project_skills_dir"]),
        preferred_instruction_files=tuple(data.get("preferred_instruction_files", ())),
        global_install_strategy=str(data.get("global_install_strategy") or "symlinked-view"),
    )


def load_agent_adapters(repo_root: Path) -> dict[str, AgentAdapter]:
    adapters_dir = repo_root / "agents"
    if not adapters_dir.is_dir():
        raise FileNotFoundError(f"Missing agents directory: {adapters_dir}")

    adapters: dict[str, AgentAdapter] = {}
    for path in sorted(adapters_dir.glob("*.toml")):
        adapter = parse_adapter_file(path)
        if adapter.name in adapters:
            raise ValueError(f"Duplicate agent adapter: {adapter.name}")
        adapters[adapter.name] = adapter
    if not adapters:
        raise ValueError(f"No agent adapters found in {adapters_dir}")
    return adapters


def agent_names(repo_root: Path) -> tuple[str, ...]:
    return tuple(load_agent_adapters(repo_root).keys())
