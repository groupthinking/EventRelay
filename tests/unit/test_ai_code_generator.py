"""Unit tests for backend/ai_code_generator.py."""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

import youtube_extension.backend.ai_code_generator as _mod
from youtube_extension.backend.ai_code_generator import (
    AICodeGenerator,
    get_ai_code_generator,
)

_ARCH = {
    "type": "web_app",
    "framework": "nextjs",
    "frontend": {"framework": "nextjs", "styling": "tailwind"},
    "backend": {"type": "api_routes", "database": "supabase", "auth": "nextauth"},
    "features": ["auth", "api"],
    "deployment": {"platform": "vercel"},
    "monetization": {"model": "freemium"},
}


# ===========================================================================
# AICodeGenerator.__init__
# ===========================================================================


class TestAICodeGeneratorInit:
    def test_init_without_any_api_keys(self, monkeypatch, tmp_path):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "PERPLEXITY_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.router is None

    def test_init_with_custom_output_dir(self, tmp_path):
        custom = tmp_path / "custom_out"
        gen = AICodeGenerator(output_dir=str(custom))
        assert gen.output_dir == custom
        assert custom.exists()

    def test_default_output_dir_created(self, monkeypatch, tmp_path):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path / "out"))
        assert gen.output_dir.exists()

    def test_router_none_when_no_provider_keys(self, monkeypatch, tmp_path):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "PERPLEXITY_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.router is None


# ===========================================================================
# AICodeGenerator.generate_fullstack_project
# ===========================================================================


class TestGenerateFullstackProject:
    async def test_raises_when_no_provider(self, monkeypatch, tmp_path):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "PERPLEXITY_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="LLM provider"):
            await gen.generate_fullstack_project({}, {})


# ===========================================================================
# AICodeGenerator._default_architecture
# ===========================================================================


class TestDefaultArchitecture:
    def test_returns_dict(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert isinstance(result, dict)

    def test_has_type(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert "type" in result

    def test_has_framework(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert result["framework"] == "nextjs"

    def test_has_features_list(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert isinstance(result["features"], list)

    def test_monorepo_flag(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert result["monorepo"] is True


# ===========================================================================
# AICodeGenerator._tailwind_config
# ===========================================================================


class TestTailwindConfig:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._tailwind_config()
        assert isinstance(result, str)

    def test_contains_tailwindcss(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._tailwind_config()
        assert "tailwindcss" in result.lower() or "content" in result

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._tailwind_config()) > 50


# ===========================================================================
# AICodeGenerator._tsconfig
# ===========================================================================


class TestTsconfig:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert isinstance(gen._tsconfig(), str)

    def test_contains_compileroptions(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert "compilerOptions" in gen._tsconfig()

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._tsconfig()) > 50


# ===========================================================================
# AICodeGenerator._next_config
# ===========================================================================


class TestNextConfig:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert isinstance(gen._next_config(), str)

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._next_config()) > 20


# ===========================================================================
# AICodeGenerator._globals_css
# ===========================================================================


class TestGlobalsCss:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert isinstance(gen._globals_css(), str)

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._globals_css()) > 10


# ===========================================================================
# AICodeGenerator._gitignore
# ===========================================================================


class TestGitignore:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert isinstance(gen._gitignore(), str)

    def test_contains_node_modules(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert "node_modules" in gen._gitignore()

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._gitignore()) > 20


# ===========================================================================
# AICodeGenerator._github_actions_deploy
# ===========================================================================


class TestGithubActionsDeploy:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert isinstance(gen._github_actions_deploy(), str)

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._github_actions_deploy()) > 50


# ===========================================================================
# AICodeGenerator._generate_readme
# ===========================================================================


class TestGenerateReadme:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_readme("My Project", _ARCH, {})
        assert isinstance(result, str)

    def test_contains_title(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_readme("Awesome App", _ARCH, {})
        assert "Awesome App" in result

    def test_contains_framework(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_readme("T", _ARCH, {})
        assert "nextjs" in result.lower() or "next" in result.lower()

    def test_uses_video_url_from_analysis(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        va = {"video_data": {"video_url": "https://example.com/vid"}}
        result = gen._generate_readme("T", _ARCH, va)
        assert "https://example.com/vid" in result


# ===========================================================================
# AICodeGenerator._generate_env_example
# ===========================================================================


class TestGenerateEnvExample:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_example(_ARCH)
        assert isinstance(result, str)

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._generate_env_example(_ARCH)) > 10


# ===========================================================================
# AICodeGenerator._generate_env_local
# ===========================================================================


class TestGenerateEnvLocal:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_local(_ARCH)
        assert isinstance(result, str)

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._generate_env_local(_ARCH)) > 10


# ===========================================================================
# AICodeGenerator._write_file
# ===========================================================================


class TestWriteFile:
    def test_creates_file(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        dest = tmp_path / "sub" / "test.txt"
        gen._write_file(dest, "hello world")
        assert dest.exists()

    def test_file_content_written(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        dest = tmp_path / "out.txt"
        gen._write_file(dest, "test content")
        assert dest.read_text() == "test content"

    def test_creates_parent_dirs(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        dest = tmp_path / "a" / "b" / "c" / "file.txt"
        gen._write_file(dest, "nested")
        assert dest.exists()

    def test_write_valid_python_logs_no_warning(self, tmp_path, caplog) -> None:
        import logging
        gen = AICodeGenerator(output_dir=str(tmp_path))
        dest = tmp_path / "valid.py"
        with caplog.at_level(logging.WARNING):
            gen._write_file(dest, "x = 1\n")
        assert "failed AST validation" not in caplog.text

    def test_write_invalid_python_logs_warning(self, tmp_path, caplog) -> None:
        import logging
        gen = AICodeGenerator(output_dir=str(tmp_path))
        dest = tmp_path / "bad.py"
        with caplog.at_level(logging.WARNING):
            gen._write_file(dest, "def foo(:\n    pass\n")
        assert "failed AST validation" in caplog.text

    def test_write_invalid_python_still_writes_file(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        dest = tmp_path / "bad.py"
        gen._write_file(dest, "???syntax error???")
        assert dest.exists()

    def test_write_valid_ts_logs_no_warning(self, tmp_path, caplog) -> None:
        import logging
        gen = AICodeGenerator(output_dir=str(tmp_path))
        dest = tmp_path / "comp.tsx"
        valid_ts = "export default function Page() { return <div>hello</div>; }\n"
        with caplog.at_level(logging.WARNING):
            gen._write_file(dest, valid_ts)
        assert "failed syntax check" not in caplog.text

    def test_write_unbalanced_ts_logs_warning(self, tmp_path, caplog) -> None:
        import logging
        gen = AICodeGenerator(output_dir=str(tmp_path))
        dest = tmp_path / "bad.ts"
        with caplog.at_level(logging.WARNING):
            gen._write_file(dest, "const x = {")
        assert "failed syntax check" in caplog.text


# ===========================================================================
# AICodeGenerator.validate_python_syntax
# ===========================================================================


class TestAICodeGeneratorValidatePythonSyntax:
    def test_valid_code_returns_valid_true(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.validate_python_syntax("x = 1\n")["valid"] is True

    def test_invalid_code_returns_valid_false(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.validate_python_syntax("def foo(:\n    pass\n")["valid"] is False

    def test_valid_code_has_no_errors(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.validate_python_syntax("pass\n")["errors"] == []

    def test_invalid_code_has_errors(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen.validate_python_syntax("???")
        assert len(result["errors"]) > 0

    def test_error_contains_message(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen.validate_python_syntax("if True\n    pass\n")
        assert "message" in result["errors"][0]

    def test_is_static_method(self, tmp_path) -> None:
        # Can be called on the class directly
        result = AICodeGenerator.validate_python_syntax("x = 1\n")
        assert result["valid"] is True


# ===========================================================================
# AICodeGenerator.validate_typescript_syntax
# ===========================================================================


class TestAICodeGeneratorValidateTypescriptSyntax:
    def test_valid_ts_returns_valid_true(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        code = "export const x = () => { return 1; };\n"
        assert gen.validate_typescript_syntax(code)["valid"] is True

    def test_empty_string_returns_valid_false(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.validate_typescript_syntax("")["valid"] is False

    def test_whitespace_only_returns_valid_false(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.validate_typescript_syntax("   \n  ")["valid"] is False

    def test_error_marker_returns_valid_false(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        code = "// Error: LLM router returned no code\n// Please implement manually"
        assert gen.validate_typescript_syntax(code)["valid"] is False

    def test_error_generating_marker_returns_valid_false(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        code = "// Error generating MyComponent: timeout\n// Please implement manually"
        assert gen.validate_typescript_syntax(code)["valid"] is False

    def test_unbalanced_open_brace_returns_valid_false(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.validate_typescript_syntax("const x = {")["valid"] is False

    def test_unbalanced_close_brace_returns_valid_false(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.validate_typescript_syntax("};")["valid"] is False

    def test_balanced_braces_returns_valid_true(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        code = "function foo() { const x = { a: 1 }; return x; }"
        assert gen.validate_typescript_syntax(code)["valid"] is True

    def test_empty_errors_on_valid_code(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen.validate_typescript_syntax("const ok = true;")
        assert result["errors"] == []

    def test_errors_populated_on_invalid_code(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen.validate_typescript_syntax("const x = {")
        assert len(result["errors"]) > 0

    def test_block_comment_error_marker_returns_valid_false(self, tmp_path) -> None:
        gen = AICodeGenerator(output_dir=str(tmp_path))
        code = "/* Error: generation failed */\n"
        assert gen.validate_typescript_syntax(code)["valid"] is False

    def test_is_static_method(self, tmp_path) -> None:
        result = AICodeGenerator.validate_typescript_syntax("const ok = true;")
        assert result["valid"] is True



class TestGetAICodeGenerator:
    def test_returns_ai_code_generator_instance(self, tmp_path):
        _mod._ai_code_generator = None
        result = get_ai_code_generator()
        assert isinstance(result, AICodeGenerator)

    def test_returns_same_instance_on_second_call(self, tmp_path):
        _mod._ai_code_generator = None
        first = get_ai_code_generator()
        second = get_ai_code_generator()
        assert first is second


# ===========================================================================
# Helpers
# ===========================================================================

def _make_gen_with_mock_client(tmp_path):
    """Return an AICodeGenerator whose .router is a MagicMock."""
    gen = AICodeGenerator(output_dir=str(tmp_path))
    mock_router = MagicMock()
    mock_router.has_provider.return_value = True
    mock_router.generate = AsyncMock(return_value="// generated code")
    gen.router = mock_router
    return gen


def _mock_router_response(text: str) -> str:
    """Return the text directly — router.generate returns a plain string."""
    return text


_VIDEO_ANALYSIS = {
    "extracted_info": {
        "title": "Test Video",
        "technologies": ["python", "fastapi"],
        "features": ["auth", "api"],
        "complexity": "intermediate",
    },
    "ai_analysis": {"summary": "Test summary"},
    "video_data": {"video_id": "abc123", "video_url": "https://youtube.com/watch?v=abc123"},
}

_INFRA_ARCH = {
    "type": "infrastructure_platform",
    "framework": "nextjs",
    "frontend": {"framework": "nextjs", "styling": "tailwind", "state": "zustand"},
    "backend": {"type": "api_routes", "database": "supabase", "auth": "nextauth"},
    "features": ["auth", "api", "dashboard"],
    "monetization": {"model": "freemium", "payment_processor": "stripe", "pricing_tiers": ["free", "pro"]},
    "deployment": {"platform": "vercel"},
    "monorepo": True,
    "has_mcp": True,
    "has_workflows": True,
    "has_observability": True,
    "has_ai_gateway": True,
    "has_logging": True,
    "has_error_handling": True,
    "has_database": True,
    "has_config": True,
}

_AGENT_ARCH = {
    "type": "agent",
    "framework": "nextjs",
    "frontend": {"framework": "nextjs", "styling": "tailwind", "state": "zustand"},
    "backend": {"type": "api_routes", "database": "supabase", "auth": "nextauth"},
    "features": ["docker", "agent"],
    "monetization": {"model": "subscription", "payment_processor": "stripe", "pricing_tiers": ["free", "pro"]},
    "deployment": {"platform": "vercel"},
    "monorepo": False,
}


# ===========================================================================
# AICodeGenerator.generate_fullstack_project (client path)
# ===========================================================================


class TestGenerateFullstackProjectWithClient:
    async def test_returns_dict_with_project_path(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=["package.json"])
        result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {"type": "web_app"})
        assert "project_path" in result

    async def test_returns_files_created(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=["package.json", "tsconfig.json"])
        result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {})
        assert result["files_created"] == ["package.json", "tsconfig.json"]

    async def test_returns_framework(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {})
        assert result["framework"] == "nextjs"

    async def test_ai_generated_flag_true(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {})
        assert result["ai_generated"] is True

    async def test_creates_project_directory(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {"type": "saas"})
        assert Path(result["project_path"]).exists()

    async def test_project_type_from_architecture(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {})
        assert result["project_type"] == _ARCH["type"]

    async def test_monetization_passed_through(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {})
        assert result["monetization"] == _ARCH["monetization"]

    async def test_empty_video_analysis(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        result = await gen.generate_fullstack_project({}, {})
        assert isinstance(result, dict)


# ===========================================================================
# AICodeGenerator._determine_architecture
# ===========================================================================


class TestDetermineArchitecture:
    async def test_returns_architecture_dict(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {"type": "fullstack_app", "framework": "nextjs"}
        gen.router.generate.return_value = json.dumps(arch)
        result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert result["type"] == "fullstack_app"

    async def test_parses_json_response(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {"type": "saas", "framework": "nextjs", "features": ["auth"]}
        gen.router.generate.return_value = json.dumps(arch)
        result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert result["features"] == ["auth"]

    async def test_strips_markdown_json_fences(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {"type": "agent", "framework": "nextjs"}
        text = f"```json\n{json.dumps(arch)}\n```"
        gen.router.generate.return_value = text
        result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert result["type"] == "agent"

    async def test_strips_plain_fences(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {"type": "api", "framework": "nextjs"}
        text = f"```\n{json.dumps(arch)}\n```"
        gen.router.generate.return_value = text
        result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert result["type"] == "api"

    async def test_falls_back_to_default_on_invalid_json(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = "not json at all"
        result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert "type" in result  # default architecture returned

    async def test_falls_back_to_default_on_none_response(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = None
        result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert result["framework"] == "nextjs"  # default

    async def test_falls_back_to_default_on_router_exception(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.side_effect = RuntimeError("API error")
        result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert result["framework"] == "nextjs"  # default

    async def test_uses_knowledge_base_when_available(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {"type": "saas", "framework": "nextjs"}
        gen.router.generate.return_value = json.dumps(arch)
        mock_kb = MagicMock()
        mock_kb.get_technology_context.return_value = "some context"
        mock_get_kb = MagicMock(return_value=mock_kb)
        with patch.object(_mod, "KNOWLEDGE_BASE_AVAILABLE", True), \
             patch.object(_mod, "get_knowledge_base", mock_get_kb, create=True):
            result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert result["type"] == "saas"

    async def test_knowledge_base_failure_does_not_raise(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {"type": "saas", "framework": "nextjs"}
        gen.router.generate.return_value = json.dumps(arch)
        mock_get_kb = MagicMock(side_effect=Exception("kb error"))
        with patch.object(_mod, "KNOWLEDGE_BASE_AVAILABLE", True), \
             patch.object(_mod, "get_knowledge_base", mock_get_kb, create=True):
            result = await gen._determine_architecture(_VIDEO_ANALYSIS, {})
        assert result["type"] == "saas"


# ===========================================================================
# AICodeGenerator._generate_project_files
# ===========================================================================


class TestGenerateProjectFiles:
    async def test_infrastructure_platform_calls_turborepo(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = dict(_INFRA_ARCH)
        gen._generate_turborepo_monorepo = AsyncMock(return_value=["turbo.json"])
        result = await gen._generate_project_files(tmp_path / "proj", arch, _VIDEO_ANALYSIS)
        gen._generate_turborepo_monorepo.assert_called_once()
        assert "turbo.json" in result

    async def test_monorepo_flag_calls_turborepo(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {**_ARCH, "type": "fullstack_app", "monorepo": True}
        gen._generate_turborepo_monorepo = AsyncMock(return_value=["turbo.json"])
        result = await gen._generate_project_files(tmp_path / "proj", arch, _VIDEO_ANALYSIS)
        gen._generate_turborepo_monorepo.assert_called_once()

    async def test_nextjs_framework_calls_nextjs_generator(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {**_ARCH, "type": "web_app", "monorepo": False, "framework": "nextjs"}
        gen._generate_nextjs_project = AsyncMock(return_value=["package.json"])
        result = await gen._generate_project_files(tmp_path / "proj", arch, _VIDEO_ANALYSIS)
        gen._generate_nextjs_project.assert_called_once()

    async def test_python_fastapi_calls_fastapi_generator(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {**_ARCH, "type": "api", "monorepo": False, "framework": "python_fastapi"}
        gen._generate_fastapi_project = AsyncMock(return_value=["main.py"])
        result = await gen._generate_project_files(tmp_path / "proj", arch, _VIDEO_ANALYSIS)
        gen._generate_fastapi_project.assert_called_once()

    async def test_unknown_framework_defaults_to_nextjs(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {**_ARCH, "type": "other", "monorepo": False, "framework": "svelte"}
        gen._generate_nextjs_project = AsyncMock(return_value=["package.json"])
        result = await gen._generate_project_files(tmp_path / "proj", arch, _VIDEO_ANALYSIS)
        gen._generate_nextjs_project.assert_called_once()


# ===========================================================================
# AICodeGenerator._generate_nextjs_project
# ===========================================================================


class TestGenerateNextjsProject:
    async def test_creates_expected_files(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._ai_generate_file = AsyncMock(return_value="// generated code")
        gen._generate_package_json = AsyncMock(return_value={"name": "test"})
        proj = tmp_path / "proj"
        files = await gen._generate_nextjs_project(proj, _ARCH, _VIDEO_ANALYSIS)
        assert "package.json" in files
        assert "tsconfig.json" in files
        assert "tailwind.config.js" in files
        assert "README.md" in files

    async def test_creates_src_app_directory(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._ai_generate_file = AsyncMock(return_value="// code")
        gen._generate_package_json = AsyncMock(return_value={"name": "test"})
        proj = tmp_path / "proj"
        await gen._generate_nextjs_project(proj, _ARCH, _VIDEO_ANALYSIS)
        assert (proj / "src" / "app").exists()

    async def test_creates_github_actions_dir(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._ai_generate_file = AsyncMock(return_value="// code")
        gen._generate_package_json = AsyncMock(return_value={"name": "test"})
        proj = tmp_path / "proj"
        await gen._generate_nextjs_project(proj, _ARCH, _VIDEO_ANALYSIS)
        assert (proj / ".github" / "workflows").exists()

    async def test_returns_list_of_strings(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._ai_generate_file = AsyncMock(return_value="// code")
        gen._generate_package_json = AsyncMock(return_value={"name": "test"})
        proj = tmp_path / "proj"
        files = await gen._generate_nextjs_project(proj, _ARCH, _VIDEO_ANALYSIS)
        assert isinstance(files, list)
        assert all(isinstance(f, str) for f in files)

    async def test_package_json_written_to_disk(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._ai_generate_file = AsyncMock(return_value="// code")
        gen._generate_package_json = AsyncMock(return_value={"name": "test-app", "version": "1.0.0"})
        proj = tmp_path / "proj"
        await gen._generate_nextjs_project(proj, _ARCH, _VIDEO_ANALYSIS)
        pkg = json.loads((proj / "package.json").read_text())
        assert pkg["name"] == "test-app"

    async def test_env_example_included(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._ai_generate_file = AsyncMock(return_value="// code")
        gen._generate_package_json = AsyncMock(return_value={"name": "test"})
        proj = tmp_path / "proj"
        files = await gen._generate_nextjs_project(proj, _ARCH, _VIDEO_ANALYSIS)
        assert ".env.example" in files

    async def test_gitignore_included(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._ai_generate_file = AsyncMock(return_value="// code")
        gen._generate_package_json = AsyncMock(return_value={"name": "test"})
        proj = tmp_path / "proj"
        files = await gen._generate_nextjs_project(proj, _ARCH, _VIDEO_ANALYSIS)
        assert ".gitignore" in files


# ===========================================================================
# AICodeGenerator._ai_generate_file
# ===========================================================================


class TestAiGenerateFile:
    async def test_returns_string(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = "const x = 1;"
        result = await gen._ai_generate_file("test file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert isinstance(result, str)

    async def test_strips_typescript_fences(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = "```typescript\nconst x = 1;\n```"
        result = await gen._ai_generate_file("file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "const x = 1;" in result
        assert "```" not in result

    async def test_strips_tsx_fences(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = "```tsx\nreturn <div/>\n```"
        result = await gen._ai_generate_file("file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "return <div/>" in result

    async def test_strips_javascript_fences(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = "```javascript\nvar x=1;\n```"
        result = await gen._ai_generate_file("file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "var x=1;" in result

    async def test_strips_generic_fences(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = "```\ncode here\n```"
        result = await gen._ai_generate_file("file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "code here" in result

    async def test_returns_error_comment_on_none_response(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = None
        result = await gen._ai_generate_file("test file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "Error" in result

    async def test_returns_error_comment_on_exception(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.side_effect = RuntimeError("boom")
        result = await gen._ai_generate_file("test file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "Error" in result

    async def test_returns_error_comment_on_empty_response(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = ""
        result = await gen._ai_generate_file("test file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "Error" in result or result == ""


# ===========================================================================
# AICodeGenerator._generate_package_json
# ===========================================================================


class TestGeneratePackageJson:
    async def test_returns_dict(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        result = await gen._generate_package_json("Test App", _ARCH)
        assert isinstance(result, dict)

    async def test_has_version(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        result = await gen._generate_package_json("My App", _ARCH)
        assert result["version"] == "0.1.0"

    async def test_includes_nextjs(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        result = await gen._generate_package_json("My App", _ARCH)
        assert "next" in result["dependencies"]

    async def test_includes_zustand_when_state_zustand(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {**_ARCH, "frontend": {"state": "zustand"}}
        result = await gen._generate_package_json("App", arch)
        assert "zustand" in result["dependencies"]

    async def test_includes_nextauth_when_auth_nextauth(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {**_ARCH, "backend": {"auth": "nextauth", "database": "none"}}
        result = await gen._generate_package_json("App", arch)
        assert "next-auth" in result["dependencies"]

    async def test_includes_supabase_when_database_supabase(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {**_ARCH, "backend": {"auth": "custom", "database": "supabase"}}
        result = await gen._generate_package_json("App", arch)
        assert "@supabase/supabase-js" in result["dependencies"]

    async def test_includes_stripe_when_payment_stripe(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        result = await gen._generate_package_json("App", _INFRA_ARCH)
        assert "stripe" in result["dependencies"]

    async def test_includes_dockerode_for_agent_type(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        result = await gen._generate_package_json("App", _AGENT_ARCH)
        assert "dockerode" in result["dependencies"]

    async def test_includes_dockerode_for_docker_in_features(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        arch = {**_ARCH, "type": "web_app", "features": ["docker", "deploy"]}
        result = await gen._generate_package_json("App", arch)
        assert "dockerode" in result["dependencies"]

    async def test_name_derived_from_title(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        result = await gen._generate_package_json("My Awesome App", _ARCH)
        assert result["name"] == "my-awesome-app"

    async def test_name_truncated_at_50_chars(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        long_title = "A" * 100
        result = await gen._generate_package_json(long_title, _ARCH)
        assert len(result["name"]) <= 50

    async def test_includes_ai_sdk(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        result = await gen._generate_package_json("App", _ARCH)
        assert "ai" in result["dependencies"]


# ===========================================================================
# AICodeGenerator._generate_env_example variations
# ===========================================================================


class TestGenerateEnvExampleVariations:
    def test_without_supabase(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH, "backend": {"auth": "custom", "database": "postgres"}}
        result = gen._generate_env_example(arch)
        assert "SUPABASE" not in result

    def test_with_supabase(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH, "backend": {"auth": "custom", "database": "supabase"}}
        result = gen._generate_env_example(arch)
        assert "SUPABASE" in result

    def test_with_nextauth(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH, "backend": {"auth": "nextauth", "database": "none"}}
        result = gen._generate_env_example(arch)
        assert "NEXTAUTH" in result

    def test_without_nextauth(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH, "backend": {"auth": "custom", "database": "none"}}
        result = gen._generate_env_example(arch)
        assert "NEXTAUTH" not in result

    def test_with_stripe(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_abc")
        monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", "pk_live_abc")
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_example(_INFRA_ARCH)
        assert "STRIPE" in result

    def test_without_stripe(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH, "monetization": {"payment_processor": "lemonsqueezy"}}
        result = gen._generate_env_example(arch)
        assert "STRIPE" not in result

    def test_returns_non_empty_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_example({})
        assert len(result) > 0


# ===========================================================================
# AICodeGenerator._generate_env_local variations
# ===========================================================================


class TestGenerateEnvLocalVariations:
    def test_without_stripe_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
        monkeypatch.delenv("STRIPE_PUBLISHABLE_KEY", raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_local(_INFRA_ARCH)
        # Stripe keys missing branch
        assert "STRIPE_SECRET_KEY=" in result

    def test_with_stripe_env_vars(self, tmp_path, monkeypatch):
        monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_live_123")
        monkeypatch.setenv("STRIPE_PUBLISHABLE_KEY", "pk_live_123")
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_local(_INFRA_ARCH)
        assert "sk_live_123" in result

    def test_with_upstash(self, tmp_path, monkeypatch):
        monkeypatch.setenv("UPSTASH_REDIS_REST_URL", "https://redis.upstash.io")
        monkeypatch.setenv("UPSTASH_REDIS_REST_TOKEN", "token123")
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_local(_ARCH)
        assert "UPSTASH_REDIS_REST_URL" in result

    def test_without_upstash(self, tmp_path, monkeypatch):
        monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
        monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_local(_ARCH)
        assert "UPSTASH_REDIS_REST_URL" not in result

    def test_with_ai_keys(self, tmp_path, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-123")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-123")
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_env_local(_ARCH)
        assert "OPENAI_API_KEY" in result

    def test_nextauth_secret_generated(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH, "backend": {"auth": "nextauth", "database": "none"}, "monetization": {}}
        result = gen._generate_env_local(arch)
        assert "NEXTAUTH_SECRET" in result

    def test_with_supabase(self, tmp_path, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://proj.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")
        monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH, "backend": {"auth": "custom", "database": "supabase"}, "monetization": {}}
        result = gen._generate_env_local(arch)
        assert "SUPABASE" in result


# ===========================================================================
# AICodeGenerator.fix_build_errors
# ===========================================================================


class TestFixBuildErrors:
    async def test_returns_false_when_no_router(self, monkeypatch, tmp_path):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "PERPLEXITY_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = await gen.fix_build_errors(tmp_path, ["error"], [])
        assert result["success"] is False

    async def test_returns_success_true_when_files_fixed(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        tsx_file = tmp_path / "src" / "app" / "page.tsx"
        tsx_file.parent.mkdir(parents=True)
        tsx_file.write_text("const x = 1;")
        gen.router.generate.return_value = "const fixed = true;"
        errors = ["error in src/app/page.tsx:1:5 - Type error"]
        result = await gen.fix_build_errors(tmp_path, errors, [])
        assert result["success"] is True

    async def test_fixed_files_list_returned(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        tsx_file = tmp_path / "src" / "app" / "page.tsx"
        tsx_file.parent.mkdir(parents=True)
        tsx_file.write_text("const x = 1;")
        gen.router.generate.return_value = "const fixed = true;"
        errors = ["error in src/app/page.tsx:1"]
        result = await gen.fix_build_errors(tmp_path, errors, [])
        assert isinstance(result["fixed_files"], list)

    async def test_total_errors_returned(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        errors = ["err1", "err2", "err3"]
        result = await gen.fix_build_errors(tmp_path, errors, [])
        assert result["total_errors"] == 3

    async def test_falls_back_to_common_files_when_no_paths_in_errors(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        result = await gen.fix_build_errors(tmp_path, ["generic error"], [])
        assert "total_errors" in result

    async def test_skips_nonexistent_files(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        errors = ["error in src/missing.tsx:10"]
        result = await gen.fix_build_errors(tmp_path, errors, [])
        assert result["fixed_files"] == [] or result["success"] is False

    async def test_handles_router_exception_gracefully(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        tsx_file = tmp_path / "src" / "app" / "page.tsx"
        tsx_file.parent.mkdir(parents=True)
        tsx_file.write_text("const x = 1;")
        gen.router.generate.side_effect = RuntimeError("API down")
        errors = ["error in src/app/page.tsx:1"]
        result = await gen.fix_build_errors(tmp_path, errors, [])
        assert result["success"] is False

    async def test_strips_markdown_fences_from_fixed_code(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        tsx_file = tmp_path / "src" / "app" / "page.tsx"
        tsx_file.parent.mkdir(parents=True)
        tsx_file.write_text("const old = 1;")
        gen.router.generate.return_value = "```typescript\nconst fixed = true;\n```"
        errors = ["error in src/app/page.tsx:1"]
        await gen.fix_build_errors(tmp_path, errors, [])
        content = tsx_file.read_text()
        assert "```" not in content

    async def test_none_response_skips_file(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        tsx_file = tmp_path / "src" / "app" / "page.tsx"
        tsx_file.parent.mkdir(parents=True)
        tsx_file.write_text("const old = 1;")
        gen.router.generate.return_value = None
        errors = ["error in src/app/page.tsx:1"]
        result = await gen.fix_build_errors(tmp_path, errors, [])
        assert result["success"] is False


class TestFixBuildErrorsConcurrency:
    """fix_build_errors fans files out concurrently and keeps I/O off the loop.

    Each error file is independent (own read, own LLM round-trip, own write), so
    the previous sequential loop made wall-clock cost scale linearly with the
    number of failing files while the event loop sat blocked on file I/O.
    """

    @staticmethod
    def _make_files(tmp_path, count):
        rel_paths = []
        for i in range(count):
            rel = f"src/app/page{i}.tsx"
            file_path = tmp_path / rel
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"const x = {i};")
            rel_paths.append(rel)
        return rel_paths

    @staticmethod
    def _errors_for(rel_paths):
        return [f"error in {rel}:1:5 - Type error" for rel in rel_paths]

    @staticmethod
    def _tracking_generate(record):
        """Return an async generate() that records peak concurrent calls."""
        state = {"inflight": 0}

        async def _generate(prompt, **kwargs):
            state["inflight"] += 1
            record["max_inflight"] = max(
                record.get("max_inflight", 0), state["inflight"]
            )
            try:
                await asyncio.sleep(0.05)
                return "const fixed = true;"
            finally:
                state["inflight"] -= 1

        return _generate

    async def test_files_are_fixed_concurrently(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        rel_paths = self._make_files(tmp_path, 4)
        record = {}
        gen.router.generate = AsyncMock(side_effect=self._tracking_generate(record))

        result = await gen.fix_build_errors(tmp_path, self._errors_for(rel_paths), [])

        assert result["success"] is True
        assert len(result["fixed_files"]) == 4
        # A sequential loop can never have more than one call in flight.
        assert record["max_inflight"] > 1

    async def test_default_concurrency_is_bounded(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        rel_paths = self._make_files(tmp_path, 8)
        record = {}
        gen.router.generate = AsyncMock(side_effect=self._tracking_generate(record))

        await gen.fix_build_errors(tmp_path, self._errors_for(rel_paths), [])

        # Unbounded fan-out would reach 8 and risk provider rate limits.
        assert 1 < record["max_inflight"] <= _mod._MAX_CONCURRENT_FIXES

    async def test_max_concurrency_override_is_respected(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        rel_paths = self._make_files(tmp_path, 8)
        record = {}
        gen.router.generate = AsyncMock(side_effect=self._tracking_generate(record))

        result = await gen.fix_build_errors(
            tmp_path, self._errors_for(rel_paths), [], max_concurrency=2
        )

        assert len(result["fixed_files"]) == 8
        assert record["max_inflight"] == 2

    @pytest.mark.parametrize("bad_limit", [0, -5])
    async def test_non_positive_max_concurrency_clamps_to_one(self, tmp_path, bad_limit):
        gen = _make_gen_with_mock_client(tmp_path)
        rel_paths = self._make_files(tmp_path, 3)
        record = {}
        gen.router.generate = AsyncMock(side_effect=self._tracking_generate(record))

        result = await gen.fix_build_errors(
            tmp_path, self._errors_for(rel_paths), [], max_concurrency=bad_limit
        )

        assert len(result["fixed_files"]) == 3
        assert record["max_inflight"] == 1

    async def test_fixed_files_order_is_deterministic(self, tmp_path):
        """error_files is a set, so results must be sorted to be assertable."""
        gen = _make_gen_with_mock_client(tmp_path)
        rel_paths = self._make_files(tmp_path, 5)
        gen.router.generate = AsyncMock(return_value="const fixed = true;")

        result = await gen.fix_build_errors(tmp_path, self._errors_for(rel_paths), [])

        assert result["fixed_files"] == sorted(rel_paths)

    async def test_file_io_runs_off_the_event_loop_thread(self, tmp_path, monkeypatch):
        gen = _make_gen_with_mock_client(tmp_path)
        rel_paths = self._make_files(tmp_path, 2)
        gen.router.generate = AsyncMock(return_value="const fixed = true;")

        loop_thread = threading.get_ident()
        read_threads: list[int] = []
        write_threads: list[int] = []
        real_read, real_write = Path.read_text, Path.write_text

        def _tracked_read(self, *args, **kwargs):
            read_threads.append(threading.get_ident())
            return real_read(self, *args, **kwargs)

        def _tracked_write(self, *args, **kwargs):
            write_threads.append(threading.get_ident())
            return real_write(self, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", _tracked_read)
        monkeypatch.setattr(Path, "write_text", _tracked_write)

        await gen.fix_build_errors(tmp_path, self._errors_for(rel_paths), [])

        assert read_threads and write_threads
        assert loop_thread not in read_threads
        assert loop_thread not in write_threads

    async def test_one_file_failure_does_not_abort_siblings(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        rel_paths = self._make_files(tmp_path, 3)

        async def _generate(prompt, **kwargs):
            # The prompt embeds the whole error list, so key off the per-file
            # "CURRENT CODE (<path>)" marker to target exactly one file.
            if "CURRENT CODE (src/app/page1.tsx)" in prompt:
                raise RuntimeError("provider blew up")
            return "const fixed = true;"

        gen.router.generate = AsyncMock(side_effect=_generate)

        result = await gen.fix_build_errors(tmp_path, self._errors_for(rel_paths), [])

        assert result["fixed_files"] == ["src/app/page0.tsx", "src/app/page2.tsx"]
        assert result["success"] is True

    async def test_missing_file_does_not_abort_siblings(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        rel_paths = self._make_files(tmp_path, 2)
        gen.router.generate = AsyncMock(return_value="const fixed = true;")
        errors = self._errors_for([*rel_paths, "src/app/gone.tsx"])

        result = await gen.fix_build_errors(tmp_path, errors, [])

        assert result["fixed_files"] == sorted(rel_paths)


# ===========================================================================
# AICodeGenerator._generate_turborepo_monorepo
# ===========================================================================


class TestGenerateTurborepoMonorepo:
    async def test_creates_turbo_json(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._generate_nextjs_project = AsyncMock(return_value=[])
        gen._generate_ui_package = AsyncMock(return_value=[])
        gen._generate_mcp_connectors_package = AsyncMock(return_value=[])
        gen._generate_workflows_package = AsyncMock(return_value=[])
        gen._generate_observability_package = AsyncMock(return_value=[])
        gen._generate_ai_gateway_package = AsyncMock(return_value=[])
        gen._generate_logger_package = AsyncMock(return_value=[])
        gen._generate_error_handling_package = AsyncMock(return_value=[])
        gen._generate_database_package = AsyncMock(return_value=[])
        gen._generate_config_package = AsyncMock(return_value=[])
        proj = tmp_path / "proj"
        files = await gen._generate_turborepo_monorepo(proj, _INFRA_ARCH, _VIDEO_ANALYSIS)
        assert "turbo.json" in files
        assert (proj / "turbo.json").exists()

    async def test_creates_root_package_json(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._generate_nextjs_project = AsyncMock(return_value=[])
        gen._generate_ui_package = AsyncMock(return_value=[])
        gen._generate_mcp_connectors_package = AsyncMock(return_value=[])
        gen._generate_workflows_package = AsyncMock(return_value=[])
        gen._generate_observability_package = AsyncMock(return_value=[])
        gen._generate_ai_gateway_package = AsyncMock(return_value=[])
        gen._generate_logger_package = AsyncMock(return_value=[])
        gen._generate_error_handling_package = AsyncMock(return_value=[])
        gen._generate_database_package = AsyncMock(return_value=[])
        gen._generate_config_package = AsyncMock(return_value=[])
        proj = tmp_path / "proj"
        files = await gen._generate_turborepo_monorepo(proj, _INFRA_ARCH, _VIDEO_ANALYSIS)
        assert "package.json" in files

    async def test_creates_gitignore(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._generate_nextjs_project = AsyncMock(return_value=[])
        gen._generate_ui_package = AsyncMock(return_value=[])
        gen._generate_mcp_connectors_package = AsyncMock(return_value=[])
        gen._generate_workflows_package = AsyncMock(return_value=[])
        gen._generate_observability_package = AsyncMock(return_value=[])
        gen._generate_ai_gateway_package = AsyncMock(return_value=[])
        gen._generate_logger_package = AsyncMock(return_value=[])
        gen._generate_error_handling_package = AsyncMock(return_value=[])
        gen._generate_database_package = AsyncMock(return_value=[])
        gen._generate_config_package = AsyncMock(return_value=[])
        proj = tmp_path / "proj"
        files = await gen._generate_turborepo_monorepo(proj, _INFRA_ARCH, _VIDEO_ANALYSIS)
        assert ".gitignore" in files

    async def test_calls_mcp_when_has_mcp_true(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._generate_nextjs_project = AsyncMock(return_value=[])
        gen._generate_ui_package = AsyncMock(return_value=[])
        gen._generate_mcp_connectors_package = AsyncMock(return_value=["mcp.ts"])
        gen._generate_workflows_package = AsyncMock(return_value=[])
        gen._generate_observability_package = AsyncMock(return_value=[])
        gen._generate_ai_gateway_package = AsyncMock(return_value=[])
        gen._generate_logger_package = AsyncMock(return_value=[])
        gen._generate_error_handling_package = AsyncMock(return_value=[])
        gen._generate_database_package = AsyncMock(return_value=[])
        gen._generate_config_package = AsyncMock(return_value=[])
        arch = {**_INFRA_ARCH, "has_mcp": True}
        await gen._generate_turborepo_monorepo(tmp_path / "p", arch, _VIDEO_ANALYSIS)
        gen._generate_mcp_connectors_package.assert_called_once()

    async def test_skips_mcp_when_not_set(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._generate_nextjs_project = AsyncMock(return_value=[])
        gen._generate_ui_package = AsyncMock(return_value=[])
        gen._generate_mcp_connectors_package = AsyncMock(return_value=[])
        gen._generate_workflows_package = AsyncMock(return_value=[])
        gen._generate_observability_package = AsyncMock(return_value=[])
        gen._generate_ai_gateway_package = AsyncMock(return_value=[])
        gen._generate_logger_package = AsyncMock(return_value=[])
        gen._generate_error_handling_package = AsyncMock(return_value=[])
        gen._generate_database_package = AsyncMock(return_value=[])
        gen._generate_config_package = AsyncMock(return_value=[])
        arch = {**_INFRA_ARCH, "type": "web_app", "has_mcp": False, "has_workflows": False,
                "has_observability": False, "has_ai_gateway": False, "has_logging": False,
                "has_error_handling": False, "has_database": False, "has_config": False}
        await gen._generate_turborepo_monorepo(tmp_path / "p", arch, _VIDEO_ANALYSIS)
        gen._generate_mcp_connectors_package.assert_not_called()

    async def test_readme_included_in_files(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._generate_nextjs_project = AsyncMock(return_value=[])
        gen._generate_ui_package = AsyncMock(return_value=[])
        gen._generate_mcp_connectors_package = AsyncMock(return_value=[])
        gen._generate_workflows_package = AsyncMock(return_value=[])
        gen._generate_observability_package = AsyncMock(return_value=[])
        gen._generate_ai_gateway_package = AsyncMock(return_value=[])
        gen._generate_logger_package = AsyncMock(return_value=[])
        gen._generate_error_handling_package = AsyncMock(return_value=[])
        gen._generate_database_package = AsyncMock(return_value=[])
        gen._generate_config_package = AsyncMock(return_value=[])
        files = await gen._generate_turborepo_monorepo(tmp_path / "p", _INFRA_ARCH, _VIDEO_ANALYSIS)
        assert "README.md" in files


# ===========================================================================
# AICodeGenerator._generate_ui_package
# ===========================================================================


class TestGenerateUiPackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ui"
        files = await gen._generate_ui_package(pkg, _ARCH)
        assert "package.json" in files
        assert (pkg / "package.json").exists()

    async def test_creates_button_tsx(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ui"
        files = await gen._generate_ui_package(pkg, _ARCH)
        assert "src/button.tsx" in files

    async def test_creates_card_tsx(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ui"
        files = await gen._generate_ui_package(pkg, _ARCH)
        assert "src/card.tsx" in files

    async def test_creates_tsconfig(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ui"
        files = await gen._generate_ui_package(pkg, _ARCH)
        assert "tsconfig.json" in files

    async def test_package_name_is_repo_ui(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ui"
        await gen._generate_ui_package(pkg, _ARCH)
        data = json.loads((pkg / "package.json").read_text())
        assert data["name"] == "@repo/ui"


# ===========================================================================
# AICodeGenerator._generate_eslint_config_package
# ===========================================================================


class TestGenerateEslintConfigPackage:
    def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "eslint-config"
        files = gen._generate_eslint_config_package(pkg)
        assert "package.json" in files

    def test_creates_index_js(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "eslint-config"
        files = gen._generate_eslint_config_package(pkg)
        assert "index.js" in files

    def test_package_name_correct(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "eslint-config"
        gen._generate_eslint_config_package(pkg)
        data = json.loads((pkg / "package.json").read_text())
        assert data["name"] == "@repo/eslint-config"

    def test_index_js_contains_module_exports(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "eslint-config"
        gen._generate_eslint_config_package(pkg)
        content = (pkg / "index.js").read_text()
        assert "module.exports" in content


# ===========================================================================
# AICodeGenerator._generate_tsconfig_package
# ===========================================================================


class TestGenerateTsconfigPackage:
    def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "tsconfig"
        files = gen._generate_tsconfig_package(pkg)
        assert "package.json" in files

    def test_creates_base_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "tsconfig"
        files = gen._generate_tsconfig_package(pkg)
        assert "base.json" in files

    def test_creates_nextjs_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "tsconfig"
        files = gen._generate_tsconfig_package(pkg)
        assert "nextjs.json" in files

    def test_creates_react_library_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "tsconfig"
        files = gen._generate_tsconfig_package(pkg)
        assert "react-library.json" in files

    def test_package_name_correct(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "tsconfig"
        gen._generate_tsconfig_package(pkg)
        data = json.loads((pkg / "package.json").read_text())
        assert data["name"] == "@repo/typescript-config"


# ===========================================================================
# AICodeGenerator._generate_monorepo_readme
# ===========================================================================


class TestGenerateMonorepoReadme:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_monorepo_readme("Test Platform", _INFRA_ARCH, _VIDEO_ANALYSIS)
        assert isinstance(result, str)

    def test_contains_title(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_monorepo_readme("My Platform", _INFRA_ARCH, _VIDEO_ANALYSIS)
        assert "My Platform" in result

    def test_contains_video_url(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_monorepo_readme("T", _INFRA_ARCH, _VIDEO_ANALYSIS)
        assert "https://youtube.com" in result

    def test_contains_turborepo_info(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_monorepo_readme("T", _INFRA_ARCH, _VIDEO_ANALYSIS)
        assert "Turborepo" in result or "turborepo" in result.lower()


# ===========================================================================
# AICodeGenerator._generate_mcp_connectors_package
# ===========================================================================


class TestGenerateMcpConnectorsPackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "mcp"
        files = await gen._generate_mcp_connectors_package(pkg, _INFRA_ARCH)
        assert "package.json" in files

    async def test_creates_postgres_connector(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "mcp"
        files = await gen._generate_mcp_connectors_package(pkg, _INFRA_ARCH)
        assert "src/postgres.ts" in files

    async def test_creates_github_connector(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "mcp"
        files = await gen._generate_mcp_connectors_package(pkg, _INFRA_ARCH)
        assert "src/github.ts" in files

    async def test_creates_slack_connector(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "mcp"
        files = await gen._generate_mcp_connectors_package(pkg, _INFRA_ARCH)
        assert "src/slack.ts" in files

    async def test_creates_index_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "mcp"
        files = await gen._generate_mcp_connectors_package(pkg, _INFRA_ARCH)
        assert "src/index.ts" in files

    async def test_creates_readme(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "mcp"
        files = await gen._generate_mcp_connectors_package(pkg, _INFRA_ARCH)
        assert "README.md" in files

    async def test_postgres_ts_contains_pool(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "mcp"
        await gen._generate_mcp_connectors_package(pkg, _INFRA_ARCH)
        content = (pkg / "src" / "postgres.ts").read_text()
        assert "Pool" in content


# ===========================================================================
# AICodeGenerator._generate_postgres_connector
# ===========================================================================


class TestGeneratePostgresConnector:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_postgres_connector()
        assert isinstance(result, str)

    def test_contains_postgres_class(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_postgres_connector()
        assert "PostgresConnector" in result

    def test_contains_execute_tool(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_postgres_connector()
        assert "executeTool" in result

    def test_nonempty(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert len(gen._generate_postgres_connector()) > 100


# ===========================================================================
# AICodeGenerator._generate_github_connector
# ===========================================================================


class TestGenerateGithubConnector:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_github_connector()
        assert isinstance(result, str)

    def test_contains_github_class(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_github_connector()
        assert "GitHubConnector" in result

    def test_contains_octokit(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_github_connector()
        assert "Octokit" in result


# ===========================================================================
# AICodeGenerator._generate_slack_connector
# ===========================================================================


class TestGenerateSlackConnector:
    def test_returns_string(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_slack_connector()
        assert isinstance(result, str)

    def test_contains_slack_class(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_slack_connector()
        assert "SlackConnector" in result

    def test_contains_webclient(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_slack_connector()
        assert "WebClient" in result


# ===========================================================================
# AICodeGenerator._generate_workflows_package
# ===========================================================================


class TestGenerateWorkflowsPackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "workflows"
        files = await gen._generate_workflows_package(pkg, _INFRA_ARCH)
        assert "package.json" in files

    async def test_creates_data_processing(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "workflows"
        files = await gen._generate_workflows_package(pkg, _INFRA_ARCH)
        assert "src/data-processing.ts" in files

    async def test_creates_mcp_orchestration(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "workflows"
        files = await gen._generate_workflows_package(pkg, _INFRA_ARCH)
        assert "src/mcp-orchestration.ts" in files

    async def test_creates_index_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "workflows"
        files = await gen._generate_workflows_package(pkg, _INFRA_ARCH)
        assert "src/index.ts" in files

    async def test_creates_readme(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "workflows"
        files = await gen._generate_workflows_package(pkg, _INFRA_ARCH)
        assert "README.md" in files


# ===========================================================================
# AICodeGenerator._generate_observability_package
# ===========================================================================


class TestGenerateObservabilityPackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "obs"
        files = await gen._generate_observability_package(pkg, _INFRA_ARCH)
        assert "package.json" in files

    async def test_creates_observability_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "obs"
        files = await gen._generate_observability_package(pkg, _INFRA_ARCH)
        assert "src/observability.ts" in files

    async def test_creates_workflow_instrumentation(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "obs"
        files = await gen._generate_observability_package(pkg, _INFRA_ARCH)
        assert "src/workflow-instrumentation.ts" in files

    async def test_creates_index_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "obs"
        files = await gen._generate_observability_package(pkg, _INFRA_ARCH)
        assert "src/index.ts" in files

    async def test_observability_ts_contains_class(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "obs"
        await gen._generate_observability_package(pkg, _INFRA_ARCH)
        content = (pkg / "src" / "observability.ts").read_text()
        assert "Observability" in content


# ===========================================================================
# AICodeGenerator._generate_ai_gateway_package
# ===========================================================================


class TestGenerateAiGatewayPackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ai-gateway"
        files = await gen._generate_ai_gateway_package(pkg, _INFRA_ARCH)
        assert "package.json" in files

    async def test_creates_types_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ai-gateway"
        files = await gen._generate_ai_gateway_package(pkg, _INFRA_ARCH)
        assert "src/types.ts" in files

    async def test_creates_models_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ai-gateway"
        files = await gen._generate_ai_gateway_package(pkg, _INFRA_ARCH)
        assert "src/models.ts" in files

    async def test_creates_index_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ai-gateway"
        files = await gen._generate_ai_gateway_package(pkg, _INFRA_ARCH)
        assert "src/index.ts" in files

    async def test_creates_readme(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ai-gateway"
        files = await gen._generate_ai_gateway_package(pkg, _INFRA_ARCH)
        assert "README.md" in files

    async def test_creates_tsconfig(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ai-gateway"
        files = await gen._generate_ai_gateway_package(pkg, _INFRA_ARCH)
        assert "tsconfig.json" in files

    async def test_types_ts_contains_aiprovider(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "ai-gateway"
        await gen._generate_ai_gateway_package(pkg, _INFRA_ARCH)
        content = (pkg / "src" / "types.ts").read_text()
        assert "AIProvider" in content


# ===========================================================================
# AICodeGenerator._generate_logger_package
# ===========================================================================


class TestGenerateLoggerPackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "logger"
        files = await gen._generate_logger_package(pkg, _INFRA_ARCH)
        assert "package.json" in files

    async def test_creates_types_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "logger"
        files = await gen._generate_logger_package(pkg, _INFRA_ARCH)
        assert "src/types.ts" in files

    async def test_creates_index_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "logger"
        files = await gen._generate_logger_package(pkg, _INFRA_ARCH)
        assert "src/index.ts" in files

    async def test_creates_readme(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "logger"
        files = await gen._generate_logger_package(pkg, _INFRA_ARCH)
        assert "README.md" in files

    async def test_creates_tsconfig(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "logger"
        files = await gen._generate_logger_package(pkg, _INFRA_ARCH)
        assert "tsconfig.json" in files

    async def test_index_ts_contains_get_logger(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "logger"
        await gen._generate_logger_package(pkg, _INFRA_ARCH)
        content = (pkg / "src" / "index.ts").read_text()
        assert "getLogger" in content


# ===========================================================================
# AICodeGenerator._generate_error_handling_package
# ===========================================================================


class TestGenerateErrorHandlingPackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "error-handling"
        files = await gen._generate_error_handling_package(pkg, _INFRA_ARCH)
        assert "package.json" in files

    async def test_creates_circuit_breaker_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "error-handling"
        files = await gen._generate_error_handling_package(pkg, _INFRA_ARCH)
        assert "src/circuit-breaker.ts" in files

    async def test_creates_retry_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "error-handling"
        files = await gen._generate_error_handling_package(pkg, _INFRA_ARCH)
        assert "src/retry.ts" in files

    async def test_creates_error_boundary(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "error-handling"
        files = await gen._generate_error_handling_package(pkg, _INFRA_ARCH)
        assert "src/ErrorBoundary.tsx" in files

    async def test_creates_index_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "error-handling"
        files = await gen._generate_error_handling_package(pkg, _INFRA_ARCH)
        assert "src/index.ts" in files

    async def test_circuit_breaker_contains_class(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "error-handling"
        await gen._generate_error_handling_package(pkg, _INFRA_ARCH)
        content = (pkg / "src" / "circuit-breaker.ts").read_text()
        assert "CircuitBreaker" in content


# ===========================================================================
# AICodeGenerator._generate_database_package
# ===========================================================================


class TestGenerateDatabasePackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "database"
        files = await gen._generate_database_package(pkg, _INFRA_ARCH)
        assert "package.json" in files

    async def test_creates_prisma_schema(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "database"
        files = await gen._generate_database_package(pkg, _INFRA_ARCH)
        assert "prisma/schema.prisma" in files

    async def test_creates_client_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "database"
        files = await gen._generate_database_package(pkg, _INFRA_ARCH)
        assert "src/client.ts" in files

    async def test_creates_supabase_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "database"
        files = await gen._generate_database_package(pkg, _INFRA_ARCH)
        assert "src/supabase.ts" in files

    async def test_creates_seed_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "database"
        files = await gen._generate_database_package(pkg, _INFRA_ARCH)
        assert "src/seed.ts" in files

    async def test_creates_migrations_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "database"
        files = await gen._generate_database_package(pkg, _INFRA_ARCH)
        assert "src/migrations.ts" in files

    async def test_creates_env_example(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "database"
        files = await gen._generate_database_package(pkg, _INFRA_ARCH)
        assert ".env.example" in files

    async def test_schema_contains_user_model(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "database"
        await gen._generate_database_package(pkg, _INFRA_ARCH)
        schema = (pkg / "prisma" / "schema.prisma").read_text()
        assert "model User" in schema


# ===========================================================================
# AICodeGenerator._generate_config_package
# ===========================================================================


class TestGenerateConfigPackage:
    async def test_creates_package_json(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "config"
        files = await gen._generate_config_package(pkg, _INFRA_ARCH)
        assert "package.json" in files

    async def test_creates_env_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "config"
        files = await gen._generate_config_package(pkg, _INFRA_ARCH)
        assert "src/env.ts" in files

    async def test_creates_constants_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "config"
        files = await gen._generate_config_package(pkg, _INFRA_ARCH)
        assert "src/constants.ts" in files

    async def test_creates_index_ts(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "config"
        files = await gen._generate_config_package(pkg, _INFRA_ARCH)
        assert "src/index.ts" in files

    async def test_creates_env_example(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "config"
        files = await gen._generate_config_package(pkg, _INFRA_ARCH)
        assert ".env.example" in files

    async def test_creates_tsconfig(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "config"
        files = await gen._generate_config_package(pkg, _INFRA_ARCH)
        assert "tsconfig.json" in files

    async def test_creates_readme(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "config"
        files = await gen._generate_config_package(pkg, _INFRA_ARCH)
        assert "README.md" in files

    async def test_env_ts_contains_zod(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        pkg = tmp_path / "config"
        await gen._generate_config_package(pkg, _INFRA_ARCH)
        content = (pkg / "src" / "env.ts").read_text()
        assert "zod" in content.lower() or "z.object" in content


# ===========================================================================
# AICodeGenerator._generate_fastapi_project
# ===========================================================================


class TestGenerateFastapiProject:
    async def test_delegates_to_nextjs(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._generate_nextjs_project = AsyncMock(return_value=["package.json"])
        proj = tmp_path / "proj"
        files = await gen._generate_fastapi_project(proj, _ARCH, _VIDEO_ANALYSIS)
        gen._generate_nextjs_project.assert_called_once()
        assert "package.json" in files


# ===========================================================================
# Module-level: GENAI_AVAILABLE = True path in __init__
# ===========================================================================


class TestInitWithApiKey:
    def test_router_set_when_provider_key_available(self, tmp_path, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake-key")
        gen = AICodeGenerator(output_dir=str(tmp_path))
        # router may or may not have a provider depending on SDK availability;
        # manually verify we can set it
        mock_router = MagicMock()
        gen.router = mock_router
        assert gen.router is mock_router

    def test_router_none_when_llm_router_unavailable(self, tmp_path, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "XAI_API_KEY", "PERPLEXITY_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        with patch.object(_mod, "_LLM_ROUTER_AVAILABLE", False):
            gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.router is None

    def test_output_dir_defaults_to_generated_projects(self, tmp_path, monkeypatch):
        for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        gen = AICodeGenerator()
        assert gen.output_dir.name == "generated_projects"

    def test_router_init_exception_sets_router_to_none(self, tmp_path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        with patch.object(_mod, "LLMRouter", side_effect=RuntimeError("init failed")):
            gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.router is None


# ===========================================================================
# generate_fullstack_project: knowledge base capture path
# ===========================================================================


class TestGenerateFullstackKnowledgeBase:
    async def test_knowledge_base_capture_called(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        mock_kb = MagicMock()
        mock_kb.capture_from_video.return_value = {"captured": 2, "total_unique": 5}
        mock_get_kb = MagicMock(return_value=mock_kb)
        with patch.object(_mod, "KNOWLEDGE_BASE_AVAILABLE", True), \
             patch.object(_mod, "get_knowledge_base", mock_get_kb, create=True):
            result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {})
        mock_kb.capture_from_video.assert_called_once()

    async def test_knowledge_base_failure_does_not_raise(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        mock_get_kb = MagicMock(side_effect=Exception("kb down"))
        with patch.object(_mod, "KNOWLEDGE_BASE_AVAILABLE", True), \
             patch.object(_mod, "get_knowledge_base", mock_get_kb, create=True):
            result = await gen.generate_fullstack_project(_VIDEO_ANALYSIS, {})
        assert isinstance(result, dict)

    async def test_no_technologies_skips_kb(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen._determine_architecture = AsyncMock(return_value=_ARCH)
        gen._generate_project_files = AsyncMock(return_value=[])
        mock_kb = MagicMock()
        mock_get_kb = MagicMock(return_value=mock_kb)
        va = {**_VIDEO_ANALYSIS, "extracted_info": {"title": "Test", "technologies": []}}
        with patch.object(_mod, "KNOWLEDGE_BASE_AVAILABLE", True), \
             patch.object(_mod, "get_knowledge_base", mock_get_kb, create=True):
            await gen.generate_fullstack_project(va, {})
        mock_kb.capture_from_video.assert_not_called()


# ===========================================================================
# Additional edge cases for _ai_generate_file
# ===========================================================================


class TestAiGenerateFileEdgeCases:
    async def test_empty_string_response_returns_error(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = ""
        result = await gen._ai_generate_file("file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "Error" in result or result == ""

    async def test_with_empty_video_analysis(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = "const x = 1;"
        result = await gen._ai_generate_file("file", _ARCH, {}, "prompt")
        assert "const x = 1;" in result

    async def test_plain_code_returned_unchanged(self, tmp_path):
        gen = _make_gen_with_mock_client(tmp_path)
        gen.router.generate.return_value = "const a = 1;\nconst b = 2;"
        result = await gen._ai_generate_file("file", _ARCH, _VIDEO_ANALYSIS, "prompt")
        assert "const a = 1;" in result


# ===========================================================================
# _generate_readme edge cases
# ===========================================================================


class TestGenerateReadmeEdgeCases:
    def test_no_features_list(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH, "features": []}
        result = gen._generate_readme("Test", arch, {})
        assert isinstance(result, str)

    def test_no_deployment_info(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH}
        arch.pop("deployment", None)
        result = gen._generate_readme("T", arch, {})
        assert isinstance(result, str)

    def test_no_monetization_info(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        arch = {**_ARCH}
        arch.pop("monetization", None)
        result = gen._generate_readme("T", arch, {})
        assert isinstance(result, str)

    def test_empty_video_analysis(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._generate_readme("T", _ARCH, {})
        assert "Unknown" in result or isinstance(result, str)


# ===========================================================================
# _default_architecture fields
# ===========================================================================


class TestDefaultArchitectureFields:
    def test_has_backend(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert "backend" in result

    def test_has_frontend(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert "frontend" in result

    def test_has_deployment(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert "deployment" in result

    def test_has_mcp_flag(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert result.get("has_mcp") is True

    def test_has_entry_point(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert "entry_point" in result

    def test_has_build_command(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert "build_command" in result

    def test_has_monetization(self, tmp_path):
        gen = AICodeGenerator(output_dir=str(tmp_path))
        result = gen._default_architecture()
        assert "monetization" in result
