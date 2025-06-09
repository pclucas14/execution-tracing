# Python Execution Tracer

A Python program execution tracer that tracks function calls, method invocations, and execution flow within specified scopes.

## Installation

```bash
pip install -e .
```

## Usage

### Basic Usage

There are two ways to run the tracer:

#### Using the Python module
```bash
python -m cli.main <script_to_trace.py> [script_arguments...]
```

#### Using the installed console script (after running `pip install -e .`)
```bash
trace_program <script_to_trace.py> [script_arguments...]
```

### Command Line Options

- `script` - The Python script to trace (required)
- `-o, --output` - Output file for trace results (optional, prints to stdout if not specified)
- `--scope` - Directory path to restrict tracing to (optional, defaults to script directory)
- `--no-external-calls` - Disable tracking of calls to functions outside the scope
- `script_args` - Arguments to pass to the traced script (supports both positional and named arguments)

### Examples

#### Basic tracing (output to stdout)
```bash
python -m cli.main my_script.py
# or
trace_program my_script.py
```

#### Trace with output file
```bash
python -m cli.main my_script.py -o trace_results.json
# or  
trace_program my_script.py -o trace_results.json
```

#### Trace with custom scope
```bash
python -m cli.main my_script.py --scope /path/to/project
# or
trace_program my_script.py --scope /path/to/project
```

#### Trace without external calls
```bash
python -m cli.main my_script.py --no-external-calls
# or
trace_program my_script.py --no-external-calls
```

#### Trace script with arguments
```bash
python -m cli.main my_script.py arg1 arg2 --script-flag=value
# or
trace_program my_script.py arg1 arg2 --script-flag=value
```

#### Combined options
```bash
python -m cli.main my_script.py -o results.json --scope /project/src arg1 arg2
# or
trace_program my_script.py -o results.json --scope /project/src arg1 arg2
```

## Visualization

### Pattern Grouping Visualization

The tracer includes advanced pattern detection that automatically groups repeating sequences of function calls. After generating a trace file, you can create an interactive HTML visualization:

```bash
# Serve visualization with pattern grouping (default)
bash scripts/serve_visualization.sh trace_output.json 8080

# Serve without pattern grouping  
bash scripts/serve_visualization.sh trace_output.json 8080 --no-patterns

# Hide import calls by default
bash scripts/serve_visualization.sh trace_output.json 8080 --hide-imports
```

**Pattern Detection Features:**
- **Nested Patterns**: Detects patterns within patterns (e.g., repeated subsequences within larger repeated blocks)
- **Visual Grouping**: Shows repeated call sequences in collapsible boxes with repetition counts
- **Interactive Controls**: Toggle pattern expansion/collapse and filter external calls
- **Statistics**: Displays pattern statistics and call counts

**Example Pattern Detection:**
```
🔄 Repeating Pattern: 6x repetitions of 6 calls (calls #22388-#22423, total: 36 calls)
  📋 Pattern template (repeated 6 times):
    ├── scaled_dot_product_attention [packed_attention_monkey_patch.py:14]
    ├── get [expert_context.py:25]  
    └── 🔄 Nested Pattern: 2x repetitions of 2 calls
        ├── forward [train_lens.py:88]
        └── layer_name [base.py:21]
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
- Function and method calls with arguments
- Call hierarchy and timing information
- Scope-filtered execution paths
- Optional external call tracking
- **Pattern-grouped visualization** with nested repetition detection

**Output Formats:**
- **JSON**: When using `-o filename.json`, saves structured trace data
- **Console**: When no output file is specified, prints formatted trace to stdout
- **HTML Visualization**: Generated using the visualization scripts from JSON trace files

Output can be saved to a file using the `-o` option, or printed to stdout if no output file is specified.

### Remote Visualization

For remote servers, use SSH port forwarding to view visualizations locally:

```bash
# On remote server
bash scripts/serve_visualization.sh trace.json 8080

# On local machine  
ssh -L 8080:localhost:8080 user@remote-server

# Then open http://localhost:8080/[filename].html in your browser
```
