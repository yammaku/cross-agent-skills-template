# AGENTS.md

This file is the development guide for this skills-registry repo itself.

Use it when this repository is the active project and the user wants to improve the skill system, not just operate it from another project.

## Read Order

1. [README.md](README.md)
2. [skills/shared/manage-agent-skills/SKILL.md](skills/shared/manage-agent-skills/SKILL.md)
3. This file

## Repo Purpose

This template is the source-of-truth catalog and install-management system for AI agent skills across:

- Antigravity
- Claude Code
- Codex
- Gemini CLI

This repo is both:

- a catalog of canonical skill sources
- a small product that generates agent-global and project-local install views from manifests
- a universal shared meta-skill that teaches agents how to operate the system safely

## Template Boundary

This repo is the public, distributable template version of the system. It is not the user's lived-in private registry.

Treat it as:

- the productized minimal starter
- the public distribution surface
- the place where reusable system behavior should remain clean and understandable to new users

Do not let it drift into a copy of the private live registry.

The private sibling repo currently lives at:

- [agent-skills](/Users/yammaku/Documents/Projects/agent-skills)

## Document Roles

Treat the docs as layered on purpose:

- [README.md](README.md): front door, bootstrap instructions, and high-level system model
- [skills/shared/manage-agent-skills/SKILL.md](skills/shared/manage-agent-skills/SKILL.md): cross-project operator manual after bootstrap
- [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md): repo-local development guide for evolving this system itself
- [README.md](README.md) is intentionally the AI-led onboarding contract for fresh install and migration. Do not split that into a separate bootstrap skill.

If a rule is necessary for correct behavior from any project, it belongs in the meta-skill. If a rule is about improving this repo as a product, it belongs here.

The intended cross-project workflow is:

1. an installed agent starts from `manage-agent-skills`
2. if the task is ordinary operation, it stays in the meta-skill workflow
3. if the task is system evolution, the meta-skill should direct the agent here

So this file is not the day-to-day entrypoint. It is the deeper development context for changing the system itself.

## Core Model

Keep these layers separate:

1. Catalog
   Canonical skill sources under `skills/`
2. Agent adapters
   Compatibility files under `agents/` that describe each harness's native paths and install strategy
3. Agent-global install views
   Generated managed install views under `installs/agent-global/<agent>`
4. Project install views
   Generated symlink views under the project-local paths declared by each agent adapter

Keep these concepts separate too:

- `shared` means cross-agent compatible source category
- `agent-specific` means source category for one agent
- `agent-global` means installed for one agent across projects on one machine
- `project` means installed only for one project

Never treat `shared` as "automatically installed everywhere."

## Public Template Boundary

Keep the template intentionally minimal.

It should usually contain:

- system files
- adapters
- bootstrap and migration helpers
- minimal manifests
- seed skills such as `manage-agent-skills`

It should not casually absorb:

- the user's private catalog
- large personal manifest sets
- one-off experiments that are not part of the product contract

## Canonical Layout

```text
skills/
  shared/
  antigravity/
  claude-code/
  codex/
  gemini-cli/
agents/
  antigravity.toml
  claude-code.toml
  codex.toml
  gemini-cli.toml
manifests/
  agent-global/
    antigravity.toml
    claude-code.toml
    codex.toml
    gemini-cli.toml
installs/
  agent-global/
    antigravity/
    claude-code/
    codex/
    gemini-cli/
templates/
  project-manifest.toml
bootstrap/
  install_agent_skills.py
  discover_global_skills.py
  apply_global_skill_migration.py
```

## Invariants

- `skills/shared/<skill>` is the canonical source for cross-agent skills.
- `skills/<agent>/<skill>` is the canonical source for agent-specific skills.
- `agents/<agent>.toml` is the compatibility contract for that harness's native global and project paths.
- `agents/<agent>.toml` also declares how that agent-global install should be materialized.
- `manifests/agent-global/<agent>.toml` declares only that agent's global install set.
- Agent-global manifests use explicit refs such as `shared/example-skill` or `codex/example-agent-skill`.
- Generated install views are outputs, not primary authoring surfaces.
- Migration V1 is agent-global only. Do not auto-scan or auto-import project-local skills during onboarding. Use the explicit `adopt-project` workflow after bootstrap when a project needs to bring local skills into the shared registry.
- Project installs are shared-only, declared in `.agent-skills.toml`, and materialized into `.agents/skills` plus any distinct native project mirrors such as `.codex/skills` and `.claude/skills`.
- `.agents/skills` is the preferred interoperable Agent Skills project surface from `agentskills.io`. `.codex/skills` and `.claude/skills` are compatibility mirrors of that same shared install set, not separate management systems or standards.
- Do not shadow a shared skill with the same name in an agent folder.
- If a shared skill needs divergence, create a renamed variant such as `my-skill-antigravity`.
- Do not auto-merge or auto-promote based on matching names alone.
- Do not hard-code the local repo path. Resolve it from `AGENT_SKILLS_REPO`, the current file location, or `~/.agent-skills/config.toml`.

## Development Rules

- Prefer changing manifests and catalog sources over editing generated install views by hand.
- Prefer adding or updating an adapter file under `agents/` over hard-coding another harness path in Python.
- Prefer shared skills by default. Agent-specific skills are the exception path.
- Keep the universal rulebook universal: create, import, classify, install, sync, and validate through the repo-first lifecycle for every agent.
- Keep onboarding AI-led: use scripts for deterministic discovery, import, and install work, but keep classification and review in the agent conversation.
- Respect adapter-specific install materialization. Today Antigravity adds one compatibility layer because it needs real top-level skill directories, while Codex, Gemini CLI, and Claude Code work with symlinked views.
- Respect adapter-specific project mirrors too. Codex project installs should use top-level directory symlinks in `.codex/skills` so they still resolve to the shared catalog, while `.agents/skills` remains the interoperable linked view.
- Keep standard and materialization separate in your reasoning: the system still has one shared project install set even when it is projected into `.agents/skills`, `.claude/skills`, and `.codex/skills` for harness compatibility.
- When documenting or debugging project-scope skills, distinguish clearly between:
  1. the standard install surface (`.agents/skills`)
  2. the managed compatibility mirrors (`.claude/skills`, `.codex/skills`)
  3. the symlink granularity each harness actually tolerates
- Never respond to a harness quirk by creating a new source-of-truth location. The workaround belongs in adapter-driven install projection, not in catalog ownership.
- Keep `manage-agent-skills` universal. Do not fork it per agent; encode agent differences in adapters and in the shared skill's instructions.
- Do not add agent-specific skills to project manifests. Those belong in agent-global manifests only.
- When system behavior changes, update all three surfaces deliberately:
  - [README.md](README.md)
  - [skills/shared/manage-agent-skills/SKILL.md](skills/shared/manage-agent-skills/SKILL.md)
  - repo-local guide files like [AGENTS.md](AGENTS.md) and [CLAUDE.md](CLAUDE.md)
- Keep bootstrap and post-bootstrap responsibilities separate.
- Keep multi-machine sync explicit: repo git state must be resolved before running `sync-agent-global` or `sync-project` on an already managed machine.
- Treat project-level validation as first-class too. `check` only covers the catalog and agent-global install views; use `check-project --project <path>` when changing project install behavior or debugging project mirrors.
- Keep workflows out of this repo for V1 unless the user explicitly expands scope.
- Bias toward explicit manifests and deterministic scripts over undocumented convention.
- When importing a change from the private live repo, productize it here instead of copying private operational baggage.
- If a change only serves the private live registry, keep it out of this template.

## Git Workflow

This repo is the maintained product. Treat git as part of the system, not an afterthought.

When you change catalog structure, skill contents, manifests, or lifecycle behavior:

1. Run the relevant `manage_agent_skills.py` operation.
2. Run `check`.
3. If project-level behavior was touched, run `check-project --project <representative-project>` too.
4. Review `git diff` in this repo.
5. Commit in this repo.
6. Push when the user asks to publish or sync the change upstream.

Remember that template publishing and private live-registry publishing are separate actions. Updating this repo does not update the user's private registry, and vice versa.

Remember:

- `sync` updates generated local install views
- `git commit` records the source-of-truth change
- `git push` publishes the update for other machines or collaborators
- migration helpers may rewire local native roots, but they still operate on this repo as the canonical source of truth

## Harness Compatibility

Some harnesses automatically load `AGENTS.md`, while others prefer `CLAUDE.md`.

Keep [CLAUDE.md](CLAUDE.md) aligned with this file closely enough that opening the repo in Claude Code gives the same development intent and system understanding.
