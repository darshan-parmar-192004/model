#!/usr/bin/env python3
"""
Time utility functions for timestamp parsing and formatting.
"""

from datetime import datetime
from typing import Optional


def parse_timestamp(ts: str) -> Optional[datetime]:
    """
    Parse a timestamp string into a datetime object.
    Handles multiple formats: ISO 8601, RFC 2822, etc.
    """
    if ts is None:
        return None
    
    # List of formats to try
    formats = [
        '%Y-%m-%dT%H:%M:%SZ',           # ISO 8601 UTC
        '%Y-%m-%dT%H:%M:%S.%fZ',        # ISO 8601 UTC with microseconds
        '%Y-%m-%dT%H:%M:%S%z',          # ISO 8601 with timezone
        '%Y-%m-%dT%H:%M:%S.%f%z',       # ISO 8601 with microseconds and timezone
        '%Y-%m-%dT%H:%M:%S',            # ISO 8601 without timezone
        '%Y-%m-%dT%H:%M:%S.%f',         # ISO 8601 with microseconds without timezone
        '%Y-%m-%d %H:%M:%S',            # Common format
        '%Y-%m-%d',                     # Date only
        '%a, %d %b %Y %H:%M:%S %z',     # RFC 2822
    ]
    
    # Handle 'Z' suffix for UTC
    if ts.endswith('Z'):
        ts = ts[:-1] + '+00:00'
    
    for fmt in formats:
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    
    # If all else fails, try fromisoformat (Python 3.7+)
    try:
        return datetime.fromisoformat(ts.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    raise ValueError(f"Unable to parse timestamp: {ts}")


def format_timestamp(dt: datetime) -> str:
    """
    Format a datetime object to ISO 8601 string.
    """
    if dt is None:
        return None
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')