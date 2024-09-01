import os
import torch
from typing import Optional, Union

import transformers
from text2sql.generator.base import BaseGenerator
from text2sql.logger import setup_console_logger
from text2sql.utils import execute_sql
from text2sql.prompts import ERROR_HANDLING_PROMPT


logger = setup_console_logger(name="[HF-EX]")


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
                "do_sample": False if temperature == 0.0 else True,
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
            output_tokens = (
                self.client.generate(
                    input_ids=input_ids,
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
            sql = self.postprocess(output_string=generated)

            error = execute_sql(dsn_or_db_path=data_blob["db_path"], sql=sql)
            if not error:
                return sql

            # Now at this stage some error is found
            if not error_already_found:
                prompt = data_blob["prompt"].split("# SQL:")[0].strip()
                error_prompt = ERROR_HANDLING_PROMPT.format(
                    existing_prompt=prompt, sql=sql, error_msg=error
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
