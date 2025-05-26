import sys
import os
import argparse

def run_tracer(script_path, output_file=None, scope_path=None, track_external_calls=True, script_args=None):
    """Run the tracer with given arguments."""
    # Add the project root directory to Python's path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, project_root)
    
    from src.tracer.core import start_tracing, stop_tracing

    # Get absolute path to the script
    script_to_trace = os.path.abspath(script_path)
    
    # Set up script args in sys.argv for the target script
    sys.argv = [script_to_trace] + (script_args or [])

    # Determine tracing scope
    if not scope_path:
        # Default to the directory containing the script
        scope_path = os.path.dirname(script_to_trace)
        
    # Start tracing
    print(f"Tracing script: {script_to_trace}")
    print(f"Tracing scope: {scope_path}")
    print(f"Track external calls: {track_external_calls}")
    start_tracing(scope_path=scope_path, main_file=script_to_trace, track_external_calls=track_external_calls)
    
    try:
        # Add script directory to path to ensure imports work
        script_dir = os.path.dirname(script_to_trace)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
            
        # Execute the script
        with open(script_to_trace) as f:
            code = compile(f.read(), script_to_trace, 'exec')
            exec(code, {'__name__': '__main__', '__file__': script_to_trace})
    finally:
        # Stop tracing and output results
        stop_tracing(output_file)

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='Trace Python program execution')
    parser.add_argument('script', help='The Python script to trace')
    parser.add_argument('-o', '--output', help='Output file for trace results')
    parser.add_argument('--scope', help='Directory path to restrict tracing to')
    parser.add_argument('--no-external-calls', action='store_true', 
                       help='Disable tracking of calls to functions outside the scope')
    parser.add_argument('script_args', nargs='*', help='Arguments for the script being traced')
    
    args, unknown = parser.parse_known_args()
    
    if not args.script:
        print("Usage: tracer <script_to_trace.py> [options] [script_args...]")
        sys.exit(1)

    # Run the tracer
    run_tracer(
        script_path=args.script,
        output_file=args.output,
        scope_path=args.scope,
        track_external_calls=not args.no_external_calls,
        script_args=args.script_args + unknown
    )

if __name__ == "__main__":
    main()