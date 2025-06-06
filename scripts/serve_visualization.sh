#!/bin/bash

echo "Starting visualization server on port $2..."
echo "Trace file: $1"

python3 << EOF
try:
    import sys
    import os
    sys.path.insert(0, '/home/lpagecaccia/my_tracer')
    
    def visualize_trace(trace_file, port):
        # Read and process the trace file
        with open(trace_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace all variations of Unicode box-drawing characters
        # Using the exact characters that appear in the output
        replacements = [
            ('â""â"€', '    '),  # └─
            ('â"œâ"€', '    '),  # ├─
            ('â"‚  ', '    '),  # │ (with spaces)
            ('â"‚ ', '   '),     # │ (with space)
            ('Ã—', 'x'),        # ×
        ]
        
        for old, new in replacements:
            content = content.replace(old, new)
        
        print("\nProcessed trace output:")
        print("-" * 80)
        print(content)
        print("-" * 80)
        
        # If you want to serve it via HTTP, add that code here
    
    visualize_trace("$1", $2)
    
except Exception as e:
    print(f"Error visualizing trace: {e}")
    import traceback
    traceback.print_exc()
EOF
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

# Check if visualize_trace.py exists
VISUALIZE_SCRIPT="$PROJECT_ROOT/examples/visualize_trace.py"
if [ ! -f "$VISUALIZE_SCRIPT" ]; then
    echo "Error: visualize_trace.py not found at $VISUALIZE_SCRIPT"
    echo "Creating a simple visualization script..."
    
    # Create a minimal visualization script if it doesn't exist
    cat > "$VISUALIZE_SCRIPT" << 'EOF'
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.visualizer.trace_visualizer import main

if __name__ == "__main__":
    exit(main())
EOF
    chmod +x "$VISUALIZE_SCRIPT"
fi

echo "Starting visualization server on port $PORT..."
echo "Trace file: $TRACE_FILE"

# The error suggests Python code is being executed
python3 << EOF
import sys
import os
sys.path.insert(0, os.path.join(os.getcwd(), 'src'))

try:
    from visualizer.trace_visualizer import visualize_trace
    
    # Generate HTML visualization
    import tempfile
    import http.server
    import socketserver
    import webbrowser
    from visualizer.html_visualizer import generate_html_visualization
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        html_file = f.name
    
    # Generate the HTML visualization
    generate_html_visualization("$TRACE_FILE", html_file)
    
    # Serve the HTML file
    os.chdir(os.path.dirname(html_file))
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", $PORT), Handler) as httpd:
        print(f"Serving visualization at http://localhost:$PORT/{os.path.basename(html_file)}")
        print("Press Ctrl+C to stop the server...")
        
        # Try to open browser
        webbrowser.open(f"http://localhost:$PORT/{os.path.basename(html_file)}")
        
        httpd.serve_forever()
        
except Exception as e:
    print(f"Error visualizing trace: {e}")
    import traceback
    traceback.print_exc()
EOF