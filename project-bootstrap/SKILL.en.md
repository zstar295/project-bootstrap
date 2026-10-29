# From User Requirements to an Executable Codex Project

English core guide for `project-bootstrap`. The discoverable entry point is [SKILL.md](SKILL.md); do not install this file as a second skill.

Turn user requirements into a local project workspace that Codex can execute, maintain, and hand over across sessions. Include a concrete goal, scope, inputs, task dependencies, working commands, acceptance criteria, current state, and next work package. Support research, software, engineering, data, and other long-running projects.

This skill creates local files and an execution structure. It does not automatically register a project in the Codex application. The user must open or add the workspace there.

## Read only what the current task needs

The detailed references and generated templates are currently in Chinese; this is an English core guide, not a fully translated runtime.

| Need | Reference |
|---|---|
| Clarify requirements, scope, and acceptance | [Requirements](references/requirements.md) |
| Create or integrate a workspace, environment, and Git | [Build](references/build.md) |
| Work packages, roles, memory, and handoff | [Execution](references/execution.md) |
| Understand method origins and limits | [Case study](references/case-study.md) |

## Workflow

1. **Inspect the intended workspace.** Respect the user's directory, existing instructions, files, data, environment, and confirmed decisions. For an existing project, identify gaps and integrate narrowly rather than overwriting its structure or history.
2. **Clarify consequential requirements.** Establish the deliverable, audience, success evidence, inputs, constraints, resources, deadline, and authorized actions. Read available evidence before asking. Ask only questions that affect the route or block execution; distinguish assumptions from confirmed facts.
3. **Design the smallest viable route.** Connect goals, inputs, methods, outputs, and acceptance criteria. Define dependencies, a first executable work package, and expansion conditions. Use relevant domain skills and evidence. Verify current tool suitability when selecting tools; install only what the route needs and authorization permits.
4. **Build the workspace.** For a new project, review a manifest and preview [the generator](scripts/bootstrap_project.py) before `--apply`. It generates the common control framework; continue environment setup and domain implementation separately. Create a short AGENTS.md, context index, work orders, state, provenance, memory, and necessary domain directories.
5. **Check the first task's execution conditions.** Implement the minimal required chain, verify real inputs, versions, licenses, and commands, and run an authorized small example where possible. If blocked, provide an executable input-review or environment task and record the missing prerequisites. A planned script is not an implemented command.
6. **Verify and hand over.** Run the generated projectctl check, project_doctor, and relevant domain checks. Report actual commands, evidence, readiness level, limitations, and the next package. Continue only within the user's scope; a bootstrap request does not authorize unrelated publication, messages, or production workloads.

## Invariants

- Keep AGENTS.md and indexes short. Load task-specific methods, evidence, and history on demand.
- Preserve existing data and unrelated edits. Resolve conflicts with traceable changes and current user intent.
- Bind initial records to the real user request. Hash checks support provenance but cannot authenticate human identity.
- Keep candidate lessons separate from formal knowledge. Major methodological or directional promotions require specific human confirmation; routine local work follows existing authorization.
- Use planner, reviewer, and executor responsibilities without assuming model names, creating other chats, or delegating automatically.
- Distinguish framework generation, environment readiness, first-task execution, and domain acceptance. One passing check does not prove all four.
- Refuse overwrites and path traversal in initialization. Do not add force options or bypass guards to integrate an existing project.
- Portable Markdown, JSON, and Git records can be shared with other tools, but automatic discovery and compatibility must be verified.

## Example

```text
Use $project-bootstrap.
My requirements: ...
Project directory: ...
Existing materials or code: ...
Clarify essential requirements, build a local project for Codex,
and verify the first task's execution conditions.
```

The agent prepares the manifest from the conversation; the user does not need to fill in JSON. [The example manifest](assets/manifest.example.json) is synthetic and is not evidence of user approval. The generator uses the Python 3.10+ standard library; consult its `--help` for arguments.
