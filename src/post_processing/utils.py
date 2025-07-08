import json
import site
import random
from typing import Any, Dict

class StepLocation: 
    # Stores minimal information about a "step" in the trace
    # It's basically a line in the code + how it's being used (e.g. function call, import, etc.)
    
    # Class-level registry to store unique instances
    _registry: Dict[tuple, "StepLocation"] = {}

    def __init__(self, location=None, name=None, call_type=None, is_external=False):
        # Only initialize if this is a new instance (not from registry)
        if not hasattr(self, '_initialized'):
            self.location = location
            self.name = name
            self.call_type = call_type
            self.is_external = is_external
            self.references = []
            self._initialized = True

    # method to clear the registry, useful for testing or resetting state
    @classmethod
    def clear_registry(cls):
        """
        Clear the registry of StepLocation instances.
        This is useful for testing or resetting state.
        """
        cls._registry = {}

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

    def __repr__(self):
        return f"StepLocation(location={self.location}, name={self.name}, call_type={self.call_type}, is_external={self.is_external})"
    
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

    @property
    def root(self):
        """
        Returns the root node of the trace.
        """
        current_node = self
        while current_node.previous_node:
            current_node = current_node.previous_node
        return current_node

    @property
    def upest_node(self):
        """
        Returns the upest node of the trace.
        This is the node that is the furthest up in the trace.
        """
        current_node = self
        while current_node.up_node:
            current_node = current_node.up_node
        return current_node

    def __repr__(self):
        # Avoid recursion by not including circular references
        return f"StepNode(location={self.location}, name={self.name}, depth={self.depth}), call_type={self.call_type}, is_external={self.is_external}, arguments={self.arguments})"
    
    def __str__(self):
        # Avoid recursion by not including circular references
        return f"StepNode(location={self.location}, name={self.name}, depth={self.depth}), call_type={self.call_type}, is_external={self.is_external}, arguments={self.arguments})"

    def to_dict(self):
        """
        Convert StepNode to dictionary for serialization.
        Avoids circular references by only including essential data.
        """
        return {
            'location': self.location,
            'name': self.name,
            'call_type': self.call_type,
            'is_external': self.is_external,
            'arguments': self.arguments,
            'depth': self.depth,
            'number_of_calls': self.number_of_calls,
            'parent_location': self.parent_location,
            'parent_call': self.parent_call
        }

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
    def where(self):
        # Like stack_trace, but returns in a format analogous to the `where` command in a debugger.
        # Namely, 1) 1 node deeper because "root".parent_location is also added
        # Use `child.parent_location` instead of self.location -> this is aligned with pdb where
        # For the last node, we increment the line number by 1 (as if we set a breakpoint on the next line)
        def increment_by_one(loc):
            if loc:
                parts = loc.rsplit(":", 1)
                if len(parts) > 1:
                    return f"{parts[0]}:{int(parts[1]) + 1}"
                else:
                    return loc
            return None

        trace = [increment_by_one(self.location)]
        current_node = self
        while current_node:
            trace.append(current_node.parent_location)
            current_node = current_node.up_node
        return trace[::-1][1:]

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
    def past(self):
        """
        Returns the past nodes in the trace, starting from the root node.
        """
        past_nodes = []
        current_node = self
        while current_node:
            past_nodes.append(current_node)
            current_node = current_node.previous_node
        return past_nodes[::-1]

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

class WhereEntry:
    # Structure to store the output of a Where Command, along with alternative paths from the same start and end node
    def __init__(self, stack_trace=None, alternate_paths=None, command=None):
        self.stack_trace = stack_trace if stack_trace is not None else []
        self.alternate_paths = alternate_paths if alternate_paths is not None else []
        self.command = command

    def to_dict(self):
        return {
            'stack_trace': [entry.to_dict() for entry in self.stack_trace],
            'alternate_paths': [[entry.to_dict() for entry in path] for path in self.alternate_paths],
            "command": self.command
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

'''
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
'''

def find_paths(end_node):
    # Now that we are using the proper format for the `where` output, we don't need the start 
    # nodes to match. We can simply find all paths to the end_node.
    paths = []
    def recurse(current_node, path):
        # This function takes in a path from end_node to current_node. It will explore all
        # possible paths to the end_node by following the down_nodes.
        # it returns all paths from the end_node to neighbors of current_node (if not already in path)
        # terminate when current_node has no up_node
        if current_node is None:
            # We reached the root node, add the path to the paths list
            # path.insert(0, current_node)
            paths.append(path.copy())
            return

        # if it's not none, we can continue

        # NOTE: we know current_node has an up_node, safe to use parent_location ? 
        # Iterate through all down nodes of the current node
        for sibling in current_node.step_location.references:
            parent = sibling.up_node

            # If the neighbor is not already in the path, we can explore it
            if sibling.step_location not in [x.step_location for x in path]:
                # Add the neighbor to the path
                path.insert(0, sibling)
                # Recurse into the neighbor
                recurse(parent, path)
                # Backtrack by removing the first node from the path
                # (we are using insert(0, ...) to build the path from end_node to start_node)
                path.pop(0)

    recurse(end_node, [])

    # We want to make sure that the StepLocation paths are unique, NOT JUST the StepNode paths
    random.shuffle(paths)

    unique_paths = {}
    for path in paths:
        unique_paths['-'.join(to_sequence(path))] = path

    return list(unique_paths.values())

def find_all_paths_to_node(end_node, expand=False):
    """
    Find all paths from any root node to the given end_node.
    A root node is defined as a node with no up_node (i.e., up_node is None).
    
    This function works backwards from the end_node to find all possible paths,
    which is much more efficient than expanding the entire tree from all roots.
    
    Args:
        end_node: The target StepNode to find paths to
        
    Returns:
        List of paths, where each path is a list of StepNode objects from root to end_node
    """
    all_paths = []
    
    def find_paths_from_node(target_node, visited=None, expand=False):
        """
        Find all paths from any root node to target_node by working backwards from the target.
        Much more efficient than expanding the entire tree from roots.
        """
        if visited is None:
            visited = set()
        
        # Add current node to visited set (using step_location for cycle detection)
        visited.add(str(target_node.step_location))
        
        # Base case: we reached a root node (no up_node)
        if target_node.up_node is None:
            return [[target_node]]
        
        # Recursive case: explore all parent nodes (up_nodes) through siblings
        paths = []
        
        # Get all siblings that share the same step_location as the target's up_node
        up_node = target_node.up_node
        if expand: 
            up_nodes = [sibling.up_node for sibling in target_node.step_location.references if sibling.up_node is not None]
        else:
            up_nodes = [sibling for sibling in up_node.step_location.references if sibling is not None]
        for up_node in up_nodes:
            # for sibling in up_node.step_location.references:
            #     # Avoid cycles by checking if we've already visited this step_location
            if str(up_node.step_location) not in visited:
                # Find all paths from root to this sibling
                parent_paths = find_paths_from_node(up_node, visited.copy(), expand=expand)
                # Append current target node to each path found
                for path in parent_paths:
                    paths.append(path + [target_node])

        """
        (OLD CODE)
        # Recursive case: explore all down_nodes
        paths = []
        # for child in current_node.down_nodes:
        for child in [down_node for sibling in current_node.step_location.references for down_node in sibling.down_nodes]:
            # Avoid cycles by checking if we've already visited this step_location
            if str(child.step_location) not in visited:
                # Find all paths from child to target
                child_paths = find_paths_from_node(child, target_node, visited.copy())
                # Prepend current node to each path found
                for path in child_paths:
                    paths.append([current_node] + path)
        """

        return paths
    
    # Find all paths from root nodes to the end_node by working backwards
    all_paths = find_paths_from_node(end_node, expand=expand)
    
    return all_paths


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


def read_jsonl_file(file_path):
    """
    Reads a JSONL file and returns a list of dictionaries.
    
    Args:
        file_path (str): The path to the JSONL file.
        
    Returns:
        list: A list of dictionaries containing the data from the JSONL file.
    """
    data = []
    with open(file_path, 'r') as file:
        for line in file:
            data.append(json.loads(line.strip()))
    return data

def read_json_file(path):
    """
    Reads a JSON file and returns its content.
    
    Args:
        path (str): The path to the JSON file.
        
    Returns:
        dict: The content of the JSON file.
    """
    with open(path, 'r') as f:
        return json.load(f)


def path_to_where(path, end_node_at_the_end=True):
    # Like stack_trace, but returns in a format analogous to the `where` command in a debugger.
    # Namely, 1) 1 node deeper because "root".parent_location is also added
    # Use `child.parent_location` instead of self.location -> this is aligned with pdb where
    # For the last node, we increment the line number by 1 (as if we set a breakpoint on the next line)
    
    if end_node_at_the_end:
        path = path[::-1]

    def increment_by_one(loc):
        if loc:
            parts = loc.rsplit(":", 1)
            if len(parts) > 1:
                return f"{parts[0]}:{int(parts[1]) + 1}"
            else:
                return loc
        return None

    trace = [increment_by_one(path[0].location)]
    current_node = path[0]
    for current_node in path[1:]:
        trace.append(current_node.parent_location)
        current_node = current_node.up_node
    return trace[::-1][1:]