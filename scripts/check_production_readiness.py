import ast
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("production-readiness")


def check_env_vars():
    logger.info("Checking environment variables...")
    required_groups = [
        (("GEMINI_API_KEY", "GOOGLE_API_KEY"), "GEMINI_API_KEY or GOOGLE_API_KEY"),
        (("YOUTUBE_API_KEY",), "YOUTUBE_API_KEY"),
    ]
    missing = [
        label
        for names, label in required_groups
        if not any(os.getenv(name) for name in names)
    ]
    if missing:
        environment = (
            (os.getenv("ENVIRONMENT") or "").strip()
            or (os.getenv("VERCEL_ENV") or "").strip()
            or "development"
        ).lower()
        if environment == "production":
            logger.error(f"❌ Missing critical env vars in production: {missing}")
            return True
        else:
            logger.warning(f"Missing critical env vars (non-fatal warning): {missing}")
    return False


def _parse_main():
    main_path = Path("src/youtube_extension/main.py")
    if not main_path.exists():
        logger.error("❌ main.py not found.")
        return None
    try:
        return ast.parse(main_path.read_text())
    except (OSError, SyntaxError) as exc:
        logger.error("❌ Unable to parse main.py: %s", exc)
        return None


def _middleware_call(tree, middleware_name):
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_middleware"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == middleware_name
        ):
            return node
    return None


def check_cors():
    tree = _parse_main()
    if tree is None:
        return True

    call = _middleware_call(tree, "CORSMiddleware")
    keywords = {item.arg: item.value for item in call.keywords} if call else {}
    origins = keywords.get("allow_origins")
    credentials = keywords.get("allow_credentials")
    middleware_is_guarded = (
        isinstance(origins, ast.Name)
        and origins.id == "_allowed_origins"
        and isinstance(credentials, ast.Constant)
        and credentials.value is True
    )

    origin_assignment = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "_allowed_origins" for target in targets):
                origin_assignment = node.value
                break

    policy_names = (
        {node.id for node in ast.walk(origin_assignment) if isinstance(node, ast.Name)}
        if origin_assignment is not None
        else set()
    )
    policy_is_guarded = {
        "_PRODUCTION_ORIGINS",
        "_EXTRA_ORIGINS",
        "_IS_PRODUCTION",
        "_DEV_ORIGINS",
    }.issubset(policy_names)

    if middleware_is_guarded and policy_is_guarded:
        logger.info("✅ CORS middleware uses the production-gated origin policy.")
        return False
    logger.error("❌ CORS middleware is not bound to the production-gated origin policy.")
    return True


def check_headers():
    tree = _parse_main()
    if tree is None:
        return True

    required = {
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
    }
    assignments = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Constant):
            continue
        for target in node.targets:
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Attribute)
                and target.value.attr == "headers"
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "response"
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                assignments[target.slice.value] = node.value.value

    registered = _middleware_call(tree, "SecurityHeadersMiddleware") is not None
    if registered and all(assignments.get(name) == value for name, value in required.items()):
        logger.info("✅ Security-header middleware assignments and registration verified.")
        return False
    logger.error("❌ Security-header middleware assignments or registration are missing.")
    return True


def check_logging():
    logger.info("Checking production logging configurations...")
    main_path = Path("src/youtube_extension/main.py")
    if not main_path.exists():
        logger.error("❌ main.py not found.")
        return True

    content = main_path.read_text()
    try:
        tree = ast.parse(content)
    except SyntaxError as exc:
        logger.error("❌ Unable to parse main.py logging configuration: %s", exc)
        return True

    # 1. Detect DEBUG defaults structurally so whitespace and line breaks cannot bypass the gate.
    def is_debug(node):
        return (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "logging"
            and node.attr == "DEBUG"
        ) or (isinstance(node, ast.Name) and node.id == "DEBUG")

    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        name = call.func.attr if isinstance(call.func, ast.Attribute) else None
        if name == "basicConfig" and any(
            keyword.arg == "level" and is_debug(keyword.value)
            for keyword in call.keywords
        ):
            logger.error("❌ Production logging cannot default to DEBUG level (leaks sensitive info).")
            return True
        if name == "setLevel" and call.args and is_debug(call.args[0]):
            logger.error("❌ Production logging cannot default to DEBUG level (leaks sensitive info).")
            return True

    # 2. Check Sentry PII settings to prevent information leakage, excluding comment lines
    has_pii_check = False
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        line_no_spaces = line.replace(" ", "")
        if "send_default_pii" in line_no_spaces:
            has_pii_check = True
            if "send_default_pii=True" in line_no_spaces:
                logger.error("❌ Sentry send_default_pii must not be hardcoded to True.")
                return True

    if has_pii_check:
        logger.info("✅ Sentry PII safety check configured.")
    else:
        logger.warning("Sentry PII safety check not found (ensure PII is not sent to Sentry).")

    logger.info("✅ Production logging configuration checks passed.")
    return False


def check_dependencies():
    logger.info("Checking dependency safety...")
    has_error = False

    # 1. Static file check for wildcards / unsafe patterns
    req_path = Path("requirements.txt")
    if req_path.exists():
        reqs = req_path.read_text()
        for line in reqs.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "==" in line:
                parts = line.split("==")
                if len(parts) > 1 and parts[1].strip() == "*":
                    logger.error(f"❌ Unsafe wildcard version found in requirements.txt: {line}")
                    has_error = True
    else:
        logger.warning("requirements.txt not found.")

    package_paths = [Path("package.json"), Path("apps/web/package.json")]
    pkg_path = package_paths[0]
    dependency_sections = (
        "dependencies",
        "devDependencies",
        "optionalDependencies",
        "peerDependencies",
    )
    for package_path in package_paths:
        if not package_path.exists():
            logger.warning("%s not found.", package_path)
            continue
        try:
            manifest = json.loads(package_path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("❌ Unable to parse %s: %s", package_path, exc)
            has_error = True
            continue
        for section in dependency_sections:
            dependencies = manifest.get(section, {})
            if not isinstance(dependencies, dict):
                logger.error("❌ %s.%s must be an object.", package_path, section)
                has_error = True
                continue
            for dependency, version in dependencies.items():
                if isinstance(version, str) and version.strip() == "*":
                    logger.error(
                        "❌ Unsafe wildcard version for %s in %s: %s",
                        dependency,
                        package_path,
                        version,
                    )
                    has_error = True

    # 2. Dynamic check via safety/npm-audit if available
    try:
        # Check safety (Python)
        if subprocess.run(["which", "safety"], capture_output=True).returncode == 0:
            logger.info("Running dynamic dependency safety scan (safety check)...")
            res = subprocess.run(["safety", "check", "-r", "requirements.txt"], capture_output=True, text=True)
            if res.returncode != 0:
                logger.error(f"❌ Safety check found dependency vulnerabilities:\n{res.stdout or res.stderr}")
                has_error = True
        else:
            logger.info("safety is not installed; skipping dynamic Python dependency scan.")
    except Exception as e:
        logger.warning(f"Failed to run safety check: {e}")

    try:
        # Check npm audit (Node)
        if subprocess.run(["which", "npm"], capture_output=True).returncode == 0 and pkg_path.exists():
            logger.info("Running dynamic dependency security scan (npm audit)...")
            res = subprocess.run(
                ["npm", "audit", "--audit-level=high"],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                logger.error(
                    "❌ npm audit found high/critical vulnerabilities or could not complete:\n"
                    f"{res.stdout or res.stderr}"
                )
                has_error = True
        else:
            logger.info("npm is not available or package.json missing; skipping dynamic Node dependency scan.")
    except Exception as e:
        logger.warning(f"Failed to run npm audit: {e}")

    if has_error:
        logger.error("❌ Dependency safety check failed.")
        return True

    logger.info("✅ Dependency safety checks passed.")
    return False


def main():
    errors = [check_cors(), check_headers(), check_logging(), check_dependencies(), check_env_vars()]
    if any(errors):
        logger.error("❌ Audit FAILED.")
        sys.exit(1)
    logger.info("✅ Audit PASSED.")


if __name__ == "__main__":
    main()
