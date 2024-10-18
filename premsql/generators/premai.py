import os
from typing import Optional

from premai import Prem

from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger

logger = setup_console_logger(name="[PREMAI-GENERATOR]")


class Text2SQLGeneratorPremAI(Text2SQLGeneratorBase):
    def __init__(
        self,
        model_name: str,
        project_id: str,
        experiment_name: str,
        type: str,
        experiment_folder: Optional[str] = None,
        premai_api_key: Optional[str] = None,
        **kwargs
    ):
        self.project_id = project_id
        self.premai_api_key = premai_api_key or os.environ.get("PREMAI_API_KEY")
        self._kwargs = kwargs
        self.model_name = model_name

        super().__init__(
            experiment_name=experiment_name,
            experiment_folder=experiment_folder,
            type=type,
        )

    @property
    def load_client(self) -> Prem:
        return Prem(api_key=self.premai_api_key)

    @property
    def load_tokenizer(self) -> None:
        pass

    @property
    def model_name_or_path(self) -> str:
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
        generated = (
            self.client.chat.completions.create(
                project_id=self.project_id,
                messages=[{"role": "user", "content": prompt}],
                **generation_config
            )
            .choices[0]
            .message.content
        )
        return self.postprocess(output_string=generated) if postprocess else generated
