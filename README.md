# Project Foresight: AI Industry Forecasting LLM

A causal autoregressive transformer repurposed as a time-series strategic forecasting engine for the AI industry.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    DATA INGESTION LAYER                   │
├──────────────────┬──────────────────┬────────────────────┤
│ Research         │ Product          │ Macro              │
│ Scraper          │ Footprint        │ Signals            │
│ (ArXiv,          │ Scraper          │ Scraper            │
│ OpenReview)      │ (GitHub)         │ (SEC EDGAR)        │
├──────────────────┴──────────────────┴────────────────────┤
│                        PIPELINE ORCHESTRATOR              │
├───────────────────────────────────────────────────────────┤
│                    TRAINING PIPELINE                      │
│   - Dataset Builder (temporal sequences)                 │
│   - QLoRA Fine-tuning (Meta-Llama-3-8B)                  │
│   - Backtesting Engine                                    │
└───────────────────────────────────────────────────────────┘
```

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### 1. Run the data pipeline

```bash
python scripts/run_pipeline.py --since 2024-01-01
```

This will:
- Scrape research papers from ArXiv/OpenReview
- Monitor GitHub repositories for commits/releases
- Poll SEC EDGAR for infrastructure filings
- Output `data/raw_events.jsonl`

### 2. Build training dataset

```bash
python scripts/build_training_dataset.py --input data/raw_events.jsonl --output-dir data/
```

This creates:
- `data/train_dataset.jsonl`
- `data/val_dataset.jsonl`

### 3. Train the model

```bash
python -m foresight.training.train --train-dataset data/train_dataset.jsonl --val-dataset data/val_dataset.jsonl
```

### 4. Run backtesting

```bash
python scripts/run_backtest.py --events data/raw_events.jsonl --output results/backtest_results.json
```

## Configuration

Training configuration is in `foresight/training/config.py`.

Key settings:
- Base model: Meta-Llama-3-8B (configurable)
- LoRA: rank 16, alpha 32
- Context length: 8K tokens
- Mixed precision: BF16

## Project Structure

```
foresight/
├── __init__.py
├── config.py                 # Training configuration
├── ingestion/
│   ├── research_scraper.py   # ArXiv/OpenReview scraper
│   ├── product_footprint_scraper.py  # GitHub scraper
│   └── macro_signals_scraper.py      # SEC EDGAR scraper
├── schema/
│   └── core_schema.py        # Data schemas
├── utils/
│   └── time_utils.py         # Timestamp utilities
├── model/
│   └── sequence_builder.py   # Temporal sequence builder
├── dataset/
│   └── augmentation.py       # Temporal augmentation
├── training/
│   ├── __init__.py
│   ├── config.py             # Training config
│   └── train.py              # Training engine
scripts/
├── run_pipeline.py           # Pipeline orchestrator
├── build_training_dataset.py # Dataset builder
└── run_backtest.py           # Backtesting engine
data/
├── known_events.json         # Seed events
└── raw_events.jsonl          # Scrape output
```

## Data Sources

### Research Stream
- ArXiv: AI/ML papers from targeted authors/institutions
- OpenReview: Conference submissions

### Product Stream
- GitHub: Commits, releases from target repositories
- Changelogs: Documentation updates

### Macro Stream
- SEC EDGAR: 10-K/Q filings for compute infrastructure mentions
- Companies: AMZN, MSFT, GOOGL, META, NVDA

## License

MIT License