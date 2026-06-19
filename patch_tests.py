import re

with open("tests/unit/test_deployment_manager.py", "r") as f:
    content = f.read()

new_tests = '''class TestUploadToGithub:
    async def test_no_token_raises(self) -> None:
        mgr = _make_manager_without_github_token()
        with pytest.raises(Exception, match="token"):
            await mgr._upload_to_github("/path", "repo")

    async def test_uploads_files(self, tmp_path) -> None:
        mgr = _make_manager(github_token="tok")

        (tmp_path / "index.ts").write_text("const x = 1;")
        (tmp_path / "style.css").write_text("body {}")

        def mock_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 200
            if "user" in url:
                resp.json = AsyncMock(return_value={"login": "u"})
            elif "refs/heads" in url:
                resp.json = AsyncMock(return_value={"object": {"sha": "csha"}})
            elif "commits" in url:
                resp.json = AsyncMock(return_value={"tree": {"sha": "tsha"}})
            return _make_aiohttp_ctx(resp)
            
        def mock_post(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 201
            if "blobs" in url:
                resp.json = AsyncMock(return_value={"sha": "bsha"})
            elif "trees" in url:
                resp.json = AsyncMock(return_value={"sha": "ntsha"})
            elif "commits" in url:
                resp.json = AsyncMock(return_value={"sha": "ncsha"})
            
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=resp)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm
            
        def mock_patch(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 200
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=resp)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm

        session_mock = MagicMock()
        session_mock.get = MagicMock(side_effect=mock_get)
        session_mock.post = MagicMock(side_effect=mock_post)
        session_mock.patch = MagicMock(side_effect=mock_patch)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._upload_to_github(str(tmp_path), "my-repo")

        assert result["files_uploaded"] == 2
        assert len(result["file_list"]) == 2

    async def test_skips_excluded_dirs(self, tmp_path) -> None:
        mgr = _make_manager(github_token="tok")

        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "dep.js").write_text("module.exports = {}")
        (tmp_path / "app.ts").write_text("export const x = 1;")

        def mock_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 200
            if "user" in url:
                resp.json = AsyncMock(return_value={"login": "u"})
            elif "refs/heads" in url:
                resp.json = AsyncMock(return_value={"object": {"sha": "csha"}})
            elif "commits" in url:
                resp.json = AsyncMock(return_value={"tree": {"sha": "tsha"}})
            return _make_aiohttp_ctx(resp)
            
        def mock_post(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 201
            resp.json = AsyncMock(return_value={"sha": "msha"})
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=resp)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm
            
        def mock_patch(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 200
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=resp)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm

        session_mock = MagicMock()
        session_mock.get = MagicMock(side_effect=mock_get)
        session_mock.post = MagicMock(side_effect=mock_post)
        session_mock.patch = MagicMock(side_effect=mock_patch)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._upload_to_github(str(tmp_path), "repo")

        # Only app.ts should be uploaded, not node_modules/dep.js
        assert result["files_uploaded"] == 1
        assert "app.ts" in result["file_list"][0]

    async def test_does_not_skip_dotfiles(self, tmp_path) -> None:
        mgr = _make_manager(github_token="tok")

        (tmp_path / ".env").write_text("SECRET=abc")
        (tmp_path / "main.ts").write_text("export const y = 2;")

        def mock_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 200
            if "user" in url:
                resp.json = AsyncMock(return_value={"login": "u"})
            elif "refs/heads" in url:
                resp.json = AsyncMock(return_value={"object": {"sha": "csha"}})
            elif "commits" in url:
                resp.json = AsyncMock(return_value={"tree": {"sha": "tsha"}})
            return _make_aiohttp_ctx(resp)
            
        def mock_post(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 201
            resp.json = AsyncMock(return_value={"sha": "msha"})
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=resp)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm
            
        def mock_patch(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 200
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=resp)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm

        session_mock = MagicMock()
        session_mock.get = MagicMock(side_effect=mock_get)
        session_mock.post = MagicMock(side_effect=mock_post)
        session_mock.patch = MagicMock(side_effect=mock_patch)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            result = await mgr._upload_to_github(str(tmp_path), "repo")

        assert result["files_uploaded"] == 2
        assert any(Path(f).name == ".env" for f in result["file_list"])

    async def test_upload_failure_raises_exception(self, tmp_path) -> None:
        mgr = _make_manager(github_token="tok")
        (tmp_path / "app.ts").write_text("export const z = 3;")

        def mock_get(url, *args, **kwargs):
            resp = MagicMock()
            resp.status = 200
            if "user" in url:
                resp.json = AsyncMock(return_value={"login": "u"})
            elif "refs/heads" in url:
                resp.json = AsyncMock(return_value={"object": {"sha": "csha"}})
            elif "commits" in url:
                resp.json = AsyncMock(return_value={"tree": {"sha": "tsha"}})
            return _make_aiohttp_ctx(resp)

        def mock_post(url, *args, **kwargs):
            resp = MagicMock()
            if "blobs" in url:
                resp.status = 500
                resp.text = AsyncMock(return_value="server error")
            else:
                resp.status = 201
                resp.json = AsyncMock(return_value={"sha": "msha"})
            
            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=resp)
            cm.__aexit__ = AsyncMock(return_value=False)
            return cm

        session_mock = MagicMock()
        session_mock.get = MagicMock(side_effect=mock_get)
        session_mock.post = MagicMock(side_effect=mock_post)

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch("youtube_extension.backend.deployment_manager.aiohttp.ClientSession", return_value=session_cm):
            with pytest.raises(Exception, match="Failed to create blob"):
                await mgr._upload_to_github(str(tmp_path), "repo")
'''

start_str = 'class TestUploadToGithub:'
end_str = '# ==========================================================================='

start_idx = content.find(start_str)
end_idx = content.find(end_str, start_idx + len(start_str))

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + new_tests + '\n\n' + content[end_idx:]
    with open("tests/unit/test_deployment_manager.py", "w") as f:
        f.write(new_content)
    print("Patched test_deployment_manager.py")
else:
    print("Could not find boundaries")
