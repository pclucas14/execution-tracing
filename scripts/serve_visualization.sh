#!/bin/bash

# Serve trace visualization for remote viewing with pattern grouping
# Usage: ./serve_visualization.sh trace_file.json [port] [--no-patterns] [--hide-imports]

TRACE_FILE=$1
PORT=${2:-8080}
GROUP_PATTERNS=True
HIDE_IMPORTS=False

# Check for flags
for arg in "$@"; do
    if [ "$arg" = "--no-patterns" ]; then
        GROUP_PATTERNS=False
    elif [ "$arg" = "--hide-imports" ]; then
        HIDE_IMPORTS=true
    fi
done

if [ -z "$TRACE_FILE" ]; then
    echo "Usage: $0 <trace_file.json> [port] [--no-patterns] [--hide-imports]"
    echo "Default port is 8080"
    echo "Use --no-patterns to disable pattern grouping"
    echo "Use --hide-imports to hide import-related calls by default"
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
export PYTHONPATH="$PROJECT_ROOT/src:$PROJECT_ROOT:$PYTHONPATH"

echo "Starting visualization server on port $PORT..."
echo "Trace file: $TRACE_FILE"
echo "Pattern grouping: $GROUP_PATTERNS"
echo "Hide imports: $HIDE_IMPORTS"

python3 << EOF
import sys
import os
import json
import tempfile
import http.server
import socketserver
import webbrowser
from urllib.parse import quote

# Add the src directory to Python path
sys.path.insert(0, '$PROJECT_ROOT/src')

def clean_and_visualize_trace(trace_file, port, group_patterns):
    try:
        # Import the HTML visualizer
        from visualizer.html_visualizer import generate_html_visualization
        
        print("Generating HTML visualization...")
        
        # Create temporary HTML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
            html_file = f.name
        
        # Generate the visualization
        generate_html_visualization(trace_file, html_file, group_patterns=$GROUP_PATTERNS)
        
        # Serve the HTML file
        os.chdir(os.path.dirname(html_file))
        
        class CustomHandler(http.server.SimpleHTTPRequestHandler):
            def end_headers(self):
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                super().end_headers()
            
            def log_message(self, format, *args):
                # Suppress access logs for cleaner output
                pass
        
        with socketserver.TCPServer(("", port), CustomHandler) as httpd:
            filename = os.path.basename(html_file)
            print(f"✓ Serving visualization at: http://localhost:{port}/{filename}")
            print(f"\n🔗 For remote access, use SSH port forwarding:")
            print(f"   ssh -L {port}:localhost:{port} [your-connection]")
            print(f"\n🌐 Then open in browser: http://localhost:{port}/{filename}")
            print(f"\n📊 Features enabled:")
            print(f"   • Pattern grouping: {'✓' if group_patterns else '✗'}")
            print(f"   • Import filtering: {'✓' if $HIDE_IMPORTS else '✗'}")
            print(f"   • Interactive filtering: ✓")
            print(f"   • Nested pattern detection: ✓")
            print("\nPress Ctrl+C to stop the server...")
            
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n\n🛑 Server stopped.")
                # Clean up temp file
                try:
                    os.unlink(html_file)
                except:
                    pass
        
    except Exception as e:
        print(f"❌ Error visualizing trace: {e}")
        import traceback
        traceback.print_exc()

# Run the visualization
clean_and_visualize_trace("$TRACE_FILE", $PORT, $GROUP_PATTERNS)
EOF