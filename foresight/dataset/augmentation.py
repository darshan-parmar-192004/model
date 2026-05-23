#!/usr/bin/env python3
"""
Temporal augmentation utilities for training dataset generation.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict


class TemporalAugmenter:
    """
    Applies temporal augmentation techniques to increase dataset diversity.
    """
    
    def __init__(self, seed: int = None):
        self.seed = seed
        if seed is not None:
            random.seed(seed)
    
    def apply_jitter(self, events: List[Dict], jitter_pct: float = 0.05) -> List[Dict]:
        """
        Apply temporal jitter to event timestamps.
        Shifts all timestamps by +/- jitter_pct of the time range.
        """
        if not events:
            return events
        
        # Find time range
        timestamps = []
        for ev in events:
            ts = ev.get('timestamp')
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except:
                    continue
            if isinstance(ts, datetime):
                timestamps.append(ts)
        
        if len(timestamps) < 2:
            return events
        
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        time_range = (max_ts - min_ts).total_seconds()
        jitter_seconds = int(time_range * jitter_pct)
        
        if jitter_seconds <= 0:
            return events
        
        # Apply random shift
        shift_seconds = random.randint(-jitter_seconds, jitter_seconds)
        shift = timedelta(seconds=shift_seconds)
        
        jittered_events = []
        for ev in events:
            new_ev = ev.copy()
            ts = ev.get('timestamp')
            if isinstance(ts, datetime):
                new_ev['timestamp'] = ts + shift
            elif isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    new_ev['timestamp'] = (dt + shift).isoformat()
                except:
                    pass
            jittered_events.append(new_ev)
        
        return jittered_events
    
    def apply_dropout(self, events: List[Dict], dropout_rate: float = 0.1) -> List[Dict]:
        """
        Randomly drop events with the given probability.
        """
        if dropout_rate <= 0:
            return events
        
        kept_events = []
        for ev in events:
            if random.random() > dropout_rate:
                kept_events.append(ev)
        
        return kept_events
    
    def apply_all(self, events: List[Dict], jitter_pct: float = 0.05, dropout_rate: float = 0.1) -> List[List[Dict]]:
        """
        Apply all augmentations and return a list of variants.
        Returns the original + augmented variants.
        """
        variants = [events]  # Always include original
        
        # Jitter variants
        for _ in range(2):  # Create 2 jittered variants
            jittered = self.apply_jitter(events, jitter_pct)
            if jittered != events:
                variants.append(jittered)
        
        # Dropout variants
        for _ in range(2):  # Create 2 dropout variants
            dropped = self.apply_dropout(events, dropout_rate)
            if dropped != events and dropped:
                variants.append(dropped)
        
        return variants