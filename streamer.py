"""
Rewrite HTML with data/
"""

import sys
import io
import http.server


class StreamingParser:
    """
    Buffered parse static HTML and add dynamic elements while streaming.
    # TODO mulitple templates and file updates
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
        #print(f"Path: {self.path}")
        #print(f"Headers: {self.headers}")
        if self.path in self.static_files:
            print(f"Static: {self.path}")
            super().do_GET()
        else:
            print(f"Dynamic: {self.path}")
            #referer = self.headers.get('Referer')
            #if referer == None:
            self.parser.output = self.wfile
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.parser.render(self.path)


def create_server(hostname, serverport, static_files, callback):
    """
    Create server
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
