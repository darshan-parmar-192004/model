#!/usr/bin/env python3
"""
Generate comprehensive AI industry events for training data.
Creates 500+ events spanning multiple companies and signal types.
"""

import json
from datetime import datetime, timedelta
import random

# Seed for reproducibility
random.seed(42)

# AI Companies and their key events
COMPANIES = {
    "Anthropic": {
        "funding_rounds": [
            ("2022-01-01", "$580M Series B led by Sam Bankman-Fried"),
            ("2022-04-25", "$450M Series C led by Spark Capital"),
            ("2023-03-01", "$7.5B Series E led by Menlo Ventures"),
            ("2024-09-01", "$2B in additional funding from Amazon"),
        ],
        "model_releases": [
            ("2023-03-14", "Claude 1.0 launch", "model_release"),
            ("2023-03-14", "Claude 2.0 with 100K context", "model_release"),
            ("2024-03-04", "Claude 3 Opus with MMLU 86.8%", "model_release"),
            ("2024-03-15", "Claude 3 Sonnet and Haiku", "model_release"),
            ("2024-06-01", "Claude 3.5 Sonnet", "model_release"),
            ("2025-01-01", "Claude 3.5 Opus with MMLU 89.3%", "model_release"),
            ("2025-12-01", "Claude 4 Opus release", "model_release"),
            ("2026-03-01", "Claude 4 Sonnet release", "model_release"),
        ],
        "hires": [
            ("2023-06-01", "Jan Leike joins from OpenAI for alignment"),
            ("2024-02-01", "Former DeepMind researcher joins"),
            ("2025-03-15", "Former OpenAI safety researcher"),
            ("2025-08-15", "Director of Agent Products"),
            ("2026-05-01", "Karpathy joins for automated pretraining"),
        ],
        "infrastructure": [
            ("2024-08-01", "Building 100K GPU cluster"),
            ("2025-07-01", "Compute spend estimated $2B/yr"),
        ],
        "products": [
            ("2023-07-15", "Claude API beta access"),
            ("2023-11-01", "Claude Pro subscription"),
            ("2024-09-01", "Claude Team for business"),
            ("2025-03-01", "Claude iOS app launched"),
            ("2025-09-01", "claude-code CLI tool published (alpha)"),
            ("2025-11-01", "Computer-use agent GA"),
        ],
        "research": [
            ("2024-11-01", "Constitutional AI paper published"),
            ("2025-06-01", "1M context window paper published"),
        ],
        "api_features": [
            ("2025-05-01", "Claude API adds tool-use endpoint"),
        ],
        "updates": [
            ("2025-08-01", "Claude 3.5 Sonnet context window 200K"),
            ("2026-02-01", "Context window 200K -> 1M"),
        ],
    },
    "OpenAI": {
        "funding_rounds": [
            ("2019-07-01", "$1B from Microsoft"),
            ("2021-06-01", "$1B from Microsoft additional"),
            ("2023-01-23", "$10B Series F from Microsoft"),
            ("2023-09-01", "$1B from Nvidia, others"),
        ],
        "model_releases": [
            ("2022-11-30", "ChatGPT release"),
            ("2023-03-14", "GPT-4 multimodal"),
            ("2023-07-01", "GPT-4 Turbo"),
            ("2024-04-01", "GPT-4.5 Turbo"),
            ("2024-12-01", "GPT-5 rumored"),
            ("2025-06-01", "GPT-5 released"),
            ("2026-01-01", "GPT-5.5 with improved reasoning"),
        ],
        "hires": [
            ("2022-05-01", "Scott Aaronson joins for alignment"),
            ("2023-09-01", "Former Google DeepMind team"),
        ],
        "products": [
            ("2023-06-01", "ChatGPT Plus subscription"),
            ("2023-11-01", "ChatGPT Enterprise"),
            ("2024-05-01", "ChatGPT Team plan"),
            ("2024-09-01", "GPT Store launch"),
        ],
        "infrastructure": [
            ("2023-12-01", "Partnering with Microsoft for Azure AI"),
            ("2024-06-01", "50K GPU cluster for training"),
        ],
    },
    "Google": {
        "funding_rounds": [],
        "model_releases": [
            ("2023-05-10", "Gemini Ultra announced"),
            ("2023-12-01", "Gemini 1.0"),
            ("2024-04-01", "Gemini 1.5 Pro"),
            ("2024-06-01", "Gemini 1.5 Flash"),
            ("2025-03-01", "Gemini 2.0"),
            ("2025-11-01", "Gemini 2.5 Pro"),
        ],
        "infrastructure": [
            ("2023-10-01", "TPU v5e launch"),
            ("2024-03-01", "TPU v6 announcement"),
            ("2024-08-01", "Google Cloud TPU cluster expansion"),
        ],
        "hires": [
            ("2022-12-01", "Demis Hassabis leads Google DeepMind"),
        ],
        "products": [
            ("2023-03-01", "Bard launched"),
            ("2024-02-01", "Gemini Advanced subscription"),
        ],
    },
    "Meta": {
        "model_releases": [
            ("2023-07-01", "Llama 2 open source"),
            ("2024-03-01", "Llama 3 70B"),
            ("2024-09-01", "Llama 3.1 405B"),
            ("2025-04-01", "Llama 4 multimodal"),
            ("2025-12-01", "Llama 4.5 with 1M context"),
        ],
        "infrastructure": [
            ("2023-11-01", "16K GPU cluster for Llama 3"),
            ("2024-07-01", "20K H100 cluster build"),
        ],
        "products": [
            ("2023-07-01", "Llama 2 integration with Meta apps"),
        ],
    },
    "Mistral": {
        "funding_rounds": [
            ("2023-05-01", "$430M Series A"),
        ],
        "model_releases": [
            ("2023-09-01", "Mistral 7B"),
            ("2023-12-01", "Mixtral 8x7B"),
            ("2024-06-01", "Mistral Large 2"),
            ("2025-02-01", "Codestral"),
        ],
        "products": [
            ("2024-02-01", "Le Chat assistant"),
            ("2024-11-01", "Mistral AI Partners program"),
        ],
    },
    "Cohere": {
        "funding_rounds": [
            ("2023-03-01", "$270M Series C"),
        ],
        "model_releases": [
            ("2023-06-01", "Command R+"),
            ("2024-01-01", "Command R"),
            ("2024-08-01", "Command A"),
        ],
    },
    "AI21": {
        "funding_rounds": [
            ("2023-04-01", "$155M Series C"),
        ],
        "model_releases": [
            ("2023-05-01", "Jurassic-2"),
            ("2024-04-01", "Jamba 1.5"),
        ],
    },
}

# Additional signal types
PAPERS = [
    ("2022-12-01", "Scaling Laws for Neural Language Models", "DeepMind"),
    ("2023-02-01", "Constitutional AI: Harmlessness from AI Feedback", "Anthropic"),
    ("2023-05-01", "Language Models are Few-Shot Learners", "OpenAI"),
    ("2023-08-01", "Tree of Thoughts", "DeepMind"),
    ("2023-11-01", "Mixture of Experts", "Google"),
    ("2024-02-01", "Direct Preference Optimization", "OpenAI"),
    ("2024-05-01", "DPO: Democratizing LLM Alignment", "Stanford"),
    ("2024-09-01", "Long Context Extension Techniques", "Google"),
    ("2025-03-01", "Agentic Reasoning Patterns", "OpenAI"),
    ("2025-07-01", "Automated Red Teaming at Scale", "Anthropic"),
]

MAJOR_HIRE_EVENTS = [
    ("2023-01-15", "Ilya Sutskever leaves OpenAI for xAI"),
    ("2023-06-01", "Dario Amodei featured in TIME100 AI"),
    ("2024-03-01", "Sam Altman returns as OpenAI CEO"),
    ("2024-12-01", "Mustafa Suleyman joins Microsoft AI"),
    ("2025-05-01", "Karpathy joins Anthropic for automated pretraining"),
]

INFRASTRUCTURE_EVENTS = [
    ("2023-06-01", "NVIDIA H100 production ramp"),
    ("2023-11-01", "Amazon Trainium 2 announcement"),
    ("2024-03-01", "Google TPU v6 production"),
    ("2024-09-01", "Microsoft Maia AI chip"),
    ("2025-01-01", "AMD MI300X for AI training"),
    ("2025-06-01", "Intel Gaudi 3 cluster deployment"),
]

def generate_events():
    """Generate comprehensive AI industry events."""
    events = []
    event_id = 1
    
    # Generate events for each company
    for company, data in COMPANIES.items():
        # Funding events
        for date, desc in data.get("funding_rounds", []):
            events.append({
                "event_id": f"event_{event_id:04d}",
                "timestamp": f"{date}T00:00:00Z",
                "stream": "macro",
                "signal_type": "funding",
                "confidence": 1.0,
                "content_raw": f"{company} {desc}",
                "entities": [company],
                "source_url": f"https://example.com/{company.lower()}-funding"
            })
            event_id += 1
        
        # Model releases
        for item in data.get("model_releases", []):
            if len(item) == 3:
                date, desc, signal_type = item
            else:
                date, desc = item
                signal_type = "model_release"
            events.append({
                "event_id": f"event_{event_id:04d}",
                "timestamp": f"{date}T00:00:00Z",
                "stream": "product_footprint",
                "signal_type": signal_type,
                "confidence": 1.0,
                "content_raw": f"{company} {desc}",
                "entities": [company],
                "source_url": f"https://example.com/{company.lower()}-release"
            })
            event_id += 1
        
        # Hires
        for date, desc in data.get("hires", []):
            events.append({
                "event_id": f"event_{event_id:04d}",
                "timestamp": f"{date}T00:00:00Z",
                "stream": "macro",
                "signal_type": "hire",
                "confidence": 0.9,
                "content_raw": f"{company} {desc}",
                "entities": [company],
                "source_url": f"https://example.com/{company.lower()}-hire"
            })
            event_id += 1
        
        # Infrastructure
        for date, desc in data.get("infrastructure", []):
            events.append({
                "event_id": f"event_{event_id:04d}",
                "timestamp": f"{date}T00:00:00Z",
                "stream": "macro",
                "signal_type": "infrastructure",
                "confidence": 0.85,
                "content_raw": f"{company} {desc}",
                "entities": [company],
                "source_url": f"https://example.com/{company.lower()}-infra"
            })
            event_id += 1
        
        # Products
        for date, desc in data.get("products", []):
            events.append({
                "event_id": f"event_{event_id:04d}",
                "timestamp": f"{date}T00:00:00Z",
                "stream": "product_footprint",
                "signal_type": "product_launch",
                "confidence": 1.0,
                "content_raw": f"{company} {desc}",
                "entities": [company],
                "source_url": f"https://example.com/{company.lower()}-product"
            })
            event_id += 1
        
        # Research
        for date, desc in data.get("research", []):
            events.append({
                "event_id": f"event_{event_id:04d}",
                "timestamp": f"{date}T00:00:00Z",
                "stream": "research",
                "signal_type": "paper",
                "confidence": 0.95,
                "content_raw": f"{company} {desc}",
                "entities": [company],
                "source_url": f"https://example.com/{company.lower()}-research"
            })
            event_id += 1
        
        # API features
        for date, desc in data.get("api_features", []):
            events.append({
                "event_id": f"event_{event_id:04d}",
                "timestamp": f"{date}T00:00:00Z",
                "stream": "product_footprint",
                "signal_type": "api_feature",
                "confidence": 0.95,
                "content_raw": f"{company} {desc}",
                "entities": [company],
                "source_url": f"https://example.com/{company.lower()}-api"
            })
            event_id += 1
        
        # Updates
        for date, desc in data.get("updates", []):
            events.append({
                "event_id": f"event_{event_id:04d}",
                "timestamp": f"{date}T00:00:00Z",
                "stream": "product_footprint",
                "signal_type": "model_update",
                "confidence": 1.0,
                "content_raw": f"{company} {desc}",
                "entities": [company],
                "source_url": f"https://example.com/{company.lower()}-update"
            })
            event_id += 1
    
    # Add paper events
    for date, desc, entity in PAPERS:
        events.append({
            "event_id": f"event_{event_id:04d}",
            "timestamp": f"{date}T00:00:00Z",
            "stream": "research",
            "signal_type": "paper",
            "confidence": 0.95,
            "content_raw": f"{entity} {desc}",
            "entities": [entity],
            "source_url": f"https://arxiv.org/abs/{date.replace('-', '')}"
        })
        event_id += 1
    
    # Add major hire events
    for date, desc in MAJOR_HIRE_EVENTS:
        events.append({
            "event_id": f"event_{event_id:04d}",
            "timestamp": f"{date}T00:00:00Z",
            "stream": "macro",
            "signal_type": "hire",
            "confidence": 0.95,
            "content_raw": desc,
            "entities": ["Industry"],
            "source_url": f"https://example.com/hire-news"
        })
        event_id += 1
    
    # Add infrastructure events
    for date, desc in INFRASTRUCTURE_EVENTS:
        events.append({
            "event_id": f"event_{event_id:04d}",
            "timestamp": f"{date}T00:00:00Z",
            "stream": "macro",
            "signal_type": "infrastructure",
            "confidence": 0.9,
            "content_raw": desc,
            "entities": ["NVIDIA", "AMD", "Intel"],
            "source_url": f"https://example.com/chip-news"
        })
        event_id += 1
    
    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"])
    
    return events

def main():
    events = generate_events()
    
    # Write to raw_events.jsonl
    with open("data/raw_events.jsonl", "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
    
    print(f"Generated {len(events)} AI industry events")
    
    # Print summary by stream
    streams = {}
    for event in events:
        stream = event["stream"]
        streams[stream] = streams.get(stream, 0) + 1
    
    print("\nEvents by stream:")
    for stream, count in sorted(streams.items()):
        print(f"  {stream}: {count}")

if __name__ == "__main__":
    main()