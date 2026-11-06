"""Local artifact execution only. Not Origin G.A.T.E. or an external authority.

Trusted operator owns the state root and code. Untrusted proposals cannot select
paths, executable code, adapters, credentials, approvals, or policy. No network.
"""

from __future__ import annotations

import contextlib
import errno
import fcntl
import hashlib
import json
import os
import re
import sqlite3
import stat
import time
from pathlib import Path

VERSION = "relay.local-command.v1"
MAX_BYTES = 1_048_576
TOOLS = {
    "write_local_artifact": {
        "effect": "local_file",
        "scope": "owned artifacts directory",
        "idempotent": True,
        "network": False,
    },
    "external_action": {
        "effect": "external",
        "scope": "unsupported",
        "idempotent": False,
        "network": False,
    },
}


class ContractError(ValueError):
    pass


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def exact(obj, keys, label):
    if not isinstance(obj, dict) or set(obj) != set(keys):
        raise ContractError(f"{label} requires exactly {sorted(keys)}")


def text(value, label, limit=10000):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ContractError(f"{label} must be a nonempty string <= {limit} characters")


def validate(proposal):
    exact(
        proposal,
        {
            "version",
            "idempotency_key",
            "goal",
            "context",
            "action",
            "acceptance",
            "budget",
            "blockers",
        },
        "proposal",
    )
    if proposal["version"] != VERSION:
        raise ContractError("Unsupported proposal version")
    text(proposal["idempotency_key"], "idempotency_key", 200)
    text(proposal["goal"], "goal")
    if not isinstance(proposal["context"], dict):
        raise ContractError(
            "context must be an object; its content is data, not authority"
        )
    if len(canonical(proposal["context"]).encode()) > 65536:
        raise ContractError("context too large")
    if not isinstance(proposal["blockers"], list) or len(proposal["blockers"]) > 30:
        raise ContractError(
            "blockers must be a list of <= 30 explicit unresolved requirements"
        )
    for blocker in proposal["blockers"]:
        text(blocker, "blocker", 1000)
    exact(proposal["budget"], {"max_attempts", "max_bytes"}, "budget")
    for name, lower, upper in (("max_attempts", 1, 3), ("max_bytes", 1, MAX_BYTES)):
        value = proposal["budget"][name]
        if type(value) is not int or not lower <= value <= upper:
            raise ContractError(f"budget.{name} must be {lower}..{upper}")
    exact(proposal["action"], {"tool", "input"}, "action")
    tool = proposal["action"]["tool"]
    if not isinstance(tool, str) or tool not in TOOLS:
        raise ContractError("Tool is not in the trusted registry")
    exact(proposal["acceptance"], {"sha256", "contains"}, "acceptance")
    gates = proposal["acceptance"]
    if not isinstance(gates["contains"], list) or len(gates["contains"]) > 30:
        raise ContractError("contains must be a list of <= 30 required substrings")
    for item in gates["contains"]:
        text(item, "required substring", 10000)
    if tool == "write_local_artifact":
        exact(proposal["action"]["input"], {"content"}, "local input")
        content = proposal["action"]["input"]["content"]
        text(content, "content", MAX_BYTES)
        if len(content.encode()) > proposal["budget"]["max_bytes"]:
            raise ContractError("Artifact exceeds byte budget")
        if not isinstance(gates["sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", gates["sha256"]
        ):
            raise ContractError("An expected SHA-256 is mandatory for a local artifact")
    else:
        exact(
            proposal["action"]["input"],
            {"operation", "target", "description"},
            "external input",
        )
        for name, value in proposal["action"]["input"].items():
            text(value, name)
        if gates["sha256"] is not None:
            raise ContractError(
                "External evidence is not implemented; sha256 must be null"
            )
    # Copy prevents a caller mutating the contract after validation.
    return json.loads(canonical(proposal))


class Harness:
    """Single-host local executor. State root must be trusted and not shared with adversaries."""

    def __init__(self, root):
        self.root = Path(os.path.abspath(root))
        # Validate before any mkdir, including a symlink in an ancestor.
        for path in (self.root, *self.root.parents):
            if path.is_symlink():
                raise ContractError("State root and its ancestors must not be symlinks")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.artifacts = self.root / "artifacts"
        if self.artifacts.is_symlink():
            raise ContractError("Artifact directory must not be a symlink")
        self.artifacts.mkdir(mode=0o700, exist_ok=True)
        for path in (self.root, self.artifacts):
            if path.is_symlink() or not path.is_dir():
                raise ContractError("State directories must not be symlinks")
            if path.stat().st_mode & 0o022:
                raise ContractError(
                    "State directories must not be group/world writable"
                )
        for name in (
            "journal.sqlite3",
            "journal.sqlite3-wal",
            "journal.sqlite3-shm",
            ".lock",
        ):
            p = self.root / name
            if p.is_symlink() or (
                p.exists() and (not p.is_file() or p.stat().st_nlink != 1)
            ):
                raise ContractError("Unsafe state file")
        with self._locked():
            self.db = sqlite3.connect(self.root / "journal.sqlite3", timeout=10)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.executescript("""
              CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, idem TEXT UNIQUE NOT NULL, contract TEXT NOT NULL,
                contract_hash TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL,
                reason TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                body TEXT NOT NULL, previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
              CREATE TRIGGER IF NOT EXISTS no_event_update BEFORE UPDATE ON events
                BEGIN SELECT RAISE(ABORT, 'History is append-only'); END;
              CREATE TRIGGER IF NOT EXISTS no_event_delete BEFORE DELETE ON events
                BEGIN SELECT RAISE(ABORT, 'History is append-only'); END;
            """)

    def close(self):
        self.db.close()

    @contextlib.contextmanager
    def _locked(self):
        fd = os.open(self.root / ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)

    def _event(self, task_id, kind, data):
        row = self.db.execute(
            "SELECT event_hash FROM events WHERE task_id=? ORDER BY seq DESC LIMIT 1",
            (task_id,),
        ).fetchone()
        previous = row[0] if row else "0" * 64
        body = canonical(
            {"task_id": task_id, "kind": kind, "data": data, "time_ns": time.time_ns()}
        )
        self.db.execute(
            "INSERT INTO events(task_id,body,previous_hash,event_hash) VALUES (?,?,?,?)",
            (task_id, body, previous, digest((previous + body).encode())),
        )

    def _task(self, task_id):
        if not isinstance(task_id, str) or not re.fullmatch(r"[0-9a-f]{32}", task_id):
            raise ContractError("Invalid task id")
        row = self.db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ContractError("Unknown task id")
        if digest(row["contract"].encode()) != row["contract_hash"]:
            raise ContractError("Persisted contract integrity failure")
        return dict(row), validate(json.loads(row["contract"]))

    def submit(self, proposal):
        contract = validate(proposal)
        serialized = canonical(contract)
        contract_hash = digest(serialized.encode())
        task_id = digest(contract["idempotency_key"].encode())[:32]
        with self._locked(), self.db:
            row = self.db.execute(
                "SELECT * FROM tasks WHERE idem=?", (contract["idempotency_key"],)
            ).fetchone()
            if row:
                if row["contract_hash"] != contract_hash:
                    raise ContractError(
                        "Idempotency key already binds a different contract"
                    )
                return row["id"]
            self.db.execute(
                "INSERT INTO tasks VALUES (?,?,?,?,?,?,?)",
                (
                    task_id,
                    contract["idempotency_key"],
                    serialized,
                    contract_hash,
                    "pending",
                    0,
                    "Submitted; not executed",
                ),
            )
            self._event(task_id, "submitted", {"contract_hash": contract_hash})
        return task_id

    def _set(self, task_id, state, reason, evidence=None):
        self.db.execute(
            "UPDATE tasks SET state=?, reason=? WHERE id=?", (state, reason, task_id)
        )
        self._event(task_id, state, {"reason": reason, "evidence": evidence})

    def _read_artifact(self, task_id):
        path = self.artifacts / (task_id + ".txt")
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return None
        try:
            info = os.fstat(fd)
            # Recover a power loss between atomic linking and temp unlinking.
            temp = self.artifacts / (task_id + ".tmp")
            if info.st_nlink == 2 and not temp.is_symlink() and temp.exists():
                temp_info = temp.stat()
                if (temp_info.st_dev, temp_info.st_ino) == (info.st_dev, info.st_ino):
                    temp.unlink()
                    info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_size > MAX_BYTES
            ):
                raise ContractError("Artifact is not a bounded regular, unlinked file")
            with os.fdopen(fd, "rb", closefd=False) as stream:
                return stream.read(MAX_BYTES + 1)
        finally:
            os.close(fd)

    def _evidence(self, task_id, contract):
        content = self._read_artifact(task_id)
        if content is None:
            return None
        expected = contract["action"]["input"]["content"].encode()
        observed_hash = digest(content)
        gates = {
            "exact_input_bytes": content == expected,
            "sha256": observed_hash == contract["acceptance"]["sha256"],
            "byte_budget": len(content) <= contract["budget"]["max_bytes"],
            "required_substrings": all(
                s.encode() in content for s in contract["acceptance"]["contains"]
            ),
        }
        return {
            "sha256": observed_hash,
            "bytes": len(content),
            "gates": gates,
            "artifact": "artifacts/" + task_id + ".txt",
            "all_passed": all(gates.values()),
        }

    def _write(self, task_id, content):
        # Atomic no-clobber link. A crash leaves either a temp or the final file;
        # recovery checks exact bytes before deciding anything was completed.
        temp = self.artifacts / (task_id + ".tmp")
        final = self.artifacts / (task_id + ".txt")
        if temp.is_symlink():
            raise ContractError("Unsafe temporary artifact")
        if temp.exists():
            if not temp.is_file() or temp.stat().st_nlink != 1:
                raise ContractError("Unsafe temporary artifact")
            temp.unlink()
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb", closefd=False) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(fd)
        finally:
            os.close(fd)
        try:
            os.link(temp, final, follow_symlinks=False)
        finally:
            temp.unlink()
        fd = os.open(self.artifacts, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def run(self, task_id, *, fault=None):
        if fault not in (None, "after_intent", "after_write"):
            raise ContractError("Unknown test fault")
        with self._locked():
            task, contract = self._task(task_id)
            self._receipt(task_id)  # Fail closed on journal corruption before effects.
            if contract["action"]["tool"] == "external_action":
                with self.db:
                    if task["state"] != "blocked":
                        self._set(
                            task_id,
                            "blocked",
                            "No external adapter, host permission decision, or verified external receipt. Model proposals cannot grant authority.",
                        )
                return self._receipt(task_id)
            if contract["blockers"]:
                with self.db:
                    if task["state"] != "blocked":
                        self._set(task_id, "blocked", "; ".join(contract["blockers"]))
                return self._receipt(task_id)
            try:
                evidence = self._evidence(task_id, contract)
            except (OSError, ContractError) as exc:
                with self.db:
                    self._set(
                        task_id, "failed", "Unsafe/unreadable artifact: " + str(exc)
                    )
                return self._receipt(task_id)
            if task["state"] == "complete":
                if not evidence or not evidence["all_passed"]:
                    with self.db:
                        self._set(
                            task_id,
                            "failed",
                            "Previously verified artifact changed or disappeared",
                            evidence,
                        )
                return self._receipt(task_id)
            if task["state"] in ("failed", "blocked"):
                return self._receipt(task_id)
            if evidence:
                with self.db:
                    self._set(
                        task_id,
                        "complete" if evidence["all_passed"] else "failed",
                        (
                            "Recovered and verified existing bytes"
                            if evidence["all_passed"]
                            else "Existing artifact does not satisfy required gates"
                        ),
                        evidence,
                    )
                return self._receipt(task_id)
            if task["attempts"] >= contract["budget"]["max_attempts"]:
                with self.db:
                    self._set(
                        task_id,
                        "failed",
                        "Attempt budget exhausted; no verified artifact",
                    )
                return self._receipt(task_id)
            with self.db:
                self.db.execute(
                    "UPDATE tasks SET attempts=attempts+1 WHERE id=?", (task_id,)
                )
                self._set(task_id, "running", "Durable execution intent recorded")
            if fault == "after_intent":
                os._exit(91)
            try:
                self._write(task_id, contract["action"]["input"]["content"].encode())
                if fault == "after_write":
                    os._exit(92)
                evidence = self._evidence(task_id, contract)
                with self.db:
                    passed = bool(evidence and evidence["all_passed"])
                    self._set(
                        task_id,
                        "complete" if passed else "failed",
                        (
                            "Local artifact verified; no external task claimed"
                            if passed
                            else "Required artifact gate failed"
                        ),
                        evidence,
                    )
            except (OSError, ContractError) as exc:
                with self.db:
                    attempts = self.db.execute(
                        "SELECT attempts FROM tasks WHERE id=?", (task_id,)
                    ).fetchone()[0]
                    denied = isinstance(exc, PermissionError) or (
                        isinstance(exc, OSError)
                        and exc.errno in (errno.EACCES, errno.EPERM, errno.EROFS)
                    )
                    state = (
                        "blocked"
                        if denied
                        else (
                            "failed"
                            if attempts >= contract["budget"]["max_attempts"]
                            or isinstance(exc, ContractError)
                            else "retryable"
                        )
                    )
                    self._set(task_id, state, "Local operation failed: " + str(exc))
            return self._receipt(task_id)

    def _receipt(self, task_id):
        task, contract = self._task(task_id)
        rows = self.db.execute(
            "SELECT * FROM events WHERE task_id=? ORDER BY seq", (task_id,)
        ).fetchall()
        previous = "0" * 64
        events = []
        if not rows:
            raise ContractError("Missing task history")
        for row in rows:
            if row["previous_hash"] != previous or row["event_hash"] != digest(
                (previous + row["body"]).encode()
            ):
                raise ContractError("History integrity failure")
            previous = row["event_hash"]
            events.append(
                {"seq": row["seq"], **json.loads(row["body"]), "event_hash": previous}
            )
        if (
            events[0]["kind"] != "submitted"
            or events[0]["data"]["contract_hash"] != task["contract_hash"]
        ):
            raise ContractError("Contract is not bound to submission history")
        expected_state = (
            "pending" if events[-1]["kind"] == "submitted" else events[-1]["kind"]
        )
        if task["state"] != expected_state or task["attempts"] != sum(
            e["kind"] == "running" for e in events
        ):
            raise ContractError("Task projection disagrees with history")
        evidence = None
        if contract["action"]["tool"] == "write_local_artifact":
            try:
                evidence = self._evidence(task_id, contract)
            except (OSError, ContractError):
                pass
        current_verified = bool(evidence and evidence["all_passed"])
        complete = (
            task["state"] == "complete"
            and current_verified
            and not contract["blockers"]
        )
        return {
            "version": "relay.local-receipt.v1",
            "task_id": task_id,
            "state": (
                task["state"]
                if task["state"] != "complete" or complete
                else "invalidated"
            ),
            "complete": complete,
            "scope": "local_artifact_only",
            "external_task_complete": False,
            "reason": (
                task["reason"]
                if task["state"] != "complete" or complete
                else "Artifact no longer verifies"
            ),
            "contract_hash": task["contract_hash"],
            "attempts": task["attempts"],
            "max_attempts": contract["budget"]["max_attempts"],
            "evidence": evidence,
            "cost": {
                "amount": None,
                "currency": None,
                "status": "unknown",
                "note": "No model/network calls; host compute cost is not metered",
            },
            "history_head": previous,
            "events": events,
        }

    def receipt(self, task_id):
        with self._locked():
            return self._receipt(task_id)


def artifact_contract(key, goal, content, *, context=None, contains=None):
    """Operator convenience only; generated contracts still pass strict validation."""
    return {
        "version": VERSION,
        "idempotency_key": key,
        "goal": goal,
        "context": context or {},
        "action": {"tool": "write_local_artifact", "input": {"content": content}},
        "acceptance": {"sha256": digest(content.encode()), "contains": contains or []},
        "budget": {"max_attempts": 2, "max_bytes": MAX_BYTES},
        "blockers": [],
    }
