#!/usr/bin/env python3
"""
Builds training and validation datasets from raw_events.jsonl.
Outputs train_dataset.jsonl and val_dataset.jsonl in causal format.
"""

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

# Ensure the foresight package is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foresight.utils.time_utils import parse_timestamp, format_timestamp
from foresight.schema.core_schema import TemporalSequence, build_context_string, build_target_string
from foresight.dataset.augmentation import TemporalAugmenter
from foresight.model.sequence_builder import TemporalSequencingEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/build_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S.log')}"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def build_training_dataset(
    input_path: str,
    output_dir: str,
    lookback_days: int = 1825,          # 5 years
    minima_hours: int = 24,             # Minimum hours for a day to count as valid
    forefront_days: int = 1,            # Number of days at forefront
    horizons_days: List[int] = [30, 90], # Forecast horizons
    stride_days: int = 14,              # Stride between sequences
    val_ratio: float = 0.2,             # Validation split ratio
    seed: int = 42                      # Random seed
) -> None:
    """Build training and validation datasets from raw events."""
    
    logger.info(f"Starting dataset builder with input_path={input_path}, output_dir={output_dir}")
    
    # 1. Load raw_events.jsonl
    events = []
    try:
        with open(input_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    event = json.loads(line)
                    events.append(event)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON at line {line_num} in {input_path}: {e}")
                    continue
        logger.info(f"Loaded {len(events)} events from {input_path}")
    except FileNotFoundError:
        logger.error(f"Input file {input_path} not found.")
        sys.exit(1)
    
    if not events:
        logger.warning("No events loaded. Exiting.")
        return
    
    # 2. Parse timestamps
    parsed_events = []
    for event in events:
        try:
            ts = parse_timestamp(event.get('timestamp'))
            event['_ts'] = ts
            parsed_events.append(event)
        except Exception as e:
            logger.error(f"Error parsing timestamp for event {event.get('event_id')}: {e}")
            event['_ts'] = None
            parsed_events.append(event)
    
    # 3. Validate and synchronize timestamps
    logger.info("Validating timestamps...")
    valid_events = [e for e in parsed_events if e['_ts'] is not None]
    invalid_ratio = 1 - (len(valid_events) / len(parsed_events)) if len(parsed_events) > 0 else 1
    if invalid_ratio > 0.3:
        logger.warning(f"High proportion of invalid timestamps ({invalid_ratio:.1%}), proceeding with caution")
    
    # 4. Sort by timestamp
    parsed_events.sort(key=lambda e: e.get('_ts', datetime.min))
    
    # 5. Create temporal sequencing engine
    logger.info("Creating temporal sequencing engine...")
    engine = TemporalSequencingEngine(events=parsed_events)
    
    # 6. Create sequences
    logger.info("Creating temporal sequences...")
    sequences = engine.create_sequences(
        lookback_days=lookback_days,
        forecast_horizons=horizons_days,
        min_past_events=20,
        stride_days=stride_days
    )
    
    if not sequences:
        logger.warning("No sequences created. Exiting.")
        return
    
    # 7. Split into train/val by cutoff date
    logger.info("Splitting sequences into train/val...")
    all_dates = [e['_ts'] for e in parsed_events if e['_ts'] is not None]
    val_cutoff = sorted(all_dates)[int(len(all_dates) * 0.8)] if len(all_dates) > 0 else None
    
    # Create train and validation sets
    train_seqs = [seq for seq in sequences if hasattr(seq, 'input_cutoff') and seq.input_cutoff < val_cutoff]
    val_seqs = [seq for seq in sequences if hasattr(seq, 'input_cutoff') and seq.input_cutoff >= val_cutoff]
    
    logger.info(f"Created {len(train_seqs)} training sequences and {len(val_seqs)} validation sequences")
    
    # 8. Augment training sequences
    logger.info("Augmenting training sequences...")
    augmenter = TemporalAugmenter(seed=seed)
    
    augmented_train_seqs = []
    for seq in train_seqs:
        variants = augmenter.apply_all(seq.past_events, jitter_pct=0.05, dropout_rate=0.10)
        for variant_events in variants:
            augmented_train_seqs.append(TemporalSequence(
                input_cutoff=seq.input_cutoff,
                lookback_start=seq.lookback_start,
                past_events=variant_events,
                future_events=seq.future_events,
                horizon_days=seq.horizon_days,
                metadata=seq.metadata
            ))
    
    logger.info(f"Performed augmentation: {len(train_seqs)} -> {len(augmented_train_seqs)} sequences")
    
    # 9. Format as JSONL (instruction-output pairs)
    logger.info("Formatting as JSONL...")
    os.makedirs(output_dir, exist_ok=True)
    
    for seq_list, output_name in [(augmented_train_seqs, 'train_dataset.jsonl'), (val_seqs, 'val_dataset.jsonl')]:
        output_path = os.path.join(output_dir, output_name)
        with open(output_path, 'w') as f:
            for seq in seq_list:
                try:
                    instruction = build_context_string(seq.past_events)
                    output = build_target_string(seq.future_events)
                    sample = {
                        "instruction": instruction,
                        "output": output,
                        "metadata": {
                            "cutoff": format_timestamp(seq.input_cutoff),
                            "horizon_days": seq.horizon_days,
                            "num_past_events": len(seq.past_events),
                            "num_future_events": len(seq.future_events)
                        }
                    }
                    f.write(json.dumps(sample) + '\n')
                except Exception as e:
                    logger.error(f"Error formatting sequence: {e}")
        
        logger.info(f"Saved {len(seq_list)} sequences to {output_path}")
    
    # 10. Log statistics
    logger.info(f"Total sequences created: {len(sequences)}")
    logger.info(f"Training sequences (augmented): {len(augmented_train_seqs)}")
    logger.info(f"Validation sequences: {len(val_seqs)}")
    logger.info(f"Training dataset saved to {os.path.join(output_dir, 'train_dataset.jsonl')}")
    logger.info(f"Validation dataset saved to {os.path.join(output_dir, 'val_dataset.jsonl')}")

def main():
    parser = argparse.ArgumentParser(
        description="Build training dataset from raw events for Project Foresight"
    )
    parser.add_argument('--input', type=str, default='data/raw_events.jsonl', help='Path to input JSONL file')
    parser.add_argument('--output-dir', type=str, default='data/', help='Output directory for datasets')
    parser.add_argument('--lookback-days', type=int, default=1825, help='Lookback period in days')
    parser.add_argument('--horizons', type=str, default='30 90', help='Forecast horizons in days (space separated)')
    parser.add_argument('--stride-days', type=int, default=14, help='Stride between sequences in days')
    parser.add_argument('--val-ratio', type=float, default=0.2, help='Ratio of data for validation')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for augmentation')
    
    args = parser.parse_args()
    
    # Parse horizons
    if args.horizons:
        horizons = [int(x) for x in args.horizons.split()]
    else:
        horizons = [30, 90]
    
    build_training_dataset(
        input_path=args.input,
        output_dir=args.output_dir,
        lookback_days=args.lookback_days,
        minima_hours=getattr(args, 'minima_hours', 24),
        forefront_days=getattr(args, 'forefront_days', 1),
        horizons_days=horizons,
        stride_days=args.stride_days,
        val_ratio=args.val_ratio,
        seed=args.seed
    )

if __name__ == "__main__":
    main()