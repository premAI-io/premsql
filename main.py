import os
from typing import Optional, Literal, Union 

import typer
from text2sql.eval.evaluation import EvalFromAPI
from text2sql.settings import EvalAPIConfig, EvalConfig

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
    eval_client.evaluate(eval_config)

if __name__ == "__main__":
    app()