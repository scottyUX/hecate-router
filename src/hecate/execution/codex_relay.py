"""Stdlib-only loopback HTTP → Unix socket relay inside a networkless container."""
import http.client
import socket
import socketserver
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    # Same as http.server.ThreadingHTTPServer (3.7+); task envs run Python 3.5/3.6 too.
    daemon_threads = True


class UnixConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(sys.argv[1])


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/v1/responses":
            self.send_error(404)
            return
        n = int(self.headers.get("Content-Length", "0"))
        if not 0 < n <= 16 * 1024 * 1024:
            self.send_error(413)
            return
        connection = UnixConnection("localhost", timeout=600)
        try:
            connection.request(
                "POST",
                self.path,
                self.rfile.read(n),
                {"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            data = response.read()
            self.send_response(response.status)
            self.send_header(
                "Content-Type", response.getheader("Content-Type", "application/json")
            )
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        finally:
            connection.close()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", int(sys.argv[2])), Handler).serve_forever()
