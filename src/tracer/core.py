import sys
import inspect
import os
import json
from . import utils

# Global tracer state
_tracer = None
_call_depth = 0
TRACER_SCOPE = None  # Directory path to restrict tracing to

class Tracer:
    def __init__(self, scope_path=None, exclude_paths=None, output_file=None, main_file=None, track_external_calls=True, track_imports=True, track_executed_lines=False):
        self.is_tracing = False
        self.log = []  # Now a list of dicts for JSON output
        self.seen_functions = set()
        self.scope_path = scope_path  # Keep as scope_path for consistency
        self.exclude_paths = exclude_paths or []
        self.output_file = output_file
        self.main_file = main_file
        self.call_stack = []  # Track the full call stack
        self.in_scope_depth = 0  # Track depth within our scope
        self.scope_entered = False  # Track if we've entered our scope
        self.traced_calls = []  # Track which calls we've traced for proper depth management
        
        # Add a flag to capture dunder methods
        self.trace_dunder_methods = True
        
        # Add flag to control tracking of external calls
        self.track_external_calls = track_external_calls
        
        # Add flag to control tracking of import calls
        self.track_imports = track_imports
        
        # Debug mode
        self.debug = True  # Enable debug logging
        
        # Store the original command
        self.original_command = ' '.join(sys.argv)
        
        # Add function call counter
        self.function_call_counts = {}
        
        # Add executed lines tracking
        self.track_executed_lines = track_executed_lines
        self.executed_lines = {}  # Changed from set to dict: {file_name: set(line_numbers)}

        
    def start(self):
        self.is_tracing = True
    
    def stop(self):
        self.is_tracing = False
    
    def log_function_call(self, function_name, args, file_path=None, line_number=None, caller_info=None, depth=0, is_external=False, parent_call=None):
        """Log a function call as a dict for JSON output."""
        if not self.is_tracing:
            return

        # Determine call type first
        call_type = utils.determine_call_type(function_name, file_path, caller_info, is_external, parent_call)

        # Only track call counts for actual function/method calls
        call_types_with_counts = {
            'function_call', 'method', 'class_instantiation', 
            'special_method', 'callable_object', 'lambda_function',
            'external_call'
        }
        
        current_call_number = None
        if call_type in call_types_with_counts:
            # Create a unique key for the function based on name and location
            function_key = f"{function_name}@{file_path}:{line_number}"
            
            # Increment call count for this function
            if function_key not in self.function_call_counts:
                self.function_call_counts[function_key] = 0
            self.function_call_counts[function_key] += 1
            current_call_number = self.function_call_counts[function_key]

        # Prepare location info
        location = None
        if file_path and line_number:
            # For external calls, show absolute path
            relative_path = utils.get_relative_path(file_path, self.scope_path)
            location = f"{relative_path}:{line_number}"
        elif file_path:
            relative_path = utils.get_relative_path(file_path, self.scope_path)
            location = relative_path
        else:
            location = "unknown"

        # Prepare parent location - show absolute path if outside scope
        parent_location = None
        if caller_info and caller_info[0] and caller_info[1]:
            relative_caller_path = utils.get_relative_path(caller_info[0], self.scope_path)
            parent_location = f"{relative_caller_path}:{caller_info[1]}"

        # Format arguments intelligently
        formatted_args = utils.format_arguments(args)

        entry = {
            "location": location,
            "parent_location": parent_location,
            "parent_call": parent_call,  # Add the actual code that made this call
            "name": function_name,
            "arguments": formatted_args,
            "depth": depth,
            "is_external": is_external,
            "call_type": call_type,
            "args": {},
            "kwargs": formatted_args,
        }
        
        # Only add number_of_calls if it's tracked for this call type
        if current_call_number is not None:
            entry["number_of_calls"] = current_call_number
            
        self.log.append(entry)

    def log_executed_line(self, file_path, line_number):
        """Log an executed line if tracking is enabled."""
        print('enter')
        if self.track_executed_lines and self.is_tracing:
            if file_path not in self.executed_lines:
                self.executed_lines[file_path] = set()
            self.executed_lines[file_path].add(line_number)
            print(f'Executed line {line_number} in {file_path}')

    def _classify_call_type(self, function_name, file_path, caller_info, is_external, parent_call=None):
        """Deprecated: Use utils.determine_call_type instead."""
        return utils.determine_call_type(function_name, file_path, caller_info, is_external, parent_call)

    def _determine_call_type(self, function_name, file_path, caller_info, is_external, parent_call=None, frame=None):
        """Standardized method name for call type classification."""
        return utils.determine_call_type(function_name, file_path, caller_info, is_external, parent_call, frame)

    def _is_class_declaration(self, function_name, caller_info, parent_call=None):
        """Check if this is a class declaration (class definition) rather than instantiation."""
        return utils.is_class_declaration(function_name, caller_info, parent_call)

    def get_trace_output(self):
        """Return the log as a JSON string with metadata."""
        try:
            # Standardized metadata structure
            metadata = {
                "original_command": self.original_command,
                "scope_path": self.scope_path,  # Always use scope_path
                "timestamp": __import__('datetime').datetime.now().isoformat()
            }
            
            # Add optional fields if they exist
            if hasattr(self, 'main_file') and self.main_file:
                metadata["main_file"] = self.main_file
            
            metadata["total_frames"] = len(self.log)  # Use total_frames for consistency
            
            # Add executed lines if tracking was enabled
            print('final 1')
            if self.track_executed_lines:
                # Convert dict to sorted list of tuples for JSON serialization
                metadata["executed_lines"] = {k:list(v) for k, v in self.executed_lines.items()}
                metadata["executed_lines_count"] = sum(len(lines) for lines in self.executed_lines.values())
                print('final 2')
            
            output_data = {
                "metadata": metadata,
                "trace_data": self.log
            }
            return json.dumps(output_data, indent=2, default=str)
        except TypeError as e:
            # If there are still serialization issues, convert problematic objects to strings
            safe_log = []
            for entry in self.log:
                safe_entry = {}
                for key, value in entry.items():
                    safe_entry[str(key)] = self._make_json_safe(value)
                safe_log.append(safe_entry)
            
            output_data = {
                "metadata": {
                    "original_command": self.original_command,
                    "scope_path": self.scope_path,
                    "main_file": self.main_file,
                    "total_calls": len(safe_log),
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                },
                "trace_data": safe_log
            }
 
            # Add executed lines to metadata in safe format
            print(f'final 3')
            if self.track_executed_lines:
                metadata["executed_lines"] = {k:list(v) for k, v in self.executed_lines.items()}
                metadata["executed_lines_count"] = sum(len(lines) for lines in self.executed_lines.values())
                print(f'final 4')
            
            return json.dumps(output_data, indent=2, default=str)
    
    def _make_json_safe(self, obj):
        """Recursively make an object JSON-safe by converting problematic types."""
        return utils.make_json_safe(obj)

    def _format_arguments(self, args):
        """Format arguments intelligently for logging."""
        return utils.format_arguments(args)
    
    def _format_value(self, value):
        """Format a single value intelligently."""
        return utils.format_value(value)

    def _should_trace(self, frame):
        """Determine if a frame should be traced based on scope and function name."""
        file_path = frame.f_code.co_filename
        func_name = frame.f_code.co_name
        
        # Ensure we capture __call__ and other special methods
        should_exclude_dunder = (not self.trace_dunder_methods and 
                                func_name.startswith('__') and 
                                func_name != '__call__')
        
        if should_exclude_dunder:
            return False
            
        # Continue with existing scope checks
        return _is_in_scope(file_path)


    def should_trace(self, filename, func_name):
        """Check if this file/function should be traced."""
        # Your existing should_trace logic
        return _is_in_scope(filename)

    def trace_function_call(self, frame, event, arg):
        if not self.is_tracing:
            return self.trace_function_call
            
        filename = frame.f_code.co_filename
        func_name = frame.f_code.co_name
        
        if event == 'call':
            # Add to call stack regardless of whether we trace it
            self.call_stack.append((filename, func_name))
            
            # Check if this is our main file entering scope
            if not self.scope_entered and self.main_file in filename:
                self.scope_entered = True
                self.in_scope_depth = 0
            
            # Only track depth if we're in scope
            if self.scope_entered and self.should_trace(filename, func_name):
                # Format log entry with the current scope depth
                log_entry = self.format_log_entry(frame, self.in_scope_depth)
                self.log.append(log_entry)
                
                if self.output_file:
                    with open(self.output_file, 'a') as f:
                        f.write(log_entry + '\n')
                
                # Increment depth after logging (so main file starts at 0)
                self.in_scope_depth += 1
        
        elif event == 'return':
            # Remove from call stack
            if self.call_stack:
                self.call_stack.pop()
            
            # Decrement depth if we're returning from a traced function
            if self.scope_entered and self.in_scope_depth > 0:
                # Check if the function we're returning from was traced
                if self.should_trace(filename, func_name):
                    self.in_scope_depth -= 1
            
            # Check if we've exited our main scope
            if self.scope_entered and self.main_file in filename and len(self.call_stack) == 0:
                self.scope_entered = False
                self.in_scope_depth = 0
        
        return self.trace_function_call


    def calculate_indent_level(self):
        """Calculate indentation level based on distance from main file."""
        # Find the position of the main file in the call stack
        main_file_indices = [i for i, (filename, _) in enumerate(self.call_stack) 
                             if self.main_file in filename]
        
        if not main_file_indices:
            # If main file not found in stack, use the entire stack depth
            return len(self.call_stack)
        
        # Use the position after the last occurrence of main file
        main_file_pos = main_file_indices[-1]
        return len(self.call_stack) - main_file_pos - 1

    def format_log_entry(self, frame, depth):
        """Format a log entry with proper indentation based on call depth."""
        func_name = frame.f_code.co_name
        filename = os.path.basename(frame.f_code.co_filename)
        lineno = frame.f_lineno
        
        # Get function arguments
        args = self.get_function_args(frame)
        
        # Create indentation with tabs based on depth
        indent = '\t' * depth
        
        # Get caller info
        caller_info = self.get_caller_info()
        
        # Format: filename:line - function_name [TAB INDENTATION] [called from ...]: args
        return f"{filename}:{lineno} - {func_name} {indent}[called from {caller_info}]: {args}"

    def get_function_args(self, frame):
        """Extract function arguments from frame."""
        args = {}
        try:
            # Get argument names and values
            arginfo = inspect.getargvalues(frame)
            for arg_name in arginfo.args:
                if arg_name in arginfo.locals:
                    value = arginfo.locals[arg_name]
                    args[arg_name] = value
                            
            # Add varargs and kwargs if present
            if arginfo.varargs and arginfo.varargs in arginfo.locals:
                args['*' + arginfo.varargs] = arginfo.locals[arginfo.varargs]
            if arginfo.keywords and arginfo.keywords in arginfo.locals:
                args['**' + arginfo.keywords] = arginfo.locals[arginfo.keywords]
                
        except Exception:
            args = {"error": "Could not extract arguments"}
            
        return args

    def get_caller_info(self):
        """Get caller information from the call stack."""
        if len(self.call_stack) > 1:
            caller_file, _ = self.call_stack[-2]
            return os.path.basename(caller_file) + ":" + str(self._get_caller_line_number())
        return "unknown"
        
    def _get_caller_line_number(self):
        """Try to get the caller's line number from the current frame."""
        try:
            import sys
            frame = sys._getframe(2)  # Go back 2 frames
            while frame:
                if frame.f_code.co_filename == self.call_stack[-2][0]:
                    return frame.f_lineno
                frame = frame.f_back
        except Exception:
            pass
        return "?"

    def start_tracing(self):
        """Start the tracing process."""
        self.is_tracing = True
        self.call_stack = []
        self.in_scope_depth = 0
        self.scope_entered = False
        sys.settrace(self.trace_function_call)
        return self

    def stop_tracing(self):
        """Stop the tracing process."""
        self.is_tracing = False
        sys.settrace(None)
        self.call_stack = []
        self.in_scope_depth = 0
        self.scope_entered = False
        return self.log

    def _is_import_call(self, function_name, file_path, caller_info):
        """Check if a function call is related to module importing."""
        return utils.is_import_call(function_name, file_path, caller_info)

    def _get_relative_path(self, file_path):
        """Get relative path if within scope, otherwise return absolute path."""
        return utils.get_relative_path(file_path, self.scope_path)

    def _get_source_line(self, frame):
        """Extract the source code line(s) from a frame."""
        return utils.get_source_line(frame)
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
    """Get the caller's file and line number, skipping external calls if not tracking them."""
    global _tracer
    try:
        caller = frame.f_back
        
        # If not tracking external calls, find the nearest internal caller
        if not _tracer.track_external_calls:
            while caller:
                caller_path = caller.f_code.co_filename
                if _is_in_scope(caller_path):
                    return (caller_path, caller.f_lineno)
                caller = caller.f_back
        
        # Default behavior - return immediate caller
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
        # Track line execution if enabled
        if event == 'line' and _tracer.track_executed_lines:
            file_path = frame.f_code.co_filename
            line_number = frame.f_lineno
            
            # Only track lines within scope
            print(f'check scope')
            if _is_in_scope(file_path):
                _tracer.log_executed_line(file_path, line_number)
            
            return _trace_function
        
        if event == 'call':
            # Get function name and file path
            code = frame.f_code
            func_name = code.co_name
            file_path = code.co_filename
            line_number = frame.f_lineno
            
            # Get caller information
            caller_info = _get_caller_info(frame)
            
            # Track if we're entering the main file
            entering = _is_in_scope(file_path) if _tracer.main_file is None else _tracer.main_file in file_path
            if not _tracer.scope_entered and entering:
                _tracer.scope_entered = True
                _tracer.in_scope_depth = 0
                if _tracer.debug:
                    print(f"[DEBUG] Entered main scope in {file_path}")
            
            # Check if this call is from within our scope
            caller_in_scope = False
            if caller_info and caller_info[0]:
                caller_in_scope = _is_in_scope(caller_info[0])
            
            # Determine if we should log this call
            is_in_scope = _is_in_scope(file_path)
            is_external = not is_in_scope
            should_log = False
            should_recurse = False
            
            if is_in_scope:
                # Function is in scope - log and recurse
                should_log = True
                should_recurse = True
            elif caller_in_scope and _tracer.scope_entered and _tracer.track_external_calls:
                # Function is out of scope but called from in-scope - log but don't recurse (only if tracking external calls)
                should_log = True
                should_recurse = False
            
            if not should_log:
                # Return None to stop tracing this branch if we shouldn't recurse
                return _trace_function if should_recurse else None
            
            # Check if this is an import call and skip if import tracking is disabled
            if not _tracer.track_imports and utils.is_import_call(func_name, file_path, caller_info):
                return _trace_function if should_recurse else None
                
            # Skip special methods and common internals, but keep __init__ and __call__
            if func_name.startswith('__') and func_name.endswith('__') and func_name not in ('__call__', '__init__'):
                return _trace_function if should_recurse else None
            if func_name in ('<genexpr>', '<listcomp>', '<dictcomp>', '<setcomp>'):
                return _trace_function if should_recurse else None
            
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
                arg_values = {"error": "Could not extract arguments"}

            # Calculate depth properly
            current_depth = 0
            if _tracer.scope_entered:
                if should_recurse:
                    # Only increment depth for in-scope functions
                    current_depth = _tracer.in_scope_depth
                    _tracer.traced_calls.append((file_path, func_name))
                    _tracer.in_scope_depth += 1
                else:
                    # For out-of-scope calls, use current depth without incrementing
                    current_depth = _tracer.in_scope_depth
            
            # Get the parent call line
            parent_call = None
            if frame.f_back:
                parent_call = utils.get_source_line(frame.f_back)
            
            # Log the call with proper depth, function name, arguments, and external status
            _tracer.log_function_call(
                func_name,
                arg_values,
                file_path=file_path,
                line_number=line_number,
                caller_info=caller_info,
                depth=current_depth,
                is_external=is_external,
                parent_call=parent_call
            )
            
            # Return None to stop tracing this branch if we shouldn't recurse
            return _trace_function if should_recurse else None
            
        elif event == 'return':
            # Only decrement if we're in scope and this was a traced call
            if _tracer.scope_entered and _tracer.in_scope_depth > 0:
                code = frame.f_code
                file_path = code.co_filename
                func_name = code.co_name
                
                # Check if this return matches a traced call (only for in-scope functions)
                if _tracer.traced_calls and (file_path, func_name) == _tracer.traced_calls[-1]:
                    _tracer.traced_calls.pop()
                    _tracer.in_scope_depth -= 1
                    
    except Exception as e:
        if _tracer.debug:
            print(f"[DEBUG] Error in trace function: {e}")
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

def start_tracing(scope_path=None, main_file=None, track_external_calls=True, track_imports=True, track_executed_lines=False):
    """Start tracing with a scope-limited approach."""
    global _tracer, _call_depth, TRACER_SCOPE
    
    # Reset state
    _call_depth = 0
    
    # Set scope if provided
    if scope_path:
        set_tracer_scope(scope_path)
    
    # Create and start the tracer with main_file parameter and track_external_calls
    _tracer = Tracer(scope_path=TRACER_SCOPE, main_file=main_file, track_external_calls=track_external_calls, track_imports=track_imports, track_executed_lines=track_executed_lines)
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