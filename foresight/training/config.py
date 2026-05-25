#!/usr/bin/env python3
"""
Training configuration for Project Foresight.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ForesightTrainingConfig:
    """Configuration for QLoRA training of Foresight model."""

    # Model settings
    model_id: str = "unsloth/llama-3-8b-Instruct-bnb-4bit"
    output_dir: str = "models/foresight_final/"

    # QLoRA settings - lower rank for 8B model
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: List[str] = field(
        default_factory=lambda: [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]
    )

    # 4-bit quantization
    use_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    use_double_quant: bool = True
    compute_dtype: str = "float16"

    # Training settings - scaled for 8B model on 4x GPU
    per_device_train_batch_size: int = 4
    gradient_accumulation_steps: int = 8
    num_train_epochs: int = 3
    learning_rate: float = 2e-4
    lr_scheduler: str = "cosine"
    max_grad_norm: float = 1.0
    optim: str = "paged_adamw_8bit"

    # Logging
    logging_steps: int = 25
    save_steps: int = 200
    save_total_limit: int = 3
    report_to: str = "none"
    run_name: str = "foresight-v1"
    warmup_steps: int = 10  # Explicitly set warmup steps

    # Sequence length settings
    max_seq_length: int = 1024
    max_context_length: int = 1024

    # Hugging Face Hub persistence — enables resume across Kaggle sessions
    hub_model_id: str = ""
    push_to_hub: bool = False
    hub_strategy: str = "every_save"

    # Mixed precision (off by default for 4-bit models — precision is internal)
    fp16: bool = False
    bf16: bool = False

    def to_training_args_dict(self) -> dict:
        """Convert to TrainingArguments dictionary."""
        d = {
            "output_dir": self.output_dir,
            "per_device_train_batch_size": self.per_device_train_batch_size,
            "gradient_accumulation_steps": self.gradient_accumulation_steps,
            "num_train_epochs": self.num_train_epochs,
            "learning_rate": self.learning_rate,
            "lr_scheduler_type": self.lr_scheduler,
            "warmup_steps": self.warmup_steps,
            "logging_steps": self.logging_steps,
            "save_strategy": "steps",
            "save_steps": self.save_steps,
            "save_total_limit": self.save_total_limit,
            "gradient_checkpointing": True,
            "max_grad_norm": self.max_grad_norm,
            "optim": self.optim,
            "remove_unused_columns": False,
            "dataloader_num_workers": 2,
            "report_to": "none",
            "run_name": self.run_name,
        }
        if self.push_to_hub and self.hub_model_id:
            d["hub_model_id"] = self.hub_model_id
            d["hub_strategy"] = self.hub_strategy
            d["push_to_hub"] = True
            hf_token = os.environ.get("HF_TOKEN")
            if hf_token:
                d["hub_token"] = hf_token
        if self.fp16:
            d["fp16"] = True
        if self.bf16:
            d["bf16"] = True
        return d
