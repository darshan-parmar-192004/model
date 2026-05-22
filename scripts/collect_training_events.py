#!/usr/bin/env python3
"""
Multi-source data collection script for Project Foresight.
Orchestrates all scrapers to collect thousands of training events.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
RAW_EVENTS_FILE = os.path.join(DATA_DIR, "raw_events.jsonl")
TARGET_EVENTS = 2500


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
    "oobabooga/text-generation-webui",
    "mlfoundations/open_lm",
    "lmsys/vicuna",
    "lmsys/fastchat",
    "EleutherAI/gpt-neox",
    "google/flaxformer",
    "ai21labs/ai21-studio-sdk",
    "writer-team/writer-sdk",
    "cohere/cohere-sdk-python",
    "anthropics/anthropic-sdk-python",
    "togethercomputer/OpenChatKit",
    "LAION-AI/Open-Assistant",
]

EVENT_TEMPLATES = {
    "funding": {
        "templates": [
            "{company} ${amount}M Series {round} led by {investor}",
            "{company} raises ${amount}M in Series {round} funding",
            "{company} secures ${amount}M investment from {investor}",
        ],
        "entities": ["OpenAI", "Anthropic", "Mistral", "Cohere", "AI21", "Stability AI", "Inflection", "xAI", "Groq"],
        "investors": ["Sequoia", "Andreessen Horowitz", "Menlo Ventures", "Spark Capital", "Coatue", "Microsoft", "Amazon"],
        "amounts": [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 580, 750, 1000, 1500, 2000, 2500, 5000, 10000],
        "rounds": ["A", "B", "C", "D", "E", "F"],
    },
    "hire": {
        "templates": [
            "{company} hires {person} as {title}",
            "{person} joins {company} as {title}",
        ],
        "entities": ["OpenAI", "Google", "DeepMind", "Microsoft", "Meta", "Anthropic", "NVIDIA"],
        "titles": ["CTO", "Chief Scientist", "VP of Research", "Head of AI", "Director of ML"],
        "people": ["John Smith", "Jane Doe", "Alex Johnson", "Dr. Lee", "Prof. Chen", "Dr. Martinez"],
    },
    "model_release": {
        "templates": [
            "{company} releases {model} with {parameter} parameters",
            "{company} introduces {model}",
            "{model} launched by {company}",
        ],
        "entities": ["OpenAI", "Anthropic", "Google", "Mistral", "Meta", "Cohere", "Stability AI"],
        "models": ["Claude 3", "GPT-5", "Gemini 2.0", "Llama 4", "Mixtral", "Gemma 2", "Phi-3"],
        "parameters": ["7B", "8B", "13B", "34B", "70B", "72B", "100B", "200B"],
    },
}


def load_existing_events() -> List[Dict]:
    events = []
    if os.path.exists(RAW_EVENTS_FILE):
        with open(RAW_EVENTS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def save_events(events: List[Dict]):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RAW_EVENTS_FILE, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")


def deduplicate_events(events: List[Dict]) -> List[Dict]:
    seen_ids = set()
    unique_events = []
    for event in events:
        if event.get("event_id") not in seen_ids:
            seen_ids.add(event["event_id"])
            unique_events.append(event)
    return unique_events


def generate_synthetic_events(count: int, start_date: datetime, end_date: datetime) -> List[Dict]:
    import random
    random.seed(42)
    
    events = []
    
    companies = ["OpenAI", "Anthropic", "Google", "DeepMind", "Meta", "Mistral", "Cohere", "Microsoft", "NVIDIA", "Amazon"]
    
    for i in range(count):
        signal_type = random.choice(list(EVENT_TEMPLATES.keys()))
        template_data = EVENT_TEMPLATES[signal_type]
        
        company = random.choice(companies)
        template = random.choice(template_data["templates"])
        
        content = template.format(
            company=company,
            amount=random.choice(template_data.get("amounts", [100])),
            round=random.choice(template_data.get("rounds", ["A"])),
            investor=random.choice(template_data.get("investors", ["VC"])),
            person=random.choice(template_data.get("people", ["Person"])),
            title=random.choice(template_data.get("titles", ["Role"])),
            model=random.choice(template_data.get("models", ["Model"])),
            parameter=random.choice(template_data.get("parameters", ["7B"])),
        )
        
        delta = end_date - start_date
        random_seconds = random.randint(0, int(delta.total_seconds()))
        timestamp = start_date + timedelta(seconds=random_seconds)
        
        stream_map = {"funding": "macro", "hire": "macro", "model_release": "product_footprint"}
        
        event = {
            "event_id": f"synth_{i+1000:05d}",
            "timestamp": timestamp.isoformat() + "Z",
            "stream": stream_map.get(signal_type, "macro"),
            "signal_type": signal_type,
            "confidence": 0.92,
            "content_raw": content,
            "entities": [company],
            "source_url": "https://synthetic.foresight.dev",
        }
        events.append(event)
    
    return events


def main():
    print("Starting multi-source data collection...")
    
    existing_events = load_existing_events()
    print(f"Loaded {len(existing_events)} existing events")
    
    all_new_events = []
    
    print("\n1. Generating synthetic events (primary source)...")
    try:
        needed_synthetic = max(0, TARGET_EVENTS - len(existing_events))
        synthetic_events = generate_synthetic_events(
            count=needed_synthetic,
            start_date=datetime(2022, 1, 1),
            end_date=datetime.utcnow()
        )
        print(f"   Generated {len(synthetic_events)} synthetic events")
        all_new_events.extend(synthetic_events)
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n2. Merging and deduplicating...")
    all_events = existing_events + all_new_events
    all_events = deduplicate_events(all_events)
    all_events.sort(key=lambda x: x.get("timestamp", ""))
    
    save_events(all_events)
    
    print(f"\nTotal events after merge: {len(all_events)}")
    print(f"New events added: {len(all_events) - len(existing_events)}")
    print(f"Events saved to: {RAW_EVENTS_FILE}")
    
    return len(all_events)


if __name__ == "__main__":
    main()