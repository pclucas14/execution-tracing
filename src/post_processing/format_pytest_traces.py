import json 
import random
import sys
import os
import numpy as np
import re
from collections import defaultdict


from post_processing.utils import build_runtime_trace, to_sequence, is_distinct_paths, read_jsonl_file, StepLocation, pp, path_to_where, find_alternate_paths, tab_print, print_stack_traces

import subprocess
import os

def to_jsonl(data, output_path):
    """
    Save data to a JSONL file.
    """
    with open(output_path, 'w') as f:
        for entry in data:
            f.write(json.dumps(entry) + '\n')

def to_json(data, output_path):
    """
    Save data to a JSON file.
    """
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

def apply_escaped_patch(patch_string: str, root_dir: str):
    """
    Decodes a Python-style escaped patch string and applies it using `git apply`
    from the specified root directory.

    Args:
        patch_string (str): The patch as a string with escaped newlines (e.g., '\\n').
        root_dir (str): The directory where `git apply` should be executed.
    """
    try:

        # save the string to file
        patch_file_path = os.path.join(root_dir, 'temp_patch.patch')
        with open(patch_file_path, 'w') as patch_file:
            patch_file.write(patch_string)

        # Apply the patch from within root_dir
        subprocess.run(
            ["git", "apply", patch_file_path],
            text=True,
            check=True,
            cwd=root_dir  # Change directory before running the command
        )
        print("Patch applied successfully.")
    except subprocess.CalledProcessError as e:
        print("Failed to apply patch:", e)
    except Exception as e:
        print("Error:", e)

def git_clone(repo_url, base_commit, target_dir):
    """
    Clone a git repository at a specific commit.
    """
    import subprocess
    import os
    cwd = os.getcwd()

    if not os.path.exists(target_dir):
        print(f"Target directory {target_dir} does not exist. Cloning repository.")

        if not repo_url.startswith('git@') and not repo_url.startswith('https://'):
            repo_url = f"https://github.com/{repo_url}.git"

        # Clone the repository
        subprocess.run(['git', 'clone', repo_url, target_dir], check=True)

    # Change to the target directory
    os.chdir(target_dir)

    # Checkout the specific commit
    subprocess.run(['git', 'checkout',  '--force', base_commit], check=True)

    os.chdir(cwd)


def get_files_from_patch(patch_text):
    lines = patch_text.splitlines()
    modified_lines_by_file = defaultdict(list)

    current_file = None
    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect file name from diff -- only care about the new file
        if line.startswith('+++ '):
            path = line[4:].strip()
            if path != '/dev/null':
                # Remove a/ or b/ prefix if present
                current_file = re.sub(r'^[ab]/', '', path)

        # Detect diff hunk
        hunk_match = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', line)
        if hunk_match and current_file:
            new_start = int(hunk_match.group(1))
            i += 1
            curr_line = new_start
            while i < len(lines) and not lines[i].startswith('@@') and not lines[i].startswith('diff '):
                patch_line = lines[i]
                if patch_line.startswith('+') and not patch_line.startswith('+++'):
                    modified_lines_by_file[current_file].append(curr_line)
                    curr_line += 1
                elif patch_line.startswith('-') and not patch_line.startswith('---'):
                    # deletion: doesn't increment new file line number
                    pass
                else:
                    # context line
                    curr_line += 1
                i += 1
        else:
            i += 1

    return dict(modified_lines_by_file)

def set_executed_lines(trace):
    trace_data, metadata = trace['trace_data'], trace['metadata']
    trace['metadata']['executed_lines'] = defaultdict(set)
    for entry in trace_data:
        if entry.get('event', '') == 'executed_line':
            file_path = entry['file']
            for line in entry['lines']:
                trace['metadata']['executed_lines'][file_path].add(line)
    
    # Convert sets to sorted lists for consistency
    for file_path in trace['metadata']['executed_lines']:
        trace['metadata']['executed_lines'][file_path] = sorted(list(trace['metadata']['executed_lines'][file_path]))

if __name__ == '__main__':
    # argparse, with arg --trace_files, array of string paths to files
    import argparse
    parser = argparse.ArgumentParser(description='Process some trace files.')
    parser.add_argument('--trace_file', required=True, help='List of trace files to process')
    parser.add_argument('--min_path_amt', type=int, default=4, help='Number of total paths to minimally have for where entry')
    parser.add_argument('--max_siblings', type=int, default=100, help='Maximum number of leaf nodes per parent node')
    parser.add_argument('--leafs_only', action='store_true', help='If set, only leaf nodes will be considered')
    parser.add_argument('--output_path', type=str, default='where_entries_pytest.json', help='Path to save the HuggingFace-friendly dataset')
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

    all_traces = read_jsonl_file(args.trace_file)  # Assuming the first file contains the relevant data

    all_where_entries = []
    where_entries_per_test = {} 

    for stuff in all_traces:
        swe_info, traces = stuff

        patched_files = get_files_from_patch(swe_info['patch'])

        # for (test_name, trace) in traces:
        for (test_name, trace, trace_out) in traces:
            set_executed_lines(trace)
            
            # for (test_name, trace, trace_out, diff) in traces:
            trace_data, metadata = trace['trace_data'], trace['metadata']
            metadata['executed_lines'] = {k.replace('/testbed/', ''): v for k, v in metadata['executed_lines'].items()}
        
            print(f'Processing trace for test: {test_name} in repo: {swe_info["repo"]})')

            test_file = test_name.split('::')[0]

            #if not any([test_file in step['location'] and step['call_type'] == 'function_call' for step in trace_data]):
            #    print(f'Skipping trace for test: {test_name} in repo: {swe_info["repo"]} because it has no function calls in the trace data.')
            #    continue

            where_entries_per_test[test_name] = 0

            # Clear the registry of StepLocation to avoid memory issues
            StepLocation._registry.clear()

            # Build the runtime trace from the raw trace data
            start_node = build_runtime_trace(trace_data)
            print(f'Total number of StepLocation entries {len(StepLocation._registry)}')
            print(f'Processing trace for test: {test_name} in repo: {swe_info["repo"]})')

            runtime_traces = start_node.runtime_trace
            print_stack_traces(runtime_traces, patched_files=patched_files)
            breakpoint()


            touched_files = defaultdict(set)
            for entry in runtime_traces:
                parts = entry.location.split(':')
                file_name = parts[0]
                line = parts[1] if len(parts) > 1 else '0'  # Default to line 0 if not specified
                touched_files[file_name].add(int(line))
                
            # check if patched_files and touched_files overlap
            if any([file in patched_files for file in touched_files.keys()]):
                print(f'Found patched files in touched files for test: {test_name} in repo: {swe_info["repo"]}')
            else:
                print(f'No patched files found in touched files for test: {test_name} in repo: {swe_info["repo"]}')
                if len(patched_files) > 0:
                    breakpoint()
                continue
            
            depths = np.bincount([node.depth for node in runtime_traces])
            print(depths)

            # First, we filter out nodes with insufficient alternate paths from root to said node
            # filtered_nodes = [node for node in runtime_traces if len(find_paths(start_node, node)) >= args.min_path_amt]

            # Once we have the runtime traces, let's filter out to select only :
            # 1) the first calls to a given StepLocation
            # 2) the last calls to a given StepLocation 

            #filtered_nodes = runtime_traces
            filtered_nodes = [node for node in runtime_traces if node.call_type == 'function_call']
            # filtered_nodes = [node for node in filtered_nodes if node.is_first_call or node.is_last_call]
            filtered_nodes = [node for node in filtered_nodes if not node.is_external]  # Exclude external calls
            
            print(f'Found {len(filtered_nodes)} nodes after filtering for first and last calls') 
            
            # Filter by the 'patch' instead (done later)
            # filtered_nodes = [x for x in filtered_nodes if any([test_file in y.location for y in x.stack_trace])]
            # print(f'Found {len(filtered_nodes)} nodes after filtering for test file {test_file}.')

            # 3) are leaf nodes 
            # 4) potentially restrict the amount of sibling nodes
            if args.leafs_only:
                filtered_nodes = [node for node in filtered_nodes if node.is_leaf_node]

            print(f'Found {len(filtered_nodes)} nodes after filtering for leaf nodes and max siblings ({args.max_siblings}).')
            # Finally, build the where entries
            where_entries = []

            for node in filtered_nodes:
                # Get the stack trace for this node
                stack_trace = node.stack_trace

                assert stack_trace[-1] == node
                assert path_to_where(stack_trace) == node.where

                # make sure that at least one file in node.where is in the patched files
                found = False
                for anode in node.stack_trace:
                    for file_and_line in anode.executed_lines:
                        file, line = file_and_line.split(':')
                        if int(line) in patched_files.get(file, []):
                            found = True
                            break
                    if found:
                        break

                if not found:
                    print(f'NOTE : node not close to the patched files.')
                    continue

                paths = find_alternate_paths(stack_trace, max_paths=50)

                # Some different alternate paths might give the same "where" location, so we filter them out
                alternate_paths = [path for path in paths if path_to_where(path) != path_to_where(stack_trace)]

                # Some different alternate paths might give the same "where" location as other alternate paths, so we filter them out
                alternate_paths = [path for i, path in enumerate(alternate_paths) if path_to_where(path) not in [path_to_where(ap) for ap in alternate_paths[:i]]]

                if len(alternate_paths) < args.min_path_amt:
                    print(f'Node {node} has only {len(alternate_paths)} paths, skipping it.')
                    continue
                else:
                    pp(stack_trace)
                    print('\n\n\n')

                for ap in alternate_paths:
                    assert stack_trace[-1].step_location == ap[-1].step_location, breakpoint() # 
                    f"Last node in alternate path {ap[-1]} should be the same as the last node in the stack trace {stack_trace[-1]}."
                    if stack_trace[0].step_location != ap[0].step_location:
                        # repo_url = os.path.join(os.environ['HOME'], swe_info['repo'].split('/')[-1])
                        # git_clone(swe_info['repo'], swe_info['base_commit'], repo_url)
                        # apply_escaped_patch(swe_info['patch'], repo_url)
                        # apply_escaped_patch(swe_info['test_patch'], repo_url)
                        # breakpoint() #
                        msg = f"First node in alternate path {ap[0]} should be the same as the first node in the stack trace {stack_trace[0]}."
                        print(msg)

                # seq_alternate_paths = [to_sequence(path) for path in alternate_paths]
                # assert is_distinct_paths(seq_alternate_paths), breakpoint() #"There are non-distinct paths in the alternate paths."

                where_alternate_paths = [path_to_where(path) for path in alternate_paths]
                assert is_distinct_paths(where_alternate_paths), breakpoint()# "There are non-distinct paths in the alternate paths (after path_to_where)."

                #if '_array_api.py' in node.location:
                #    breakpoint()
                print('---')
                for i, ap in enumerate(alternate_paths):
                    if path_to_where(ap) == path_to_where(stack_trace):
                        breakpoint()
                    if path_to_where(ap) == node.where:
                        breakpoint()
                        print(f'Node {node} has an alternate path that is the same as the stack trace: {path_to_where(ap)}')
                        continue
                    if any([path_to_where(ap) == path_to_where(app) for app in alternate_paths[i+1:]]):
                        breakpoint()
                        print(path_to_where(ap))
                        print()
                print('---')

                for path in alternate_paths: 
                    if any(['contextlib' in loc for loc in path_to_where(path)]):
                        repo_url = os.path.join(os.environ['HOME'], swe_info['repo'].split('/')[-1])
                        git_clone(swe_info['repo'], swe_info['base_commit'], repo_url)
                        apply_escaped_patch(swe_info['patch'], repo_url)
                        apply_escaped_patch(swe_info['test_patch'], repo_url)
                        breakpoint()
                        print(f'Skipping node {node} because it has contextlib in the alternate paths.')
                        continue

                for i, path in enumerate(alternate_paths):
                    for j, opath in enumerate(alternate_paths[i+1:]):
                        if path_to_where(path) == path_to_where(opath):
                            print(f'Found duplicate alternate paths: {path_to_where(path)} and {path_to_where(opath)}')
                            breakpoint()
                            continue

                where_entry = {
                    'stack_trace': node.where, #[node.to_dict() for node in stack_trace],
                    'alternate_paths': [path_to_where(path) for path in alternate_paths],     # [[node.to_dict() for node in path] for path in alternate_paths],
                    'metadata': metadata,
                    'repo': swe_info['repo'],
                    'instance_id': swe_info['instance_id'],
                    'base_commit': swe_info['base_commit'],
                    'patch' : swe_info['patch'],
                    'test_patch': swe_info['test_patch'],
                    'test_name': test_name,
                    'is_first': node.is_first_call,
                    'is_last': node.is_last_call,
                    'og_stack_trace': to_sequence(node.stack_trace),
                    'og_alternate_paths': [to_sequence(path) for path in alternate_paths],
                    'executed_lines': metadata['executed_lines'],
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