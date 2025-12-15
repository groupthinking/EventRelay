#!/usr/bin/env python3
"""
Simple HTTP server for viewing the Cursor-styled documentation locally.
"""

import http.server
import socketserver
import os
import webbrowser
from threading import Timer

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

def open_browser():
    """Open the documentation in the default browser."""
    webbrowser.open(f'http://localhost:{PORT}')

def main():
    print(f"🚀 Starting Cursor-styled documentation server...")
    print(f"📁 Serving from: {DIRECTORY}")
    print(f"🌐 Access at: http://localhost:{PORT}")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Open browser after a short delay
    Timer(1.0, open_browser).start()
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✅ Server stopped")

if __name__ == "__main__":
    main() 