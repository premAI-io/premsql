import json
import os
import shutil
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

import requests

from text2sql.logger import setup_console_logger

logger = setup_console_logger("[UTILS]")


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
    split: Optional[str] = "train",
    download_folder: Optional[str] = "./data",
    force: Optional[bool] = False,
):
    assert split in ["train", "validation"], "Invalid split name"

    download_folder = Path(download_folder)
    download_path = download_folder / "bird" / split

    if split == "train":
        pass
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


download_and_process_bird_dataset(split="validation")
