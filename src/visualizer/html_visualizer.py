import json
import os
from typing import List, Dict, Any
from .pattern_grouper import group_trace_patterns

def generate_html_visualization(trace_file: str, output_file: str = None, group_patterns: bool = True):
    """Generate an interactive HTML visualization of the trace."""
    
    # Load trace data
    with open(trace_file, 'r') as f:
        raw_data = json.load(f)
    
    # Handle both old format (list) and new format (dict with metadata)
    if isinstance(raw_data, dict) and 'trace_data' in raw_data:
        trace_data = raw_data['trace_data']
        metadata = raw_data.get('metadata', {})
    else:
        # Legacy format - just a list of trace entries
        trace_data = raw_data
        metadata = {}
    
    # Group patterns if requested
    if group_patterns and isinstance(trace_data, list):
        print("Grouping repeating patterns...")
        grouped_data = group_trace_patterns(trace_data, min_pattern_length=2, min_repetitions=2)
        print(f"Grouped {len(trace_data)} calls into {len(grouped_data)} items")
    else:
        grouped_data = trace_data
    
    # Generate summary for original data
    if isinstance(trace_data, list):
        summary_output = _generate_summary_stats(trace_data, metadata)
    else:
        summary_output = "No trace data found"
    
    # Extract unique call types from the data
    call_types_in_data = set()
    for entry in trace_data:
        if 'arguments' not in entry:
            entry['arguments'] = {}
        call_type = entry.get('call_type', 'unknown')
        call_types_in_data.add(call_type)
    
    # Generate filter controls for each call type
    filter_controls = _generate_call_type_filters(call_types_in_data)

    # Generate suggested filename for filtered export
    trace_basename = os.path.basename(trace_file)
    trace_name, trace_ext = os.path.splitext(trace_basename)
    import random
    random_suffix = f"_{random.randint(1000, 9999)}"
    suggested_filename = f"{trace_name}_filtered{random_suffix}{trace_ext}"
    
    # Get the directory of the original trace file for server-side saving
    trace_directory = os.path.dirname(os.path.abspath(trace_file))

    # Create HTML content
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Python Execution Trace Visualization</title>
    <style>
        body {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            margin: 20px;
            background-color: #1e1e1e;
            color: #d4d4d4;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .summary {{
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            white-space: pre-wrap;
            color: #000;
        }}
        .metadata-info {{
            color: #000;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stats-section {{
            color: #333;
            margin-top: 10px;
        }}
        .trace-tree {{
            background-color: #f8f8f8;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 14px;
            line-height: 1.6;
        }}
        .pattern-group {{
            border: 2px solid #007acc;
            border-radius: 8px;
            margin: 10px 0;
            padding: 10px;
            background-color: #f0f8ff;
        }}
        .pattern-header {{
            background-color: #007acc;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 12px;
            cursor: pointer;
        }}
        .pattern-toggle {{
            float: right;
            padding: 2px 6px;
            background: rgba(255,255,255,0.2);
            border-radius: 3px;
        }}
        .pattern-content {{
            margin-left: 10px;
        }}
        .pattern-content.collapsed {{
            display: none;
        }}
        .call-entry {{
            margin: 2px 0;
            padding: 3px 5px;
            font-family: 'Courier New', monospace;
            cursor: pointer;
            border-radius: 3px;
            transition: background-color 0.2s;
            color: #222;
        }}
        .call-entry:hover {{
            background-color: #e8f4f8;
        }}
        .call-entry.expanded {{
            background-color: #d4edda;
        }}
        .args-container {{
            display: none;
            margin-top: 8px;
            padding: 8px 12px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-left: 3px solid #007acc;
        }}
        .args-container.show {{
            display: block;
        }}
        .args-header {{
            font-weight: bold;
            color: #007acc;
            margin-bottom: 4px;
        }}
        .arg-item {{
            margin: 2px 0;
            padding-left: 16px;
        }}
        .arg-name {{
            color: #0066cc;
            font-weight: bold;
        }}
        .arg-value {{
            color: #008000;
        }}
        .arg-type {{
            color: #333;
            font-style: italic;
            font-size: 0.9em;
        }}
        .no-args {{
            color: #333;
            font-style: italic;
        }}
        .external {{
            color: #555;
            background-color: #fff3cd;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        .import-call {{
            color: #444;
            background-color: #f5f5f5;
            font-style: italic;
        }}
        .filter-controls {{
            margin-bottom: 15px;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
        }}
        .filter-controls label {{
            margin-right: 15px;
            margin-bottom: 8px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            font-size: 14px;
        }}
        .filter-controls input[type="checkbox"] {{
            margin-right: 6px;
        }}
        .filter-section {{
            margin-bottom: 10px;
        }}
        .filter-title {{
            font-weight: bold;
            color: #333;
            margin-bottom: 8px;
            font-size: 16px;
        }}
        .call-type-filters {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        .legend-section {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .legend-title {{
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            font-size: 16px;
        }}
        .legend-items {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 8px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            font-size: 14px;
            color: #333;
        }}
        .legend-badge {{
            margin-right: 8px;
        }}
        .legend-description {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        .save-section {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .save-controls {{
            display: flex;
            gap: 10px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .filename-input {{
            flex: 1;
            min-width: 300px;
            padding: 8px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
        }}
        .save-button {{
            background-color: #007acc;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }}
        .save-button:hover {{
            background-color: #005a9f;
        }}
        .save-button:disabled {{
            background-color: #ccc;
            cursor: not-allowed;
        }}
        .save-info {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
        }}
        .server-path {{
            font-size: 11px;
            color: #888;
            font-style: italic;
            margin-top: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Python Execution Trace Visualization</h1>
        
        <div class="summary">
{summary_output}
        </div>
        
        <div class="legend-section">
            <div class="legend-title">📋 Call Type Legend</div>
            <div class="legend-items">
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('function_call')}</span>
                    <span class="legend-description">function_call - Regular function calls within scope</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('method_call')}</span>
                    <span class="legend-description">method_call - Method calls on objects</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('class_method')}</span>
                    <span class="legend-description">class_method - Class method calls</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('class_instantiation')}</span>
                    <span class="legend-description">class_instantiation - Class __init__ methods</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('class_declaration')}</span>
                    <span class="legend-description">class_declaration - Class definitions (not instantiations)</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('special_method')}</span>
                    <span class="legend-description">special_method - Dunder methods (__str__, __repr__, etc.)</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('callable_object')}</span>
                    <span class="legend-description">callable_object - __call__ method invocations</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('lambda_function')}</span>
                    <span class="legend-description">lambda_function - Anonymous lambda functions</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('module_execution')}</span>
                    <span class="legend-description">module_execution - Module-level code execution</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('import')}</span>
                    <span class="legend-description">import - Module import operations</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('external_call')}</span>
                    <span class="legend-description">external_call - Calls to external libraries/modules</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('comprehension')}</span>
                    <span class="legend-description">comprehension - List/dict/set comprehensions</span>
                </div>
                <div class="legend-item">
                    <span class="legend-badge">{_get_call_type_badge('unknown')}</span>
                    <span class="legend-description">unknown - Unclassified call types</span>
                </div>
            </div>
        </div>
        
        <h2>📋 Call Tree with Pattern Groups (Click any row to view arguments)</h2>
        <div class="filter-controls">
            <div class="filter-section">
                <div class="filter-title">General Filters</div>
                <label>
                    <input type="checkbox" id="showExternal" checked onchange="toggleExternal()">
                    Show external calls
                </label>
                <label>
                    <input type="checkbox" id="expandPatterns" checked onchange="togglePatterns()">
                    Expand pattern groups
                </label>
            </div>
            <div class="filter-section">
                <div class="filter-title">Call Type Filters</div>
                <div class="call-type-filters">
{filter_controls}
                </div>
            </div>
        </div>
        
        <div class="save-section">
            <div class="legend-title">💾 Save Filtered Data</div>
            <div class="save-controls">
                <input type="text" class="filename-input" id="exportFilename" 
                       value="{suggested_filename}" 
                       placeholder="Enter filename for filtered export">
                <button class="save-button" onclick="saveFilteredData()">
                    Save to Server
                </button>
            </div>
            <div class="save-info">
                Export will include only the calls visible with current filter settings.
                Original metadata and structure will be preserved.
            </div>
            <div class="server-path">
                Files will be saved to: {trace_directory}/
            </div>
        </div>
        
        <div class="trace-tree" id="traceTree">
{_format_grouped_calls(grouped_data, trace_data)}
        </div>
    </div>
    
    <script>
        // Store the original trace data for filtering
        const originalTraceData = {json.dumps(trace_data, default=str)};
        const originalMetadata = {json.dumps(metadata, default=str)};
        const serverPath = {json.dumps(trace_directory)};
        
        function formatArgValue(value) {{
            if (value === null) return 'None';
            if (typeof value === 'string') {{
                if (value.length > 50) {{
                    return '"' + value.substring(0, 47) + '..."';
                }}
                return '"' + value + '"';
            }}
            if (typeof value === 'object') {{
                if (Array.isArray(value)) {{
                    if (value.length === 0) return '[]';
                    if (value.length > 3) return '[...' + value.length + ' items]';
                    return JSON.stringify(value);
                }}
                try {{
                    const jsonStr = JSON.stringify(value, null, 2);
                    if (jsonStr.length > 100) {{
                        const keys = Object.keys(value || {{}});
                        return '{{' + keys.length + ' keys}}';
                    }}
                    return jsonStr;
                }} catch (e) {{
                    return String(value);
                }}
            }}
            return String(value);
        }}
        
        function getArgType(value) {{
            if (value === null) return 'NoneType';
            if (Array.isArray(value)) return 'list';
            if (typeof value === 'object') return 'dict';
            if (typeof value === 'string') return 'str';
            if (typeof value === 'number') return Number.isInteger(value) ? 'int' : 'float';
            if (typeof value === 'boolean') return 'bool';
            return typeof value;
        }}
        
        function toggleCallArgs(callId) {{
            const argsDiv = document.getElementById('args_' + callId);
            const callDiv = argsDiv.previousElementSibling;
            
            if (argsDiv.style.display === 'none' || argsDiv.style.display === '') {{
                argsDiv.style.display = 'block';
                callDiv.classList.add('expanded');
            }} else {{
                argsDiv.style.display = 'none';
                callDiv.classList.remove('expanded');
            }}
        }}
        
        function toggleExternal() {{
            const showExternal = document.getElementById('showExternal').checked;
            const externalElements = document.querySelectorAll('.external');
            externalElements.forEach(el => {{
                const argsDiv = el.nextElementSibling;
                if (showExternal) {{
                    el.style.display = 'block';
                    if (argsDiv && argsDiv.classList.contains('args-container')) {{
                        argsDiv.style.display = el.classList.contains('expanded') ? 'block' : 'none';
                    }}
                }} else {{
                    el.style.display = 'none';
                    if (argsDiv && argsDiv.classList.contains('args-container')) {{
                        argsDiv.style.display = 'none';
                    }}
                }}
            }});
        }}
        
        function toggleCallType(callType) {{
            const checkbox = document.getElementById('show' + callType.replace(/_/g, '').replace(/-/g, ''));
            const showCallType = checkbox.checked;
            const elements = document.querySelectorAll('[data-call-type="' + callType + '"]');
            
            elements.forEach(el => {{
                const argsDiv = el.nextElementSibling;
                if (showCallType) {{
                    el.style.display = 'block';
                    if (argsDiv && argsDiv.classList.contains('args-container')) {{
                        argsDiv.style.display = el.classList.contains('expanded') ? 'block' : 'none';
                    }}
                }} else {{
                    el.style.display = 'none';
                    if (argsDiv && argsDiv.classList.contains('args-container')) {{
                        argsDiv.style.display = 'none';
                    }}
                }}
            }});
        }}
        
        function togglePatterns() {{
            const expandPatterns = document.getElementById('expandPatterns').checked;
            const patternContents = document.querySelectorAll('.pattern-content');
            patternContents.forEach(content => {{
                if (expandPatterns) {{
                    content.classList.remove('collapsed');
                }} else {{
                    content.classList.add('collapsed');
                }}
            }});
        }}
        
        function togglePatternGroup(element) {{
            const content = element.parentElement.querySelector('.pattern-content');
            content.classList.toggle('collapsed');
            const toggle = element.querySelector('.pattern-toggle');
            toggle.textContent = content.classList.contains('collapsed') ? '▶' : '▼';
        }}
        
        function getActiveFilters() {{
            const filters = {{
                showExternal: document.getElementById('showExternal')?.checked ?? true,
                callTypes: {{}}
            }};
            
            // Get all call type checkboxes
            const callTypeCheckboxes = document.querySelectorAll('[id^="show"][id$="call"], [id^="show"][id$="method"], [id^="show"][id$="function"], [id^="show"][id$="instantiation"], [id^="show"][id$="execution"], [id^="show"][id$="import"], [id^="show"][id$="lambda"], [id^="show"][id$="object"], [id^="show"][id$="comprehension"], [id^="show"][id$="unknown"]');
            
            callTypeCheckboxes.forEach(checkbox => {{
                const callType = checkbox.getAttribute('onchange')?.match(/toggleCallType\\('([^']+)'\\)/)?.[1];
                if (callType) {{
                    filters.callTypes[callType] = checkbox.checked;
                }}
            }});
            
            return filters;
        }}
        
        function shouldIncludeCall(call, filters) {{
            // Check external filter
            if (call.is_external && !filters.showExternal) {{
                return false;
            }}
            
            // Check call type filter
            const callType = call.call_type || 'unknown';
            if (filters.callTypes[callType] === false) {{
                return false;
            }}
            
            return true;
        }}
        
        function getFilteredTraceData() {{
            const filters = getActiveFilters();
            const filteredData = originalTraceData.filter(call => shouldIncludeCall(call, filters));
            
            return {{
                metadata: {{
                    ...originalMetadata,
                    filtered: true,
                    filter_applied_at: new Date().toISOString(),
                    original_total_calls: originalTraceData.length,
                    filtered_total_calls: filteredData.length,
                    filters_applied: filters
                }},
                trace_data: filteredData
            }};
        }}
        
        function saveFilteredData() {{
            try {{
                const filteredData = getFilteredTraceData();
                const filename = document.getElementById('exportFilename').value.trim();
                
                if (!filename) {{
                    alert('Please enter a filename for the export.');
                    return;
                }}
                
                // Ensure filename has .json extension
                const finalFilename = filename.endsWith('.json') ? filename : filename + '.json';
                
                // Disable button during save
                const button = document.querySelector('.save-button');
                const originalText = button.textContent;
                button.textContent = 'Saving...';
                button.disabled = true;
                
                // Send to server
                fetch('/save_filtered', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{
                        filename: finalFilename,
                        data: filteredData,
                        directory: serverPath
                    }})
                }})
                .then(response => response.json())
                .then(result => {{
                    if (result.success) {{
                        button.textContent = 'Saved!';
                        button.style.backgroundColor = '#28a745';
                        
                        // Update the info to show the saved file path
                        const info = document.querySelector('.save-info');
                        info.innerHTML = `<strong>✓ Saved successfully to:</strong> ${{result.filepath}}<br>Export included ${{filteredData.trace_data.length}} of ${{originalTraceData.length}} calls with current filter settings.`;
                        
                        console.log(`Saved ${{filteredData.trace_data.length}} calls to ${{result.filepath}}`);
                    }} else {{
                        throw new Error(result.error || 'Unknown error occurred');
                    }}
                }})
                .catch(error => {{
                    console.error('Error saving filtered data:', error);
                    alert('Error saving data: ' + error.message);
                    button.textContent = 'Error';
                    button.style.backgroundColor = '#dc3545';
                }})
                .finally(() => {{
                    // Reset button after 3 seconds
                    setTimeout(() => {{
                        button.textContent = originalText;
                        button.style.backgroundColor = '#007acc';
                        button.disabled = false;
                    }}, 3000);
                }});
                
            }} catch (error) {{
                console.error('Error preparing filtered data:', error);
                alert('Error preparing data: ' + error.message);
            }}
        }}
        
        // Update export info when filters change
        function updateExportInfo() {{
            const filteredData = getFilteredTraceData();
            const info = document.querySelector('.save-info');
            if (info && !info.innerHTML.includes('Saved successfully')) {{
                info.textContent = `Export will include ${{filteredData.trace_data.length}} of ${{originalTraceData.length}} calls with current filter settings.`;
            }}
        }}
        
        // Override existing filter functions to update export info
        const originalToggleExternal = toggleExternal;
        toggleExternal = function() {{
            originalToggleExternal();
            updateExportInfo();
        }};
        
        const originalToggleCallType = toggleCallType;
        toggleCallType = function(callType) {{
            originalToggleCallType(callType);
            updateExportInfo();
        }};
        
        // Initialize export info
        document.addEventListener('DOMContentLoaded', function() {{
            updateExportInfo();
        }});
    </script>
</body>
</html>
"""
    
    # Write HTML file
    if output_file:
        with open(output_file, 'w') as f:
            f.write(html_content)
        print(f"HTML visualization written to: {output_file}")
    else:
        return html_content

def _generate_summary_stats(trace_data: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> str:
    """Generate summary statistics for trace data."""
    if not trace_data:
        return "No trace data found"
    
    total_calls = len(trace_data)
    external_calls = sum(1 for call in trace_data if call.get('is_external', False))
    internal_calls = total_calls - external_calls
    
    # Count import vs non-import calls using the same logic as the filter
    import_calls = sum(1 for call in trace_data if _is_import_call(call))
    non_import_calls = total_calls - import_calls
    
    unique_functions = len(set(call.get('name', 'unknown') for call in trace_data))
    unique_locations = len(set(call.get('location', 'unknown') for call in trace_data))
    
    # Count call types
    call_type_counts = {}
    for call in trace_data:
        call_type = call.get('call_type', 'unknown')
        call_type_counts[call_type] = call_type_counts.get(call_type, 0) + 1
    
    # Sort call types by count (descending) for better display
    sorted_call_types = sorted(call_type_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Build summary with metadata if available
    summary_parts = []
    
    if metadata:
        summary_parts.append('<div class="metadata-info">')
        if metadata.get('original_command'):
            summary_parts.append(f'💻 Original Command: <code style="background: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: \'Courier New\', monospace;">{metadata["original_command"]}</code>')
        if metadata.get('scope_path'):
            summary_parts.append(f'📁 Scope Path: <code style="background: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: \'Courier New\', monospace;">{metadata["scope_path"]}</code>')
        if metadata.get('main_file'):
            summary_parts.append(f'📄 Main File: <code style="background: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: \'Courier New\', monospace;">{metadata["main_file"]}</code>')
        if metadata.get('timestamp'):
            summary_parts.append(f'🕐 Timestamp: <code style="background: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: \'Courier New\', monospace;">{metadata["timestamp"]}</code>')
        summary_parts.append('</div>')
        summary_parts.append('<div style="border-top: 2px solid #333; margin: 10px 0;"></div>')
    
    summary_parts.append('<div class="stats-section">')
    
    # Build call type breakdown
    call_type_breakdown = []
    for call_type, count in sorted_call_types:
        badge = _get_call_type_badge(call_type).replace('<span', '<span style="display: inline-block;"')
        percentage = (count / total_calls) * 100
        call_type_breakdown.append(f'{badge} {call_type}: {count:,} ({percentage:.1f}%)')
    
    call_type_section = '\n'.join(call_type_breakdown)
    
    summary_parts.append(f"""📊 Trace Statistics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total function calls: {total_calls:,}
Internal calls: {internal_calls:,}
External calls: {external_calls:,}
Import calls: {import_calls:,}
Non-import calls: {non_import_calls:,}
Unique functions: {unique_functions:,}
Unique locations: {unique_locations:,}

📋 Call Type Breakdown:
{call_type_section}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━""")
    summary_parts.append('</div>')
    
    return '\n'.join(summary_parts)

def _generate_call_type_filters(call_types_in_data: set) -> str:
    """Generate HTML for call type filter checkboxes."""
    # Sort call types for consistent display
    sorted_call_types = sorted(call_types_in_data)
    
    filter_html = []
    for call_type in sorted_call_types:
        # Get the badge for visual consistency
        badge = _get_call_type_badge(call_type)
        # Create a safe ID that matches what JavaScript expects
        safe_id = call_type.replace('_', '').replace('-', '').replace(' ', '')
        
        filter_html.append(f'''                    <label>
                        <input type="checkbox" id="show{safe_id}" checked onchange="toggleCallType('{call_type}')">
                        {badge} {call_type.replace('_', ' ').title()}
                    </label>''')
    
    return '\n'.join(filter_html)

def _format_grouped_calls(grouped_data: List[Dict[str, Any]], original_trace_data: List[Dict[str, Any]], depth: int = 0) -> str:
    """Format grouped calls as HTML with clickable entries."""
    html_parts = []
    
    for i, item in enumerate(grouped_data):
        if item.get('type') == 'pattern_group':
            pattern_html = _format_pattern_group(item, original_trace_data, depth)
            html_parts.append(pattern_html)
        else:
            call_html = _format_single_call(item, original_trace_data, i, depth)
            html_parts.append(call_html)
    
    return '\n'.join(html_parts)

def _format_pattern_group(pattern_group: Dict[str, Any], original_trace_data: List[Dict[str, Any]], depth: int) -> str:
    """Format a pattern group as HTML."""
    repetitions = pattern_group.get('repetitions', 1)
    pattern_length = pattern_group.get('pattern_length', 1)
    total_calls = pattern_group.get('total_calls', 0)
    start_index = pattern_group.get('start_index', 0)
    end_index = pattern_group.get('end_index', 0)
    
    pattern_calls = pattern_group.get('pattern_calls', [])
    
    # Get depth range for the pattern
    depths = [call.get('depth', 0) for call in pattern_calls if 'depth' in call]
    depth_info = ""
    if depths:
        min_depth = min(depths)
        max_depth = max(depths)
        if min_depth == max_depth:
            depth_info = f" (depth: {min_depth})"
        else:
            depth_info = f" (depths: {min_depth}-{max_depth})"
    
    content_html = _format_grouped_calls(pattern_calls, original_trace_data, depth + 1)
    
    return f"""
<div class="pattern-group">
    <div class="pattern-header" onclick="togglePatternGroup(this)">
        <span class="pattern-toggle">▼</span>
        🔄 Repeating Pattern: {repetitions}x repetitions of {pattern_length} calls{depth_info}
        (calls #{start_index + 1}-#{end_index + 1}, total: {total_calls} calls)
    </div>
    <div class="pattern-content">
        <div style="margin-bottom: 8px; font-size: 11px; color: #666;">
            📋 Pattern template (repeated {repetitions} times):
        </div>
        {content_html}
    </div>
</div>"""

def _is_import_call(call: Dict[str, Any]) -> bool:
    """Check if a call is related to module importing."""
    name = call.get('name', '')
    location = call.get('location', '')
    parent_location = call.get('parent_location', '')
    
    # Check for common import patterns
    return (
        '<frozen importlib._bootstrap>' in parent_location or
        '<frozen importlib._bootstrap>' in location or
        name == '<module>' or
        'importlib' in location
    )

def _format_single_call(call: Dict[str, Any], original_trace_data: List[Dict[str, Any]], index: int, depth: int) -> str:
    """Format a single call as HTML with clickable arguments."""
    name = call.get('name', 'unknown')
    location = call.get('location', 'unknown')
    parent_location = call.get('parent_location', '')
    parent_call = call.get('parent_call', '')
    is_external = call.get('is_external', False)
    is_import = _is_import_call(call)
    call_depth = call.get('depth', 0)
    call_type = call.get('call_type', 'unknown')
    
    # Find the original trace entry to get full argument data
    original_entry = None
    call_name = call.get('name', '')
    call_location = call.get('location', '')
    for entry in original_trace_data:
        if (entry.get('name') == call_name and 
            entry.get('location') == call_location):
            original_entry = entry
            break
    
    arguments = original_entry.get('arguments', {}) if original_entry else {}
    
    css_classes = "call-entry"
    if is_external:
        css_classes += " external"
    if is_import:
        css_classes += " import-call"
    
    indent = "  " * depth
    call_id = f"call_{index}_{hash(str(call))}"
    args_display = ""
    if arguments:
        args_count = len(arguments)
        args_display = f" ({args_count} args)"
    
    # Add parent call info if available
    parent_call_display = ""
    if parent_call:
        parent_call_display = f' <span style="color: #888; font-style: italic;">← {parent_call}</span>'
    
    # Add call type badge with appropriate styling
    call_type_badge = _get_call_type_badge(call_type)
    
    depth_badge = f'<span style="background: #007acc; color: white; padding: 1px 4px; border-radius: 3px; font-size: 0.85em; margin-right: 4px;">d:{call_depth}</span>'
    args_html = _format_arguments_html(arguments, parent_location, parent_call)
    
    return f"""<div class="{css_classes}" data-call-type="{call_type}" onclick="toggleCallArgs('{call_id}')">
{indent}{depth_badge}{call_type_badge}[#{index + 1}] <strong>{name}</strong>{args_display} <span style="color: #666;">[{location}]</span>{parent_call_display}
</div>
<div id="args_{call_id}" class="args-container" style="display: none;">
    {args_html}
</div>"""

def _format_arguments_html(arguments: Dict[str, Any], parent_location: str = "", parent_call: str = "") -> str:
    """Format function arguments as HTML for display."""
    if not arguments:
        return '<div class="no-args">No arguments</div>'
    
    html_parts = ['<div class="args-header">Arguments:</div>']
    
    for arg_name, arg_value in arguments.items():
        # Skip error entries
        if arg_name == "error":
            html_parts.append(f'<div class="arg-item"><span class="arg-name">Error:</span> <span class="arg-value">{arg_value}</span></div>')
            continue
            
        # Format the argument value for display
        formatted_value = _format_arg_value_for_html(arg_value)
        arg_type = _get_arg_type_for_html(arg_value)
        
        html_parts.append(f'''
        <div class="arg-item">
            <span class="arg-name">{arg_name}:</span> 
            <span class="arg-value">{formatted_value}</span>
            <span class="arg-type">({arg_type})</span>
        </div>''')
    
    # Add parent call information if available
    if parent_call and parent_call.strip():
        html_parts.append(f'<div style="margin-top: 10px; padding-top: 8px; border-top: 1px solid #ddd; font-size: 0.9em; color: #666;">Called from: <code>{parent_call}</code></div>')
    
    return ''.join(html_parts)

def _format_arg_value_for_html(value) -> str:
    """Format an argument value for HTML display."""
    if value is None:
        return '<em>None</em>'
    
    if isinstance(value, str):
        # Escape HTML characters and handle long strings
        escaped = value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        if len(escaped) > 100:
            return f'<span title="{escaped}">{escaped[:97]}...</span>'
        return f'"{escaped}"'
    
    if isinstance(value, (int, float, bool)):
        return str(value)
    
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return '[]' if isinstance(value, list) else '()'
        elif len(value) > 5:
            return f'{type(value).__name__} with {len(value)} items'
        else:
            items = [_format_arg_value_for_html(item) for item in value[:3]]
            if len(value) > 3:
                items.append('...')
            bracket_open = '[' if isinstance(value, list) else '('
            bracket_close = ']' if isinstance(value, list) else ')'
            return f'{bracket_open}{", ".join(items)}{bracket_close}'
    
    if isinstance(value, dict):
        if len(value) == 0:
            return '{}'
        elif len(value) > 3:
            return f'dict with {len(value)} keys'
        else:
            items = []
            for k, v in list(value.items())[:3]:
                key_str = _format_arg_value_for_html(k)
                val_str = _format_arg_value_for_html(v)
                items.append(f'{key_str}: {val_str}')
            if len(value) > 3:
                items.append('...')
            return '{' + ', '.join(items) + '}'
    
    # For other objects, show type and try to get a useful representation
    try:
        str_repr = str(value)
        if len(str_repr) > 50:
            return f'&lt;{type(value).__name__} object&gt;'
        else:
            escaped = str_repr.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return f'&lt;{escaped}&gt;'
    except Exception:
        return f'&lt;{type(value).__name__} object&gt;'

def _get_arg_type_for_html(value) -> str:
    """Get the type name for an argument value."""
    if value is None:
        return 'NoneType'
    elif isinstance(value, bool):
        return 'bool'
    elif isinstance(value, int):
        return 'int'
    elif isinstance(value, float):
        return 'float'
    elif isinstance(value, str):
        return 'str'
    elif isinstance(value, list):
        return 'list'
    elif isinstance(value, tuple):
        return 'tuple'
    elif isinstance(value, dict):
        return 'dict'
    elif isinstance(value, set):
        return 'set'
    else:
        return type(value).__name__

def _get_call_type_badge(call_type: str) -> str:
    """Generate a styled badge for the call type."""
    type_colors = {
        'function_call': '#28a745',      # Green
        'method_call': '#17a2b8',        # Cyan
        'class_method': '#6f42c1',       # Purple
        'class_instantiation': '#fd7e14', # Orange
        'class_declaration': '#e83e8c',  # Pink
        'special_method': '#6c757d',     # Gray
        'callable_object': '#20c997',    # Teal
        'lambda_function': '#e83e8c',    # Pink
        'module_execution': '#ffc107',   # Yellow
        'import': '#dc3545',             # Red
        'external_call': '#868e96',      # Light gray
        'comprehension': '#495057',      # Dark gray
        'unknown': '#6c757d'             # Gray
    }
    
    type_symbols = {
        'function_call': '🔧',
        'method_call': '⚙️',
        'class_method': '🏗️',
        'class_instantiation': '🏭',
        'class_declaration': '🎨',
        'special_method': '✨',
        'callable_object': '📞',
        'lambda_function': 'λ',
        'module_execution': '📦',
        'import': '📥',
        'external_call': '🔗',
        'comprehension': '🔄',
        'unknown': '❓'
    }
    
    color = type_colors.get(call_type, type_colors['unknown'])
    symbol = type_symbols.get(call_type, type_symbols['unknown'])
    
    return f'<span style="background: {color}; color: white; padding: 1px 4px; border-radius: 3px; font-size: 0.8em; margin-right: 4px;" title="{call_type}">{symbol}</span>'