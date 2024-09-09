from typing import Optional, Sequence

import transformers

from premsql.datasets.base import Text2SQLBaseDataset
from premsql.datasets.collator import DataCollatorForSupervisedDataset
from premsql.evaluator.base import BaseExecutor
from premsql.logger import setup_console_logger
from premsql.tuner.callback import Text2SQLEvaluationCallback
from premsql.tuner.config import DefaultTrainingArguments

logger = setup_console_logger("[FULL-FINETUNE]")


class Text2SQLFullFinetuner:
    def __init__(
        self,
        model_name_or_path: str,
        experiment_name: str,
        hf_token: Optional[str] = None,
        **model_kwargs,
    ):
        self.model_name_or_path = model_name_or_path

        logger.warning("Setting up Pretrained-Model: " + str(model_name_or_path))
        self.model = transformers.AutoModelForCausalLM.from_pretrained(
            model_name_or_path, token=hf_token, **model_kwargs
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
        per_device_train_batch_size: int,
        gradient_accumulation_steps: int,
        evaluation_dataset: Optional[Text2SQLBaseDataset] = None,
        eval_steps: Optional[int] = 500,
        executor: Optional[BaseExecutor] = None,
        filter_eval_results_by: Optional[tuple] = None,
        **training_arguments,
    ):
        self.training_arguments = DefaultTrainingArguments(
            output_dir=output_dir,
            num_train_epochs=num_train_epochs,
            per_device_train_batch_size=per_device_train_batch_size,
            gradient_accumulation_steps=gradient_accumulation_steps,
            **training_arguments,
        )

        data_module = dict(
            train_dataset=train_datasets,
            eval_dataset=None,
            data_collator=self.data_collator,
        )
        trainer = transformers.Trainer(
            model=self.model,
            tokenizer=self.tokenizer,
            args=self.training_arguments,
            **data_module,
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
