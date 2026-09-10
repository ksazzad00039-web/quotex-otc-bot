from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from config import PORT, logger

class SimpleHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = '{"status":"ONLINE","engine":"Quotex Quant 1-Hour"}'
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        return  # Silence standard logs to keep output clean

def start_web_server():
    server = HTTPServer(('0.0.0.0', PORT), SimpleHealthHandler)
    logger.info(f"Health check web server running on port {PORT}")
    server.serve_forever()

