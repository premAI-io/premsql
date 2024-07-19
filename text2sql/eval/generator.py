import json
from abc import abstractmethod
from typing import List, Optional, Union

from premai import Prem
from tqdm import tqdm

from text2sql.eval.common import (
    decouple_question_schema,
    generate_combined_prompts_one,
    generate_sql_file,
)
from text2sql.settings import APIConfig, ModelConfig, SQLGeneratorConfig
from text2sql.eval.prompts import SYSTEM_PROMPT
import sqlparse


class BaseGenerator:
    def __init__(
        self,
        generator_config: SQLGeneratorConfig,
        engine_config: Union[APIConfig, ModelConfig],
    ) -> None:
        self.generator_config = generator_config
        self.engine_config = engine_config

        # we do this to ensure that everything is same all around
        self.generator_config.model_name = self.engine_config.model_name
        self.client = None

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def collect_response_from_gpt(
        self,
        db_path_list: List[str],
        question_list: List[str],
        knowledge_list: Optional[List[str]] = None,
        num_rows: Optional[int] = None,
    ) -> List[str]:
        """Returns list of generated SQL for evaluation"""
        response_list = []
        num_rows = len(question_list) if num_rows is None else num_rows
        question_list = question_list[:num_rows]

        for i, question in tqdm(enumerate(question_list), total=len(question_list)):
            if knowledge_list:
                curr_prompt = generate_combined_prompts_one(
                    db_path=db_path_list[i], question=question
                )
            else:
                curr_prompt = generate_combined_prompts_one(
                    db_path=db_path_list[i], question=question
                )
            sql = self.generate(prompt=curr_prompt)
            db_id = db_path_list[i].split("/")[-1].split(".sqlite")[0]
            sql = sql + "\t----- bird -----\t" + db_id
            response_list.append(sql)

        return response_list

    def generate_sql(self, num_rows: Optional[int] = None):
        eval_data = json.load(open(self.generator_config.eval_path, "r"))
        question_list, db_path_list, knowledge_list = decouple_question_schema(
            datasets=eval_data, db_root_path=self.generator_config.db_root_path
        )

        assert len(question_list) == len(db_path_list) == len(knowledge_list)
        if self.generator_config.use_knowledge == True:
            responses = self.collect_response_from_gpt(
                db_path_list=db_path_list,
                question_list=question_list,
                knowledge_list=knowledge_list,
                num_rows=num_rows,
            )
        else:
            responses = self.collect_response_from_gpt(
                db_path_list=db_path_list,
                question_list=question_list,
                num_rows=num_rows,
            )

        generate_sql_file(
            sql_lst=responses, output_path=self.generator_config.data_output_path
        )
        print(
            "successfully collect results from {} for {} evaluation; Use knowledge: {}; Use COT: {}".format(
                self.generator_config.model_name,
                self.generator_config.mode,
                self.generator_config.use_knowledge,
                self.generator_config.chain_of_thought,
            )
        )

    def get_sql_query(self, result: str) -> str:
        start = result.find("sql\n") + len("sql\n")
        end = result.find("\n```", start)
        sql_query = result[start:end]
        sql_query = sqlparse.format(sql_query, reindent=True, keyword_case="upper")
        return sql_query or ""


class SQLGeneratorFromAPI(BaseGenerator):
    def __init__(
        self, generator_config: SQLGeneratorConfig, engine_config: APIConfig
    ) -> None:
        super().__init__(generator_config=generator_config, engine_config=engine_config)
        self.client = Prem(api_key=self.engine_config.api_key)

    def generate(self, prompt: str) -> str:
        if isinstance(prompt, str):
            prompt = [{"role": "user", "content": prompt}]

        try:
            result = self.client.chat.completions.create(
                project_id=self.engine_config.project_id,
                model=self.engine_config.model_name,
                messages=prompt,
                max_tokens=self.engine_config.max_tokens,
                temperature=self.engine_config.temperature,
                stop=self.engine_config.stop,
            )
            result = result.choices[0].message.content
        except Exception as e:
            result = "error:{}".format(e)

        return self.get_sql_query(result=result)


class SQLGeneratorFromModel(BaseGenerator):
    def __init__(
        self, generator_config: SQLGeneratorConfig, engine_config: ModelConfig
    ):
        super().__init__(generator_config=generator_config, engine_config=engine_config)
        assert engine_config.backened in ["vllm", "huggingface", "hf"], ValueError(
            "Supported backends: 'vllm', 'huggingface' and 'hf'"
        )
        if engine_config.backened == "vllm":
            try:
                from vllm import LLM, SamplingParams
            except ImportError:
                print(
                    "Install vllm first. Head over their documentation: https://docs.vllm.ai/en/latest/getting_started/examples/offline_inference.html"
                )

            self.generation_config = SamplingParams(
                temperature=self.engine_config.temperature,
                max_tokens=self.engine_config.max_tokens,
                stop=self.engine_config.stop,
            )
            self.llm = LLM(model=engine_config.model_path)
        else:
            try:
                import torch
                from transformers import AutoModelForCausalLM, AutoTokenizer
                from transformers import GenerationConfig
            except ImportError:
                print("Install transformers by: pip install transformers")

            self.generation_config = GenerationConfig(
                temperature=self.engine_config.temperature,
                max_new_tokens=self.engine_config.max_tokens,
                stop=self.engine_config.stop,
            )
            self.llm = AutoModelForCausalLM.from_pretrained(
                pretrained_model_name_or_path=self.engine_config.model_path,
                **{
                    "device_map": self.engine_config.device,
                    "torch_dtype": torch.float16,
                }
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                pretrained_model_name_or_path=self.engine_config.model_path
            )

    def generate(self, prompt: str) -> str:
        if self.engine_config.backened == "vllm":
            output = self.llm.generate([prompt], self.generation_config)
            result = output.outputs[0].text
        else:
            prompt_template = SYSTEM_PROMPT + prompt
            prompt = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt_template}], tokenize=False
            )

            inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(
                self.engine_config.device
            )
            num_input_tokens = len(inputs)

            output = (
                self.llm.generate(
                    input_ids=inputs,
                    do_sample=False if self.engine_config.temperature == 0 else True,
                    generation_config=self.generation_config,
                    pad_token_id=self.tokenizer.eos_token_id,
                )
                .detach()
                .tolist()[0]
            )

            output_tokens = (
                output[num_input_tokens:] if len(output) > num_input_tokens else output
            )
            result = self.tokenizer.decode(output_tokens, skip_special_tokens=True)

        return self.get_sql_query(result=result)
