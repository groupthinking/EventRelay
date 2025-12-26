#!/bin/bash
# ACE Response Tracking Hook - Captures agent responses for AI-Trail
# Input: text (assistant final text)

input=$(cat)
mkdir -p .cursor/ace
echo "$input" >> .cursor/ace/response_trajectory.jsonl
exit 0
