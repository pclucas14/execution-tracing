def main():
    import sys
    from tracer.core import start_tracing, stop_tracing
    from tracer.hooks import apply_filters

    # Example filter function to log only specific function calls
    def filter_function_call(func_name):
        return func_name in ["target_function", "another_function"]

    # Apply filters to the tracer
    apply_filters(filter_function_call)

    # Start tracing
    start_tracing()

    # Import and run the target program
    if len(sys.argv) > 1:
        target_program = sys.argv[1]
        exec(open(target_program).read())
    else:
        print("Please provide a target program to trace.")

    # Stop tracing
    stop_tracing()

if __name__ == "__main__":
    main()