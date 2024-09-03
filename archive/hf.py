import os 
import sqlite3
from collections import Counter
from typing import Optional, Union, Any

import torch
import torch.nn.functional as F
import transformers
from text2sql.generator.base import BaseGenerator
from text2sql.logger import setup_console_logger

logger = setup_console_logger(name="[GENERATOR-HF]")

def get_results(dsn_or_db_path: str, predicted_sql: str):
    try:
        conn = sqlite3.connect(dsn_or_db_path)
        cursor = conn.cursor()
        cursor.execute(predicted_sql)
        predicted_res = cursor.fetchall()
        return set(predicted_res)
    except Exception:
        return None 

def get_final_sql(data: list[dict], filter_by: str):
    if filter_by not in ["max_prob", "majority"]:
        raise ValueError("filter_by must be either 'max_prob' or 'majority'")

    if filter_by == "max_prob":
        max_prob = -1
        final_sql = ""
        result = None 
        for item in data.values():
            if item['prob'] > max_prob:
                max_prob = item['prob']
                final_sql = item['sql']
                result = item["result"]
        return final_sql

    elif filter_by == "majority":
        results = [str(item['result']) for item in data.values() if item['result'] is not None]
        if not results:
            return None  # No valid results found
        most_common_result = Counter(results).most_common(1)[0][0]
        for item in data.values():
            if str(item['result']) == most_common_result:
                return item['sql']
    return ""


import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional, Union

import sqlparse
from tqdm import tqdm

from text2sql.dataset.base import BaseDataInstance, BaseDataset
from text2sql.evaluator.from_sqlite import EvaluatorFromSQLite

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
        data: Union[BaseDataInstance, BaseDataset, List[dict]],
        temperature: Optional[float] = 0.0,
        max_new_tokens: Optional[int] = 256,
        force: Optional[bool] = False, 
        decode_strategy: Optional[str] = None,
        num_return_sequences: Optional[int] = 5,
        **kwargs: Optional[Any],
    ) -> dict:
        existing_response = self.load_results_from_folder()
        
        decode_strategy = decode_strategy if decode_strategy is not None else "No strategy"
        print(decode_strategy)
        
        logger.info(
            f"Going with decode strategy: {decode_strategy}"
        )

        if decode_strategy != "No strategy":
            assert decode_strategy in ["max_prob", "majority"], "Invalid option"

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
                        decode_strategy=None if decode_strategy == "No strategy" else decode_strategy,
                        num_return_sequences=num_return_sequences,
                        **kwargs,
                    )
                )
                to_dump.append({
                    **content,
                    "generated": sql
                })

            # to_dump = data.data if hasattr(data, "data") else data
            json.dump(
                to_dump, open(self.experiment_path / "predict.json", "w"), indent=4
            )
            logger.info(f"All responses are written to: {self.experiment_path}")
            return to_dump

        logger.info("Already results found")
        return existing_response

    def load_results_from_folder(self):
        item_names = [item.name for item in self.experiment_path.iterdir()]

        if self.experiment_path.exists() and "predict.json" in item_names:
            return json.load(open(self.experiment_path / "predict.json", "r"))
        return None


class GeneratorHFModel(BaseGenerator):
    def __init__(
        self,
        model_or_name_or_path: Union[str, transformers.PreTrainedModel],
        experiment_name: str,
        type: str,
        experiment_folder: Optional[str] = None,
        hf_token: Optional[str] = None,
        device: Optional[str] = None,
        **kwargs
    ):
        self.hf_api_key = os.environ.get("HF_TOKEN") or hf_token

        super().__init__(
            experiment_name=experiment_name,
            experiment_folder=experiment_folder,
            type=type,
        )

        self.device = (
            device
            if device is not None
            else ("cuda:0" if torch.cuda.is_available() else "cpu")
        )

        if isinstance(model_or_name_or_path, str):
            self.client = transformers.AutoModelForCausalLM.from_pretrained(
                pretrained_model_name_or_path=model_or_name_or_path,
                token=hf_token,
                **{"device_map": self.device, "torch_dtype": torch.float16, **kwargs}
            )
        else:
            self.client = model_or_name_or_path

        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            pretrained_model_name_or_path=self.client.config.name_or_path,
            token=hf_token,
            padding_side="right",
        )
        self.model_or_name_or_path = model_or_name_or_path
    
    
    def _get_generated_dict(self, blob: dict, input_ids: list[torch.Tensor], outputs: Any) -> dict:
        output_probabilities_dict = {}
        for i in range(len(outputs.sequences)):
            output_tokens = outputs.sequences[i].detach().tolist()
            output_tokens = (
                output_tokens[len(input_ids[0]):] if 
                len(output_tokens) > len(input_ids[0]) else output_tokens
            )
            scores = outputs.scores
            cumulative_prob = 1.0

            # TODO: Revisit this part to be mathemtically accurate as much as possible
            for j, token_logits in enumerate(scores):
                token_probs = F.softmax(token_logits[0], dim=-1)  
                token_prob = token_probs[output_tokens[j]].item()  
                cumulative_prob *= token_prob
            
            output_probabilities_dict[i] = {
                "tokens": output_tokens,
                "prob": cumulative_prob
            }
        
        for i in range(len(output_probabilities_dict)):
            tokens = output_probabilities_dict[i]["tokens"]
            decoded = self.tokenizer.decode(tokens, skip_special_tokens=True)

            output_probabilities_dict[i]["sql"] = decoded
            output_probabilities_dict[i]["result"] = get_results(blob["db_path"], decoded)

        return output_probabilities_dict


    def generate(
        self,
        data_blob: dict,
        temperature: Optional[float] = 0.0,
        max_new_tokens: Optional[int] = 256,
        decode_strategy: Optional[str] = None,
        num_return_sequences: Optional[int] = 5,
        **kwargs
    ):
        if decode_strategy is not None:
            assert decode_strategy in ["max_prob", "majority"], "Invalid option"
        
        prompt = data_blob["prompt"]
        input_ids = self.tokenizer.encode(
            text=prompt,
            return_tensors="pt",
            padding="longest",
            max_length=self.tokenizer.model_max_length,
            truncation=False,
        ).to(self.device)

        if decode_strategy is None:
            do_sample = False if temperature == 0.0 else True
            generation_config = transformers.GenerationConfig(
                **{**kwargs, "temperature": temperature, "max_new_tokens": max_new_tokens}
            )
            output_tokens = (
                self.client.generate(
                    input_ids=input_ids,
                    do_sample=do_sample,
                    generation_config=generation_config,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
                .detach()
                .tolist()[0]
            )
            output_tokens = (
                output_tokens[len(input_ids[0]) :]
                if len(output_tokens) > len(input_ids[0])
                else output_tokens
            )
            generated = self.tokenizer.decode(output_tokens, skip_special_tokens=True)
        else:
            temp = 0.7 if temperature == 0.0 else temperature
            generation_config = {
                **kwargs,
                "do_sample": True,
                "temperature": temp,
                "top_k": 50,
                "max_new_tokens": max_new_tokens,
                "num_return_sequences": num_return_sequences,
                "output_scores": True,  
                "return_dict_in_generate": True,  
                "pad_token_id": self.tokenizer.eos_token_id
            }
            outputs = self.client.generate(input_ids=input_ids, **generation_config)
            output_prob_map_dict = self._get_generated_dict(
                blob=data_blob, input_ids=input_ids, outputs=outputs
            )
            
            generated = get_final_sql(
                data=output_prob_map_dict,
                filter_by=decode_strategy
            )
        return generated
    


import sqlite3
from typing import Optional, Union

import transformers 
from text2sql.generator.huggingface import GeneratorHFModel
from text2sql.logger import setup_console_logger

logger = setup_console_logger(name="[HF-EX]")
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


class GeneratorHFModeWithExecution(GeneratorHFModel):
    def __init__(
        self,
        model_or_name_or_path: Union[str, transformers.PreTrainedModel],
        experiment_name: str,
        type: str,
        experiment_folder: Optional[str] = None,
        hf_token: Optional[str] = None,
        device: Optional[str] = None,
        **kwargs
    ):
        super().__init__(
            model_or_name_or_path=model_or_name_or_path,
            experiment_folder=experiment_folder,
            experiment_name=experiment_name,
            type=type,
            hf_token=hf_token,
            device=device,
            **kwargs
        )

    def generate(
        self, 
        data_blob: dict,
        temperature: Optional[float] = 0.0,
        max_new_tokens: Optional[int] = 256,
        **kwargs
    ):
        prompt = data_blob["prompt"] 
        generation_config = transformers.GenerationConfig(
            **{
                **kwargs, 
                "temperature": temperature, 
                "max_new_tokens": max_new_tokens,
                "do_sample": False if temperature == 0.0 else True
            }
        )
        input_ids = self.tokenizer.encode(
            text=prompt,
            return_tensors="pt",
            padding="longest",
            max_length=self.tokenizer.model_max_length,
            truncation=False,
        ).to(self.device)
        
        error_already_found = False
        max_retries = kwargs.get("max_retries", 1)

        for _ in range(max_retries):
            output_tokens = self.client.generate(
                input_ids=input_ids,
                generation_config=generation_config,
                pad_token_id=self.tokenizer.eos_token_id,
            ).detach().tolist()[0]
            output_tokens = (
                output_tokens[len(input_ids[0]) :]
                if len(output_tokens) > len(input_ids[0])
                else output_tokens
            )
            generated = self.tokenizer.decode(output_tokens, skip_special_tokens=True)
            sql = self.postprocess(output_string=generated)

            error = execute_sql(
                dsn_or_db_path=data_blob["db_path"], 
                sql=sql
            )
            if not error:
                return sql 
            
            # Now at this stage some error is found
            if not error_already_found:
                prompt = data_blob["prompt"].split("# SQL:")[0].strip()
                error_prompt = ERROR_HANDLING_PROMPT.format(
                    existing_prompt=prompt,
                    sql=sql,
                    error_msg=error
                )
                input_ids = self.tokenizer.encode(
                    text=error_prompt,
                    return_tensors="pt",
                    padding="longest",
                    max_length=self.tokenizer.model_max_length,
                    truncation=False,
                ).to(self.device)
                error_already_found = True
        return sql 

