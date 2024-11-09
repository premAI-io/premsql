import os
from typing import Optional, Union

from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger

logger = setup_console_logger(name="[HF-GENERATOR]")

try:
    import torch
    import transformers
except ImportError:
    logger.warn("Ensure torch and transformers are installed.")
    logger.warn("Install them by: pip install torch transformers")

class Text2SQLGeneratorHF(Text2SQLGeneratorBase):
    def __init__(
        self,
        model_or_name_or_path: Union[str, "transformers.PreTrainedModel"],
        experiment_name: str,
        type: str,
        experiment_folder: Optional[str] = None,
        hf_token: Optional[str] = None,
        device: Optional[str] = None,
        **kwargs
    ):
        self.hf_api_key = os.environ.get("HF_TOKEN") or hf_token
        self._kwargs = kwargs
        self.device = (
            device
            if device is not None
            else ("cuda:0" if torch.cuda.is_available() else "cpu")
        )
        self.model_or_name_or_path = model_or_name_or_path
        super().__init__(
            experiment_name=experiment_name,
            experiment_folder=experiment_folder,
            type=type,
        )

    @property
    def load_client(self) -> "transformers.PreTrainedModel":
        if isinstance(self.model_or_name_or_path, str):
            return transformers.AutoModelForCausalLM.from_pretrained(
                pretrained_model_name_or_path=self.model_or_name_or_path,
                token=self.hf_api_key,
                **{
                    "device_map": self.device,
                    "torch_dtype": torch.float16,
                    **self._kwargs,
                }
            )
        return self.model_or_name_or_path

    @property
    def load_tokenizer(self) -> "transformers.PreTrainedTokenizer":
        tokenizer = transformers.AutoTokenizer.from_pretrained(
            pretrained_model_name_or_path=self.client.config.name_or_path,
            token=self.hf_api_key,
            padding_side="right",
        )
        tokenizer.pad_token = tokenizer.eos_token
        return tokenizer

    @property
    def model_name_or_path(self):
        return self.model_or_name_or_path

    def generate(
        self,
        data_blob: dict,
        temperature: Optional[float] = 0.0,
        max_new_tokens: Optional[int] = 256,
        postprocess: Optional[bool] = True,
        **kwargs
    ) -> str:

        prompt = data_blob["prompt"]
        input_ids = self.tokenizer.encode(
            text=prompt,
            return_tensors="pt",
            padding="longest",
            max_length=self.tokenizer.model_max_length,
            truncation=False,
        ).to(self.device)

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
        return self.postprocess(output_string=generated) if postprocess else generated
