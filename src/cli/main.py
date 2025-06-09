import sys
import os
import argparse
from tracer.core import start_tracing, stop_tracing

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Trace Python program execution')
    parser.add_argument('script', help='The Python script to trace')
    parser.add_argument('-o', '--output', help='Output file for trace results')
    parser.add_argument('--scope', help='Directory path to restrict tracing to')
    parser.add_argument('--no-external-calls', action='store_true', 
                       help='Disable tracking of calls to functions outside the scope')
    parser.add_argument('script_args', nargs='*', help='Arguments for the script being traced')
    
    args, unknown = parser.parse_known_args()
    
    # Import tracer modules
    from tracer.core import set_tracer_scope

    if not args.script:
        print("Usage: trace_program <script_to_trace.py> [args...]")
        sys.exit(1)

    # Get absolute path to the script
    script_to_trace = os.path.abspath(args.script)
    
    # Set up script args in sys.argv for the target script
    sys.argv = [script_to_trace] + args.script_args + unknown

    # Determine tracing scope
    scope_path = args.scope
    if not scope_path:
        # Default to the directory containing the script
        print(f'No scope specified, using directory of the script: {script_to_trace}')
        scope_path = os.path.dirname(script_to_trace)
    else:
        # Resolve the scope path to an absolute path
        scope_path = os.path.abspath(scope_path)
        print(f'Scope path set to: {scope_path}')

    # Start tracing
    print(f"Tracing script: {script_to_trace}")
    print(f"Tracing scope: {scope_path}")
    track_external = not args.no_external_calls
    print(f"Track external calls: {track_external}")
    start_tracing(scope_path=scope_path, main_file=script_to_trace, track_external_calls=track_external)
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
        stop_tracing(args.output)

def run_tracer(args):
    """Run the tracer with the given arguments."""
    from tracer.core import start_tracing, stop_tracing
    
    # Start tracing with the provided arguments
    start_tracing(
        scope_path=getattr(args, 'scope_path', None),
        main_file=getattr(args, 'main_file', None),
        track_external_calls=getattr(args, 'track_external_calls', True)
    )
    
    # Execute the target script/module
    if hasattr(args, 'target') and args.target:
        exec(open(args.target).read())
    
    # Stop tracing and save output
    output_file = getattr(args, 'output_file', None)
    return stop_tracing(output_file)

if __name__ == "__main__":
    main()
