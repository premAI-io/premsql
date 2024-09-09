import os
from typing import Optional

from premsql.generators.base import Text2SQLGeneratorBase

try:
    from openai import OpenAI
except ImportError:
    raise ImportError("Module openai is not installed")


class Text2SQLGeneratorOpenAI(Text2SQLGeneratorBase):
    def __init__(
        self,
        model_name: str,
        experiment_name: str,
        type: str,
        experiment_folder: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):
        self._api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = model_name
        super().__init__(
            experiment_folder=experiment_folder,
            experiment_name=experiment_name,
            type=type,
        )

    @property
    def load_client(self):
        client = OpenAI(api_key=self._api_key)
        return client

    @property
    def load_tokenizer(self):
        pass

    @property
    def model_name_or_path(self):
        return self.model_name

    def generate(
        self,
        data_blob: dict,
        temperature: Optional[float] = 0.0,
        max_new_tokens: Optional[int] = 256,
        postprocess: Optional[bool] = True,
        **kwargs
    ) -> str:
        prompt = data_blob["prompt"]
        max_tokens = max_new_tokens
        generation_config = {
            **kwargs,
            **{"temperature": temperature, "max_tokens": max_tokens},
        }
        completion = (
            self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                **generation_config
            )
            .choices[0]
            .message.content
        )
        return self.postprocess(output_string=completion) if postprocess else completion
