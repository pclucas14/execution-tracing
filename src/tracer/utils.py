"""Common utilities for tracer package."""

import os
import json
import inspect
import linecache


def determine_call_type(function_name, file_path, caller_info, is_external, parent_call=None, frame=None):
    """Standardized method for call type classification."""
    # Check for import-related calls
    if is_import_call(function_name, file_path, caller_info):
        return "import"
    
    # Check for module execution
    if function_name == '<module>':
        if caller_info and caller_info[0] and '<frozen importlib' in caller_info[0]:
            return "import"
        return "module_execution"
    
    # Check for class declarations
    if is_class_declaration(function_name, caller_info, parent_call):
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
    
    # Check for comprehensions
    if function_name in ('<genexpr>', '<listcomp>', '<dictcomp>', '<setcomp>'):
        return "comprehension"
    
    # Check for methods (if frame is provided)
    if frame and 'self' in frame.f_locals:
        return "method"
    
    # Classify based on external status
    if is_external:
        return "external_call"
    
    # Default to regular function call
    return "function_call"


def is_import_call(function_name, file_path, caller_info):
    """Check if a function call is related to module importing."""
    # Get parent location for pattern matching
    parent_location = ""
    if caller_info and caller_info[0]:
        parent_location = caller_info[0]
    
    # Check for common import patterns
    return (
        '<frozen importlib._bootstrap>' in parent_location or
        '<frozen importlib._bootstrap>' in (file_path or '') or
        function_name == '<module>' or
        'importlib' in (file_path or '')
    )


def is_class_declaration(function_name, caller_info, parent_call=None):
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
            frame_parent_call = get_source_line(frame)
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


def get_relative_path(file_path, scope_path):
    """Get relative path if within scope, otherwise return absolute path."""
    if not file_path:
        return "unknown"
    
    if scope_path and file_path.startswith(scope_path):
        return os.path.relpath(file_path, scope_path)
    else:
        # Return absolute path for files outside scope
        return file_path


def get_source_line(frame):
    """Extract the source code line(s) from a frame."""
    if not frame:
        return None
        
    try:
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
            
            # NEW: Check if this line looks like a continuation (doesn't start with expected keywords)
            # If so, look backwards to find the start of the statement
            if line and not line.startswith(('class ', 'def ', 'if ', 'while ', 'for ', 'with ', 'try:', 'except', 'import ', 'from ')):
                # Check if the line looks like it might be part of a multi-line statement
                # (e.g., ends with '):', contains base classes, etc.)
                if ('):' in line or 
                    (line.endswith(':') and ('(' in line or ')' in line)) or
                    (line.count(')') > line.count('('))):
                    
                    # Look backwards to find the start of the statement
                    backward_lines = []
                    for i in range(1, 6):  # Look back up to 5 lines
                        prev_line = linecache.getline(filename, lineno - i)
                        if prev_line:
                            prev_line_stripped = prev_line.strip()
                            # Prepend this line
                            backward_lines.insert(0, prev_line_stripped)
                            
                            # Check if this looks like the start of a statement
                            if (prev_line_stripped.startswith(('class ', 'def ', 'if ', 'while ', 'for ', 'with ', 'try:', 'except', 'import ', 'from ')) or
                                # Also check if we've balanced parentheses/brackets
                                (' = ' in prev_line_stripped and not prev_line_stripped.endswith(','))):
                                # Found the start, combine all lines
                                combined = ' '.join(backward_lines) + ' ' + line
                                # Check if parentheses are balanced
                                if (combined.count('(') == combined.count(')') and
                                    combined.count('[') == combined.count(']') and
                                    combined.count('{') == combined.count('}')):
                                    line = combined
                                    break
                                # If not balanced, continue looking back
                        else:
                            break
                    
                    # If we collected backward lines but didn't find a clear start,
                    # use what we have if it looks reasonable
                    if backward_lines and line.endswith('):'):
                        combined = ' '.join(backward_lines) + ' ' + line
                        if 'class ' in combined or 'def ' in combined:
                            line = combined
            
            # For multi-line calls, try to get additional context (looking forward)
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


def format_value(value):
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
                formatted_items = [format_value(item) for item in value[:3]]
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
                    formatted_dict[str_key] = format_value(v)
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


def format_arguments(args):
    """Format arguments intelligently for logging."""
    if not isinstance(args, dict):
        return args
        
    formatted = {}
    for key, value in args.items():
        # Convert all keys to strings for JSON compatibility
        str_key = str(key) if key is not None else "None"
        formatted[str_key] = format_value(value)
    return formatted


def serialize_value(value):
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


def make_json_safe(obj):
    """Recursively make an object JSON-safe by converting problematic types."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, dict):
        safe_dict = {}
        for k, v in obj.items():
            safe_dict[str(k)] = make_json_safe(v)
        return safe_dict
    elif isinstance(obj, (list, tuple)):
        return [make_json_safe(item) for item in obj]
    else:
        return str(obj)
