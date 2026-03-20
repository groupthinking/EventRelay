import os
import sys

from dotenv import load_dotenv

# Add prescient-twin to path
sys.path.append(os.path.join(os.getcwd(), "prescient-twin"))

try:
    from main import app
    print("Successfully imported app from prescient-twin/main.py")

    print("\nRoutes:")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"  {route.methods} {route.path}")

except ImportError as e:
    print(f"Failed to import app: {e}")
except Exception as e:
    print(f"Error inspecting app: {e}")

print("\nEnvironment Check:")
load_dotenv()
print(f"  STITCH_ACCESS_TOKEN present: {'STITCH_ACCESS_TOKEN' in os.environ}")
