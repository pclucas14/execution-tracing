import sys
import inspect
import os
from typing import Dict, Any, Set, Optional

# Global tracer state
_tracer = None
_call_depth = 0
TRACER_SCOPE = None  # Directory path to restrict tracing to

class Tracer:
    def __init__(self, scope_path=None):
        self.is_tracing = False
        self.log = []
        self.seen_functions = set()
        self.scope_path = scope_path
        
    def start(self):
        self.is_tracing = True
    
    def stop(self):
        self.is_tracing = False
    
    def log_function_call(self, function_name, args, file_path=None, line_number=None, caller_info=None, depth=0):
        """Log a function call with context information and line numbers."""
        if not self.is_tracing:
            return
            
        # Format the arguments for better readability
        args_str = {}
        try:
            for k, v in args.items():
                try:
                    if isinstance(v, (list, dict, tuple, set)) and len(str(v)) > 100:
                        args_str[k] = f"{type(v).__name__} with {len(v)} items"
                    else:
                        val_str = str(v)
                        if len(val_str) > 100:
                            args_str[k] = val_str[:97] + "..."
                        else:
                            args_str[k] = val_str
                except Exception:
                    args_str[k] = f"<{type(v).__name__}>"
        except Exception:
            args_str = {"error": "Could not format arguments"}
        
        # Prepare file and line information
        location_info = ""
        if file_path:
            location_info = f"{os.path.basename(file_path)}"
            if line_number:
                location_info += f":{line_number}"
        
        # Add caller information
        call_source = ""
        if caller_info:
            caller_file, caller_line = caller_info
            if caller_file and caller_line:
                call_source = f" [called from {os.path.basename(caller_file)}:{caller_line}]"
        
        indent = "  " * depth
        entry = f"{indent}{location_info} - {function_name}{call_source}: {args_str}"
        self.log.append(entry)
    
    def get_trace_output(self):
        return "\n".join(self.log)

def _is_in_scope(file_path):
    """Check if a file is within the tracing scope."""
    global TRACER_SCOPE
    
    if not TRACER_SCOPE or not file_path:
        return False
        
    # Skip Python standard library files
    if "site-packages" in file_path or "lib/python" in file_path:
        return False
        
    # Check if the file is within our defined scope
    return file_path.startswith(TRACER_SCOPE)

def _get_caller_info(frame):
    """Get the caller's file and line number."""
    try:
        # The caller is one frame back
        caller = frame.f_back
        if caller:
            return (caller.f_code.co_filename, caller.f_lineno)
    except Exception:
        pass
    return (None, None)

def _trace_function(frame, event, arg):
    """Simple trace function that only traces functions within the defined scope."""
    global _tracer, _call_depth
    
    # Always return the function to maintain tracing
    if not _tracer:
        return _trace_function
    
    try:
        if event == 'call':
            # Get function name and file path
            code = frame.f_code
            func_name = code.co_name
            file_path = code.co_filename
            line_number = frame.f_lineno  # Line number where the function is defined
            
            # Get caller information
            caller_info = _get_caller_info(frame)
            
            # Check if we should trace this file
            if not _is_in_scope(file_path):
                return _trace_function
                
            # Skip special methods and common internals
            if func_name.startswith('__') and func_name.endswith('__'):
                return _trace_function
            if func_name in ('<genexpr>', '<listcomp>', '<dictcomp>', '<setcomp>'):
                return _trace_function
                
            # Track call depth for indentation
            _call_depth += 1
            
            # Get arguments safely
            arg_values = {}
            try:
                args = inspect.getargvalues(frame)
                for arg_name in args.args:
                    if arg_name in args.locals:
                        arg_values[arg_name] = args.locals[arg_name]
                
                # Add varargs and kwargs
                if args.varargs and args.varargs in args.locals:
                    arg_values['*' + args.varargs] = args.locals[args.varargs]
                
                if args.keywords and args.keywords in args.locals:
                    arg_values['**' + args.keywords] = args.locals[args.keywords]
            except Exception:
                # Silently fail if we can't get args
                pass
            
            # Log the call
            _tracer.log_function_call(
                func_name, 
                arg_values, 
                file_path,
                line_number,
                caller_info,
                depth=_call_depth-1
            )
            
        elif event == 'return':
            # Maintain proper indentation on return
            if _call_depth > 0:
                _call_depth -= 1
    except Exception:
        # Silently fail on any error
        pass
    
    return _trace_function

def set_tracer_scope(scope_path):
    """Set the directory scope for tracing."""
    global TRACER_SCOPE
    
    if scope_path:
        # Ensure it's an absolute path
        TRACER_SCOPE = os.path.abspath(scope_path)
        print(f"Tracer scope set to: {TRACER_SCOPE}")
    else:
        TRACER_SCOPE = None

def start_tracing(scope_path=None):
    """Start tracing with a scope-limited approach."""
    global _tracer, _call_depth, TRACER_SCOPE
    
    # Reset state
    _call_depth = 0
    
    # Set scope if provided
    if scope_path:
        set_tracer_scope(scope_path)
    
    # Create and start the tracer
    _tracer = Tracer(scope_path=TRACER_SCOPE)
    _tracer.start()
    
    # Install trace function
    sys.settrace(_trace_function)
    
    # Also trace threads if possible
    try:
        import threading
        threading.settrace(_trace_function)
    except Exception:
        pass

def stop_tracing(output_file=None):
    """Stop tracing and save output."""
    global _tracer, _call_depth
    
    # Disable tracing
    sys.settrace(None)
    try:
        import threading
        threading.settrace(None)
    except Exception:
        pass
    
    if _tracer:
        _tracer.stop()
        _call_depth = 0
        
        # Get trace output
        trace_output = _tracer.get_trace_output()
        print(f"\nTraced {len(_tracer.log)} function calls")
        
        # Write to file if specified
        if output_file:
            try:
                directory = os.path.dirname(output_file)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)
                    
                with open(output_file, 'w') as f:
                    f.write(trace_output)
                print(f"Trace output written to: {output_file}")
            except Exception as e:
                print(f"Error writing trace output: {e}")
            
        return trace_output
    return ""