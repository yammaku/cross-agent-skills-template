---
name: manage-agent-skills
description: Manage the shared skills-registry repo across Antigravity, Claude Code, Codex, and Gemini CLI. Use when creating a new shared or agent-specific skill, promoting an agent-specific skill to shared, forking a shared skill into a renamed agent-specific variant, or managing agent-global and project install manifests.
---

# Manage Agent Skills

Maintain the configured repo-backed skills registry.

Prefer the bundled script for structural mutations so catalog placement, manifests, and generated install views stay consistent.

This skill is the cross-project operator manual for the skills-registry system after bootstrap. Once an agent has this skill installed, it should rely on this document for day-to-day skill operations and repo maintenance, even when working from another project.

This is one universal shared meta-skill. Do not create agent-specific copies of it. Agent-specific differences belong in adapter files under `agents/`, not in forked meta-skill variants.

## System Rules

- `skills/shared/<skill>` is the canonical source for cross-agent skills.
- `skills/<agent>/<skill>` is the canonical source for agent-specific skills.
- `agents/<agent>.toml` is the adapter definition for that harness's native global and project skill directories.
- `agents/<agent>.toml` also decides how that agent-global install is materialized.
- `manifests/agent-global/<agent>.toml` decides what is installed agent-globally for one agent.
- Project `.agent-skills.toml` files decide what shared skills are installed inside individual projects.
- Generated install views live under `installs/agent-global/<agent>` plus the project-local directories defined by each agent adapter.
- Do not shadow a shared skill with the same name in one agent folder.
- If a shared skill needs agent-specific behavior, create a renamed variant such as `my-skill-antigravity`.
- Workflows are out of scope for this repo.
- Agent-global manifests use explicit refs like `shared/example-skill` or `codex/example-agent-skill`.
- Shared is the default source category.
- Project installs are shared-only.
- Agent-specific skills may be installed agent-globally, but not at project scope.

## Universal Lifecycle

All agents follow the same core lifecycle:

1. decide whether the skill already exists in the catalog
2. if not, create or import the canonical source in the repo first
3. classify that source as `shared` or `agent-specific`
4. update the relevant manifest
5. sync the generated install view
6. run `check`
7. review, commit, and push the repo change when appropriate

Apply this same lifecycle whether the incoming request is:

- create a new skill
- install a catalog skill
- import a skill from GitHub, the internet, or another local folder
- adopt an unmanaged native skill folder
- promote or fork an existing skill
- update a skill that originally came from outside this repo

The invariant is simple:

- the repo catalog is always the source of truth
- native agent skill folders are managed install surfaces
- install shape may vary by adapter, but the lifecycle does not

## Universal Meta-Skill Rule

- `manage-agent-skills` is shared on purpose.
- Onboarding should install this same shared skill into every selected agent's agent-global install set.
- Do not create `manage-agent-skills-antigravity`, `manage-agent-skills-codex`, or other agent-specific copies.
- Keep one universal operating manual and make it agent-aware through the adapter model.

The correct split is:

- shared meta-skill for universal policy and lifecycle
- agent adapters for path and install-materialization differences

## Agent Paths

Use one of these entrypoints:

- From the repo root:
  `python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py --help`
- From an installed agent:
  `python3 ~/.codex/skills/manage-agent-skills/scripts/manage_agent_skills.py --help`

The script resolves the repo root in this order:

- `AGENT_SKILLS_REPO`
- walking up from the script file location
- `~/.agent-skills/config.toml`

The machine should ultimately be anchored to a real local skills-registry clone. Do not treat a bare remote URL or a managed install surface like `~/.gemini/antigravity/skills` as the repo of record.

## Pre-Install Boundary

If the machine has not been onboarded yet, do not assume the installed copy of this skill exists.

Before bootstrap or migration:

1. clone or open the user's skills-registry repo
2. read the root `README.md`
3. follow the AI-led onboarding contract there

For an existing user on a new machine, a remote Git link is not enough by itself. Ensure the user's skills-registry repo is cloned locally first, then continue from that local clone. That local clone becomes the repo this machine should use for future pull, push, diff, status, and sync operations.

The README owns:

- fresh install
- agent-global migration discovery
- batch classification and user confirmation
- applying the approved migration plan

This skill takes over only after onboarding has installed `shared/manage-agent-skills` into the selected agents' agent-global views.

Codex and Claude Code are supported through the same onboarding flow. Their adapters map agent-global installs to `~/.codex/skills` and `~/.claude/skills`, and may project shared project installs into `.codex/skills` and `.claude/skills` as managed compatibility mirrors.

## Scope Boundary

Use this skill for the live operational lifecycle of the skill system:

- create or recategorize catalog skills
- install skills agent-globally or into projects
- sync generated install views
- validate invariants
- maintain the skills-registry repo with git after skill changes
- add or update agent adapters when a new harness needs support

Do not depend on this skill alone for repo-local contributor context when the active project is the skills-registry repo itself. In that case, also follow the repo's `AGENTS.md` or `CLAUDE.md`, which act as the development guide for improving the system itself.

Do not use this skill as a substitute for the onboarding README when the system is not installed yet. Pre-install onboarding and migration remain README-driven on purpose.

## When Evolving The System

Use this skill as the first entrypoint even for deeper system changes, but do not rely on it alone when the request is about changing the architecture, distribution model, or development workflow of the system itself.

If the request is about evolving the system rather than operating it, first open the configured repo's `AGENTS.md` or `CLAUDE.md` and use that repo-local guide together with this skill.

Typical system-evolution requests include:

- adding or removing a supported agent
- changing adapter schema or install materialization behavior
- changing bootstrap or migration flow
- changing manifest schema or install policy
- changing documentation boundaries between README, meta-skill, and repo-local guides
- changing distribution, packaging, or template structure

Use this handoff deliberately:

1. use this meta-skill to locate the correct repo and understand the live operational model
2. if the request changes the system itself, open `AGENTS.md` or `CLAUDE.md` in that repo
3. make the change in the repo source of truth, not in generated install views
4. if the behavior is user-facing from any project, update this meta-skill too
5. if onboarding, migration, or distribution behavior changed, update `README.md`
6. run `check`
7. review the diff, then commit and push in the repo

For normal create, install, promote, fork, sync, and git-maintenance work, this meta-skill should usually be enough on its own.

## Agent-Aware Execution

When using this skill, always:

1. identify the current agent
2. read its adapter behavior from `agents/<agent>.toml`
3. apply the adapter's path and install strategy deliberately

Do not assume every agent consumes the same on-disk install shape.

Current examples:

- Codex, Gemini CLI, and Claude Code can consume symlinked agent-global views.
- Antigravity requires real top-level skill directories in its native global path.
- Shared project installs still come from one shared manifest and one shared catalog. The ideal interoperable surface is `.agents/skills`, because that is the public Agent Skills standard from `agentskills.io`.
- `.codex/skills` and `.claude/skills` in this system are managed compatibility mirrors, not separate standards and not separate authoring surfaces.
- Shared project install surfaces are materialized per adapter. The interoperable `.agents/skills` path remains a real top-level skill directory view with linked contents, while compatibility mirrors such as `.codex/skills` and `.claude/skills` can use the host-specific shape they need.
- Antigravity and Codex have been observed to disagree about symlink granularity for project-scoped skills. Antigravity needs real top-level skill directories with linked contents; Codex reliably accepts top-level directory symlinks to canonical skill folders.
- Codex project mirrors should therefore use top-level directory symlinks to canonical shared skills. That preserves the catalog as source of truth while letting Codex resolve `.codex/skills/<skill>/SKILL.md` as a normal file path.
- Treat `.agents/skills`, `.codex/skills`, and `.claude/skills` as three views over one shared install set. Never reason about them as separate skill systems.

Those differences are an adapter concern, not a reason to fork the meta-skill.

## External Intake Rule

If the user wants a skill that is not already in this repo, do not install it straight into a native agent folder.

Use this flow instead:

1. inspect the external source
2. decide whether it belongs in `skills/shared/` or `skills/<agent>/`
3. import it into the repo catalog first
4. install it through the relevant manifest
5. sync the managed install view
6. run `check`

This applies equally to:

- a skill from GitHub
- a skill found on the internet
- a skill copied from another local directory
- an unmanaged native skill folder that needs to be adopted

If the source is unclear, default to `shared` unless the skill clearly depends on one harness.

## Repo-First Creation Rule

For every agent, including Antigravity:

- create new skills in the repo catalog first
- then install or sync them into the relevant agent or project view

Do not create a brand-new global skill directly inside a native agent folder and treat that as authoritative.

This is especially important for Antigravity because its native global folder is materialized for compatibility and can contain real top-level directories.

Editing existing managed Antigravity skills is safe because their contents link back to the repo. Creating a brand-new skill directly there is not the source-of-truth path.

## Antigravity Compatibility Layer

Antigravity follows the same universal lifecycle as every other agent.

It adds one extra compatibility rule:

- its native global skill scanner requires real top-level skill directories

So Antigravity's adapter materializes real top-level skill folders whose contents link back to the repo catalog. That means its native global folder is still managed output, not a source-of-truth exception.

In practice, the extra rule is:

If the current agent is Antigravity:

- never create a new global skill by writing directly into `~/.gemini/antigravity/skills/<name>`
- treat `~/.gemini/antigravity/skills` as managed output only
- create the skill in `skills/shared/` or `skills/antigravity/` first
- then sync or install it through this system

If you discover an unmanaged native Antigravity skill folder, treat it as an adoption or migration case, not as canonical source by default.

## Decision Guide

Use the matching operation:

- User wants a portable, universal, or cross-agent skill:
  Run `create`.
- User wants an agent-only integration or environment-specific skill:
  Run `create-agent`.
- An agent-specific skill has proven portable and should now be shared:
  Run `promote`.
- A shared skill needs one agent-specific variant:
  Run `fork` and use a renamed agent variant.
- A skill should be available agent-globally in one agent:
  Run `install-agent-global`.
- A skill should stop being available agent-globally in one agent:
  Run `remove-agent-global`.
- A skill should be available only inside one project:
  Run `install-project`.
- A project already has unmanaged local skills that should join the registry:
  Run `adopt-project`.
- A project should stop using a previously installed skill:
  Run `remove-project`.
- Generated install views drift:
  Run `sync-agent-global` or `sync-project`.
- The user says "sync skills" on a machine that already uses this system:
  Follow the multi-machine sync protocol below.
- You want to verify repo invariants before or after changes:
  Run `check`.

## Project Manifest Guardrail

When this meta-skill is invoked from inside a project repo, do not assume the local project skill surfaces are already materialized just because the project tracks `.agent-skills.toml`.

Use this rule:

1. detect whether the current project has `.agent-skills.toml`
2. if it does, treat that file as the desired shared project skill state
3. before project-scope skill work, verify that the local project install surfaces are present and look consistent with that manifest
4. if the state is missing, stale, or unclear, run `sync-project --project <project-root>` first
5. then continue with the requested skill-management task

This guardrail is part of `manage-agent-skills` itself. Do not rely only on per-project `AGENTS.md` snippets to trigger project skill materialization.

In practice, this means:

- if the user asks to install or remove a project skill, the skill may sync the project first before applying the new change
- if the user asks for project skill help and `.agent-skills.toml` already exists, check whether `.agents/skills`, `.codex/skills`, `.claude/skills`, and other project install surfaces need regeneration
- if one harness discovers a project skill and another does not, do not assume the manifest is wrong. First separate:
  1. whether the shared catalog entry exists
  2. whether the project manifest installs it
  3. whether each managed surface was regenerated
  4. whether the failing harness rejects the current symlink granularity
- if everything is already clearly in sync, continue without redundant work

## Human Intent Playbook

Humans will often invoke this meta-skill with intent-level requests instead of low-level commands. Treat the following as the default contract.

### 1. "Install a skill for this project"

Expected behavior:

1. If the current project already has `.agent-skills.toml`, verify that the project install surfaces are materialized first. If they are missing, stale, or unclear, run `sync-project`.
1. Check whether the skill already exists in the catalog.
2. If it exists, install it only into the current project.
3. Do not modify any agent-global manifest unless the user explicitly says to install it globally.
4. Project installs are shared-only. If the skill is agent-specific, stop and route it to agent-global install instead.

Default operation:

- If the skill already exists: run `install-project`.
- If the skill does not exist: follow scenario 3 below first, then install-project.

### 2. "Install a skill globally"

Expected behavior:

1. Install it only for the current agent by editing that agent's manifest.
2. Do not modify the other agents' manifests unless the user explicitly asks for a cross-agent rollout.

Default operation:

- Run `install-agent-global --agent <current-agent> ...`

### 3. "Create a new skill and install it for this project"

Expected behavior:

1. If the current project already has `.agent-skills.toml`, verify that the project install surfaces are materialized first. If they are missing, stale, or unclear, run `sync-project`.
1. Check whether an existing catalog skill already satisfies the request.
2. If an existing skill is good enough, reuse it instead of creating a duplicate.
3. If a new skill is needed, create the canonical source in the catalog first.
4. Then install it into the project only.
5. Do not add it to any agent-global manifest unless the user explicitly asks for that.
6. Because project installs are shared-only, a new project skill should be created as shared by default.

Default source-category rule:

- Create it in `skills/shared` by default.
- Only use `create-agent` when the human explicitly wants an agent-specific skill or the skill clearly depends on one harness.
- If the request also introduces a new harness, add or update that harness's adapter before assuming hard-coded paths.

Default operation:

1. Create with `create` unless there is a clear reason to use `create-agent`
2. Fill in or improve the skill content
3. Run `install-project`

Never bypass this flow by creating a new folder directly in a native agent skills directory.

### 4. "Create a new skill and install it globally"

Expected behavior:

1. Create the canonical source first.
2. Install it only for the current agent unless the human explicitly asks for multiple agents.
3. If the human asked for a shared skill, that means shared source category, not automatic cross-agent global install.

Default operation:

1. Create with `create` unless there is a clear reason to use `create-agent`
2. Fill in or improve the skill content
3. Run `install-agent-global --agent <current-agent> ...`

For Antigravity, this repo-first flow is mandatory because its native global folder is a managed materialization surface.

### 4B. "Adopt these existing project-local skills into our registry"

Expected behavior:

1. Treat this as a deliberate post-bootstrap cleanup flow, not as onboarding migration.
2. Prefer importing project-local skills into `skills/shared/` by default, because project installs are shared-only.
3. Refuse to overwrite a conflicting shared catalog skill silently.
4. Back up the replaced local project entries before changing the project install surfaces.
5. Update the project's `.agent-skills.toml`.
6. Resync the project so `.agents/skills`, `.codex/skills`, `.claude/skills`, and any compatibility mirrors become registry-managed outputs.

Default operation:

1. Run `adopt-project`
2. Review the imported or reused shared skills
3. Verify the project still discovers the regenerated skill surfaces

### 5. "Promote this skill"

Expected behavior:

1. Promotion means source recategorization, not automatic install changes.
2. Move the source from `skills/<agent>/<name>` to `skills/shared/<name>`.
3. Keep existing shared project installs and agent-global installs working.
4. Only broaden installation if the user explicitly asks for it.

Default operation:

1. Run `promote`
2. If needed, update manifests to use the explicit `shared/<name>` ref
3. Sync the affected install views

### 6. "Recategorize this skill" or "make this agent-specific"

Expected behavior:

1. Do not shadow a shared skill with the same name.
2. Keep the shared skill intact.
3. Create a renamed agent-specific variant if one agent now needs different behavior.
4. Update only the affected agent's global manifest or the shared project manifest as appropriate.

Default operation:

1. Run `fork --new-name <name>-<agent>`
2. Update the relevant manifest or project install to point at the new variant
3. Sync only the affected agent or project

### 7. "Install this shared skill for Codex" or "for Antigravity"

Expected behavior:

1. `shared` is a source category only.
2. Installing a shared skill for one agent should touch only that agent's manifest.
3. Do not infer "shared source" as "install for all agents."

Default operation:

- Add `shared/<name>` only to `manifests/agent-global/<agent>.toml` or to the target project's manifest, then sync the relevant target.

### 8. "Use the same skill in multiple agents"

Expected behavior:

1. First decide whether the source should be shared or remain agent-specific.
2. Then install it into each target agent explicitly.
3. Do not broaden all agents by default just because two agents are involved.

Default operation:

- If portable, use `shared/<name>` and add it explicitly to each target agent's manifest.
- If not portable, keep separate agent-specific sources.

## Safety Defaults

Unless the human explicitly says otherwise:

- Prefer project install over agent-global install.
- Prefer reusing an existing catalog skill over creating a duplicate.
- Prefer shared source over agent-specific source unless the skill clearly depends on one harness.
- Prefer promotion only after a skill has actually proven portable.
- Treat source-category changes and install-policy changes as separate decisions.
- Treat project installs as shared-only by default and by policy.
- Treat native agent skill folders as install surfaces, not as the place to author new canonical skills.

If a request would both recategorize a skill and broaden where it is installed, call that out and handle the two changes deliberately instead of collapsing them into one implied action.

## Preferred Workflow

1. If you are inside a project repo and `.agent-skills.toml` exists, verify whether project installs need `sync-project` before doing project-scope skill work.
2. Pick the structural operation and run the bundled script first.
3. If the operation creates a new skill scaffold, edit the new `SKILL.md` and any resources after the folder layout is correct.
4. When writing or improving the skill contents themselves, use `skill-creator` guidance if the task is substantial.
5. Sync the relevant install view if the skill should become available agent-globally or inside a project.
6. When changing agent-global installs, edit only that agent's manifest and sync only that agent unless the user explicitly wants a broader rollout.
7. Run `check` after structural changes.
8. Use plain git commands in the configured skills-registry repo to review, commit, and push.
9. If compatibility behavior changed, update the relevant file under `agents/` and the docs that describe the lifecycle.
10. If the user asks to "sync skills" on an already managed machine, follow the multi-machine sync protocol before any install sync.

If the current agent is Antigravity, be extra deliberate about step 1. Do not create a new skill folder directly in `~/.gemini/antigravity/skills`; always start from the repo operation first.

For a create-and-install request, do not stop after scaffolding the source skill. Complete the full flow:

1. create source
2. improve the skill contents enough to be usable
3. install it to the requested target
4. sync
5. run `check`

## Git Lifecycle

Changing a skill, manifest, or install policy is only half of the maintenance loop. The source of truth is still the git repo.

After meaningful changes in the skills-registry repo:

1. Run `check`.
2. Review the diff in the configured repo.
3. Commit in the skills-registry repo with a message that describes the catalog or lifecycle change.
4. Push when the user asks you to publish the update or when the workflow explicitly requires it.

Use git in the repo itself, not through one agent category. The repo is the maintained product.

Keep the distinction clear:

- `sync` updates generated install views on the current machine
- `git commit` records source-of-truth changes in the repo
- `git push` publishes those changes for other machines or collaborators

When another machine needs the update, the intended flow is:

1. if the machine is new, return to the onboarding README
2. otherwise inspect the skills-registry repo's git state first
3. only after the repo state is resolved, run `sync-agent-global`
4. if the current project repo has `.agent-skills.toml`, run `sync-project --project <project-root>`

## Multi-Machine Sync Protocol

When the user says "sync skills" on a machine that already uses this system, do not interpret that as "blindly pull and then sync installs."

Use this protocol:

1. treat the skills-registry repo as the cross-machine source of truth
2. if you are currently working inside another project repo, keep that separate in your head:
   - the project repo is only a consumer of project-level installs
   - it is not the source of truth for the shared skill catalog
3. inspect the skills-registry repo's git state before any install sync
4. only after the skills-registry repo state is resolved, materialize that state onto the current machine

Check at least:

- whether the working tree is dirty
- whether the local branch is ahead of remote
- whether it is behind remote
- whether local and remote have diverged

Then branch:

- clean and only **behind** remote:
  1. pull with a safe fast-forward workflow
  2. run `sync-agent-global`
  3. if the current project repo has `.agent-skills.toml`, run `sync-project --project <project-root>`
- clean and only **ahead** of remote:
  1. do not pull blindly
  2. tell the user this machine has unpushed commits
  3. ask whether to push first or only sync local install surfaces from the current local skills-registry repo state
- **diverged** local and remote:
  1. stop before install sync
  2. explain that both local and remote have commits
  3. resolve merge or rebase deliberately before materializing installs
- **dirty** working tree:
  1. stop before pull
  2. ask whether to commit, stash, or discard local changes

Important distinction:

- repo sync can be bidirectional because multiple machines may edit the repo
- install sync is always local materialization from the resolved skills-registry repo state
- `sync skills` is primarily about synchronizing the skills-registry repo; project repos only get their `.agent-skills.toml` installs materialized afterward when relevant

## Adapter Lifecycle

Use adapter files under `agents/` to teach the system about a harness's native paths.

When adding a new agent:

1. create `agents/<agent>.toml`
2. create `skills/<agent>/`
3. add `manifests/agent-global/<agent>.toml`
4. update bootstrap and docs only if behavior changed beyond what the adapter can express

Prefer adapter changes over more hard-coded path logic in Python.

## Commands

### Create a shared skill

Creates the real skill folder in `skills/shared/<name>`. It does not install the skill anywhere by itself.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  create my-skill --resources scripts,references
```

### Create an agent-specific skill

Creates the real skill folder only in the chosen agent.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  create-agent antigravity my-skill --resources scripts
```

### Promote an agent-specific skill to shared

Moves the agent-owned folder into `shared`. It does not automatically install it anywhere.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  promote antigravity my-skill
```

### Fork a shared skill into an agent-specific variant

Keeps the shared skill intact and creates a renamed agent-specific copy.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  fork antigravity my-skill --new-name my-skill-antigravity
```

### Install a skill agent-globally

Adds one or more catalog skills to `manifests/agent-global/<agent>.toml` for an agent and regenerates only that agent's global install view.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  install-agent-global \
  --agent codex \
  gstack cloudflare
```

### Install a skill in one project

Adds one or more shared catalog skills to a project's `.agent-skills.toml` and regenerates both the interoperable and agent-native project views.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  install-project \
  --project /path/to/project \
  gstack
```

### Adopt unmanaged project-local skills into the registry

Imports existing local project skills into `skills/shared/`, updates the project's `.agent-skills.toml`, backs up the replaced local entries, and then rebuilds the managed project install surfaces.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  adopt-project \
  --project /path/to/project
```

You can also target specific skills or point at one project-local source root explicitly. The source root can be `.agents/skills`, `.codex/skills`, `.claude/skills`, or another project-local skill directory:

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  adopt-project \
  --project /path/to/project \
  --source-dir /path/to/project/.codex/skills \
  wrangler cloudflare
```

### Sync generated installs

Rebuilds the generated agent-global or project install views from the manifest files.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py sync-agent-global
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py \
  sync-project \
  --project /path/to/project
```

### Check the system

Validates the catalog and generated install invariants.

```bash
python3 skills/shared/manage-agent-skills/scripts/manage_agent_skills.py check
```

## Notes

- The script creates a minimal scaffold for new skills. It does not finish the skill content for you.
- If a name collision happens, stop and resolve the ownership question instead of forcing a move.
- If an agent already has a real folder with the same name as a shared skill, treat that as a system inconsistency and fix it deliberately.
- `adopt-project` is the explicit path for bringing unmanaged project-local skills into the registry after bootstrap. Keep onboarding migration focused on agent-global roots.
- Installing a skill agent-globally or into a project does not create a second source of truth. It creates managed views back to the canonical source in this repo.
- Those managed views may differ per adapter. For example, Antigravity uses real top-level skill dirs with linked contents, while Codex project mirrors use top-level directory symlinks and other harnesses may consume direct symlinked views.
- Bare skill names are allowed in commands for convenience, but agent-global manifests are stored using explicit refs.
- Project commands accept shared skills only. Agent-specific refs must be handled through agent-global commands.
