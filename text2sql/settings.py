import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Union

root_path: Path = Path("./text2sql-slm")


@dataclass
class EvalConfig:
    eval_path: str = str(root_path / "data" / "dev.json")
    mode: str = "dev"
    test_path: str = ""
    use_knowledge: bool = False
    db_root_path: str = ""
    data_output_path: str = None
    chain_of_thought: str = None
    engine: Literal["premai", "hf"] = "premai"

    # Configs for Evaluation for VES
    predicted_sql_path: str = ""
    ground_truth_path: str = ""
    data_mode: str = ""
    db_root_path: str = ""
    num_cpus: str = ""
    meta_time_out: float = 30.0
    # gt: ground-truth, and gpt: preicted
    mode_gt: str = "gt"
    mode_predict: str = "gpt"
    diff_json_path: str = ""


@dataclass
class EvalAPIConfig:
    project_id: int = None
    premai_api_key: str = os.environ.get("PREMAI_API_KEY", None)
    model_name: str = "gpt-4o"
    max_tokens: int = (256,)
    temperature: Union[float, int] = (0,)
    stop: list[str] = (["--", "\n\n", ";", "#"],)


@dataclass
class EvalHFConfig:
    model_name: str = "phi3"
