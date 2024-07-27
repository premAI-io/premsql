import os
from typing import Optional

import typer
from text2sql.eval.generator import SQLGeneratorFromAPI
from text2sql.settings import APIConfig, SQLGeneratorConfig, MetricConfig
from text2sql.eval.executor import SQLExecutorEX
from text2sql.eval.ves import SQLVesEvaluator

app = typer.Typer()

@app.command()
def version():
    typer.echo("version+v1.0.1")


@app.command()
def download_data(type: Optional[str] = "eval", force: Optional[bool] = False):
    if type == "eval":
        command = f"./data/download.sh {'--force' if force else ''}"
        os.system(command)
    else:
        typer.echo("Downloading for eval is only supported now")


@app.command()
def generate_dev(
    engine: str,
    model_name: str,
    metric: Optional[str] = "acc",
    num_rows: Optional[int] = None,
    use_knowledge: Optional[bool] = False,
    chain_of_thought: Optional[bool] = False,
    temperature: float = 0,
    max_tokens: Optional[int] = 256,
    stop: Optional[list[str]] = (["--", "\n\n", ";", "#"],),
):
    typer.echo("Starting to generate SQL for eval ...")
    assert engine in ["prem", "hf"], ValueError("Supported engines: 'prem' and 'hf'")
    assert metric in ["acc", "ves", "both"], ValueError(
        "Argument metric should be either: 'acc' or 'ves' or 'both'"
    )

    generator_config = SQLGeneratorConfig(
        model_name=model_name,
        use_knowledge=use_knowledge,
        chain_of_thought=chain_of_thought,
        engine=engine,
    )

    if engine == "prem":
        api_config = APIConfig(
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            stop=stop,
        )
        client = SQLGeneratorFromAPI(
            generator_config=generator_config, engine_config=api_config
        )

        client.generate_sql(num_rows=num_rows)

        metric_config = MetricConfig()
        metric_config.num_rows = num_rows

        # Doing execution here
        if metric == "acc":
            executor = SQLExecutorEX()
            _ = executor.execute_ex(
                generator_config=generator_config,
                metric_config=metric_config,
                num_rows=num_rows,
            )

        elif metric == "ves":
            executor = SQLVesEvaluator()
            _ = executor.execute(
                generator_config=generator_config,
                metric_config=metric_config,
                num_rows=num_rows,
            )
        else:
            executor = SQLExecutorEX()
            _ = executor.execute_ex(
                generator_config=generator_config,
                metric_config=metric_config,
                num_rows=num_rows,
            )

            executor = SQLVesEvaluator()
            _ = executor.execute(
                generator_config=generator_config,
                metric_config=metric_config,
                num_rows=num_rows,
            )

    else:
        eval_client = None
        raise NotImplementedError
    typer.echo("Starting to evaluate Generated SQL ...")

if __name__ == "__main__":
    app()
