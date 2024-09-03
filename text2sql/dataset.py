import json
import sqlite3
from pathlib import Path
from textwrap import dedent
from typing import Optional

import torch
from tqdm import tqdm
from transformers import AutoTokenizer

from text2sql.logger import setup_console_logger
from text2sql.utils import _filter_options, get_random_few_shot_prompts

logger = setup_console_logger(name="[BIRD-DEV]")


class BirdDevInstance:
    def __init__(self, data: dict) -> None:

        assert "question" in data[0], "question is required"
        assert "SQL" in data[0], "sql is required"
        assert "db_path" in data[0], "db_path is required"
        self.data = data

    def __repr__(self) -> str:
        return str(json.dumps(self.data, indent=4))

    def schema_prompt(self, db_path: str) -> str:
        schema_list, schemas = [], {}

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        for table in tables:
            if table == "sqlite_sequence":
                continue
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='{}';".format(
                    table[0]
                )
            )
            schema = cursor.fetchone()[0]
            schemas[table[0]] = schema

        for _, v in schemas.items():
            schema_list.append(v)

        schema_prompt = "\n".join(schema_list)
        return dedent("# Database Schema:\n\n" + schema_prompt)

    def question_prompt(self, question: str) -> str:
        return f"# Question: {question}"

    def additional_prompt(self, prompt: str):
        return f"# Additional Knowledge: {prompt}"

    def add_few_shot_examples(self, db_id: str, k: int = 3) -> str:
        assert k > 0, "k should be greater than 0"
        few_shot_instructions = dedent(
            """
        # Here are some Examples on how to generate SQL statements and use column names
        """
        )
        db_fewshot_prompts_map = get_random_few_shot_prompts(
            dataset=self.data, num_few_shot=k
        )
        return few_shot_instructions + db_fewshot_prompts_map[db_id]

    def apply_prompt(
        self, system_prompt: Optional[str] = None, num_fewshot: Optional[int] = None
    ) -> str:
        system_prompt = (
            f"# Instruction: {system_prompt}"
            if system_prompt is not None
            else dedent(
                """
            # Instruction: 
            - You will be given a question and a database schema.
            - You need to write a SQL query to answer the question.
            Do not add ``` at start / end of the query. It should be a single line query in 
            a single line (string format).
            - Make sure the column names are correct and exists in the table
            - For column names which has a space with it, make sure you have put `` in that column name
            """,
            )
        )

        for blob in tqdm(self.data, total=len(self.data), desc="Applying prompt"):
            few_shot_prompt = (
                ""
                if num_fewshot is None
                else f"""
                {self.add_few_shot_examples(db_id=blob['db_id'], k=num_fewshot)}
                """
            )

            final_prompt = dedent(
                system_prompt
                + "\n"
                + self.schema_prompt(blob["db_path"])
                + few_shot_prompt
                + "\n"
                + self.additional_prompt(blob["evidence"])
                + self.question_prompt(blob["question"])
                + "\n\n"
                + "# SQL:"
            )
            blob["prompt"] = final_prompt

        return self.data


class BirdDevDataset(torch.utils.data.Dataset):
    def __init__(
        self,
        data_path: str,
        databases_folder_name: Optional[str] = "dev_databases",
        json_file_name: Optional[str] = "dev.json",
        system_prompt: Optional[str] = None,
        num_fewshot: Optional[int] = None,
        filter_by: Optional[tuple] = None,
        num_rows: Optional[int] = None,
        model_name_or_path: Optional[str] = None,
        hf_token: Optional[str] = None,
    ):
        self.path = Path(data_path)  # example: data/bird/dev
        data = json.load(open(self.path / json_file_name, "r"))
        for blob in data:
            blob["db_path"] = str(
                self.path
                / f"{databases_folder_name}"
                / blob["db_id"]
                / f"{blob['db_id']}.sqlite"
            )

        if filter_by is not None:
            data = _filter_options(
                data=data, filter_by=filter_by, accepted_keys=["db_id", "difficulty"]
            )

        if num_rows is not None:
            assert 0 < num_rows <= len(data), ValueError(
                f"num_rows should be more than 0 and less than or equal to {len(data)}"
            )
            data = data[:num_rows]

        bird_instance = BirdDevInstance(data=data)
        self.data = bird_instance.apply_prompt(
            system_prompt=system_prompt, num_fewshot=num_fewshot
        )
        self.tokenizer = (
            AutoTokenizer.from_pretrained(
                model_name_or_path, padding_size="right", token=hf_token
            )
            if model_name_or_path
            else None
        )

        if self.tokenizer.chat_template:
            for content in self.data:
                content["dataset_type"] = "real"
                content["prompt"] = self.tokenizer.apply_chat_template(
                    [{"role": "user", "content": content["prompt"]}], tokenize=False
                )
            logger.info("Casted with the chat template")

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        return dict(**self.data[idx])
