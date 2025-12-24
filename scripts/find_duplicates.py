#!/usr/bin/env python3
"""
Find Duplicate Files and Unused Code
===================================

Analyzes the codebase for:
- Duplicate files (by content hash)
- Similar files (by name pattern)
- Unused imports
- Dead code
"""

import os
import hashlib
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple
import ast
import json

class DuplicateFinder:
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.file_hashes = defaultdict(list)
        self.similar_names = defaultdict(list)
        self.imports_map = {}
        self.unused_files = []
        self.report = {
            "duplicate_files": {},
            "similar_names": {},
            "unused_imports": {},
            "potentially_unused_files": [],
            "redundant_scripts": []
        }
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file content"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None
            
    def find_duplicate_files(self):
        """Find files with identical content"""
        ignore_patterns = [
            "__pycache__", ".git", ".venv", "venv", "node_modules",
            "archived_dev_artifacts", ".pytest_cache", "htmlcov"
        ]
        
        for file_path in self.base_path.rglob("*"):
            if file_path.is_file():
                # Skip ignored directories
                if any(pattern in str(file_path) for pattern in ignore_patterns):
                    continue
                    
                # Skip binary files
                if file_path.suffix in ['.pyc', '.png', '.jpg', '.jpeg', '.ico', '.db']:
                    continue
                    
                hash_val = self.calculate_file_hash(file_path)
                if hash_val:
                    self.file_hashes[hash_val].append(str(file_path))
                    
        # Find duplicates
        for hash_val, files in self.file_hashes.items():
            if len(files) > 1:
                self.report["duplicate_files"][hash_val] = files
                
    def find_similar_names(self):
        """Find files with similar names that might be duplicates"""
        name_patterns = defaultdict(list)
        
        for file_path in self.base_path.rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
                
            base_name = file_path.stem
            # Remove common suffixes
            cleaned_name = re.sub(r'(_test|_old|_backup|_copy|_v\d+|_\d+)$', '', base_name)
            name_patterns[cleaned_name].append(str(file_path))
            
        for pattern, files in name_patterns.items():
            if len(files) > 1:
                self.report["similar_names"][pattern] = files
                
    def analyze_imports(self):
        """Analyze Python imports to find unused modules"""
        python_files = list(self.base_path.rglob("*.py"))
        all_imports = set()
        all_from_imports = set()
        
        for file_path in python_files:
            if "__pycache__" in str(file_path):
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            all_imports.add(alias.name.split('.')[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            all_from_imports.add(node.module.split('.')[0])
            except:
                pass
                
        # Check which Python files are never imported
        for file_path in python_files:
            if file_path.stem == "__init__" or file_path.stem == "setup":
                continue
                
            module_name = file_path.stem
            relative_path = file_path.relative_to(self.base_path)
            
            # Check if this module is imported anywhere
            is_imported = (
                module_name in all_imports or
                module_name in all_from_imports or
                any(imp in str(relative_path) for imp in all_imports | all_from_imports)
            )
            
            # Check if it's a script or test
            is_script = (
                file_path.parent.name in ["scripts", "tests", "tools"] or
                module_name.startswith("test_") or
                module_name.endswith("_test") or
                module_name in ["main", "__main__"]
            )
            
            if not is_imported and not is_script:
                self.unused_files.append(str(relative_path))
                
        self.report["potentially_unused_files"] = self.unused_files
        
    def find_redundant_scripts(self):
        """Find scripts that might have overlapping functionality"""
        script_purposes = {
            "deploy": [],
            "test": [],
            "start": [],
            "build": [],
            "analyze": [],
            "process": [],
            "clean": [],
            "setup": []
        }
        
        for file_path in self.base_path.rglob("*"):
            if file_path.is_file() and (file_path.suffix in ['.py', '.sh', '.js']):
                name_lower = file_path.stem.lower()
                
                for purpose, files in script_purposes.items():
                    if purpose in name_lower:
                        files.append(str(file_path))
                        
        # Report redundant scripts
        for purpose, files in script_purposes.items():
            if len(files) > 1:
                self.report["redundant_scripts"].append({
                    "purpose": purpose,
                    "files": files,
                    "count": len(files)
                })
                
    def generate_report(self):
        """Generate comprehensive duplication report"""
        print("\n=== DUPLICATION ANALYSIS REPORT ===\n")
        
        # Duplicate files
        if self.report["duplicate_files"]:
            print(f"Found {len(self.report['duplicate_files'])} sets of duplicate files:")
            for i, (hash_val, files) in enumerate(self.report["duplicate_files"].items()):
                print(f"\nDuplicate Set {i+1}:")
                for file in files:
                    size = os.path.getsize(file) / 1024
                    print(f"  - {file} ({size:.1f} KB)")
                    
        # Similar names
        if self.report["similar_names"]:
            print(f"\n\nFound {len(self.report['similar_names'])} groups of similarly named files:")
            for pattern, files in self.report["similar_names"].items():
                print(f"\nPattern: {pattern}")
                for file in files:
                    print(f"  - {file}")
                    
        # Unused files
        if self.report["potentially_unused_files"]:
            print(f"\n\nFound {len(self.report['potentially_unused_files'])} potentially unused Python files:")
            for file in self.report["potentially_unused_files"]:
                print(f"  - {file}")
                
        # Redundant scripts
        if self.report["redundant_scripts"]:
            print("\n\nFound redundant scripts by purpose:")
            for group in self.report["redundant_scripts"]:
                print(f"\n{group['purpose'].upper()} scripts ({group['count']} files):")
                for file in group['files']:
                    print(f"  - {file}")
                    
        # Save JSON report
        report_path = self.base_path / "DUPLICATION_REPORT.json"
        with open(report_path, 'w') as f:
            json.dump(self.report, f, indent=2)
            
        print(f"\n\nDetailed report saved to: {report_path}")
        
        # Calculate potential space savings
        total_duplicate_size = 0
        for files in self.report["duplicate_files"].values():
            for file in files[1:]:  # Skip first file in each set
                try:
                    total_duplicate_size += os.path.getsize(file)
                except:
                    pass
                    
        print(f"\nPotential space savings from removing duplicates: {total_duplicate_size / (1024*1024):.2f} MB")
        
    def run(self):
        """Run all analyses"""
        print("Starting duplication analysis...")
        
        self.find_duplicate_files()
        self.find_similar_names()
        self.analyze_imports()
        self.find_redundant_scripts()
        self.generate_report()
        

if __name__ == "__main__":
    finder = DuplicateFinder()
    finder.run()
