import re
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
            # TODO: add a `call` attribute when running the tracer (akin to parent_call), so we can see 
            # the line being executed

            if loc:
                parts = loc.rsplit(":", 1)
                if len(parts) > 1:
                    return f"{parts[0]}:{int(parts[1]) + 1}"
                else:
                    return loc
            return None

        def is_importlib(loc):
            return 'import' in loc or 'importlib_' in loc
        
        def replace_line_no_by(loc, replacement):
            if loc:
                parts = loc.rsplit(":", 1)
                if len(parts) > 1:
                    return f"{parts[0]}:{replacement}"
                else:
                    return loc
            return None

        trace = [increment_by_one(self.location)]
        current_node = self
        while current_node:
            if current_node.parent_location is None:
                assert current_node.depth == 0
                trace.append(current_node.location)
            elif is_importlib(current_node.parent_location):
                if current_node.up_node is None:
                    breakpoint()
                trace.append(replace_line_no_by(current_node.up_node.location, '<import_call>'))
                # If we hit an importlib location, we stop the trace here
                # This is to avoid going too deep into the import resolution
            else:
                trace.append(current_node.parent_location)
            current_node = current_node.up_node
       
        trace = trace[::-1]
        return trace[1:]

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

    def print_graph(self, max_depth=None, show_siblings=False, expand_all=False):
        """
        Print the full graph starting from this node as root.
        
        Args:
            max_depth: Maximum depth to traverse (None for unlimited)
            show_siblings: Whether to show sibling references from the same StepLocation
            expand_all: Whether to expand and show all sibling nodes recursively
        """
        print_full_graph(self, max_depth=max_depth, show_siblings=show_siblings, expand_all=expand_all)

def print_full_graph(root_node, max_depth=None, show_siblings=False, expand_all=False):
    """
    Print the full graph starting from the given root node.
    
    Args:
        root_node: The StepNode to use as the root of the graph
        max_depth: Maximum depth to traverse (None for unlimited)
        show_siblings: Whether to show sibling references from the same StepLocation
        expand_all: Whether to expand and show all sibling nodes recursively
    """
    def print_node(node, prefix="", is_last=True, depth=0, visited=None, expanded_locations=None):
        if visited is None:
            visited = set()
        if expanded_locations is None:
            expanded_locations = set()
        
        # Check max depth
        if max_depth is not None and depth > max_depth:
            return
        
        # Create a unique identifier for the node
        node_id = id(node)
        
        # Prepare node info
        connector = "└── " if is_last else "├── "
        node_info = f"{node.name or 'unnamed'} @ {node.location}"
        
        # Add additional info
        extras = []
        if node_id in visited:
            extras.append("*CYCLE*")
        
        # Check if this is a sibling reference
        if node.step_location.references.index(node) > 0:
            extras.append(f"ref#{node.step_location.references.index(node) + 1}")
        
        extras_str = f" [{', '.join(extras)}]" if extras else ""
        
        # Print the node
        print(f"{prefix}{connector}{node_info}{extras_str}")
        
        # Mark as visited
        if node_id in visited:
            return
        visited.add(node_id)
        
        # Show siblings if requested
        if show_siblings and len(node.step_location.references) > 1:
            sibling_prefix = prefix + ("    " if is_last else "│   ")
            print(f"{sibling_prefix}    [Siblings: {len(node.step_location.references)} total references]")
        
        # Process children and siblings
        nodes_to_process = []
        
        # Always add direct children
        nodes_to_process.extend(node.down_nodes)
        
        # If expand_all is True and we haven't expanded this location yet, add siblings
        if expand_all and str(node.step_location) not in expanded_locations:
            expanded_locations.add(str(node.step_location))
            
            # Get all sibling nodes except the current one
            siblings = [down_node for sibling in node.step_location.references for down_node in sibling.down_nodes if down_node is not node]
            
            # For each sibling, we want to process its down_nodes
            for sibling in siblings:
                if sibling.down_nodes:
                    # Add a special marker node to indicate this is from a sibling
                    nodes_to_process.append(('sibling', sibling))
        
        if nodes_to_process:
            # Prepare the prefix for children
            extension = "    " if is_last else "│   "
            child_prefix = prefix + extension
            
            # Print each child/sibling expansion
            for i, item in enumerate(nodes_to_process):
                is_last_child = (i == len(nodes_to_process) - 1)
                
                if isinstance(item, tuple) and item[0] == 'sibling':
                    # This is a sibling expansion
                    sibling = item[1]
                    sibling_id = sibling.step_location.references.index(sibling) + 1
                    print(f"{child_prefix}{'└── ' if is_last_child else '├── '}[Sibling expansion from ref#{sibling_id}]")
                    
                    # Print the sibling's children
                    sibling_extension = "    " if is_last_child else "│   "
                    sibling_prefix = child_prefix + sibling_extension
                    
                    for j, child in enumerate(sibling.down_nodes):
                        is_last_sibling_child = (j == len(sibling.down_nodes) - 1)
                        print_node(child, sibling_prefix, is_last_sibling_child, depth + 1, visited, expanded_locations)
                else:
                    # This is a regular child
                    print_node(item, child_prefix, is_last_child, depth + 1, visited, expanded_locations)
    
    print("=" * 80)
    print(f"Call Graph from: {root_node.name or 'root'} @ {root_node.location}")
    if expand_all:
        print("(Showing expanded graph with all sibling paths)")
    print("=" * 80)
    print_node(root_node)
    print("=" * 80)

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

    for index, entry in enumerate(raw_trace_data):
        previous_depth_node = depths.get(entry['depth'] - 1)

        if previous_depth_node is None and entry['depth'] > 0:
            print(f'Warning: No previous depth node found for depth {entry["depth"] - 1}. This might indicate a missing parent call.')

        if entry['is_external']:
            continue

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


def find_alternate_paths(stack_trace, max_paths=None):
    """
    Given a stack trace, find alternate paths to reach the end node. 
    1) For each node in the stack trace, "branch" by looking at node.step_location.references
    2) For each reference, climb up the tree to reach a root node
    stack_trace[0] is the top of the stack 
    stack_trace[-1] is the deepest call (the end node)
    """
    branches = []
    for index in range(len(stack_trace)):
        node = stack_trace[index]
        for sibling in node.step_location.references:
            if sibling is not node:
                branches.append((index, sibling))

    if max_paths is not None:
        print(f'Sampling {max_paths} branches from {len(branches)} total branches.')
        branches = random.sample(branches, min(max_paths, len(branches)))

    # For each branch, find all paths to the root node
    unique_paths = []
    seen_sequences = set()
    for index, sibling in branches:
        path = sibling.stack_trace + stack_trace[index+1:]
        if len(path) == 0 and sibling.depth >  0:
            print(f'Node {sibling} has depth {sibling.depth} but up node is {sibling.up_node} (None). Skipping')
            continue
        if str(path) not in seen_sequences:
            seen_sequences.add(str(path))
            unique_paths.append(path)

    return unique_paths

def find_all_paths_to_node(end_node, expand=False, max_paths=None, oracle_path=None):
    """
    Find all paths from any root node to the given end_node.
    A root node is defined as a node with no up_node (i.e., up_node is None).
    
    This function works backwards from the end_node to find all possible paths,
    which is much more efficient than expanding the entire tree from all roots.
    
    Args:
        end_node: The target StepNode to find paths to
        expand: Whether to expand all siblings or just direct parent references
        max_paths: Maximum number of paths to return (for performance)
        oracle_path: A known path to prioritize variations around
        
    Returns:
        List of paths, where each path is a list of StepNode objects from root to end_node
    """
    unique_paths = []
    seen_sequences = set()
    
    def find_paths_from_node(target_node, visited=None, expand=False):
        """
        Find all paths from any root node to target_node by working backwards from the target.
        Much more efficient than expanding the entire tree from roots.
        """
        if visited is None:
            visited = set()
        
        # Early termination if we already have enough unique paths
        if max_paths is not None and len(unique_paths) >= max_paths:
            return []
        
        # Add current node to visited set (using step_location for cycle detection)
        visited.add(str(target_node.step_location))
        
        # Base case: we reached a root node (no up_node)
        if target_node.up_node is None:
            path = [target_node]
            # Check uniqueness immediately
            path_sequence = tuple(str(node.step_location) for node in path)
            if path_sequence not in seen_sequences:
                seen_sequences.add(path_sequence)
                unique_paths.append(path)
            return [path] if path_sequence not in seen_sequences else []
        
        # Recursive case: explore all parent nodes (up_nodes) through siblings
        paths = []
        
        # Get parent nodes to explore
        if expand: 
            up_nodes = [sibling.up_node for sibling in target_node.step_location.references if sibling.up_node is not None]
        else:
            up_node = target_node.up_node
            up_nodes = [sibling for sibling in up_node.step_location.references if sibling is not None]
        
        # If we have an oracle path, prioritize nodes that appear in it
        if oracle_path:
            oracle_locations = {str(node.step_location) for node in oracle_path}
            # Sort up_nodes to prioritize those in oracle path
            up_nodes = sorted(up_nodes, key=lambda node: str(node.step_location) in oracle_locations, reverse=True)
        
        for up_node in up_nodes:
            # Early termination check
            if max_paths is not None and len(unique_paths) >= max_paths:
                break

            if str(up_node.step_location) not in visited:
                # Find all paths from root to this parent node
                parent_paths = find_paths_from_node(up_node, visited.copy(), expand=expand)
                # Append current target node to each path found
                for path in parent_paths:
                    new_path = path + [target_node]
                    
                    # Check uniqueness immediately before adding
                    path_sequence = tuple(str(node.step_location) for node in new_path)
                    if path_sequence not in seen_sequences:
                        seen_sequences.add(path_sequence)
                        unique_paths.append(new_path)
                        paths.append(new_path)
                        
                        # Early termination check
                        if max_paths is not None and len(unique_paths) >= max_paths:
                            break

        return paths

    # Find all paths from root nodes to the end_node by working backwards
    find_paths_from_node(end_node, expand=expand)
    
    return unique_paths


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
        
    def is_importlib(loc):
        return 'import' in loc or 'importlib_' in loc
    
    def replace_line_no_by(loc, replacement):
        if loc:
            parts = loc.rsplit(":", 1)
            if len(parts) > 1:
                return f"{parts[0]}:{replacement}"
            else:
                return loc
        return None
    
    trace = [increment_by_one(path[0].location)]
    for i, current_node in enumerate(path):
        if current_node.parent_location is None:
            assert current_node.depth == 0, breakpoint()
            assert current_node is path[-1]
            trace.append(current_node.location)
        elif is_importlib(current_node.parent_location):
            if current_node is path[-1]:
                # If this is the last node, we replace the line number by <import_call>
                # We leave as-is -> will get removed 
                trace.append(current_node.parent_location)
            else:
                trace.append(replace_line_no_by(path[i+1].location, '<import_call>'))
            # If we hit an importlib location, we stop the trace here
            # This is to avoid going too deep into the import resolution
        else:
            trace.append(current_node.parent_location)
    return trace[::-1][1:]

def tab_print(text, indent_size=2):
    """
    Transform and print code with proper tabs and carriage returns for enhanced readability.
    
    Args:
        text (str): The text/code to format and print
        indent_size (int): Number of spaces per indentation level (default: 2)
    """
    if isinstance(text, list):
        text = ''.join(text)

    # Replace literal \n with actual newlines
    formatted_text = text.replace('\\n', '\n')
    
    lines = formatted_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Skip empty lines but preserve them
        if not line.strip():
            formatted_lines.append('')
            continue
            
        # Count leading spaces to determine indentation level
        stripped_line = line.lstrip()
        leading_spaces = len(line) - len(stripped_line)
        
        # Convert spaces to proper indentation
        indent_level = leading_spaces // indent_size if leading_spaces > 0 else 0
        proper_indent = '    ' * indent_level  # Use 4 spaces per indent level
        
        # Handle special file markers
        if stripped_line.startswith('[FILE:'):
            formatted_lines.append('\n' + '=' * 60)
            formatted_lines.append(stripped_line)
            formatted_lines.append('=' * 60)
        else:
            formatted_lines.append(proper_indent + stripped_line)
    
    # Join lines and print
    formatted_output = '\n'.join(formatted_lines)
    
    # Clean up excessive newlines (more than 2 consecutive)
    formatted_output = re.sub(r'\n{3,}', '\n\n', formatted_output)
    
    print(formatted_output)