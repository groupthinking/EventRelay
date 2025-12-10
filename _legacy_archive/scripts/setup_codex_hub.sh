set -euo pipefail
mkdir -p ~/Dev/OpenAI_Hub/{apps,agents,projects,configs/envs,keys,backups}
ln -snf ~/Downloads/openai-apps-sdk-examples  ~/Dev/OpenAI_Hub/apps/apps-sdk
ln -snf ~/Downloads/openai-agents-demo        ~/Dev/OpenAI_Hub/agents/agents-demo
ln -snf ~/Downloads/codex-sdk-demo            ~/Dev/OpenAI_Hub/projects/sdk-demo
ln -snf ~/agents                              ~/Dev/OpenAI_Hub/agents/docs
cat > ~/Dev/OpenAI_Hub/hub.index.yaml <<'YAML'
openai_hub:
  root: ~/Dev/OpenAI_Hub
  apps:    [ { path: apps/apps-sdk } ]
  agents:  [ { path: agents/agents-demo }, { path: agents/docs } ]
  projects:[ { path: projects/sdk-demo } ]
YAML
echo "Hub ready at ~/Dev/OpenAI_Hub"
