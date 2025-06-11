import sys
import inspect
import os
import json

# Global tracer state
_tracer = None
_call_depth = 0
TRACER_SCOPE = None  # Directory path to restrict tracing to

class Tracer:
    def __init__(self, scope_path=None, exclude_paths=None, output_file=None, main_file=None, track_external_calls=True, track_imports=True):
        self.is_tracing = False
        self.log = []  # Now a list of dicts for JSON output
        self.seen_functions = set()
        self.scope_path = scope_path
        self.exclude_paths = exclude_paths or []
        self.output_file = output_file
        self.main_file = main_file or "train_km_simple.py"
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

        
    def start(self):
        self.is_tracing = True
    
    def stop(self):
        self.is_tracing = False
    
    def log_function_call(self, function_name, args, file_path=None, line_number=None, caller_info=None, depth=0, is_external=False, parent_call=None):
        """Log a function call as a dict for JSON output."""
        if not self.is_tracing:
            return

        # Determine call type
        call_type = self._classify_call_type(function_name, file_path, caller_info, is_external, parent_call)

        # Prepare location info
        location = None
        if file_path and line_number:
            relative_path = self._get_relative_path(file_path)
            location = f"{relative_path}:{line_number}"
        elif file_path:
            relative_path = self._get_relative_path(file_path)
            location = relative_path
        else:
            location = "unknown"

        # Prepare parent location - show absolute path if outside scope
        parent_location = None
        if caller_info and caller_info[0] and caller_info[1]:
            relative_caller_path = self._get_relative_path(caller_info[0])
            parent_location = f"{relative_caller_path}:{caller_info[1]}"

        # Format arguments intelligently
        formatted_args = self._format_arguments(args)

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
            "kwargs": formatted_args
        }
        self.log.append(entry)

    def _classify_call_type(self, function_name, file_path, caller_info, is_external, parent_call=None):
        """Classify the type of function call."""
        # Check for import-related calls
        if self._is_import_call(function_name, file_path, caller_info):
            return "import"
        
        # Check for module execution
        if function_name == '<module>':
            return "module_execution"
        
        # Check for class declarations (class definitions, not instantiations)
        if self._is_class_declaration(function_name, caller_info, parent_call):
            return "class_declaration"
        
        # Check for class instantiation
        if function_name == '__init__':
            return "class_instantiation"
        
        # Check for special/dunder methods
        if function_name.startswith('__') and function_name.endswith('__'):
            if function_name == '__call__':
                return "callable_object"
            else:
                return "special_method"
        
        # Check for lambda/anonymous functions
        if function_name == '<lambda>':
            return "lambda_function"
        
        # Check for comprehensions (filtered out but classified for completeness)
        if function_name in ('<genexpr>', '<listcomp>', '<dictcomp>', '<setcomp>'):
            return "comprehension"
        
        # Classify based on external status
        if is_external:
            return "external_call"
        
        # Default to regular function call
        return "function_call"

    def _is_class_declaration(self, function_name, caller_info, parent_call=None):
        """Check if this is a class declaration (class definition) rather than instantiation."""
        # Skip dunder methods and module-level code
        if (function_name.startswith('__') and function_name.endswith('__')) or function_name == '<module>':
            return False
        
        # Use the parent_call if it's provided (most reliable)
        if parent_call:
            # Look for patterns like "class ClassName:" or "class ClassName(Parent):"
            import re
            class_def_pattern = r'^\s*class\s+' + re.escape(function_name) + r'\s*[\(:]'
            if re.match(class_def_pattern, parent_call.strip()):
                return True
                
            # Also check for class definitions without the exact name match
            # (in case of metaclass calls or inheritance)
            if parent_call.strip().startswith('class ') and ':' in parent_call:
                return True
        
        # Fallback: try to get parent call information from frame inspection if parent_call wasn't provided
        if not parent_call and caller_info and len(caller_info) > 0:
            try:
                import sys
                frame = sys._getframe(3)  # Go back to find the actual call frame
                frame_parent_call = self._get_source_line(frame)
                if frame_parent_call:
                    import re
                    class_def_pattern = r'^\s*class\s+' + re.escape(function_name) + r'\s*[\(:]'
                    if re.match(class_def_pattern, frame_parent_call.strip()):
                        return True
                        
                    # Also check for class definitions without the exact name match
                    if frame_parent_call.strip().startswith('class ') and ':' in frame_parent_call:
                        return True
            except Exception:
                pass
        
        return False

    def get_trace_output(self):
        """Return the log as a JSON string with metadata."""
        try:
            output_data = {
                "metadata": {
                    "original_command": self.original_command,
                    "scope_path": self.scope_path,
                    "main_file": self.main_file,
                    "total_calls": len(self.log),
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                },
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
            return json.dumps(output_data, indent=2, default=str)
    
    def _make_json_safe(self, obj):
        """Recursively make an object JSON-safe by converting problematic types."""
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        elif isinstance(obj, dict):
            safe_dict = {}
            for k, v in obj.items():
                safe_dict[str(k)] = self._make_json_safe(v)
            return safe_dict
        elif isinstance(obj, (list, tuple)):
            return [self._make_json_safe(item) for item in obj]
        else:
            return str(obj)

    def _format_arguments(self, args):
        """Format arguments intelligently for logging."""
        if not isinstance(args, dict):
            return args
            
        formatted = {}
        for key, value in args.items():
            # Convert all keys to strings for JSON compatibility
            str_key = str(key) if key is not None else "None"
            formatted[str_key] = self._format_value(value)
        return formatted
    
    def _format_value(self, value):
        """Format a single value intelligently."""
        try:
            # Handle None
            if value is None:
                return None
                
            # Handle strings
            if isinstance(value, str):
                if len(value) > 100:
                    return f"{value[:100]}..."  # 100 chars + "..." = 103 total
                return value
                
            # Handle numbers and booleans
            if isinstance(value, (int, float, bool)):
                return value
                
            # Handle collections
            if isinstance(value, (list, tuple)):
                if len(value) == 0:
                    return value
                elif len(value) > 10:
                    return f"{type(value).__name__} with {len(value)} items"
                else:
                    # Show first few items
                    formatted_items = [self._format_value(item) for item in value[:3]]
                    if len(value) > 3:
                        formatted_items.append("...")
                    return formatted_items
                    
            elif isinstance(value, dict):
                if len(value) == 0:
                    return value
                elif len(value) > 5:
                    return f"dict with {len(value)} keys"
                else:
                    # Show first few key-value pairs and ensure all keys are strings
                    items = list(value.items())[:3]
                    formatted_dict = {}
                    for k, v in items:
                        str_key = str(k) if k is not None else "None"
                        formatted_dict[str_key] = self._format_value(v)
                    if len(value) > 3:
                        formatted_dict["...more"] = f"and {len(value) - 3} more"
                    return formatted_dict
                    
            elif isinstance(value, set):
                if len(value) == 0:
                    return "set()"
                elif len(value) > 5:
                    return f"set with {len(value)} items"
                else:
                    return f"set({list(value)[:3]}{'...' if len(value) > 3 else ''})"
                    
            # Handle objects with useful string representations
            else:
                str_repr = str(value)
                if len(str_repr) > 100:
                    return f"{type(value).__name__} object"
                return str_repr
                
        except Exception:
            return f"{type(value).__name__} object"

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
        
        # Get parent location for pattern matching
        parent_location = ""
        if caller_info and caller_info[0]:
            parent_location = caller_info[0]
        
        # Check for common import patterns (same logic as visualization)
        return (
            '<frozen importlib._bootstrap>' in parent_location or
            '<frozen importlib._bootstrap>' in (file_path or '') or
            function_name == '<module>' or
            'importlib' in (file_path or '')
        )

    def _get_relative_path(self, file_path, show_absolute_if_external=True):
        """Convert an absolute file path to a relative path based on the scope."""
        if not file_path:
            return "unknown"
        
        # If we have a scope path, try to make the path relative to it
        if self.scope_path and file_path.startswith(self.scope_path):
            # Remove the scope path prefix and any leading slash
            relative_path = file_path[len(self.scope_path):].lstrip(os.sep)
            return relative_path if relative_path else os.path.basename(file_path)
        
        # For external files or files outside scope
        if show_absolute_if_external:
            return file_path  # Return full absolute path
        else:
            return os.path.basename(file_path)  # Just return the basename

    def _get_source_line(self, frame):
        """Extract the source code line(s) from a frame."""
        if not frame:
            return None
            
        try:
            import linecache
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            
            # Check for special cases where source is not available
            if '<frozen' in filename:
                return f"<frozen module call>"
            
            if filename.startswith('<'):
                return f"<built-in or generated code>"
            
            # Get the line from the file
            line = linecache.getline(filename, lineno)
            if line:
                # Strip whitespace and return the line
                line = line.strip()
                
                # For multi-line calls, try to get additional context
                # Check if the line looks incomplete (ends with comma, opening paren, etc.)
                if line and (line.endswith(',') or line.endswith('(') or 
                           line.count('(') > line.count(')') or
                           line.count('[') > line.count(']') or
                           line.count('{') > line.count('}')):
                    # Try to get the next few lines to complete the call
                    additional_lines = []
                    for i in range(1, 4):  # Look ahead up to 3 lines
                        next_line = linecache.getline(filename, lineno + i)
                        if next_line:
                            next_line = next_line.strip()
                            additional_lines.append(next_line)
                            # Stop if we seem to have completed the call
                            combined = line + ' ' + ' '.join(additional_lines)
                            if (combined.count('(') == combined.count(')') and
                                combined.count('[') == combined.count(']') and
                                combined.count('{') == combined.count('}')):
                                break
                        else:
                            break
                    
                    if additional_lines:
                        line = line + ' ' + ' '.join(additional_lines)
                
                # Limit length to avoid extremely long lines
                if len(line) > 150:
                    line = line[:147] + "..."
                    
                return line
            else:
                # If we can't read the line, provide a fallback
                return f"<source unavailable: {os.path.basename(filename)}:{lineno}>"
            
        except Exception as e:
            # If we can't get the source, return a descriptive error
            return f"<source error: {str(e)}>"
            
        return None
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
            line_number = frame.f_lineno
            
            # Get caller information
            caller_info = _get_caller_info(frame)
            
            # Track if we're entering the main file
            if not _tracer.scope_entered and _tracer.main_file in file_path:
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
            if not _tracer.track_imports and _tracer._is_import_call(func_name, file_path, caller_info):
                return _trace_function if should_recurse else None
                
            # Skip special methods and common internals
            if func_name.startswith('__') and func_name.endswith('__') and func_name != '__call__':
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
            
            # Log the call with proper depth, function name, arguments, and external status
            _tracer.log_function_call(
                func_name, 
                arg_values, 
                file_path,
                line_number,
                caller_info,
                depth=current_depth,
                is_external=is_external,
                parent_call=_tracer._get_source_line(frame.f_back)  # Get the actual code that led to this call
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

def start_tracing(scope_path=None, main_file=None, track_external_calls=True, track_imports=True):
    """Start tracing with a scope-limited approach."""
    global _tracer, _call_depth, TRACER_SCOPE
    
    # Reset state
    _call_depth = 0
    
    # Set scope if provided
    if scope_path:
        set_tracer_scope(scope_path)
    
    # Create and start the tracer with main_file parameter and track_external_calls
    _tracer = Tracer(scope_path=TRACER_SCOPE, main_file=main_file, track_external_calls=track_external_calls, track_imports=track_imports)
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