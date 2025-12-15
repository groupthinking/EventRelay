#!/usr/bin/env python3
"""
Simple HTTP Server to serve the test page
"""

import http.server
import socketserver
import os
import webbrowser

PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

if __name__ == "__main__":
    print(f"Starting server at http://localhost:{PORT}")
    print(f"Serving test page: http://localhost:{PORT}/test-page.html")
    print("Press Ctrl+C to stop the server")
    
    # Automatically open the test page in the default browser
    webbrowser.open(f"http://localhost:{PORT}/test-page.html")
    
    # Create the server
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            # Start the server
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
