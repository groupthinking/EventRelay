import sys
from src.agents.openai_dev_task_manager import OpenAIDevTaskManager

try:
    m = OpenAIDevTaskManager()
    m._load_mcp_video_processor()
    print("Success")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
