#!/usr/bin/env python3
"""
Production ingestion pipeline for Project Foresight.
Polls all data sources, merges into chronological event database,
outputs raw_events.jsonl.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Set, Dict

# Ensure the foresight package is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from foresight.ingestion.research_scraper import poll_since as research_poll_since
from foresight.ingestion.product_footprint_scraper import ProductFootprintScraper
from foresight.ingestion.macro_signals_scraper import MacroSignalsScraper

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"logs/pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S.log')}"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Event:
    def __init__(self, event_dict: Dict):
        self.event_dict = event_dict
        self.event_id = event_dict.get('event_id')
        self.timestamp = event_dict.get('timestamp')
    
    def to_json(self) -> str:
        return json.dumps(self.event_dict)
    
    def __eq__(self, other):
        return isinstance(other, Event) and self.event_id == other.event_id
    
    def __hash__(self):
        return hash(self.event_id)

def load_seed_events(seed_file: str) -> List[Dict]:
    """Load seed events from known_events.json"""
    try:
        with open(seed_file, 'r') as f:
            events = json.load(f)
        logger.info(f"Loaded {len(events)} seed events from {seed_file}")
        return events
    except FileNotFoundError:
        logger.warning(f"Seed file {seed_file} not found. Starting with empty seed.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding seed file {seed_file}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Production ingestion pipeline for Project Foresight.")
    parser.add_argument('--since', type=str, default=None, help='Pull events after this date (YYYY-MM-DD), default: 5 years ago')
    parser.add_argument('--output', type=str, default='data/raw_events.jsonl', help='Output file path')
    parser.add_argument('--seed', type=str, default='data/known_events.json', help='Seed events file')
    
    args = parser.parse_args()
    
    # Parse since date
    if args.since:
        try:
            since_date = datetime.strptime(args.since, '%Y-%m-%d')
        except ValueError:
            logger.error(f"Invalid date format for --since: {args.since}. Use YYYY-MM-DD.")
            sys.exit(1)
    else:
        # Default: 5 years ago
        since_date = datetime.now() - timedelta(days=5*365)
    
    logger.info(f"Starting pipeline with since_date: {since_date}")
    
    # 1. Load seed events
    seed_events = load_seed_events(args.seed)
    
    # 2. Import and register scrapers
    # Research scraper (ArXiv/OpenReview)
    logger.info("Polling research scraper (ArXiv/OpenReview)...")
    research_events = research_poll_since(since=since_date)
    logger.info(f"Collected {len(research_events)} research events")
    
    # Product footprint scraper (GitHub)
    logger.info("Polling product footprint scraper (GitHub)...")
    product_scraper = ProductFootprintScraper()
    product_events = product_scraper.poll(since=since_date)
    logger.info(f"Collected {len(product_events)} product footprint events")
    
    # Macro signals scraper (SEC EDGAR)
    logger.info("Polling macro signals scraper (SEC EDGAR)...")
    macro_scraper = MacroSignalsScraper()
    macro_events = macro_scraper.poll(since=since_date)
    logger.info(f"Collected {len(macro_events)} macro signal events")
    
    # 3. Combine all events
    all_events = seed_events + research_events + product_events + macro_events
    
    # 4. Deduplicate by event_id
    seen_ids: Set[str] = set()
    unique_events = []
    for event_dict in all_events:
        event_id = event_dict.get('event_id')
        if event_id and event_id not in seen_ids:
            seen_ids.add(event_id)
            unique_events.append(event_dict)
        elif not event_id:
            # If no event_id, we still include it (shouldn't happen with proper scrapers)
            unique_events.append(event_dict)
    
    logger.info(f"After deduplication: {len(unique_events)} unique events (from {len(all_events)} total)")
    
    # 5. Sort chronologically by timestamp
    def get_timestamp(event_dict):
        ts = event_dict.get('timestamp')
        if ts:
            try:
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except:
                return datetime.min  # Placeholder for unparseable dates
        return datetime.min
    
    unique_events.sort(key=get_timestamp)
    
    # 6. Write output file
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        for event_dict in unique_events:
            f.write(json.dumps(event_dict) + '\n')
    
    logger.info(f"Wrote {len(unique_events)} events to {args.output}")
    
    # 7. Log summary
    stream_counts = {}
    for event in unique_events:
        stream = event.get('stream', 'unknown')
        stream_counts[stream] = stream_counts.get(stream, 0) + 1
    
    date_range = {"earliest": None, "latest": None}
    for event in unique_events:
        ts = event.get('timestamp')
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                if date_range["earliest"] is None or dt < date_range["earliest"]:
                    date_range["earliest"] = dt
                if date_range["latest"] is None or dt > date_range["latest"]:
                    date_range["latest"] = dt
            except:
                pass
    
    logger.info("=== Pipeline Summary ===")
    logger.info(f"Total events collected: {len(unique_events)}")
    logger.info(f"Per-stream counts: {stream_counts}")
    logger.info(f"Date range: {date_range['earliest']} to {date_range['latest']}")
    logger.info(f"Output file: {args.output}")

if __name__ == "__main__":
    main()