import os
from typing import Optional

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig

from text2sql.eval.generator.bird.base import BaseGenerator
from text2sql.eval.settings import ModelConfig, SQLGeneratorConfig

# TODO: Currently we are assuming it will be a causal model instead of Seq2Seq


class SQLGeneratorFromModel(BaseGenerator):
    def __init__(
        self, generator_config: SQLGeneratorConfig, engine_config: ModelConfig
    ):
        super().__init__(generator_config=generator_config, engine_config=engine_config)
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        gen_config = {
            "max_new_tokens": self.engine_config.max_tokens,
            "stop": self.engine_config.stop,
        }
        if self.engine_config.temperature > 0:
            gen_config = {**gen_config, "temperature": self.engine_config.temperature}

        self.generation_config = GenerationConfig(**gen_config)

        self.llm = AutoModelForCausalLM.from_pretrained(
            pretrained_model_name_or_path=self.engine_config.model_path,
            token=self.engine_config.hf_token,
            **{
                "device_map": self.engine_config.device,
                "torch_dtype": torch.float16,
            }
        )
        self.llm.generation_config.temperature = None
        self.llm.generation_config.top_p = None
        self.tokenizer = AutoTokenizer.from_pretrained(
            pretrained_model_name_or_path=self.engine_config.model_path,
            token=self.engine_config.hf_token,
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        system_prompt = (
            system_prompt if system_prompt is not None else ModelConfig.system_prompt
        )
        prompt_template = system_prompt + "\n" + prompt

        if self.engine_config.is_instruct:
            prompt = self.tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt_template}], tokenize=False
            )
        else:
            prompt = prompt_template

        inputs = self.tokenizer.encode(prompt, return_tensors="pt").to(
            self.engine_config.device
        )
        num_input_tokens = len(inputs[0])

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
        return result 
