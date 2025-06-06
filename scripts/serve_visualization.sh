#!/bin/bash

# Serve trace visualization for remote viewing
# Usage: ./serve_visualization.sh trace_file.json [port]

TRACE_FILE=$1
PORT=${2:-8080}

if [ -z "$TRACE_FILE" ]; then
    echo "Usage: $0 <trace_file.json> [port]"
    echo "Default port is 8080"
    exit 1
fi

if [ ! -f "$TRACE_FILE" ]; then
    echo "Error: Trace file '$TRACE_FILE' not found"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Add project root to PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "Starting visualization server on port $PORT..."
echo "Trace file: $TRACE_FILE"

python3 << EOF
import sys
import os
import json
import tempfile
import http.server
import socketserver
import webbrowser
from urllib.parse import quote

def clean_and_visualize_trace(trace_file, port):
    try:
        # Read the trace file
        with open(trace_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Try to parse as JSON
        try:
            trace_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            print("Attempting to clean up the trace data...")
            
            # Try to fix common JSON issues
            content = content.strip()
            if not content.startsWith('['):
                content = '[' + content
            if not content.endsWith(']'):
                content = content + ']'
            
            try:
                trace_data = json.loads(content)
            except json.JSONDecodeError:
                print("Could not repair JSON. Showing raw content...")
                trace_data = []
        
        # Filter out incomplete entries
        if isinstance(trace_data, list):
            valid_entries = []
            for entry in trace_data:
                if isinstance(entry, dict) and 'name' in entry and 'location' in entry:
                    valid_entries.append(entry)
            
            print(f"Found {len(valid_entries)} valid entries out of {len(trace_data)} total")
            trace_data = valid_entries
        
        # Generate HTML visualization
        html_content = generate_html_visualization(trace_data, trace_file)
        
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html_content)
            html_file = f.name
        
        # Serve the HTML file
        os.chdir(os.path.dirname(html_file))
        
        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def end_headers(self):
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                super().end_headers()
        
        with socketserver.TCPServer(("", port), CustomHandler) as httpd:
            filename = os.path.basename(html_file)
            print(f"Serving visualization at http://localhost:{port}/{filename}")
            print("Press Ctrl+C to stop the server...")
            
            # Try to open browser
            try:
                webbrowser.open(f"http://localhost:{port}/{filename}")
            except:
                pass
            
            httpd.serve_forever()
        
    except Exception as e:
        print(f"Error visualizing trace: {e}")
        import traceback
        traceback.print_exc()

def generate_html_visualization(trace_data, trace_file):
    """Generate HTML visualization for trace data."""
    
    if not trace_data:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trace Visualization - No Data</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .error {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>Trace Visualization</h1>
            <p class="error">No valid trace data found in {trace_file}</p>
            <p>The trace file appears to be empty or corrupted. Please regenerate the trace.</p>
        </body>
        </html>
        """
    
    # Generate the visualization
    html_parts = ["""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Function Call Trace Visualization</title>
            <style>
                body {
                    font-family: 'Courier New', monospace;
                    margin: 20px;
                    background-color: #f5f5f5;
                }
                .trace-container {
                    background: white;
                    padding: 20px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .trace-entry {
                    margin: 2px 0;
                    padding: 3px 5px;
                    border-left: 2px solid #ddd;
                }
                .function-name {
                    font-weight: bold;
                    color: #2c3e50;
                }
                .location {
                    color: #7f8c8d;
                    font-size: 0.9em;
                }
                .arguments {
                    color: #27ae60;
                    font-size: 0.85em;
                    margin-left: 20px;
                }
                .external {
                    background-color: #fff3cd;
                    border-left-color: #ffc107;
                }
                .depth-0 { margin-left: 0px; }
                .depth-1 { margin-left: 20px; }
                .depth-2 { margin-left: 40px; }
                .depth-3 { margin-left: 60px; }
                .depth-4 { margin-left: 80px; }
                .depth-5 { margin-left: 100px; }
                .depth-6 { margin-left: 120px; }
                .depth-7 { margin-left: 140px; }
                .stats {
                    background: #e8f4f8;
                    padding: 10px;
                    border-radius: 3px;
                    margin-bottom: 20px;
                }
            </style>
        </head>
        <body>
            <h1>Function Call Trace Visualization</h1>
    """]
    
    # Add statistics
    external_count = sum(1 for entry in trace_data if entry.get('is_external', False))
    internal_count = len(trace_data) - external_count
    
    html_parts.append(f"""
        <div class="stats">
            <strong>Statistics:</strong><br>
            Total function calls: {len(trace_data)}<br>
            Internal calls: {internal_count}<br>
            External calls: {external_count}<br>
            Source file: {trace_file}
        </div>
        <div class="trace-container">
    """)
    
    # Add trace entries
    for i, entry in enumerate(trace_data):
        name = entry.get('name', 'unknown')
        location = entry.get('location', 'unknown')
        arguments = entry.get('arguments', {})
        depth = entry.get('depth', 0)
        is_external = entry.get('is_external', False)
        
        # Format arguments
        args_str = ""
        if arguments:
            if isinstance(arguments, dict):
                arg_parts = []
                for k, v in list(arguments.items())[:3]:  # Show first 3 args
                    if isinstance(v, str) and len(v) > 30:
                        v = v[:27] + "..."
                    arg_parts.append(f"{k}={v}")
                if len(arguments) > 3:
                    arg_parts.append("...")
                args_str = f"({', '.join(arg_parts)})"
            else:
                args_str = f"({arguments})"
        
        # CSS classes
        css_classes = f"trace-entry depth-{min(depth, 7)}"
        if is_external:
            css_classes += " external"
        
        html_parts.append(f"""
            <div class="{css_classes}">
                <span class="function-name">[#{i+1}] {name}</span>
                <span class="arguments">{args_str}</span>
                <span class="location">[{location}]</span>
            </div>
        """)
    
    html_parts.append("""
        </div>
        </body>
        </html>
    """)
    
    return ''.join(html_parts)

# Run the visualization
clean_and_visualize_trace("$TRACE_FILE", $PORT)
EOF