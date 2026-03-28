# CLAUDE.md

This file mirrors the repo-local development intent of [AGENTS.md](AGENTS.md) for harnesses that recognize `CLAUDE.md`.

Use it when the active project is this skills-registry repo and the user wants to improve the system.

## Read Order

1. [README.md](README.md)
2. [skills/shared/manage-agent-skills/SKILL.md](skills/shared/manage-agent-skills/SKILL.md)
3. [AGENTS.md](AGENTS.md)

## What This Repo Is

This template is the source-of-truth catalog and install-management system for agent skills across Antigravity, Claude Code, Codex, and Gemini CLI.

It contains:

- canonical skill sources under `skills/`
- adapter files under `agents/`
- agent-global manifests under `manifests/agent-global/`
- generated install views under `installs/agent-global/`
- bootstrap and migration tooling for onboarding a new machine

This repo is the public minimal template, not the user's lived-in private registry. Its private sibling currently lives at [agent-skills](/Users/yammaku/Documents/Projects/agent-skills).

## Key Rules

- All agents follow the same repo-first lifecycle: create or import into the repo, classify, install through manifests, sync, and validate.
- `shared` is a source category, not an install policy.
- `agents/<agent>.toml` is the compatibility layer for each harness's native paths.
- `agents/<agent>.toml` also defines the agent-global install materialization strategy.
- Agent-global installs are per-agent and live in `manifests/agent-global/<agent>.toml`.
- Generated install views are outputs, not primary authoring surfaces.
- Antigravity does not get a separate lifecycle. It adds one compatibility layer because its native global scanner needs real top-level skill directories.
- README is the AI-led onboarding contract for fresh install and migration.
- Project installs are shared-only. They live in a project's `.agent-skills.toml` and materialize into `.agents/skills` plus native mirrors such as `.codex/skills` and `.claude/skills` for host-specific discovery.
- Treat `.agents/skills` as the preferred interoperable Agent Skills surface. Native mirrors such as `.codex/skills` and `.claude/skills` are compatibility projections of the same shared install set, not separate ownership domains or separate standards.
- When project skill discovery differs across harnesses, assume the problem is materialization shape before assuming the system needs another authoring surface.
- Onboarding migration stays agent-global only. Explicit post-bootstrap project-local adoption belongs in `manage_agent_skills.py adopt-project`.
- On an already managed machine, resolve repo git state before running `sync-agent-global` or `sync-project`.
- Treat project-level validation as first-class too. `check` only covers the catalog and agent-global install views; use `check-project --project <path>` when changing project install behavior or debugging project mirrors.
- Do not hard-code the repo path.
- Do not shadow a shared skill with the same name in an agent folder.
- If a shared skill needs divergence, create a renamed agent-specific variant.
- Keep the template minimal and productized. Do not copy private catalog history or private manifest clutter into it.

## Doc Boundary

- [README.md](README.md): front door, bootstrap, and pre-install migration contract
- [skills/shared/manage-agent-skills/SKILL.md](skills/shared/manage-agent-skills/SKILL.md): cross-project operator manual after bootstrap
- [AGENTS.md](AGENTS.md) and this file: repo-local development guide for improving the system itself

If behavior must be followed from any project, make sure it lives in the meta-skill, not only in repo-local docs.

The expected flow is:

1. an installed agent starts with `manage-agent-skills`
2. if the user is operating the system, the meta-skill is usually enough
3. if the user is evolving the system itself, the meta-skill should then point the agent to this file or `AGENTS.md`

## Git Workflow

When changing this repo:

1. run the relevant management operation
2. run `check`
3. if project-level behavior was touched, run `check-project --project <representative-project>` too
4. review `git diff`
5. commit in this repo
6. push when the user asks to publish the update

Remember that publishing this template and publishing the private live registry are separate actions.
