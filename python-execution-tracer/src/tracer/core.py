import sys
import inspect
import os
import types
from typing import Dict, Any, Set, Optional
import importlib.util
import re

# Global tracer instance
_tracer = None
_traced_script_path = None
_tracked_modules = set()
_call_depth = 0
_frame_stack = []

class Tracer:
    def __init__(self, trace_external=False, max_depth=100, recursive=True, include_patterns=None, exclude_patterns=None):
        self.is_tracing = False
        self.log = []
        self.trace_external = trace_external
        self.seen_functions = set()
        self.max_depth = max_depth  # Increased maximum call depth
        self.recursive = recursive   # Whether to trace recursively into function calls
        self.include_patterns = include_patterns or []  # Regex patterns for modules to include
        self.exclude_patterns = exclude_patterns or []  # Regex patterns for modules to exclude
    
    def start(self):
        self.is_tracing = True
    
    def stop(self):
        self.is_tracing = False
    
    def log_function_call(self, function_name, args, module_name=None, file_path=None, depth=0):
        """Log a function call with context information."""
        if not self.is_tracing:
            return
            
        # Format the arguments more cleanly
        args_str = {}
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
        
        # Add indentation to show call hierarchy
        prefix = ""
        if file_path:
            prefix = f"{os.path.basename(file_path)} - "
        
        indent = "  " * depth
        entry = f"{indent}{prefix}{function_name}: {args_str}"
        self.log.append(entry)
    
    def get_trace_output(self):
        return "\n".join(self.log)

def _should_trace_module(module_name: str, file_path: str, trace_external: bool) -> bool:
    """Determine if we should trace functions from this module."""
    global _tracked_modules, _tracer
    
    # Always trace the main module
    if module_name == "__main__":
        return True
    
    # Skip certain internal Python modules
    if (
        module_name.startswith("_") or 
        module_name in ("marshal", "importlib", "encodings", "codecs", 
                      "gc", "abc", "io", "stat", "posixpath", "runpy") or
        "encodings." in module_name
    ):
        return False
    
    # Apply exclusion patterns
    if _tracer and _tracer.exclude_patterns:
        for pattern in _tracer.exclude_patterns:
            if re.search(pattern, module_name) or (file_path and re.search(pattern, file_path)):
                return False
    
    # Apply inclusion patterns - these take precedence
    if _tracer and _tracer.include_patterns:
        for pattern in _tracer.include_patterns:
            if re.search(pattern, module_name) or (file_path and re.search(pattern, file_path)):
                return True
    
    # Check if module is in tracked_modules
    module_base = module_name.split('.')[0]
    if module_base in _tracked_modules:
        return True
    
    # Guess if a file is part of the project by checking if it's in or under 
    # the project directory
    if file_path:
        project_dir = os.path.dirname(os.path.dirname(_traced_script_path))
        if file_path.startswith(project_dir):
            return True
    
    # If we're tracing external modules, allow it
    if trace_external:
        return True
        
    return False

def _trace_calls(frame, event, arg):
    """Internal function used for tracing."""
    global _tracer, _traced_script_path, _call_depth, _frame_stack
    
    if event == 'call':
        # Get function name, module and file info
        code = frame.f_code
        func_name = code.co_name
        file_path = code.co_filename
        module_name = frame.f_globals.get('__name__', '')
        
        # Skip our internal tracer functions
        if func_name in ('_trace_calls', 'start_tracing', 'stop_tracing'):
            return _trace_calls
            
        # Skip Python internals and special methods
        if func_name.startswith('__') and func_name.endswith('__'):
            return _trace_calls
        
        # Skip common generators and comprehensions that pollute the trace
        if func_name in ('<genexpr>', '<listcomp>', '<dictcomp>', '<setcomp>'):
            if not _tracer.trace_external:  # Skip these only if not tracing externals
                return _trace_calls
        
        # Manage call depth
        _call_depth += 1
        _frame_stack.append(frame)
        
        if _call_depth > _tracer.max_depth:
            _call_depth -= 1
            _frame_stack.pop()
            return _trace_calls
        
        # Check if this module should be traced
        if not _should_trace_module(module_name, file_path, _tracer.trace_external):
            _call_depth -= 1
            try:
                _frame_stack.pop()
            except:
                pass
            return _trace_calls
        
        # Get arguments
        try:
            args = inspect.getargvalues(frame)
            arg_values = {}
            
            for arg_name in args.args:
                if arg_name in args.locals:
                    arg_values[arg_name] = args.locals[arg_name]
            
            # Add varargs and kwargs
            if args.varargs and args.varargs in args.locals:
                arg_values['*' + args.varargs] = args.locals[args.varargs]
            
            if args.keywords and args.keywords in args.locals:
                arg_values['**' + args.keywords] = args.locals[args.keywords]
        except Exception as e:
            # Fallback if getting arguments fails
            arg_values = {"<error>": f"Could not inspect arguments: {str(e)}"}
        
        # Log the function call
        _tracer.log_function_call(
            func_name, 
            arg_values, 
            module_name, 
            file_path,
            depth=_call_depth-1
        )
        
        # Determine whether to continue tracing into this call
        if not _tracer.recursive and _call_depth > 1:
            _call_depth -= 1
            _frame_stack.pop()
            return None  # Stop tracing this call branch
            
        return _trace_calls
    
    elif event == 'return':
        if _call_depth > 0:
            _call_depth -= 1
            if _frame_stack:  # Guard against empty stack
                _frame_stack.pop()
    
    return _trace_calls

def _find_project_modules(root_dir):
    """Find all Python modules in a project directory."""
    global _tracked_modules
    
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                module_path = os.path.join(root, file)
                module_name = os.path.splitext(file)[0]
                _tracked_modules.add(module_name)
                
                # Try to infer package name
                rel_path = os.path.relpath(root, root_dir)
                if rel_path != '.' and not rel_path.startswith('..'):
                    package = rel_path.replace(os.sep, '.')
                    _tracked_modules.add(package)
                    _tracked_modules.add(f"{package}.{module_name}")

def start_tracing(trace_external=False, max_depth=100, recursive=True, 
                 include_patterns=None, exclude_patterns=None):
    """
    Start the tracing process.
    
    Args:
        trace_external (bool): Whether to trace functions from external libraries.
        max_depth (int): Maximum depth of function calls to trace.
        recursive (bool): Whether to trace recursively into function calls.
        include_patterns (list): Regex patterns for modules to include regardless of other rules.
        exclude_patterns (list): Regex patterns for modules to exclude regardless of other rules.
    """
    global _tracer, _traced_script_path, _tracked_modules, _call_depth, _frame_stack
    
    # Reset tracking state
    _call_depth = 0
    _tracked_modules = set()
    _frame_stack = []
    
    # Register the main script and its directory
    _traced_script_path = os.path.abspath(sys.argv[0])
    _register_module(_traced_script_path)
    
    # Find project modules
    project_root = os.path.dirname(os.path.dirname(_traced_script_path))
    _find_project_modules(project_root)
    
    # Initialize and start the tracer with enhanced settings
    _tracer = Tracer(
        trace_external=trace_external,
        max_depth=max_depth,
        recursive=recursive,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns
    )
    _tracer.start()
    
    # Set up the trace function
    sys.settrace(_trace_calls)
    
    # Also trace threads if possible
    try:
        import threading
        threading.settrace(_trace_calls)
    except (ImportError, AttributeError):
        pass

def _register_module(module_path: str):
    """Register a module to be traced."""
    global _tracked_modules
    if module_path:
        module_name = os.path.splitext(os.path.basename(module_path))[0]
        _tracked_modules.add(module_name)

def stop_tracing(output_file=None):
    """
    Stop the tracing process.
    
    Args:
        output_file (str, optional): Path to file where trace output should be written.
    
    Returns:
        str: The trace output.
    """
    global _tracer, _frame_stack
    if _tracer:
        _tracer.stop()
        sys.settrace(None)
        _frame_stack = []  # Clear frame stack
        
        # Disable thread tracing if possible
        try:
            import threading
            threading.settrace(None)
        except (ImportError, AttributeError):
            pass
        
        # Get the trace output
        trace_output = _tracer.get_trace_output()
        
        # Print a summary to console
        print(f"\nTraced {len(_tracer.log)} function calls")
        
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