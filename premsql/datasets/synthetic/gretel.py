from pathlib import Path
from typing import Optional, Union

from datasets import load_dataset
from tqdm.auto import tqdm

from premsql.datasets.base import (
    SupervisedDatasetForTraining,
    Text2SQLBaseDataset,
    Text2SQLBaseInstance,
)
from premsql.logger import setup_console_logger
from premsql.prompts import BASE_TEXT2SQL_PROMPT
from premsql.utils import filter_options, save_to_json

logger = setup_console_logger("[GRETELAI-DATASET]")


class GretelAIInstance(Text2SQLBaseInstance):
    def __init__(self, dataset: list[dict]) -> None:
        super().__init__(dataset)

    def apply_prompt(
        self,
        num_fewshot: Optional[int] = None,
        prompt_template: Optional[str] = BASE_TEXT2SQL_PROMPT,
    ):
        prompt_template = (
            BASE_TEXT2SQL_PROMPT if prompt_template is None else prompt_template
        )
        for blob in tqdm(self.dataset, total=len(self.dataset), desc="Applying prompt"):
            few_shot_prompt = (
                ""
                if num_fewshot is None
                else self.add_few_shot_examples(db_id=blob["db_id"], k=num_fewshot)
            )
            final_prompt = prompt_template.format(
                schemas=blob["context"],
                additional_knowledge="",
                few_shot_examples=few_shot_prompt,
                question=blob["question"],
            )
            blob["prompt"] = final_prompt
        return self.dataset


class GretelAIDataset(Text2SQLBaseDataset):
    def __init__(
        self,
        split: Optional[str] = "train",
        dataset_folder: Optional[Union[str, Path]] = "./data",
        hf_token: Optional[str] = None,
        force_download: Optional[bool] = False,
    ):
        dataset_folder = Path(dataset_folder)
        dataset_path = dataset_folder / "gretel"
        if not dataset_path.exists() or force_download:
            dataset_path.mkdir(parents=True, exist_ok=True)
            dataset = []
            raw_dataset = load_dataset("gretelai/synthetic_text_to_sql", token=hf_token)

            for split in ["train", "test"]:
                for content in raw_dataset[split]:
                    blob_content = {
                        "id": content["id"],
                        "question": content["sql_prompt"],
                        "schema": content["sql_context"],
                        "SQL": content["sql"],
                        "context": content["sql_context"],
                        "task_type": content["sql_task_type"],
                        "complexity": content["sql_complexity"],
                        "db_id": content["domain"],
                        "db_path": None,
                    }
                    dataset.append(blob_content)

            save_to_json(save_path=dataset_path / "train.json", json_object=dataset)

        super().__init__(
            split="train",
            dataset_path=dataset_path,
            database_folder_name=None,
            json_file_name="train.json",
        )

    def setup_dataset(
        self,
        filter_by: Optional[tuple] = None,
        num_rows: Optional[int] = None,
        num_fewshot: Optional[int] = None,
        model_name_or_path: Optional[str] = None,
        prompt_template: Optional[str] = BASE_TEXT2SQL_PROMPT,
    ):
        if filter_by:
            self.dataset = filter_options(data=self.dataset, filter_by=filter_by)

        if num_rows:
            self.dataset = self.dataset[:num_rows]

        self.dataset = GretelAIInstance(dataset=self.dataset).apply_prompt(
            num_fewshot=num_fewshot, prompt_template=prompt_template
        )

        return SupervisedDatasetForTraining(
            dataset=self.dataset,
            model_name_or_path=model_name_or_path,
            hf_token=self.hf_token,
        )
