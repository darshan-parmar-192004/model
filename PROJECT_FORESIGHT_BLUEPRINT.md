# Project Foresight: Technical Blueprint

## 1. Comprehensive Project Strategy & Scope

### 1.1 Core Thesis

A causal autoregressive transformer can be repurposed as a *time-series strategic forecasting engine* by training it on chronologically ordered sequences of structured and unstructured signals from the AI industry. The model learns to predict the next *state vector* of the competitive landscape (releases, capabilities, compute allocations, regulatory shifts, talent movements) given the current and past state vectors.

The key architectural insight: **Corporate strategy manifests as weakly periodic, signal-driven cycles** — hiring surges precede research shifts, compute procurement precedes scaling announcements, paper preprints precede product launches. An LLM's causal attention mechanism is naturally suited to model these delayed dependencies.

### 1.2 Primary Target Prediction Classes

| Prediction Class | Examples | Signal Horizon | Evaluation Metric |
|---|---|---|---|
| **Release Timing** | Claude 4 Opus/Sonnet/Haiku dates, multimodal API GA, computer-use agent GA | 3-12 months | Precision@K, MAE (days) |
| **Capability Step-Change** | Context window jumps (200K → 1M+), benchmark score vectors (MMLU, SWE-bench, MATH), multi-agent orchestration frameworks | 1-6 months | Directional Accuracy, Kendall's Tau |
| **Compute Scaling** | Training FLOP budgets, cluster sizes (10K → 100K+ GPUs), infrastructure partnerships | 2-18 months | Log-MAPE, Brier Score |
| **Talent Acquisition** | Strategic hires, team formations, departures | 0-6 months | Precision@K, Recall@K |
| **Regulatory/Govt** | Executive orders, EU AI Act amendments, NIST framework updates | 3-24 months | Brier Score |

### 1.3 Leading Indicator Analysis: The Karpathy Signal

Andrej Karpathy's transition to lead an automated pretraining research team at Anthropic in May 2026 is a **high-information-density event** that cascades across multiple prediction axes:

```
Signal Decomposition:
├── Personal Signal: Karpathy leaves OpenAI → joins Anthropic
│   └── Implies: Anthropic offered superior research autonomy, compute resources,
│       and strategic alignment
├── Role Signal: "Lead team automating pretraining research"
│   ├── Anthropic is investing in recursive self-improvement pipelines
│   ├── Pretraining research is becoming automatable via LLM-guided search
│   └── Implies Claude itself is being used to design better versions of itself
│       (a form of algorithmic alignment or AI-assisted architecture search)
└── Timing Signal: Mid-2026
    └── Suggests: Anticipate automated pretraining results → Claude 5 or
        Claude 4.5 series in late 2026 / early 2027
```

**Predictive mappings derived from this hire:**

1. *Compute demand inflection*: Within 3 months of hire → 2x compute procurement (automated search requires orders of magnitude more FLOPs)
2. *Paper emergence*: 4-6 months post-hire → ArXiv preprint on "LLM-Directed Neural Architecture Search" or "Automated Pretraining via Reward Modeling"
3. *Release acceleration*: 8-14 months → Claude model with automated-pretraining-derived improvements (benchmark deltas > 2x typical iteration)
4. *Talent cascade*: 2-6 months → Poaching of AutoML/neuro-evolution researchers from Google DeepMind, Meta, and OpenAI

The Foresight model must learn this pattern: **high-profile hires in specific roles → predictable downstream compute, research, and product events** with quantifiable lead-lag correlations.

---

## 2. Multi-Stream Real-Time Data Ingestion Pipeline

### 2.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                   │
├────────────┬────────────┬────────────┬───────────────────┤
│ Research   │ Infra      │ Product    │ Macro             │
│ Scraper    │ Scraper    │ Footprint  │ Signal            │
│            │            │ Scraper    │ Scraper           │
├────────────┼────────────┼────────────┼───────────────────┤
│ ArXiv API  │ CloudWatch │ GitHub API │ LinkedIn API      │
│ OpenReview │ AWS Cost   │ Docs CI    │ SEC EDGAR         │
│ Semantic   │ Latency    │ Changelog  │ Crunchbase        │
│ Scholar    │ Graphs     │ Parsers    │ GovTrack          │
├────────────┴────────────┴────────────┴───────────────────┤
│                    STREAMING QUEUE (Kafka / Pulsar)        │
├───────────────────────────────────────────────────────────┤
│              FEATURE STORE (Redis + PostgreSQL)            │
│         Dedup, normalize, timestamp, embed (text → vec)   │
└───────────────────────────────────────────────────────────┘
```

### 2.2 Stream 1: Research & Literature Scraping

```python
# research_scraper.py — Stub for continuous ArXiv/OpenReview ingestion

import arxiv
import openreview
from datetime import datetime, timedelta
from typing import List, Dict
import json
from kafka import KafkaProducer

ANTHROPIC_AFFILIATIONS = ["Anthropic", "Anthropic AI"]
TARGET_AUTHORS = [
    "Dario Amodei", "Tom Brown", "Jared Kaplan", "Jack Clark",
    "Amanda Askell", "Yuntao Bai", "Sam McCandlish",
    # Dynamic: updated weekly from talent tracking
]
TARGET_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "stat.ML"]
KEYWORD_FILTERS = [
    "constitutional AI", "RLHF", "pretraining", "scaling law",
    "agent", "tool use", "computer use", "automated red teaming",
    "mechanistic interpretability", "safety", "alignment",
]

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def poll_arxiv(last_poll: datetime) -> List[Dict]:
    search = arxiv.Search(
        query=" AND ".join(f"cat:{cat}" for cat in TARGET_CATEGORIES),
        max_results=500,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    papers = []
    for result in search.results():
        if result.published < last_poll:
            continue
        if any(auth in str(result.authors) for auth in TARGET_AUTHORS):
            papers.append({
                "id": result.entry_id,
                "title": result.title,
                "authors": [str(a) for a in result.authors],
                "abstract": result.summary,
                "categories": result.categories,
                "published": result.published.isoformat(),
                "stream": "research",
                "signal_type": "paper",
            })
    return papers

def poll_openreview(last_poll: datetime) -> List[Dict]:
    # OpenReview API v2 client
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')
    submissions = client.get_all_notes(
        invitation='*/-/Submission',
        details='original'
    )
    papers = []
    for note in submissions:
        # Filter by affiliation matching or keyword matching
        if any(kw.lower() in (note.content.get('title','') + 
                              note.content.get('abstract','')).lower() 
               for kw in KEYWORD_FILTERS):
            papers.append({
                "id": note.id,
                "title": note.content.get('title'),
                "authors": note.content.get('authors', []),
                "abstract": note.content.get('abstract'),
                "published": note.cdate,
                "stream": "research",
                "signal_type": "openreview",
            })
    return papers

# Run on 1-hour cron / event-driven schedule
for paper in poll_arxiv(datetime.utcnow() - timedelta(hours=1)):
    producer.send('tech_intel_stream', value=paper)
```

### 2.3 Stream 2: Technical Infrastructure Metrics

Data sources and scrape targets:

| Source | Data Collected | Frequency | Access Method |
|---|---|---|---|
| **AWS Cost & Usage Reports** | Compute spend trends, GPU instance utilization, reserved instance counts | Daily | AWS Cost Explorer API (configurable billing role) |
| **Google Cloud Pricing API** | TPU v5p/v6 availability, spot pricing history | Weekly | GCP API |
| **Cloud Vendor Supercomputer Announcements** | Cluster sizes, GPU counts, interconnect type (NVLink, InfiniBand) | Event-driven | RSS + press release parsers |
| **CoreWeave / Lambda / Paperspace** | Spot GPU pricing curves, availability zones | Daily | API + scraping |
| **NVIDIA Earnings Calls** | Data Center revenue guidance, Hopper/Blackwell shipment volumes | Quarterly | SEC EDGAR + transcript parsers |
| **Electricity Maps / EIA** | Data center power capacity by region | Monthly | API |

**Key derived metric**: *Estimated Training FLOP Budget*

```
Training FLOP Budget = f(cluster_gpu_count, gpu_type_flops, training_duration, utilization_rate)
```

Compute an estimated trajectory from public signals. This is a critical input feature.

### 2.4 Stream 3: Code & Product Footprints

```python
# product_footprint_scraper.py — Stub

from github import Github
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
TARGET_REPOS = [
    "anthropics/anthropic-cookbook",
    "anthropics/claude-code",
    "anthropics/claude-api-docs",
    "anthropics/evals",
]

CHANGELOG_URLS = [
    "https://docs.anthropic.com/en/docs/changelog",
    "https://docs.anthropic.com/en/api/getting-started",
]

def monitor_github_repos():
    g = Github(GITHUB_TOKEN)
    for repo_name in TARGET_REPOS:
        repo = g.get_repo(repo_name)
        commits = repo.get_commits(since=datetime.utcnow() - timedelta(hours=6))
        for commit in commits:
            yield {
                "type": "commit",
                "repo": repo_name,
                "sha": commit.sha,
                "message": commit.commit.message,
                "author": str(commit.commit.author),
                "date": commit.commit.author.date.isoformat(),
                "files_changed": commit.files if commit.files else [],
                "stats": commit.stats,
                "stream": "product_footprint",
            }

def parse_changelogs():
    for url in CHANGELOG_URLS:
        resp = requests.get(url)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for entry in soup.select('.changelog-entry'):
            yield {
                "type": "changelog",
                "source": url,
                "title": entry.select_one('h3').text.strip(),
                "body": entry.select_one('.entry-content').text.strip(),
                "date": entry.select_one('time').get('datetime'),
                "stream": "product_footprint",
            }
```

**Critical signals extracted**:

- New API endpoints (especially `computer_use`, `tool_use`, `agent_mode`)
- Context window limits changing in API docs
- Rate limit tiers (free → paid → enterprise)
- Model ID strings (claude-3-opus → claude-4-opus → claude-4-opus-2026xxxx)

### 2.5 Stream 4: Macro Corporate Signals

| Source | Signal Type | Method |
|---|---|---|
| **LinkedIn API** | Talent migration (lateral hires, departures, role changes) | Scraping + People Data Labs API |
| **SEC EDGAR** | Funding rounds, valuation, insider transactions | `sec-api.io` + manual parsing |
| **Crunchbase / PitchBook** | Investment rounds, acqui-hires, SPVs | API |
| **GovTrack / Congress.gov** | AI legislation status, executive orders | RSS + text parsers |
| **News RSS** | General news sentiment, pressure, leaks | GDELT Project API + NewsCatcher |
| **Glassdoor / Levels.fyi** | Compensation trends, team size estimates | Scraping (rate-limited) |

**Talent flow graph construction**:

```python
# Build a directed graph of talent movement between labs
# Nodes = researchers/engineers (anonymized hash)
# Edges = employer transitions with timestamps
# Edge features: role, seniority, team, prior papers with employer

import networkx as nx

HISTORICAL_INFLOWS = {
    "Anthropic": [3.2, 4.1, 5.0, 2.8, 3.5],
    "OpenAI": [6.2, 5.8, 7.1, 4.9, 5.5],
    "Google DeepMind": [4.5, 3.9, 5.2, 4.0, 4.8],
    "Meta AI": [2.5, 3.0, 2.2, 1.8, 2.7],
}

TALENT_GRAPH = nx.DiGraph()
TALENT_GRAPH.add_edge("Researcher_A", "Anthropic", role="senior", timestamp=datetime(2026, 3, 1))
TALENT_GRAPH.add_edge("Researcher_B", "Anthropic", role="scientist", timestamp=datetime(2026, 4, 15))
TALENT_GRAPH.add_edge("Researcher_C", "OpenAI", role="engineer", timestamp=datetime(2026, 2, 1))
TALENT_GRAPH.add_edge("Researcher_D", "Anthropic", role="senior", timestamp=datetime(2026, 5, 1))


def load_talent_graph() -> nx.DiGraph:
    """Load and return the talent movement graph (built from LinkedIn/People Data Labs)."""
    return TALENT_GRAPH


def compute_talent_inflow(lab_name: str, window_days: int = 180) -> float:
    """Compute weighted talent inflow score for a target lab.

    Weights: senior researcher = 3.0, research scientist = 2.0,
    engineer = 1.0, intern = 0.5. Returns z-score normalized
    inflow magnitude used as model feature.
    """
    talent_graph = load_talent_graph()
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    inflow_score = 0.0
    for edge in talent_graph.edges(data=True):
        src, dst, attrs = edge
        if dst == lab_name and attrs.get("timestamp", datetime.min) > cutoff:
            weight = {"senior": 3.0, "scientist": 2.0, "engineer": 1.0, "intern": 0.5}
            inflow_score += weight.get(attrs.get("role", "engineer"), 1.0)
    mean = np.mean(HISTORICAL_INFLOWS.get(lab_name, [0]))
    std = np.std(HISTORICAL_INFLOWS.get(lab_name, [1])) or 1.0
    return (inflow_score - mean) / std
```

---

## 3. Data Preparation, Labelling, and Temporal Formatting

### 3.1 Unification Schema

All streaming events are normalized to a common schema:

```json
{
  "event_id": "sha256(content + timestamp)",
  "timestamp": "2026-03-15T14:30:00Z",
  "stream": "research|infra|product|macro",
  "signal_type": "paper|commit|hire|changelog|compute_announcement|regulation",
  "confidence": 0.0-1.0,
  "content_raw": "...",
  "content_embedding": [0.123, -0.456, ...],
  "entities": ["Anthropic", "Claude-4", "Karpathy"],
  "relations": [{"subject": "Karpathy", "predicate": "joins", "object": "Anthropic"}],
  "source_url": "...",
  "processed_features": {}
}
```

### 3.2 Temporal Causal Sequencing

Each training example is a *structured timeline slice*:

```
Example: Predict Claude 4 announcement (Dec 2025) from signals available up to Sep 2025

INPUT PROMPT:
[SYSTEM]
You are Foresight, a predictive model forecasting AI industry events.
Given the following timeline of observations, predict the events 
that will occur in the next 3 months.

[TIMELINE: 2024-01 to 2025-09]

### Compute Indicators
2024-03: Anthropic announces $7.5B Series E
2024-06: Claude 3.5 Sonnet released
2024-08: Anthropic reportedly building 100K GPU cluster
2025-01: Claude 3.5 Opus released (benchmark: MMLU 89.3%, HumanEval 92.1%)
2025-03: Anthropic hires former OpenAI safety researcher
2025-05: Claude API adds tool-use endpoint (beta)
2025-07: Compute spend estimated at $2B/yr
2025-08: ArXiv paper: "Scaling Multi-Turn Agent Evaluation"
2025-09: Claude 3.5 Sonnet context window expanded to 200K

### Research Signals
2024-11: "Constitutional AI: Harmlessness from AI Feedback" (Anthropic)
2025-02: "Training a Helpful and Harmless Assistant from Human Feedback" (Anthropic)
2025-06: "Extending Context Windows to 1M Tokens" (Anthropic)
2025-08: "Agentic Evaluations: Measuring Tool-Use Capabilities" (Anthropic)

### Hiring Signals
2024-12: 15 new safety researchers hired
2025-04: VP of Infrastructure hired from Google Cloud
2025-07: Director of Agent Products hired
2025-08: 30+ infrastructure engineers posted on LinkedIn

### Product Signals
2025-03: Claude iOS app launched
2025-06: Claude API rate limits increased 10x for paid tier
2025-08: claude-code CLI tool published (alpha)

TARGET OUTPUT:
{
  "predictions": [
    {
      "event_type": "model_release",
      "model_name": "Claude 4 Opus",
      "predicted_date": "2025-12",
      "confidence": 0.78,
      "key_capabilities": [
        "context_window_1M",
        "computer_use_agent",
        "swe_bench_70_percent",
        "multimodal_video_understanding"
      ]
    },
    {
      "event_type": "api_feature",
      "feature": "computer_use_agent_api_ga",
      "predicted_date": "2025-11",
      "confidence": 0.85
    },
    {
      "event_type": "compute_announcement",
      "description": "50K GPU cluster expansion",
      "predicted_date": "2025-10",
      "confidence": 0.65
    }
  ]
}
```

### 3.3 Dataset Construction Pipeline

```python
# dataset_builder.py — Stub

import pandas as pd
from typing import List, Tuple, Dict
import numpy as np
from datetime import datetime, timedelta

class TemporalDatasetBuilder:
    def __init__(self, events: List[Dict], window_size_days: int = 180):
        self.events = sorted(events, key=lambda e: e['timestamp'])
        self.window = timedelta(days=window_size_days)

    def create_training_sequences(
        self,
        lookback_days: int = 365 * 2,      # 2 years context
        forecast_horizons: List[int] = [30, 90, 180],  # 1, 3, 6 months
    ) -> List[Dict]:
        """Create (input_context, target_events) pairs."""
        sequences = []
        event_df = pd.DataFrame(self.events)

        for cutoff_idx in range(len(self.events)):
            cutoff_date = self.events[cutoff_idx]['timestamp']

            # Block: use only events up to cutoff_date
            past_mask = event_df['timestamp'] <= cutoff_date
            past_events = event_df[past_mask]

            # Need minimum history
            if len(past_events) < 100:
                continue

            for horizon in forecast_horizons:
                future_date = cutoff_date + timedelta(days=horizon)
                future_mask = (
                    (event_df['timestamp'] > cutoff_date) &
                    (event_df['timestamp'] <= future_date)
                )
                future_events = event_df[future_mask]

                if len(future_events) == 0:
                    continue  # Skip empty future windows

                sequences.append({
                    "input_cutoff": cutoff_date.isoformat(),
                    "lookback_start": (cutoff_date - timedelta(days=lookback_days)).isoformat(),
                    "past_events_count": len(past_events),
                    "future_window_days": horizon,
                    "future_events_count": len(future_events),
                    "past_events": past_events.to_dict('records'),
                    "future_events": future_events.to_dict('records'),
                })

        return sequences

    def tokenize_sequence(self, seq: Dict, tokenizer) -> Dict:
        """Convert a temporal sequence into model input/output tokens."""

        context_str = self._build_context_string(seq['past_events'])
        target_str = self._build_target_string(seq['future_events'])

        # Format in chat template
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context_str},
            {"role": "assistant", "content": target_str},
        ]

        tokenized = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=False,
            return_tensors="pt",
        )

        return {
            "input_ids": tokenized[:, :-1],  # Everything except last token
            "labels": tokenized[:, 1:],       # Shifted for next-token prediction
            "mask": self._create_loss_mask(tokenized, target_tokens=target_str, tokenizer=tokenizer),
            "metadata": {
                "cutoff_date": seq['input_cutoff'],
                "horizon_days": seq['future_window_days'],
            }
        }

    def _build_context_string(self, past_events: List[Dict]) -> str:
        """Structured timeline format."""
        sections = {"compute": [], "research": [], "product": [], "hiring": []}
        stream_map = {
            "infra": "compute", "research": "research",
            "product_footprint": "product", "macro": "hiring",
        }
        for ev in past_events:
            key = stream_map.get(ev.get("stream", ""), "research")
            ts = ev.get("timestamp", "unknown")[:10]
            content = ev.get("content_raw", ev.get("title", str(ev)))
            sections[key].append(f"{ts}: {content}")
        parts = []
        for section_name, events in sections.items():
            if events:
                header = section_name.capitalize()
                parts.append(f"### {header} Indicators")
                parts.extend(events)
        return "\n".join(parts)

    def _build_target_string(self, future_events: List[Dict]) -> str:
        """Build structured target string from future events."""
        lines = ["PREDICTED EVENTS:"]
        for ev in future_events:
            ts = ev.get("timestamp", "unknown")[:10]
            desc = ev.get("content_raw", ev.get("title", str(ev)))
            event_type = ev.get("signal_type", "event")
            lines.append(f"  - [{ts}] ({event_type}) {desc}")
        return "\n".join(lines)

    def _create_loss_mask(self, tokenized, target_tokens: str, tokenizer) -> torch.Tensor:
        """Zero out loss for non-target (context) tokens so model only learns from predictions."""
        import torch
        target_ids = tokenizer.encode(target_tokens, add_special_tokens=False)
        seq_len = tokenized.shape[1]
        mask = torch.zeros(seq_len, dtype=torch.bool)
        target_len = len(target_ids)
        if target_len > 0 and target_len <= seq_len:
            mask[-target_len:] = True
        return mask
```

### 3.4 Augmentation Strategy

| Technique | Description | Rationale |
|---|---|---|
| **Temporal Jitter** | Shift all timestamps by ±5% | Prevent overfitting to exact dates |
| **Signal Dropout** | Randomly mask 10% of input events | Force robustness to partial information |
| **Lead-Acceleration** | Create synthetic sequences with compressed timelines | Model learns from analogous historical patterns |
| **Counterfactual** | Generate "what if" sequences (e.g., what if Karpathy had joined in 2024 instead) | Improves causal reasoning |

---

## 4. LLM Architecture, Fine-Tuning, and Training Methodology

### 4.1 Base Model Selection

**Recommended choice**: Fine-tune **Llama-3.1-70B** with custom architecture modifications.

Rationale:
- Open weights allow full architectural control
- 128K native context window (expandable to 256K+ via YaRN/LongRoPE)
- Strong baseline for structured reasoning
- Extensive tooling ecosystem (FSDP, vLLM, SGLang)

**Architecture modifications for Foresight**:

```
Base Llama-3.1-70B
├── Input Embeddings (unchanged, 8192 vocab)
├── 80 Transformer Layers
│   ├── RMSNorm + RoPE (context extend to 256K)
│   ├── GQA (8 KV heads)
│   ├── SwiGLU FFN
│   └── [NEW] Temporal Position Encoding Adapter
│       └── Learns to weight recent events > distant events
├── [NEW] Mixture of Prediction Heads
│   ├── Release Timing Head
│   ├── Capability Vector Head
│   ├── Compute Budget Head
│   └── Talent Movement Head
└── Output Projection (shared embedding)
```

### 4.2 Training Regimen

**Phase 1: Long-Context Continual Pretraining (optional, compute-permitting)**

If budget allows, extend pretraining on a corpus of ~50B tokens of time-series formatted data:
- Financial filings (10-K/10-Q text)
- Tech press releases (2000-2026)
- ArXiv chronology
- GitHub commit logs (public repos)

This normalizes the distribution of temporal industry data into the model's weights.

**Phase 2: Supervised Fine-Tuning (SFT)**

```
Training Configuration:
├── Base model: Llama-3.1-70B (or Qwen2.5-72B for better reasoning)
├── Method: QLoRA (Quantized Low-Rank Adaptation)
│   ├── r: 64
│   ├── lora_alpha: 128
│   ├── lora_dropout: 0.1
│   ├── target_modules: ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
│   └── quantize_base: 4-bit NF4 (NormalFloat4)
├── Batch size: 128 (gradient accumulation steps)
├── Learning rate: 2e-4 (cosine schedule with 3% warmup)
├── Optimizer: paged_adamw_8bit
├── Context length: 131072 (128K tokens)
├── Gradient checkpointing: enabled
├── Flash Attention 2: enabled
├── Training epochs: 3
└── Loss: next-token prediction on target portion only (loss masking)
```

```python
# training_config.py — Fine-tuning configuration stub

from transformers import (
    AutoModelForCausalLM, AutoTokenizer,
    TrainingArguments, BitsAndBytesConfig
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

model_id = "meta-llama/Meta-Llama-3.1-70B"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype="bfloat16",
)

lora_config = LoraConfig(
    r=64,
    lora_alpha=128,
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ],
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM",
)

training_args = TrainingArguments(
    output_dir="./foresight-v1",
    per_device_train_batch_size=2,        # Per GPU
    gradient_accumulation_steps=64,        # Effective batch = 128
    num_train_epochs=3,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=10,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=5,
    bf16=True,
    gradient_checkpointing=True,
    max_grad_norm=1.0,
    optim="paged_adamw_8bit",
    remove_unused_columns=False,
    dataloader_num_workers=8,
    ddp_find_unused_parameters=False,
    report_to="wandb",
    # Long context support
    model_max_length=131072,
    gradient_checkpointing_kwargs={"use_reentrant": False},
)
```

**Phase 3: Prediction-Head Tuning (optional)**

For structured forecasting outputs (timelines, metrics), add lightweight linear heads:

```python
class ForesightPredictionHeads(nn.Module):
    def __init__(self, hidden_size=8192):
        super().__init__()
        self.release_timing = nn.Sequential(
            nn.Linear(hidden_size, 1024),
            nn.GELU(),
            nn.Linear(1024, 1),  # Days from now
        )
        self.capability_vector = nn.Sequential(
            nn.Linear(hidden_size, 2048),
            nn.GELU(),
            nn.Linear(2048, 50),  # Benchmark scores
        )
        self.compute_budget = nn.Sequential(
            nn.Linear(hidden_size, 512),
            nn.GELU(),
            nn.Linear(512, 1),   # Log(FLOPs)
        )

    def forward(self, hidden_states):
        # Take representation from the last token of the context
        context_repr = hidden_states[:, -1, :]
        return {
            "release_timing": self.release_timing(context_repr),
            "capability_vector": self.capability_vector(context_repr),
            "compute_budget": self.compute_budget(context_repr),
        }
```

These heads are trained with task-specific losses (MSE for regressions, cross-entropy for categorical), weighted and combined via uncertainty weighting.

### 4.3 Inference Optimization

```yaml
# foresight_serve.yaml — vLLM deployment config
model: ./foresight-v1/final
served_model_name: foresight
max_model_len: 262144  # 256K context
tensor_parallel_size: 8  # 8 GPUs
gpu_memory_utilization: 0.90
trust_remote_code: true

# Prediction mode
guided_decoding:
  type: json
  schema: |
    {
      "type": "object",
      "properties": {
        "predictions": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "event_type": {"type": "string"},
              "predicted_date": {"type": "string", "format": "date"},
              "confidence": {"type": "number", "minimum": 0, "maximum": 1},
              "reasoning": {"type": "string"}
            }
          }
        }
      }
    }
```

---

## 5. Rigorous Backtesting, Testing Matrix, and Evaluation

### 5.1 Historical Backtesting Framework

The gold standard: train on data up to a historical cutoff, then evaluate predictions against known outcomes.

```
┌───────────────────────────────────────────────────┐
│                BACKTESTING PIPELINE                 │
├───────────────────────────────────────────────────┤
│ 1. Sliding Window Training                         │
│    Train on data ending 2024-12-31                 │
│    └── Test: Predict 2025-Q1 through 2026-Q2       │
│                                                     │
│ 2. Point-in-Time Evaluation                        │
│    For each month in [2025-01, 2026-06]:           │
│      └── Generate predictions using only           │
│          information available at that time         │
│                                                     │
│ 3. Ground Truth Matching                           │
│    └── Compare predictions against actual           │
│        events (pre-built holdout dataset)           │
│                                                     │
│ 4. Metric Computation                              │
│    └── Precision@K, Recall@K, MAE, Brier Score     │
└───────────────────────────────────────────────────┘
```

**Implementation**:

```python
# backtest_runner.py — Stub

class BacktestEngine:
    def __init__(self, model, tokenizer, event_db):
        self.model = model
        self.tokenizer = tokenizer
        self.event_db = event_db  # All events with timestamps

    def sliding_window_eval(
        self,
        train_cutoffs: List[datetime],
        eval_horizons: List[int] = [30, 90, 180],
    ):
        """Run multiple backtest experiments with different training cutoffs."""
        results = []

        for cutoff in train_cutoffs:
            # Split: train = events before cutoff, test = events after cutoff
            train_events = self.event_db.query(end_date=cutoff)
            test_events = self.event_db.query(
                start_date=cutoff,
                end_date=cutoff + timedelta(days=max(eval_horizons))
            )

            # Fine-tune on train_events (or use adapter for efficiency)
            # adapter = train_qlora(train_events, base_model)

            for horizon in eval_horizons:
                preds = self.generate_predictions(
                    context=train_events,
                    horizon=horizon,
                )
                metrics = self.compute_metrics(preds, test_events, horizon)
                results.append({
                    "cutoff": cutoff.isoformat(),
                    "horizon": horizon,
                    **metrics,
                })

        return pd.DataFrame(results)

    def generate_predictions(
        self,
        context: List[Dict],
        horizon: int,
    ) -> List[Dict]:
        """Generate structured predictions from context."""
        from ..data.schema import build_context_string
        context_str = build_context_string(context)
        prompt = self._build_forecast_prompt(context_str, horizon_days=horizon)
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=131072)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1024,
                temperature=0.1,
                do_sample=True,
                num_return_sequences=5,
            )

        return self._parse_forecasts(outputs)

    def _build_forecast_prompt(self, context_str: str, horizon_days: int) -> str:
        system = (
            "You are Foresight, a predictive model forecasting AI industry events. "
            f"Given the following timeline of observations, predict the events "
            f"that will occur in the next {horizon_days} days. "
            "Respond with a JSON object containing a 'predictions' array."
        )
        return self.tokenizer.apply_chat_template([
            {"role": "system", "content": system},
            {"role": "user", "content": context_str},
        ], tokenize=False, add_generation_prompt=True)

    def _parse_forecasts(self, outputs) -> List[Dict]:
        import json
        from collections import defaultdict
        responses = [self.tokenizer.decode(o, skip_special_tokens=True) for o in outputs]
        ensemble = defaultdict(list)
        for resp in responses:
            start, end = resp.find('{'), resp.rfind('}')
            if start >= 0 and end > start:
                data = json.loads(resp[start:end+1])
                for pred in data.get("predictions", []):
                    key = f"{pred.get('event_type','')}::{pred.get('predicted_date','')}"
                    ensemble[key].append(pred)
        result = []
        for key, preds in ensemble.items():
            confs = [p.get("confidence", 0.0) for p in preds if isinstance(p.get("confidence"), (int, float))]
            result.append({
                "event_type": key.split("::")[0],
                "predicted_date": key.split("::")[1],
                "confidence": round(sum(confs) / len(confs), 3) if confs else 0.0,
                "consensus_ratio": len(preds) / len(responses),
            })
        return sorted(result, key=lambda x: x["confidence"], reverse=True)

    def compute_metrics(self, predictions, ground_truth, horizon):
        from .metrics import precision_at_k, recall_at_k, temporal_brier_score
        from .metrics import directional_accuracy, date_mae
        pred_events = [p for p in predictions if p.get('event_type')]
        return {
            "precision_at_1": precision_at_k(pred_events, ground_truth, k=1),
            "precision_at_3": precision_at_k(pred_events, ground_truth, k=3),
            "recall_at_k": recall_at_k(pred_events, ground_truth),
            "temporal_brier": temporal_brier_score(pred_events, ground_truth, horizon),
            "directional_accuracy": directional_accuracy(pred_events, ground_truth),
            "date_mae_days": date_mae(pred_events, ground_truth),
        }
```

### 5.2 Key Historical Test Cases

The following known events form the **holdout evaluation set** — events that occurred after the training cutoff:

| Event | Actual Date | Train Cutoff | Prediction Target |
|---|---|---|---|
| Claude 4 Opus release | Dec 2025 | Sep 2025 | Model name, date, capabilities |
| Claude 4 Sonnet release | Mar 2026 | Dec 2025 | Model name, date, benchmark scores |
| Computer-use agent GA | Nov 2025 | Aug 2025 | Feature launch date, API changes |
| 200K → 1M context window | Feb 2026 | Nov 2025 | Context size increase, timing |
| Karpathy hire announcement | May 2026 | Feb 2026 | Hire prediction, role, team |
| Automated pretraining team formation | May 2026 | Feb 2026 | New research direction, compute reqs |
| "Vibe coding" → "Agentic engineering" shift | Early 2026 | Late 2025 | Tooling paradigm shift, dev workflow change |

### 5.3 Evaluation Metrics — Detailed Specification

**Precision-at-K for Feature Announcements**

```
Precision@K = (number of correctly predicted events among top K) / K

Where "correctly predicted" means:
  - Event type matches (model_release, feature_launch, hire, etc.)
  - Predicted date within ±30 days of actual
  - For capability predictions: predicted benchmark score within ±5% of actual
```

**Temporal Brier Score for Timeline Estimation**

```
Brier Score = (1/N) * Σ (p_i - o_i)²

Where:
  - p_i = predicted probability of event occurring by time t_i
  - o_i = binary outcome (1 if event occurred by t_i, else 0)

For timelines of length T, compute Brier at intervals {T/4, T/2, 3T/4, T}
A score < 0.10 is considered excellent for forecasting.
```

**Directional Accuracy for Compute Growth**

```
Directional Accuracy = (1/N) * Σ 1[sign(predicted_delta) == sign(actual_delta)]

Evaluated on:
  - GPU cluster size changes
  - Training FLOP budget changes
  - Infrastructure spend changes
```

**Calibration Curve**: Plot predicted confidence vs. empirical accuracy over all predictions. Perfect calibration = diagonal line. Expected deviation < 0.05 for a well-tuned model.

### 5.4 Ablation Studies

| Ablation | Change | Expected Impact |
|---|---|---|
| Remove compute signals | No FLOP/GPU data | Release timing MAE ↑ 40% |
| Remove hiring signals | No talent migration | Karpathy-level prediction fails |
| Remove research signals | No ArXiv data | Capability prediction accuracy ↓ 60% |
| Shorten context (32K) | 128K → 32K | Recall for multi-year patterns ↓ 50% |
| No temporal jitter | Fixed dates | Overfits to specific timeline |
| Remove long-tail events | Filter < 5% frequency | Misses rare but high-impact signals |

---

## Summary: Critical Path Items

| Phase | Duration | Key Milestone | Critical Risk |
|---|---|---|---|
| Data pipeline construction | 4-6 weeks | All 4 streams producing clean, timestamped events | API rate limits, legal constraints on scraping |
| Historical event database | 2-3 weeks | Structured DB with 5+ years of AI industry events | Missing events, data quality |
| SFT training run | 2-4 weeks (on 8×H100) | Checkpoint with <2.0 eval loss on holdout | Compute budget, convergence |
| Backtesting framework | 2 weeks | Reproducible historical evaluation pipeline | Temporal data leakage |
| Calibration & tuning | 2 weeks | Brier < 0.10 on validation set | Overconfidence in predictions |
| Live deployment | 1 week | Streaming inference at 1 prediction/day | Latency, cost of 128K context |

---

This blueprint covers the full lifecycle from data ingestion through deployment with actionable implementation details at each stage. The key architectural insight is that **LLMs are naturally suited to this task** because the causal attention mechanism maps directly onto the time-series prediction problem — the model learns to attend to the most informative historical signals when forecasting future events.
