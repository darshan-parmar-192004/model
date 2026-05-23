#!/usr/bin/env python3
"""
Product footprint scraper for Project Foresight.
Continuously monitors GitHub repositories for commits, releases, and changelogs.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    logger.warning("PyGithub not installed. Install with: pip install PyGithub")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kafka producer (optional, for streaming)
try:
    from kafka import KafkaProducer
    import json
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    KAFKA_AVAILABLE = True
except Exception as e:
    logger.warning(f"Kafka not available: {e}. Events will be logged but not streamed.")
    KAFKA_AVAILABLE = False
    producer = None

class ProductFootprintScraper:
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize the scraper with GitHub token.
        If token is not provided, will attempt to read from GITHUB_TOKEN env var.
        """
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        if not self.github_token:
            logger.warning("No GitHub token provided. Rate limits will be severely limited (60/hr).")
        
        if GITHUB_AVAILABLE and self.github_token:
            self.github = Github(self.github_token)
        else:
            self.github = None
        
        # Target repositories to monitor
        self.TARGET_REPOS = [
            "anthropics/anthropic-cookbook",
            "anthropics/claude-code",
            "anthropics/claude-api-docs",
            "anthropics/evals",
        ]
        
        # Changelog URLs to monitor
        self.CHANGELOG_URLS = [
            "https://docs.anthropic.com/en/docs/changelog",
            "https://docs.anthropic.com/en/api/getting-started",
        ]
        
        # Keywords that indicate significant product changes
        self.SIGNIFICANT_KEYWORDS = [
            "computer_use", "tool_use", "agent_mode", 
            "context_window", "rate_limit", 
            "claude-3", "claude-4", "model_id"
        ]

    def poll(self, since: Optional[datetime] = None) -> List[Dict]:
        """
        Poll GitHub for new commits and releases since the given timestamp.
        If since is None, defaults to last 7 days.
        Returns list of SignalEvent dictionaries.
        """
        if since is None:
            since = datetime.utcnow() - timedelta(days=7)
        
        events = []
        
        # Poll each target repository
        for repo_name in self.TARGET_REPOS:
            try:
                repo_events = self._poll_repo(repo_name, since)
                events.extend(repo_events)
                # Be nice to GitHub API - small delay between repos
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error polling repository {repo_name}: {e}")
                continue
        
        # Poll changelogs
        try:
            changelog_events = self._poll_changelogs(since)
            events.extend(changelog_events)
        except Exception as e:
            logger.error(f"Error polling changelogs: {e}")
        
        # Stream to Kafka if available
        if KAFKA_AVAILABLE and producer:
            for event in events:
                try:
                    producer.send('tech_intel_stream', value=event)
                except Exception as e:
                    logger.error(f"Failed to send to Kafka: {e}")
        
        logger.info(f"Found {len(events)} new product footprint events since {since}")
        return events

    def _poll_repo(self, repo_name: str, since: datetime) -> List[Dict]:
        """
        Poll a single repository for commits and releases.
        """
        events = []
        
        if not self.github:
            # Fallback to mock data if GitHub not available
            logger.warning("GitHub not available, returning mock data for development")
            return self._get_mock_repo_events(repo_name, since)
        
        try:
            repo = self.github.get_repo(repo_name)
            
            # Get commits since 'since'
            commits = repo.get_commits(since=since)
            for commit in commits:
                # Skip if commit is older than since (should be handled by GitHub API, but double-check)
                commit_date = commit.commit.author.date.replace(tzinfo=None)
                if commit_date < since:
                    continue
                
                # Determine if this commit is significant
                message = commit.commit.message.lower()
                significant = any(keyword in message for keyword in self.SIGNIFICANT_KEYWORDS)
                confidence = 0.98 if significant else 0.95
                
                event = {
                    "event_id": f"github_commit_{commit.sha}",
                    "timestamp": commit_date.isoformat(),
                    "stream": "product_footprint",
                    "signal_type": "commit",
                    "confidence": confidence,
                    "content_raw": f"[{repo_name}] {commit.commit.message.strip()}",
                    "entities": ["Anthropic", repo_name.split('/')[1]],
                    "source_url": commit.html_url,
                    "metadata": {
                        "sha": commit.sha,
                        "repo": repo_name,
                        "author": str(commit.commit.author),
                        "files_changed": [f.filename for f in commit.files] if commit.files else [],
                        "additions": commit.stats.additions if commit.stats else 0,
                        "deletions": commit.stats.deletions if commit.stats else 0,
                    }
                }
                events.append(event)
            
            # Get releases since 'since'
            releases = repo.get_releases()
            for release in releases:
                # Skip if release is older than since
                release_date = release.published_at.replace(tzinfo=None) if release.published_at else None
                if release_date and release_date < since:
                    continue
                
                # If no published_at, use created_at
                if not release_date:
                    release_date = release.created_at.replace(tzinfo=None)
                    if release_date < since:
                        continue
                
                event = {
                    "event_id": f"github_release_{release.id}",
                    "timestamp": release_date.isoformat(),
                    "stream": "product_footprint",
                    "signal_type": "release",
                    "confidence": 0.98,
                    "content_raw": f"[{repo_name}] Release {release.title or release.tag_name}: {release.body[:200] if release.body else ''}",
                    "entities": ["Anthropic", repo_name.split('/')[1], release.tag_name],
                    "source_url": release.html_url,
                    "metadata": {
                        "tag_name": release.tag_name,
                        "release_name": release.title,
                        "release_body": release.body,
                        "repo": repo_name,
                        "prerelease": release.prerelease,
                    }
                }
                events.append(event)
                
        except GithubException as e:
            if e.status == 403 and "rate limit" in str(e).lower():
                logger.warning(f"GitHub rate limit exceeded for {repo_name}. Waiting for reset.")
                # In a real implementation, we would wait or use a backup token
                # For now, we'll return what we have and log the issue
            else:
                logger.error(f"GitHub API error for {repo_name}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error polling {repo_name}: {e}")
        
        return events

    def _poll_changelogs(self, since: datetime) -> List[Dict]:
        """
        Parse changelog pages for updates.
        """
        events = []
        
        for url in self.CHANGELOG_URLS:
            try:
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Look for changelog entries - this is site-specific
                # Anthropic's changelog uses entries with dates
                entries = soup.select('.changelog-entry, .release-note, .update-entry')
                
                for entry in entries:
                    # Try to extract date
                    date_elem = entry.select_one('time, .date, .timestamp')
                    date_str = date_elem.get('datetime') if date_elem and date_elem.has_attr('datetime') else None
                    if not date_elem:
                        date_elem = entry.select_one('[data-date]')
                        date_str = date_elem.get('data-date') if date_elem else None
                    
                    entry_date = None
                    if date_str:
                        try:
                            # Try parsing ISO format
                            entry_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        except:
                            try:
                                # Try other formats
                                entry_date = datetime.strptime(date_str, '%Y-%m-%d')
                            except:
                                pass
                    
                    # If we can't parse a date or it's too old, skip
                    if not entry_date or entry_date < since:
                        continue
                    
                    # Extract title and content
                    title_elem = entry.select_one('h3, h2, .title')
                    title = title_elem.get_text(strip=True) if title_elem else "Changelog update"
                    
                    content_elem = entry.select_one('.entry-content, .description, .body')
                    content = content_elem.get_text(strip=True) if content_elem else entry.get_text(strip=True)
                    
# Determine significance
                    text_to_check = (title + " " + content).lower()
                    significant = any(keyword in text_to_check for keyword in self.SIGNIFICANT_KEYWORDS)
                    confidence = 0.95 if significant else 0.85
                    
                    event = {
                        "event_id": f"changelog_{hash(url + title + str(entry_date))}",
                        "timestamp": entry_date.isoformat(),
                        "stream": "product_footprint",
                        "signal_type": "changelog",
                        "confidence": confidence,
                        "content_raw": f"{title}: {content[:200]}",
                        "entities": ["Anthropic"],
                        "source_url": url,
                        "metadata": {
                            "title": title,
                            "content": content,
                            "url": url
                        }
                    }
                    events.append(event)
                    
            except Exception as e:
                logger.error(f"Error polling changelog {url}: {e}")
                continue
        
        return events

    def _get_mock_repo_events(self, repo_name: str, since: datetime) -> List[Dict]:
        """
        Return mock events for development when GitHub is not available.
        """
        # This is just for testing - in production we want real data
        logger.info(f"Generating mock events for {repo_name}")
        return []

def run_continuous_polling(interval_seconds: int = 300):  # 5 minutes
    """
    Run continuous polling at the given interval.
    """
    scraper = ProductFootprintScraper()
    logger.info("Starting continuous polling for product footprint...")
    last_poll = datetime.utcnow() - timedelta(hours=1)  # Start by looking at last hour
    
    while True:
        try:
            events = scraper.poll(since=last_poll)
            if events:
                logger.info(f"Polled {len(events)} new product footprint events")
                # In a real system, we would save these to a database or message queue
                # For now, we just log
                for event in events[:5]:  # Log first 5
                    logger.info(f"  - {event['content_raw'][:100]}...")
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
    scraper = ProductFootprintScraper()
    events = scraper.poll()
    print(f"Found {len(events)} events")
    for event in events[:3]:
        print(f"- {event['content_raw']}")