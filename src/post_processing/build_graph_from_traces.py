import os
import re
import json 
import site
import numpy as np
import networkx as nx
from collections import defaultdict
from dataclasses import dataclass, field

class TraceEntry:
    def __init__(
        self,
        location=None,
        parent_location=None,
        parent_call=None,
        name=None,
        arguments=None,
        depth=None,
        is_external=False,
        call_type=None,
        number_of_calls=None,
        args=None,
        kwargs=None,
        is_first_call=False,
        is_last_call=False
    ):
        self.location = location
        self.parent_location = parent_location
        self.parent_call = parent_call
        self.name = name
        self.arguments = arguments if arguments is not None else {}
        self.depth = depth
        self.is_external = is_external
        self.call_type = call_type
        self.number_of_calls = number_of_calls
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.is_first_call = is_first_call
        self.is_last_call = is_last_call

    def is_callable(self):
        return self.call_type not in ['import', 'class_declaration', 'external_call']

@dataclass
class WhereEntry:
    # Structure to store the output of a Where Command, along with alternative paths from the same start and end node
    stack_trace: list[TraceEntry] = field(default_factory=list)
    alternate_paths: list[TraceEntry] = field(default_factory=list)

def get_stack_trace(traces: list[TraceEntry], entry_idx: int) -> list[TraceEntry]:
    stack_trace = []
    current_entry = traces[entry_idx]
    current_depth = current_entry.depth
    while current_entry:
        stack_trace.append(current_entry)
        # Find the previous entry with a lower depth
        previous_entries = traces[:entry_idx]
        depth_minus_one_entries = [entry for entry in previous_entries if entry.depth == current_depth - 1]
        if depth_minus_one_entries:
            # We select the last entry with the same depth minus one
            current_depth -= 1
            current_entry = depth_minus_one_entries[-1]
            assert current_entry.depth == current_depth, f"Expected depth {current_depth}, got {current_entry.depth}"
            entry_idx = traces.index(current_entry)
        else:
            current_entry = None

    return stack_trace

def pp(stack_trace):
    for entry in stack_trace:
        print(f"Location: {entry.location}")
        print(f"Name: {entry.name}")
        print(f"Depth: {entry.depth}")
        print(f"Arguments: {entry.arguments}")
        print(f"Parent Call: {entry.parent_call}")
        print(f"Call type : {entry.call_type}")
        print(f'Is External: {entry.is_external}')
        if entry.number_of_calls: 
            # This is a trace entry that has been called multiple times
            print(f"Number of Calls: {entry.number_of_calls}")
        print("-" * 40)

def show(traces, line_no):
    """Pretty print the stack trace for a given line number."""
    stack_trace = get_stack_trace(traces, line_no)
    pp(stack_trace)

def build_stack_trace_graph(stack_traces, G=None):
    if G is None:
        G = nx.DiGraph()
    for entry_idx, stack_trace in stack_traces.items():
        for i in range(len(stack_trace) - 1):
            parent = stack_trace[i]
            child = stack_trace[i + 1]
            # G.add_edge(parent['location'], child['location'])
            G.add_edge(child.location, parent.location)
    return G

# for a given node in the graph, compute the list of paths to another node. If cycle exists, mark it.
def find_paths(G, start_node, end_node):
    """Find all paths from start_node to end_node in the graph G."""
    paths = []
    def dfs(current_node, path):
        if current_node == end_node:
            paths.append(path.copy())
            return
        for neighbor in G.neighbors(current_node):
            if neighbor not in path:  # Avoid cycles
                path.append(neighbor)
                dfs(neighbor, path)
                path.pop()
    
    dfs(start_node, [start_node])

    # assert all paths are unique
    unique_paths = set(tuple(path) for path in paths)
    paths = [list(path) for path in unique_paths]

    return paths

def detect_cycles(G):
    """Detect cycles in the graph G."""
    cycles = []
    for node in G.nodes:
        visited = set()
        stack = []
        
        def dfs(current_node):
            if current_node in visited:
                if current_node in stack:
                    cycles.append(stack[stack.index(current_node):] + [current_node])
                return
            visited.add(current_node)
            stack.append(current_node)
            for neighbor in G.neighbors(current_node):
                dfs(neighbor)
            stack.pop()
        
        dfs(node)
    
    return cycles

# For some external calls, the "location" entry is logged as 
# # "location": "/home/lpagecaccia/miniconda3/envs/sdpa/lib/python3.10/site-packages/lightning_utilities/core/rank_zero.py:28",
def find_all_external_packages(traces):
    external_packages = set()
    pckg_path = site.getsitepackages()[0]  # Get the first site-packages path
    
    for trace in traces:
        if trace.location and trace.location.startswith(pckg_path):
            package = trace.location.split('/site-packages/')[1].split('/')[0]
            external_packages.add(package)
    return external_packages

def extract_leaf_indices(traces):
    # A trace entry is a leaf node if the next entry in the trace has a lower depth.
    leaf_nodes_indices = []
    for i in range(len(traces) - 1):
        current_entry = traces[i]
        next_entry = traces[i + 1]
        if next_entry['depth'] < current_entry['depth']:
            leaf_nodes_indices.append(i)

    return leaf_nodes_indices


def extract_callables(traces, include_external_calls=True):
    # A trace entry is a non-import node if it does not contain 'import' in its name.
    non_import_nodes_indices = []
    for i, trace in enumerate(traces):
        if trace.is_callable():
            if trace.is_external and not include_external_calls:
                continue
            non_import_nodes_indices.append(i)

    return non_import_nodes_indices

def cluster_by_call_type(traces):
    call_type_clusters = defaultdict(list)
    for i, trace in enumerate(traces):
        call_type_clusters[trace.call_type].append(i)
    
    return call_type_clusters

def show(traces, line_no):
    pp(get_stack_trace(traces, line_no))

def get_stack_traces(trace_data, indices):
    """
    Get stack traces for a list of indices from the trace data.
    """
    fill_ = lambda x : (8 - len(str(x))) * ' ' + str(x)
    stack_traces = {}
    for entry_idx in indices:
        print(f'Processing line {fill_(entry_idx)} of {len(trace_data)}', end='\r')
        stack_traces[entry_idx] = get_stack_trace(trace_data, entry_idx)
    return stack_traces

def get_where_entries(stack_traces, G):
    global args
    """
    For each stack trace entry, get the equivalent of `pdb where`, and alternate paths from the same start and end node
    """
    where_entries = {}
    for entry_idx, stack_trace in stack_traces.items():
        start_location = stack_trace[-1].location
        end_location = stack_trace[0].location
        # check if `end_location` matches `<*>` e.g. `<string>:2` or '<module>:1'
        if re.match(r'<.*?>:\d+', end_location):
            print(f'Skipping end location : {end_location}')
            continue
        paths = find_paths(G, start_location, end_location)
        if len(paths) < args.min_path_amt: 
            print(f'Skipping entry {entry_idx} as it has only {len(paths)} path(s)')
            continue
        
        # Create a WhereEntry object
        where_entry = WhereEntry(
            stack_trace=stack_trace,
            alternate_paths=paths
        )
        where_entries[entry_idx] = where_entry
    
    return where_entries

def is_distinct_paths(paths):
    """
    Check if all paths are distinct.
    """
    seen = set()
    for path in paths:
        path_tuple = tuple(path)
        if path_tuple in seen:
            return False
        seen.add(path_tuple)
    return True

def group_by_start_and_end(where_entries):
    """
    Group stack traces by their start and end locations.
    """
    grouped = defaultdict(list)
    for entry_idx, where_entry in where_entries.items():
        start_location = where_entry.stack_trace[-1].location
        end_location = where_entry.stack_trace[0].location
        grouped[(start_location, end_location)].append(where_entry)
    return grouped

def mark_first_and_last_calls(trace_data, include_external_calls=True):
    # For each trace entry, if it's a function call, get the first and last call
    # First, we bin each trace entry by its location
    call_bins = defaultdict(list)
    for i, entry in enumerate(trace_data):
        if entry.is_callable():
            call_bins[entry.location].append(i)

    # Now, for each bin, we can get the first and last call
    first_last_call_indices = []
    for location, indices in call_bins.items():
        if not include_external_calls and any(trace_data[i].is_external for i in indices):
            continue
        trace_data[indices[0]].is_first = True
        trace_data[indices[-1]].is_last = True
        first_last_call_indices.append(indices[0])
        first_last_call_indices.append(indices[-1])

    return first_last_call_indices

def to_sequence(stack_trace):
    """
    Convert a stack trace to a sequence of locations.
    """
    return [entry.location for entry in stack_trace]

def remove_nested_stack_traces(stack_traces):
    """
    Given stack trace A and stack trace B, if A is a subset of B, remove A.
    """
    unique_stack_traces = {}
    for idx, stack_trace in stack_traces.items():
        # check if the stack trace is already in the unique_stack_traces
        if idx in unique_stack_traces:
            continue
        is_subset = False
        for other_idx, other_stack_trace in unique_stack_traces.items():
            seq_stack_strace = to_sequence(stack_trace)
            seq_other_stack_trace = to_sequence(other_stack_trace)
            if set(seq_stack_strace).issubset(set(seq_other_stack_trace)) and seq_stack_strace != seq_other_stack_trace:
                print(f'Skipping {idx} as it is a subset of {other_idx}')
                print(to_sequence(stack_trace), 'is a subset of', to_sequence(other_stack_trace))
                is_subset = True
                break
        if not is_subset:
            unique_stack_traces[idx] = stack_trace
    
    return unique_stack_traces

if __name__ == '__main__':
    # argparse, with arg --trace_files, array of string paths to files
    import argparse
    parser = argparse.ArgumentParser(description='Process some trace files.')
    parser.add_argument('--trace_files', nargs='+', required=True, help='List of trace files to process')
    parser.add_argument('--min_path_amt', type=int, default=4, help='Number of total paths to minimally have for where entry')
    args = parser.parse_args()

    G = None
    for trace_file in args.trace_files:
        print(f'Processing trace file: {trace_file}')
        with open(trace_file, 'r') as f:
            traces = json.load(f)
            metadata, trace_data = traces['metadata'], traces['trace_data']

        # convert to TraceEntry objects
        trace_data = [TraceEntry(**entry) for entry in trace_data]

        ok_idx = mark_first_and_last_calls(trace_data, include_external_calls=False)
        print(f'Found {len(ok_idx)} callable entries in the trace data.')
        call_types = cluster_by_call_type(trace_data)
        show(trace_data, ok_idx[-100])

        stack_traces = get_stack_traces(trace_data, ok_idx)
        stack_traces = remove_nested_stack_traces(stack_traces)

        # Next, let's build a graph of the stack trace, where a stack trace is a "list" of nodes, and each node is a trace entry.
        # The node will be the location of the entry.

        # search for the trace in our where output
        indices = [i for i, trace in enumerate(trace_data) if trace.parent_call == 'storage_uri, container = self._parse_repo_id_to_storage_info(repo_id)']
        G = build_stack_trace_graph(stack_traces, G=G)

        # sort the nodes by degree
        sorted_nodes = sorted(G.nodes, key=lambda x: G.degree(x), reverse=True)

        # Print all the nodes in the graph, and the number of edges
        for node in sorted_nodes:
            print(f"Node: {node}, Edges: {G.degree(node)}")

        where_entries = get_where_entries(stack_traces, G)

        # Finally, let's group the where entries by their start and end locations.
        grouped_where_entries = group_by_start_and_end(where_entries)

        print(f'Found {len(grouped_where_entries)} unique trajectories out of {len(where_entries)} where entries.')

        for (start, end), value in grouped_where_entries.items():
            pp(value[0].stack_trace)
            print('\n')
            pp(value[-1].stack_trace)
            print('\n\n\n')

        print(np.bincount([len(entry.alternate_paths) for entry in where_entries.values()]))

        assert all(is_distinct_paths(entry.alternate_paths) for entry in where_entries.values()), "There are non-distinct paths in the where entries."

        external_packages = find_all_external_packages(trace_data)
        cycles = detect_cycles(G)