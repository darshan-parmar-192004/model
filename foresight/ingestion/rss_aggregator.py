#!/usr/bin/env python3
"""
RSS feed aggregator for Project Foresight.
Continuously monitors AI-related news sources.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import feedparser
import re

try:
    from kafka import KafkaProducer
    import json
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    KAFKA_AVAILABLE = True
except Exception:
    KAFKA_AVAILABLE = False
    producer = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RSS_SOURCES = {
    "techcrunch_ai": "http://feeds.feedburner.com/TechCrunchAI",
    "venturebeat_ai": "https://venturebeat.com/category/ai/feed/",
    "mit_tech_review": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
    "ars_technica_ai": "https://feeds.arstechnica.com/arstechnica/technology-review/",
    "ieee_spectrum": "http://rssspectrum.ieee.org/rss/ai.xml",
    "ai_news": "https://artificialintelligence-news.com/feed/",
}

AI_KEYWORDS = [
    r"funding", r"series [a-z]", r"raises \$", r"investment",
    r"model", r"llm", r"large language", r"gpt", r"claude", r"gemini",
    r"hiring", r"appoints", r"cto", r"chief", r"researcher",
    r"release", r"launch", r"api", r"feature",
    r"nvidia", r"gpu", r"h100", r"a100", r"blackwell",
    r"anthropic", r"openai", r"google", r"deepmind", r"mistral", r"cohere",
]

class RSSAggregator:
    def __init__(self):
        self.seen_entries = set()

    def poll(self, since: Optional[datetime] = None) -> List[Dict]:
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        events = []
        
        for source_name, feed_url in RSS_SOURCES.items():
            try:
                source_events = self._poll_feed(source_name, feed_url, since)
                events.extend(source_events)
            except Exception as e:
                logger.error(f"Error polling {source_name}: {e}")
                continue
        
        if KAFKA_AVAILABLE and producer:
            for event in events:
                try:
                    producer.send('tech_intel_stream', value=event)
                except Exception as e:
                    logger.error(f"Failed to send to Kafka: {e}")
        
        logger.info(f"Found {len(events)} new RSS events since {since}")
        return events

    def _poll_feed(self, source_name: str, feed_url: str, since: datetime) -> List[Dict]:
        events = []
        
        feed = feedparser.parse(feed_url)
        
        for entry in feed.entries[:50]:
            entry_id = f"rss_{source_name}_{hash(entry.get('link', entry.get('title', '')))}"
            
            if entry_id in self.seen_entries:
                continue
            self.seen_entries.add(entry_id)
            
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6])
            
            if not pub_date or pub_date < since:
                continue
            
            title = entry.get('title', '')
            summary = entry.get('summary', entry.get('description', ''))
            content = title + " " + summary
            
            keyword_matches = []
            for pattern in AI_KEYWORDS:
                if re.search(pattern, content, re.IGNORECASE):
                    keyword_matches.append(pattern)
            
            if not keyword_matches:
                continue
            
            signal_type = "funding" if any(k in ' '.join(keyword_matches).lower() for k in ["funding", "series", "raises", "investment"]) else "news"
            
            event = {
                "event_id": entry_id,
                "timestamp": pub_date.isoformat(),
                "stream": "macro",
                "signal_type": signal_type,
                "confidence": 0.85,
                "content_raw": f"[{source_name}] {title}: {summary[:300]}",
                "entities": self._extract_entities(summary),
                "source_url": entry.get('link', ''),
                "metadata": {
                    "source": source_name,
                    "keyword_matches": keyword_matches,
                }
            }
            events.append(event)
        
        return events

    def _extract_entities(self, text: str) -> List[str]:
        companies = ["OpenAI", "Anthropic", "Google", "DeepMind", "Mistral", "Cohere", 
                     "Microsoft", "Meta", "NVIDIA", "Amazon", "Apple", "IBM"]
        found = []
        for company in companies:
            if company.lower() in text.lower():
                found.append(company)
        return found


def run_continuous_polling(interval_seconds: int = 1800):
    aggregator = RSSAggregator()
    logger.info("Starting continuous polling for RSS feeds...")
    last_poll = datetime.utcnow() - timedelta(hours=1)
    
    while True:
        try:
            events = aggregator.poll(since=last_poll)
            if events:
                logger.info(f"Polled {len(events)} new RSS events")
                for event in events[:5]:
                    logger.info(f"  - {event['content_raw'][:100]}...")
            last_poll = datetime.utcnow()
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Stopping continuous polling.")
            break
        except Exception as e:
            logger.error(f"Error in continuous polling: {e}")
            time.sleep(60)


if __name__ == "__main__":
    aggregator = RSSAggregator()
    events = aggregator.poll()
    print(f"Found {len(events)} events")