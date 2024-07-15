import os

import typer

from text2sql.settings import root_path

app = typer.Typer()


@app.command()
def start_evaluation(model_name: str, engine: str):
    typer.echo("Starting evaluation")
