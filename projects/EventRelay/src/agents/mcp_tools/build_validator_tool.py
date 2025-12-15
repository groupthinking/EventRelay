#!/usr/bin/env python3
"""
Build Validator MCP Tool - Validates and fixes generated projects
Runs npm build and uses Gemini to fix errors
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import json

logger = logging.getLogger(__name__)

# Import Gemini SDK for error fixing
try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-genai SDK not available - AI error fixing disabled")


class BuildValidatorMCPTool:
    """
    MCP-compatible wrapper for build validation.
    Validates generated projects can build successfully and fixes errors.
    """

    def __init__(self):
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.client = None

        if GENAI_AVAILABLE and self.gemini_api_key:
            self.client = genai.Client(api_key=self.gemini_api_key)
            logger.info("✅ Build Validator initialized with Gemini")
        else:
            logger.warning("⚠️  Build Validator running without AI error fixing")

    async def close(self):
        """Clean up resources"""
        pass

    async def validate_build(
        self,
        project_path: str,
        max_fix_attempts: int = 3
    ) -> Dict[str, Any]:
        """
        Validate that a generated project can build successfully.

        MCP Tool: validate_build

        Args:
            project_path: Path to generated project
            max_fix_attempts: Maximum number of auto-fix attempts

        Returns:
            Dict with build_status, errors, fixes_applied
        """
        try:
            logger.info(f"🔨 Validating build: {project_path}")

            project_dir = Path(project_path)
            if not project_dir.exists():
                return {
                    "status": "error",
                    "error": f"Project path does not exist: {project_path}"
                }

            # Check for package.json
            package_json = project_dir / "package.json"
            if not package_json.exists():
                return {
                    "status": "error",
                    "error": "No package.json found - not a Node.js project"
                }

            results = {
                "status": "in_progress",
                "project_path": str(project_path),
                "install_success": False,
                "build_success": False,
                "errors": [],
                "fixes_applied": [],
                "attempts": 0
            }

            # Attempt build with auto-fix
            for attempt in range(max_fix_attempts):
                results["attempts"] = attempt + 1
                logger.info(f"Build attempt {attempt + 1}/{max_fix_attempts}")

                # Step 1: npm install
                install_result = await self._run_npm_install(project_dir)
                results["install_success"] = install_result["success"]

                if not install_result["success"]:
                    results["errors"].append({
                        "stage": "install",
                        "message": install_result["error"]
                    })

                    # Try to fix install errors
                    if self.client and attempt < max_fix_attempts - 1:
                        fix = await self._fix_errors(
                            project_dir,
                            "npm install",
                            install_result["error"]
                        )
                        if fix["success"]:
                            results["fixes_applied"].append(fix)
                            continue

                    results["status"] = "failed"
                    return results

                # Step 2: npm run build
                build_result = await self._run_npm_build(project_dir)
                results["build_success"] = build_result["success"]

                if build_result["success"]:
                    results["status"] = "success"
                    results["build_time"] = build_result.get("duration", "unknown")
                    logger.info(f"✅ Build successful on attempt {attempt + 1}")
                    return results

                # Build failed - collect errors
                results["errors"].append({
                    "stage": "build",
                    "message": build_result["error"]
                })

                # Try to fix build errors
                if self.client and attempt < max_fix_attempts - 1:
                    logger.info(f"Attempting to fix build errors...")
                    fix = await self._fix_errors(
                        project_dir,
                        "npm run build",
                        build_result["error"]
                    )
                    if fix["success"]:
                        results["fixes_applied"].append(fix)
                    else:
                        # Can't fix, give up
                        break

            # All attempts exhausted
            results["status"] = "failed"
            logger.warning(f"Build failed after {max_fix_attempts} attempts")
            return results

        except Exception as e:
            logger.error(f"Build validation error: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e),
                "project_path": project_path
            }

    async def _run_npm_install(self, project_dir: Path) -> Dict[str, Any]:
        """Run npm install"""
        try:
            logger.info(f"Running npm install in {project_dir}")

            # SECURITY: subprocess call uses hardcoded command list.
            # project_dir is used as cwd, ensure it is a valid path.
            if not project_dir.exists() or not project_dir.is_dir():
                return {"success": False, "error": "Invalid project directory"}

            result = subprocess.run(
                ["npm", "install"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes
            )

            if result.returncode == 0:
                return {"success": True}
            else:
                error_msg = result.stderr or result.stdout
                return {
                    "success": False,
                    "error": error_msg[-2000:]  # Last 2000 chars
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "npm install timed out (>3min)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_npm_build(self, project_dir: Path) -> Dict[str, Any]:
        """Run npm run build"""
        try:
            import time
            logger.info(f"Running npm run build in {project_dir}")

            # SECURITY: subprocess call uses hardcoded command list.
            # project_dir is used as cwd, ensure it is a valid path.
            if not project_dir.exists() or not project_dir.is_dir():
                return {"success": False, "error": "Invalid project directory"}

            start_time = time.time()
            result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes
            )
            duration = time.time() - start_time

            if result.returncode == 0:
                return {
                    "success": True,
                    "duration": f"{duration:.1f}s"
                }
            else:
                error_msg = result.stderr or result.stdout
                return {
                    "success": False,
                    "error": error_msg[-3000:]  # Last 3000 chars
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "npm build timed out (>5min)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _fix_errors(
        self,
        project_dir: Path,
        command: str,
        error_output: str
    ) -> Dict[str, Any]:
        """
        Use Gemini to analyze and fix build errors.

        Args:
            project_dir: Project directory
            command: Command that failed
            error_output: Error output from command

        Returns:
            Dict with success status and fixes applied
        """
        if not self.client:
            return {"success": False, "error": "No Gemini client available"}

        try:
            logger.info("🤖 Using Gemini to fix build errors...")

            # Read key project files for context
            context_files = {}
            for filename in ["package.json", "tsconfig.json", "next.config.js"]:
                file_path = project_dir / filename
                if file_path.exists():
                    context_files[filename] = file_path.read_text()

            fix_prompt = f"""You are a senior full-stack developer fixing build errors.

COMMAND THAT FAILED: {command}

ERROR OUTPUT:
{error_output}

PROJECT FILES:
{json.dumps(context_files, indent=2)}

Analyze the error and provide a specific fix. Return ONLY valid JSON:
{{
    "diagnosis": "brief explanation of the issue",
    "fixes": [
        {{
            "file": "path/to/file.ext",
            "action": "modify" | "create" | "delete",
            "content": "full file content if modify/create"
        }}
    ]
}}

Focus on common issues:
- Missing dependencies in package.json
- TypeScript config errors
- Import path issues
- Next.js config issues
"""

            response = self.client.models.generate_content(
                model='gemini-3-pro-preview',
                contents=fix_prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=1.0,
                    max_output_tokens=4096
                )
            )

            # Handle Gemini 3's thought_signature responses
            response_text = response.text
            if response_text is None:
                # Try extracting from parts directly
                if response.candidates and response.candidates[0].content.parts:
                    text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, 'text') and p.text]
                    response_text = "\n".join(text_parts) if text_parts else None

            if response_text is None:
                return {"success": False, "error": "No text response from Gemini"}

            # Extract JSON from potential markdown fences
            text = response_text
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]

            fix_data = json.loads(text.strip())

            # Apply fixes
            fixes_applied = []
            for fix in fix_data.get("fixes", []):
                file_path = project_dir / fix["file"]
                action = fix["action"]

                if action == "modify" or action == "create":
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(fix["content"])
                    fixes_applied.append(f"{action}: {fix['file']}")
                elif action == "delete":
                    if file_path.exists():
                        file_path.unlink()
                        fixes_applied.append(f"delete: {fix['file']}")

            logger.info(f"✅ Applied {len(fixes_applied)} fixes")

            return {
                "success": True,
                "diagnosis": fix_data.get("diagnosis", ""),
                "fixes_applied": fixes_applied
            }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return {"success": False, "error": "Invalid JSON from Gemini"}
        except Exception as e:
            logger.error(f"Error fixing build: {e}")
            return {"success": False, "error": str(e)}


# Singleton instance
_tool = None

def get_build_validator_tool() -> BuildValidatorMCPTool:
    """Get or create Build Validator MCP Tool singleton"""
    global _tool
    if _tool is None:
        _tool = BuildValidatorMCPTool()
    return _tool

# MCP Tool registry for agent network
MCP_TOOLS = {
    "validate_build": get_build_validator_tool().validate_build
}
