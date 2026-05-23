#!/usr/bin/env python3
"""
Training configuration for Project Foresight.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ForesightTrainingConfig:
    """Configuration for QLoRA training of Foresight model."""

    # Model settings
    model_id: str = "meta-llama/Meta-Llama-3-8B"
    output_dir: str = "models/foresight_final/"

    # QLoRA settings - lower rank for 8B model
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.1
    lora_target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",
        "gate_proj", "up_proj", "down_proj",
    ])

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
    warmup_ratio: float = 0.03
    max_grad_norm: float = 1.0
    optim: str = "paged_adamw_8bit"

    # Context (reduced for 8B model efficiency)
    max_context_length: int = 8192

    # SFTTrainer specific
    packing: bool = True
    dataset_text_field: str = "text"
    max_seq_length: int = 8192

    # Logging
    logging_steps: int = 25
    save_steps: int = 200
    save_total_limit: int = 3
    report_to: str = "none"
    run_name: str = "foresight-v1"
    warmup_steps: int = 10  # Explicitly set warmup steps instead of warmup_ratio

    def to_training_args_dict(self) -> dict:
        """Convert to TrainingArguments dictionary."""
        return {
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
            "fp16": True,
            "gradient_checkpointing": True,
            "max_grad_norm": self.max_grad_norm,
            "optim": self.optim,
            "remove_unused_columns": False,
            "dataloader_num_workers": 2,
            "report_to": "none",
            "run_name": self.run_name,
        }