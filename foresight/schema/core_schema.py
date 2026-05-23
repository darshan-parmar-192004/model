#!/usr/bin/env python3
"""
Core schema definitions for Project Foresight.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class TemporalSequence:
    """Represents a single training sequence with past and future events."""
    input_cutoff: datetime
    lookback_start: datetime
    past_events: List[Dict]
    future_events: List[Dict]
    horizon_days: int
    metadata: Dict = field(default_factory=dict)


@dataclass
class SignalEvent:
    """Represents a single signal event from any data source."""
    event_id: str
    timestamp: datetime
    stream: str
    signal_type: str
    confidence: float
    content_raw: str
    entities: List[str] = field(default_factory=list)
    source_url: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


def build_context_string(past_events: List[Dict]) -> str:
    """
    Build a structured timeline string from past events for model input.
    Format follows the blueprint specification.
    """
    sections = {"compute": [], "research": [], "product": [], "hiring": []}
    stream_map = {
        "infra": "compute", 
        "research": "research",
        "product_footprint": "product", 
        "macro": "hiring",
    }
    
    for ev in past_events:
        key = stream_map.get(ev.get("stream", ""), "research")
        ts = ev.get("timestamp", "unknown")
        if isinstance(ts, datetime):
            ts = ts[:10] if len(ts) >= 10 else ts
        content = ev.get("content_raw", ev.get("title", str(ev)))
        sections[key].append(f"{ts}: {content}")
    
    parts = ["[TIMELINE: OBSERVED EVENTS]"]
    for section_name, events in sections.items():
        if events:
            header = section_name.capitalize()
            parts.append(f"\n### {header} Indicators")
            parts.extend(events)
    
    return "\n".join(parts)


def build_target_string(future_events: List[Dict]) -> str:
    """
    Build a structured target string from future events for model output.
    Format follows the blueprint specification.
    """
    lines = ["{\"predictions\": ["]
    preds = []
    
    for ev in future_events:
        ts = ev.get("timestamp", "unknown")
        if isinstance(ts, datetime):
            ts = ts[:10] if len(ts) >= 10 else ts
        
        pred = {
            "event_type": ev.get("signal_type", "event"),
            "predicted_date": ts,
            "description": ev.get("content_raw", ev.get("title", str(ev)))[:200],
            "confidence": ev.get("confidence", 0.5)
        }
        preds.append(pred)
    
    for pred in preds:
        lines.append(f"  {pred},")
    
    lines.append("]}")
    return "\n".join(lines)