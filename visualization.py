import matplotlib.pyplot as plt
import numpy as np
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

def visualize_trace(trace_file, port):
    """Visualize ray tracing data from the given trace file"""
    # Read and parse the trace file
    with open(trace_file, 'r') as f:
        data = f.read()
    
    # ...existing code...
    
    # Start HTTP server to serve the visualization
    os.chdir(os.path.dirname(trace_file) or '.')
    httpd = HTTPServer(('', port), SimpleHTTPRequestHandler)
    print(f"Serving visualization at http://localhost:{port}")
    httpd.serve_forever()