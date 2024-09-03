import json
import random
from collections import defaultdict
from pathlib import Path
from textwrap import dedent
from typing import Sequence, Union

from tqdm import tqdm
from transformers import PreTrainedTokenizer

from text2sql.logger import setup_console_logger

logger = setup_console_logger(name="[UTILS]")


def save_to_json(save_path: Union[str, Path], json_object: dict):
    try:
        save_path = Path(save_path) if isinstance(save_path, str) else save_path
        with open(save_path, "w") as json_file:
            json.dump(json_object, json_file, indent=4)
        logger.info(f"Saved JSON in: {save_path}")
    except Exception as e:
        logger.error(f"Unable to save JSON, Error: {e}")


def load_from_json(result_json_path: str) -> dict:
    try:
        with open(result_json_path, "r") as json_file:
            return json.load(json_file)
    except Exception as e:
        logger.error(f"Unable to load JSON, Error: {e}")


def get_random_few_shot_prompts(dataset: list[dict], num_few_shot: int):
    assert "db_id" in dataset[0], ValueError(
        "db_id key should be present to use this function"
    )

    grouped_content = defaultdict(list)
    few_shot_prompts = {}
    template = dedent(
        """
    Question: {question}
    SQL: {sql}
    """
    )

    for content in dataset:
        grouped_content[content["db_id"]].append(content)

    for db_id, contents in grouped_content.items():
        num_few_shot = min(num_few_shot, len(contents))
        random_sample = random.sample(contents, num_few_shot)

        few_shot_prompt = "".join(
            template.format(question=element["question"], sql=element["SQL"])
            for element in random_sample
        )
        few_shot_prompts[db_id] = few_shot_prompt
    return few_shot_prompts


def filter_options(data: list[dict], filter_by: tuple):
    filter_key, filter_value = filter_by

    not_to_filter = ["question", "SQL"]
    accepted_keys = [
        key for key in accepted_keys if key in data[0] if key not in not_to_filter
    ]

    assert filter_key in accepted_keys, ValueError(
        f"Filtering is supported for keys: `{''.join(accepted_keys)}`"
    )
    for key in accepted_keys:
        if filter_key == key:
            accepted_values = set([content[key] for content in data])
            assert filter_value in accepted_values, ValueError(
                f"Available values for key: {key} are: {', '.join(accepted_values)}"
            )

    filtered_data = [content for content in data if content[filter_key] == filter_value]
    return filtered_data


def tokenize_fn(strings: Sequence[str], tokenizer: PreTrainedTokenizer) -> dict:
    """Tokenizes a list of string"""
    tokenized_list = [
        tokenizer(
            text=text,
            return_tensors="pt",
            padding="longest",
            max_length=tokenizer.model_max_length,
            truncation=False,
        )
        for text in tqdm(strings, total=len(strings), desc="Tokenizing")
    ]
    input_ids = labels = [tokenized.input_ids[0] for tokenized in tokenized_list]
    input_ids_lens = label_ids_lens = [
        tokenized.input_ids.ne(tokenizer.pad_token_id).sum().item()
        for tokenized in tokenized_list
    ]
    return dict(
        input_ids=input_ids,
        labels=labels,
        input_ids_lens=input_ids_lens,
        label_ids_lens=label_ids_lens,
    )
