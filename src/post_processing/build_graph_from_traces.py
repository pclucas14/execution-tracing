import json 
import site
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class StepLocation: 
    # Stores minimal information about a "step" in the trace
    # It's basically a line in the code + how it's being used (e.g. function call, import, etc.)
    location: Optional[str] = None
    name: Optional[str] = None
    call_type: Optional[str] = None
    is_external: bool = False
    references: List["StepNode"] = field(default_factory=list)

    # Class-level registry to store unique instances
    _registry: Dict[tuple, "StepLocation"] = field(default_factory=dict, init=False, repr=False)

    def __new__(cls, location=None, name=None, call_type=None, is_external=False):
        # Ensure the registry exists at class level
        if not hasattr(cls, '_registry') or cls._registry is None:
            cls._registry = {}
        
        # Create a key from the attributes
        key = (location, name, call_type, is_external)
        
        # Check if an instance with these attributes already exists
        if key in cls._registry:
            return cls._registry[key]
        
        # Create new instance and register it
        instance = object.__new__(cls)
        cls._registry[key] = instance
        return instance

    def __eq__(self, other):
        if not isinstance(other, StepLocation):
            return False
        # Compare only the basic fields, not circular references
        return (self.location == other.location and 
                self.name == other.name and 
                self.call_type == other.call_type and
                self.is_external == other.is_external)

    def is_callable(self):
        return self.call_type not in ['import', 'class_declaration', 'external_call']

    def __str__(self):
        return f"StepLocation(location={self.location}, name={self.name}, call_type={self.call_type})"
    
class StepNode:
    # Where in the code ?
    def __init__(
        self,
        arguments=None,
        parent_location=None,
        parent_call=None,
        depth=None,
        number_of_calls=None,
        next_node=None,
        previous_node=None,
        up_node=None,
        down_nodes=None,
        location=None,
        name=None,
        call_type=None,
        is_external=False,
        step_location=None,
        *args,
        **kwargs
    ):
        # Create or retrieve StepLocation if not provided
        if step_location is None:
            self.step_location = StepLocation(
                location=location,
                name=name,
                call_type=call_type,
                is_external=is_external
            )
        else:
            self.step_location = step_location

        # add this node to the references of the step location
        self.step_location.references.append(self)            

        # Set arguments
        self.arguments = arguments
        self.parent_location = parent_location
        self.parent_call = parent_call
        self.depth = depth
        self.number_of_calls = number_of_calls

        self.previous_node = previous_node
        self.next_node = next_node
        self.up_node = up_node
        self.down_nodes = down_nodes if down_nodes is not None else []
        self._runtime_trace = None  # Lazy loading of runtime trace

    @property
    def location(self):
        return self.step_location.location

    @property
    def name(self):
        return self.step_location.name

    @property
    def call_type(self):
        return self.step_location.call_type

    @property
    def is_external(self):
        return self.step_location.is_external

    @property
    def is_first_call(self):
        return self.step_location.references[0] is self 
    
    @property
    def is_last_call(self):
        return self.step_location.references[-1] is self

    @property
    def is_leaf_node(self):
        return len(self.down_nodes) == 0

    def __repr__(self):
        # Avoid recursion by not including circular references
        return f"StepNode(location={self.location}, name={self.name}, depth={self.depth}), call_type={self.call_type}, is_external={self.is_external}, arguments={self.arguments})"
    
    def __str__(self):
        # Avoid recursion by not including circular references
        return f"StepNode(location={self.location}, name={self.name}, depth={self.depth}), call_type={self.call_type}, is_external={self.is_external}, arguments={self.arguments})"

    @property
    def stack_trace(self):
        """
        Returns the stack trace as a list of StepNode objects.
        """
        trace = []
        current_node = self
        while current_node:
            trace.append(current_node)
            current_node = current_node.up_node
        return trace[::-1]

    @property
    def runtime_trace(self):
        """
        Lazily compute the runtime trace.
        """
        if self._runtime_trace is None:
            trace = []
            current_node = self
            while current_node:
                trace.append(current_node)
                current_node = current_node.next_node
            self._runtime_trace = trace[::-1] 

        return self._runtime_trace

    @property
    def leaf_nodes(self):
        """ 
        Starting with the current node as root, return all the leaf nodes in the trace.
        A node is a leaf node if it has no down nodes.
        """
        if not self._leaf_nodes:
            self._leaf_nodes = []
            current_node = self
            while current_node:
                if current_node.is_leaf_node:
                    self._leaf_nodes.append(current_node)
                current_node = current_node.next_node

        return self._leaf_nodes

@dataclass
class WhereEntry:
    # Structure to store the output of a Where Command, along with alternative paths from the same start and end node
    stack_trace: list[StepNode] = field(default_factory=list)
    alternate_paths: list[StepNode] = field(default_factory=list)

    def to_dict(self):
        return {
            'stack_trace': [entry.to_dict() for entry in self.stack_trace],
            'alternate_paths': [[entry.to_dict() for entry in path] for path in self.alternate_paths]
        }
    
def build_runtime_trace(raw_trace_data: list[Dict[str, Any]]) -> StepNode:
    """
    Convert raw trace data to a list of StepNode objects.
    """
    previous_node = root_node = None

    # To keep track of the previous "depth" node, let's keep track of the latest node 
    # at each depth
    depths = {}

    for entry in raw_trace_data:
        previous_depth_node = depths.get(entry['depth'] - 1)

        node = StepNode(**entry, 
                        previous_node=previous_node, 
                        up_node=previous_depth_node)

        # Update the previous node
        if not previous_node:
            root_node = node
        else:
            previous_node.next_node = node

        if previous_depth_node:
            previous_depth_node.down_nodes.append(node)

        previous_node = node

        # Update the latest node at this depth
        depths[node.depth] = node

    return root_node

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

# for a given node in the graph, compute the list of paths to another node. If cycle exists, mark it.
def find_paths(start_node, end_node):
    """Find all paths from start_node to end_node in the graph G."""
    paths = []
    def dfs(current_node, path):
        if current_node.step_location == end_node.step_location:
            paths.append(path.copy())
            return
        for neighbor in current_node.down_nodes:  # Assuming down_nodes are the neighbors
            if neighbor.step_location not in [x.step_location for x in path]:  # Avoid cycles
                path.append(neighbor)
                dfs(neighbor, path)
                path.pop()

    dfs(start_node, [start_node])

    # We want to make sure that the StepLocation paths are unique, NOT JUST the StepNode paths
    random.shuffle(paths)

    unique_paths = {}
    for path in paths:
        unique_paths['-'.join(to_sequence(path))] = path

    return list(unique_paths.values())

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
    parser.add_argument('--max_siblings', type=int, default=100, help='Maximum number of leaf nodes per parent node')
    parser.add_argument('--leafs_only', action='store_true', help='If set, only leaf nodes will be considered')
    args = parser.parse_args()

    G = None
    start_nodes = []
    for trace_file in args.trace_files:
        print(f'Processing trace file: {trace_file}')
        with open(trace_file, 'r') as f:
            traces = json.load(f)
            metadata, raw_trace_data = traces['metadata'], traces['trace_data']

        start_node = build_runtime_trace(raw_trace_data)
        start_nodes.append(start_node)

        runtime_traces = start_node.runtime_trace

        # First, we filter out nodes with insufficient alternate paths from root to said node
        # filtered_nodes = [node for node in runtime_traces if len(find_paths(start_node, node)) >= args.min_path_amt]

        # Once we have the runtime traces, let's filter out to select only :
        # 1) the first calls to a given StepLocation
        # 2) the last calls to a given StepLocation 

        filtered_nodes = [node for node in runtime_traces if node.is_first_call or node.is_last_call]
        filtered_nodes = [node for node in filtered_nodes if not node.is_external]  # Exclude external calls
        filtered_nodes = [node for node in filtered_nodes if len(find_paths(start_node, node)) >= args.min_path_amt]
        print(f'Found {len(filtered_nodes)} nodes after filtering for first and last calls with at least {args.min_path_amt} paths.')
        
        # 3) are leaf nodes 
        # 4) potentially restrict the amount of sibling nodes
        if args.leafs_only:
            parents_to_leaf_nodes = list(set([
                node.up_node for node in filtered_nodes if node.is_leaf_node and node.up_node is not None
            ]))
            subsampled_leaf_nodes = []
            for parent in parents_to_leaf_nodes:
                leaf_nodes = [child for child in parent.down_nodes if child.is_leaf_node and not child.is_external]
                if len(leaf_nodes) > args.max_siblings:
                    leaf_nodes = random.sample(leaf_nodes, args.max_siblings)
                subsampled_leaf_nodes.extend(leaf_nodes)

            filtered_nodes = subsampled_leaf_nodes
        else:
            # We consider all nodes, but remove a node if it appears in another node's trace
            filtered_nodes = [
                node for node in filtered_nodes if not any(
                    other_node != node and node.step_location in other_node.step_location.references
                    for other_node in filtered_nodes
                )
            ]

        # Finally, build the where entries
        where_entries = []

        for node in filtered_nodes:
            # Get the stack trace for this node
            stack_trace = node.stack_trace
            paths = find_paths(start_node, node)
            alternate_paths = [path for path in paths if to_sequence(path) != to_sequence(stack_trace)]
            assert len(alternate_paths) + 1 == len(paths), "The number of alternate paths should be one less than the total paths."
            where_entry = WhereEntry(
                stack_trace=stack_trace,
                alternate_paths=alternate_paths
            )
            where_entries.append(where_entry)

        assert all(is_distinct_paths(entry.alternate_paths) for entry in where_entries), "There are non-distinct paths in the where entries."

        # Finally, let's save as a dataset we can use Later. 
        # where_traces = [x.to_dict() for x in where_entries.values()]

        external_packages = find_all_external_packages(runtime_traces)
        breakpoint()
        xx = 1  