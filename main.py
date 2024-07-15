import os
from typing import Optional

import typer
from text2sql.eval.evaluation import EvalFromAPI
from text2sql.settings import EvalAPIConfig, EvalConfig, EvalHFConfig

app = typer.Typer()

default_eval_config = EvalConfig()

# Command line will only have those parameters which needs to be tweaked 
# for experimentation. Others are kept fixed. However if you want to change
# then you can do that inside settings. In those cases, code might needs to 
# change. 


@app.command()
def generate_sql_for_eval(
    db_root_path: Optional[str] = default_eval_config.db_root_path,
    engine: Optional[str] = "prem",
    model_name: Optional[str] = "gpt-4o",
    eval_path: Optional[str] = default_eval_config.eval_path,
    data_output_path: Optional[str] = default_eval_config.data_kg_output_path, 
    use_knowledge: Optional[bool] = False,
    chain_of_thought: Optional[bool] = default_eval_config.cot

):
    typer.echo("Starting to generate SQL for eval")
    if engine == "premai":
        api_config = EvalAPIConfig(model_name=model_name)
        eval_engine = ... 
    else:
        raise NotImplementedError
