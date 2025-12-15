# Agent Self-Creation Quick Reference

## TL;DR

**Question**: Can new custom GitHub Copilot agents self-create when needed?

**Answer**: Yes, through semi-automated detection and generation! While agents can't literally write themselves to the repo (static files), the system automatically:
1. Detects when new agents are needed
2. Recommends agents with confidence scores
3. Generates production-ready templates
4. Guides human review and activation

## Quick Start

```bash
# 1. Analyze current coverage
python scripts/manage_custom_agents.py analyze --demo

# 2. Get recommendations
python scripts/manage_custom_agents.py recommend

# 3. Generate agent template
python scripts/manage_custom_agents.py generate infrastructure

# 4. Review and activate
mv ~/.eventrelay/agent_gaps/recommendations/infrastructure.agent.md .github/agents/
git add .github/agents/infrastructure.agent.md
git commit -m "Add infrastructure agent"
git push

# 5. Use in GitHub Copilot
# @infrastructure How do I configure Kubernetes health checks?
```

## Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `analyze` | Detect gaps in coverage | `analyze --demo` |
| `recommend` | Get agent recommendations | `recommend` |
| `generate` | Create agent template | `generate database` |
| `report` | Full analysis report | `report` |
| `list` | List existing agents | `list` |
| `validate` | Validate agent files | `validate` |

## How Detection Works

```python
# System monitors usage patterns:
- File access: infrastructure/k8s/deployment.yaml → Infrastructure gap
- Error patterns: DatabaseConnectionError (3x) → Database gap
- Technology keywords: terraform, helm, docker → Infrastructure gap

# When thresholds met:
- Confidence ≥ 70% AND
- Frequency ≥ 3 occurrences
→ Recommendation generated
```

## Recognized Domains

- **infrastructure**: Docker, Kubernetes, Terraform
- **database**: PostgreSQL, MongoDB, Redis
- **security**: Auth, OAuth, JWT
- **devops**: CI/CD, GitHub Actions
- **performance**: Optimization, caching
- **data-science**: Pandas, NumPy, ML
- **mobile**: iOS, Android, React Native
- **blockchain**: Web3, Ethereum
- **ai-ml**: Machine learning, LLMs

## Generated Template Includes

✅ Valid YAML frontmatter (name, description, tools, target)  
✅ EventRelay workflow integration  
✅ Project-specific best practices  
✅ Security standards (no secrets, input validation)  
✅ Testing standards (>80% coverage, standard video ID)  
✅ Domain-specific expertise areas  
✅ Real usage examples  
✅ Integration with other agents  

## Optional Monitoring

Enable automatic gap detection:

```bash
export EVENTRELAY_MONITOR_AGENT_GAPS=true
```

```python
from youtube_extension.services.agents.monitor import monitor_agent_usage

# Track file access
monitor_agent_usage(file_path="deploy.yml", task="Configure CI/CD")

# Track errors
monitor_agent_usage(error=("DatabaseError", "Timeout", 3))
```

## Example Workflow

**Scenario**: Need infrastructure agent

1. **Detection**: 
   ```
   Edit k8s/deployment.yaml (3x)
   → Gap detected: infrastructure (confidence: 0.75)
   ```

2. **Recommendation**:
   ```
   $ python scripts/manage_custom_agents.py recommend
   🔴 INFRASTRUCTURE Agent (Priority: HIGH, Confidence: 0.85)
   ```

3. **Generation**:
   ```
   $ python scripts/manage_custom_agents.py generate infrastructure
   ✅ Template created
   ```

4. **Activation**:
   ```
   $ mv ~/.eventrelay/.../infrastructure.agent.md .github/agents/
   $ git add && git commit && git push
   ```

5. **Usage**:
   ```
   @infrastructure Configure Kubernetes deployment
   ```

## Files

| File | Purpose | Lines |
|------|---------|-------|
| `agent_gap_analyzer.py` | Core detection engine | 540 |
| `manage_custom_agents.py` | CLI tool | 368 |
| `monitor.py` | Optional monitoring | 111 |
| `AGENT_SELF_CREATION.md` | Full documentation | 400 |
| `agent_self_creation_demo.py` | Interactive demo | 159 |

## Key Features

✅ **Automated Detection**: Tracks patterns, identifies gaps  
✅ **Data-Driven**: Confidence scores, frequency thresholds  
✅ **Production-Ready**: Templates follow all conventions  
✅ **Non-Breaking**: No changes to existing agents  
✅ **Well-Tested**: All commands verified  
✅ **Documented**: Comprehensive guides and examples  

## Limitations

❌ Cannot truly self-create at runtime (GitHub Copilot constraint)  
❌ Requires human review before activation  
❌ Cannot modify existing agents automatically  
✅ But achieves goal: identifies when new agents are needed!  

## Demo

```bash
python examples/agent_self_creation_demo.py
```

## Documentation

- **Full Guide**: `/docs/AGENT_SELF_CREATION.md`
- **Summary**: `/AGENT_SELF_CREATION_SUMMARY.md`
- **Quick Ref**: This file
- **Agent README**: `/.github/agents/README.md`

## Support

Questions? Check:
1. Run the demo: `python examples/agent_self_creation_demo.py`
2. Read docs: `/docs/AGENT_SELF_CREATION.md`
3. List agents: `python scripts/manage_custom_agents.py list`
4. Open GitHub issue

---

**Remember**: The system recommends agents when patterns emerge. Review recommendations regularly and generate agents as needed to enhance development productivity!
