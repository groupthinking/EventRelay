import argparse
import json
import os
import sqlite3
import stat
import sys

from .adapter import prepare_review_artifact
from .core import MAX_BYTES, ContractError, Harness


def load(path):
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ContractError("Input JSON must be a regular file")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(2 * MAX_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > 2 * MAX_BYTES:
        raise ContractError("Input JSON is too large")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ContractError("Duplicate JSON key")
            result[key] = value
        return result

    return json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=lambda _: (_ for _ in ()).throw(
            ContractError("Nonfinite JSON number")
        ),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Offline EventRelay durable local artifact slice"
    )
    parser.add_argument(
        "--state", required=True, help="Trusted operator-owned state directory"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("submit").add_argument("proposal")
    review = sub.add_parser("import-review")
    review.add_argument("actions")
    review.add_argument("--key", required=True)
    run = sub.add_parser("run")
    run.add_argument("task_id")
    run.add_argument(
        "--test-crash",
        choices=["after_intent", "after_write"],
        help="FAULT INJECTION: exits without cleanup",
    )
    sub.add_parser("receipt").add_argument("task_id")
    args = parser.parse_args()
    harness = None
    try:
        harness = Harness(args.state)
        if args.command in ("submit", "import-review"):
            proposal = (
                load(args.proposal)
                if args.command == "submit"
                else prepare_review_artifact(args.key, load(args.actions))
            )
            result = {"task_id": harness.submit(proposal), "executed": False}
        elif args.command == "run":
            result = harness.run(args.task_id, fault=args.test_crash)
        else:
            result = harness.receipt(args.task_id)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if "complete" not in result or result["complete"] else 2
    except (ContractError, ValueError, OSError, sqlite3.Error, RecursionError) as exc:
        print(json.dumps({"error": str(exc), "complete": False}), file=sys.stderr)
        return 1
    finally:
        if harness is not None:
            harness.close()


if __name__ == "__main__":
    sys.exit(main())
