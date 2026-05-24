# Foresight Model Training - Colab / Kaggle Guide

## Cell 1 - Clone and Setup
```python
# Clone the repository and set up working directory
!git clone https://github.com/darshan-parmar-192004/model.git

# --- Colab ---
%cd /content/model
# --- Kaggle (comment out if on Colab) ---
# %cd /kaggle/working/model

# Install huggingface_hub for Python-based login
!pip install -q huggingface_hub
```

## Cell 2 - Hugging Face Login
```python
# Login to Hugging Face
from huggingface_hub import login

# --- Colab ---
from google.colab import userdata
hf_token = userdata.get("HF_TOKEN")
# --- Kaggle (comment out if on Colab) ---
# from kaggle_secrets import UserSecretsClient
# hf_token = UserSecretsClient().get_secret("HF_TOKEN")

login(token=hf_token)
print("Logged in to Hugging Face successfully!")
```

## Cell 3 - Install Requirements
```python
# Install requirements from the correct path
!pip install -r requirements.txt
```

## Cell 4 - Configure Training
```python
import sys

# --- Colab ---
sys.path.insert(0, "/content/model")
# --- Kaggle (comment out if on Colab) ---
# sys.path.insert(0, "/kaggle/working/model")

from foresight.training.config import ForesightTrainingConfig

# T4-optimized config (16GB VRAM)
config = ForesightTrainingConfig(
    model_id="unsloth/llama-3-8b-Instruct-bnb-4bit",  # 4-bit quantized
    output_dir="/content/foresight-model",            # Colab
    # output_dir="/kaggle/working/foresight-model",   # Kaggle
    per_device_train_batch_size=1,       # Memory limit
    gradient_accumulation_steps=32,      # Compensate for small batch
    num_train_epochs=3,
    learning_rate=2e-4,
    max_seq_length=1024,                 # Reduced for memory
    max_context_length=1024,
    lora_r=8,                            # Smaller LoRA rank
    lora_alpha=32,
    compute_dtype="float16",             # T4 needs float16, not bf16
)
```

## Cell 5 - Train the Model
```python
from foresight.training.train import train_foresight

train_foresight(config, "data/train_dataset.jsonl", "data/val_dataset.jsonl")
```

## Cell 6 - Save and Download Model
```python
# Zip and save the model
import zipfile
import os

# --- Colab ---
!zip -r /content/foresight_model.zip /content/foresight-model/
# --- Kaggle (comment out if on Colab) ---
# !zip -r /kaggle/working/foresight_model.zip /kaggle/working/foresight-model/

from IPython.display import FileLink
FileLink("/content/foresight_model.zip")
```

## Key Fixes Applied

1. **HF CLI Error**: Replaced `huggingface-cli login` with Python API `huggingface_hub.login()`
2. **Working Directory**: Added `%cd model` before installing requirements
3. **Module Import**: Added `sys.path.insert` before imports
4. **Requirements Path**: Uses `requirements.txt` after changing to `model` directory
5. **Memory**: Reduced `per_device_train_batch_size=1`, `gradient_accumulation_steps=32`, `max_seq_length=1024`
6. **4-bit Model**: Using `unsloth/llama-3-8b-Instruct-bnb-4bit` for VRAM constraints
7. **compute_dtype**: Set to `float16` for T4 GPU compatibility
8. **Colab support**: Added `google.colab.userdata` alternative for secrets

## Expected Output

After running all cells:
- 7,093 training samples
- 35 validation samples  
- Trained model saved to `/content/foresight_model.zip` (~200MB LoRA adapter)