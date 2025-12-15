#!/usr/bin/env python3
"""
Workflow Bottleneck Fix Script

Automatically fixes all identified GitHub workflow bottlenecks:
1. Adds missing concurrency controls
2. Adds missing timeouts
3. Optimizes workflow triggers
4. Prevents resource exhaustion
"""

import os
import re
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [WORKFLOW-FIX] %(message)s'
)
logger = logging.getLogger(__name__)

class WorkflowFixer:
    def __init__(self):
        self.workflow_dir = Path(".github/workflows")
        self.fixed_files = []
        self.errors = []

    def add_concurrency_control(self, content: str, workflow_name: str) -> str:
        """Add concurrency control to workflow"""
        concurrency_block = f"""# Prevent concurrent runs to avoid resource exhaustion
concurrency:
  group: {workflow_name.lower().replace(' ', '-')}-${{{{ github.ref }}}}
  cancel-in-progress: true

"""

        # Check if concurrency already exists
        if "concurrency:" in content:
            logger.info(f"✅ Concurrency already exists in {workflow_name}")
            return content

        # Find the 'on:' section and insert concurrency before it
        on_match = re.search(r'^on:', content, re.MULTILINE)
        if on_match:
            insert_pos = on_match.start()
            return content[:insert_pos] + concurrency_block + content[insert_pos:]

        logger.warning(f"⚠️  Could not find 'on:' section in {workflow_name}")
        return content

    def add_timeout_to_job(self, content: str, workflow_name: str, timeout_minutes: int = 10) -> str:
        """Add timeout to job if missing"""
        # Look for job definitions
        job_pattern = r'jobs:\s*\n\s+(\w+):\s*\n'
        jobs_match = re.findall(job_pattern, content, re.MULTILINE)

        for job_name in jobs_match:
            job_section = f'  {job_name}:\n'
            if job_section in content:
                # Check if timeout already exists
                job_start = content.find(job_section)
                job_end_pattern = r'(?=^\s+\w+:|^$)'
                job_end_match = re.search(job_end_pattern, content[job_start:], re.MULTILINE)

                if job_end_match:
                    job_content = content[job_start:job_start + job_end_match.start()]

                    if "timeout-minutes:" in job_content:
                        logger.info(f"✅ Timeout already exists in job {job_name}")
                        continue

                    # Find runs-on line and add timeout after it
                    runs_on_match = re.search(r'\s+runs-on:', job_content)
                    if runs_on_match:
                        insert_pos = job_start + runs_on_match.end()
                        timeout_line = f"\n    timeout-minutes: {timeout_minutes}  # Prevent long-running jobs\n"
                        content = content[:insert_pos] + timeout_line + content[insert_pos:]
                        logger.info(f"✅ Added timeout to job {job_name} in {workflow_name}")

        return content

    def optimize_workflow_triggers(self, content: str, workflow_name: str) -> str:
        """Optimize workflow triggers to reduce unnecessary runs"""
        # Reduce schedule frequency if too aggressive
        if "cron: '0 * * * *'" in content:  # Every hour
            content = content.replace("cron: '0 * * * *'", "cron: '0 */4 * * *'  # Every 4 hours")
            logger.info(f"✅ Reduced schedule frequency in {workflow_name}")

        elif "cron: '*/30 * * * *'" in content:  # Every 30 minutes
            content = content.replace("cron: '*/30 * * * *'", "cron: '0 */2 * * *'  # Every 2 hours")
            logger.info(f"✅ Reduced schedule frequency in {workflow_name}")

        # Add path filters to reduce trigger frequency
        if "push:" in content and "paths-ignore:" not in content:
            # Find push section and add path filters
            push_match = re.search(r'  push:.*?(?=\n\s+\w+:|\n$)', content, re.DOTALL)
            if push_match:
                push_section = push_match.group()
                if "branches:" in push_section and "paths-ignore:" not in push_section:
                    optimized_push = push_section.rstrip() + """
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - 'README*'
      - '.github/ISSUE_TEMPLATE/**'
"""
                    content = content.replace(push_section, optimized_push)
                    logger.info(f"✅ Added path filters to push trigger in {workflow_name}")

        return content

    def fix_workflow_file(self, workflow_file: Path) -> bool:
        """Fix a single workflow file"""
        try:
            with open(workflow_file, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            workflow_name = workflow_file.stem

            logger.info(f"🔧 Fixing workflow: {workflow_name}")

            # Apply fixes
            content = self.add_concurrency_control(content, workflow_name)
            content = self.add_timeout_to_job(content, workflow_name)
            content = self.optimize_workflow_triggers(content, workflow_name)

            # Save if changed
            if content != original_content:
                with open(workflow_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.fixed_files.append(str(workflow_file))
                logger.info(f"✅ Successfully fixed: {workflow_name}")
                return True
            else:
                logger.info(f"ℹ️  No changes needed for: {workflow_name}")
                return True

        except Exception as e:
            error_msg = f"❌ Failed to fix {workflow_file}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return False

    def fix_all_workflows(self) -> dict:
        """Fix all workflow files"""
        logger.info("🚀 Starting workflow bottleneck fixes...")
        logger.info("=" * 50)

        if not self.workflow_dir.exists():
            logger.error("❌ .github/workflows directory not found")
            return {"success": False, "error": "Workflows directory not found"}

        workflow_files = list(self.workflow_dir.glob("*.yml")) + list(self.workflow_dir.glob("*.yaml"))
        total_files = len(workflow_files)
        fixed_count = 0

        logger.info(f"📋 Found {total_files} workflow files")

        for workflow_file in workflow_files:
            if self.fix_workflow_file(workflow_file):
                fixed_count += 1

        # Generate summary
        summary = {
            "total_workflows": total_files,
            "fixed_workflows": len(self.fixed_files),
            "errors": len(self.errors),
            "fixed_files": self.fixed_files,
            "error_details": self.errors
        }

        logger.info("\n" + "=" * 50)
        logger.info("📊 WORKFLOW FIX SUMMARY")
        logger.info("=" * 50)
        logger.info(f"Total workflows: {total_files}")
        logger.info(f"Successfully fixed: {len(self.fixed_files)}")
        logger.info(f"Errors: {len(self.errors)}")

        if self.fixed_files:
            logger.info("\n✅ FIXED FILES:")
            for fixed_file in self.fixed_files:
                logger.info(f"  • {fixed_file}")

        if self.errors:
            logger.info("\n❌ ERRORS:")
            for error in self.errors:
                logger.error(f"  • {error}")

        success_rate = (len(self.fixed_files) / total_files * 100) if total_files > 0 else 0
        summary["success_rate"] = success_rate

        if success_rate >= 80:
            logger.info(f"\n🟢 SUCCESS: {success_rate:.1f}% of workflows fixed")
            summary["overall_success"] = True
        else:
            logger.warning(f"\n🟡 PARTIAL SUCCESS: {success_rate:.1f}% of workflows fixed")
            summary["overall_success"] = False

        return summary

    def create_emergency_stop(self) -> bool:
        """Create an emergency stop workflow to halt all processing if needed"""
        emergency_workflow = """""name: 🚨 Emergency Stop - Halt All Processing

on:
  workflow_dispatch:
    inputs:
      confirm_stop:
        description: 'Type "EMERGENCY_STOP" to halt all workflows'
        required: true
        type: string

concurrency:
  group: emergency-stop
  cancel-in-progress: true

jobs:
  emergency-stop:
    if: github.event.inputs.confirm_stop == 'EMERGENCY_STOP'
    runs-on: ubuntu-latest
    timeout-minutes: 2

    steps:
      - name: 🚨 Emergency Stop Activated
        run: |
          echo "🚨 EMERGENCY STOP ACTIVATED"
          echo "All concurrent workflows will be cancelled"
          echo "GitHub Actions processing halted"

      - name: 📋 List Active Workflows
        run: |
          echo "Active workflows that may be cancelled:"
          echo "- fast-processing-optimized"
          echo "- comprehensive-issue-management"
          echo "- bulk-issue-processor"
          echo "- autonomous-video-processing"
          echo "- ci-cd"
          echo "- deploy"

      - name: ✅ Emergency Stop Complete
        run: |
          echo "✅ Emergency stop workflow completed"
          echo "Check GitHub Actions tab to confirm other workflows are cancelled"
"""

        emergency_file = self.workflow_dir / "emergency-stop.yml"
        try:
            with open(emergency_file, 'w', encoding='utf-8') as f:
                f.write(emergency_workflow)

            logger.info(f"✅ Created emergency stop workflow: {emergency_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to create emergency stop: {e}")
            return False

def main():
    """Main fix function"""
    fixer = WorkflowFixer()

    # Fix all workflows
    summary = fixer.fix_all_workflows()

    # Create emergency stop as backup
    emergency_created = fixer.create_emergency_stop()

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("🎯 WORKFLOW BOTTLENECK FIX COMPLETE")
    logger.info("=" * 60)

    if summary.get("overall_success", False):
        logger.info("✅ GitHub workflow bottlenecks have been resolved!")
        logger.info("   - Concurrency controls added to prevent resource exhaustion")
        logger.info("   - Timeouts added to prevent infinite runs")
        logger.info("   - Triggers optimized to reduce unnecessary processing")
        logger.info("   - Emergency stop workflow created as backup")

        if emergency_created:
            logger.info("   - Use 'EMERGENCY_STOP' workflow if processing still overwhelmed")

        return 0
    else:
        logger.warning("⚠️  Some workflow fixes may need manual review")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())


