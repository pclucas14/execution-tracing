# Python Execution Tracer

A Python program execution tracer that tracks function calls, method invocations, and execution flow within specified scopes.

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

```bash
python -m cli.main <script_to_trace.py> [script_arguments...]
```

### Command Line Options

- `script` - The Python script to trace (required)
- `-o, --output` - Output file for trace results (optional)
- `--scope` - Directory path to restrict tracing to (optional)
- `--no-external-calls` - Disable tracking of calls to functions outside the scope
- `script_args` - Arguments to pass to the traced script

### Examples

#### Basic tracing
```bash
python -m cli.main my_script.py
```

#### Trace with output file
```bash
python -m cli.main my_script.py -o trace_results.json
```

#### Trace with custom scope
```bash
python -m cli.main my_script.py --scope /path/to/project
```

#### Trace without external calls
```bash
python -m cli.main my_script.py --no-external-calls
```

#### Trace script with arguments
```bash
python -m cli.main my_script.py arg1 arg2 --script-flag
```

#### Combined options
```bash
python -m cli.main my_script.py -o results.json --scope /project/src arg1 arg2
```

## Scope Detection

The tracer automatically determines the scope for tracing:

1. If `--scope` is specified, uses that path
2. If no scope is specified, defaults to the directory containing the script
3. **MTTL Project Detection**: If the script path contains 'mttl', automatically sets scope to the mttl directory root

### MTTL Project Example
```bash
# For a script at /path/to/mttl/experiments/train.py
# Automatically sets scope to /path/to/mttl/
python -m cli.main /path/to/mttl/experiments/train.py --config config.yaml
```

## Output

The tracer generates execution traces that include:
- Function and method calls
- Call hierarchy and timing
- Scope-filtered execution paths
- Optional external call tracking

Output can be saved to a file using the `-o` option, or printed to stdout if no output file is specified.
