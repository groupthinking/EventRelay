#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def rebuild_archive(manifest_path: Path, output_path: Path | None = None) -> Path:
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    chunk_dir = manifest_path.parent
    hash_file = chunk_dir / 'manifest.sha256.txt'
    expected = manifest.get('sha256')
    if hash_file.exists():
        hash_value = hash_file.read_text(encoding='utf-8').strip()
        if expected is None:
            expected = hash_value
        elif expected != hash_value:
            raise SystemExit(
                f'Manifest SHA-256 mismatch: JSON expects {expected}, hash file has {hash_value}'
            )
    if expected is None:
        raise SystemExit('No expected SHA-256 was provided in the artifact manifest.')
    assembled = b''.join(
        base64.b64decode((chunk_dir / chunk).read_bytes())
        for chunk in manifest['parts']
    )
    if output_path is None:
        output_path = chunk_dir / manifest['artifact_name']
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(assembled)
    actual = sha256_file(output_path)
    if actual != expected:
        raise SystemExit(
            f'SHA-256 mismatch for {output_path.name}: expected {expected}, got {actual}'
        )
    print(f'Rebuilt {output_path} ({len(assembled)} bytes)')
    print(f'SHA-256: {actual}')
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description='Rebuild the AdIntelligence app zip from base64 chunks and verify its SHA-256.')
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('manifest.json'), help='Path to the manifest JSON file.')
    parser.add_argument('--output', type=Path, default=None, help='Optional output path for the reconstructed archive.')
    args = parser.parse_args()
    rebuild_archive(args.manifest, args.output)


if __name__ == '__main__':
    main()
