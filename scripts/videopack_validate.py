#!/usr/bin/env python3
import sys, json
from src.youtube_extension.videopack import read_pack, validate_pack

def main():
    if len(sys.argv) != 2:
        print("Usage: videopack_validate.py /path/to/pack.json"); sys.exit(2)
    pack = read_pack(sys.argv[1])
    validate_pack(pack)
    print("OK")

if __name__ == "__main__":
    main()
