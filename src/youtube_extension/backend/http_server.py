#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
from typing import Any
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import sys
from pathlib import Path

# REMOVED: sys.path.insert with Path manipulation
from backend.real_video_processor import RealVideoProcessor

class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, code: int = 200, content_type: str = 'application/json'):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        # Basic CORS for local dev (frontend on 3000)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/health':
            self._set_headers(200)
            self.wfile.write(json.dumps({'status': 'ok'}).encode())
            return
        if parsed.path == '/results/learning_log':
            log_path = Path(__file__).resolve().parents[1] / 'workflow_results' / 'learning_log.json'
            if not log_path.exists():
                self._set_headers(200)
                self.wfile.write(b'[]')
                return
            try:
                data = json.loads(log_path.read_text())
            except Exception:
                data = []
            self._set_headers(200)
            self.wfile.write(json.dumps(data).encode())
            return
        if parsed.path == '/results/videos':
            videos_dir = Path(__file__).resolve().parents[1] / 'workflow_results' / 'videos'
            videos_dir.mkdir(parents=True, exist_ok=True)
            items = []
            for fp in videos_dir.glob('*.json'):
                try:
                    obj = json.loads(fp.read_text())
                    items.append({
                        'video_id': obj.get('video_id'),
                        'category': (obj.get('actionable_content') or {}).get('category','Unknown'),
                        'actions': len((obj.get('actionable_content') or {}).get('actions') or []),
                        'processing_time': obj.get('processing_time'),
                        'metadata': obj.get('metadata', {}),
                    })
                except Exception:
                    continue
            self._set_headers(200)
            self.wfile.write(json.dumps(items).encode())
            return
        if parsed.path.startswith('/results/videos/'):
            video_id = parsed.path.split('/results/videos/')[-1]
            fp = Path(__file__).resolve().parents[1] / 'workflow_results' / 'videos' / f'{video_id}.json'
            if not fp.exists():
                self._set_headers(404)
                self.wfile.write(json.dumps({'error': 'not_found'}).encode())
                return
            try:
                obj = json.loads(fp.read_text())
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({'error': 'read_error', 'detail': str(e)}).encode())
                return
            self._set_headers(200)
            self.wfile.write(json.dumps(obj).encode())
            return
        self._set_headers(404)
        self.wfile.write(json.dumps({'error': 'not_found'}).encode())

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/feedback':
            length = int(self.headers.get('Content-Length', '0'))
            body = self.rfile.read(length) if length else b'{}'
            try:
                data = json.loads(body.decode() or '{}')
                video_id = data.get('video_id')
                rating = data.get('rating')
                note = data.get('note')
                if not video_id or rating is None:
                    raise ValueError('video_id and rating are required')
            except Exception as e:
                self._set_headers(400)
                self.wfile.write(json.dumps({'error': 'bad_request', 'detail': str(e)}).encode())
                return

            log_path = Path(__file__).resolve().parents[1] / 'workflow_results' / 'learning_log.json'
            log_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                arr = json.loads(log_path.read_text()) if log_path.exists() else []
            except Exception:
                arr = []
            arr.append({'video_id': video_id, 'feedback': {'rating': rating, 'note': note}})
            log_path.write_text(json.dumps(arr, indent=2))
            self._set_headers(200)
            self.wfile.write(json.dumps({'ok': True}).encode())
            return

        if parsed.path != '/process':
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'not_found'}).encode())
            return

        length = int(self.headers.get('Content-Length', '0'))
        body = self.rfile.read(length) if length else b'{}'
        try:
            data = json.loads(body.decode() or '{}')
            video = data.get('video') or ''
            if not video:
                raise ValueError('Missing "video"')
        except Exception as e:
            self._set_headers(400)
            self.wfile.write(json.dumps({'error': 'bad_request', 'detail': str(e)}).encode())
            return

        # Run async processing
        async def run(video_url: str) -> Any:
            proc = RealVideoProcessor(real_mode_only=False)
            return await proc.process_video_real(video_url)

        try:
            result = asyncio.run(run(video))
            self._set_headers(200)
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': 'processing_failed', 'detail': str(e)}).encode())

def main():
    port = int(os.getenv('HTTP_PORT', '8088'))
    with HTTPServer(('', port), Handler) as httpd:
        print(f"HTTP server listening on http://localhost:{port}")
        httpd.serve_forever()

if __name__ == '__main__':
    main()

