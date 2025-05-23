# My Tracer

A comprehensive Python function call tracer that provides detailed insights into function execution, including call hierarchies, timing, arguments, return values, and external calls.

## Features

- **Function Call Tracing**: Track function calls with detailed timing information
- **Call Hierarchy Visualization**: See the nested structure of function calls with indentation
- **Argument and Return Value Logging**: Capture input arguments and return values
- **External Call Detection**: Identify calls to functions outside the traced scope
- **Flexible Configuration**: Customize tracing behavior with various options
- **Multiple Output Formats**: Support for console output and file logging
- **Performance Metrics**: Execution time tracking for performance analysis

## Installation

Clone the repository:
```bash
git clone <repository-url>
cd my_tracer
```

No additional dependencies required - uses only Python standard library.

## Quick Start

Basic usage as a decorator:

```python
from tracer import trace

@trace()
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

result = fibonacci(5)
```

## Configuration Options

### Basic Parameters

- **`depth`** (int, default: None): Maximum depth of function calls to trace
- **`show_args`** (bool, default: True): Include function arguments in trace output
- **`show_returns`** (bool, default: True): Include return values in trace output
- **`track_external_calls`** (bool, default: True): Track calls to functions outside the traced scope

### Output Control

- **`output_file`** (str, default: None): File path to write trace output (None for console)
- **`indent`** (str, default: "  "): String used for indenting nested calls

## Usage Examples

### 1. Basic Function Tracing

```python
from tracer import trace

@trace()
def add(a, b):
    return a + b

@trace()
def multiply(x, y):
    return x * y

@trace()
def calculate(a, b):
    sum_result = add(a, b)
    product = multiply(a, b)
    return sum_result, product

result = calculate(3, 4)
```

Output:
```
-> calculate(a=3, b=4)
  -> add(a=3, b=4)
  <- add() returned 7 (0.0001s)
  -> multiply(x=3, y=4)
  <- multiply() returned 12 (0.0001s)
<- calculate() returned (7, 12) (0.0002s)
```

### 2. Limiting Trace Depth

```python
@trace(depth=2)
def deep_function():
    level1()

def level1():
    level2()

def level2():
    level3()

def level3():
    return "deep"

deep_function()
```

### 3. Hiding Arguments or Return Values

```python
@trace(show_args=False, show_returns=False)
def process_sensitive_data(password, data):
    # Function implementation
    return processed_data

# Output will show function names and timing only
```

### 4. Tracking External Calls

```python
import math
import random

@trace(track_external_calls=True)
def calculate_area(radius):
    # This will show calls to math.pi and math.pow
    area = math.pi * math.pow(radius, 2)
    # This will show call to random.random
    jitter = random.random() * 0.1
    return area + jitter

calculate_area(5)
```

Output:
```
-> calculate_area(radius=5)
  [EXTERNAL] math.pow(5, 2) -> 25.0
  [EXTERNAL] random.random() -> 0.0423...
<- calculate_area() returned 78.58... (0.0003s)
```

### 5. Disabling External Call Tracking

```python
@trace(track_external_calls=False)
def function_with_external_calls():
    import os
    return os.getcwd()

# External calls to os.getcwd() won't be shown
```

### 6. File Output

```python
@trace(output_file="trace_log.txt")
def logged_function():
    return "This trace goes to file"

logged_function()
# Check trace_log.txt for output
```

### 7. Custom Indentation

```python
@trace(indent="    ")  # 4 spaces instead of 2
def custom_indent_function():
    nested_call()

def nested_call():
    return "nested"

custom_indent_function()
```

### 8. Complex Example with All Features

```python
import time
import math

@trace(
    depth=3,
    show_args=True,
    show_returns=True,
    track_external_calls=True,
    output_file="complex_trace.log",
    indent="  "
)
def complex_calculation(data):
    """Complex function demonstrating all tracer features"""
    processed = preprocess(data)
    result = compute(processed)
    return postprocess(result)

def preprocess(data):
    # Simulate some processing time
    time.sleep(0.001)
    return [x * 2 for x in data]

def compute(data):
    total = sum(data)
    # External call to math
    sqrt_total = math.sqrt(total)
    return sqrt_total

def postprocess(value):
    return round(value, 2)

result = complex_calculation([1, 2, 3, 4, 5])
```

## Context Manager Usage

You can also use the tracer as a context manager for more control:

```python
from tracer import TracingContext

def my_function():
    return "traced"

def another_function():
    return my_function()

# Trace specific code blocks
with TracingContext(show_args=True, show_returns=True):
    result = another_function()
```

## Advanced Features

### Performance Analysis

The tracer automatically tracks execution time for each function call, making it useful for performance analysis:

```python
@trace()
def slow_function():
    import time
    time.sleep(0.1)
    return "done"

# Output will show: <- slow_function() returned 'done' (0.1001s)
```

### Recursive Function Tracing

The tracer handles recursive functions gracefully:

```python
@trace(depth=5)
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

factorial(4)
```

### Error Handling

The tracer captures and reports exceptions:

```python
@trace()
def error_function():
    raise ValueError("Something went wrong")

try:
    error_function()
except ValueError:
    pass  # Error will be shown in trace output
```

## Best Practices

1. **Use appropriate depth limits** for recursive or deeply nested functions
2. **Disable argument/return logging** for functions with sensitive data
3. **Use file output** for long traces to avoid cluttering console
4. **Disable external call tracking** if you only want to see your own functions
5. **Consider performance impact** - tracing adds overhead, so disable in production

## Troubleshooting

### Common Issues

1. **Too much output**: Use `depth` parameter to limit trace depth
2. **Sensitive data in logs**: Set `show_args=False` and `show_returns=False`
3. **Performance impact**: Tracing adds overhead; use selectively
4. **File permissions**: Ensure write permissions for output file location

### Performance Considerations

- Tracing adds overhead to function calls
- External call tracking has additional overhead
- File output is generally faster than console output for large traces
- Consider using conditional tracing in production environments

## API Reference

### `trace()` Decorator

```python
def trace(depth=None, show_args=True, show_returns=True, 
          track_external_calls=True, output_file=None, indent="  ")
```

### `TracingContext` Context Manager

```python
class TracingContext:
    def __init__(self, depth=None, show_args=True, show_returns=True,
                 track_external_calls=True, output_file=None, indent="  ")
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
- Initial release with basic tracing functionality
- Support for depth limiting, argument/return value logging
- External call tracking
- File and console output options