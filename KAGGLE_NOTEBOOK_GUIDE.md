# Foresight Model Training on Kaggle - Complete Guide

> Training auto-resumes **across Kaggle sessions** via Hugging Face Hub checkpoint sync.
> Kaggle gives 30h/week GPU — enough for multiple retries.
> Checkpoints are pushed to HF Hub every `save_steps` and pulled on next session.

---

## Only 2 Cells Needed — Run Both, Every Time, In Order

### Cell 1 — Setup (clone repo, install deps, login to HF)
```python
!git clone https://github.com/darshan-parmar-192004/model.git
%cd /kaggle/working/model/foresight
!pip install -q huggingface_hub
!pip install -r requirements.txt

from kaggle_secrets import UserSecretsClient
from huggingface_hub import login
token = UserSecretsClient().get_secret("HF_TOKEN")
login(token=token)
```

### Cell 2 — Train (auto-detects fresh or resume)
```python
import sys
sys.path.insert(0, "/kaggle/working/model/foresight")

from foresight.training.config import ForesightTrainingConfig
from foresight.training.train import train_foresight

config = ForesightTrainingConfig(
    model_id="unsloth/llama-3-8b-Instruct-bnb-4bit",
    output_dir="/kaggle/working/foresight-model",
    hub_model_id="darshan8823/foresight-checkpoints",
    push_to_hub=True,
    per_device_train_batch_size=1,
    gradient_accumulation_steps=32,
    num_train_epochs=3,
    learning_rate=2e-4,
    max_seq_length=1024,
    lora_r=8,
    lora_alpha=32,
    compute_dtype="float16",
)

train_foresight(config, "data/train_dataset.jsonl", "data/val_dataset.jsonl")
```

### Cell 3 (Optional) — Download final model zip
```python
!zip -r /kaggle/working/foresight_model.zip /kaggle/working/foresight-model/

from IPython.display import FileLink
FileLink("/kaggle/working/foresight_model.zip")
```

---

## How Resume Works

| Session | What happens |
|---|---|
| **Session 1** | Trains from scratch, pushes `checkpoint-200`, `checkpoint-400`, etc. to `darshan8823/foresight-checkpoints` on HF Hub |
| **Session 2+** | Cell 2 downloads all checkpoints from HF Hub → finds latest → resumes from exact step → continues pushing |

**Requirements:**
1. HF secret `HF_TOKEN` in Kaggle Secrets (add via Notebook → Add-ons → Secrets)
2. Create an empty HF model repo `darshan8823/foresight-checkpoints` at https://huggingface.co/new

---

## Expected Output

- 7,093 training samples, 35 validation samples  
- Model saved to `/kaggle/working/foresight_model.zip` (~200MB LoRA adapter)
- Logs on first run: `No checkpoint found, starting fresh training...`
- Logs on resume: `Downloading remote checkpoints from darshan8823/foresight-checkpoints...` → `Resuming from checkpoint: /kaggle/working/foresight-model/checkpoint-XXX`
