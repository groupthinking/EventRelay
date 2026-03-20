#!/usr/bin/env python3
"""
Generate OpenAPI specification from FastAPI app.
Used for SDK generation with Stainless.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from youtube_extension.backend.main import app

    # Generate OpenAPI schema
    openapi_schema = app.openapi()

    # Save to file
    output_path = Path(__file__).parent.parent / "openapi.yaml"

    # Convert to YAML for better readability
    try:
        import yaml

        with open(output_path, "w") as f:
            yaml.dump(openapi_schema, f, sort_keys=False, default_flow_style=False)
        print(f"✅ OpenAPI spec generated at: {output_path}")

    except ImportError:
        # Fallback to JSON if PyYAML not available
        output_path = Path(__file__).parent.parent / "openapi.json"
        with open(output_path, "w") as f:
            json.dump(openapi_schema, f, indent=2)
        print(f"✅ OpenAPI spec generated at: {output_path}")

except Exception as e:
    print(f"❌ Error generating OpenAPI spec: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
