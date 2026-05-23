#!/usr/bin/env python3
"""
GitHub releases scraper for Project Foresight.
Continuously monitors AI-related repositories for releases and commits.
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False

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

AI_REPOS = [
    "huggingface/transformers",
    "facebookresearch/llama",
    "mistralai/mistral-src",
    "google-deepmind/gemma",
    "microsoft/phi",
    "openai/gpt-4",
    "google-research/bert",
    "tiiuae/falcon",
    "stability-ai/stable-diffusion",
    "CompVis/stable-diffusion",
    "AUTOMATIC1111/stable-diffusion-webui",
    "oobabooga/text-generation-webui",
    "mlfoundations/open_lm",
    "mosaicml/llm-foundry",
    "lmsys/vicuna",
    "lmsys/fastchat",
    "bigscience-workshop/Megatron-DeepSpeed",
    "EleutherAI/gpt-neox",
    "google/flaxformer",
    "google/gemma",
    "ai21labs/ai21-studio-sdk",
    "writer-team/writer-sdk",
    "cohere/cohere-sdk-python",
    "anthropics/anthropic-sdk-python",
    "togethercomputer/OpenChatKit",
    "LAION-AI/Open-Assistant",
    "chatbotrenaissance/rwkv.cpp",
]

class GitHubReleasesScraper:
    def __init__(self, github_token: Optional[str] = None):
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        if not self.github_token:
            logger.warning("No GitHub token provided. Rate limits will be limited.")
        
        if GITHUB_AVAILABLE and self.github_token:
            self.github = Github(self.github_token)
        else:
            self.github = None

    def poll(self, since: Optional[datetime] = None) -> List[Dict]:
        if since is None:
            since = datetime.utcnow() - timedelta(days=30)
        
        events = []
        
        for repo_name in AI_REPOS:
            try:
                repo_events = self._poll_repo(repo_name, since)
                events.extend(repo_events)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Error polling repository {repo_name}: {e}")
                continue
        
        if KAFKA_AVAILABLE and producer:
            for event in events:
                try:
                    producer.send('tech_intel_stream', value=event)
                except Exception as e:
                    logger.error(f"Failed to send to Kafka: {e}")
        
        logger.info(f"Found {len(events)} new GitHub events since {since}")
        return events

    def _poll_repo(self, repo_name: str, since: datetime) -> List[Dict]:
        events = []
        
        if not self.github:
            return self._get_mock_events(repo_name, since)
        
        try:
            repo = self.github.get_repo(repo_name)
            
            releases = repo.get_releases()
            for release in releases:
                release_date = release.published_at.replace(tzinfo=None) if release.published_at else release.created_at.replace(tzinfo=None)
                if release_date < since:
                    continue
                
                event = {
                    "event_id": f"github_release_{release.id}",
                    "timestamp": release_date.isoformat(),
                    "stream": "product_footprint",
                    "signal_type": "model_release",
                    "confidence": 0.98,
                    "content_raw": f"[{repo_name}] Release {release.title or release.tag_name}: {release.body[:300] if release.body else ''}".strip(),
                    "entities": [repo_name.split('/')[0], repo_name.split('/')[1]],
                    "source_url": release.html_url,
                    "metadata": {
                        "tag_name": release.tag_name,
                        "release_name": release.title,
                        "repo": repo_name,
                        "prerelease": release.prerelease,
                    }
                }
                events.append(event)
            
            commits = repo.get_commits(since=since)
            count = 0
            for commit in commits:
                if count >= 10:
                    break
                count += 1
                commit_date = commit.commit.author.date.replace(tzinfo=None)
                message = commit.commit.message.strip().split('\n')[0][:100]
                
                event = {
                    "event_id": f"github_commit_{commit.sha}",
                    "timestamp": commit_date.isoformat(),
                    "stream": "product_footprint",
                    "signal_type": "commit",
                    "confidence": 0.95,
                    "content_raw": f"[{repo_name}] Commit: {message}",
                    "entities": [repo_name.split('/')[0], repo_name.split('/')[1]],
                    "source_url": commit.html_url,
                    "metadata": {
                        "sha": commit.sha[:7],
                        "repo": repo_name,
                    }
                }
                events.append(event)
                
        except Exception as e:
            logger.error(f"Error polling {repo_name}: {e}")
        
        return events

    def _get_mock_events(self, repo_name: str, since: datetime) -> List[Dict]:
        logger.info(f"Generating mock events for {repo_name}")
        return []


def run_continuous_polling(interval_seconds: int = 3600):
    scraper = GitHubReleasesScraper()
    logger.info("Starting continuous polling for GitHub releases...")
    last_poll = datetime.utcnow() - timedelta(hours=1)
    
    while True:
        try:
            events = scraper.poll(since=last_poll)
            if events:
                logger.info(f"Polled {len(events)} new GitHub events")
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
    scraper = GitHubReleasesScraper()
    events = scraper.poll()
    print(f"Found {len(events)} events")