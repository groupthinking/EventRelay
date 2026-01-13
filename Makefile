
scan-dupes:
	python3 scripts/duplicate_scan.py --root . > reports/duplicate_report.md

# NotebookLM MCP - spawn on demand (avoids background CPU drain)
# Usage: make notebooklm-mcp
notebooklm-mcp:
	@echo "Starting NotebookLM MCP server (Ctrl+C to stop)..."
	npx -y notebooklm-mcp@latest
