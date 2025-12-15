#!/usr/bin/env python3
"""
Infrastructure Packaging MCP Server
===================================

MCP server for agent-triggered, Codex-validated infrastructure packaging.
Provides secure ZIP creation, validation, and deployment capabilities.

Usage:
    python3 infrastructure_packaging_mcp.py

MCP Tools:
    - create_secure_package: Create validated project ZIP
    - validate_project_structure: Security validation only
    - get_packaging_status: Agent status and history
    - list_packages: List created packages
"""

import asyncio
import json
import sys
from typing import Any, Dict, List
from datetime import datetime

# Add UVAI src to path
sys.path.append('/Users/garvey/UVAI/src')

from agents.infrastructure_packaging_agent import InfrastructurePackagingAgent

class InfrastructurePackagingMCPServer:
    """MCP Server for Infrastructure Packaging Agent"""
    
    def __init__(self):
        self.packaging_agent = InfrastructurePackagingAgent()
        self.server_info = {
            "name": "infrastructure-packaging-mcp",
            "version": "1.0.0",
            "description": "Agent-triggered, Codex-validated infrastructure packaging"
        }
        
    async def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": self.server_info
        }
    
    async def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools"""
        tools = [
            {
                "name": "create_secure_package",
                "description": "Create agent-triggered, Codex-validated project package",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project to package"
                        },
                        "project_structure": {
                            "type": "object",
                            "description": "Nested project structure with folders and files"
                        },
                        "flat_files": {
                            "type": "object",
                            "description": "Flat files like .env, requirements.txt"
                        },
                        "deployment_target": {
                            "type": "string",
                            "description": "Target environment (development, staging, production)",
                            "default": "development"
                        }
                    },
                    "required": ["project_name", "project_structure"]
                }
            },
            {
                "name": "validate_project_structure",
                "description": "Validate project structure for security issues without creating package",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_structure": {
                            "type": "object",
                            "description": "Project structure to validate"
                        },
                        "flat_files": {
                            "type": "object",
                            "description": "Flat files to validate"
                        }
                    },
                    "required": ["project_structure"]
                }
            },
            {
                "name": "get_packaging_status",
                "description": "Get current packaging agent status and history",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "list_packages",
                "description": "List all created packages with metadata",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of packages to return",
                            "default": 10
                        }
                    }
                }
            }
        ]
        
        return {"tools": tools}
    
    async def handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "create_secure_package":
                return await self._create_secure_package(arguments)
            elif tool_name == "validate_project_structure":
                return await self._validate_project_structure(arguments)
            elif tool_name == "get_packaging_status":
                return await self._get_packaging_status(arguments)
            elif tool_name == "list_packages":
                return await self._list_packages(arguments)
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Unknown tool: {tool_name}"
                        }
                    ]
                }
                
        except Exception as e:
            return {
                "content": [
                    {
                        "type": "text", 
                        "text": f"Error executing {tool_name}: {str(e)}"
                    }
                ]
            }
    
    async def _create_secure_package(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create secure package with full validation"""
        project_name = args.get("project_name")
        project_structure = args.get("project_structure", {})
        flat_files = args.get("flat_files", {})
        deployment_target = args.get("deployment_target", "development")
        
        trigger_data = {
            'project_name': project_name,
            'project_structure': project_structure,
            'flat_files': flat_files,
            'triggered_by': 'MCP_Agent',
            'deployment_target': deployment_target
        }
        
        result = await self.packaging_agent.agent_triggered_packaging(trigger_data)
        
        if result['success']:
            response_text = f"""🎯 **SECURE PACKAGE CREATED SUCCESSFULLY**

**Project**: {result['project_name']}
**ZIP Location**: {result['zip_path']}
**Project Directory**: {result['base_dir']}
**Validation Report**: {result['validation_report']}
**Metadata**: {result['metadata']}

✅ **Features Applied**:
- 🤖 Agent-triggered packaging
- 🔒 Codex security validation  
- 🛡️ Secrets sanitization
- 📦 Error-proof ZIP creation
- 📊 Comprehensive validation report

**Next Steps**:
1. Review validation report for security issues
2. Test deployment in {deployment_target} environment
3. Access logs at: /Users/garvey/UVAI/logs/infrastructure_packaging.log

🚀 **Ready for billion-dollar AI/agent deployment!**"""
        else:
            response_text = f"""❌ **PACKAGE CREATION FAILED**

**Error**: {result['error']}
**Timestamp**: {result['timestamp']}

Check logs for detailed error information."""
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": response_text
                }
            ]
        }
    
    async def _validate_project_structure(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate project structure without creating package"""
        project_structure = args.get("project_structure", {})
        flat_files = args.get("flat_files", {})
        
        validation_results = {
            'total_files': 0,
            'security_issues': [],
            'warnings': []
        }
        
        # Validate nested files
        for folder, files in project_structure.items():
            if isinstance(files, dict):
                for file_name, content in files.items():
                    file_path = f"{folder}/{file_name}"
                    is_valid, issues = await self.packaging_agent.codex_validate_content(content, file_path)
                    validation_results['total_files'] += 1
                    
                    if not is_valid:
                        validation_results['security_issues'].extend(issues)
        
        # Validate flat files
        for file_name, content in flat_files.items():
            is_valid, issues = await self.packaging_agent.codex_validate_content(content, file_name)
            validation_results['total_files'] += 1
            
            if not is_valid:
                validation_results['security_issues'].extend(issues)
        
        # Calculate security score
        security_score = max(0, 100 - (len(validation_results['security_issues']) * 10))
        
        response_text = f"""🔍 **PROJECT STRUCTURE VALIDATION**

**Files Analyzed**: {validation_results['total_files']}
**Security Issues Found**: {len(validation_results['security_issues'])}
**Security Score**: {security_score}%

**Security Issues**:
"""
        
        if validation_results['security_issues']:
            for issue in validation_results['security_issues']:
                response_text += f"⚠️ {issue}\n"
        else:
            response_text += "✅ No security issues detected\n"
        
        response_text += f"""
**Validation Status**: {'✅ PASSED' if security_score >= 80 else '❌ FAILED - Security issues need attention'}

**Recommendation**: {'Ready for packaging' if security_score >= 80 else 'Fix security issues before packaging'}"""
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": response_text
                }
            ]
        }
    
    async def _get_packaging_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get packaging agent status"""
        status = self.packaging_agent.get_packaging_status()
        
        response_text = f"""📊 **INFRASTRUCTURE PACKAGING AGENT STATUS**

**Agent Name**: {status['agent_name']}
**Status**: {status['status'].upper()}
**Total Packages Created**: {status['total_packages_created']}
**Last Activity**: {status['last_activity']}
**Validation Patterns Loaded**: {status['validation_patterns_loaded']}
**Log File**: {status['log_file']}

🔧 **Capabilities**:
- ✅ Agent-triggered packaging
- ✅ Codex security validation
- ✅ Secrets sanitization
- ✅ Error-proof ZIP creation
- ✅ MCP ecosystem integration

🎯 **Ready for billion-dollar AI/agent deployment scenarios!**"""
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": response_text
                }
            ]
        }
    
    async def _list_packages(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List created packages"""
        limit = args.get("limit", 10)
        
        # For now, return a placeholder - in production this would query the database
        response_text = f"""📦 **RECENT PACKAGES** (Last {limit})

🔍 **To implement**: Query database for packaging history
📊 **Current**: Check /Users/garvey/UVAI/temp/packaged_projects/
📋 **Logs**: /Users/garvey/UVAI/logs/infrastructure_packaging.log

**Example packages that can be created**:
- 🎯 Palantir MCP Integration
- 🚀 UVAI Extension Packages  
- 🔧 MCP Server Deployments
- 📦 Agent Tool Bundles

**Usage**: Use `create_secure_package` to create new packages"""
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": response_text
                }
            ]
        }

async def main():
    """Main MCP server loop"""
    server = InfrastructurePackagingMCPServer()
    
    while True:
        try:
            # Read MCP request from stdin
            line = sys.stdin.readline()
            if not line:
                break
                
            request = json.loads(line.strip())
            method = request.get("method")
            params = request.get("params", {})
            request_id = request.get("id")
            
            # Handle different MCP methods
            if method == "initialize":
                result = await server.handle_initialize(params)
            elif method == "tools/list":
                result = await server.handle_tools_list(params)
            elif method == "tools/call":
                result = await server.handle_tools_call(params)
            else:
                result = {"error": f"Unknown method: {method}"}
            
            # Send response
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
            print(json.dumps(response))
            sys.stdout.flush()
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0", 
                "id": request.get("id") if 'request' in locals() else None,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            print(json.dumps(error_response))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())