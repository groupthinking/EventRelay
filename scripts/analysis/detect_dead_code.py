import os
import re
import ast
from pathlib import Path

# Configuration
IGNORE_DIRS = {
    "node_modules",
    "venv",
    "__pycache__",
    ".git",
    "dist",
    "build",
    "_archive",
    "site-packages",
    "ai-edge-torch",
    "examples",
    "tests",
}
IGNORE_FILES = {"__init__.py", "setup.py", "conftest.py", "manage.py"}
EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx"}


def get_all_files(root_dir):
    """Recursively yield all coding files."""
    for path in Path(root_dir).rglob("*"):
        if path.is_file():
            # Skip ignored dirs
            parts = path.parts
            if any(p in IGNORE_DIRS for p in parts):
                continue

            if path.suffix in EXTENSIONS and path.name not in IGNORE_FILES:
                yield path


def get_imports_from_file(file_path):
    """Parse a file to find what other modules/files it imports."""
    imports = set()
    content = ""
    try:
        content = file_path.read_text(errors="ignore")
    except:
        return imports

    # Python specific parsing
    if file_path.suffix == ".py":
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
        except SyntaxError:
            pass  # analyzing partial code

    # Generic Regex fallback for string references (works for JS/TS too)
    # Matches "from 'path'", "import 'path'", "require('path')"
    # And also looks for mentions of the filename stem in specific strings

    matches = re.findall(r'[\'"]([^\'"\s]+)[\'"]', content)
    for m in matches:
        # Simple heuristic: treat any string that looks like a path or module name as a ref
        if len(m) > 3:
            imports.add(os.path.basename(m).split(".")[0])

    return imports


def main():
    root = Path.cwd()
    print(f"Scanning {root} for dead code...")

    all_files = list(get_all_files(root))
    file_map = {f.name: f for f in all_files}  # simplistic map: filename -> path
    file_set = set(f.stem for f in all_files)  # verify against stems

    # Track references
    referenced_files = set()

    # Known entry points implicitly referenced
    entry_points = {"main", "app", "server", "manage", "wsgi", "asgi", "index"}

    for f in all_files:
        # If it's an entry point, mark it referenced
        if f.stem in entry_points:
            referenced_files.add(f.stem)
            continue

        imports = get_imports_from_file(f)
        for imp in imports:
            # If import matches a file stem, mark that file as referenced
            if imp in file_set:
                referenced_files.add(imp)

    # Calculate dead code
    dead_candidates = []
    for f in all_files:
        if f.stem not in referenced_files:
            dead_candidates.append(f)

    # Report
    print(f"Total files scanned: {len(all_files)}")
    print(f"Potentially unused files: {len(dead_candidates)}")

    with open("dead_code_report.md", "w") as report:
        report.write("# Dead Code Candidates\n\n")
        report.write(
            f"Scanned {len(all_files)} files. Found {len(dead_candidates)} candidates.\n"
        )
        report.write(
            "> Note: Heuristic analysis based on imports and string references. Always verify manually.\n\n"
        )

        for f in sorted(dead_candidates):
            report.write(f"- `{f.relative_to(root)}`\n")

    print("Report generated: dead_code_report.md")


if __name__ == "__main__":
    main()
