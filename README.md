# cross-agent-skills-template

Single source of truth for AI agent skills across Antigravity, Codex, Gemini CLI, and Claude Code.

This repo is a skill catalog first. A skill being available here does not mean it is installed agent-globally everywhere.

## Who This README Is For

This README is for both:

- the human who owns the skills registry
- the AI agent that will onboard or operate it

The goal is to make the first decision clear before any scripts run:

- which repo should be used on this machine
- what the AI agent should inspect before choosing an onboarding path

## For Humans

### If this is your first time using the system

The simplest path is:

1. give this repo to your AI agent
2. let the agent read this README
3. let the agent create your own repo from this template and continue there

You generally should not need to run the setup manually yourself.

### If you already use this system

Do **not** use the upstream public template on a new machine.

Instead:

1. use **your own existing skills-registry repo**
2. give that repo to your AI agent
3. let the agent onboard the new machine to your repo

Your own repo is the source of truth once you have one.

### What should you expect the AI agent to do?

The AI agent should inspect the repo and the machine, then guide you.

It should only ask you to choose when there is a real branch to decide, for example:

- whether to migrate existing unmanaged local skills
- or replace them with backup

Fresh install does **not** silently overwrite unmanaged local skill roots. If they already exist, the system will stop and ask for confirmation.

### If this machine already uses this system and you want to "sync skills"

The right mental model is:

- repo sync first
- install sync second

There may be two repos in play:

- **repo B**: your skills-registry repo, which owns the catalog, manifests, and source of truth
- **repo A**: the current project repo you may be working in, which may contain `.agent-skills.toml`

In other words, "sync skills" on an already managed machine does **not** mean "blindly pull and overwrite local state."

It means:

1. inspect the git state of the skills-registry repo first
2. resolve whether that repo should pull, push, or stop for conflict handling
3. only after the skills-registry repo state is clear, sync the local install surfaces

So `sync skills` means:

- first, sync **repo B**
- then, if the current context is **repo A** and it tracks `.agent-skills.toml`, materialize that project's shared skill installs too

The AI agent should handle that for you. In normal use, you can just give your private repo to the agent and say:

`Read this README first. This machine already uses this system. Sync skills for this machine.`

## Start Here

If you are handing this repo to an AI agent, a good starter prompt is:

`Help me adopt this cross-agent skills system. Read this README first, detect whether this repo is the upstream template or my own repo, inspect the machine state, and then guide me through the correct onboarding path.`

## OSS Distribution Model

For open source, the intended distribution model is:

1. publish the project as a **GitHub template repo**
2. each user creates **their own repo** from that template, ideally private
3. the user clones **their own repo**
4. the user gives that repo to an AI agent
5. the agent follows this README to onboard the system

This README is the **pre-install onboarding contract** for that AI-led flow.

The public template should seed only the system files plus `shared/manage-agent-skills` as the initial always-on skill. It does not need to include a large shared catalog.

That usually means the public template should ship:

- the repo structure and docs
- agent adapters under `agents/`
- bootstrap and migration helpers under `bootstrap/`
- minimal agent-global manifests that install `shared/manage-agent-skills`
- the `shared/manage-agent-skills` skill itself

`manage-agent-skills` is one universal shared meta-skill. It should be installed for every selected agent during onboarding. Agent-specific differences belong in adapter files, not in separate copies of the meta-skill.

## Universal Rulebook

All supported agents follow the same repo-first lifecycle:

1. create or import the skill into this repo first
2. classify it as `shared` or `agent-specific`
3. install it through manifests
4. sync the generated install view

That rule applies whether the skill starts as:

- a brand-new skill
- an existing catalog skill
- a skill imported from GitHub or the internet
- a skill adopted from an existing local agent setup

Antigravity does not have a different lifecycle. It only adds one compatibility layer at install time.

For project installs, shared skill surfaces are materialized as real top-level skill directories with linked contents. That shape keeps the interoperable `.agents/skills` surface compatible with Antigravity while still working for Codex, Gemini CLI, and Claude Code.

After onboarding, `.agent-skills.toml` is the project-level source of truth. When an agent is using `manage-agent-skills` inside a project that already tracks `.agent-skills.toml`, it should treat that manifest as desired state and run `sync-project` before project-scope skill work if the local project install surfaces are missing, stale, or unclear.

For multi-machine use, keep this distinction clear:

- the skills-registry git repo is the cross-machine source of truth
- `sync-agent-global` always applies the skills-registry repo state onto the current machine
- `sync-project` applies that same resolved skills-registry state into one project repo that declares `.agent-skills.toml`
- install surfaces do not sync to each other directly across machines

## Agentic Onboarding Contract

An agent opening this repo for the first time should treat onboarding as a conversation with the user, not as a blind script run.

### 1. Confirm repo ownership before mutating anything

Inspect the current git remote and confirm whether this is the user's own template-derived repo.

If the repo still points to the upstream public template, do **not** assume that automatically means the user is new to this system.

Ask one disambiguation question:

- `Is this your first time using this cross-agent-skills system?`

Then branch:

- if **yes**:
  1. create the user's own repo from the template
  2. clone that repo locally
  3. continue onboarding there
- if **no**:
  1. ask the user for the link or local path to their existing skills-registry repo
  2. open or clone that repo instead
  3. continue onboarding there

Do not mutate the upstream public template clone as if it were the user's personal registry.

### 2. Inspect machine state before asking the user to choose a path

Before asking the human to choose anything, inspect the selected agents' native global skill roots and decide whether this machine looks like:

- **already managed by this repo**
- **empty or missing**
- **unmanaged local skills exist**

Use that state to drive the conversation:

- if this repo is the upstream template, first resolve whether this is the user's first time using this system
- if native roots are empty or missing, treat it as a likely fresh install
- if native roots already contain unmanaged skills, ask whether to migrate them or replace them with backup
- if the machine is already managed by this repo, verify or resync instead of re-onboarding blindly

Do not ask the vague question "are you a first-time user?" if repo state and machine state already answer what matters.

The one exception is the upstream public template case. There, asking whether this is the user's first time using **this specific system** is the right guardrail, because it distinguishes:

- first-time adoption of this system
- accidental use of the upstream template by an existing user who should really be using their own repo

### 2B. If the machine is already managed and the user asks to "sync skills"

Treat this as a multi-machine sync request, not as onboarding.

The protocol is:

1. inspect the git state of the skills-registry repo first
2. do **not** run install sync until the repo state is clear
3. then materialize the resolved skills-registry repo state onto this machine

At minimum, inspect:

- whether the working tree is dirty
- whether the local branch is ahead of remote
- whether it is behind remote
- whether local and remote have diverged

Then branch:

- if the skills-registry repo is clean and only **behind** remote:
  - pull with a safe fast-forward workflow
  - then run `sync-agent-global`
  - if the current project repo has `.agent-skills.toml`, run `sync-project`
- if the skills-registry repo is clean and only **ahead** of remote:
  - do not blindly pull
  - tell the user this machine has unpushed commits
  - ask whether to push first or only sync local install surfaces from the current local repo state
- if the skills-registry repo is **diverged**:
  - stop before install sync
  - explain that both local and remote have commits
  - resolve the merge or rebase deliberately before materializing installs
- if the skills-registry repo working tree is **dirty**:
  - stop before pull
  - ask whether the user wants to commit, stash, or discard those changes

The important guardrail is:

- repo sync can be bidirectional because multiple machines may edit the repo
- install sync is always local materialization from the resolved skills-registry repo state
- the project repo's own git state is a separate concern and is not what `sync skills` is primarily synchronizing

### 3. Ask which agents to manage

Supported agents:

- `codex`
- `gemini-cli`
- `antigravity`
- `claude-code`

### 4. Use repo maturity only as a soft hint

If this repo contains only the seed system skill(s), that is a hint that the registry may be in an early state.

Do **not** treat that alone as the source of truth for whether the user is new. Repo ownership and machine state are the primary signals.

### 5A. Fresh install flow

For a fresh machine or an empty native root, run:

```bash
python3 bootstrap/install_agent_skills.py --agent codex
python3 bootstrap/install_agent_skills.py --agent gemini-cli
python3 bootstrap/install_agent_skills.py --agent antigravity
python3 bootstrap/install_agent_skills.py --agent claude-code
```

You can install multiple agents at once:

```bash
python3 bootstrap/install_agent_skills.py \
  --agent codex \
  --agent gemini-cli \
  --agent antigravity \
  --agent claude-code
```

If an unmanaged native skill root already exists and the user still wants a **fresh install instead of migration**, get explicit confirmation first, then rerun with:

```bash
python3 bootstrap/install_agent_skills.py \
  --agent codex \
  --replace-existing
```

`--replace-existing` backs up the unmanaged native root into `~/.agent-skills/backups/` and replaces it with this repo's generated agent-global view. It should only be used after the user explicitly chooses replacement over migration.

### 5B. Migration flow

Migration V1 handles **agent-global skills only**. Do not scan random projects on disk and do not attempt project-local migration during onboarding.

#### Discover existing native global skills

```bash
python3 bootstrap/discover_global_skills.py \
  --agent codex \
  --agent claude-code \
  --output .agent-skills-discovery.json
```

The discovery report is deterministic. It inventories current native agent-global roots and visible skill folders. It does **not** classify them.

#### Review and classify in batch

After discovery, the onboarding agent should:

1. read the discovery report
2. inspect the actual skill contents
3. recommend classification in **batch**
4. group results into:
   - recommended `shared`
   - recommended `agent-specific`
   - recommended `skip`
5. explain every non-shared recommendation briefly
6. ask the user to confirm or edit the batch before import

Default migration policy:

- recommend **shared** by default
- recommend **agent-specific** only when a skill clearly depends on one harness
- recommend **skip** for obsolete, broken, generated, or intentionally excluded skills

The migration plan should be written to a machine-readable JSON file. See:

- [migration-plan.example.json](templates/migration-plan.example.json)

#### Apply the approved migration plan

```bash
python3 bootstrap/apply_global_skill_migration.py \
  --plan .agent-skills-migration.json
```

That script will:

- import approved skills into the catalog
- update agent-global manifests to preserve what stays available
- back up and replace existing unmanaged native roots
- sync generated agent-global views
- run `check`

After apply, review the git diff and recommend an initial migration commit.

### 5. Verify post-onboarding state

After either fresh install or migration, verify the system with:

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py check
```

The onboarding is complete when the selected agents have `shared/manage-agent-skills` available agent-globally.

That is important on purpose: after onboarding, the user should be able to ask any installed agent to create, install, promote, or recategorize skills through the same shared meta-skill workflow.

## Which Document To Use

- New machine, fresh install, or migration:
  Start here in [README.md](README.md).
- Working from any project after bootstrap:
  Use [manage-agent-skills](skills/shared/manage-agent-skills/SKILL.md) as the operating manual.
- Improving this template or a user's derived skills-registry repo:
  Follow [AGENTS.md](AGENTS.md) or [CLAUDE.md](CLAUDE.md) when this repo is the active project.

## System Model

There are four layers:

1. Catalog
   The repo contains every available skill.
2. Agent adapters
   `agents/*.toml` defines how each harness maps the catalog into its own native skill locations.
3. Agent-global install set
   A small per-agent always-on view generated from `manifests/agent-global/<agent>.toml`.
4. Project install set
   A per-project opt-in view generated from a local `.agent-skills.toml`.

A skill can be:

- shared across agents
- agent-specific
- installed agent-globally
- installed only in selected projects
- available in the catalog but not installed anywhere yet

Project installs are intentionally stricter than agent-global installs:

- project installs are **shared-only**
- agent-specific skills are **agent-global only**

This separation is important. It keeps the catalog rich without forcing every agent to load every skill globally.

## Layout

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
templates/
  migration-plan.example.json
  project-manifest.toml
bootstrap/
  install_agent_skills.py
  discover_global_skills.py
  apply_global_skill_migration.py
installs/
  agent-global/
    antigravity/
    claude-code/
    codex/
    gemini-cli/
```

- `skills/shared/<skill>`: canonical source folder for cross-agent skills.
- `skills/<agent>/<skill>`: canonical source folder for agent-specific skills.
- `agents/<agent>.toml`: adapter definition for that harness's native global and project skill directories.
- `manifests/agent-global/<agent>.toml`: declares which catalog skills are installed agent-globally for one agent only.
- `bootstrap/discover_global_skills.py`: deterministic discovery helper for agent-global migration planning.
- `bootstrap/apply_global_skill_migration.py`: deterministic migration executor that applies an approved plan.
- `templates/migration-plan.example.json`: example machine-readable migration plan.
- `installs/agent-global/<agent>/<skill>`: generated managed install view consumed directly or indirectly by that agent's global skill path.
- `.agent-skills.toml` in a project: declares only shared catalog skills for that project.
- `.agents/skills/` in a project: generated shared project-local symlink view.
- `.claude/skills/` in a project: Claude-native mirror of the shared project skill set.
- `manage_agent_skills.py adopt-project --project /path/to/project`: explicit post-bootstrap flow for adopting unmanaged project-local skills into the shared registry.

## Agent Install Conventions

After onboarding, the local agent roots should be managed from the generated agent-global install views:

- `~/.gemini/antigravity/skills -> <repo>/installs/agent-global/antigravity`
- `~/.claude/skills -> <repo>/installs/agent-global/claude-code`
- `~/.codex/skills -> <repo>/installs/agent-global/codex`
- `~/.gemini/skills -> <repo>/installs/agent-global/gemini-cli`

Agent-global install materialization is adapter-driven, but the underlying lifecycle stays universal:

- most agents use direct symlinks back to the real catalog sources under `skills/`
- Antigravity uses real top-level skill directories whose contents link back to the catalog, because its skill scanner does not reliably discover symlinked top-level skill folders

So the rule is:

- all agents use the same repo-first source-of-truth model
- Antigravity adds one compatibility layer over the final install materialization

Either way, edits made through installed paths still write back to this repo.

One important operational rule follows from this:

- native agent skill folders are managed install surfaces
- the repo catalog is still the canonical place to create new skills

This matters most for Antigravity because its native global folder uses real top-level skill directories for compatibility.

Shared project installs materialize from one manifest into both `.agents/skills` and any distinct native project directories defined by adapters. Today that means Claude Code gets the same shared project skills mirrored into `.claude/skills`.

## Authoring Rules

- Create new skills in `skills/shared/` by default.
- Create new agent-specific skills directly in `skills/<agent>/`.
- Do not auto-promote a skill to shared just because names happen to match.
- Agent-specific skills are the exception path for real harness-specific behavior.
- Shared means cross-agent compatible, not automatically installed agent-globally.
- Agent-global and project installs are controlled by manifests, not by placing symlinks in the catalog.
- Agent-global manifests use explicit refs like `shared/example-skill` or `codex/example-agent-skill`.
- Editing `manifests/agent-global/codex.toml` should never be necessary to change Antigravity or Gemini CLI.
- Adding support for a new harness should usually mean adding one adapter file under `agents/`, including its install strategy, not hard-coding more Python path logic.
- Project installs are shared-only. If a skill is agent-specific, install it agent-globally instead.

## Divergence Rule

If a shared skill later needs agent-specific behavior, do not shadow it with the same name in one agent folder. Keep the shared skill intact and create a renamed agent-specific variant such as `my-skill-antigravity`.

## Project Installs

For a project-specific install, create or update `.agent-skills.toml` in the project root and then sync it:

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  install-project \
  --project /path/to/project \
  my-shared-skill
```

That command:

- adds the skill to `/path/to/project/.agent-skills.toml`
- creates or updates `/path/to/project/.agents/skills`
- mirrors the same shared project skill into `/path/to/project/.claude/skills` when Claude support is present
- materializes managed links back to this repo's catalog

Project installs are shared-only. If you try to install `codex/...` or `antigravity/...` at project scope, the manager will reject it and direct you to agent-global manifests instead.

If a project already has unmanaged local skill folders from another installer or older workflow, do not treat that as onboarding migration. After bootstrap, use:

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  adopt-project \
  --project /path/to/project
```

That explicit adoption flow:

- imports missing local project skills into `skills/shared/`
- refuses to overwrite conflicting shared catalog skills silently
- backs up the replaced project-local entries
- updates `.agent-skills.toml`
- resyncs the managed project install surfaces

This lets big skill collections live in the catalog without becoming global default baggage.

## Agent-Global Manifests

Each agent owns its own agent-global manifest file:

- `manifests/agent-global/antigravity.toml`
- `manifests/agent-global/claude-code.toml`
- `manifests/agent-global/codex.toml`
- `manifests/agent-global/gemini-cli.toml`

Those files contain explicit catalog refs. Example:

```toml
skills = [
  "shared/manage-agent-skills",
  "shared/example-skill",
  "codex/example-agent-skill",
]
```

That means:

- `shared` is only a source category
- a shared skill is not installed anywhere unless an agent manifest explicitly includes it
- one agent can add or remove a shared skill without modifying the other agents' settings

## Day-to-Day Workflow

- Before bootstrap or migration, follow the AI-led onboarding contract in this README.
- Use plain git commands in this repo.
- Use the `manage-agent-skills` skill or its bundled script for structural changes.
- Treat `agents/*.toml` as the compatibility layer for native harness paths.
- Workflows are still out of scope for this repo in V1.
