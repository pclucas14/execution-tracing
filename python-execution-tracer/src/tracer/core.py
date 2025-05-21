import sys
import inspect
import os

# Global tracer instance
_tracer = None

class Tracer:
    def __init__(self):
        self.is_tracing = False
        self.log = []
    
    def start(self):
        self.is_tracing = True
    
    def stop(self):
        self.is_tracing = False
    
    def log_function_call(self, function_name, args):
        if self.is_tracing:
            self.log.append((function_name, args))
    
    def get_trace_output(self):
        return "\n".join([f"{func}: {args}" for func, args in self.log])
    
    def dump_trace_output(self, filename):
        """Write trace output to a file."""
        output = self.get_trace_output()
        with open(filename, 'w') as f:
            f.write(output)
        return output

def _trace_calls(frame, event, arg):
    """Internal function used for tracing."""
    global _tracer
    
    if event == 'call':
        # Get function name
        code = frame.f_code
        func_name = code.co_name
        
        # Skip certain functions
        if func_name == '_trace_calls' or func_name.startswith('__'):
            return _trace_calls
        
        # Get arguments
        args = inspect.getargvalues(frame)
        arg_values = {}
        
        for arg_name in args.args:
            if arg_name in args.locals:
                arg_values[arg_name] = args.locals[arg_name]
        
        # Add any varargs
        if args.varargs and args.varargs in args.locals:
            arg_values['*' + args.varargs] = args.locals[args.varargs]
        
        # Add any kwargs
        if args.keywords and args.keywords in args.locals:
            arg_values['**' + args.keywords] = args.locals[args.keywords]
        
        # Log the function call
        _tracer.log_function_call(func_name, arg_values)
    
    return _trace_calls

def start_tracing():
    """Start the tracing process."""
    global _tracer
    _tracer = Tracer()
    _tracer.start()
    sys.settrace(_trace_calls)

def stop_tracing(output_file=None):
    """
    Stop the tracing process.
    
    Args:
        output_file (str, optional): Path to file where trace output should be written.
                                    If None, output is only returned/printed.
    
    Returns:
        str: The trace output.
    """
    global _tracer
    if _tracer:
        _tracer.stop()
        sys.settrace(None)
        
        # Get the trace output
        trace_output = _tracer.get_trace_output()
        
        # Print to console
        print(trace_output)
        
        # Write to file if specified
        if output_file:
            directory = os.path.dirname(output_file)
            if directory and not os.path.exists(directory):
                os.makedirs(directory)
                
            with open(output_file, 'w') as f:
                f.write(trace_output)
            print(f"Trace output written to: {output_file}")
            
        return trace_output
    return ""