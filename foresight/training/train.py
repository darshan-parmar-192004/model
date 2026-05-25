#!/usr/bin/env python3
"""
Production QLoRA training engine for Project Foresight.
Uses SFTTrainer from TRL for efficient supervised fine-tuning.
"""

import math
import logging
import glob
import re
from typing import Tuple, Optional, List, Dict

import torch
from torch import nn


# Lazy imports to avoid import-time failures
def _import_training_deps():
    """Lazy import training dependencies."""
    global transformers, peft, trl, datasets, bitsandbytes
    try:
        import transformers
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            TrainingArguments,
            BitsAndBytesConfig,
        )
        import peft
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        import trl
        from trl import SFTTrainer, SFTConfig
        import datasets
        import bitsandbytes

        return True
    except ImportError as e:
        logging.warning(f"Training dependencies not installed: {e}")
        return False


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_model_and_tokenizer(config):
    """
    Setup model and tokenizer for training.
    """
    if not _import_training_deps():
        raise ImportError(
            "Training dependencies not installed. Install with: pip install transformers peft trl datasets bitsandbytes"
        )

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import prepare_model_for_kbit_training

    # Check if model is a pre-quantized Unsloth model
    is_unsloth = "unsloth" in config.model_id.lower()

    # Only use quantization_config for non-pre-quantized models
    if not is_unsloth:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
    else:
        bnb_config = None

    # Load model
    model_kwargs = {
        "device_map": "auto",
        "dtype": torch.float16,
        "use_cache": False,
    }
    if bnb_config is not None:
        model_kwargs["quantization_config"] = bnb_config

    model = AutoModelForCausalLM.from_pretrained(
        config.model_id,
        **model_kwargs,
    )

    # Set max_length to user-requested seq length for SFTTrainer fallback
    model.config.max_length = config.max_seq_length

    # Prepare model for k-bit training
    model = prepare_model_for_kbit_training(model)

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        config.model_id,
        padding_side="right",
        add_eos_token=True,
    )

    # Set pad token if not set
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Set model_max_length so SFTTrainer fallback uses our value
    tokenizer.model_max_length = config.max_seq_length

    return model, tokenizer


def apply_lora(model, config):
    """
    Apply LoRA adaptation to the model.
    """
    from peft import LoraConfig, get_peft_model

    lora_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        target_modules=config.lora_target_modules,
        lora_dropout=config.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model


def make_format_func(tokenizer):
    """
    Create a formatting function for SFTTrainer that converts examples to text.
    SFTTrainer calls this on each example on-the-fly.
    """

    def format_foresight_sample(example: Dict) -> str:
        messages = [
            {
                "role": "system",
                "content": "You are Foresight, a predictive model forecasting AI industry events.",
            },
            {"role": "user", "content": example["instruction"]},
            {"role": "assistant", "content": example["output"]},
        ]
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=False
        )

    return format_foresight_sample


def find_latest_checkpoint(output_dir: str) -> Optional[str]:
    checkpoint_dirs = glob.glob(os.path.join(output_dir, "checkpoint-*"))
    if not checkpoint_dirs:
        return None

    def extract_step(path):
        match = re.search(r"checkpoint-(\d+)$", path)
        return int(match.group(1)) if match else 0

    return max(checkpoint_dirs, key=extract_step)


def train_foresight(config, train_dataset_path, val_dataset_path=None) -> str:
    """
    Train the Foresight model with QLoRA.
    """
    if not _import_training_deps():
        raise ImportError("Training dependencies not installed.")

    from transformers import TrainingArguments
    from trl import SFTTrainer, SFTConfig
    from datasets import load_dataset

    # Setup model and tokenizer
    logger.info("Setting up model and tokenizer...")
    model, tokenizer = setup_model_and_tokenizer(config)
    model = apply_lora(model, config)

    # Load datasets
    logger.info("Loading datasets...")
    train_dataset = load_dataset("json", data_files=train_dataset_path, split="train")
    if val_dataset_path:
        val_dataset = load_dataset("json", data_files=val_dataset_path, split="train")
    else:
        val_dataset = None

    # Create formatting function (applied on-the-fly by SFTTrainer)
    formatting_func = make_format_func(tokenizer)

    # Create training arguments - use SFTConfig for newer TRL
    training_args = SFTConfig(**config.to_training_args_dict())

    # Create trainer
    logger.info("Creating trainer...")
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        formatting_func=formatting_func,
    )

    # Download remote checkpoints from HF Hub so resume works across Kaggle sessions
    try:
        from huggingface_hub import snapshot_download, HfApi

        if config.push_to_hub and config.hub_model_id:
            api = HfApi()
            try:
                api.model_info(config.hub_model_id)
                logger.info(f"Downloading remote checkpoints from {config.hub_model_id}...")
                snapshot_download(
                    repo_id=config.hub_model_id,
                    local_dir=config.output_dir,
                    allow_patterns="checkpoint-*",
                    token=os.environ.get("HF_TOKEN"),
                )
            except Exception:
                logger.info(f"No remote hub repo found at {config.hub_model_id}, will create during training")
    except ImportError:
        logger.info("huggingface_hub not installed, skipping remote checkpoint download")

    # Check for existing checkpoint to resume from (now includes downloaded ones)
    checkpoint = find_latest_checkpoint(config.output_dir)
    if checkpoint:
        logger.info(f"Resuming from checkpoint: {checkpoint}")
    else:
        logger.info("No checkpoint found, starting fresh training...")

    # Train
    trainer.train(resume_from_checkpoint=checkpoint)

    # Save model
    logger.info("Saving model...")
    trainer.save_model(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)

    return config.output_dir


def load_foresight_model(
    model_path: str, base_model_id: str = "meta-llama/Meta-Llama-3-8B"
) -> Tuple:
    """
    Load a trained Foresight model for inference.
    """
    if not _import_training_deps():
        raise ImportError("Training dependencies not installed.")

    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel

    # Check if model is a pre-quantized Unsloth model
    is_unsloth = "unsloth" in base_model_id.lower()

    # Only use quantization_config for non-pre-quantized models
    if not is_unsloth:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
        )
    else:
        bnb_config = None

    model_kwargs = {
        "device_map": "auto",
        "dtype": torch.float16,
    }
    if bnb_config is not None:
        model_kwargs["quantization_config"] = bnb_config

    model = AutoModelForCausalLM.from_pretrained(
        base_model_id,
        **model_kwargs,
    )

    # Load LoRA adapter
    model = PeftModel.from_pretrained(model, model_path)

    tokenizer = AutoTokenizer.from_pretrained(model_path)

    return model, tokenizer


class ForesightPredictionHeads(nn.Module):
    """
    Optional prediction heads for structured forecasting outputs.
    """

    def __init__(self, hidden_size: int = 4096):
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
            nn.Linear(512, 1),  # Log(FLOPs)
        )

    def forward(self, hidden_states):
        # Take representation from the last token of the context
        context_repr = hidden_states[:, -1, :]
        return {
            "release_timing": self.release_timing(context_repr),
            "capability_vector": self.capability_vector(context_repr),
            "compute_budget": self.compute_budget(context_repr),
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Train Foresight model")
    parser.add_argument(
        "--train-dataset",
        type=str,
        required=True,
        help="Path to training dataset JSONL",
    )
    parser.add_argument(
        "--val-dataset", type=str, default=None, help="Path to validation dataset JSONL"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="models/foresight_final/",
        help="Output directory",
    )

    args = parser.parse_args()

    from foresight.training.config import ForesightTrainingConfig

    config = ForesightTrainingConfig(output_dir=args.output_dir)
    train_foresight(config, args.train_dataset, args.val_dataset)
