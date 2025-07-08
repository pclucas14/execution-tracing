import json 
import random
import sys
import os
import numpy as np

from post_processing.utils import build_runtime_trace, find_paths, to_sequence, is_distinct_paths, WhereEntry, read_jsonl_file, StepLocation, pp, read_json_file, path_to_where, find_all_paths_to_node

if __name__ == '__main__':
    # argparse, with arg --trace_files, array of string paths to files
    import argparse
    parser = argparse.ArgumentParser(description='Process some trace files.')
    parser.add_argument('--trace_file', required=True, help='List of trace files to process')
    parser.add_argument('--min_path_amt', type=int, default=4, help='Number of total paths to minimally have for where entry')
    parser.add_argument('--max_siblings', type=int, default=100, help='Maximum number of leaf nodes per parent node')
    parser.add_argument('--leafs_only', action='store_true', help='If set, only leaf nodes will be considered')
    parser.add_argument('--output_path', type=str, default='where_entries_pytest.json', help='Path to save the HuggingFace-friendly dataset')
    parser.add_argument('--repo', type=str, required=True, help='Repository name for the traces')
    args = parser.parse_args()

    """
    Format of the JSONL file:
    list[
        tuple[
            str (image_name),
            list (traces) [
                tuple[
                    str (test_name),
                    dict (trace),
                ]
            ]
        ]    
    ]
    """


    if args.trace_file.endswith('.json'):
        # If the trace file is a JSON file, read it as a single JSON object
        swe_info = {'repo': args.repo, 'instance_id': None, 'base_commit': None}
        test_name = 'single_trace'
        all_traces = [(swe_info, [(test_name, read_json_file(args.trace_file))])]
    else:
        all_traces = read_jsonl_file(args.trace_file)  # Assuming the first file contains the relevant data

    STUFF = {
        'start_node' : [],
        'swe_info' : [],
        'processed_trace' : [],
        'test_name': [],
        'metadata': []
    }
    all_where_entries = []
    where_entries_per_test = {}

    for stuff in all_traces:
        swe_info, traces = stuff

        for (test_name, trace) in traces:
            trace_data, metadata = trace['trace_data'], trace['metadata']
        
            print(f'Processing trace for test: {test_name} in repo: {swe_info["repo"]})')
            
            # Build the runtime trace from the raw trace data
            start_node = build_runtime_trace(trace_data)
            STUFF['start_node'].append(start_node)
            STUFF['swe_info'].append(swe_info)
            STUFF['processed_trace'].append(trace)
            STUFF['test_name'].append(test_name)
            STUFF['metadata'].append(metadata)

            print(f'Total number of StepLocation entries {len(StepLocation._registry)}')

    for i in range(len(STUFF['start_node'])):

        start_node = STUFF['start_node'][i]
        trace = STUFF['processed_trace'][i]
        swe_info = STUFF['swe_info'][i]
        test_name = STUFF['test_name'][i]
        metadata = STUFF['metadata'][i]

        print(f'Processing trace for test: {test_name} in repo: {swe_info["repo"]})')

        where_entries_per_test[test_name] = 0
        
        runtime_traces = start_node.runtime_trace
        depths = np.bincount([node.depth for node in runtime_traces])
        print(depths)

        # First, we filter out nodes with insufficient alternate paths from root to said node
        # filtered_nodes = [node for node in runtime_traces if len(find_paths(start_node, node)) >= args.min_path_amt]

        # Once we have the runtime traces, let's filter out to select only :
        # 1) the first calls to a given StepLocation
        # 2) the last calls to a given StepLocation 

        filtered_nodes = [node for node in runtime_traces if node.is_first_call or node.is_last_call]
        filtered_nodes = [node for node in filtered_nodes if not node.is_external]  # Exclude external calls
        # n_paths = [len(find_paths(start_node, node)) for node in filtered_nodes]
        paths = find_all_paths_to_node(filtered_nodes[5])
        for path in paths:
            print(path_to_where(path))
            print('---')
        print('\n\n')
        print(path_to_where(filtered_nodes[5].stack_trace))
        print('---')
        n_paths = [len(find_all_paths_to_node(node)) for node in filtered_nodes]
        breakpoint()
        # filtered_nodes = [node for node in filtered_nodes if len(find_all_paths_to_node(node.upest_node, node)) >= args.min_path_amt]
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
            where_trace = node.where

            assert stack_trace[-1] == node

            # paths = find_all_paths_to_node(stack_trace[0], stack_trace[-1]) #start_node, node)
            paths = find_all_paths_to_node(stack_trace[-1]) #start_node, node)
            alternate_paths = [path for path in paths if to_sequence(path) != to_sequence(stack_trace)]
            if len(paths) < args.min_path_amt:
                print(f'Node {node} has only {len(paths)} paths, skipping it.')
                continue
            else:
                pp(stack_trace)
                print('\n\n\n')
            assert len(alternate_paths) + 1 == len(paths) or len(stack_trace) > len(set(to_sequence(stack_trace))), "stack trace either exists in path, or contains a cycle"

            """
            start_node = STUFF['start_node'][i]
            trace = STUFF['processed_trace'][i]
            swe_info = STUFF['swe_info'][i]
            test_name = STUFF['test_name'][i]
            metadata = STUFF['metadata'][i] 
            """

            assert is_distinct_paths(alternate_paths), "There are non-distinct paths in the alternate paths."

            def to_where_format(path):
                # instead of each entry having a location to the start of the function, we want the line where the function is called
                pass
                
            ap = alternate_paths[0]
            breakpoint()
            where_entry = {
                'stack_trace': node.where, #[node.to_dict() for node in stack_trace],
                'alternate_paths': [[node.to_dict() for node in path] for path in alternate_paths],
                'metadata': metadata,
                'repo': swe_info['repo'],
                'instance_id': swe_info['instance_id'],
                'base_commit': swe_info['base_commit'],
                'test_name': test_name,
                'is_first': node.is_first_call,
                'is_last': node.is_last_call,
            }
            where_entries.append(where_entry)
            where_entries_per_test[test_name] += 1

        # Add where entries from this trace file to the global collection
        all_where_entries.extend(where_entries)

        # assert all(is_distinct_paths(entry.alternate_paths) for entry in where_entries), "There are non-distinct paths in the where entries."

        print(f'Added {len(where_entries)} where entries from {args.trace_file}')

    # After processing all trace files, save the dataset in HuggingFace-friendly format
    print(f'Total where entries collected: {len(all_where_entries)}')

    # Save the dataset
    output_data = {
        'metadata': {
            'total_entries': len(all_where_entries),
            'min_path_amt': args.min_path_amt,
            'max_siblings': args.max_siblings,
            'leafs_only': args.leafs_only,
            'source_trace_files': args.trace_file,
            'where_entries_per_test': where_entries_per_test,

        },
        'data': all_where_entries
    }

    with open(args.output_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f'Saved {len(all_where_entries)} where entries to {args.output_path}')