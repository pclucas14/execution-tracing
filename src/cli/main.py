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
    parser.add_argument('--track-executed-lines', action='store_true',
                       help='Track all executed lines of code (file path, line number)')
    
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
        track_imports=not args.no_imports,
        track_executed_lines=args.track_executed_lines
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
    parser.add_argument('--track-executed-lines', action='store_true',
                       help='Track all executed lines of code (file path, line number)')
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
    start_tracing(scope_path=scope_path, main_file=script_to_trace, track_external_calls=track_external, track_imports=not args.no_imports, track_executed_lines=args.track_executed_lines)
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
    from tracer.where import main as where_main
    parser = argparse.ArgumentParser(
        description="Run a Python script and print stack trace at a breakpoint.",
        usage='trace_where <script_to_run.py> [script args...] --file FILE --line LINE --iterations N [-o OUTPUT] [--scope SCOPE]'
    )
    
    # Positional argument for the script to run
    parser.add_argument("script", help="The Python script to run")
    
    # Required arguments for breakpoint
    parser.add_argument("--file", required=True, help="Target file where to set the breakpoint")
    parser.add_argument("--line", type=int, required=True, help="Line number for the breakpoint")
    parser.add_argument("--iterations", type=int, required=True, help="Number of times to hit the breakpoint before printing stack trace")
    
    # Optional arguments
    parser.add_argument("-o", "--output_file", type=str, help="File name to save the tracing output")
    parser.add_argument("--scope", type=str, default=None, help="Constrain the logging to the given scope. If None, it logs all traces.")
    parser.add_argument("--track-executed-lines", action="store_true", help="Track all executed lines of code (file path, line number)")
    
    # Parse known args to handle script arguments
    args, script_args = parser.parse_known_args()
    
    # Get absolute paths
    script_path = os.path.abspath(args.script)
    breakpoint_file = os.path.abspath(args.file)
    
    # Default output file if not specified
    if not args.output_file:
        output_file = f"trace_where_output_{os.path.basename(args.script).replace('.py', '')}"
    else:
        output_file = args.output_file
    
    # Resolve scope path
    scope_path = None
    if args.scope:
        scope_path = os.path.abspath(os.path.expanduser(args.scope))
    else:
        # Default to the directory containing the script
        scope_path = os.path.dirname(script_path)
    
    print(f"Running trace_where:")
    print(f"  Script: {script_path}")
    print(f"  Breakpoint: {breakpoint_file}:{args.line}")
    print(f"  Iterations: {args.iterations}")
    print(f"  Output: {output_file}")
    if scope_path:
        print(f"  Scope: {scope_path}")
    
    # Run the tracer
    where_main(
        script_path=script_path,
        breakpoint_file=breakpoint_file,
        lineno=args.line,
        iterations=args.iterations,
        output_file=output_file,
        scope_path=scope_path,  # Changed from scope_dir
        script_args=script_args,
        track_executed_lines=args.track_executed_lines
    )

def where_pytest_command():
    from tracer.where import main_pytest as where_main_pytest
    parser = argparse.ArgumentParser(
        description="Run pytest and print stack trace at a breakpoint.",
        usage='trace_where_pytest [pytest args...] --file FILE --line LINE --iterations N [-o OUTPUT] [--scope SCOPE] [--continue]'
    )
    
    # Required arguments for breakpoint
    parser.add_argument("--file", required=True, help="Target file where to set the breakpoint")
    parser.add_argument("--line", type=int, required=True, help="Line number for the breakpoint")
    parser.add_argument("--iterations", type=int, required=True, help="Number of times to hit the breakpoint before printing stack trace")
    
    # Optional arguments
    parser.add_argument("-o", "--output_file", type=str, help="File name to save the tracing output")
    parser.add_argument("--scope", type=str, default=None, help="Constrain the logging to the given scope. If None, it logs all traces.")
    parser.add_argument("--continue", dest="continue_execution", action="store_true", 
                       help="Continue test execution after hitting the breakpoint (don't exit)")
    parser.add_argument("--track-executed-lines", action="store_true", help="Track all executed lines of code (file path, line number)")
    
    # Parse known args to handle pytest arguments
    args, pytest_args = parser.parse_known_args()
    
    # Get absolute paths
    breakpoint_file = os.path.abspath(args.file)
    
    # Default output file if not specified
    if not args.output_file:
        output_file = f"trace_where_pytest_output_{os.path.basename(args.file).replace('.py', '')}"
    else:
        output_file = args.output_file
    
    # Resolve scope path
    scope_path = None
    if args.scope:
        scope_path = os.path.abspath(os.path.expanduser(args.scope))
    else:
        # Default to current working directory
        scope_path = os.getcwd()
    
    print(f"Running trace_where_pytest:")
    print(f"  Pytest args: {' '.join(pytest_args)}")
    print(f"  Breakpoint: {breakpoint_file}:{args.line}")
    print(f"  Iterations: {args.iterations}")
    print(f"  Output: {output_file}")
    print(f"  Scope: {scope_path}")
    
    # Run the tracer
    where_main_pytest(
        pytest_args=pytest_args,
        breakpoint_file=breakpoint_file,
        lineno=args.line,
        iterations=args.iterations,
        output_file=output_file,
        scope_path=scope_path,
        continue_execution=args.continue_execution,
        track_executed_lines=args.track_executed_lines
    )

if __name__ == "__main__":
    main()
