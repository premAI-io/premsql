import os
from typing import Optional

from premsql.datasets.base import Text2SQLBaseDataset
from premsql.evaluator.base import BaseExecutor, Text2SQLEvaluator
from premsql.generators.huggingface import Text2SQLGeneratorHF
from premsql.logger import setup_console_logger

logger = setup_console_logger("[EVALUATION-CALLBACK]")

try:
    from torch.utils.tensorboard import SummaryWriter
    from transformers import (
        Trainer,
        TrainerCallback,
        TrainerControl,
        TrainerState,
        TrainingArguments,
    )
except ImportError:
    logger.warn("Unable to import torch and transformers. Install: pip install torch transformers")


class Text2SQLEvaluationCallback(TrainerCallback):
    def __init__(
        self,
        trainer: Trainer,
        trainer_args: TrainingArguments,
        eval_dataset: Text2SQLBaseDataset,
        executor: BaseExecutor,
        experiment_name: str,
        model_or_name_or_id: str,
        eval_steps: int,
        hf_token: Optional[str] = None,
        filter_results_by: Optional[tuple] = None,
    ):
        self.trainer = trainer
        self.eval_steps = eval_steps
        self.experiment_name = experiment_name

        log_dir = trainer_args.logging_dir
        os.makedirs(log_dir, exist_ok=True)

        self.tb_writer = SummaryWriter(log_dir=log_dir)
        logger.info(f"TensorBoard log directory: {log_dir}")

        self.model_or_name_or_id = model_or_name_or_id
        self.hf_token = hf_token
        self.dataset = eval_dataset
        self.executor = executor
        self.filter_by = filter_results_by

    def on_step_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        if args.local_rank == 0 and state.global_step % self.eval_steps == 0:
            logger.info(f"Evaluating at step {state.global_step}")
            model = Text2SQLGeneratorHF(
                model_or_name_or_path=self.trainer.model,
                experiment_name=f"{self.experiment_name}_step_{state.global_step}",
                type="test",
                device="cuda:0",
            )
            responses = model.generate_and_save_results(
                dataset=self.dataset, temperature=0.1, max_new_tokens=256, force=True
            )
            evaluator = Text2SQLEvaluator(
                executor=self.executor, experiment_path=model.experiment_path
            )
            if self.filter_by:
                ex_score = evaluator.execute(
                    metric_name="accuracy",
                    model_responses=responses,
                    filter_by=self.filter_by[0],
                )
            else:
                ex_score = evaluator.execute(
                    metric_name="accuracy",
                    model_responses=responses,
                )
            logger.info(f"Execution Accuracy at step {state.global_step} | {ex_score}")

            # Log into tensorboard
            logger.info(f"Logging to TensorBoard: {ex_score}")
            for difficulty, score in ex_score.items():
                logger.info(f"Logging {difficulty}: {score}")
                self.tb_writer.add_scalar(
                    f"execution_accuracy/{difficulty}", score, state.global_step
                )
            self.tb_writer.flush()  # Force writing to disk

            state.log_history.append(
                {
                    "step": state.global_step,
                    "execution_accuracy": (
                        ex_score.get(self.filter_by[1])
                        if self.filter_by
                        else ex_score.get("overall")
                    ),
                    "selected_difficulty": (
                        self.filter_by[0] if self.filter_by else "overall"
                    ),
                }
            )
        return control

    def on_train_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        self.tb_writer.close()
        logger.info("TensorBoard writer closed")
