"""Portable project context, task records, memory proposals and Git policy checks.

No third-party dependencies. Domain execution and identity verification are separate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
KINDS = {"user_requirement", "observation", "local_experience", "hypothesis", "method"}
TASK_STATES = {"running", "completed", "blocked", "failed"}
EXECUTOR_PREFIXES = (
    "work/", "memory/candidates/", "src/", "data/derived/", "scripts/", "tests/", "reports/tasks/",
)
PROTECTED_FILES = {
    "AGENTS.md", "spec.md", "project_profile.md", ".gitignore", ".gitattributes",
    "context/GOVERNANCE.md", "scripts/projectctl.py", "scripts/project_doctor.py", "scripts/configure_project_git.py",
    "configs/governance.policy.json", "configs/project.json", "planning/WORK_ORDERS.md",
}
PROTECTED_PREFIXES = ("skills/", "schemas/", ".githooks/", "memory/approved/")


class PolicyError(ValueError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")


def identifier(prefix):
    return f"{prefix}-{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:8]}"


def relpath(value):
    value = str(value).replace("\\", "/")
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ":" in value or any(x in {"..", ".git"} for x in p.parts):
        raise PolicyError(f"Expected a safe project-relative path: {value}")
    return p.as_posix()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(record):
    return (json.dumps(record, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def git(root, *args):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if p.returncode:
        raise PolicyError(p.stderr.decode("utf-8", errors="replace").strip())
    return p.stdout


class View:
    """Index view prevents staged approvals being validated against unstaged edits."""
    def __init__(self, root=ROOT, staged=False):
        self.root = Path(root).resolve()
        self.staged = staged
        self.tracked = set()
        if staged:
            self.tracked = {x.decode("utf-8") for x in git(self.root, "ls-files", "-z").split(b"\0") if x}

    def read(self, path):
        path = relpath(path)
        if self.staged:
            if path not in self.tracked:
                raise PolicyError(f"Evidence/approval must be staged or tracked: {path}")
            return git(self.root, "show", f":{path}")
        absolute = (self.root / path).resolve()
        if not absolute.is_relative_to(self.root):
            raise PolicyError(f"Path escapes project: {path}")
        if not absolute.is_file():
            raise PolicyError(f"File not found: {path}")
        return absolute.read_bytes()

    def load(self, path):
        try:
            return json.loads(self.read(path).decode("utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError) as e:
            raise PolicyError(f"Invalid JSON {path}: {e}") from e

    def files(self, prefix, suffix=".json"):
        prefix = relpath(prefix).rstrip("/") + "/"
        if self.staged:
            return sorted(p for p in self.tracked if p.startswith(prefix) and p.endswith(suffix))
        return sorted(p.relative_to(self.root).as_posix() for p in (self.root / prefix).rglob(f"*{suffix}") if p.is_file())


def reference(view, path, locator=""):
    path = relpath(path)
    return {"path": path, "sha256": sha(view.read(path)), "locator": locator}


def verify_ref(view, ref):
    if not isinstance(ref, dict) or not ref.get("path") or not re.fullmatch(r"[0-9a-f]{64}", ref.get("sha256", "")):
        raise PolicyError("Evidence requires path and SHA256")
    data = view.read(ref["path"])
    if sha(data) != ref["sha256"]:
        raise PolicyError(f"Evidence changed since recording: {ref['path']}")
    return data


def write_new(root, path, record):
    path = relpath(path)
    destination = (Path(root) / path).resolve()
    if not destination.is_relative_to(Path(root).resolve()):
        raise PolicyError("Output escapes project")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as out:
        out.write(encoded(record))
    return path


def task_path(task):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", task):
        raise PolicyError("Invalid task ID")
    return f"work/tasks/{task}/task.json"


def validate_task(view, record):
    if record.get("schema_version") != 1:
        raise PolicyError("Task schema_version must be 1")
    for name in ("id", "title", "session_id", "actor", "created_at"):
        if not record.get(name):
            raise PolicyError(f"Task missing {name}")
    if record.get("role") not in {"executor", "steward", "human"}:
        raise PolicyError("Task role is invalid")
    verify_ref(view, record["request"])
    return record


def validate_approval(view, record):
    if record.get("status") != "human_confirmed" or record.get("approved_by") != "human_user":
        raise PolicyError("A promotion needs explicit human confirmation")
    if record.get("approval_type") not in {"specific_change", "bootstrap_user_requirements"}:
        raise PolicyError("Unknown approval type")
    for key in ("id", "session_id", "recorded_by", "reason", "recorded_at"):
        if not record.get(key):
            raise PolicyError(f"Approval missing {key}")
    source = record.get("source", {})
    text = verify_ref(view, source).decode("utf-8-sig")
    if not source.get("quote") or source["quote"] not in text:
        raise PolicyError("Human approval quote must occur in its retained source context")
    targets = record.get("targets", [])
    if not targets:
        raise PolicyError("Approval must bind concrete target paths and hashes")
    seen = set()
    for target in targets:
        path = relpath(target["path"])
        if path in seen or target.get("action") not in {"add", "modify", "delete"}:
            raise PolicyError("Duplicate target or invalid approval action")
        seen.add(path)
        if target["action"] != "delete" and not re.fullmatch(r"[0-9a-f]{64}", target.get("sha256", "")):
            raise PolicyError("Approval target requires exact SHA256")
    return record


def approved_payload(candidate, candidate_path, candidate_bytes, approval_id):
    record = dict(candidate)
    record["status"] = "approved"
    record["approval_id"] = approval_id
    record["source_candidate"] = {"path": relpath(candidate_path), "sha256": sha(candidate_bytes), "locator": "whole record"}
    return record


def approval_covers(approval, path, data, action=None):
    path = relpath(path)
    for target in approval["targets"]:
        if target["path"] == path and (action is None or target["action"] == action):
            return target["action"] == "delete" if data is None else target.get("sha256") == sha(data)
    return False


def validate_candidate(view, record, path):
    if record.get("schema_version") != 1 or record.get("status") != "proposed":
        raise PolicyError("Candidate must remain proposed, schema_version=1")
    if record.get("kind") not in KINDS or not record.get("claim") or not record.get("scope") or not record.get("limitations"):
        raise PolicyError("Candidate needs kind, claim, applicability scope and limitations")
    if PurePosixPath(path).stem != record.get("id"):
        raise PolicyError("Memory ID must match filename")
    origin = record.get("origin", {})
    task = validate_task(view, view.load(task_path(origin.get("task_id", ""))))
    if origin.get("session_id") != task["session_id"] or not origin.get("actor") or not origin.get("recorded_at"):
        raise PolicyError("Memory origin must identify the source task, session, author and time")
    verify_ref(view, origin.get("source_context", {}))
    if origin["source_context"] != task["request"]:
        raise PolicyError("Memory source context must match its recorded task request")
    previous = record.get("supersedes")
    if previous:
        if previous == record["id"] or not re.fullmatch(r"[A-Za-z0-9_-]+", previous):
            raise PolicyError("Invalid superseded memory ID")
        available = view.files("memory/candidates") + view.files("memory/approved")
        if not any(PurePosixPath(p).stem == previous for p in available):
            raise PolicyError("Superseded memory must already exist; preserve the old record")
    if not record.get("evidence"):
        raise PolicyError("Memory needs concrete evidence; inference cannot promote itself")
    for ref in record["evidence"]:
        verify_ref(view, ref)
    return record


def validate_memory(view, record, path):
    if record.get("status") == "proposed":
        return validate_candidate(view, record, path)
    if record.get("status") != "approved":
        raise PolicyError("Unknown memory status")
    candidate_ref = record.get("source_candidate", {})
    candidate_bytes = verify_ref(view, candidate_ref)
    candidate = json.loads(candidate_bytes.decode("utf-8-sig"))
    validate_candidate(view, candidate, candidate_ref["path"])
    approval = validate_approval(view, view.load(f"records/approvals/{record.get('approval_id', '')}.json"))
    bindings = approval.get("candidates", [])
    if not any(x.get("id") == candidate["id"] and x.get("sha256") == sha(candidate_bytes) for x in bindings):
        raise PolicyError("Approval does not bind this exact candidate")
    if record != approved_payload(candidate, candidate_ref["path"], candidate_bytes, approval["id"]):
        raise PolicyError("Approved memory differs from the reviewed candidate")
    if not approval_covers(approval, path, encoded(record)):
        raise PolicyError("Approval does not cover the exact approved record")
    return record


def section(text, heading):
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line == heading or line.startswith(heading + " "):
            level = len(line) - len(line.lstrip("#"))
            for end in range(start + 1, len(lines)):
                match = re.match(r"^(#{1,6})\s", lines[end])
                if match and len(match[1]) <= level:
                    return "\n".join(lines[start:end]).strip() + "\n"
            return "\n".join(lines[start:]).strip() + "\n"
    raise PolicyError(f"Section not found: {heading}")


def policy_for(view):
    record = view.load("configs/governance.policy.json")
    for name in ("executor_prefixes", "protected_files", "protected_prefixes", "excluded_prefixes"):
        if not isinstance(record.get(name), list) or not all(isinstance(p, str) and p and relpath(p) for p in record[name]):
            raise PolicyError(f"Invalid governance policy: {name}")
    return record


def protected(path, policy=None):
    extra = policy or {}
    return path in PROTECTED_FILES or path in extra.get("protected_files", []) or path.startswith(PROTECTED_PREFIXES + tuple(extra.get("protected_prefixes", []))) or (path.startswith("configs/") and "contract" in path)


def immutable(path):
    return path.startswith(("memory/candidates/", "memory/approved/", "records/approvals/", "records/requests/")) or (
        path.startswith("work/tasks/") and (path.endswith("/task.json") or path.endswith("/request.md") or "/events/" in path)
    )


def guard_changes(view, changes, role):
    policy = policy_for(view)
    approvals = [validate_approval(view, view.load(p)) for p in view.files("records/approvals")]
    for action, path in changes:
        path = relpath(path)
        if path.startswith(tuple(policy["excluded_prefixes"])):
            raise PolicyError(f"Do not commit original materials, installed tools or environments: {path}")
        if action != "A" and immutable(path):
            raise PolicyError(f"Append a superseding record; do not overwrite provenance: {path}")
        if role == "executor" and (protected(path, policy) or not path.startswith(tuple(policy["executor_prefixes"]))):
            raise PolicyError(f"Executor cannot modify formal project context: {path}; prepare a proposal in work/reviews/")
        if role != "executor" and protected(path, policy):
            payload = None if action == "D" else view.read(path)
            required_action = {"A": "add", "M": "modify", "D": "delete"}.get(action)
            if required_action is None or not any(approval_covers(a, path, payload, required_action) for a in approvals):
                raise PolicyError(f"Protected change needs human-source approval bound to this content: {path}")
        if path.startswith("memory/") and path.endswith(".json") and action != "D":
            validate_memory(view, view.load(path), path)
        if path.startswith("records/approvals/") and action != "D":
            if role == "executor":
                raise PolicyError("Executors cannot create human approval records")
            validate_approval(view, view.load(path))


def check(view):
    errors = []
    required = ("AGENTS.md", "context/INDEX.md", "context/STATUS.json", "context/catalog.json", "context/GOVERNANCE.md")
    for path in required:
        try:
            view.read(path)
        except PolicyError as e:
            errors.append(str(e))
    try:
        policy_for(view)
        if len(view.read("AGENTS.md").decode("utf-8-sig").splitlines()) > 90:
            errors.append("AGENTS.md exceeds 90 lines; move detailed content to indexed references")
        catalog = view.load("context/catalog.json")
        for item in catalog["topics"].values():
            for document in item["documents"]:
                text = view.read(document["path"]).decode("utf-8-sig")
                if document.get("heading"):
                    section(text, document["heading"])
        for path in view.files("memory/candidates") + view.files("memory/approved"):
            validate_memory(view, view.load(path), path)
        for path in view.files("records/approvals"):
            validate_approval(view, view.load(path))
        for path in view.files("work/tasks"):
            if path.endswith("/task.json"):
                task = validate_task(view, view.load(path))
                if path != task_path(task["id"]):
                    raise PolicyError("Task ID does not match its directory")
            elif "/events/" in path:
                event = view.load(path)
                if event.get("status") not in TASK_STATES or not event.get("actor") or not event.get("summary"):
                    raise PolicyError(f"Invalid task event: {path}")
                task = validate_task(view, view.load(task_path(event.get("task_id", ""))))
                if event.get("session_id") != task["session_id"] or not event.get("recorded_at") or PurePosixPath(path).stem != event.get("id") or not path.startswith(f"work/tasks/{task['id']}/events/"):
                    raise PolicyError(f"Task event provenance mismatch: {path}")
                for ref in event.get("evidence", []):
                    verify_ref(view, ref)
        for path in ("README.md", "AGENTS.md", "context/INDEX.md", "context/GOVERNANCE.md", "skills/project-memory/SKILL.md", "skills/project-workflow/SKILL.md"):
            text = view.read(path).decode("utf-8-sig")
            for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                if "://" in link or link.startswith("#"):
                    continue
                destination = (view.root / PurePosixPath(path).parent / link.split("#")[0]).resolve()
                if not destination.is_relative_to(view.root):
                    raise PolicyError(f"Document link escapes project: {path}: {link}")
                relative = destination.relative_to(view.root).as_posix()
                if not destination.is_dir():
                    view.read(relative)
    except (PolicyError, KeyError, TypeError, ValueError) as e:
        errors.append(str(e))
    if errors:
        raise PolicyError("\n".join(errors))
    return {"status": "PASS", "scope": "framework links, evidence hashes and memory provenance only; domain results need their own acceptance evidence"}


def print_json(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    context = sub.add_parser("context")
    context.add_argument("--topic")
    context.add_argument("--work-order")
    context.add_argument("--with-spec", action="store_true")
    read = sub.add_parser("section")
    read.add_argument("--path", required=True)
    read.add_argument("--heading", required=True)
    start = sub.add_parser("task-start")
    start.add_argument("--title", required=True)
    start.add_argument("--work-order")
    start.add_argument("--session", required=True)
    start.add_argument("--actor", required=True)
    start.add_argument("--role", choices=["executor", "steward", "human"], default="executor")
    start.add_argument("--model", default="unspecified")
    request_group = start.add_mutually_exclusive_group(required=True)
    request_group.add_argument("--request-text")
    request_group.add_argument("--request-file")
    update = sub.add_parser("task-update")
    update.add_argument("--task", required=True)
    update.add_argument("--status", choices=sorted(TASK_STATES), required=True)
    update.add_argument("--summary", required=True)
    update.add_argument("--actor", required=True)
    update.add_argument("--evidence", action="append", default=[])
    note = sub.add_parser("propose")
    note.add_argument("--task", required=True)
    note.add_argument("--kind", choices=sorted(KINDS), required=True)
    note.add_argument("--claim", required=True)
    note.add_argument("--scope", required=True)
    note.add_argument("--limitations", required=True)
    note.add_argument("--actor", required=True)
    note.add_argument("--evidence", action="append", required=True)
    note.add_argument("--supersedes")
    recall = sub.add_parser("recall")
    recall.add_argument("--scope")
    recall.add_argument("--kind", choices=sorted(KINDS))
    recall.add_argument("--include-candidates", action="store_true")
    plan = sub.add_parser("plan-promotion")
    plan.add_argument("--candidate", required=True)
    plan.add_argument("--approval-id", required=True)
    promote = sub.add_parser("promote")
    promote.add_argument("--candidate", required=True)
    promote.add_argument("--approval", required=True)
    promote.add_argument("--role", choices=["executor", "steward", "human"], default="executor")
    validate = sub.add_parser("check")
    validate.add_argument("--staged", action="store_true")
    guard = sub.add_parser("guard")
    guard.add_argument("--staged", action="store_true", required=True)
    guard.add_argument("--role", choices=["executor", "steward", "human"], default=os.environ.get("PROJECT_ROLE", "executor"))
    args = parser.parse_args(argv)
    view = View(ROOT, staged=getattr(args, "staged", False))
    if args.command == "status":
        tasks = []
        for path in view.files("work/tasks"):
            if not path.endswith("/task.json"):
                continue
            record = view.load(path)
            events = view.files(f"work/tasks/{record['id']}/events")
            last = max((view.load(p) for p in events), key=lambda x: (x["recorded_at"], x["id"]), default={})
            tasks.append({"id": record["id"], "title": record["title"], "work_order": record.get("work_order"), "status": last.get("status", "running"), "summary": last.get("summary", "")})
        print_json({"project": view.load("context/STATUS.json"), "tasks": tasks})
    elif args.command == "context":
        key = args.work_order or args.topic
        catalog = view.load("context/catalog.json")
        if not key:
            print_json({k: {"summary": v["summary"], "documents": v["documents"]} for k, v in catalog["topics"].items()})
        elif key not in catalog["topics"]:
            raise PolicyError(f"Unknown context topic: {key}")
        else:
            item = catalog["topics"][key]
            print_json(item)
            for document in item["documents"]:
                if document.get("heading") and (document["path"] != "spec.md" or args.with_spec):
                    print(section(view.read(document["path"]).decode("utf-8-sig"), document["heading"]))
    elif args.command == "section":
        print(section(view.read(args.path).decode("utf-8-sig"), args.heading))
    elif args.command == "task-start":
        if args.work_order and args.work_order not in view.load("context/catalog.json")["topics"]:
            raise PolicyError("Unknown work order; task creation does not authorize execution")
        task_id = identifier("TASK")
        base = f"work/tasks/{task_id}"
        source_text = args.request_text if args.request_text is not None else view.read(args.request_file).decode("utf-8-sig")
        source = ROOT / base / "request.md"
        source.parent.mkdir(parents=True, exist_ok=False)
        source.write_text(source_text.rstrip() + "\n", encoding="utf-8")
        record = {"schema_version": 1, "id": task_id, "title": args.title, "work_order": args.work_order, "session_id": args.session, "actor": args.actor, "role": args.role, "model": args.model, "created_at": now(), "request": reference(view, f"{base}/request.md", "exact user request or retained source context"), "source_request": reference(view, args.request_file) if args.request_file else None, "inputs": [reference(view, p) for p in ("AGENTS.md", "context/catalog.json", "context/GOVERNANCE.md")]}
        validate_task(view, record)
        write_new(ROOT, f"{base}/task.json", record)
        print_json({"task_id": task_id, "path": base, "authorization": "Only the retained request authorizes action; a task record itself grants no permission."})
    elif args.command == "task-update":
        task = validate_task(view, view.load(task_path(args.task)))
        event = {"schema_version": 1, "id": identifier("EVENT"), "task_id": task["id"], "session_id": task["session_id"], "recorded_at": now(), "actor": args.actor, "status": args.status, "summary": args.summary, "evidence": [reference(view, p) for p in args.evidence]}
        path = write_new(ROOT, f"work/tasks/{task['id']}/events/{event['id']}.json", event)
        print_json({"event": path, "status": event["status"]})
    elif args.command == "propose":
        task = validate_task(view, view.load(task_path(args.task)))
        mem_id = identifier("MEM")
        record = {"schema_version": 1, "id": mem_id, "status": "proposed", "kind": args.kind, "claim": args.claim, "scope": args.scope, "limitations": args.limitations, "supersedes": args.supersedes, "origin": {"task_id": task["id"], "session_id": task["session_id"], "actor": args.actor, "recorded_at": now(), "source_context": task["request"]}, "evidence": [reference(view, p) for p in args.evidence]}
        path = f"memory/candidates/{mem_id}.json"
        validate_candidate(view, record, path)
        write_new(ROOT, path, record)
        print_json({"candidate": path, "status": "proposed", "instruction": "This is not an approved fact or project rule."})
    elif args.command == "recall":
        paths = view.files("memory/approved") + (view.files("memory/candidates") if args.include_candidates else [])
        records = [(p, view.load(p)) for p in paths]
        superseded = {r.get("supersedes") for _, r in records if r.get("status") == "approved" and r.get("supersedes")}
        result = []
        for path, record in records:
            if record["id"] in superseded or (args.scope and args.scope.casefold() not in record["scope"].casefold()) or (args.kind and args.kind != record["kind"]):
                continue
            result.append({"id": record["id"], "status": record["status"], "kind": record["kind"], "scope": record["scope"], "summary": record["claim"][:180], "path": path})
        print_json(result)
    elif args.command in {"plan-promotion", "promote"}:
        candidate_path = f"memory/candidates/{args.candidate}.json"
        candidate_bytes = view.read(candidate_path)
        candidate = validate_candidate(view, json.loads(candidate_bytes.decode("utf-8-sig")), candidate_path)
        approval_id = args.approval_id if args.command == "plan-promotion" else args.approval
        if not re.fullmatch(r"[A-Za-z0-9_-]+", approval_id):
            raise PolicyError("Invalid approval ID")
        result = approved_payload(candidate, candidate_path, candidate_bytes, approval_id)
        destination = f"memory/approved/{candidate['id']}.json"
        if args.command == "plan-promotion":
            preview = write_new(ROOT, f"work/reviews/{candidate['id']}/{approval_id}/approved-preview.json", result)
            print_json({"preview": preview, "target": destination, "sha256": sha(encoded(result)), "candidate_sha256": sha(candidate_bytes), "next": "Review applicability/evidence; obtain explicit user approval for this concrete proposal, then retain its exact quote in an approval record."})
        else:
            if args.role == "executor":
                raise PolicyError("An executor can propose memory but cannot promote it")
            validate_memory(view, result, destination)
            write_new(ROOT, destination, result)
            print_json({"approved": destination})
    elif args.command == "check":
        print_json(check(view))
    elif args.command == "guard":
        tokens = [x.decode("utf-8") for x in git(ROOT, "diff", "--cached", "--name-status", "--no-renames", "-z").split(b"\0") if x]
        changes = list(zip(tokens[0::2], tokens[1::2]))
        guard_changes(view, changes, args.role)
        print_json(check(view))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PolicyError, FileExistsError, OSError, KeyError) as exc:
        print(f"FRAMEWORK CHECK FAILED: {exc}", file=sys.stderr)
        raise SystemExit(2)
