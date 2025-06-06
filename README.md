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

## Visualization

### Pattern Grouping Visualization

The tracer includes advanced pattern detection that automatically groups repeating sequences of function calls:

```bash
# Serve visualization with pattern grouping (default)
bash scripts/serve_visualization.sh trace_output.json 8080

# Serve without pattern grouping
bash scripts/serve_visualization.sh trace_output.json 8080 --no-patterns
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
