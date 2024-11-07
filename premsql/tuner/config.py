from dataclasses import dataclass, field
from typing import List, Optional
from premsql.logger import setup_console_logger

logger = setup_console_logger("[TUNER-CONFIG]")

try:
    from peft import LoraConfig, TaskType
    from transformers import TrainingArguments
except ImportError:
    logger.warn("Unable to find peft and transformers. Install: pip install peft transformers")


@dataclass
class DefaultTrainingArguments(TrainingArguments):
    output_dir: str
    num_train_epochs: int
    per_device_train_batch_size: int
    gradient_accumulation_steps: int

    load_best_model_at_end: Optional[bool] = field(default=True)
    gradient_checkpointing: Optional[bool] = field(default=True)
    evaluation_strategy: Optional[str] = field(default="no")

    cache_dir: Optional[str] = field(default=None)
    optim: str = field(default="adamw_hf")
    model_max_length: int = field(
        default=1024,
        metadata={
            "help": "Maximum sequence length. Sequences will be right padded (and possibly truncated)."
        },
    )
    max_seq_length: int = field(default=1024)
    ddp_find_unused_parameters: Optional[bool] = field(default=False)
    fp16: bool = field(default=False)
    bf16: bool = field(default=True)

    weight_decay: float = field(default=0.1)
    lr_scheduler_type: str = field(default="cosine")
    warmup_ratio: float = field(default=0.01)
    logging_steps: int = field(default=10)
    save_strategy: str = field(default="steps")
    save_steps: int = field(default=200)
    save_total_limit: int = field(default=3)
    auto_find_batch_size: Optional[bool] = field(default=False)
    report_to: List[str] = field(default_factory=lambda: ["tensorboard"])


@dataclass
class DefaultPeftArguments(TrainingArguments):
    output_dir: str
    num_train_epochs: int
    per_device_train_batch_size: int
    gradient_accumulation_steps: int

    load_best_model_at_end: Optional[bool] = field(default=False)
    gradient_checkpointing: Optional[bool] = field(default=True)
    evaluation_strategy: Optional[str] = field(default="no")
    optim: str = field(default="adamw_hf")

    max_grad_norm: Optional[bool] = field(default=0.3)
    weight_decay: float = field(default=0.1)
    lr_scheduler_type: str = field(default="cosine")
    warmup_ratio: float = field(default=0.01)
    logging_steps: int = field(default=10)
    save_strategy: str = field(default="steps")
    save_steps: int = field(default=200)
    save_total_limit: int = field(default=3)
    auto_find_batch_size: Optional[bool] = field(default=False)
    report_to: List[str] = field(default_factory=lambda: ["tensorboard"])

    fp16: Optional[bool] = field(default=False)
    bf16: Optional[bool] = field(default=True)
    neftune_noise_alpha: Optional[int] = field(default=5)


@dataclass
class DefaultLoraConfig(LoraConfig):
    lora_alpha: float = field(default=32)
    lora_dropout: float = field(default=0.1)
    r: int = field(default=64)
    target_modules: List[str] = field(
        default_factory=lambda: [
            "q_proj",
            "v_proj",
            "k_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
            "lm_head",
        ]
    )
    task_type: TaskType = field(default=TaskType.CAUSAL_LM)
