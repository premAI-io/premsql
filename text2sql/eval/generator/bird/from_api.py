from typing import Optional

from premai import Prem

from text2sql.eval.generator.bird.base import BaseGenerator
from text2sql.eval.settings import APIConfig, SQLGeneratorConfig


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

        return result
