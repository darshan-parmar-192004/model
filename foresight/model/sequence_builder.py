#!/usr/bin/env python3
"""
Temporal sequencing engine for creating training sequences.
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

from foresight.schema.core_schema import TemporalSequence

logger = logging.getLogger(__name__)


class TemporalSequencingEngine:
    """
    Creates temporal sequences from a list of events for time-series prediction.
    """
    
    def __init__(self, events: List[Dict]):
        self.events = sorted(events, key=lambda e: e.get('_ts', datetime.min))
    
    def create_sequences(
        self,
        lookback_days: int = 365 * 2,      # 2 years context
        forecast_horizons: List[int] = [30, 90],  # 1, 3 months
        min_past_events: int = 20,
        stride_days: int = 14
    ) -> List[TemporalSequence]:
        """
        Create (input_context, target_events) pairs.
        """
        sequences = []
        
        event_df = self.events
        
        # Create cutoff points
        cutoff_points = []
        for i in range(len(event_df)):
            current_ts = event_df[i].get('_ts')
            if current_ts is None:
                continue
            cutoff_points.append((i, current_ts))
        
        # For each cutoff point, create sequences with different horizons
        for cutoff_idx, cutoff_date in cutoff_points:
            # Block: use only events up to cutoff_date
            past_events = event_df[:cutoff_idx + 1]
            
            # Need minimum history
            if len(past_events) < min_past_events:
                continue
            
            for horizon in forecast_horizons:
                future_date = cutoff_date + timedelta(days=horizon)
                
                # Find future events
                future_events = []
                for ev in event_df[cutoff_idx + 1:]:
                    ev_ts = ev.get('_ts')
                    if ev_ts and cutoff_date < ev_ts <= future_date:
                        future_events.append(ev)
                
                if len(future_events) > 0:
                    lookback_start = cutoff_date - timedelta(days=lookback_days)
                    
                    sequence = TemporalSequence(
                        input_cutoff=cutoff_date,
                        lookback_start=lookback_start,
                        past_events=past_events,
                        future_events=future_events,
                        horizon_days=horizon,
                        metadata={
                            'cutoff_idx': cutoff_idx,
                            'num_past_events': len(past_events),
                            'num_future_events': len(future_events)
                        }
                    )
                    sequences.append(sequence)
        
        logger.info(f"Created {len(sequences)} temporal sequences")
        return sequences