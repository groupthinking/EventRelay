#!/usr/bin/env python3
"""
Test Infrastructure Packaging Integration with Generated Project
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from agents.packaging_agent import InfrastructurePackagingAgent


async def read_generated_project(project_dir):
    """Read generated project structure"""
    project_path = Path(project_dir)
    
    if not project_path.exists():
        raise FileNotFoundError(f"Project not found: {project_dir}")
    
    project_structure = {}
    flat_files = {}
    
    # Read all files
    for file_path in project_path.rglob('*'):
        if file_path.is_file():
            try:
                relative_path = file_path.relative_to(project_path)
                
                # Skip certain directories
                if any(part in str(relative_path) for part in ['node_modules', '.git', '.next', 'dist']):
                    continue
                
                content = file_path.read_text()
                
                # Organize into nested structure or flat files
                parts = list(relative_path.parts)
                if len(parts) == 1:
                    # Flat file
                    flat_files[parts[0]] = content
                else:
                    # Nested file
                    folder = '/'.join(parts[:-1]) + '/'
                    filename = parts[-1]
                    
                    if folder not in project_structure:
                        project_structure[folder] = {}
                    
                    project_structure[folder][filename] = content
                    
            except Exception as e:
                print(f"⚠️  Skipping {file_path}: {e}")
    
    return project_structure, flat_files


async def main():
    # Find most recent generated project
    generated_dir = Path('generated_projects')
    
    if not generated_dir.exists():
        print("❌ No generated_projects directory found")
        return
    
    projects = sorted(generated_dir.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not projects:
        print("❌ No generated projects found")
        return
    
    latest_project = projects[0]
    print(f"📂 Testing with: {latest_project.name}")
    
    # Read project structure
    print("\n📖 Reading project structure...")
    project_structure, flat_files = await read_generated_project(latest_project)
    
    print(f"   Folders: {len(project_structure)}")
    print(f"   Flat files: {len(flat_files)}")
    print(f"   Total files: {sum(len(files) for files in project_structure.values()) + len(flat_files)}")
    
    # Initialize packaging agent
    print("\n🤖 Initializing packaging agent...")
    agent = InfrastructurePackagingAgent()
    
    # Package and validate
    print("\n🔒 Running security validation...")
    trigger_data = {
        'project_name': latest_project.name[:50],  # Limit length
        'project_structure': project_structure,
        'flat_files': flat_files,
        'triggered_by': 'EventRelay_Integration_Test',
        'deployment_target': 'production'
    }
    
    result = await agent.agent_triggered_packaging(trigger_data)
    
    # Display results
    print("\n" + "="*70)
    print("PACKAGING RESULTS")
    print("="*70)
    
    if result['success']:
        print(f"✅ Status: SUCCESS")
        print(f"📦 ZIP: {result['zip_path']}")
        print(f"📊 Report: {result['validation_report']}")
        
        # Read validation report
        with open(result['validation_report']) as f:
            report = json.load(f)
        
        print(f"\n📋 Validation Summary:")
        print(f"   Total Files: {report['total_files']}")
        print(f"   Passed: {report['passed_validation']}")
        print(f"   Failed: {report['failed_validation']}")
        print(f"   Score: {report['validation_score']:.1f}%")
        
        if report['security_issues']:
            print(f"\n⚠️  Security Issues ({len(report['security_issues'])}):")
            for issue in report['security_issues'][:5]:  # Show first 5
                print(f"   • {Path(issue['file']).name}: {len(issue['issues'])} issues")
        
    else:
        print(f"❌ Status: FAILED")
        print(f"   Error: {result['error']}")
    
    return result


if __name__ == "__main__":
    asyncio.run(main())
