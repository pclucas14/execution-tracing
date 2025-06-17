import sys
import os
import argparse
from tracer.core import start_tracing, stop_tracing

def trace_pytest_main():
    """Entry point for trace_pytest command."""
    # Set up argument parser for pytest tracing
    parser = argparse.ArgumentParser(
        description='Trace pytest execution',
        usage='trace_pytest [pytest args...] [-o OUTPUT] [--scope SCOPE] [--no-external-calls] [--no-imports]'
    )
    parser.add_argument('-o', '--output', 
                       default='pytest_trace_output.json',
                       help='Output file for trace results (default: pytest_trace_output.json)')
    parser.add_argument('--scope', help='Directory path to restrict tracing to')
    parser.add_argument('--no-external-calls', action='store_true', 
                       help='Disable tracking of calls to functions outside the scope')
    parser.add_argument('--no-imports', action='store_true', 
                       help='Disable tracking of import related calls')
    
    # Parse known args, leaving pytest args for later
    args, pytest_args = parser.parse_known_args()
    
    # Import pytest
    try:
        import pytest
    except ImportError:
        print("Error: pytest is not installed. Please install it with: pip install pytest")
        sys.exit(1)
    
    # Determine tracing scope
    scope_path = args.scope
    if not scope_path:
        # Default to current working directory
        scope_path = os.getcwd()
        print(f'No scope specified, using current directory: {scope_path}')
    else:
        scope_path = os.path.abspath(scope_path)
        print(f'Scope path set to: {scope_path}')
    
    # Start tracing
    print(f"Tracing pytest execution with args: {' '.join(pytest_args)}")
    print(f"Tracing scope: {scope_path}")
    print(f"Output file: {args.output}")
    track_external = not args.no_external_calls
    print(f"Track external calls: {track_external}")
    
    start_tracing(
        scope_path=scope_path, 
        main_file=None,  # No specific main file for pytest
        track_external_calls=track_external, 
        track_imports=not args.no_imports
    )
    
    try:
        # Run pytest with the provided arguments
        exit_code = pytest.main(pytest_args)
    finally:
        # Stop tracing and output results
        stop_tracing(args.output)
    
    # Exit with pytest's exit code
    sys.exit(exit_code)

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Trace Python program execution')
    parser.add_argument('script', help='The Python script to trace')
    parser.add_argument('-o', '--output', help='Output file for trace results')
    parser.add_argument('--scope', help='Directory path to restrict tracing to')
    parser.add_argument('--no-external-calls', action='store_true', 
                       help='Disable tracking of calls to functions outside the scope')
    parser.add_argument('--no-imports', action='store_true', 
                       help='Disable tracking of import related calls')
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
    start_tracing(scope_path=scope_path, main_file=script_to_trace, track_external_calls=track_external, track_imports=not args.no_imports)
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

'''
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
'''

def where_command():
    from tracer.where import IterationBreakpointTracer
    parser = argparse.ArgumentParser(description="Run a Python script and print stack trace at a breakpoint.")
    parser.add_argument("--file", help="Target Python file to run")
    parser.add_argument("--scope", type=str, default=None, help="Constrain the logging to the given scope. If None, it logs all traces.")
    parser.add_argument("--output_file", type=str, help="File name to save the tracing output")
    parser.add_argument("--line", type=int, help="Line number for the breakpoint")
    parser.add_argument("--iterations", type=int, help="Number of times to hit the breakpoint before printing stack trace")
    parser.add_argument('--args', nargs=argparse.REMAINDER, help='Arguments for the target script')
    args = parser.parse_args()

    filename = args.file
    lineno = args.line
    sys.argv = [filename] + (args.args if args.args is not None else [])
    print("-"*40)
    print(f"Running file [{filename}]. Setting breakpoint in line [{args.line}] for [{args.iterations}] iteration!")
    print("-"*40)
    tracer = IterationBreakpointTracer(filename, lineno, args.iterations, args.output_file, args.scope)
    with open(filename, "rb") as fp:
        code = compile(fp.read(), filename, 'exec')
        tracer.run(code, globals(), globals())

if __name__ == "__main__":
    main()
