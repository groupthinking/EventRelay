from pathlib import Path
import os
import subprocess

project_path = "/tmp/test"
npm_path = "/usr/local/bin/npm" if os.path.exists("/usr/local/bin/npm") else "npm"

print(npm_path)
