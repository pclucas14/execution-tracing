# My Tracer

A comprehensive Python function call tracer that provides detailed insights into function execution with scope-based filtering, call hierarchies, argument logging, and external call detection.

## Features

- **Scope-Based Tracing**: Restrict tracing to specific directories or projects
- **Call Hierarchy Visualization**: See the nested structure of function calls with proper indentation
- **Argument Logging**: Capture and intelligently format function arguments
- **External Call Detection**: Identify and optionally track calls to functions outside the traced scope
- **JSON Output**: Structured output format for easy parsing and analysis
- **Configurable Filtering**: Control what gets traced and logged
- **Command-Line Interface**: Easy-to-use script for tracing any Python program

## Installation

Clone the repository:
```bash
git clone <repository-url>
cd my_tracer
```

No additional dependencies required - uses only Python standard library.

## Quick Start

### Using the Command-Line Interface

The easiest way to use the tracer is through the command-line interface:

```bash
# Basic usage - trace a script
python examples/basic_trace.py your_script.py

# With output file
python examples/basic_trace.py your_script.py -o trace_output.json

# With custom scope
python examples/basic_trace.py your_script.py --scope /path/to/project

# Disable external call tracking
python examples/basic_trace.py your_script.py --no-external-calls
```

### Using the API Directly

```python
import os
from src.tracer.core import start_tracing, stop_tracing

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Start tracing
start_tracing(scope_path=os.getcwd(), track_external_calls=True)

try:
    result = fibonacci(5)
finally:
    # Stop tracing and get output
    trace_output = stop_tracing("fibonacci_trace.json")
    print("Tracing complete!")
```

## Configuration Options

### Core Functions

#### `start_tracing(scope_path=None, main_file=None, track_external_calls=True)`

- **`scope_path`** (str, optional): Directory path to restrict tracing to
- **`main_file`** (str, optional): Main file being traced (used for depth calculation)
- **`track_external_calls`** (bool, default: True): Whether to log calls to functions outside the scope

#### `stop_tracing(output_file=None)`

- **`output_file`** (str, optional): File path to write JSON trace output

### Command-Line Options

- **`--scope`**: Directory path to restrict tracing to
- **`--no-external-calls`**: Disable tracking of external function calls
- **`-o, --output`**: Output file for trace results

## Output Format

The tracer outputs JSON with the following structure for each function call:

```json
{
  "location": "filename.py:line_number",
  "parent_location": "caller_file.py:caller_line",
  "name": "function_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  },
  "depth": 0,
  "is_external": false
}
```

### Field Descriptions

- **`location`**: Where the function is defined
- **`parent_location`**: Where the function was called from
- **`name`**: Function name
- **`arguments`**: Function arguments (intelligently formatted)
- **`depth`**: Nesting depth within the traced scope
- **`is_external`**: Whether the function is outside the traced scope

## Advanced Features

### Intelligent Argument Formatting

The tracer intelligently formats function arguments:

- Large strings are truncated with "..."
- Large collections show count instead of full contents
- Complex objects show type name
- Nested structures are handled recursively

### Performance Considerations

- Tracing adds overhead to function calls
- External call tracking has additional overhead
- File output is generally faster than console output for large traces
- Consider using conditional tracing in production environments

## Testing

Run the test suite:

```bash
python -m pytest tests/
```

Or run individual test files:

```bash
python tests/test_tracer.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Changelog

### Version 1.0.0
- Initial release with scope-based tracing
- JSON output format
- External call detection and filtering
- Command-line interface
- Intelligent argument formatting
