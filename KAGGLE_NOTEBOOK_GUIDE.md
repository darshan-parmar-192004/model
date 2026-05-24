# Foresight Model Training on Kaggle - Complete Guide

> Training auto-resumes from checkpoints if interrupted (e.g. session timeout).
> Kaggle gives 30h/week GPU — enough for multiple retries.

---

## First Run — Run all cells in order

### Cell 1 - Clone and Setup
```python
!git clone https://github.com/darshan-parmar-192004/model.git
%cd /kaggle/working/model
!pip install -q huggingface_hub
```

### Cell 2 - Hugging Face Login
```python
from kaggle_secrets import UserSecretsClient
from huggingface_hub import login

hf_token = UserSecretsClient().get_secret("HF_TOKEN")
login(token=hf_token)
print("Logged in to Hugging Face successfully!")
```

### Cell 3 - Install Requirements
```python
!pip install -r requirements.txt
```

### Cell 4 - Configure Training
```python
import sys
sys.path.insert(0, "/kaggle/working/model")

from foresight.training.config import ForesightTrainingConfig

config = ForesightTrainingConfig(
    model_id="unsloth/llama-3-8b-Instruct-bnb-4bit",
    output_dir="/kaggle/working/foresight-model",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=32,
    num_train_epochs=3,
    learning_rate=2e-4,
    max_seq_length=1024,
    max_context_length=1024,
    lora_r=8,
    lora_alpha=32,
    compute_dtype="float16",
)
```

### Cell 5 - Train the Model (auto-resumes if interrupted)
```python
from foresight.training.train import train_foresight

train_foresight(config, "data/train_dataset.jsonl", "data/val_dataset.jsonl")
```

### Cell 6 - Save and Download Model
```python
!zip -r /kaggle/working/foresight_model.zip /kaggle/working/foresight-model/

from IPython.display import FileLink
FileLink("/kaggle/working/foresight_model.zip")
```

---

## Resume Run — If session disconnected mid-training

If Kaggle disconnects, restart from **Cell 1** (to clone the repo + download model again).
The weights download each time, but `train_foresight` automatically detects the
existing checkpoint in `/kaggle/working/foresight-model/` and resumes from there.

You do NOT need to change anything — Cells 4 + 5 will pick up where you left off
because the checkpoint folder is persistent within the Kaggle session.

### Quick Resume (if repo already cloned in session)
```python
import sys
sys.path.insert(0, "/kaggle/working/model")

from foresight.training.config import ForesightTrainingConfig
from foresight.training.train import train_foresight

config = ForesightTrainingConfig(
    model_id="unsloth/llama-3-8b-Instruct-bnb-4bit",
    output_dir="/kaggle/working/foresight-model",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=32,
    num_train_epochs=3,
    learning_rate=2e-4,
    max_seq_length=1024,
    max_context_length=1024,
    lora_r=8,
    lora_alpha=32,
    compute_dtype="float16",
)

# Auto-detects checkpoint and resumes
train_foresight(config, "data/train_dataset.jsonl", "data/val_dataset.jsonl")
```

---

## Expected Output

After training completes:
- 7,093 training samples, 35 validation samples
- Model saved to `/kaggle/working/foresight_model.zip` (~200MB LoRA adapter)
- Logs will show: `Resuming from checkpoint: ...` or `No checkpoint found, starting fresh`
