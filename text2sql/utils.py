import os
import json
import shutil
import random
import sqlite3
import requests
from pathlib import Path
from zipfile import ZipFile
from typing import Optional, Union
from textwrap import dedent
from collections import defaultdict

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


def load_results_from_json(result_json_path: str) -> dict:
    try:
        with open(result_json_path, "r") as json_file:
            return json.load(json_file)
    except Exception as e:
        logger.error(f"Unable to load JSON, Error: {e}")


def execute_sql(dsn_or_db_path: str, sql: str):
    conn = sqlite3.connect(dsn_or_db_path)
    cursor = conn.cursor()
    error = None
    try:
        cursor.execute(sql)
        conn.commit()
        return None
    except Exception as e:
        error = f"Error: {str(e)}"
    return error


def _filter_options(data: list[dict], filter_by: tuple, accepted_keys: list[str]):
    filter_key, filter_value = filter_by
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


def _bird_bench_dev_dataset_steps(download_path: Path, force: Optional[bool] = False):
    url = "https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip"
    zip_file = download_path / "dev.zip"
    unzip_dir = download_path / "dev_20240627"
    inner_zip_file = unzip_dir / "dev_databases.zip"
    macosx_dir = download_path / "__MACOSX"

    if not (download_path).exists() or force:
        logger.info(
            "=> Starting to download the dataset for evaluation [BirdBench devset]."
        )
        download_path.mkdir(parents=True, exist_ok=True)
        response = requests.get(url)

        with open(zip_file, "wb") as f:
            f.write(response.content)

        # Now extract
        with ZipFile(zip_file, "r") as zip_ref:
            zip_ref.extractall(download_path)
        os.remove(zip_file)

        with ZipFile(inner_zip_file, "r") as zip_ref:
            zip_ref.extractall(unzip_dir)
        os.remove(inner_zip_file)

        # Move things
        for item in os.listdir(unzip_dir):
            shutil.move(unzip_dir / item, download_path)
        os.rmdir(unzip_dir)

        if macosx_dir.exists():
            shutil.rmtree(macosx_dir, ignore_errors=True)

        logger.info(
            "=> Finished downloading the dataset for evaluation [BirdBench devset]."
        )
    else:
        logger.info("=> Dataset for evaluation [BirdBench devset] already exists.")


def download_and_process_bird_dataset(
    split: Optional[str] = "dev",
    download_folder: Optional[str] = "./data",
    force: Optional[bool] = False,
):
    assert split in ["train", "validation", "dev"], "Invalid split name"

    download_folder = Path(download_folder)
    download_path = download_folder / "bird" / split

    if split == "train":
        logger.error("This version is not supported for downloading train dataset.")
    else:
        _bird_bench_dev_dataset_steps(download_path, force)

    data_split = "train" if split == "train" else "dev"
    dataset = json.load(open(download_path / f"{data_split}.json", "r"))

    for blob in dataset:
        blob["db_path"] = str(
            download_path
            / f"{data_split}_databases"
            / blob["db_id"]
            / f"{blob['db_id']}.sqlite"
        )
    return dataset


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
