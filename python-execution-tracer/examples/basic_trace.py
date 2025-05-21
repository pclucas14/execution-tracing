def main():
    import sys
    import os
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Trace Python program execution')
    parser.add_argument('script', help='The Python script to trace')
    parser.add_argument('-o', '--output', help='Output file for trace results')
    parser.add_argument('script_args', nargs='*', help='Arguments for the script being traced')
    
    args, unknown = parser.parse_known_args()
    
    # Add the project root directory to Python's path
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.insert(0, project_root)
    
    from src.tracer.core import start_tracing, stop_tracing

    if not args.script:
        print("Usage: python basic_trace.py <script_to_trace.py> [args...]")
        sys.exit(1)

    script_to_trace = args.script
    
    # Set script args back in sys.argv for the target script to use
    sys.argv = [script_to_trace] + args.script_args + unknown

    start_tracing()
    try:
        exec(open(script_to_trace).read(), {'__name__': '__main__', '__file__': script_to_trace})
    finally:
        stop_tracing(args.output)

if __name__ == "__main__":
    main()