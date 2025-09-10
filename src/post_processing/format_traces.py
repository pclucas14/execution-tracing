import json 
import random
import sys
import os

from post_processing.utils import build_runtime_trace, find_paths, to_sequence, is_distinct_paths, WhereEntry

if __name__ == '__main__':
    # argparse, with arg --trace_files, array of string paths to files
    import argparse
    parser = argparse.ArgumentParser(description='Process some trace files.')
    parser.add_argument('--trace_files', nargs='+', required=True, help='List of trace files to process')
    parser.add_argument('--min_path_amt', type=int, default=4, help='Number of total paths to minimally have for where entry')
    parser.add_argument('--max_siblings', type=int, default=100, help='Maximum number of leaf nodes per parent node')
    parser.add_argument('--leafs_only', action='store_true', help='If set, only leaf nodes will be considered')
    parser.add_argument('--output_path', type=str, default='where_entries_dataset.json', help='Path to save the HuggingFace-friendly dataset')
    args = parser.parse_args()

    start_nodes = []
    all_where_entries = []  # Collect all where entries from all trace files
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

        # Add where entries from this trace file to the global collection
        all_where_entries.extend(where_entries)

        assert all(is_distinct_paths(entry.alternate_paths) for entry in where_entries), "There are non-distinct paths in the where entries."

        print(f'Added {len(where_entries)} where entries from {trace_file}')

    # After processing all trace files, save the dataset in HuggingFace-friendly format
    print(f'Total where entries collected: {len(all_where_entries)}')
    
    # Convert to HuggingFace-friendly format
    hf_dataset = []
    for idx, entry in enumerate(all_where_entries):
        hf_entry = {
            'id': idx,
            'stack_trace': [node.to_dict() for node in entry.stack_trace],
            'alternate_paths': [[node.to_dict() for node in path] for path in entry.alternate_paths],
            'stack_trace_locations': [node.location for node in entry.stack_trace],
            'stack_trace_names': [node.name for node in entry.stack_trace],
            'num_alternate_paths': len(entry.alternate_paths),
            'stack_trace_depth': len(entry.stack_trace)
        }
        hf_dataset.append(hf_entry)
    
    # Save the dataset
    output_data = {
        'metadata': {
            'total_entries': len(all_where_entries),
            'min_path_amt': args.min_path_amt,
            'max_siblings': args.max_siblings,
            'leafs_only': args.leafs_only,
            'source_trace_files': args.trace_files
        },
        'trace_data': hf_dataset
    }
    
    with open(args.output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f'Saved {len(all_where_entries)} where entries to {args.output_path}')

        # Finally, let's save as a dataset we can use Later. 
        # where_traces = [x.to_dict() for x in where_entries.values()]
        # external_packages = find_all_external_packages(runtime_traces)