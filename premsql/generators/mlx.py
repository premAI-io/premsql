import os 
from typing import Optional
from mlx_lm import generate
from mlx_lm.utils import load_model, get_model_path
from mlx_lm.tokenizer_utils import load_tokenizer
from mlx_lm.tuner.utils import apply_lora_layers

from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger

logger = setup_console_logger(name="[MLX-GENERATOR]")

class Text2SQLGeneratorMLX(Text2SQLGeneratorBase):
    def __init__(
        self, 
        model_name_or_path: str,
        experiment_name: str,
        type: str,
        experiment_folder: Optional[str] = None,
        hf_token: Optional[str] = None,
        **kwargs
    ):
        self.hf_api_key = os.environ.get("HF_TOKEN") or hf_token
        self._kwargs = kwargs
        self.mlx_model_name_or_path = model_name_or_path
        super().__init__(
            experiment_name=experiment_name,
            experiment_folder=experiment_folder,
            type=type,
        )
    
    @property
    def load_client(self):
        model_path = get_model_path(self.model_name_or_path)
        model = load_model(model_path, **self._kwargs)
        if self._kwargs.get("adapter_path", None) is not None:
            model = apply_lora_layers(model, self._kwargs["adapter_path"])
            model.eval()    
        return model 
    
    @property
    def load_tokenizer(self):
        model_path = get_model_path(self.model_name_or_path)
        return load_tokenizer(model_path, **self._kwargs)
    
    @property
    def model_name_or_path(self):
        return self.mlx_model_name_or_path

    def generate(
        self, 
        data_blob: dict, 
        temperature: Optional[float] = 0.0,
        max_new_tokens: Optional[int] = 256,
        postprocess: Optional[bool] = True,
        **kwargs
    ) -> str:
        prompt = data_blob["prompt"]
        temp = temperature
        generation_args = {
            "temp": temp,
            **kwargs
        }
        output = generate(
            model=self.client,
            tokenizer=self.tokenizer,
            prompt=prompt,
            max_tokens=max_new_tokens,
            **generation_args
        )
        return self.postprocess(output) if postprocess else output