import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Union

root_path: Path = Path("./text2sql")
curr_dt = str(datetime.now())

# Most of the file and folder paths needs to be fixed. Subject to change miggt
# cause error. So that needs to be handled accordingly. Some of the configs can be changed through the command line itself. 

@dataclass
class EvalConfig:
    eval_path: str = str("./data" / "eval" / "dev.json")
    dev_path: str = str("./experiments" / "eval" / "output")
    db_root_path: str = str("./data" / "eval" / "dev_databases")
    use_knowledge: bool = False
    mode: str = "dev"
    cot: bool = False
    data_output_path: str = str(
        root_path / "eval" / "exp_results" / f"model_output_{curr_dt}"
    )
    data_kg_output_path: str = str(
        root_path / "eval" / "exp_results" / f"model_output_kg_{curr_dt}"
    )

    # Engine
    engine: Literal["premai", "hf"] = "premai"

    # Configs for Evaluation for VES
    predicted_sql_path: str = str(
        root_path / "eval" / "exp_results" / f"model_output_{curr_dt}"
    )
    predicted_sql_path_kg = str(
        root_path / "eval" / "exp_results" / f"model_output_kg_{curr_dt}"
    )

    ground_truth_path: str = str(root_path / "data" / "eval")

    data_mode: str = "dev"
    mode_gt: str = "gt"
    mode_predict: str = "gpt"
    num_cpus: int = 16
    meta_time_out: float = 30.0

    diff_json_path: str = ""


@dataclass
class EvalAPIConfig:
    project_id: int = 4071
    premai_api_key: str = os.environ.get("PREMAI_API_KEY", None)
    model_name: str = "gpt-4o"
    max_tokens: int = (256,)
    temperature: Union[float, int] = (0,)
    stop: list[str] = (["--", "\n\n", ";", "#"],)


@dataclass
class EvalHFConfig:
    model_name: str = "phi3"
