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
from src.tracer.core import start_tracing, stop_tracing

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Start tracing
start_tracing(scope_path="/path/to/your/project", track_external_calls=True)

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

## Usage Examples

### 1. Basic Project Tracing

```python
from src.tracer.core import start_tracing, stop_tracing

def add(a, b):
    return a + b

def multiply(x, y):
    return x * y

def calculate(a, b):
    sum_result = add(a, b)
    product = multiply(a, b)
    return sum_result, product

# Start tracing with scope
start_tracing(scope_path="/home/user/my_project")

try:
    result = calculate(3, 4)
finally:
    output = stop_tracing("calculation_trace.json")
```

Example JSON output:
```json
[
  {
    "location": "example.py:15",
    "parent_location": null,
    "name": "calculate",
    "arguments": {"a": 3, "b": 4},
    "depth": 0,
    "is_external": false
  },
  {
    "location": "example.py:5",
    "parent_location": "example.py:16",
    "name": "add",
    "arguments": {"a": 3, "b": 4},
    "depth": 1,
    "is_external": false
  }
]
```

### 2. Tracing with External Calls

```python
import math
import os
from src.tracer.core import start_tracing, stop_tracing

def calculate_area(radius):
    # External call to math.pi - will be logged
    area = math.pi * (radius ** 2)
    # External call to os.getpid - will be logged
    pid = os.getpid()
    return area, pid

start_tracing(scope_path="/path/to/project", track_external_calls=True)
try:
    result = calculate_area(5)
finally:
    stop_tracing("area_trace.json")
```

### 3. Disabling External Call Tracking

```python
from src.tracer.core import start_tracing, stop_tracing

def function_with_external_calls():
    import json
    import os
    data = {"key": "value"}
    # These external calls won't be logged
    json_str = json.dumps(data)
    cwd = os.getcwd()
    return json_str, cwd

start_tracing(scope_path="/path/to/project", track_external_calls=False)
try:
    result = function_with_external_calls()
finally:
    stop_tracing("no_external_trace.json")
```

### 4. Command-Line Usage Examples

```bash
# Trace a machine learning training script
python examples/basic_trace.py train_model.py --scope /path/to/ml_project -o training_trace.json

# Trace with arguments passed to the target script
python examples/basic_trace.py data_processor.py --input data.csv --output results.csv

# Trace without external calls for cleaner output
python examples/basic_trace.py web_scraper.py --no-external-calls -o clean_trace.json
```

### 5. Recursive Function Tracing

```python
from src.tracer.core import start_tracing, stop_tracing

def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

start_tracing(scope_path="/path/to/project")
try:
    result = factorial(5)
finally:
    stop_tracing("factorial_trace.json")
```

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

### Scope Detection

For projects with recognizable structures (like MTTL), the tracer can automatically detect the appropriate scope:

```bash
# Will automatically detect and use the 'mttl' directory as scope
python examples/basic_trace.py /path/to/mttl/experiments/train.py
```

### Threading Support

The tracer attempts to trace function calls in threads when possible.

## Best Practices

1. **Set appropriate scope**: Use `--scope` to limit tracing to your project directory
2. **Disable external calls for cleaner output**: Use `--no-external-calls` when you only care about your own functions
3. **Use file output for large traces**: Always specify an output file for non-trivial programs
4. **Consider performance impact**: Tracing adds overhead, so use judiciously in performance-critical code

## Troubleshooting

### Common Issues

1. **Too much output**: Use `--scope` to limit tracing to your project directory
2. **Performance impact**: Disable external call tracking or use more restrictive scoping
3. **File permissions**: Ensure write permissions for output file location
4. **Import errors**: Make sure the tracer's `src` directory is in your Python path

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