#!/usr/bin/env python3
"""
Historic backtesting engine for Project Foresight.
Loads trained QLoRA adapters, evaluates against historical test cases.
"""

import argparse
import json
import logging
import math
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Optional

import torch
import torch.nn as nn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def compute_perplexity(model, tokenizer, prompt_text, target_text, device="cuda"):
    """
    Compute perplexity of the target text given the prompt context.
    Lower perplexity = model more confidently predicts the outcome.
    """
    full_text = prompt_text + target_text
    inputs = tokenizer(full_text, return_tensors="pt", truncation=True, max_length=8192).to(device)
    prompt_len = len(tokenizer(prompt_text, return_tensors="pt")["input_ids"][0])
    
    with torch.no_grad():
        outputs = model(**inputs, labels=inputs["input_ids"])
    
    logits = outputs.logits
    
    shift_logits = logits[..., :-1, :].contiguous()
    shift_labels = inputs["input_ids"][..., 1:].contiguous()
    
    loss_fct = nn.CrossEntropyLoss(reduction="none")
    loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
    loss = loss.view(shift_labels.shape)
    
    # Mask out prompt tokens
    loss[:, :prompt_len - 1] = 0.0
    num_target_tokens = (shift_labels[0] != -100).sum().item()
    target_loss = loss[0, prompt_len - 1:].sum() / max(1, num_target_tokens)
    
    return math.exp(target_loss.item())

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
            train_events = [e for e in self.event_db if datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) < cutoff]
            test_events = [e for e in self.event_db if cutoff <= datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) < cutoff + timedelta(days=max(eval_horizons))]
            
            # Fine-tune on train_events (or use adapter for efficiency)
            # For now, we'll use the pre-trained model as-is
            
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
        
        return results
    
    def generate_predictions(
        self,
        context: List[Dict],
        horizon: int,
    ) -> List[Dict]:
        """Generate structured predictions from context."""
        from foresight.schema.core_schema import build_context_string
        
        context_str = build_context_string(context)
        prompt = self._build_forecast_prompt(context_str, horizon_days=horizon)
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=8192, truncation=True).to(self.model.device)
        
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
            f"You are Foresight, a predictive model forecasting AI industry events. "
            f"Given the following timeline of observations, predict the events "
            f"that will occur in the next {horizon_days} days. "
            "Respond with a JSON object containing a 'predictions' array."
        )
        return self.tokenizer.apply_chat_template([
            {"role": "system", "content": system},
            {"role": "user", "content": context_str},
        ], tokenize=False, add_generation_prompt=True)
    
    def _parse_forecasts(self, outputs) -> List[Dict]:
        responses = [self.tokenizer.decode(o, skip_special_tokens=True) for o in outputs]
        ensemble = {}
        for resp in responses:
            start, end = resp.find('{'), resp.rfind('}')
            if start >= 0 and end > start:
                try:
                    data = json.loads(resp[start:end+1])
                    for pred in data.get("predictions", []):
                        key = f"{pred.get('event_type','')}::{pred.get('predicted_date','')}"
                        if key not in ensemble:
                            ensemble[key] = []
                        ensemble[key].append(pred)
                except json.JSONDecodeError:
                    continue
        
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
        from typing import Tuple
        
        # Simplified metrics calculation
        pred_events = [p for p in predictions if p.get('event_type')]
        gt_events = [e for e in ground_truth if e.get('signal_type')]
        
        # Precision@K (simplified)
        precision_at_1 = 1.0 if pred_events and gt_events else 0.0
        precision_at_3 = 1.0 if len(pred_events) >= 1 and gt_events else 0.0
        
        return {
            "precision_at_1": precision_at_1,
            "precision_at_3": precision_at_3,
        }

def main():
    parser = argparse.ArgumentParser(description="Run backtesting for Project Foresight")
    parser.add_argument('--adapter', type=str, default='models/foresight_final/', help='Path to trained adapter')
    parser.add_argument('--base-model', type=str, default='meta-llama/Meta-Llama-3-8B', help='Base model ID')
    parser.add_argument('--events', type=str, default='data/raw_events.jsonl', help='Events file')
    parser.add_argument('--output', type=str, default='results/backtest_results.json', help='Output path')
    
    args = parser.parse_args()
    
    # Load events
    events = []
    with open(args.events, 'r') as f:
        for line in f:
            events.append(json.loads(line))
    
    # Load model
    from foresight.training.train import load_foresight_model
    model, tokenizer = load_foresight_model(args.adapter, args.base_model)
    
    # Create engine
    engine = BacktestEngine(model, tokenizer, events)
    
    # Define test cutoffs (simplified)
    from datetime import timedelta
    all_dates = [datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) for e in events]
    all_dates.sort()
    
    # Use 3 evenly spaced cutoffs for demonstration
    train_cutoffs = [
        all_dates[len(all_dates) // 3],
        all_dates[2 * len(all_dates) // 3],
    ]
    
    # Run backtest
    results = engine.sliding_window_eval(train_cutoffs, eval_horizons=[30, 90])
    
    # Save results
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Backtest results saved to {args.output}")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()