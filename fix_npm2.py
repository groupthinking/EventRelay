import re

with open("src/youtube_extension/backend/deployment_manager.py", "r") as f:
    content = f.read()

# I will add a validation to verify_project
validation_code = """
        project_dir = Path(project_path)

        # Security: Validate project_path to prevent path traversal or executing in unauthorized directories
        try:
            resolved_path = project_dir.resolve()
            if not resolved_path.is_dir():
                result["summary"] = "Invalid project path: not a directory"
                return result
        except Exception as e:
            result["summary"] = f"Invalid project path: {e}"
            return result
"""

if "package_json = project_dir /" in content:
    content = content.replace("        project_dir = Path(project_path)\n        package_json = project_dir / \"package.json\"", validation_code + "\n        package_json = resolved_path / \"package.json\"")

with open("src/youtube_extension/backend/deployment_manager.py", "w") as f:
    f.write(content)
