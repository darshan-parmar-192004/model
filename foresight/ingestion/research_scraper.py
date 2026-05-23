#!/usr/bin/env python3
"""
Research scraper for Project Foresight.
Continuously ingests papers from ArXiv and OpenReview.
"""

import arxiv
try:
    import openreview
    OPENREVIEW_AVAILABLE = True
except ImportError:
    OPENREVIEW_AVAILABLE = False
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import time
import logging
from kafka import KafkaProducer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ANTHROPIC_AFFILIATIONS = ["Anthropic", "Anthropic AI"]
TARGET_AUTHORS = [
    "Dario Amodei", "Tom Brown", "Jared Kaplan", "Jack Clark",
    "Amanda Askell", "Yuntao Bai", "Sam McCandlish", "Andrej Karpathy",
]
TARGET_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "stat.ML"]
KEYWORD_FILTERS = [
    "constitutional AI", "RLHF", "pretraining", "scaling law",
    "agent", "tool use", "computer use", "automated red teaming",
    "mechanistic interpretability", "safety", "alignment",
]

# Kafka producer (optional, for streaming)
try:
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    KAFKA_AVAILABLE = True
except Exception as e:
    logger.warning(f"Kafka not available: {e}. Events will be logged but not streamed.")
    KAFKA_AVAILABLE = False
    producer = None

def poll_arxiv(last_poll: Optional[datetime] = None) -> List[Dict]:
    """
    Poll ArXiv for new papers matching our criteria.
    """
    if last_poll is None:
        last_poll = datetime.utcnow() - timedelta(hours=1)
    
    # Build query for categories
    cat_query = " AND ".join(f"cat:{cat}" for cat in TARGET_CATEGORIES)
    # Build query for authors (OR'ed)
    author_query = " OR ".join(f'au:"{author}"' for author in TARGET_AUTHORS)
    # Combine: we want papers in our categories AND by our target authors
    # Note: ArXiv API doesn't support complex queries easily, so we'll fetch by category and filter by author
    search = arxiv.Search(
        query=cat_query,
        max_results=500,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    
    papers = []
    # arxiv 4.0.0 uses different API - iterate directly over the search object
    try:
        for result in search:
            # Skip if older than last poll
            if result.published < last_poll:
                continue
            
            # Check if any target author is in the paper's authors
            author_match = any(
                author.lower() in str(result.authors).lower()
                for author in TARGET_AUTHORS
            )
            
            # Check for keyword matches in title and abstract
            text_to_search = (result.title + " " + result.summary).lower()
            keyword_match = any(
                keyword in text_to_search
                for keyword in KEYWORD_FILTERS
            )
            
            # Also check affiliations (though ArXiv doesn't always provide them)
            # We'll rely on author matching for now
            
            if author_match or keyword_match:
                paper = {
                    "event_id": f"arxiv_{result.entry_id.split('/')[-1]}",
                    "timestamp": result.published.isoformat(),
                    "stream": "research",
                    "signal_type": "paper",
                    "confidence": 0.95 if author_match else 0.70,
                    "content_raw": f"[{result.title}] {result.summary[:200]}...",
                    "entities": [str(a) for a in result.authors] + ANTHROPIC_AFFILIATIONS,
                    "source_url": result.entry_id,
                    "metadata": {
                        "authors": [str(a) for a in result.authors],
                        "categories": result.categories,
                    }
                }
                papers.append(paper)
    except Exception as e:
        logger.error(f"Error polling ArXiv: {e}")
    
    logger.info(f"Found {len(papers)} new papers from ArXiv since {last_poll}")
    return papers

def poll_openreview(last_poll: Optional[datetime] = None) -> List[Dict]:
    """
    Poll OpenReview for new submissions matching our criteria.
    """
    if not OPENREVIEW_AVAILABLE:
        logger.warning("OpenReview not available, returning empty list")
        return []
    
    if last_poll is None:
        last_poll = datetime.utcnow() - timedelta(hours=1)
    
    try:
        # OpenReview API v2 client
        client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
        # Get submissions from relevant venues (we'll use a broad invitation and filter)
        # Note: This is simplified; in practice, you'd target specific conferences/journals
        submissions = client.get_all_notes(
            invitation='*/-/Submission',
            details='original'
        )
        
        papers = []
        for note in submissions:
            # Skip if older than last poll
            cdate = datetime.fromtimestamp(note.cdate / 1000.0)  # OpenReview uses milliseconds
            if cdate < last_poll:
                continue
            
            # Check for keyword matches in title and abstract
            title = note.content.get('title', '')
            abstract = note.content.get('abstract', '')
            text_to_search = (title + " " + abstract).lower()
            
            keyword_match = any(
                keyword in text_to_search
                for keyword in KEYWORD_FILTERS
            )
            
            # Check for author affiliations (simplified)
            # OpenReview doesn't always provide structured affiliations, so we'll look for strings
            author_string = str(note.content.get('authors', []))
            author_match = any(
                author.lower() in author_string.lower()
                for author in TARGET_AUTHORS
            )
            
            if keyword_match or author_match:
                paper = {
                    "event_id": f"openreview_{note.id}",
                    "timestamp": cdate.isoformat(),
                    "stream": "research",
                    "signal_type": "openreview",
                    "confidence": 0.9 if (keyword_match and author_match) else 0.7,
                    "content_raw": f"[{title}] {abstract[:200]}...",
                    "entities": note.content.get('authors', []) + ANTHROPIC_AFFILIATIONS,
                    "source_url": f"https://openreview.net/forum?id={note.id}",
                    "metadata": {
                        "title": title,
                        "authors": note.content.get('authors', []),
                        "abstract": abstract,
                    }
                }
                papers.append(paper)
        
        logger.info(f"Found {len(papers)} new submissions from OpenReview since {last_poll}")
        return papers
    except Exception as e:
        logger.error(f"Error polling OpenReview: {e}")
        return []

def poll_since(since: Optional[datetime] = None) -> List[Dict]:
    """
    Poll both ArXiv and OpenReview for new events since the given timestamp.
    """
    arxiv_papers = poll_arxiv(since)
    openreview_papers = poll_openreview(since)
    
    all_papers = arxiv_papers + openreview_papers
    
    # Stream to Kafka if available
    if KAFKA_AVAILABLE and producer:
        for paper in all_papers:
            try:
                producer.send('tech_intel_stream', value=paper)
            except Exception as e:
                logger.error(f"Failed to send to Kafka: {e}")
    
    return all_papers

def run_continuous_polling(interval_seconds: int = 3600):
    """
    Run continuous polling at the given interval (default: 1 hour).
    """
    logger.info("Starting continuous polling for research papers...")
    last_poll = datetime.utcnow() - timedelta(hours=1)  # Start by looking at last hour
    
    while True:
        try:
            papers = poll_since(last_poll)
            if papers:
                logger.info(f"Polled {len(papers)} new research papers")
                # In a real system, we would save these to a database or message queue
                # For now, we just log
                for paper in papers[:5]:  # Log first 5
                    logger.info(f"  - {paper['title'][:100]}...")
            last_poll = datetime.utcnow()
            time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Stopping continuous polling.")
            break
        except Exception as e:
            logger.error(f"Error in continuous polling: {e}")
            time.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    # Run a single poll for testing
    papers = poll_since()
    print(f"Found {len(papers)} papers")
    for paper in papers[:3]:
        print(f"- {paper['title']}")