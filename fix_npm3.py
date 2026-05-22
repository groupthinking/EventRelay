import re

with open("src/youtube_extension/backend/deployment_manager.py", "r") as f:
    content = f.read()

# Make sure we use resolved_path for cwd instead of project_path
content = content.replace("cwd=project_path", "cwd=str(resolved_path)")

with open("src/youtube_extension/backend/deployment_manager.py", "w") as f:
    f.write(content)
