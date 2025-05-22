import sys
import os
import argparse

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Trace Python program execution')
    parser.add_argument('script', help='The Python script to trace')
    parser.add_argument('-o', '--output', help='Output file for trace results')
    parser.add_argument('--scope', help='Directory path to restrict tracing to')
    parser.add_argument('script_args', nargs='*', help='Arguments for the script being traced')
    
    args, unknown = parser.parse_known_args()
    
    # Add the project root directory to Python's path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    
    from src.tracer.core import start_tracing, stop_tracing, set_tracer_scope

    if not args.script:
        print("Usage: python basic_trace.py <script_to_trace.py> [args...]")
        sys.exit(1)

    # Get absolute path to the script
    script_to_trace = os.path.abspath(args.script)
    
    # Set up script args in sys.argv for the target script
    sys.argv = [script_to_trace] + args.script_args + unknown

    # Determine tracing scope
    scope_path = args.scope
    if not scope_path:
        # Default to the directory containing the script
        scope_path = os.path.dirname(script_to_trace)
        
    # For MTTL project structure, try to detect the mttl directory
    if 'mttl' in script_to_trace:
        mttl_index = script_to_trace.find('mttl')
        if mttl_index > 0:
            # Use the mttl directory as scope
            scope_path = os.path.abspath(script_to_trace[:mttl_index+4])
            print(f"Detected MTTL project, setting scope to: {scope_path}")

    # Start tracing
    print(f"Tracing script: {script_to_trace}")
    print(f"Tracing scope: {scope_path}")
    start_tracing(scope_path=scope_path, main_file=script_to_trace)
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

if __name__ == "__main__":
    main()