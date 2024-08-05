import json
import os
import re
from abc import ABC, abstractmethod
from typing import Optional, Union

from tqdm import tqdm

from text2sql.eval.settings import APIConfig, ModelConfig, SQLGeneratorConfig
from text2sql.logger import setup_console_logger

logger = setup_console_logger(name="text2sql-eval")


class BaseGenerator(ABC):
    def __init__(
        self,
        generator_config: SQLGeneratorConfig,
        engine_config: Union[APIConfig, ModelConfig],
    ) -> None:
        self.generator_config = generator_config
        self.engine_config = engine_config

        self.generator_config.model_name = self.engine_config.model_name
        self.client = None

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_sql_file(self, response_list: list[str]) -> dict[int, str]:
        """Returns the final result with the sql file to execute"""
        if self.generator_config.data_output_path:
            directory_path = os.path.dirname(self.generator_config.data_output_path)
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            json.dump(
                response_list,
                open(self.generator_config.data_output_path, "w"),
                indent=4,
            )
            logger.info(
                f"all responses written to {self.generator_config.data_output_path}"
            )

    def generate_and_save_results(
        self,
        data: list[dict],
        postprocess: Optional[callable] = lambda x:x,
        force: Optional[bool] = False,
    ) -> dict:
        assert "prompt" in data[0], ValueError(
            "key: 'prompt' is not present in data. Please process it first"
        )
        result_from_folder = self.load_from_folder()

        def _generate(data):
            for content in tqdm(data, total=len(data)):
                sql = self.generate(prompt=content["prompt"], postprocess=postprocess)
                content["generated"] = sql
            self.generate_sql_file(response_list=data)
            return data

        if result_from_folder is None:
            return _generate(data)
        else:
            if force:
                logger.warn("Forcing generations")
                return _generate(data)
            return result_from_folder

    def load_from_folder(self):
        if os.path.exists(self.generator_config.data_output_path):
            logger.info("Already found results from folder")
            return json.load(open(self.generator_config.data_output_path, "r"))
        return None
