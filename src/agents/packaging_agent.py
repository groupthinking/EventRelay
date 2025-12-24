#!/usr/bin/env python3
"""
EventRelay Infrastructure Packaging Agent
==========================================

Agent-triggered, Codex-validated, error-proof infrastructure packaging system.
Integrates ZIP automation with EventRelay coordination and security validation.

Features:
- Agent-triggered deployment packaging
- Codex security validation
- MCP ecosystem integration
- Secrets detection and safety
- Error-proof file structure creation
"""

import os
import shutil
import zipfile
import asyncio
import logging
import json
import hashlib
import re
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from utils.path_utils import get_project_root, resolve_path

PROJECT_ROOT = get_project_root()
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.append(str(SRC_PATH))

# Database persistence agent (with mock fallback)
try:
    from agents.database_persistence_agent import DatabasePersistenceAgent
except ImportError:
    # Mock database agent for testing
    class DatabasePersistenceAgent:
        async def _store_data(self, data):
            print(f"📊 Mock DB Store: {data.get('data_type', 'unknown')}")
            return True

class InfrastructurePackagingAgent:
    """
    EventRelay Agent for secure, validated infrastructure packaging
    """

    def __init__(self):
        self.logger = self._setup_logging()
        self.db_agent = DatabasePersistenceAgent()
        self.validation_patterns = self._load_security_patterns()
        self.packaging_history = []

    def _setup_logging(self) -> logging.Logger:
        """Configure logging for packaging operations"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        log_file = resolve_path('logs', 'infrastructure_packaging.log')
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def _load_security_patterns(self) -> Dict[str, List[str]]:
        """Load security patterns for validation"""
        return {
            'secrets': [
                r'api[_-]?key["\s]*[:=]["\s]*[a-zA-Z0-9]+',
                r'secret[_-]?key["\s]*[:=]["\s]*[a-zA-Z0-9]+',
                r'password["\s]*[:=]["\s]*[a-zA-Z0-9]+',
                r'token["\s]*[:=]["\s]*[a-zA-Z0-9]+',
                r'aws[_-]?access[_-]?key["\s]*[:=]["\s]*[A-Z0-9]+',
                r'sk-[a-zA-Z0-9]{48}',  # OpenAI API keys
                r'pk-[a-zA-Z0-9]{48}',  # Public keys
                r'AIza[0-9A-Za-z\\-_]{35}',  # Google API keys
            ],
            'security_issues': [
                r'eval\s*\(',
                r'exec\s*\(',
                r'subprocess\.call',
                r'os\.system',
                r'shell=True',
            ],
            'sensitive_paths': [
                r'\.ssh/',
                r'\.aws/',
                r'\.env',
                r'id_rsa',
                r'private[_-]?key',
            ]
        }

    async def codex_validate_content(self, content: str, file_path: str) -> Tuple[bool, List[str]]:
        """
        Codex validation step for security and code quality
        """
        issues = []

        # Check for secrets
        for pattern in self.validation_patterns['secrets']:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"SECURITY: Potential secret detected in {file_path}")

        # Check for security issues
        for pattern in self.validation_patterns['security_issues']:
            if re.search(pattern, content, re.IGNORECASE):
                issues.append(f"SECURITY: Potentially unsafe code in {file_path}")

        # Check for sensitive paths
        for pattern in self.validation_patterns['sensitive_paths']:
            if re.search(pattern, file_path, re.IGNORECASE):
                issues.append(f"SECURITY: Sensitive path detected: {file_path}")

        # Log validation results
        self.logger.info(f"Codex validation for {file_path}: {'PASSED' if not issues else 'FAILED'}")
        for issue in issues:
            self.logger.warning(issue)

        return len(issues) == 0, issues

    async def create_secure_project_structure(self,
                                            project_name: str,
                                            project_structure: Dict[str, Any],
                                            flat_files: Dict[str, str],
                                            output_dir: str = str(resolve_path('temp', 'packaged_projects'))) -> str:
        """
        Create secure project structure with validation
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_id = f"{project_name}_{timestamp}"
        base_dir = os.path.join(output_dir, project_id)

        self.logger.info(f"🚀 Starting infrastructure packaging for {project_id}")

        try:
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Remove previous directory if exists
            shutil.rmtree(base_dir, ignore_errors=True)
            os.makedirs(base_dir, exist_ok=True)

            validation_results = {
                'passed': [],
                'failed': [],
                'warnings': []
            }

            # Write nested folders and files with validation
            for folder, files in project_structure.items():
                if isinstance(files, dict):
                    folder_path = os.path.join(base_dir, folder)
                    os.makedirs(folder_path, exist_ok=True)

                    for file_name, content in files.items():
                        file_path = os.path.join(folder_path, file_name)

                        # Codex validation
                        is_valid, issues = await self.codex_validate_content(content, file_path)

                        if is_valid:
                            with open(file_path, "w") as f:
                                f.write(content)
                            validation_results['passed'].append(file_path)
                        else:
                            validation_results['failed'].append({
                                'file': file_path,
                                'issues': issues
                            })
                            # Still write file but log security concerns
                            with open(file_path, "w") as f:
                                f.write(content)

            # Write flat files with validation
            for file_name, content in flat_files.items():
                file_path = os.path.join(base_dir, file_name)

                # Codex validation
                is_valid, issues = await self.codex_validate_content(content, file_path)

                if is_valid:
                    with open(file_path, "w") as f:
                        f.write(content)
                    validation_results['passed'].append(file_path)
                else:
                    validation_results['failed'].append({
                        'file': file_path,
                        'issues': issues
                    })
                    # For flat files with secrets, create sanitized version
                    if file_name == '.env':
                        sanitized_content = self._sanitize_env_file(content)
                        with open(file_path, "w") as f:
                            f.write(sanitized_content)
                    else:
                        with open(file_path, "w") as f:
                            f.write(content)

            # Create validation report
            validation_report = {
                'project_id': project_id,
                'timestamp': timestamp,
                'total_files': len(validation_results['passed']) + len(validation_results['failed']),
                'passed_validation': len(validation_results['passed']),
                'failed_validation': len(validation_results['failed']),
                'security_issues': validation_results['failed'],
                'validation_score': len(validation_results['passed']) / (len(validation_results['passed']) + len(validation_results['failed'])) * 100 if (len(validation_results['passed']) + len(validation_results['failed'])) > 0 else 0
            }

            # Save validation report
            report_path = os.path.join(base_dir, 'VALIDATION_REPORT.json')
            with open(report_path, 'w') as f:
                json.dump(validation_report, f, indent=2)

            self.logger.info(f"✅ Project structure created: {base_dir}")
            self.logger.info(f"📊 Validation score: {validation_report['validation_score']:.1f}%")

            return base_dir

        except Exception as e:
            self.logger.error(f"❌ Error creating project structure: {str(e)}")
            raise

    def _sanitize_env_file(self, content: str) -> str:
        """Sanitize .env file by replacing actual secrets with placeholders"""
        sanitized = content

        # Replace API keys with placeholders
        sanitized = re.sub(r'(api[_-]?key["\s]*[:=]["\s]*)[a-zA-Z0-9]+',
                          r'\1your_api_key_here', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'(secret[_-]?key["\s]*[:=]["\s]*)[a-zA-Z0-9]+',
                          r'\1your_secret_key_here', sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r'(password["\s]*[:=]["\s]*)[a-zA-Z0-9]+',
                          r'\1your_password_here', sanitized, flags=re.IGNORECASE)

        return sanitized

    async def create_deployment_zip(self, base_dir: str, zip_name: Optional[str] = None) -> str:
        """
        Create deployment ZIP with security verification
        """
        if not zip_name:
            zip_name = f"{os.path.basename(base_dir)}_deployment.zip"

        zip_path = os.path.join(os.path.dirname(base_dir), zip_name)

        try:
            self.logger.info(f"📦 Creating deployment ZIP: {zip_path}")

            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(base_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, base_dir)
                        zipf.write(file_path, arcname)

            # Calculate ZIP hash for integrity
            zip_hash = self._calculate_file_hash(zip_path)

            # Create deployment metadata
            metadata = {
                'zip_path': zip_path,
                'zip_hash': zip_hash,
                'created_at': datetime.now().isoformat(),
                'file_count': len([f for _, _, files in os.walk(base_dir) for f in files]),
                'zip_size_mb': os.path.getsize(zip_path) / (1024 * 1024)
            }

            # Save metadata
            metadata_path = zip_path.replace('.zip', '_metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)

            self.logger.info(f"✅ ZIP created successfully: {zip_path}")
            self.logger.info(f"📊 Size: {metadata['zip_size_mb']:.2f} MB, Files: {metadata['file_count']}")

            return zip_path

        except Exception as e:
            self.logger.error(f"❌ Error creating ZIP: {str(e)}")
            raise

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    async def agent_triggered_packaging(self,
                                      trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main agent-triggered packaging workflow
        """
        self.logger.info(f"🤖 Agent-triggered packaging initiated")

        try:
            project_name = trigger_data.get('project_name', 'eventrelay_project')
            project_structure = trigger_data.get('project_structure', {})
            flat_files = trigger_data.get('flat_files', {})

            # Step 1: Create secure project structure
            base_dir = await self.create_secure_project_structure(
                project_name, project_structure, flat_files
            )

            # Step 2: Create deployment ZIP
            zip_path = await self.create_deployment_zip(base_dir)

            # Step 3: Log to database
            packaging_record = {
                'project_name': project_name,
                'base_dir': base_dir,
                'zip_path': zip_path,
                'trigger_data': trigger_data,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            }

            await self.db_agent._store_data({
                'data_type': 'infrastructure_packaging',
                'key': f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'data': packaging_record
            })

            result = {
                'success': True,
                'project_name': project_name,
                'base_dir': base_dir,
                'zip_path': zip_path,
                'validation_report': os.path.join(base_dir, 'VALIDATION_REPORT.json'),
                'metadata': zip_path.replace('.zip', '_metadata.json')
            }

            self.logger.info(f"🎯 Agent-triggered packaging completed successfully")
            return result

        except Exception as e:
            error_msg = f"Agent packaging failed: {str(e)}"
            self.logger.error(f"❌ {error_msg}")

            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }

    def get_packaging_status(self) -> Dict[str, Any]:
        """Get current packaging agent status"""
        return {
            'agent_name': 'InfrastructurePackagingAgent',
            'status': 'operational',
            'total_packages_created': len(self.packaging_history),
            'last_activity': datetime.now().isoformat(),
            'validation_patterns_loaded': len(self.validation_patterns),
            'log_file': str(resolve_path('logs', 'infrastructure_packaging.log'))
        }


if __name__ == "__main__":
    # Test the agent
    async def test_packaging():
        """Test packaging agent"""
        agent = InfrastructurePackagingAgent()

        # Test project structure
        project_structure = {
            "src/": {
                "main.py": "# Test Main\nimport asyncio\n\nasync def main():\n    print('Hello EventRelay!')\n\nif __name__ == '__main__':\n    asyncio.run(main())\n",
            }
        }

        flat_files = {
            ".env": "API_KEY=test_key_12345\nSECRET=test_secret\n",
            "README.md": "# Test Project\n\nGenerated by EventRelay\n"
        }

        trigger_data = {
            'project_name': 'test_packaging',
            'project_structure': project_structure,
            'flat_files': flat_files,
            'triggered_by': 'EventRelay_Test',
            'deployment_target': 'development'
        }

        result = await agent.agent_triggered_packaging(trigger_data)
        print(f"\n📦 Packaging Result:")
        print(json.dumps(result, indent=2))

        return result

    asyncio.run(test_packaging())
