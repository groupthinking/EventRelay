#!/usr/bin/env python3
"""
Phase 1.3: Create Import Mapping
Builds a dependency map for internal imports in the youtube_extension package
"""

import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List

class ImportMapper:
    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.import_map: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_map: Dict[str, Set[str]] = defaultdict(set)
        self.module_files: Dict[str, str] = {}

    def build_import_map(self) -> Dict[str, Dict]:
        """Build comprehensive import mapping"""
        # Focus on core directories to avoid the massive file count
        core_patterns = [
            "*.py",  # Root level Python files
            "backend/*.py",  # Backend files
            "agents/*.py",  # Agent files
            "intelligence_layer/*.py",  # Intelligence layer
            "factory/*.py",  # Factory files
            "tools/*.py",  # Tools
            "scripts/*.py",  # Scripts
        ]

        python_files = []
        for pattern in core_patterns:
            python_files.extend(list(self.root_path.glob(pattern)))

        # Remove duplicates and filter out venv files
        python_files = list(set(python_files))
        python_files = [f for f in python_files if not str(f).startswith(str(self.root_path / ".venv"))]

        print(f"Building import map for {len(python_files)} core Python files...")

        for file_path in python_files:
            self._analyze_file_imports(file_path)

        # Convert to regular dict for JSON serialization
        result = {
            "import_map": {k: list(v) for k, v in self.import_map.items()},
            "reverse_map": {k: list(v) for k, v in self.reverse_map.items()},
            "module_files": self.module_files
        }

        return result

    def _analyze_file_imports(self, file_path: Path):
        """Analyze imports in a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            return

        # Extract module name from file path
        rel_path = file_path.relative_to(self.root_path)
        module_name = self._path_to_module_name(rel_path)
        self.module_files[module_name] = str(rel_path)

        # Find all import statements
        import_lines = self._extract_import_lines(content)

        for line in import_lines:
            imported_modules = self._parse_import_line(line)
            for imported in imported_modules:
                if self._is_internal_import(imported):
                    self.import_map[module_name].add(imported)
                    self.reverse_map[imported].add(module_name)

    def _extract_import_lines(self, content: str) -> List[str]:
        """Extract all import lines from file content"""
        lines = content.split('\n')
        import_lines = []

        for line in lines:
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                import_lines.append(line)

        return import_lines

    def _parse_import_line(self, line: str) -> List[str]:
        """Parse an import line to extract module names"""
        modules = []

        try:
            if line.startswith('import '):
                # Handle multiple imports: import a, b, c
                parts = line[7:].split(',')
                for part in parts:
                    part = part.strip()
                    if part:
                        module_parts = part.split()
                        if module_parts:
                            module = module_parts[0]  # Remove 'as alias'
                            modules.append(module)
            elif line.startswith('from '):
                # Handle from imports: from module import something
                match = re.match(r'from (\S+)', line)
                if match:
                    module = match.group(1)
                    modules.append(module)
        except Exception:
            # Skip malformed import lines
            pass

        return modules

    def _is_internal_import(self, module: str) -> bool:
        """Check if an import is internal to the project"""
        # Check if it starts with youtube_extension or known internal modules
        internal_prefixes = [
            'youtube_extension',
            'backend',
            'agents',
            'intelligence_layer',
            'factory',
            'tools',
            'scripts'
        ]

        return any(module.startswith(prefix) for prefix in internal_prefixes)

    def _path_to_module_name(self, rel_path: Path) -> str:
        """Convert file path to module name"""
        path_str = str(rel_path)
        if path_str.endswith('.py'):
            path_str = path_str[:-3]  # Remove .py extension

        # Convert path separators to dots
        return path_str.replace('/', '.').replace('\\', '.')

    def generate_report(self, mapping_data: Dict) -> str:
        """Generate import mapping report"""
        report = "# Import Mapping Report - Phase 1.3\n\n"

        report += "## Summary\n"
        report += f"- Total modules analyzed: {len(mapping_data['module_files'])}\n"
        report += f"- Internal dependencies found: {len(mapping_data['import_map'])}\n\n"

        # Most imported modules
        all_imports = []
        for imports in mapping_data['import_map'].values():
            all_imports.extend(imports)

        import_counts = defaultdict(int)
        for imp in all_imports:
            import_counts[imp] += 1

        report += "## Most Imported Modules\n"
        sorted_imports = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)
        for module, count in sorted_imports[:10]:
            report += f"- {module}: imported by {count} modules\n"

        report += "\n## Modules with Most Dependencies\n"
        sorted_modules = sorted(mapping_data['import_map'].items(),
                               key=lambda x: len(x[1]), reverse=True)
        for module, deps in sorted_modules[:10]:
            report += f"- {module}: {len(deps)} dependencies\n"

        return report

def main():
    project_root = Path(__file__).resolve().parent.parent
    mapper = ImportMapper(str(project_root))
    mapping_data = mapper.build_import_map()

    report = mapper.generate_report(mapping_data)

    with open("PHASE1_IMPORT_MAPPING_REPORT.md", "w") as f:
        f.write(report)

    # Save the raw mapping data for later use
    import json
    with open("import_mapping.json", "w") as f:
        json.dump(mapping_data, f, indent=2)

    print(f"Import mapping complete!")
    print(f"- Analyzed {len(mapping_data['module_files'])} modules")
    print(f"- Found {len(mapping_data['import_map'])} modules with internal dependencies")
    print("Reports saved to PHASE1_IMPORT_MAPPING_REPORT.md and import_mapping.json")

    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
