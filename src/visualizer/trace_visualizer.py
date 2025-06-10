import json
import argparse
import os
from collections import defaultdict
from typing import List, Dict, Any, Tuple

class TraceVisualizer:
    def __init__(self, trace_data: List[Dict[str, Any]]):
        self.trace_data = trace_data
        self.condensed_entries = []
        
    def condense_repeated_calls(self) -> List[Dict[str, Any]]:
        """Condense repeated contiguous function calls into single entries with counts."""
        if not self.trace_data:
            return []
        
        condensed = []
        current_group = None
        call_index = 1
        
        for i, entry in enumerate(self.trace_data):
            # Create a signature for the call based on function name and location only
            signature = self._get_call_signature_without_args(entry)
            
            if current_group and current_group['signature'] == signature:
                # Same function call, increment count
                current_group['count'] += 1
                current_group['entries'].append(entry)
                current_group['end_call_number'] = call_index
            else:
                # Different function call, start new group
                if current_group:
                    condensed.append(current_group)
                
                current_group = {
                    'signature': signature,
                    'count': 1,
                    'entries': [entry],
                    'first_entry': entry,
                    'start_call_number': call_index,
                    'end_call_number': call_index
                }
            
            call_index += 1
        
        # Don't forget the last group
        if current_group:
            condensed.append(current_group)
        
        return condensed
    
    def _get_call_signature(self, entry: Dict[str, Any]) -> str:
        """Create a unique signature for a function call."""
        # Include function name, location, and arguments
        args_str = json.dumps(entry.get('arguments', {}), sort_keys=True)
        return f"{entry.get('name', '')}|{entry.get('location', '')}|{args_str}"
    
    def _get_call_signature_without_args(self, entry: Dict[str, Any]) -> str:
        """Create a signature for a function call without arguments."""
        # Only include function name and location
        return f"{entry.get('name', '')}|{entry.get('location', '')}"
    
    def format_as_tree(self, show_numbers: bool = True, show_parent_calls: bool = False) -> str:
        """Format the trace as a tree structure with indentation."""
        output_lines = []
        depth_stack = []
        
        condensed = self.condense_repeated_calls()
        
        for group in condensed:
            entry = group['first_entry']
            count = group['count']
            depth = entry.get('depth', 0)
            
            # Adjust depth stack
            while len(depth_stack) > depth:
                depth_stack.pop()
            
            # Create indentation using spaces instead of Unicode characters
            indent = "    " * depth  # 4 spaces per level
            
            # Format call numbers
            call_number_str = ""
            if show_numbers:
                if count > 1:
                    call_number_str = f"[#{group['start_call_number']}-{group['end_call_number']}] "
                else:
                    call_number_str = f"[#{group['start_call_number']}] "
            
            # Format the entry
            name = entry.get('name', 'unknown')
            location = entry.get('location', 'unknown')
            is_external = entry.get('is_external', False)
            parent_call = entry.get('parent_call', '')
            
            # For grouped calls, show argument variations if they differ
            if count > 1:
                # Check if all arguments are the same
                all_args = [e.get('arguments', {}) for e in group['entries']]
                args_vary = len(set(json.dumps(args, sort_keys=True) for args in all_args)) > 1
                
                if args_vary:
                    # Show that arguments vary
                    args = "varying args"
                else:
                    # All arguments are the same, show them
                    args = self._format_arguments_concise(entry.get('arguments', {}))
            else:
                args = self._format_arguments_concise(entry.get('arguments', {}))
            
            # Build the line with depth information
            depth_str = f"[depth:{depth}] "
            if count > 1:
                line = f"{call_number_str}{depth_str}{indent}{name}({args}) [{location}] x {count} times"
            else:
                line = f"{call_number_str}{depth_str}{indent}{name}({args}) [{location}]"
            
            if is_external:
                line += " [EXTERNAL]"
            
            # Add parent call if requested and available
            if show_parent_calls and parent_call:
                line += f" ← {parent_call}"
            
            output_lines.append(line)
            
        return "\n".join(output_lines)
    
    def _format_arguments_concise(self, args: Dict[str, Any]) -> str:
        """Format arguments in a concise way."""
        if not args:
            return ""
        
        formatted_args = []
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 20:
                value = f'"{value[:17]}..."'
            elif isinstance(value, str):
                value = f'"{value}"'
            elif isinstance(value, (list, dict)) and len(str(value)) > 30:
                value = f"{type(value).__name__}(...)"
            formatted_args.append(f"{key}={value}")
        
        return ", ".join(formatted_args)
    
    def generate_summary_stats(self) -> str:
        """Generate summary statistics about the trace."""
        stats = {
            'total_calls': len(self.trace_data),
            'unique_functions': len(set(e.get('name', '') for e in self.trace_data)),
            'max_depth': max((e.get('depth', 0) for e in self.trace_data), default=0),
            'external_calls': sum(1 for e in self.trace_data if e.get('is_external', False)),
            'files_touched': len(set(e.get('location', '').split(':')[0] for e in self.trace_data))
        }
        
        # Count calls per function
        function_counts = defaultdict(int)
        for entry in self.trace_data:
            function_counts[entry.get('name', 'unknown')] += 1
        
        # Find most called functions
        most_called = sorted(function_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        output = ["=== Trace Summary ==="]
        output.append(f"Total function calls: {stats['total_calls']} (numbered #1-{stats['total_calls']})")
        output.append(f"Unique functions: {stats['unique_functions']}")
        output.append(f"Maximum call depth: {stats['max_depth']}")
        output.append(f"External calls: {stats['external_calls']}")
        output.append(f"Files touched: {stats['files_touched']}")
        output.append("\nMost called functions:")
        for func, count in most_called:
            output.append(f"  - {func}: {count} times")
        
        return "\n".join(output)
    
    def generate_call_graph_dot(self) -> str:
        """Generate a DOT file for Graphviz visualization."""
        edges = defaultdict(int)
        nodes = set()
        
        for i in range(len(self.trace_data) - 1):
            current = self.trace_data[i]
            next_call = self.trace_data[i + 1]
            
            # Check if next call is a child (deeper) of current
            if next_call.get('depth', 0) > current.get('depth', 0):
                caller = current.get('name', 'unknown')
                callee = next_call.get('name', 'unknown')
                nodes.add(caller)
                nodes.add(callee)
                edges[(caller, callee)] += 1
        
        dot_lines = ["digraph CallGraph {"]
        dot_lines.append('  rankdir=TB;')
        dot_lines.append('  node [shape=box, style=rounded];')
        
        # Add nodes
        for node in nodes:
            dot_lines.append(f'  "{node}";')
        
        # Add edges with call counts
        for (caller, callee), count in edges.items():
            if count > 1:
                dot_lines.append(f'  "{caller}" -> "{callee}" [label="{count}x"];')
            else:
                dot_lines.append(f'  "{caller}" -> "{callee}";')
        
        dot_lines.append("}")
        return "\n".join(dot_lines)


def visualize_trace(input_file: str, output_format: str = "tree", output_file: str = None):
    """Main function to visualize a trace file."""
    # Load the trace data
    with open(input_file, 'r') as f:
        trace_data = json.load(f)
    
    visualizer = TraceVisualizer(trace_data)
    
    # Generate the requested output
    if output_format == "tree":
        output = visualizer.format_as_tree()
    elif output_format == "summary":
        output = visualizer.generate_summary_stats()
    elif output_format == "dot":
        output = visualizer.generate_call_graph_dot()
    elif output_format == "all":
        output = []
        output.append(visualizer.generate_summary_stats())
        output.append("\n\n=== Call Tree ===")
        output.append(visualizer.format_as_tree())
        output = "\n".join(output)
    else:
        raise ValueError(f"Unknown output format: {output_format}")
    
    # Write output
    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)
        print(f"Visualization written to: {output_file}")
    else:
        print(output)


def main():
    """CLI entry point for the visualizer."""
    parser = argparse.ArgumentParser(description='Visualize Python execution traces')
    parser.add_argument('trace_file', help='JSON trace file to visualize')
    parser.add_argument('-f', '--format', 
                        choices=['tree', 'summary', 'dot', 'all'],
                        default='tree',
                        help='Output format (default: tree)')
    parser.add_argument('-o', '--output', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.trace_file):
        print(f"Error: Trace file '{args.trace_file}' not found")
        return 1
    
    try:
        visualize_trace(args.trace_file, args.format, args.output)
    except Exception as e:
        print(f"Error visualizing trace: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())