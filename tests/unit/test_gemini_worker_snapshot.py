"""A queued request must retain its selected client, policy, and receipt identity."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from youtube_extension.services.ai import gemini_service as module


@pytest.mark.asyncio
@pytest.mark.parametrize("fails", [False, True])
@pytest.mark.parametrize("kind,old_model,new_model,backend", [
    *[(kind, old, new, "gemini")
      for kind in ("text", "image", "video", "audio")
      for old, new in (("gemini-2.5-flash", "gemini-3.8-flash"),
                       ("gemini-3.8-flash", "gemini-2.5-flash"))],
    ("veo", "veo-2.0", "gemini-3.8-flash", "veo"),
    ("text", "gemma-2-9b-it", "gemini-3.8-flash", "gemma"),
])
async def test_queued_request_keeps_model_snapshot(monkeypatch, tmp_path, kind, old_model, new_model, backend, fails):
    monkeypatch.setattr(module.GeminiService, "_initialize_client", lambda self: None)
    monkeypatch.setattr(module.GeminiService, "is_available", lambda self: True)
    monkeypatch.setattr(module, "Part", SimpleNamespace(from_data=lambda *args, **kwargs: "media-part"), raising=False)
    monkeypatch.setattr(module, "genai_types", None)
    uploaded = SimpleNamespace(name="offline-file", state=SimpleNamespace(name="ACTIVE"))
    monkeypatch.setattr(module, "genai", SimpleNamespace(upload_file=Mock(return_value=uploaded), delete_file=Mock()))
    service = module.GeminiService(module.GeminiConfig(api_key="test-key", model_name=old_model))
    old_client = SimpleNamespace(generate_content=Mock(return_value=SimpleNamespace(text="old result")))
    if fails:
        old_client.generate_content.side_effect = RuntimeError("provider failure")
    new_client = SimpleNamespace(generate_content=Mock(return_value=SimpleNamespace(text="new result")))
    # The switch changes the provider format as well as the selected model.
    service._register_model(new_model, new_client, backend="gemini", use_vertex=False)
    service._register_model(old_model, old_client, backend=backend, use_vertex=backend == "gemini")
    if kind == "text":
        request = service.process_text("question", temperature=0.3, max_tokens=123)
    elif kind == "image":
        request = service.process_image(Image.new("RGB", (2, 2)), "question", temperature=0.3, max_tokens=123)
    else:
        media = tmp_path / ("clip.mp3" if kind == "audio" else "clip.mp4")
        media.write_bytes(b"test-only-media")
        method = service.process_audio if kind == "audio" else service.process_video
        request = method(media, "question", temperature=0.3, max_tokens=123)

    loop = asyncio.get_running_loop()
    submitted = asyncio.Event()
    release_worker = Event()
    dispatch = loop.run_in_executor
    with ThreadPoolExecutor(max_workers=1) as executor:
        blocker = executor.submit(release_worker.wait, 5)

        def enqueue(_executor, function, *args):
            future = dispatch(executor, function, *args)
            submitted.set()
            return future

        monkeypatch.setattr(loop, "run_in_executor", enqueue)
        task = asyncio.create_task(request)
        try:
            await asyncio.wait_for(submitted.wait(), 2)
            service.select_model(new_model)
        finally:
            release_worker.set()
        result = await asyncio.wait_for(task, 2)
        blocker.result()

    assert result.success is not fails
    if fails:
        assert result.error == "provider failure"
    assert result.model_name == old_model
    assert result.backend == (backend if kind in {"text", "veo"} else "vertex")
    old_client.generate_content.assert_called_once()
    new_client.generate_content.assert_not_called()
    config = old_client.generate_content.call_args.kwargs["generation_config"]
    assert config["max_output_tokens"] == 123
    assert ("temperature" in config) == (old_model != "gemini-3.8-flash")
    if old_model != "gemini-3.8-flash":
        assert config["temperature"] == 0.3
    else:
        assert not {"temperature", "top_p", "top_k"} & config.keys()
