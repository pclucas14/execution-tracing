import os
import sys
import bdb
import json
import datetime
import linecache
import inspect

class IterationBreakpointTracer(bdb.Bdb):
    def __init__(self, filename, lineno, max_hits, output_file, scope_path=None):  # Changed from scope_dir
        super().__init__()
        self.filename = os.path.abspath(filename)
        self.lineno = lineno
        self.max_hits = max_hits
        self.hit_count = 0
        self.output_file = output_file 
        self.scope_path = os.path.abspath(scope_path) if scope_path else None  # Changed from scope_dir
        self.stack_trace = []
        self.original_command = ' '.join(sys.argv)
        print(f"Setting breakpoint at {self.filename}:{self.lineno}")
        print(f"Scope path: {self.scope_path}")  # Changed from scope_dir
        self.set_break(self.filename, lineno)

    def user_line(self, frame):
        # Check if we've hit our breakpoint
        filename = os.path.abspath(frame.f_code.co_filename)
        if filename == self.filename and frame.f_lineno == self.lineno:
            self.hit_count += 1
            print(f"Hit breakpoint #{self.hit_count} at {self.filename}:{self.lineno}")
            
            if self.hit_count == self.max_hits:
                print(f"\nBreakpoint hit {self.max_hits} times at {self.filename}:{self.lineno}")
                self.stack_trace = self.collect_detailed_stack_trace(frame)
                self.print_stack_trace()
                self.save_trace()
                sys.exit(0)

    def collect_detailed_stack_trace(self, frame):
        """Collect detailed information about each frame in the stack."""
        stack = []
        depth = 0
        current_frame = frame
        
        while current_frame:
            code = current_frame.f_code
            filename = os.path.abspath(code.co_filename)
            
            # Check if we should include this frame based on scope
            include_frame = True
            if self.scope_path:  # Changed from scope_dir
                include_frame = filename.startswith(self.scope_path)
            
            if include_frame:
                # Get the source line
                line_content = linecache.getline(filename, current_frame.f_lineno).strip()
                
                # Get parent information
                parent_frame = current_frame.f_back
                parent_location = None
                parent_call = None
                if parent_frame:
                    parent_filename = os.path.abspath(parent_frame.f_code.co_filename)
                    parent_lineno = parent_frame.f_lineno
                    parent_location = f"{self._get_relative_path(parent_filename)}:{parent_lineno}"
                    parent_call = linecache.getline(parent_filename, parent_lineno).strip()
                
                # Extract ONLY the actual arguments passed to the function
                args, kwargs = self._extract_actual_arguments(current_frame, code)
                
                # Determine call type using standardized method
                call_type = self._determine_call_type(code.co_name, filename, 
                                                     (parent_filename, parent_lineno) if parent_frame else None,
                                                     not filename.startswith(self.scope_path) if self.scope_path else False,
                                                     parent_call, current_frame)
                
                frame_info = {
                    "location": f"{self._get_relative_path(filename)}:{current_frame.f_lineno}",
                    "parent_location": parent_location,
                    "parent_call": parent_call,
                    "call": line_content,
                    "name": code.co_name,
                    "arguments": {**args, **kwargs},
                    "depth": depth,
                    "is_external": not filename.startswith(self.scope_path) if self.scope_path else False,
                    "call_type": call_type,
                    "args": args,
                    "kwargs": kwargs
                }
                stack.append(frame_info)
                depth += 1
            
            current_frame = current_frame.f_back
        
        # Return in order from deepest (breakpoint) to main
        return stack

    def _extract_actual_arguments(self, frame, code):
        """Extract only the actual arguments passed to the function."""
        args = {}
        kwargs = {}
        
        try:
            # Get the function's signature if possible
            if code.co_name != '<module>':
                # Get argument names from code object
                argcount = code.co_argcount
                kwonlyargcount = code.co_kwonlyargcount
                varnames = code.co_varnames
                
                # Extract positional arguments
                for i in range(argcount):
                    arg_name = varnames[i]
                    if arg_name in frame.f_locals:
                        value = frame.f_locals[arg_name]
                        # Skip 'self' and 'cls' unless it's the actual argument name
                        if arg_name not in ('self', 'cls') or argcount == 1:
                            args[arg_name] = self._serialize_value(value)
                
                # Extract keyword-only arguments
                for i in range(argcount, argcount + kwonlyargcount):
                    arg_name = varnames[i]
                    if arg_name in frame.f_locals:
                        kwargs[arg_name] = self._serialize_value(frame.f_locals[arg_name])
                
                # Check for *args and **kwargs
                flags = code.co_flags
                if flags & inspect.CO_VARARGS:  # Has *args
                    varargs_index = argcount + kwonlyargcount
                    if varargs_index < len(varnames):
                        varargs_name = varnames[varargs_index]
                        if varargs_name in frame.f_locals:
                            args[f"*{varargs_name}"] = self._serialize_value(frame.f_locals[varargs_name])
                
                if flags & inspect.CO_VARKEYWORDS:  # Has **kwargs
                    varkw_index = argcount + kwonlyargcount + (1 if flags & inspect.CO_VARARGS else 0)
                    if varkw_index < len(varnames):
                        varkw_name = varnames[varkw_index]
                        if varkw_name in frame.f_locals:
                            kwargs[f"**{varkw_name}"] = self._serialize_value(frame.f_locals[varkw_name])
        except Exception:
            # Fallback: just get what we can
            pass
        
        return args, kwargs

    def _serialize_value(self, value):
        """Serialize a value for JSON output."""
        try:
            json.dumps(value)
            return value
        except:
            # Convert to string representation if not JSON serializable
            value_str = str(value)
            if len(value_str) > 100:
                return f"{type(value).__name__} object"
            return value_str

    def _determine_call_type(self, name, filename, caller_info, is_external, line_content, frame):
        """Standardized call type determination matching core.py logic."""
        # Check for module execution
        if name == '<module>':
            if caller_info and caller_info[0] and '<frozen importlib' in caller_info[0]:
                return "import"
            return 'module_execution'
        
        # Check for class instantiation
        elif name == '__init__':
            return 'class_instantiation'
        
        # Check for special methods
        elif name.startswith('__') and name.endswith('__'):
            return 'special_method' if name != '__call__' else 'callable_object'
        
        # Check for class declaration
        elif line_content and line_content.strip().startswith('class '):
            return 'class_declaration'
        
        # Check for lambda
        elif name == '<lambda>':
            return 'lambda_function'
        
        # Check for comprehensions
        elif name in ('<genexpr>', '<listcomp>', '<dictcomp>', '<setcomp>'):
            return 'comprehension'
        
        # Check for method
        elif frame and 'self' in frame.f_locals:
            return 'method'
        
        # Check for external
        elif is_external:
            return 'external_call'
        
        # Default
        else:
            return 'function_call'

    def _get_relative_path(self, file_path):
        """Get relative path if within scope, otherwise return absolute path."""
        if not file_path:
            return "unknown"
        
        if self.scope_path and file_path.startswith(self.scope_path):  # Changed from scope_dir
            return os.path.relpath(file_path, self.scope_path)
        else:
            return file_path

    def print_stack_trace(self):
        """Print the stack trace in a readable format."""
        print("\n" + "="*60)
        print("Stack trace (from breakpoint to main):")
        print("="*60)
        for frame_info in self.stack_trace:
            print(f"\nDepth {frame_info['depth']}: {frame_info['location']}")
            print(f"  Function: {frame_info['name']}")
            print(f"  Type: {frame_info['call_type']}")
            print(f"  Current line: {frame_info['call']}")  # Add display of current line
            if frame_info['parent_location']:
                print(f"  Called from: {frame_info['parent_location']}")
                print(f"  Call: {frame_info['parent_call']}")
            if frame_info['args'] or frame_info['kwargs']:
                print(f"  Arguments:")
                if frame_info['args']:
                    print(f"    args: {json.dumps(frame_info['args'], indent=6)}")
                if frame_info['kwargs']:
                    print(f"    kwargs: {json.dumps(frame_info['kwargs'], indent=6)}")

    def save_trace(self):
        """Save the stack trace to a JSON file in standard format."""
        output_filename = self.output_file
        if not output_filename.endswith('.json'):
            output_filename += '.json'
        
        # Get the line content at the breakpoint
        breakpoint_line = linecache.getline(self.filename, self.lineno).strip()
        
        # Create output in standard format with metadata
        output_data = {
            "metadata": {
                "original_command": self.original_command,
                "breakpoint": f"{self.filename}:{self.lineno}",
                "call": breakpoint_line,
                "iterations": self.max_hits,
                "scope_path": self.scope_path,  # Changed from scope_dir
                "total_frames": len(self.stack_trace),  # Keep as total_frames
                "timestamp": datetime.datetime.now().isoformat()
            },
            "trace_data": self.stack_trace
        }
            
        with open(output_filename, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        print(f"\nStack trace saved to: {output_filename}")

def main(script_path, breakpoint_file, lineno, iterations, output_file, scope_path, script_args):  # Changed from scope_dir
    """Main function to run the tracer."""
    # Set up sys.argv for the target script
    sys.argv = [script_path] + script_args
    
    # Create and run the tracer
    tracer = IterationBreakpointTracer(
        filename=breakpoint_file,
        lineno=lineno,
        max_hits=iterations,
        output_file=output_file,
        scope_path=scope_path  # Changed from scope_dir
    )
    
    # Add script directory to path
    script_dir = os.path.dirname(os.path.abspath(script_path))
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    
    print(f"Running script: {script_path}")
    print(f"With arguments: {script_args}")
    
    # Execute the script
    with open(script_path, 'rb') as fp:
        code = compile(fp.read(), script_path, 'exec')
        exec_globals = {
            '__name__': '__main__',
            '__file__': script_path,
            '__builtins__': __builtins__,
        }
        tracer.run(code, exec_globals, exec_globals)