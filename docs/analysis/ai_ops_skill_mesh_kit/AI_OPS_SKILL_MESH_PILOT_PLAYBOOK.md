AI Ops Skill Mesh Pilot Playbook
================================

Objective
---------
Deliver a 7-day pilot that proves the value of the collective-learning network for a real operations or platform team.

Pilot Roles
-----------
- **Champion**: Ops lead responsible for rollout and daily check-ins.
- **Two Agents**: Engineer workflows (or automation scripts) that will capture/consume skills.
- **Observer**: Tracks metrics and gathers anecdotes for the go/no-go deck.

Day 0 – Setup (60 minutes)
--------------------------
1. Clone repository and install dependencies.  
2. Verify bridge is active: `ls ~/.claude/claude_bridge_enhanced.db`.  
3. Run smoke tests:  
   ```
   python3 test_skill_connector.py
   python3 test_multi_agent_learning.py
   ```
4. Start watchdog loops (use `tmux`/`pm2`/`systemd`):  
   ```
   # Artifact integrity
   python3 ../../scripts/validate_runs_loop.py --watch --interval 300 --include-warnings

   # Skill network health
   python3 ../../scripts/monitor_collective_learning.py --watch --interval 300 --include-manifest
   ```
5. Announce pilot start in team channel; share quick commands cheat-sheet (below).

Days 1-5 – Live Usage
---------------------
- Route real incidents or failed runs to the pilot agents first.  
- When an agent resolves an issue, ensure they use `collective_auto_resolve` or call `capture_error_resolution` so the fix propagates.  
- At end of each day:
  - `tail -n 20 collective_learning_monitor_log.jsonl` for new skills, success counts.
  - `python3 scripts/monitor_collective_learning.py --skip-tests --include-manifest` to snapshot metrics.
  - Log duplicates avoided or minutes saved in a shared spreadsheet.

Metrics to Capture
------------------
| Metric | How to collect | Target |
|--------|---------------|--------|
| Skills added | `python3 scripts/monitor_collective_learning.py --skip-tests` | ≥ 1/day |
| Auto-resolved issues | `skills_database.json` stats | Upward trend |
| Validation success | Output of `validate_runs_loop.py` | 100% |
| MTTR delta | Manual log from engineers | ≥ 20% faster |

Day 6 – Review & Storytelling
-----------------------------
- Export the latest monitor and validator logs.  
- Run `python3 scripts/monitor_collective_learning.py --show-output --include-manifest` to capture final state.  
- Assemble screenshots of key log lines (auto-resolve messages, zero pending queue).  
- Draft a one-page outcome summary referencing the `AI_OPS_SKILL_MESH_CASE_STUDY.md`.

Day 7 – Recommend Next Steps
----------------------------
- Present findings to stakeholders.  
- Choose one of the upgrade paths: web-socket push (Tier 2) or cache/index package (Tier 3).  
- If green-lit, scope production integration (cron jobs, dashboards, access controls).

Cheat-Sheet Commands
--------------------
```
# Inject a new skill manually
python3 -c "from skill_bridge_connector import collective_builder; collective_builder.capture_error_resolution('ImportError', 'No module named sample', 'pip install sample')"

# Check shared bridge
sqlite3 ~/.claude/claude_bridge_enhanced.db \"SELECT COUNT(*), status FROM enhanced_messages WHERE message_id LIKE 'skill_%' GROUP BY status\"

# Validate latest run artifacts
npm run validate:run-id -- integration-test-TEST12345
```

Exit Criteria
-------------
- ≥5 unique skills broadcast with 0 pending messages.  
- Measurable MTTR reduction on at least one recurring error.  
- Stakeholders acknowledge the manual time saved (captured in retro notes).  
- Decision made: move to Tier-2 upgrade or pause.  

Appendix – Deliverables
-----------------------
- `AI_OPS_SKILL_MESH_CASE_STUDY.md` (updated with pilot data).  
- `collective_learning_monitor_log.jsonl` (full pilot timeline).  
- `workflow_results/runs/*` artifacts with validated schemas.  
- Slide/recording summarising the journey (optional but recommended).
