"""Compare recorded tools/list evidence with a reviewed pin, entirely offline."""
import argparse

from audit_local_mcp_configs import canonical, catalog_record, compare_catalog, load


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, help="JSON: identity and response")
    parser.add_argument("--approval", help="Separately reviewed JSON pin")
    options = parser.parse_args()
    try:
        capture = load(options.capture)
        if not isinstance(capture, dict) or set(capture) != {"identity", "response"}:
            raise ValueError("invalid capture")
        if options.approval:
            result = compare_catalog(capture["identity"], capture["response"], load(options.approval))
        else:
            result = {"status": "REVIEW_REQUIRED", "observed": catalog_record(capture["identity"], capture["response"])}
    except (OSError, ValueError, TypeError, RecursionError):
        # Do not echo exception text, paths, identity, schemas or descriptions.
        result = {"status": "BLOCKED", "findings": ["INVALID_CATALOG_OR_APPROVAL"]}
    print(canonical(result))
    return 0 if result["status"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
