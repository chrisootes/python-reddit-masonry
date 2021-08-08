"""
Stream HTML from generator
For example the reddit api is rate limited
With this you can send data between api calls instead of just waiting
"""

import sys
import io
import http.server


class StreamingParser:
    """
    Stream bytes from callback generator
    """

    def __init__(self, callback):
        self.output = sys.stdout
        self.callback = callback

    def render(self, path):
        """
        Put generator output in http file
        """
        for i in self.callback(path):
            self.output.write(i)


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    parser = StreamingParser(lambda a : a)
    static_files = []

    def do_GET(self):
        """
        Overloaded but for static files use original function with super().do_GET()
        """
        # Static files
        if self.path in self.static_files:
            print(f"Static: {self.path}")
            super().do_GET()
        # Dynamic content based on path
        else:
            print(f"Dynamic: {self.path}")
            self.parser.output = self.wfile
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.parser.render(self.path)


def create_server(hostname, serverport, static_files, callback):
    """
    Create streaming server
    """
    print("Creating server")

    # Setup parser
    parser = StreamingParser(callback)

    # Setup handler
    handler = RequestHandler
    handler.parser = parser
    handler.static_files = static_files

    # Setup server
    server = http.server.HTTPServer((hostname, serverport), handler)
    print(f"Starting server on http://{hostname}:{serverport}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    print("Server stopped")
