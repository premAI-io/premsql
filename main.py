import os
from typing import Optional 

import typer
from text2sql.eval.evaluation import EvalFromAPI
from text2sql.settings import EvalAPIConfig, EvalConfig
from text2sql.eval.evaluator import evaluate_sql
app = typer.Typer()

default_eval_config = EvalConfig()

# Command line will only have those parameters which needs to be tweaked 
# for experimentation. Others are kept fixed. However if you want to change
# then you can do that inside settings. In those cases, code might needs to 
# change. 

@app.command()
def version():
    typer.echo("version+v1.0.1")


@app.command()
def download_data(type: Optional[str]="eval", force: Optional[bool]=False):
    if type == "eval":
        command = f"./data/download.sh {'--force' if force else ''}"
        os.system(command)   
    else:
        typer.echo("Downloading for eval is only supported now")

@app.command()
def evaluate(
    engine: str,
    model_name: str,
    use_knowledge: Optional[bool] = False,
    chain_of_thought: Optional[bool] = False,
    temperature: float = 0,
    max_tokens: Optional[int] = 256,
    stop: Optional[list[str]] = (["--", "\n\n", ";", "#"],)
):
    typer.echo("Starting to generate SQL for eval ...")
    assert engine in ["prem", "hf"], ValueError(
        "Supported engines: 'prem' and 'hf'"
    )
    eval_config = EvalConfig(use_knowledge=use_knowledge, cot=chain_of_thought)
    if engine == "prem":
        api_config = EvalAPIConfig(
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop
        ) 
        eval_client = EvalFromAPI(engine_config=api_config)
        eval_client.generate_sql(
            eval_config=eval_config,
            temperature=temperature,
            max_tokens=max_tokens,
            stop=stop, 
            model_name=api_config.model_name
        )
    else:
        eval_client = None
        raise NotImplementedError
    
    typer.echo("Starting to evaluate Generated SQL ...")
    evaluate_sql(
        predicted_sql_path=eval_config.predicted_sql_path,
        ground_truth_path=eval_config.ground_truth_path,
        db_root_path=eval_config.db_root_path,
        num_cpus=eval_config.num_cpus,
        diff_json_path=eval_config.diff_json_path,
        data_mode=eval_config.data_mode
    )


if __name__ == "__main__":
    app()