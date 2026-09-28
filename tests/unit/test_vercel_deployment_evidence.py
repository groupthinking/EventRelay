"""Provider response fixtures test failure handling, not live deployment proof.

Run without the application's unrelated integration fixtures:
PYTHONPATH=src python -m unittest discover -s tests/unit -p test_vercel_deployment_evidence.py -v
"""

import os
import unittest
from unittest.mock import AsyncMock, patch

from youtube_extension.backend.deploy.core import BaseDeploymentAdapter, DeploymentError
from youtube_extension.backend.deploy.vercel import VercelAdapter


class VercelDeploymentEvidenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env_patch = patch.dict(os.environ, {"VERCEL_TOKEN": "test-only"}, clear=True)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.adapter = VercelAdapter()
        self.request = AsyncMock()
        self.adapter._make_request_with_retry = self.request
        self.sleep_patch = patch(
            "youtube_extension.backend.deploy.core.asyncio.sleep", new_callable=AsyncMock
        )
        self.sleep_patch.start()
        self.addCleanup(self.sleep_patch.stop)

    async def deploy(self, config=None):
        return await self.adapter.deploy(
            ".", config or {"project_type": "web"},
            {"GITHUB_REPO_URL": "https://github.com/example/fixture"},
        )

    async def test_ready_on_creation_preserves_provider_evidence(self):
        self.request.return_value = {
            "id": "dpl_fixture", "readyState": "READY", "url": "fixture.vercel.app"
        }
        result = await self.deploy()
        self.assertEqual(result.status, "success")
        self.assertEqual(result.url, "https://fixture.vercel.app")
        self.assertEqual(result.metadata["ready_state"], "READY")
        self.assertEqual(self.request.await_count, 1)

    async def test_actual_poller_understands_ready_state(self):
        final = {"id": "dpl_fixture", "readyState": "READY", "url": "final.vercel.app"}
        self.request.side_effect = [
            {"id": "dpl_fixture", "readyState": "BUILDING", "url": "initial.vercel.app"},
            {"readyState": "BUILDING"}, final,
        ]
        result = await self.deploy()
        self.assertEqual(result.status, "success")
        self.assertEqual(result.url, "https://final.vercel.app")
        self.assertEqual(result.metadata["deployment_data"], final)

    async def test_terminal_failures_never_return_initial_url(self):
        for state in ("ERROR", "CANCELED", "CANCELLED"):
            with self.subTest(state=state):
                self.request.side_effect = [
                    {"id": "dpl_fixture", "readyState": "BUILDING", "url": "initial.vercel.app"},
                    {"readyState": state},
                ]
                result = await self.deploy()
                self.assertEqual(result.status, "failed")
                self.assertIsNone(result.url)
                self.assertEqual(result.deployment_id, "dpl_fixture")

    async def test_poll_timeout_does_not_become_success(self):
        self.request.return_value = {
            "id": "dpl_fixture", "readyState": "BUILDING", "url": "initial.vercel.app"
        }
        # Exercise the real polling timeout branch without waiting fifteen minutes.
        with patch("youtube_extension.backend.deploy.core.time.time", side_effect=[0, 901]):
            result = await self.deploy()
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.url)
        self.assertTrue(result.metadata["recoverable"])

    async def test_ready_without_final_url_does_not_invent_or_reuse_one(self):
        self.request.side_effect = [
            {"id": "dpl_fixture", "readyState": "BUILDING", "url": "initial.vercel.app"},
            {"id": "dpl_fixture", "readyState": "READY"},
        ]
        result = await self.deploy()
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.url)

    async def test_creation_error_keeps_import_link_out_of_live_url(self):
        self.request.side_effect = DeploymentError("vercel", "create", "Denied")
        result = await self.deploy()
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.url)
        self.assertIn("vercel.com/new/import", result.metadata["import_url"])

    async def test_missing_id_keeps_import_link_out_of_live_url(self):
        self.request.return_value = {"readyState": "READY", "url": "fixture.vercel.app"}
        result = await self.deploy()
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.url)

    async def test_creation_terminal_error_does_not_poll(self):
        self.request.return_value = {"id": "dpl_fixture", "readyState": "ERROR"}
        result = await self.deploy()
        self.assertEqual(result.status, "failed")
        self.assertEqual(self.request.await_count, 1)

    async def test_default_settings_do_not_suppress_build_or_install(self):
        self.request.return_value = {
            "id": "dpl_fixture", "readyState": "READY", "url": "fixture.vercel.app"
        }
        await self.deploy()
        settings = self.request.call_args.kwargs["json_data"]["projectSettings"]
        self.assertEqual(settings, {"framework": "nextjs"})

    async def test_explicit_settings_are_preserved(self):
        self.request.return_value = {
            "id": "dpl_fixture", "readyState": "READY", "url": "fixture.vercel.app"
        }
        await self.deploy({"framework": "vite", "install_command": "npm ci",
                           "build_command": "npm run build", "output_directory": "dist"})
        settings = self.request.call_args.kwargs["json_data"]["projectSettings"]
        self.assertEqual(settings, {"framework": "vite", "installCommand": "npm ci",
                                    "buildCommand": "npm run build", "outputDirectory": "dist"})

    def test_other_providers_retain_status_field(self):
        self.assertEqual(
            BaseDeploymentAdapter._deployment_status(self.adapter, {"status": "ready"}),
            "ready",
        )
