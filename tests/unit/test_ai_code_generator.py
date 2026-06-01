"""Unit tests for backend/ai_code_generator.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
sys.path.insert(0, str(_SRC))

sys.modules.pop("youtube_extension.backend.ai_code_generator", None)

from youtube_extension.backend.ai_code_generator import AICodeGenerator, get_ai_code_generator
import youtube_extension.backend.ai_code_generator as _mod

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
    def test_init_without_api_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.gemini_api_key is None
        assert gen.client is None

    def test_init_with_custom_output_dir(self, tmp_path):
        custom = tmp_path / "custom_out"
        gen = AICodeGenerator(output_dir=str(custom))
        assert gen.output_dir == custom
        assert custom.exists()

    def test_default_output_dir_created(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path / "out"))
        assert gen.output_dir.exists()

    def test_client_none_without_genai(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        assert gen.client is None


# ===========================================================================
# AICodeGenerator.generate_fullstack_project
# ===========================================================================


class TestGenerateFullstackProject:
    async def test_raises_when_no_client(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        gen = AICodeGenerator(output_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="Gemini API key"):
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


# ===========================================================================
# get_ai_code_generator global function
# ===========================================================================


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
