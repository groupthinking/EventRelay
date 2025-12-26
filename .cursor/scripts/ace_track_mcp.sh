#!/bin/bash
# ACE MCP Tracking Hook - Captures tool executions for AI-Trail
# Input: tool_name, tool_input, result_json, duration

input=$(cat)
mkdir -p .cursor/ace
echo "$input" >> .cursor/ace/mcp_trajectory.jsonl
exit 0
