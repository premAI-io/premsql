import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

import sqlparse
from tqdm import tqdm

from text2sql.logger import setup_console_logger

logger = setup_console_logger(name="[GENERATOR]")


class BaseGenerator(ABC):
    def __init__(
        self, experiment_name: str, type: str, experiment_folder: Optional[str] = None
    ) -> None:
        """BaseGenerator is a base abstract class that can be extended for
        any kind of model / workflow based inferences. Each generation session
        is treated as a experiment and by default goes inside a ./experiment folder.

        Args:
            experiment_name (str): The name of the experiment
            type (str): The type of the experiment
            experiment_folder (Optional[str]): The folder in which all the generation results will be stored.
        """
        self.experiment_folder = (
            Path(experiment_folder)
            if experiment_folder is not None
            else Path("./experiments")
        )
        self.experiment_path = self.experiment_folder / type / experiment_name

        self.client = None

        if not self.experiment_path.exists():
            self.experiment_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created new experiment folder: {self.experiment_path}")
        else:
            logger.info(f"Experiment folder found in: {self.experiment_path}")

    @abstractmethod
    def generate(self, data_blob: dict, **kwargs: Optional[Any]) -> str:
        """The main generation logic

        Arguments
            data_blob (dict): Single blob of the dataset which should contain atleast the following keywords:
                - db_path (str): The path in which db file exists to connect
                - prompt (str): The main prompt
        """
        raise NotImplementedError

    def postprocess(self, output_string: str):
        sql_start_keywords = [
            r"\bSELECT\b",
            r"\bINSERT\b",
            r"\bUPDATE\b",
            r"\bDELETE\b",
            r"\bWITH\b",
        ]

        sql_start_pattern = re.compile("|".join(sql_start_keywords), re.IGNORECASE)
        match = sql_start_pattern.search(output_string)
        if match:
            start_pos = match.start()
            sql_statement = output_string[start_pos:]
            return sqlparse.format(sql_statement)
        else:
            return sqlparse.format(output_string)

    # TODO: Fuse execution with results

    def generate_and_save_results(
        self,
        data: List[dict],
        temperature: Optional[float] = 0.0,
        max_new_tokens: Optional[int] = 256,
        force: Optional[bool] = False,
        **kwargs: Optional[Any],
    ) -> dict:
        existing_response = self.load_results_from_folder()

        if existing_response is None or force == True:
            if force == True:
                logger.warn("Forcing evaluation results")

            to_dump = []
            for content in tqdm(data, total=len(data), desc="Generating results"):
                sql = self.postprocess(
                    self.generate(
                        data_blob=content,
                        temperature=temperature,
                        max_new_tokens=max_new_tokens,
                        **kwargs,
                    )
                )
                to_dump.append({**content, "generated": sql})

            # to_dump = data.data if hasattr(data, "data") else data
            json.dump(
                to_dump, open(self.experiment_path / "predict.json", "w"), indent=4
            )

            # Also write a .sql file in the same path
            sqls = []
            for content in to_dump:
                sqls.append(content["generated"])
            
            with open(self.experiment_path / "predict.sql", "w") as f:
                f.write("\n".join(sqls))

            logger.info(f"All responses are written to: {self.experiment_path}")
            return to_dump

        logger.info("Already results found")
        return existing_response

    def load_results_from_folder(self):
        item_names = [item.name for item in self.experiment_path.iterdir()]

        if self.experiment_path.exists() and "predict.json" in item_names:
            return json.load(open(self.experiment_path / "predict.json", "r"))
        return None
