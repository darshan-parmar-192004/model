#!/usr/bin/env python3
"""
Synthetic data generator for Project Foresight.
Generates realistic AI industry events for training.
"""

import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

EVENT_TEMPLATES = {
    "funding": {
        "templates": [
            "{company} ${amount}M Series {round} led by {investor}",
            "{company} raises ${amount}M in Series {round} funding",
            "{company} secures ${amount}M investment from {investor}",
            "{company} ${amount}M Series {round} funding round",
        ],
        "entities": ["OpenAI", "Anthropic", "Mistral", "Cohere", "AI21", "Stability AI", "Inflection", "xAI", "Groq", "Together", "Runway", "Character AI"],
        "investors": ["Sequoia", "Andreessen Horowitz", "Menlo Ventures", "Spark Capital", "Coatue", "Tiger Global", "SoftBank", "Microsoft", "Amazon", "Google Ventures", "NVIDIA"],
        "amounts": [50, 100, 150, 200, 250, 300, 350, 400, 450, 500, 580, 750, 1000, 1500, 2000, 2500, 5000, 10000],
        "rounds": ["A", "B", "C", "D", "E", "F"],
    },
    "hire": {
        "templates": [
            "{company} hires {person} as {title}",
            "{person} joins {company} as {title}",
            "{company} appoints {person} to {title} role",
            "{person} moves to {company} from {previous}",
        ],
        "entities": ["OpenAI", "Anthropic", "Google", "DeepMind", "Microsoft", "Meta", "Mistral", "Cohere", "NVIDIA", "Amazon"],
        "titles": ["CTO", "Chief Scientist", "VP of Research", "Head of AI", "Director of ML", "Research Lead", "AI Safety Lead"],
        "people": ["John Smith", "Jane Doe", "Alex Johnson", "Sam Wilson", "Dr. Lee", "Prof. Chen", "Dr. Martinez", "Dr. Kumar"],
        "previous": ["OpenAI", "DeepMind", "Google", "Stanford", "MIT", "Microsoft Research", "Meta AI"],
    },
    "model_release": {
        "templates": [
            "{company} releases {model} with {parameter} parameters",
            "{company} introduces {model}, a {capability} model",
            "{model} {version} launched by {company}",
            "{company} open-sources {model}",
        ],
        "entities": ["OpenAI", "Anthropic", "Google", "Mistral", "Cohere", "Meta", "Microsoft", "Stability AI", "Together"],
        "models": ["Claude 3", "Claude 2", "Claude 1.3", "GPT-5", "GPT-4.5", "Gemini 1.5", "Gemini Pro", "Llama 3", "Llama 2", "Mixtral", "Mistral-7B", "Command R+", "Gemma 2", "Phi-3", "OpenChat", "R1"],
        "parameters": ["7B", "8B", "13B", "34B", "70B", "72B", "100B", "200B", "1T"],
        "capabilities": ["multimodal", "instruction-following", "code-specialized", "long-context", "lightweight", "open-source", "reasoning-focused"],
        "versions": ["v1", "v2", "v3", "Turbo", "Preview", "Pro", "Ultra"],
    },
    "paper": {
        "templates": [
            "{authors} publish {title} on arXiv",
            "New paper: {title} from {organization}",
            "{organization} researchers release {title}",
        ],
        "organizations": ["OpenAI", "Anthropic", "DeepMind", "Google", "Meta", "Microsoft", "Stanford", "MIT", "Berkeley", "CMU"],
        "titles": [
            "Scaling Laws for Neural Language Models",
            "Constitutional AI: Harmlessness from AI Feedback",
            "Improving Mathematical Reasoning with Self-Verification",
            "Tool Use and Tool Creation in LLMs",
            "Mechanistic Interpretability of Neural Networks",
            "Sparse Autoencoders for Feature Discovery",
            "Constitutional AI: Safe and Helpful AI Assistants",
            "Tree of Thoughts: Deliberate Problem Solving with LLMs",
            "Chain-of-Verification Reduces Hallucination",
            "Self-RAG: Learning to Retrieve, Generate, and Critique",
            "RAG vs Fine-tuning: A Comprehensive Comparison",
            "Agent Tuning: Teaching LLMs to Use Tools",
        ],
    },
    "infra": {
        "templates": [
            "{company} announces {project} with {capacity} GPUs",
            "{company} deploys {count}x {gpu} GPUs for AI training",
            "New {location} data center by {company} for AI workloads",
            "{company} partners with {partner} on {project}",
        ],
        "entities": ["Google", "Microsoft", "Amazon", "Meta", "OpenAI", "Anthropic", "NVIDIA", "Oracle", "IBM"],
        "projects": ["Project Trillium", "Cirrus", "Nimbus", "Aurora", "Vulcan", "Titan"],
        "gpus": ["H100", "A100", "B100", "Blackwell", "Hopper", "Lovelace"],
        "capacities": ["10,000", "25,000", "50,000", "100,000", "200,000"],
        "partners": ["NVIDIA", "AMD", "Intel", "Graphcore", "Cerebras", "Groq"],
        "locations": ["Iowa", "Ohio", "Nevada", "Texas", "Oregon", "Sweden", "Singapore"],
    },
    "product": {
        "templates": [
            "{company} launches {product} API",
            "{product} now available from {company}",
            "{company} introduces {product} to {audience}",
        ],
        "entities": ["OpenAI", "Anthropic", "Google", "Microsoft", "Mistral", "Cohere", "Perplexity"],
        "products": ["ChatGPT", "Claude", "Gemini", "Copilot", "Assistant", "API v2", "Enterprise version"],
        "audiences": ["enterprise customers", "developers", "researchers", "general availability"],
    },
}


class SyntheticDataGenerator:
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
        
        self.company_categories = {
            "funding": ["OpenAI", "Anthropic", "Mistral", "Cohere", "AI21", "Stability AI", "Inflection", "xAI", "Groq"],
            "hire": ["OpenAI", "Google", "DeepMind", "Microsoft", "Meta", "Anthropic", "NVIDIA"],
            "model_release": ["OpenAI", "Anthropic", "Google", "Mistral", "Meta", "Cohere", "Stability AI"],
            "paper": ["OpenAI", "Anthropic", "DeepMind", "Google", "Meta", "Stanford", "MIT"],
            "infra": ["Google", "Microsoft", "Amazon", "Meta", "OpenAI", "NVIDIA"],
            "product": ["OpenAI", "Anthropic", "Google", "Microsoft"],
        }

    def generate_events(self, count: int, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> List[Dict]:
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.utcnow()
        
        events = []
        event_id_counter = 1000
        
        for _ in range(count):
            signal_type = random.choice(list(EVENT_TEMPLATES.keys()))
            template_data = EVENT_TEMPLATES[signal_type]
            
            event = self._generate_event(signal_type, template_data, event_id_counter)
            event["timestamp"] = self._random_timestamp(start_date, end_date)
            
            events.append(event)
            event_id_counter += 1
        
        events.sort(key=lambda x: x["timestamp"])
        return events

    def _generate_event(self, signal_type: str, template_data: Dict, event_id: int) -> Dict:
        template = random.choice(template_data["templates"])
        
        content = template.format(
            company=random.choice(template_data.get("entities", ["Company"])),
            amount=random.choice(template_data.get("amounts", [100])),
            round=random.choice(template_data.get("rounds", ["A"])),
            investor=random.choice(template_data.get("investors", ["VC Firm"])),
            person=random.choice(template_data.get("people", ["Person"])),
            title=random.choice(template_data.get("titles", ["Role"])),
            previous=random.choice(template_data.get("previous", ["Previous Company"])),
            model=random.choice(template_data.get("models", ["Model"])),
            parameter=random.choice(template_data.get("parameters", ["7B"])),
            capability=random.choice(template_data.get("capabilities", ["advanced"])),
            version=random.choice(template_data.get("versions", ["v1"])),
            authors=random.choice(template_data.get("authors", ["Researchers"])),
            authors_short=random.choice(template_data.get("authors", ["Researchers"])),
            organization=random.choice(template_data.get("organizations", ["Org"])),
            project=random.choice(template_data.get("projects", ["Project"])),
            count=random.choice(template_data.get("capacities", ["10,000"])),
            gpu=random.choice(template_data.get("gpus", ["H100"])),
            location=random.choice(template_data.get("locations", ["Data Center"])),
            product=random.choice(template_data.get("products", ["Product"])),
            audience=random.choice(template_data.get("audiences", [])),
            partner=random.choice(template_data.get("partners", ["Partner"])),
            capacity=random.choice(template_data.get("capacities", ["10,000"])),
        )
        
        return {
            "event_id": f"synth_{event_id:05d}",
            "timestamp": datetime.utcnow().isoformat(),
            "stream": self._get_stream(signal_type),
            "signal_type": signal_type,
            "confidence": round(random.uniform(0.85, 0.99), 2),
            "content_raw": content,
            "entities": [e for e in template_data.get("entities", []) if e in content][:3],
            "source_url": "https://synthetic.foresight.dev",
            "metadata": {
                "synthetic": True,
                "template_used": template,
            }
        }

    def _get_stream(self, signal_type: str) -> str:
        stream_map = {
            "funding": "macro",
            "hire": "macro",
            "model_release": "product_footprint",
            "paper": "research",
            "infra": "infra",
            "product": "product_footprint",
        }
        return stream_map.get(signal_type, "macro")

    def _random_timestamp(self, start_date: datetime, end_date: datetime) -> str:
        delta = end_date - start_date
        random_seconds = random.randint(0, int(delta.total_seconds()))
        ts = start_date + timedelta(seconds=random_seconds)
        return ts.isoformat() + "Z"


if __name__ == "__main__":
    generator = SyntheticDataGenerator(seed=42)
    events = generator.generate_events(1000)
    
    with open("synthetic_events.jsonl", "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
    
    print(f"Generated {len(events)} synthetic events")