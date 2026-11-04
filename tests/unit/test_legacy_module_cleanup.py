import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RETIRED_MODULES = {
    "agents.markdown_video_processor": "src/agents/markdown_video_processor.py",
    "integration.data_pipeline": "src/integration/data_pipeline.py",
    "enterprise_mcp_server": "src/youtube_extension/mcp/enterprise_mcp_server.py",
    "notebooklm_processor": "src/youtube_extension/mcp/notebooklm_processor.py",
    "test_enterprise_mcp": "test_enterprise_mcp.py",
}


def test_retired_modules_are_not_present_or_import_mapped() -> None:
    import_mapping = json.loads((ROOT / "config/import_mapping.json").read_text())
    mapped_modules = set(import_mapping["module_files"])
    mapped_modules.update(import_mapping["reverse_map"])
    mapped_modules.update(
        module
        for dependencies in import_mapping["import_map"].values()
        for module in dependencies
    )

    for module, path in RETIRED_MODULES.items():
        assert not (ROOT / path).exists()
        assert module not in mapped_modules
