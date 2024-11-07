from typing import Optional

from premsql.generators.base import Text2SQLGeneratorBase
from premsql.logger import setup_console_logger

logger = setup_console_logger(name="[OLLAMA-GENERATOR]")

try:
    from ollama import Client
except ImportError:
    logger.warn("Ensure ollama is installed")
    logger.warn("Install Ollama: curl -fsSL https://ollama.com/install.sh | sh")
    logger.warn("Install Ollama python: pip install ollama")


class Text2SQLGeneratorOllama(Text2SQLGeneratorBase):
    def __init__(
        self, 
        model_name: str,
        experiment_name: str,
        type: str,
        experiment_folder: Optional[str]=None,
        **kwargs
    ):
        self._kwargs = kwargs
        self.model_name = model_name
        super().__init__(
            experiment_name=experiment_name,
            experiment_folder=experiment_folder,
            type=type
        )
    
    @property
    def load_client(self):
        return Client(host='http://localhost:11434')
    
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
        response = self.load_client.chat(
            model=self.model_name_or_path,
            messages=[{"role":"user", "content":prompt}],
            options=dict(
                temperature=temperature,
                num_ctx=2048 + max_new_tokens
            )
        )["message"]["content"]
        return self.postprocess(output_string=response) if postprocess else response
    