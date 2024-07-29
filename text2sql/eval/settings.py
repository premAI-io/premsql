import os
from dataclasses import dataclass, field
from typing import Optional, Union

from text2sql.eval.prompts.bird import SYSTEM_PROMPT


@dataclass
class SQLGeneratorConfig:
    eval_path: str = "./data/eval/dev.json"
    db_root_path: str = "./data/eval/"
    chain_of_thought: bool = False 
    databases_folder_name: str = "dev_databases/"
    mode: str = "dev"
    model_name: str = "default"
    use_knowledge: bool = False
    data_output_folder: str = field(init=False)
    data_output_path: str = field(init=False)
    engine: str = "prem"

    def __post_init__(self):
        self.data_output_folder = (
            f"./experiments/eval/{self.engine}_{self.model_name}_kg"
            if self.use_knowledge
            else f"./experiments/eval/{self.engine}_{self.model_name}"
        )

        self.data_output_path = os.path.join(
            self.data_output_folder,
            f"predict_{self.mode}{'_cot.json' if self.chain_of_thought else '.json'}",
        )


@dataclass
class MetricConfig:
    gt_path: str = "./data/eval/"
    num_cpus: int = 8
    diff_json_path: str = "./data/eval/dev.json"
    meta_time_out: float = 30.0
    num_rows: int = None


@dataclass
class APIConfig:
    model_name: str = "gpt-4o"
    project_id: int = 4071
    api_key: str = os.environ.get("PREMAI_API_KEY", None)
    max_tokens: int = (256,)
    temperature: Union[float, int] = (0,)
    stop: list[str] = (["--", "\n\n", ";", "#"],)
    system_prompt = SYSTEM_PROMPT


@dataclass
class ModelConfig:
    model_name: str = "default_model"
    model_path: Optional[str] = None
    device: str = "cuda"
    backend: str = "vllm"
    max_tokens: int = (256,)
    temperature: Union[float, int] = (0,)
    stop: list[str] = (["--", "\n\n", ";", "#"],)
    is_instruct: bool = False
    hf_token: str = os.environ.get("HF_TOKEN", None)
    system_prompt = SYSTEM_PROMPT

    def __post_init__(self):
        if self.model_path is None:
            self.model_path = self.model_name
