import json
from copy import deepcopy
from pathlib import Path
from typing import Optional, Sequence, Union

from transformers import AutoTokenizer

from text2sql.dataset.base import BaseDataset
from text2sql.dataset.bird.train import BirdTrainSet
from text2sql.dataset.domains.common import DomainDatasetBase
from text2sql.dataset.spider.common import SpiderDatasetBase
from text2sql.dataset.utils import tokenize_fn
from text2sql.evaluator.from_sqlite import EvaluatorFromSQLite
from text2sql.generator.huggingface import GeneratorHFModel
from text2sql.generator.premai import GeneratorPremAI
from text2sql.logger import setup_console_logger

IGNORE_INDEX = -100
logger = setup_console_logger("[ERROR-DATASET]")

# NOTE: Currently reasoning based error are not handled
# in this dataset


ERROR_HANDLING_PROMPT = """
{existing_prompt}

# Generated SQL: {sql}

## Error Message

{error_msg}

Carefully review the original question and error message, then rewrite the SQL query to address the identified issues. 
Ensure your corrected query uses correct column names, 
follows proper SQL syntax, and accurately answers the original question 
without introducing new errors.

# SQL: 
"""


class ErrorDataset(BaseDataset):
    def __init__(
        self,
        experiment_name: str,
        num_rows: Optional[int] = None,
        model_name_or_path: Optional[str] = None,
        tokenize: Optional[bool] = False,
        hf_token: Optional[str] = None,
    ):
        self.data = ErrorInstance.from_existing(experiment_name=experiment_name)
        if num_rows is not None:
            assert 0 < num_rows <= len(self.data), ValueError(
                f"num_rows should be more than 0 and less than or equal to {len(self.data)}"
            )
            self.data = self.data[:num_rows]

        self.tokenizer = (
            AutoTokenizer.from_pretrained(
                model_name_or_path, padding_size="right", token=hf_token
            )
            if model_name_or_path
            else None
        )
        self.tokenize = tokenize
        if self.tokenizer.chat_template:
            for content in self.data:
                content["dataset_type"] = "real"
                content["prompt"] = self.tokenizer.apply_chat_template(
                    [{"role": "user", "content": content["prompt"]}], tokenize=False
                )
        logger.info("Casted with the chat template")

        if self.tokenize:
            sources, targets = [], []

            for example in self.data:
                sources.append(example["prompt"])
                targets.append(f"{example['SQL']}{self.tokenizer.eos_token}")

            logger.info("=> Starting tokenization")
            data_dict = self.preprocess(sources=sources, targets=targets)

            self.input_ids = data_dict["input_ids"]
            self.labels = data_dict["labels"]
        else:
            self.input_ids, self.labels = None, None

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
        return len(self.data)

    def __getitem__(self, idx):
        if not self.tokenize:
            return dict(**self.data[idx])
        return dict(
            input_ids=self.input_ids[idx],
            labels=self.labels[idx],
            raw=dict(**self.data[idx]),
        )


class ErrorInstance:
    @classmethod
    def from_existing(cls, experiment_name: str) -> dict:
        path = Path("./experiments") / "train" / experiment_name / "error_dataset.json"
        if not path.exists():
            raise FileNotFoundError(f"Path {path} does not exists")
        return json.load(open(path, "r"))

    def __init__(
        self,
        datasets: Union[str, list[str], list[dict]],
        generator: Union[GeneratorPremAI, GeneratorHFModel],
        num_rows: Optional[int] = None,
    ) -> None:
        """Error dataset is a dataset type to create dataset from errors generated
        from the model of choice, such that the LLM can be made more error free by
        training using that dataset

        Points to strictly note:
        - The dataset can not come from a test / dev set
        - If you are bringing your own dataset, make sure it has the following keys:
            - question
            - SQL
            - db_path
            a db_path is important because we will run the generated SQL to the DB
        - You can also choose from the existing datasets. You can choose one or multiple
        Here are the supported keys as of now:
            - bird
            - spider
            - domains

        When you will define the generator, make sure the argument
        `type` is set to train not test.
        """

        self.datasets = datasets
        self.generator = generator
        model_name_or_path = (
            generator.model_or_name_or_path
            if isinstance(generator, GeneratorHFModel)
            else "gpt2"
        )
        tokenize = False

        if isinstance(self.datasets, str):
            self.datasets = [self.datasets]

        if all(isinstance(key, str) for key in self.datasets):
            valid_keys = ["bird", "spider", "domains"]
            for key in self.datasets:
                assert key in valid_keys, "Invalid key"

            # Initialize an empty list to store the unpacked lists from each dataset object
            combined_datasets = []

            # Conditionally unpack and extend datasets
            if "bird" in self.datasets:
                bird_dataset = BirdTrainSet(
                    data_path="./data",
                    model_name_or_path=model_name_or_path,
                    tokenize=tokenize,
                    num_rows=num_rows,
                )
                combined_datasets.extend(
                    bird_dataset.data
                )  # Assume the list property is called data_list

            if "spider" in self.datasets:
                spider_dataset = SpiderDatasetBase(
                    split="train",
                    data_path="./data",
                    model_name_or_path=model_name_or_path,
                    tokenize=tokenize,
                    num_rows=num_rows,
                )
                combined_datasets.extend(
                    spider_dataset.data
                )  # Assume the list property is called data_list

            if "domains" in self.datasets:
                domain_dataset = DomainDatasetBase(
                    split="train",
                    data_path="./data",
                    model_name_or_path=model_name_or_path,
                    tokenize=tokenize,
                    num_rows=num_rows,
                )
                combined_datasets.extend(
                    domain_dataset.data
                )  # Assume the list property is called data_list

            # Assign the combined list to self.datasets
            self.datasets = combined_datasets

        else:
            # If not all elements are strings, apply num_rows limitation if provided
            if num_rows is not None:
                self.datasets = self.datasets[:num_rows]

        self.evaluator = EvaluatorFromSQLite(
            experiment_path=self.generator.experiment_path
        )

    def generate_and_save(
        self, force: Optional[bool] = False, path_to_save: Optional[str] = None
    ):
        path_to_save = (
            (self.generator.experiment_path / "error_dataset.json")
            if path_to_save is None
            else Path(path_to_save)
        )

        if path_to_save.exists() and force == False:
            logger.info("Error dataset already exists")
            with open(path_to_save, "w") as json_file:
                data_to_return = json.load(json_file)
            return data_to_return

        responses = self.generator.generate_and_save_results(
            data=self.datasets, temperature=0.1, max_new_tokens=256, force=force
        )

        logger.info("Starting Evaluation")
        _ = self.evaluator.execution_accuracy(model_responses=responses)
        del responses
        # Now iterate over the error dataset

        with open(self.generator.experiment_path / "predict.json", "r") as file:
            error_dataset = json.load(file)

        data_to_return = []
        for content in error_dataset:
            # Assuming the prompt template has been the same for all
            error_msg = content["error"]
            if error_msg is not None:
                prompt = content["prompt"].split("# SQL:")[0].strip()
                sql = content["generated"]
                error_prompt = ERROR_HANDLING_PROMPT.format(
                    existing_prompt=prompt, sql=sql, error_msg=error_msg
                )
                data_to_return.append(
                    {
                        "question": content["question"],
                        "SQL": content["SQL"],
                        "prompt": error_prompt,
                        "db_path": content["db_path"],
                    }
                )

        with open(path_to_save, "w") as json_file:
            json.dump(data_to_return, json_file, indent=4)
        return data_to_return
