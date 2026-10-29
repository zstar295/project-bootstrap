# Project Bootstrap for Codex

English | [简体中文](README.md)

Turn user requirements into a local project that Codex can execute and maintain across sessions, with requirements clarification, task planning, workspace setup, and persistent project context.

Use it for research, software, engineering, data analysis, and other long-running projects. Start with a description of what you need; the skill clarifies consequential gaps and connects inputs, methods, tasks, outputs, and acceptance criteria.

## What it builds

- A scoped project brief and work orders with dependencies and acceptance conditions.
- A local directory structure, concise AGENTS.md, source index, status, and handoff notes.
- Environment and input checks, with authorized setup and first-task execution checks.
- On-demand context and traceable local records of sources, decisions, and candidate lessons.

A Codex project here means a local workspace. This skill does not automatically register it in the Codex application's project list; open or add the directory there after setup. The generator supplies a common framework. Domain implementation and final deliverables still need to be completed and verified through the work orders.

## Install and use

Download this repository and copy the project-bootstrap folder into .codex/skills/ under your user home directory.

Ask Codex:

```text
Use $project-bootstrap.
My requirements: ...
Project directory: ...
Existing materials or code: ...
Clarify essential requirements, build a local project for Codex,
and verify the first task's execution conditions.
```

Entry point: [SKILL.md](project-bootstrap/SKILL.md). An [English core guide](project-bootstrap/SKILL.en.md) is included. Detailed references and generated templates are currently mainly in Chinese; the runtime is not fully localized. Other AI tools may read the local files, but their loading behavior and compatibility need separate verification.

The generator previews by default. Use --apply after reviewing the configuration; existing-file collisions are rejected. Existing projects should be integrated through gap analysis and targeted changes.

## Development and verification

Runtime: Python 3.10+ standard library. Development validation dependencies are listed in requirements-dev.txt.

```sh
python -X utf8 project-bootstrap/scripts/bootstrap_project.py --help
python -X utf8 project-bootstrap/scripts/test_bootstrap.py
```

Tests use synthetic projects. Passing framework checks does not establish domain correctness or final acceptance. Memory approval records do not replace operating-system access controls or identity authentication.

## License

No open-source license has been granted yet. Contact the repository owner for permission to reuse, modify, or redistribute. The public repository excludes original conversations, private research materials, and prior development history.
