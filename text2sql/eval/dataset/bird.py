import json
import os
import shutil
import sqlite3
from typing import Optional
from zipfile import ZipFile

import requests

import text2sql.eval.prompts.bird as prompts
from text2sql.eval.settings import SQLGeneratorConfig
from text2sql.logger import setup_console_logger

logger = setup_console_logger(name="text2sql-eval")


class DataInstance:
    def __init__(self, config: SQLGeneratorConfig, processed_data: dict) -> None:
        self.config = config
        self.processed_data = processed_data

    def __repr__(self) -> str:
        return str(json.dumps(self.processed_data, indent=4))

    def generate_schema_prompt(self, db_path) -> list[str]:
        """Returns a list of string which contains the schema of different tables"""
        schema_list = []
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        schemas = {}
        for table in tables:
            if table == "sqlite_sequence":
                continue
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='{}';".format(
                    table[0]
                )
            )
            create_prompt = cursor.fetchone()[0]
            schemas[table[0]] = create_prompt

        for _, v in schemas.items():
            schema_list.append(v)
        schema_prompt = "\n\n".join(schema_list)
        return schema_prompt

    def generate_comment_prompt(
        self, question: str, knowledge: Optional[str] = None
    ) -> str:
        """Returns the instruction prompt with or without
        knowledge
        """
        question_prompt = "-- {}".format(question)
        knowledge_prompt = "-- External Knowledge: {}".format(knowledge)

        if not knowledge_prompt:
            result_prompt = prompts.PATTERN_PROMPT_NO_KG + "\n" + question_prompt
        else:
            result_prompt = (
                knowledge_prompt
                + "\n"
                + prompts.PATTERN_PROMPT_KG
                + "\n"
                + question_prompt
            )
        return result_prompt

    # Chain of Thought is applied by default here
    def apply_prompt(
        self,
        apply_knowledge: Optional[bool] = False,
        header_prompt: Optional[str] = None,
    ) -> str:
        """Combines different parts of the prompt to generate a single prompt

        Args:
            db_path (str): the path of the
        """
        for content in self.processed_data:
            schema_prompt = self.generate_schema_prompt(db_path=content["db_path"])
            comment_prompt = self.generate_comment_prompt(
                question=content["question"],
                knowledge=None if apply_knowledge is False else content["evidence"],
            )
            combined = (
                schema_prompt
                + "\n\n"
                + comment_prompt
                + prompts.COT_WIZARD
                + "\nSELECT "
            )
            combined = header_prompt + combined if header_prompt else combined
            content["prompt"] = combined
        return self.processed_data


class BirdBenchEvalDataset:
    def __init__(self, config: SQLGeneratorConfig) -> None:
        self.config = config

    @property
    def data(self) -> dict:
        return self.download(download_path=self.config.db_root_path, force=False)

    def process_and_filter(
        self, filter_by: Optional[tuple] = None, num_rows: Optional[int] = None
    ) -> dict:
        """
        Preprocesses the raw dataset and filters out either by difficulty level or database of choice.

        Args:
            filter_by (Optional[tuple], optional): Filters data by difficulty or db_id. Defaults to None.
            num_rows (Optional[int], optional): Acts as an offset to take a sample. Defaults to None.

        Returns:
            dict: A data dictionary with relevant database paths, based on filtering and offset.

        Example usage:
            from text2sql.eval.dataset.bird import BirdBenchEvalDataset
            eval_data = BirdBenchEvalDataset(path=config)
            data = eval_data.data
            processed_data = eval_data.process_and_filter(
                filter_by=("difficulty", "challenging"),
                num_rows=10
            )
        """
        data = self.data

        if filter_by is not None:
            filter_key, filter_value = filter_by
            assert filter_key in ["db_id", "difficulty"], ValueError(
                "Filtering is supported for keys: 'db_id' and 'difficulty'"
            )
            if filter_key == "difficulty":
                assert filter_value in [
                    "simple",
                    "moderate",
                    "challenging",
                ], ValueError(
                    "difficulty can either be: 'simple' or 'moderate' or 'challenging'"
                )
            else:
                available_dbs = set([content["db_id"] for content in data])
                assert filter_value in available_dbs, ValueError(
                    f"available_dbs: {', '.join(available_dbs)}"
                )
            data = [content for content in data if content[filter_key] == filter_value]

        processed_data = []
        for content in data:
            curr_db_path = (
                self.config.db_root_path
                + self.config.databases_folder_name
                + content["db_id"]
                + "/"
                + content["db_id"]
                + ".sqlite"
            )
            content["db_path"] = curr_db_path
            processed_data.append(content)

        if num_rows is not None:
            assert 0 < num_rows < len(processed_data), ValueError(
                f"num_rows should be more than 0 and less than {len(processed_data)}"
            )
            processed_data = processed_data[:num_rows]

        return DataInstance(config=self.config, processed_data=processed_data)

    def download(
        self,
        download_path: Optional[str] = "./data/eval",
        force: Optional[bool] = False,
    ):
        url = "https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip"
        zip_file = os.path.join(download_path, "dev.zip")
        unzip_dir = os.path.join(download_path, "dev_20240627")
        inner_zip_file = os.path.join(unzip_dir, "dev_databases.zip")
        macosx_dir = os.path.join(download_path, "__MACOSX")

        def perform_download_and_extraction():
            os.makedirs(download_path, exist_ok=True)
            logger.info(
                "=> Starting to download the dataset for evaluation [BirdBench devset]."
            )
            response = requests.get(url)
            with open(zip_file, "wb") as f:
                f.write(response.content)

            with ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(download_path)
            os.remove(zip_file)

            with ZipFile(inner_zip_file, "r") as zip_ref:
                zip_ref.extractall(unzip_dir)
            os.remove(inner_zip_file)

            for item in os.listdir(unzip_dir):
                shutil.move(os.path.join(unzip_dir, item), download_path)
            os.rmdir(unzip_dir)
            if os.path.exists(macosx_dir):
                shutil.rmtree(macosx_dir)

            logger.info("Download and extraction complete.")

        if os.path.isdir(download_path):
            if force:
                logger.warn(f"Cleaning up {download_path} as --force is used.")
                for item in os.listdir(download_path):
                    item_path = os.path.join(download_path, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                perform_download_and_extraction()
            else:
                logger.info(
                    f"{download_path} is not empty. Use force=True to re-download and overwrite the contents."
                )
        else:
            perform_download_and_extraction()

        return json.load(open(os.path.join(download_path, "dev.json"), "r"))
