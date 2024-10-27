import os
import subprocess
import sys
from pathlib import Path

import click


@click.group()
def cli():
    """PremSQL CLI to manage API servers"""
    pass

@click.group()
@click.option('--help', '-h', is_flag=True, help="Show this message and exit.")
@click.pass_context
def cli(ctx, help):
    """PremSQL CLI to manage API servers and Streamlit app"""
    if help:
        click.echo(ctx.get_help())
        ctx.exit()

@cli.command()
def startapi():
    click.echo("Starting the PremSQL backend API server ...")
    premsql_path = Path(__file__).parent.parent.absolute()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(premsql_path)
    manage_py_path = premsql_path / "premsql" / "playground" / "backend" / "manage.py"

    if not manage_py_path.exists():
        click.echo(f"Error: manage.py not found at {manage_py_path}", err=True)
        sys.exit(1)

    cmd = [sys.executable, str(manage_py_path), "runserver"]
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error starting the API server: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("API server stopped.")


@cli.command()
def stopapi():
    click.echo("Stopping PremsQL API server...")

    try:
        if sys.platform == "win32":
            subprocess.run(
                [
                    "taskkill",
                    "/F",
                    "/IM",
                    "python.exe",
                    "/FI",
                    "WINDOWTITLE eq premsql*",
                ],
                check=True,
            )
        else:
            subprocess.run(["pkill", "-f", "manage.py runserver"], check=True)
        click.echo("API server stopped successfully.")
    except subprocess.CalledProcessError:
        click.echo("No running API server found.")
    except Exception as e:
        click.echo(f"Error stopping the API server: {e}", err=True)
        sys.exit(1)


@cli.command()
def startapp():
    click.echo("Starting the PremSQL Streamlit app...")
    premsql_path = Path(__file__).parent.parent.absolute()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(premsql_path)
    main_py_path = premsql_path / "premsql" / "playground" / "frontend" / "main.py"

    if not main_py_path.exists():
        click.echo(f"Error: main.py not found at {main_py_path}", err=True)
        sys.exit(1)

    cmd = [sys.executable, "-m", "streamlit", "run", str(main_py_path)]
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error starting the Streamlit app: {e}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("Streamlit app stopped.")


if __name__ == "__main__":
    cli()
