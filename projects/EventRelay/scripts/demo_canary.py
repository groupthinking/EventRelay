#!/usr/bin/env python3
import os
import sys

# Import from parent src directory
from ...src.canary_router import route_user


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "guest"
    lane = route_user(user, "canary", "mcp_video_processor")
    print(f"user={user} lane={lane}")


if __name__ == "__main__":
    main()


