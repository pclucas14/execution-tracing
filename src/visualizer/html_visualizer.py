import json
import os
from typing import List, Dict, Any
from .trace_visualizer import TraceVisualizer
from .pattern_grouper import group_trace_patterns

def generate_html_visualization(trace_file: str, output_file: str = None, group_patterns: bool = True):
    """Generate an interactive HTML visualization of the trace."""
    
    # Load trace data
    with open(trace_file, 'r') as f:
        trace_data = json.load(f)
    
    # Group patterns if requested
    if group_patterns and isinstance(trace_data, list):
        print("Grouping repeating patterns...")
        grouped_data = group_trace_patterns(trace_data, min_pattern_length=2, min_repetitions=2)
        print(f"Grouped {len(trace_data)} calls into {len(grouped_data)} items")
    else:
        grouped_data = trace_data
    
    # Generate summary for original data
    if isinstance(trace_data, list):
        summary_output = _generate_summary_stats(trace_data)
    else:
        summary_output = "No trace data found"
    
    # Ensure each entry has the required structure for clicking
    for entry in trace_data:
        if 'arguments' not in entry:
            entry['arguments'] = {}
    
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
        .call-entry strong {{
            color: #000;
            font-weight: bold;
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
            padding: 10px;
            border-radius: 5px;
        }}
        .filter-controls label {{
            margin-right: 20px;
            cursor: pointer;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>Python Execution Trace Visualization</h1>
        
        <div class="summary">
{summary_output}
        </div>
        
        <h2>📋 Call Tree with Pattern Groups (Click any row to view arguments)</h2>
        <div class="filter-controls">
            <label>
                <input type="checkbox" id="showExternal" checked onchange="toggleExternal()">
                Show external calls
            </label>
            <label>
                <input type="checkbox" id="showImports" onchange="toggleImports()">
                Show import calls
            </label>
            <label>
                <input type="checkbox" id="expandPatterns" checked onchange="togglePatterns()">
                Expand pattern groups
            </label>
        </div>
        
        <div class="trace-tree" id="traceTree">
{_format_grouped_calls(grouped_data, trace_data)}
        </div>
    </div>
    
    <script>
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
        
        function toggleImports() {{
            const showImports = document.getElementById('showImports').checked;
            const importElements = document.querySelectorAll('.import-call');
            importElements.forEach(el => {{
                const argsDiv = el.nextElementSibling;
                if (showImports) {{
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
        
        // Initialize - hide imports by default
        document.addEventListener('DOMContentLoaded', function() {{
            toggleImports();
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

def _generate_summary_stats(trace_data: List[Dict[str, Any]]) -> str:
    """Generate summary statistics for trace data."""
    if not trace_data:
        return "No trace data found"
    
    total_calls = len(trace_data)
    external_calls = sum(1 for call in trace_data if call.get('is_external', False))
    internal_calls = total_calls - external_calls
    
    unique_functions = len(set(call.get('name', 'unknown') for call in trace_data))
    unique_locations = len(set(call.get('location', 'unknown') for call in trace_data))
    
    return f"""📊 Trace Statistics:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total function calls: {total_calls:,}
Internal calls: {internal_calls:,}
External calls: {external_calls:,}
Unique functions: {unique_functions:,}
Unique locations: {unique_locations:,}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

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
    content_html = _format_grouped_calls(pattern_calls, original_trace_data, depth + 1)
    
    return f"""
<div class="pattern-group">
    <div class="pattern-header" onclick="togglePatternGroup(this)">
        <span class="pattern-toggle">▼</span>
        🔄 Repeating Pattern: {repetitions}x repetitions of {pattern_length} calls 
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
    is_external = call.get('is_external', False)
    is_import = _is_import_call(call)
    
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
    
    args_html = _format_arguments_html(arguments)
    
    return f"""<div class="{css_classes}" onclick="toggleCallArgs('{call_id}')">
{indent}[#{index + 1}] <strong>{name}</strong>{args_display} <span style="color: #666;">[{location}]</span>
</div>
<div id="args_{call_id}" class="args-container" style="display: none;">
    {args_html}
</div>"""

def _format_arguments_html(arguments: dict) -> str:
    """Format arguments as HTML for display."""
    if not arguments:
        return '<div class="no-args">No arguments</div>'
    
    html_parts = ['<div class="args-header">Function Arguments:</div>']
    
    for name, value in arguments.items():
        if isinstance(value, str):
            if len(value) > 50:
                formatted_value = f'"{value[:47]}..."'
            else:
                formatted_value = f'"{value}"'
            value_type = 'str'
        elif isinstance(value, (int, float)):
            formatted_value = str(value)
            value_type = 'int' if isinstance(value, int) else 'float'
        elif isinstance(value, bool):
            formatted_value = str(value)
            value_type = 'bool'
        elif value is None:
            formatted_value = 'None'
            value_type = 'NoneType'
        elif isinstance(value, (list, tuple)):
            if len(value) == 0:
                formatted_value = '[]' if isinstance(value, list) else '()'
            elif len(value) > 3:
                formatted_value = f'[...{len(value)} items]'
            else:
                formatted_value = str(value)
            value_type = 'list' if isinstance(value, list) else 'tuple'
        elif isinstance(value, dict):
            if len(value) == 0:
                formatted_value = '{}'
            elif len(value) > 3:
                formatted_value = f'{{{len(value)} keys}}';
            else:
                formatted_value = str(value)
            value_type = 'dict'
        else:
            formatted_value = str(value)
            value_type = type(value).__name__
            
        html_parts.append(f'''
            <div class="arg-item">
                <span class="arg-name">{name}:</span>
                <span class="arg-value">{formatted_value}</span>
                <span class="arg-type">({value_type})</span>
            </div>
        ''')
    
    return ''.join(html_parts)