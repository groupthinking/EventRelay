import re

with open("src/youtube_extension/backend/deployment_manager.py", "r") as f:
    content = f.read()

# Add ignore scripts to prevent arbitrary script execution
content = content.replace('"--legacy-peer-deps"', '"--legacy-peer-deps", "--ignore-scripts"')

with open("src/youtube_extension/backend/deployment_manager.py", "w") as f:
    f.write(content)
