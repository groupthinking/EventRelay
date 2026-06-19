import re

with open("src/youtube_extension/backend/deployment_manager.py", "r") as f:
    content = f.read()

new_upload = '''    async def _upload_to_github(self, project_path: str, repo_name: str) -> dict[str, Any]:
        """Upload project files to GitHub repository using Git Trees API for atomic commit"""
        if not self.github_token:
            raise Exception("GitHub token not configured")

        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with aiohttp.ClientSession() as session:
            # Get user info
            async with session.get("https://api.github.com/user", headers=headers) as user_response:
                user_data = await user_response.json()
                username = user_data["login"]

            project_path_obj = Path(project_path)

            # Directories to exclude from GitHub upload (standard .gitignore patterns)
            EXCLUDED_DIRS = {'node_modules', '.next', '.git', '__pycache__', '.vercel', 'dist', '.turbo'}

            def should_skip_path(path: Path) -> bool:
                """Check if any parent directory is in the exclusion list"""
                return any(part in EXCLUDED_DIRS for part in path.parts)

            files_to_upload = []
            for file_path in project_path_obj.rglob("*"):
                # Skip excluded directories
                if should_skip_path(file_path.relative_to(project_path_obj)):
                    continue
                if file_path.is_file():  # Dotfiles should be uploaded
                    files_to_upload.append(file_path)

            if not files_to_upload:
                return {
                    "files_uploaded": 0,
                    "file_list": []
                }

            # 1. Get branch reference
            branch_url = f"https://api.github.com/repos/{username}/{repo_name}/git/refs/heads/main"
            async with session.get(branch_url, headers=headers) as branch_response:
                if branch_response.status != 200:
                    error_text = await branch_response.text()
                    raise Exception(f"Failed to get branch reference: {error_text}")
                branch_data = await branch_response.json()
                base_commit_sha = branch_data["object"]["sha"]

            # 2. Get base tree
            commit_url = f"https://api.github.com/repos/{username}/{repo_name}/git/commits/{base_commit_sha}"
            async with session.get(commit_url, headers=headers) as commit_response:
                if commit_response.status != 200:
                    error_text = await commit_response.text()
                    raise Exception(f"Failed to get base commit: {error_text}")
                commit_data = await commit_response.json()
                base_tree_sha = commit_data["tree"]["sha"]

            # 3. Create blobs concurrently
            tree_items = []
            uploaded_files = []
            semaphore = asyncio.Semaphore(10)

            async def create_blob(file_path: Path):
                relative_path = file_path.relative_to(project_path_obj)
                async with semaphore:
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()

                        encoded_content = base64.b64encode(content).decode('utf-8')
                        blob_data = {
                            "content": encoded_content,
                            "encoding": "base64"
                        }

                        blob_url = f"https://api.github.com/repos/{username}/{repo_name}/git/blobs"
                        async with session.post(blob_url, headers=headers, json=blob_data) as response:
                            if response.status == 201:
                                blob_result = await response.json()
                                tree_items.append({
                                    "path": str(relative_path).replace("\\", "/"),
                                    "mode": "100644",
                                    "type": "blob",
                                    "sha": blob_result["sha"]
                                })
                                uploaded_files.append(str(relative_path))
                            else:
                                error_text = await response.text()
                                raise Exception(f"Failed to create blob for {relative_path}: {error_text}")
                    except Exception as e:
                        logger.error(f"Error uploading {file_path}: {e}")
                        raise

            # Execute blob creations and fail fast if any errors out
            await asyncio.gather(*(create_blob(f) for f in files_to_upload))

            # 4. Create new tree
            tree_data = {
                "base_tree": base_tree_sha,
                "tree": tree_items
            }
            tree_url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees"
            async with session.post(tree_url, headers=headers, json=tree_data) as tree_response:
                if tree_response.status != 201:
                    error_text = await tree_response.text()
                    raise Exception(f"Failed to create tree: {error_text}")
                new_tree_data = await tree_response.json()
                new_tree_sha = new_tree_data["sha"]

            # 5. Create new commit
            new_commit_data = {
                "message": "Initial project deployment from EventRelay",
                "tree": new_tree_sha,
                "parents": [base_commit_sha]
            }
            new_commit_url = f"https://api.github.com/repos/{username}/{repo_name}/git/commits"
            async with session.post(new_commit_url, headers=headers, json=new_commit_data) as new_commit_response:
                if new_commit_response.status != 201:
                    error_text = await new_commit_response.text()
                    raise Exception(f"Failed to create commit: {error_text}")
                created_commit_data = await new_commit_response.json()
                new_commit_sha = created_commit_data["sha"]

            # 6. Update reference
            ref_update_data = {
                "sha": new_commit_sha,
                "force": False
            }
            async with session.patch(branch_url, headers=headers, json=ref_update_data) as ref_response:
                if ref_response.status != 200:
                    error_text = await ref_response.text()
                    raise Exception(f"Failed to update reference: {error_text}")

        return {
            "files_uploaded": len(uploaded_files),
            "file_list": uploaded_files
        }'''

# Replace from `    async def _upload_to_github(self, project_path: str, repo_name: str) -> dict[str, Any]:`
# up to `    # NOTE: legacy _deploy_to_vercel removed; real implementation now in backend.deploy.vercel`
start_str = '    async def _upload_to_github(self, project_path: str, repo_name: str) -> dict[str, Any]:'
end_str = '    # NOTE: legacy _deploy_to_vercel removed; real implementation now in backend.deploy.vercel'

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + new_upload + '\n\n' + content[end_idx:]
    with open("src/youtube_extension/backend/deployment_manager.py", "w") as f:
        f.write(new_content)
    print("Patched deployment_manager.py")
else:
    print("Could not find boundaries")
