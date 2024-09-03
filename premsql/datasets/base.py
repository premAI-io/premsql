import json
import os
import sqlite3
from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Optional, Sequence, Union

import torch
from tqdm import tqdm
from transformers import AutoTokenizer

from text2sql.datasets.prompts import OLD_BASE_TEXT2SQL_PROMPT
from text2sql.datasets.utils import (
    filter_options,
    get_random_few_shot_prompts,
    tokenize_fn,
)
from text2sql.logger import setup_console_logger

logger = setup_console_logger(name="[DATASET]")

IGNORE_INDEX = -100


class Text2SQLBaseInstance(ABC):
    def __init__(self, dataset: list[dict]) -> None:

        assert "question" in dataset[0], "question is required"
        assert "SQL" in dataset[0], "sql is required"
        assert "db_path" in dataset[0], "db_path is required"
        assert "db_id" in dataset[0], "db_id is required"

        self.dataset = dataset

    def __repr__(self) -> str:
        return str(json.dumps(self.dataset[:3], indent=4))

    def __len__(self) -> int:
        return len(self.dataset)

    def __getitem__(self, idx: int) -> dict:
        return dict(**self.dataset[idx])

    @abstractmethod
    def schema_prompt(self, db_path: str) -> str:
        schemas = {}
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            if table_name == "sqlite_sequence":
                continue
            cursor.execute(
                f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';"
            )
            create_table_sql = cursor.fetchone()
            if create_table_sql:
                schemas[table_name] = create_table_sql[0]
            else:
                schemas[table_name] = "Schema does not exist"

        schema_prompt = "\n".join(schemas[table[0]] for table in tables if table[0])
        return schema_prompt

    def additional_prompt(self, prompt: Optional[str] = None):
        return "" if prompt is None else f"# Additional Knowledge:\n{prompt}"

    def add_few_shot_examples(self, db_id: str, k: int = 3) -> str:
        assert k > 0, "k should be greater than 0"
        db_fewshot_prompts_map = get_random_few_shot_prompts(
            dataset=self.dataset, num_few_shot=k
        )
        return db_fewshot_prompts_map[db_id]

    @abstractmethod
    def apply_prompt(
        self,
        num_fewshot: Optional[int] = None,
        prompt_template: Optional[str] = OLD_BASE_TEXT2SQL_PROMPT,
    ):
        for blob in tqdm(self.dataset, total=len(self.dataset), desc="Applying prompt"):
            few_shot_prompt = (
                ""
                if num_fewshot is None
                else self.add_few_shot_examples(db_id=blob["db_id"], k=num_fewshot)
            )
            final_prompt = prompt_template.format(
                schemas=self.schema_prompt(blob["db_path"]),
                additional_knowledge=(
                    ""
                    if "knowledge" not in blob
                    else self.additional_prompt(blob["knowledge"])
                ),
                few_shot_examples=few_shot_prompt,
                question=blob["question"],
            )
            blob["prompt"] = final_prompt
        return self.dataset


class SupervisedDatasetForTraining(torch.utils.data.Dataset):
    def __init__(
        self, dataset: dict, model_name_or_path: str, hf_token: Optional[str] = None
    ):
        self.tokenizer = AutoTokenizer.from_pretrained(
            pretrained_model_name_or_path=model_name_or_path,
            padding_side="right",
            token=hf_token,
        )

        assert "prompt" in dataset[0], "key prompt is required"
        assert "SQL" in dataset[0], "key SQL is required"
        self.dataset = dataset

        if self.tokenizer.chat_template:
            for content in self.dataset:
                content["prompt"] = self.tokenizer.apply_chat_template(
                    [{"role": "user", "content": content["prompt"]}], tokenize=False
                )
            logger.info("Casted dataset with model chat template")

        logger.info("Starting Tokenization ...")
        sources, targets = [], []
        for example in self.dataset:
            sources.append(example["prompt"])
            targets.append(f"{example['SQL']}{self.tokenizer.eos_token}")

        data_dict = self.preprocess(sources=sources, targets=targets)
        self.input_ids = data_dict["input_ids"]
        self.labels = data_dict["labels"]

    def preprocess(self, sources: Sequence[str], targets: Sequence[str]):
        examples = [s + t for s, t in zip(sources, targets)]
        examples_tokenized, sources_tokenized = [
            tokenize_fn(strings, self.tokenizer) for strings in (examples, sources)
        ]
        input_ids = examples_tokenized["input_ids"]
        labels = deepcopy(input_ids)

        for label, source_len in zip(labels, sources_tokenized["input_ids_lens"]):
            label[:source_len] = IGNORE_INDEX

        return dict(input_ids=input_ids, labels=labels)

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx: int):
        return dict(
            input_ids=self.input_ids[idx],
            labels=self.labels[idx],
            raw=dict(**self.dataset[idx]),
        )


class Text2SQLBaseDataset(ABC):
    def __init__(
        self,
        split: str,
        dataset_path: Union[str, Path],
        database_folder_name: str,
        json_file_name: str,
        hf_token: Optional[str] = None,
    ):
        self.dataset_path = Path(dataset_path)
        self.database_folder_name = database_folder_name
        self.dataset = json.load(open(self.dataset_path / json_file_name, "r"))
        assert split in ["train", "validation"], ValueError(
            "Split should be either train or validation"
        )
        self.split = split
        self.hf_token = hf_token if hf_token else os.environ.get("HF_TOKEN", None)

    @abstractmethod
    def setup_dataset(
        self,
        filter_by: Optional[tuple] = None,
        num_rows: Optional[int] = None,
        num_fewshot: Optional[int] = None,
        model_name_or_path: Optional[str] = None,
        prompt_template: Optional[str] = OLD_BASE_TEXT2SQL_PROMPT,
    ):
        for content in self.dataset:
            content["db_path"] = str(
                self.dataset_path
                / f"{self.database_folder_name}"
                / content["db_id"]
                / f"{content['db_id']}.sqlite"
            )

        if filter_by:
            self.dataset = filter_options(data=self.dataset, filter_by=filter_by)

        if num_rows:
            self.dataset = self.dataset[:num_rows]

        self.dataset = Text2SQLBaseInstance(data=self.dataset).apply_prompt(
            num_fewshot=num_fewshot, prompt_template=prompt_template
        )
        return (
            self.dataset
            if self.split != "train"
            else SupervisedDatasetForTraining(
                dataset=self.dataset,
                model_name_or_path=model_name_or_path,
                hf_token=self.hf_token,
            )
        )

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        return dict(**self.dataset[idx])
