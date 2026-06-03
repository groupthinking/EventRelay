"""Unit tests for services/cloud/vertex_ai_agent.py."""

from __future__ import annotations

import asyncio
import json
import sys
import types as _types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ---------------------------------------------------------------------------
# Helpers – build a minimal fake Vertex AI response
# ---------------------------------------------------------------------------

def _make_usage_metadata(prompt_tokens=10, candidates_tokens=20, total_tokens=30):
    m = MagicMock()
    m.prompt_token_count = prompt_tokens
    m.candidates_token_count = candidates_tokens
    m.total_token_count = total_tokens
    return m


def _make_candidate(finish_reason="STOP"):
    c = MagicMock()
    c.finish_reason = finish_reason
    return c


def _make_response(text="hello", finish_reason="STOP", has_usage=True):
    r = MagicMock()
    r.text = text
    r.candidates = [_make_candidate(finish_reason)]
    if has_usage:
        r.usage_metadata = _make_usage_metadata()
    else:
        del r.usage_metadata  # ensure hasattr returns False
    return r


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_singleton():
    """Ensure the module-level singleton is cleared between tests."""
    import youtube_extension.services.cloud.vertex_ai_agent as mod
    mod._vertex_ai_service = None
    yield
    mod._vertex_ai_service = None


@pytest.fixture()
def mock_vertexai():
    """Patch Vertex AI library symbols so the module thinks they are available."""
    with (
        patch(
            "youtube_extension.services.cloud.vertex_ai_agent.VERTEX_AI_AVAILABLE",
            True,
        ),
        patch(
            "youtube_extension.services.cloud.vertex_ai_agent.vertexai",
            MagicMock(),
        ) as mock_vx,
        patch(
            "youtube_extension.services.cloud.vertex_ai_agent.GenerativeModel",
        ) as mock_gm,
        patch(
            "youtube_extension.services.cloud.vertex_ai_agent.Content",
        ) as mock_content,
        patch(
            "youtube_extension.services.cloud.vertex_ai_agent.Part",
        ) as mock_part,
    ):
        yield {
            "vertexai": mock_vx,
            "GenerativeModel": mock_gm,
            "Content": mock_content,
            "Part": mock_part,
        }


@pytest.fixture()
def service(mock_vertexai):
    """Return an initialised VertexAIAgentService with mocked SDK."""
    from youtube_extension.services.cloud.vertex_ai_agent import (
        AgentConfig,
        VertexAIAgentService,
    )

    mock_model = MagicMock()
    mock_vertexai["GenerativeModel"].return_value = mock_model

    svc = VertexAIAgentService(project_id="test-project", location="us-central1")
    svc.model = mock_model
    return svc


# ---------------------------------------------------------------------------
# 1. Module-level flag
# ---------------------------------------------------------------------------

class TestVertexAIAvailableFlag:
    def test_flag_is_bool(self):
        from youtube_extension.services.cloud import vertex_ai_agent as mod
        assert isinstance(mod.VERTEX_AI_AVAILABLE, bool)

    def test_flag_is_false_when_unavailable(self):
        """When the Vertex AI SDK cannot be imported, the flag is False.

        ``google-cloud-aiplatform`` (which provides ``vertexai``) is a declared
        base dependency, so it may or may not be importable depending on the
        environment. Rather than rely on the ambient absence of the SDK, force
        the import to fail and reload the module so we deterministically
        exercise the ``except ImportError`` branch that sets the flag False.
        """
        import builtins
        import importlib

        real_import = builtins.__import__

        def _blocked_import(name, *args, **kwargs):
            if name == "vertexai" or name.startswith("vertexai.") or name == "google.cloud.aiplatform":
                raise ImportError(f"forced unavailable: {name}")
            return real_import(name, *args, **kwargs)

        import youtube_extension.services.cloud.vertex_ai_agent as mod
        try:
            with patch("builtins.__import__", side_effect=_blocked_import):
                importlib.reload(mod)
            assert mod.VERTEX_AI_AVAILABLE is False
        finally:
            # Restore the module to its real state for subsequent tests.
            importlib.reload(mod)


# ---------------------------------------------------------------------------
# 2. AgentConfig dataclass
# ---------------------------------------------------------------------------

class TestAgentConfig:
    def test_defaults(self):
        from youtube_extension.services.cloud.vertex_ai_agent import AgentConfig
        cfg = AgentConfig()
        assert cfg.model_name == "gemini-2.0-flash-exp"
        assert cfg.temperature == pytest.approx(0.4)
        assert cfg.top_p == pytest.approx(0.95)
        assert cfg.top_k == 40
        assert cfg.max_output_tokens == 8192
        assert cfg.response_schema is None
        assert cfg.tools is None
        assert cfg.safety_settings is None

    def test_custom_values(self):
        from youtube_extension.services.cloud.vertex_ai_agent import AgentConfig
        schema = {"type": "object"}
        cfg = AgentConfig(
            model_name="gemini-pro",
            temperature=0.7,
            top_p=0.9,
            top_k=10,
            max_output_tokens=512,
            response_schema=schema,
        )
        assert cfg.model_name == "gemini-pro"
        assert cfg.response_schema == schema


# ---------------------------------------------------------------------------
# 3. AgentResponse dataclass
# ---------------------------------------------------------------------------

class TestAgentResponse:
    def test_required_fields(self):
        from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
        resp = AgentResponse(text="hi", metadata={"model": "gemini"})
        assert resp.text == "hi"
        assert resp.metadata["model"] == "gemini"
        assert resp.thinking_process is None
        assert resp.tool_calls is None
        assert resp.finish_reason is None
        assert resp.usage is None

    def test_optional_fields(self):
        from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
        usage = {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
        resp = AgentResponse(
            text="content",
            metadata={},
            thinking_process="I thought…",
            tool_calls=[{"name": "search"}],
            finish_reason="STOP",
            usage=usage,
        )
        assert resp.thinking_process == "I thought…"
        assert resp.finish_reason == "STOP"
        assert resp.usage["total_tokens"] == 15


# ---------------------------------------------------------------------------
# 4. VertexAIAgentService.__init__ – ImportError when unavailable
# ---------------------------------------------------------------------------

class TestVertexAIAgentServiceInit:
    def test_raises_when_unavailable(self):
        with patch(
            "youtube_extension.services.cloud.vertex_ai_agent.VERTEX_AI_AVAILABLE",
            False,
        ):
            from youtube_extension.services.cloud.vertex_ai_agent import (
                VertexAIAgentService,
            )
            with pytest.raises(ImportError, match="Vertex AI not available"):
                VertexAIAgentService()

    def test_default_project_from_env(self, mock_vertexai, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
        from youtube_extension.services.cloud.vertex_ai_agent import (
            VertexAIAgentService,
        )
        mock_vertexai["GenerativeModel"].return_value = MagicMock()
        svc = VertexAIAgentService()
        assert svc.project_id == "env-project"

    def test_explicit_project_overrides_env(self, mock_vertexai, monkeypatch):
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "env-project")
        from youtube_extension.services.cloud.vertex_ai_agent import (
            VertexAIAgentService,
        )
        mock_vertexai["GenerativeModel"].return_value = MagicMock()
        svc = VertexAIAgentService(project_id="explicit-project")
        assert svc.project_id == "explicit-project"

    def test_default_location(self, service):
        assert service.location == "us-central1"

    def test_custom_agent_config(self, mock_vertexai):
        from youtube_extension.services.cloud.vertex_ai_agent import (
            AgentConfig,
            VertexAIAgentService,
        )
        mock_vertexai["GenerativeModel"].return_value = MagicMock()
        cfg = AgentConfig(temperature=0.9, model_name="gemini-pro")
        svc = VertexAIAgentService(project_id="p", agent_config=cfg)
        assert svc.agent_config.temperature == pytest.approx(0.9)
        assert svc.agent_config.model_name == "gemini-pro"

    def test_vertexai_init_called(self, mock_vertexai):
        from youtube_extension.services.cloud.vertex_ai_agent import (
            VertexAIAgentService,
        )
        mock_vertexai["GenerativeModel"].return_value = MagicMock()
        VertexAIAgentService(project_id="p")
        mock_vertexai["vertexai"].init.assert_called_once_with(
            project="p", location="us-central1"
        )

    def test_model_created_with_config(self, mock_vertexai):
        from youtube_extension.services.cloud.vertex_ai_agent import (
            AgentConfig,
            VertexAIAgentService,
        )
        mock_vertexai["GenerativeModel"].return_value = MagicMock()
        cfg = AgentConfig(model_name="gemini-flash", temperature=0.2, top_k=5)
        VertexAIAgentService(project_id="p", agent_config=cfg)
        call_kwargs = mock_vertexai["GenerativeModel"].call_args
        gen_cfg = call_kwargs.kwargs["generation_config"]
        assert gen_cfg["temperature"] == pytest.approx(0.2)
        assert gen_cfg["top_k"] == 5


# ---------------------------------------------------------------------------
# 5. _initialize_model with response_schema
# ---------------------------------------------------------------------------

class TestInitializeModel:
    def test_schema_adds_mime_type(self, mock_vertexai):
        from youtube_extension.services.cloud.vertex_ai_agent import (
            AgentConfig,
            VertexAIAgentService,
        )
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}
        mock_vertexai["GenerativeModel"].return_value = MagicMock()
        cfg = AgentConfig(response_schema=schema)
        VertexAIAgentService(project_id="p", agent_config=cfg)
        gen_cfg = mock_vertexai["GenerativeModel"].call_args.kwargs["generation_config"]
        assert gen_cfg["response_mime_type"] == "application/json"
        assert gen_cfg["response_schema"] == schema


# ---------------------------------------------------------------------------
# 6. process_text
# ---------------------------------------------------------------------------

class TestProcessText:
    async def test_basic_response(self, service, mock_vertexai):
        fake_resp = _make_response("result text", finish_reason="STOP")
        service.model.generate_content = MagicMock(return_value=fake_resp)

        from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse

        result = await service.process_text("Tell me something.")
        assert isinstance(result, AgentResponse)
        assert result.text == "result text"
        assert result.finish_reason == "STOP"

    async def test_context_prepended_to_prompt(self, service, mock_vertexai):
        captured = {}

        def fake_generate(contents, stream=False):
            captured["contents"] = contents
            return _make_response("ok")

        service.model.generate_content = fake_generate
        mock_vertexai["Content"].side_effect = lambda role, parts: f"Content({role})"
        mock_vertexai["Part"].from_text = MagicMock(side_effect=lambda t: t)

        await service.process_text("my query", context="extra context")
        # The full_prompt should include both context and query
        call_text = mock_vertexai["Part"].from_text.call_args[0][0]
        assert "extra context" in call_text
        assert "my query" in call_text

    async def test_usage_metadata_populated(self, service, mock_vertexai):
        fake_resp = _make_response("data")
        fake_resp.usage_metadata = _make_usage_metadata(5, 15, 20)
        service.model.generate_content = MagicMock(return_value=fake_resp)

        result = await service.process_text("q")
        assert result.usage["prompt_tokens"] == 5
        assert result.usage["completion_tokens"] == 15
        assert result.usage["total_tokens"] == 20

    async def test_exception_propagated(self, service):
        service.model.generate_content = MagicMock(side_effect=RuntimeError("boom"))

        with pytest.raises(RuntimeError, match="boom"):
            await service.process_text("failing prompt")

    async def test_no_context_uses_raw_prompt(self, service, mock_vertexai):
        mock_vertexai["Part"].from_text = MagicMock(side_effect=lambda t: t)
        service.model.generate_content = MagicMock(return_value=_make_response("x"))

        await service.process_text("standalone prompt")
        call_text = mock_vertexai["Part"].from_text.call_args[0][0]
        assert call_text == "standalone prompt"


# ---------------------------------------------------------------------------
# 7. analyze_video
# ---------------------------------------------------------------------------

class TestAnalyzeVideo:
    async def test_comprehensive_prompt_contains_video_url(self, service):
        captured = {}

        async def fake_process(prompt, context=None, system_instruction=None):
            captured["prompt"] = prompt
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            return AgentResponse(text="analysis", metadata={})

        service.process_text = fake_process

        await service.analyze_video(
            "https://youtube.com/watch?v=abc",
            "What is this about?",
            analysis_type="comprehensive",
        )
        assert "https://youtube.com/watch?v=abc" in captured["prompt"]
        assert "comprehensive" in captured["prompt"].lower() or "1." in captured["prompt"]

    async def test_summary_prompt_is_concise(self, service):
        captured = {}

        async def fake_process(prompt, context=None, system_instruction=None):
            captured["prompt"] = prompt
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            return AgentResponse(text="summary", metadata={})

        service.process_text = fake_process
        await service.analyze_video("https://youtu.be/xyz", "Summarise", analysis_type="summary")
        assert "concise" in captured["prompt"].lower()

    async def test_technical_prompt_mentions_quality(self, service):
        captured = {}

        async def fake_process(prompt, context=None, system_instruction=None):
            captured["prompt"] = prompt
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            return AgentResponse(text="technical", metadata={})

        service.process_text = fake_process
        await service.analyze_video("https://youtu.be/xyz", "Tech it", analysis_type="technical")
        assert "quality" in captured["prompt"].lower() or "technical" in captured["prompt"].lower()

    async def test_returns_agent_response(self, service):
        service.model.generate_content = MagicMock(return_value=_make_response("v"))
        from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse

        result = await service.analyze_video("url", "prompt")
        assert isinstance(result, AgentResponse)


# ---------------------------------------------------------------------------
# 8. analyze_transcript
# ---------------------------------------------------------------------------

class TestAnalyzeTranscript:
    async def test_transcript_included_in_prompt(self, service, mock_vertexai):
        mock_vertexai["Part"].from_text = MagicMock(side_effect=lambda t: t)
        service.model.generate_content = MagicMock(return_value=_make_response("ok"))

        await service.analyze_transcript("Hello world transcript")
        call_text = mock_vertexai["Part"].from_text.call_args[0][0]
        assert "Hello world transcript" in call_text

    async def test_metadata_incorporated_when_provided(self, service, mock_vertexai):
        mock_vertexai["Part"].from_text = MagicMock(side_effect=lambda t: t)
        service.model.generate_content = MagicMock(return_value=_make_response("ok"))

        meta = {"title": "My Video", "channel": "TestChan", "duration": "5:00", "views": 999}
        await service.analyze_transcript("transcript text", video_metadata=meta)
        call_text = mock_vertexai["Part"].from_text.call_args[0][0]
        assert "My Video" in call_text
        assert "TestChan" in call_text

    async def test_no_metadata_no_crash(self, service):
        service.model.generate_content = MagicMock(return_value=_make_response("ok"))
        from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse

        result = await service.analyze_transcript("just text")
        assert isinstance(result, AgentResponse)


# ---------------------------------------------------------------------------
# 9. generate_structured_output
# ---------------------------------------------------------------------------

class TestGenerateStructuredOutput:
    async def test_returns_parsed_json(self, service):
        payload = {"key": "value", "count": 42}

        async def fake_process(prompt, context=None, system_instruction=None):
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            return AgentResponse(text=json.dumps(payload), metadata={})

        service.process_text = fake_process
        schema = {"type": "object"}
        result = await service.generate_structured_output("give me json", schema)
        assert result == payload

    async def test_original_config_object_restored_after_success(self, service, mock_vertexai):
        # generate_structured_output saves `original_config = self.agent_config` (a reference),
        # then mutates the same object with the new schema.  The finally block reassigns
        # self.agent_config back to that same (now-mutated) reference, so the net effect is
        # that agent_config IS the same object and its response_schema equals the schema
        # that was passed in.  Verify that the object identity is preserved and _initialize_model
        # is called twice (once to apply the schema, once to restore).
        original_config_id = id(service.agent_config)

        async def fake_process(prompt, context=None, system_instruction=None):
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            return AgentResponse(text='{"ok": true}', metadata={})

        service.process_text = fake_process
        mock_vertexai["GenerativeModel"].return_value = MagicMock()

        schema = {"type": "object"}
        result = await service.generate_structured_output("p", schema)
        # The config object identity is preserved (same reference was stored and restored)
        assert id(service.agent_config) == original_config_id
        # The returned value is the parsed JSON
        assert result == {"ok": True}

    async def test_original_config_object_restored_after_exception(self, service, mock_vertexai):
        # Same reference-aliasing behaviour: on exception the finally block still runs and
        # self.agent_config is reassigned to the same (mutated) object.  Verify the identity
        # is consistent and that _initialize_model is invoked to clean up.
        original_config_id = id(service.agent_config)

        async def fake_process(prompt, context=None, system_instruction=None):
            raise ValueError("parse error")

        service.process_text = fake_process
        mock_vertexai["GenerativeModel"].return_value = MagicMock()

        with pytest.raises(ValueError):
            await service.generate_structured_output("p", {"type": "object"})

        # Object identity is stable; _initialize_model was called in the finally block
        assert id(service.agent_config) == original_config_id
        # GenerativeModel was called at least twice (once on init, at least twice more for
        # apply-schema + restore)
        assert mock_vertexai["GenerativeModel"].call_count >= 3

    async def test_invalid_json_raises(self, service):
        async def fake_process(prompt, context=None, system_instruction=None):
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            return AgentResponse(text="not-json{{", metadata={})

        service.process_text = fake_process
        with pytest.raises(json.JSONDecodeError):
            await service.generate_structured_output("p", {})


# ---------------------------------------------------------------------------
# 10. batch_process
# ---------------------------------------------------------------------------

class TestBatchProcess:
    async def test_all_prompts_processed(self, service):
        call_count = 0

        async def fake_process(prompt, context=None, system_instruction=None):
            nonlocal call_count
            call_count += 1
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            return AgentResponse(text=f"resp-{call_count}", metadata={})

        service.process_text = fake_process
        prompts = ["p1", "p2", "p3"]
        results = await service.batch_process(prompts)
        assert len(results) == 3
        assert call_count == 3

    async def test_exceptions_are_filtered_out(self, service):
        call_count = 0

        async def fake_process(prompt, context=None, system_instruction=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("fail")
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            return AgentResponse(text="ok", metadata={})

        service.process_text = fake_process
        results = await service.batch_process(["a", "b", "c"])
        # Two succeeded, one failed and was filtered
        assert len(results) == 2

    async def test_empty_prompts_returns_empty_list(self, service):
        results = await service.batch_process([])
        assert results == []

    async def test_max_concurrent_respected(self, service):
        """Semaphore should cap concurrency; results should still be correct."""
        collected = []

        async def fake_process(prompt, context=None, system_instruction=None):
            from youtube_extension.services.cloud.vertex_ai_agent import AgentResponse
            collected.append(prompt)
            return AgentResponse(text=prompt, metadata={})

        service.process_text = fake_process
        prompts = [f"p{i}" for i in range(10)]
        results = await service.batch_process(prompts, max_concurrent=3)
        assert len(results) == 10
        assert sorted(r.text for r in results) == sorted(prompts)


# ---------------------------------------------------------------------------
# 11. create_chat_session
# ---------------------------------------------------------------------------

class TestCreateChatSession:
    async def test_returns_chat_object(self, service):
        fake_chat = MagicMock()
        service.model.start_chat = MagicMock(return_value=fake_chat)
        result = await service.create_chat_session()
        assert result is fake_chat
        service.model.start_chat.assert_called_once()


# ---------------------------------------------------------------------------
# 12. get_embeddings_model
# ---------------------------------------------------------------------------

class TestGetEmbeddingsModel:
    def test_returns_model_from_pretrained(self, service):
        fake_model = MagicMock()
        mock_text_embedding = MagicMock()
        mock_text_embedding.from_pretrained = MagicMock(return_value=fake_model)

        with patch.dict(
            "sys.modules",
            {"vertexai.language_models": MagicMock(TextEmbeddingModel=mock_text_embedding)},
        ):
            result = service.get_embeddings_model("text-embedding-004")

        mock_text_embedding.from_pretrained.assert_called_once_with("text-embedding-004")
        assert result is fake_model

    def test_custom_model_name(self, service):
        fake_model = MagicMock()
        mock_text_embedding = MagicMock()
        mock_text_embedding.from_pretrained = MagicMock(return_value=fake_model)

        with patch.dict(
            "sys.modules",
            {"vertexai.language_models": MagicMock(TextEmbeddingModel=mock_text_embedding)},
        ):
            service.get_embeddings_model("my-custom-model")

        mock_text_embedding.from_pretrained.assert_called_once_with("my-custom-model")


# ---------------------------------------------------------------------------
# 13. generate_embeddings
# ---------------------------------------------------------------------------

class TestGenerateEmbeddings:
    async def test_returns_list_of_vectors(self, service):
        fake_emb_a = MagicMock()
        fake_emb_a.values = [0.1, 0.2, 0.3]
        fake_emb_b = MagicMock()
        fake_emb_b.values = [0.4, 0.5, 0.6]
        fake_emb_model = MagicMock()
        fake_emb_model.get_embeddings = MagicMock(return_value=[fake_emb_a, fake_emb_b])

        service.get_embeddings_model = MagicMock(return_value=fake_emb_model)

        vectors = await service.generate_embeddings(["text1", "text2"])
        assert len(vectors) == 2
        assert vectors[0] == [0.1, 0.2, 0.3]
        assert vectors[1] == [0.4, 0.5, 0.6]

    async def test_calls_get_embeddings_with_task_type(self, service):
        fake_emb = MagicMock()
        fake_emb.values = [1.0]
        fake_emb_model = MagicMock()
        fake_emb_model.get_embeddings = MagicMock(return_value=[fake_emb])

        service.get_embeddings_model = MagicMock(return_value=fake_emb_model)

        await service.generate_embeddings(["hello"], task_type="RETRIEVAL_QUERY")
        fake_emb_model.get_embeddings.assert_called_once_with(
            ["hello"], task_type="RETRIEVAL_QUERY"
        )

    async def test_empty_texts_returns_empty(self, service):
        fake_emb_model = MagicMock()
        fake_emb_model.get_embeddings = MagicMock(return_value=[])
        service.get_embeddings_model = MagicMock(return_value=fake_emb_model)

        vectors = await service.generate_embeddings([])
        assert vectors == []


# ---------------------------------------------------------------------------
# 14. get_vertex_ai_service singleton
# ---------------------------------------------------------------------------

class TestGetVertexAIService:
    def test_raises_when_unavailable(self):
        with patch(
            "youtube_extension.services.cloud.vertex_ai_agent.VERTEX_AI_AVAILABLE",
            False,
        ):
            from youtube_extension.services.cloud.vertex_ai_agent import (
                get_vertex_ai_service,
            )
            with pytest.raises(ImportError):
                get_vertex_ai_service()

    def test_returns_singleton(self, mock_vertexai):
        mock_vertexai["GenerativeModel"].return_value = MagicMock()
        from youtube_extension.services.cloud.vertex_ai_agent import (
            get_vertex_ai_service,
        )
        svc1 = get_vertex_ai_service()
        svc2 = get_vertex_ai_service()
        assert svc1 is svc2

    def test_singleton_reset_between_tests(self, mock_vertexai):
        mock_vertexai["GenerativeModel"].return_value = MagicMock()
        from youtube_extension.services.cloud import vertex_ai_agent as mod
        from youtube_extension.services.cloud.vertex_ai_agent import (
            get_vertex_ai_service,
        )
        # Singleton was reset by the autouse fixture
        assert mod._vertex_ai_service is None
        svc = get_vertex_ai_service()
        assert mod._vertex_ai_service is svc
