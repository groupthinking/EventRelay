#!/bin/bash
# ACE Shell Tracking Hook - Captures terminal commands for AI-Trail
# Input: command, output, duration

input=$(cat)
mkdir -p .cursor/ace
echo "$input" >> .cursor/ace/shell_trajectory.jsonl
exit 0
