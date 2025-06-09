from typing import List, Dict, Any, Tuple, Optional
import json

class PatternGrouper:
    def __init__(self, min_pattern_length=2, min_repetitions=2):
        self.min_pattern_length = min_pattern_length
        self.min_repetitions = min_repetitions
        
    def group_patterns(self, trace_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group repeating patterns in trace data."""
        if not trace_data:
            return trace_data
            
        # Create a simplified representation for pattern matching
        simplified_calls = self._simplify_calls(trace_data)
        
        # Find all patterns starting with longer ones
        patterns = self._find_patterns(simplified_calls)
        
        # Apply patterns to create grouped structure
        return self._apply_patterns(trace_data, patterns)
    
    def _simplify_calls(self, trace_data: List[Dict[str, Any]]) -> List[str]:
        """Create simplified representation of calls for pattern matching."""
        simplified = []
        for call in trace_data:
            # Use function name + location as the pattern key
            key = f"{call.get('name', 'unknown')}@{call.get('location', 'unknown')}"
            simplified.append(key)
        return simplified
    
    def _find_patterns(self, simplified_calls: List[str]) -> List[Tuple[int, int, int]]:
        """Find repeating patterns. Returns list of (start_idx, pattern_length, repetitions)."""
        patterns = []
        used_indices = set()
        
        # Try different pattern lengths, starting with longer patterns
        for pattern_length in range(min(20, len(simplified_calls) // 2), self.min_pattern_length - 1, -1):
            i = 0
            while i <= len(simplified_calls) - pattern_length * self.min_repetitions:
                # Skip if this index is already part of a pattern
                if i in used_indices:
                    i += 1
                    continue
                    
                pattern = simplified_calls[i:i + pattern_length]
                repetitions = self._count_repetitions(simplified_calls, i, pattern)
                
                if repetitions >= self.min_repetitions:
                    # Found a valid pattern
                    total_length = pattern_length * repetitions
                    patterns.append((i, pattern_length, repetitions))
                    
                    # Mark these indices as used
                    for idx in range(i, i + total_length):
                        used_indices.add(idx)
                    
                    i += total_length
                else:
                    i += 1
        
        return sorted(patterns)  # Sort by start index
    
    def _count_repetitions(self, simplified_calls: List[str], start_idx: int, pattern: List[str]) -> int:
        """Count how many times a pattern repeats consecutively."""
        repetitions = 0
        pattern_length = len(pattern)
        idx = start_idx
        
        while idx + pattern_length <= len(simplified_calls):
            if simplified_calls[idx:idx + pattern_length] == pattern:
                repetitions += 1
                idx += pattern_length
            else:
                break
                
        return repetitions
    
    def _apply_patterns(self, trace_data: List[Dict[str, Any]], patterns: List[Tuple[int, int, int]]) -> List[Dict[str, Any]]:
        """Apply detected patterns to create grouped structure."""
        if not patterns:
            return trace_data
            
        grouped_data = []
        i = 0
        
        while i < len(trace_data):
            # Check if current index starts a pattern
            pattern_found = False
            for start_idx, pattern_length, repetitions in patterns:
                if i == start_idx:
                    # Create a pattern group
                    pattern_calls = trace_data[i:i + pattern_length * repetitions]
                    
                    # Recursively find nested patterns within this pattern
                    single_pattern = pattern_calls[:pattern_length]
                    nested_grouped = self._find_nested_patterns(single_pattern)
                    
                    pattern_group = {
                        "type": "pattern_group",
                        "pattern_length": pattern_length,
                        "repetitions": repetitions,
                        "pattern_calls": nested_grouped,
                        "total_calls": len(pattern_calls),
                        "start_index": start_idx,
                        "end_index": start_idx + len(pattern_calls) - 1
                    }
                    
                    grouped_data.append(pattern_group)
                    i += pattern_length * repetitions
                    pattern_found = True
                    break
            
            if not pattern_found:
                grouped_data.append(trace_data[i])
                i += 1
        
        return grouped_data
    
    def _find_nested_patterns(self, pattern_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find nested patterns within a single pattern instance."""
        if len(pattern_calls) < self.min_pattern_length * self.min_repetitions:
            return pattern_calls
            
        # Create a new grouper for nested patterns with potentially smaller requirements
        nested_grouper = PatternGrouper(min_pattern_length=2, min_repetitions=2)
        return nested_grouper.group_patterns(pattern_calls)

def group_trace_patterns(trace_data: List[Dict[str, Any]], 
                        min_pattern_length: int = 2, 
                        min_repetitions: int = 2) -> List[Dict[str, Any]]:
    """Convenience function to group patterns in trace data."""
    grouper = PatternGrouper(min_pattern_length, min_repetitions)
    return grouper.group_patterns(trace_data)
