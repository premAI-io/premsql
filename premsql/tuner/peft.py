from typing import Optional, Sequence

from premsql.datasets.base import Text2SQLBaseDataset
from premsql.datasets.collator import DataCollatorForSupervisedDataset
from premsql.evaluator.base import BaseExecutor
from premsql.logger import setup_console_logger
from premsql.tuner.callback import Text2SQLEvaluationCallback
from premsql.tuner.config import DefaultLoraConfig, DefaultPeftArguments

logger = setup_console_logger("[LORA-FINETUNE]")

try:
    import torch
    import transformers
    from peft import LoraConfig
    from transformers import BitsAndBytesConfig
    from trl import SFTTrainer
except ImportError:
    logger.warn("Ensure torch transformers peft and trl are installed.")
    logger.warn("Install them by: pip install torch peft trl transformers")


class Text2SQLPeftTuner:
    def __init__(
        self,
        model_name_or_path: str,
        experiment_name: str,
        peft_config: Optional[LoraConfig] = None,
        bnb_config: Optional[BitsAndBytesConfig] = None,
        hf_token: Optional[str] = None,
        **model_kwargs,
    ):
        self.peft_config = peft_config or DefaultLoraConfig()
        self.bnb_config = bnb_config
        self.model_name_or_path = model_name_or_path

        logger.warning("Setting up Pretrained-Model: " + str(model_name_or_path))

        self.model = transformers.AutoModelForCausalLM.from_pretrained(
            model_name_or_path,
            token=hf_token,
            torch_dtype=torch.bfloat16,
            quantization_config=bnb_config,
            **model_kwargs,
        )
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_name_or_path, padding_size="right", token=hf_token
        )
        self.data_collator = DataCollatorForSupervisedDataset(tokenizer=self.tokenizer)

        self._hf_token = hf_token
        self.experiment_name = experiment_name

    def train(
        self,
        train_datasets: Sequence[Text2SQLBaseDataset],
        output_dir: str,
        num_train_epochs: int,
        max_seq_length: int,
        per_device_train_batch_size: int,
        gradient_accumulation_steps: int,
        evaluation_dataset: Optional[Text2SQLBaseDataset] = None,
        eval_steps: Optional[int] = 500,
        executor: Optional[BaseExecutor] = None,
        filter_eval_results_by: Optional[tuple] = None,
        **training_arguments,
    ):
        self.training_arguments = transformers.TrainingArguments(
            **DefaultPeftArguments(
                output_dir=output_dir,
                num_train_epochs=num_train_epochs,
                per_device_train_batch_size=per_device_train_batch_size,
                gradient_accumulation_steps=gradient_accumulation_steps,
                **training_arguments,
            ).to_dict()
        )

        if "raw" in train_datasets[0]:
            formatting_func = lambda x: x["raw"]["prompt"]
        else:
            formatting_func = lambda x: x["prompt"]

        trainer = SFTTrainer(
            model=self.model,
            train_dataset=train_datasets,
            peft_config=self.peft_config,
            tokenizer=self.tokenizer,
            args=self.training_arguments,
            packing=True,
            formatting_func=formatting_func,
            max_seq_length=max_seq_length,
        )

        if evaluation_dataset is not None and executor is not None:
            eval_callback = Text2SQLEvaluationCallback(
                trainer=trainer,
                trainer_args=self.training_arguments,
                eval_dataset=evaluation_dataset,
                experiment_name=self.experiment_name,
                model_or_name_or_id=self.model_name_or_path,
                eval_steps=eval_steps,
                executor=executor,
                filter_results_by=filter_eval_results_by,
                hf_token=self._hf_token,
            )
            trainer.add_callback(eval_callback)

        trainer.train()
        trainer.save_model(output_dir=self.training_arguments.output_dir)
