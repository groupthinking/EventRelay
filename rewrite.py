import sys

with open("src/agents/openai_dev_task_manager.py", "r") as f:
    content = f.read()

direct_import = """        try:
            from mcp.mcp_video_processor import MCPVideoProcessor
            return MCPVideoProcessor()
        except ImportError as e:
            raise ImportError("Unable to load MCPVideoProcessor module") from e"""

content = content.replace("""        try:
            from mcp.mcp_video_processor import MCPVideoProcessor
            return MCPVideoProcessor()
        except ImportError:
            raise ImportError("Unable to load MCPVideoProcessor module")""", direct_import)

with open("src/agents/openai_dev_task_manager.py", "w") as f:
    f.write(content)
