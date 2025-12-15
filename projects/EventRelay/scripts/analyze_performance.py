#!/usr/bin/env python3
"""
Performance Analysis Script for EventRelay
==========================================

Automatically detects common performance anti-patterns and bottlenecks in the codebase.
Provides actionable recommendations for improvements.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Any, Set
from collections import defaultdict
import json

class PerformanceAnalyzer(ast.NodeVisitor):
    """AST visitor to detect performance anti-patterns"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.issues: List[Dict[str, Any]] = []
        self.in_async_function = False
        self.imports: Set[str] = set()
        
    def visit_Import(self, node: ast.Import):
        """Track imports"""
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports"""
        if node.module:
            self.imports.add(node.module)
            for alias in node.names:
                self.imports.add(f"{node.module}.{alias.name}")
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track when we're in an async function"""
        was_async = self.in_async_function
        self.in_async_function = True
        self.generic_visit(node)
        self.in_async_function = was_async
    
    def visit_Call(self, node: ast.Call):
        """Detect problematic function calls"""
        
        # Check for time.sleep in async context
        if self.in_async_function:
            if isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Name) and 
                    node.func.value.id == 'time' and 
                    node.func.attr == 'sleep'):
                    self.issues.append({
                        'severity': 'critical',
                        'type': 'blocking_sleep_in_async',
                        'line': node.lineno,
                        'message': 'time.sleep() blocks event loop in async function',
                        'recommendation': 'Replace with await asyncio.sleep()'
                    })
            
            # Check for synchronous requests in async function
            if isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Name) and 
                    node.func.value.id == 'requests'):
                    self.issues.append({
                        'severity': 'critical',
                        'type': 'sync_http_in_async',
                        'line': node.lineno,
                        'message': f'Synchronous requests.{node.func.attr}() in async function',
                        'recommendation': 'Replace with httpx AsyncClient'
                    })
            
            # Check for synchronous open() in async function
            if isinstance(node.func, ast.Name) and node.func.id == 'open':
                # Check if it's not already wrapped in aiofiles context
                self.issues.append({
                    'severity': 'high',
                    'type': 'sync_file_io_in_async',
                    'line': node.lineno,
                    'message': 'Synchronous file I/O in async function',
                    'recommendation': 'Use aiofiles for async file operations'
                })
        
        # Check for repeated regex compilation
        if isinstance(node.func, ast.Attribute):
            if (isinstance(node.func.value, ast.Name) and 
                node.func.value.id == 're' and 
                node.func.attr in ('compile', 'search', 'match', 'findall')):
                # This is a heuristic - we'd need more context to be sure
                if node.func.attr != 'compile':
                    self.issues.append({
                        'severity': 'medium',
                        'type': 'repeated_regex',
                        'line': node.lineno,
                        'message': 'Regex pattern may be compiled repeatedly',
                        'recommendation': 'Pre-compile patterns at module level'
                    })
        
        self.generic_visit(node)
    
    def visit_For(self, node: ast.For):
        """Detect inefficient loops"""
        
        # Check for nested loops (potential N+1)
        if self._is_nested_loop(node):
            self.issues.append({
                'severity': 'medium',
                'type': 'nested_loops',
                'line': node.lineno,
                'message': 'Nested loop detected - potential O(n²) complexity',
                'recommendation': 'Consider using dict/set for O(1) lookups or list comprehension'
            })
        
        self.generic_visit(node)
    
    def _is_nested_loop(self, node: ast.For) -> bool:
        """Check if this is a nested loop"""
        for child in ast.walk(node):
            if isinstance(child, (ast.For, ast.While)) and child != node:
                return True
        return False


def analyze_file(filepath: Path) -> Dict[str, Any]:
    """Analyze a single Python file for performance issues"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = PerformanceAnalyzer(str(filepath))
        analyzer.visit(tree)
        
        # Additional regex-based checks for patterns AST can't catch
        
        # Check file size
        file_size = len(content)
        if file_size > 100_000:  # 100KB
            analyzer.issues.append({
                'severity': 'medium',
                'type': 'large_file',
                'line': 0,
                'message': f'Large file ({file_size // 1024}KB) - consider splitting',
                'recommendation': 'Refactor into smaller, focused modules'
            })
        
        # Check for string formatting in log statements
        log_pattern = re.compile(r'logger\.\w+\(f["\']')
        for i, line in enumerate(content.split('\n'), 1):
            if log_pattern.search(line) and 'debug' in line.lower():
                analyzer.issues.append({
                    'severity': 'low',
                    'type': 'expensive_logging',
                    'line': i,
                    'message': 'F-string in log statement always evaluated',
                    'recommendation': 'Use lazy evaluation: logger.debug("msg %s", value)'
                })
        
        # Check for missing connection pooling indicators
        if 'requests.' in content and 'Session' not in content:
            analyzer.issues.append({
                'severity': 'medium',
                'type': 'no_connection_pooling',
                'line': 0,
                'message': 'Using requests without Session (no connection pooling)',
                'recommendation': 'Use requests.Session() for connection reuse'
            })
        
        return {
            'file': str(filepath.relative_to(Path.cwd())),
            'issues': analyzer.issues,
            'imports': list(analyzer.imports)
        }
    
    except Exception as e:
        return {
            'file': str(filepath.relative_to(Path.cwd())),
            'error': str(e),
            'issues': []
        }


def analyze_codebase(root_dir: Path = None) -> Dict[str, Any]:
    """Analyze entire codebase for performance issues"""
    
    if root_dir is None:
        root_dir = Path.cwd()
    
    src_dir = root_dir / 'src'
    if not src_dir.exists():
        print(f"Warning: {src_dir} not found")
        return {'error': 'src directory not found'}
    
    results = {
        'summary': {
            'total_files': 0,
            'files_with_issues': 0,
            'critical_issues': 0,
            'high_issues': 0,
            'medium_issues': 0,
            'low_issues': 0
        },
        'files': [],
        'issues_by_severity': defaultdict(list),
        'issues_by_type': defaultdict(int)
    }
    
    # Find all Python files
    python_files = list(src_dir.rglob('*.py'))
    
    print(f"Analyzing {len(python_files)} Python files...")
    
    for filepath in python_files:
        # Skip test files and migrations
        if 'test' in str(filepath) or 'migration' in str(filepath):
            continue
        
        file_result = analyze_file(filepath)
        
        if file_result.get('error'):
            print(f"Error analyzing {filepath}: {file_result['error']}")
            continue
        
        results['summary']['total_files'] += 1
        
        if file_result['issues']:
            results['summary']['files_with_issues'] += 1
            results['files'].append(file_result)
            
            for issue in file_result['issues']:
                severity = issue['severity']
                issue_type = issue['type']
                
                # Count by severity
                results['summary'][f'{severity}_issues'] += 1
                
                # Group by severity
                results['issues_by_severity'][severity].append({
                    'file': file_result['file'],
                    'line': issue['line'],
                    'type': issue_type,
                    'message': issue['message']
                })
                
                # Count by type
                results['issues_by_type'][issue_type] += 1
    
    return results


def generate_report(results: Dict[str, Any]) -> str:
    """Generate a human-readable report"""
    
    report = []
    report.append("=" * 80)
    report.append("EVENTRELAY PERFORMANCE ANALYSIS REPORT")
    report.append("=" * 80)
    report.append("")
    
    summary = results['summary']
    report.append("SUMMARY")
    report.append("-" * 80)
    report.append(f"Total files analyzed: {summary['total_files']}")
    report.append(f"Files with issues: {summary['files_with_issues']}")
    report.append("")
    report.append(f"Critical issues: {summary['critical_issues']}")
    report.append(f"High priority issues: {summary['high_issues']}")
    report.append(f"Medium priority issues: {summary['medium_issues']}")
    report.append(f"Low priority issues: {summary['low_issues']}")
    report.append("")
    
    # Issues by type
    if results['issues_by_type']:
        report.append("ISSUES BY TYPE")
        report.append("-" * 80)
        for issue_type, count in sorted(
            results['issues_by_type'].items(), 
            key=lambda x: x[1], 
            reverse=True
        ):
            report.append(f"  {issue_type}: {count}")
        report.append("")
    
    # Critical issues
    if results['issues_by_severity']['critical']:
        report.append("CRITICAL ISSUES (IMMEDIATE ACTION REQUIRED)")
        report.append("-" * 80)
        for issue in results['issues_by_severity']['critical']:
            report.append(f"  📛 {issue['file']}:{issue['line']}")
            report.append(f"     {issue['message']}")
        report.append("")
    
    # High priority issues
    if results['issues_by_severity']['high']:
        report.append("HIGH PRIORITY ISSUES")
        report.append("-" * 80)
        for issue in results['issues_by_severity']['high'][:10]:  # Top 10
            report.append(f"  ⚠️  {issue['file']}:{issue['line']}")
            report.append(f"     {issue['message']}")
        if len(results['issues_by_severity']['high']) > 10:
            report.append(f"  ... and {len(results['issues_by_severity']['high']) - 10} more")
        report.append("")
    
    # Recommendations
    report.append("TOP RECOMMENDATIONS")
    report.append("-" * 80)
    
    if results['issues_by_type'].get('blocking_sleep_in_async', 0) > 0:
        report.append("1. Replace time.sleep() with await asyncio.sleep() in async functions")
        report.append("   Impact: Critical - prevents event loop blocking")
        report.append("")
    
    if results['issues_by_type'].get('sync_http_in_async', 0) > 0:
        report.append("2. Replace requests library with httpx AsyncClient for async HTTP")
        report.append("   Impact: Critical - enables concurrent request processing")
        report.append("")
    
    if results['issues_by_type'].get('sync_file_io_in_async', 0) > 0:
        report.append("3. Use aiofiles for async file I/O operations")
        report.append("   Impact: High - improves file operation throughput")
        report.append("")
    
    if results['issues_by_type'].get('no_connection_pooling', 0) > 0:
        report.append("4. Implement connection pooling for HTTP clients")
        report.append("   Impact: Medium - reduces connection overhead")
        report.append("")
    
    report.append("=" * 80)
    
    return "\n".join(report)


def main():
    """Main entry point"""
    
    print("Starting performance analysis...\n")
    
    root_dir = Path(__file__).parent.parent
    results = analyze_codebase(root_dir)
    
    if results.get('error'):
        print(f"Error: {results['error']}")
        return
    
    # Generate and print report
    report = generate_report(results)
    print(report)
    
    # Save detailed results to JSON
    output_file = root_dir / 'performance_analysis_results.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
    
    # Exit code based on severity
    if results['summary']['critical_issues'] > 0:
        print("\n⚠️  Critical issues found! Immediate action recommended.")
        return 1
    elif results['summary']['high_issues'] > 0:
        print("\n⚠️  High priority issues found. Action recommended.")
        return 0
    else:
        print("\n✅ No critical performance issues found.")
        return 0


if __name__ == '__main__':
    exit(main())
