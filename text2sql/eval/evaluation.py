from premai import Prem

from text2sql.eval.base import BaseGenerator
from text2sql.settings import EvalAPIConfig


class EvalFromAPI(BaseGenerator):
    def __init__(self, engine_config: EvalAPIConfig):
        self.engine_config = engine_config
        self.client = Prem(api_key=engine_config.premai_api_key)

    def connect_model(
        self,
        prompt: str,
        max_tokens: int | None = 256,
        temperature: float | int | None = 0,
        stop: list[str] | None = ["--", "\n\n", ";", "#"],
    ) -> str:
        if isinstance(prompt, str):
            prompt = [{"role": "user", "content": prompt}]
        try:
            result = self.client.chat.completions.create(
                project_id=self.engine_config.project_id,
                model=self.engine_config.model_name,
                messages=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
            )
            result = result.choices[0].message.content
        except Exception as e:
            result = "error:{}".format(e)
        return result
