"""
Stream HTML from generator
For example the reddit api is rate limited
With this you can send data between api calls instead of just waiting
"""

import http.server
import logging

logger = logging.getLogger(__name__)


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    callback = lambda a : [str(a)]
    static_files = []

    def do_GET(self):
        """
        Overloaded but for static files use original function with super().do_GET()
        """
        # Static files
        if self.path in self.static_files:
            logger.debug(f"Static: {self.path}")
            super().do_GET()
        # Dynamic content based on path
        else:
            logger.debug(f"Dynamic: {self.path}")
            # Put generator output in http file
            for i in self.callback(self.path):
                self.wfile.write(i.encode('utf-8'))


def create_server(hostname, serverport, static_files, callback):
    """
    Create streaming server
    """
    logger.debug("Creating server")

    # Setup handler
    handler = RequestHandler
    handler.callback = callback
    handler.static_files = static_files

    # Setup server
    server = http.server.HTTPServer((hostname, serverport), handler)
    logger.debug(f"Starting server on http://{hostname}:{serverport}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    logger.debug("Server stopped")
