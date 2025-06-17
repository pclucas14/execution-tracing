import os
import sys
import bdb
import json
import datetime

class IterationBreakpointTracer(bdb.Bdb):
    def __init__(self, filename, lineno, max_hits, output_file, scope_dir=None):
        super().__init__()
        self.filename = filename
        self.lineno = lineno
        self.max_hits = max_hits
        self.hit_count = 0
        self.output_file = output_file 
        self.scope_dir = os.path.abspath(scope_dir) if scope_dir else None
        self.traces = []
        self.trace_data = []  # Store trace data in the new format
        print(f"Scope dir - {self.scope_dir}")
        self.set_break(filename, lineno)

    def user_line(self, frame):
        print('here', frame.f_code.co_filename, self.filename)
        print(f'here 2 : {frame.f_lineno}, {self.lineno}')
        if (frame.f_code.co_filename == self.filename and
                frame.f_lineno == self.lineno):
            self.hit_count += 1
            stack_trace = self.collect_stack_trace(frame)
            self.traces.append(stack_trace)  # Keep old format for backward compatibility
            self.trace_data.extend(stack_trace)  # Add individual entries to new format
            if self.hit_count == self.max_hits:
                print(f"\nBreakpoint hit {self.max_hits} times at {self.filename}:{self.lineno}")
                print("Stack trace (pdb where):")
                self.print_stack_trace(frame)
                self.save_traces()
                sys.exit(0)
        # Do not call super().user_line(frame) to avoid interactive mode

    def collect_stack_trace(self, frame):
        stack = []
        depth = 0
        while frame:
            code = frame.f_code
            filename = os.path.abspath(code.co_filename)
            print('filename', filename)
            if self.scope_dir is None or filename.startswith(self.scope_dir):
                # Convert to the new format matching trace_program/trace_pytest
                relative_path = self._get_relative_path(filename)
                location = f"{relative_path}:{frame.f_lineno}"
                
                # Get parent frame info
                parent_location = None
                parent_call = None
                if frame.f_back:
                    parent_code = frame.f_back.f_code
                    parent_filename = os.path.abspath(parent_code.co_filename)
                    if self.scope_dir is None or parent_filename.startswith(self.scope_dir):
                        parent_relative_path = self._get_relative_path(parent_filename)
                        parent_location = f"{parent_relative_path}:{frame.f_back.f_lineno}"
                        parent_call = self._get_source_line(frame.f_back)
                
                # Create trace entry in the new format
                trace_entry = {
                    "location": location,
                    "parent_location": parent_location,
                    "parent_call": parent_call,
                    "name": code.co_name,
                    "arguments": self._get_function_args(frame),
                    "depth": depth,
                    "is_external": False,  # Within scope
                    "call_type": self._classify_call_type(code.co_name, filename),
                    "args": {},
                    "kwargs": self._get_function_args(frame)
                }
                
                stack.append(trace_entry)
                depth += 1
            frame = frame.f_back
        return list(reversed(stack))

    def print_stack_trace(self, frame):
        stack = []
        while frame:
            code = frame.f_code
            filename = os.path.abspath(code.co_filename)
            if self.scope_dir is None or filename.startswith(self.scope_dir):
                # is the scope_dir is given, we restrict the stack to only the files within them
                stack.append(frame)
            frame = frame.f_back
        print("\n======================================\n")
        print("Stack trace:")
        for f in reversed(stack):
            code = f.f_code
            print(f'  {code.co_filename}({f.f_lineno}): {code.co_name}')

    def save_traces(self):
        # Create the new format matching trace_program/trace_pytest
        
        # Construct the original command
        original_command = f"{self.filename} --line {self.lineno} --iterations {self.max_hits}"
        if self.scope_dir:
            original_command += f" --scope {self.scope_dir}"
        
        output_data = {
            "metadata": {
                "original_command": original_command,
                "scope_path": self.scope_dir or os.path.dirname(os.path.abspath(self.filename)),
                "main_file": os.path.basename(self.filename),
                "total_calls": len(self.trace_data),
                "timestamp": datetime.datetime.now().isoformat(),
                "breakpoint_file": self.filename,
                "breakpoint_line": self.lineno,
                "iterations_captured": self.hit_count,
                "max_iterations": self.max_hits
            },
            "trace_data": self.trace_data
        }
        
        with open(f"{self.output_file}.json", "w") as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"Done saving results in .. {self.output_file}.json")

    def run(self, *args, **kwargs):
        """Run the code with the given arguments."""
        return super().run(*args, **kwargs)

    def _get_relative_path(self, file_path):
        """Convert an absolute file path to a relative path based on the scope."""
        if not file_path:
            return "unknown"
        
        # Handle special cases
        if '<frozen' in file_path or file_path.startswith('<'):
            return file_path
        
        # If we have a scope path, try to make the path relative to it
        if self.scope_dir and file_path.startswith(self.scope_dir):
            # Remove the scope path prefix and any leading slash
            relative_path = file_path[len(self.scope_dir):].lstrip(os.sep)
            return relative_path if relative_path else os.path.basename(file_path)
        
        # For external files or files outside scope
        return os.path.basename(file_path)

    def _get_source_line(self, frame):
        """Extract the source code line from a frame."""
        if not frame:
            return None
            
        try:
            import linecache
            filename = frame.f_code.co_filename
            lineno = frame.f_lineno
            
            # Check for special cases where source is not available
            if '<frozen' in filename:
                return "<frozen module call>"
            
            if filename.startswith('<'):
                return "<built-in or generated code>"
            
            # Get the line from the file
            line = linecache.getline(filename, lineno)
            if line:
                # Strip whitespace and return the line
                line = line.strip()
                
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

    def _get_function_args(self, frame):
        """Extract function arguments from frame."""
        args = {}
        try:
            import inspect
            # Get argument names and values  
            arginfo = inspect.getargvalues(frame)
            for arg_name in arginfo.args:
                if arg_name in arginfo.locals:
                    value = arginfo.locals[arg_name]
                    args[arg_name] = self._format_value(value)
                            
            # Add varargs and kwargs if present
            if arginfo.varargs and arginfo.varargs in arginfo.locals:
                args['*' + arginfo.varargs] = self._format_value(arginfo.locals[arginfo.varargs])
            if arginfo.keywords and arginfo.keywords in arginfo.locals:
                args['**' + arginfo.keywords] = self._format_value(arginfo.locals[arginfo.keywords])
                
        except Exception:
            args = {"error": "Could not extract arguments"}
            
        return args

    def _format_value(self, value):
        """Format a single value intelligently."""
        try:
            # Handle None
            if value is None:
                return None
                
            # Handle strings
            if isinstance(value, str):
                if len(value) > 100:
                    return f"{value[:100]}..."
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

    def _classify_call_type(self, function_name, file_path):
        """Classify the type of function call."""
        # Check for module execution
        if function_name == '<module>':
            return "module_execution"
        
        # Check for class instantiation
        if function_name == '__init__':
            return "class_instantiation"
        
        # Check for special methods
        if function_name.startswith('__') and function_name.endswith('__'):
            return "special_method"
        
        # Check for lambda functions
        if function_name == '<lambda>':
            return "lambda_function"
        
        # Check for comprehensions
        if function_name in ('<genexpr>', '<listcomp>', '<dictcomp>', '<setcomp>'):
            return "comprehension"
        
        # Default to function call
        return "function_call"
